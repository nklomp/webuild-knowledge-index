import asyncio,json,os,socket,threading,time
from pathlib import Path
import pytest,psycopg,httpx,uvicorn
from mcp.client import Client
from fastapi.testclient import TestClient
from gateway.api import create_app
from gateway.model import record,validate,digest,classify
from gateway.ingest import GitHub
from gateway.site import generate

@pytest.mark.parametrize('status',['accepted','proposed','draft','superseded','deprecated','withdrawn'])
def test_status_evidence(status):
    r=record('x','v','https://example.org/source','Status: '+status,'r',path='adr/a.md');validate([r]);assert r['decision_status']==status

def test_closed_not_answered(corpus):assert corpus[2]['decision_status']=='unknown' and corpus[2]['unresolved_questions']
def test_merged_draft(corpus):assert corpus[1]['decision_status']=='draft' and corpus[1]['lifecycle']=='merged'
def test_exact_versions(corpus):assert corpus[1]['specifications'][0]['cited_version']=='1.2.1' and corpus[1]['specifications'][0]['upstream_version'] is None
def test_private_rejected(corpus):
    corpus[0]['visibility']='private'
    with pytest.raises(ValueError):validate(corpus)
def test_hash_validation(corpus):
    corpus[0]['text']='tampered'
    with pytest.raises(ValueError):validate(corpus)
def test_status_evidence_validation(corpus):
    corpus[0]['status_evidence']='unsupported'
    with pytest.raises(ValueError):validate(corpus)
def test_pagination_get_only():
    seen=[]
    def handle(req):
        seen.append(req); assert req.method=='GET'
        return httpx.Response(200,json=[{'id':len(seen)}],headers={'Link':'<https://api.github.com/page1?page=2>; rel="next"'} if len(seen)==1 else {})
    gh=GitHub(httpx.Client(transport=httpx.MockTransport(handle)))
    assert [r['id'] for r in gh.pages('https://api.github.com/page1')]==[1,2]
    with pytest.raises(ValueError):gh.get('https://evil.test/data')

def test_real_pgvector_and_fts(stores):
    _,reader,sid=stores;result=reader.search('historical authorization keys');assert result['snapshot']==sid
    assert result['results'][0]['source']['id']=='authzen'
    assert result['results'][0]['vector_distance']<1
    result=reader.search('AuthZEN');assert result['results'][0]['lexical_score']>0

def test_status_version_filter(stores):
    _,r,_=stores;assert [x['source']['id'] for x in r.search('authorization',status='draft',version='1.2.1')['results']]==['proposal']
def test_page_disjoint(stores):
    _,r,_=stores;a=r.search('wallet',limit=2);b=r.search('wallet',limit=2,offset=2)
    assert a['total']==5 and not ({x['source']['id'] for x in a['results']}&{x['source']['id'] for x in b['results']})
@pytest.mark.parametrize('kwargs',[{'limit':0},{'limit':101},{'offset':-1},{'q':'x'*1001}])
def test_bounds(stores,kwargs):
    _,r,_=stores
    with pytest.raises(ValueError):r.search(**({'q':'test'}|kwargs))
def test_idempotence(stores,corpus):
    w,r,s=stores;assert w.publish(corpus,r.manifest()['coverage'])==s
def test_model_mismatch(stores):
    _,r,_=stores;old=r.embed.revision;r.embed.revision='incompatible'
    try:
        with pytest.raises(ValueError):r.search('keys')
    finally:r.embed.revision=old

def test_reader_cannot_write(stores):
    _,r,_=stores
    for statement in ["INSERT INTO revoked VALUES('x','y')","UPDATE publication SET snapshot=NULL","DELETE FROM records","CREATE TABLE public.forbidden(id int)"]:
        with r.connect() as c:
            with pytest.raises(psycopg.Error):c.execute(statement)

def test_deleted_hidden_from_old_snapshot(stores,corpus):
    w,r,old=stores;new=w.publish(corpus[1:],{'coverage':[{'state':'complete'}]})
    with pytest.raises(LookupError):r.source('authzen',old)
    assert all(x['source']['id']!='authzen' for x in r.search('AuthZEN',old)['results'])
    assert new!=old

def test_pinned_revisions(stores,corpus):
    w,r,old=stores;corpus[0]['revision']='sha-new';corpus[0]['text']+='\nNew context';corpus[0]['content_hash']=digest(corpus[0]['text'])
    new=w.publish(corpus,{'coverage':[{'state':'complete'}]})
    assert r.source('authzen',old)['source']['revision']=='sha-auth'
    assert r.source('authzen',new)['source']['revision']=='sha-new'
    assert r.changes(old,new)['changes'][0]['id']=='authzen'
    assert len(r.history('authzen')['history'])==2

def test_relation_citations(stores):
    _,r,s=stores;result=r.related('authzen');assert result['snapshot']==s
    assert result['relations'][0]['evidence']['revision']=='sha-auth'
    assert result['relations'][0]['kind']=='references' and result['relations'][0]['confirmed']

def test_restricted_content(stores,corpus):
    w,r,_=stores;corpus[0]['reuse_permissions']='metadata-only';w.publish(corpus,{'coverage':[]})
    assert 'text' not in r.source('authzen')['source']

def test_rest_readonly_cors(stores):
    _,r,_=stores
    with TestClient(create_app(r)) as c:
        assert c.post('/v1/search',json={}).status_code==405
        assert c.get('/v1/manifest',headers={'Origin':'https://evil.test'}).status_code==403
        assert c.get('/v1/manifest',headers={'Origin':'http://localhost:8080'}).headers['access-control-allow-origin']=='http://localhost:8080'
        assert c.get('/v1/search',params={'q':'AuthZEN'}).json()==r.search('AuthZEN')
        assert c.get('/v1/decisions/authzen/history').status_code==200

def test_stale_health(stores):
    w,r,s=stores
    with w.connect() as c:c.execute("UPDATE snapshots SET manifest=jsonb_set(manifest,'{published_at}','\"2020-01-01T00:00:00+00:00\"') WHERE id=%s",(s,))
    with TestClient(create_app(r)) as c:assert c.get('/health').status_code==503

def test_safe_site_navigation(stores,corpus,tmp_path):
    _,r,s=stores;corpus[0]['text']+='<script>alert(1)</script>'
    generate(corpus,r.manifest(),tmp_path,'https://api.example.org')
    pages=list(tmp_path.glob('*.html'));assert {'index.html','groups.html','topics.html','questions.html','decisions.html','developers.html'}|{digest(r['id'])[:24]+'.html' for r in corpus}<={p.name for p in pages}
    assert '&lt;script&gt;' in ''.join(p.read_text() for p in pages)
    assert '<script>alert' not in ''.join(p.read_text() for p in pages)
    assert json.loads((tmp_path/'config.json').read_text())['snapshot']==s
    for artifact in ['llms.txt','sources.jsonl','topics.md','groups.html','topics.html','search.js']:assert (tmp_path/artifact).exists()
    assert 'Live search unavailable' in (tmp_path/'search.js').read_text()

@pytest.mark.parametrize('scheme',['http','https'])
def test_actual_remote_http_mcp_parity(stores,tmp_path,monkeypatch,scheme):
    import copy
    w,r,s=stores
    # Keep the selected snapshot older than latest, so dropping a snapshot argument
    # changes observable history/source results rather than passing accidentally.
    updated=copy.deepcopy(w.export_records(s))
    updated[0]['revision']='new-revision'
    updated[0]['text']+='\nNew reference https://example.org/new-policy'
    updated[0]['content_hash']=digest(updated[0]['text'])
    w.publish(updated,{'coverage':[{'state':'complete'}]})
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    tls={}
    if scheme=='https':
        import subprocess
        cert=tmp_path/'cert.pem';key=tmp_path/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=IP:127.0.0.1,DNS:localhost'],check=True,capture_output=True)
        monkeypatch.setenv('SSL_CERT_FILE',str(cert));tls={'ssl_keyfile':str(key),'ssl_certfile':str(cert)}
    server=uvicorn.Server(uvicorn.Config(create_app(r),host='127.0.0.1',port=port,log_level='warning',**tls))
    thread=threading.Thread(target=server.run,daemon=True);thread.start()
    for _ in range(100):
        if server.started:break
        time.sleep(.05)
    assert server.started
    async def check():
        async with Client(f'{scheme}://127.0.0.1:{port}/mcp') as client:
            tools=await client.list_tools();assert len(tools.tools)==6
            assert all(t.annotations.read_only_hint and not t.annotations.destructive_hint for t in tools.tools)
            result=await client.call_tool('search',{'q':'historical authorization keys','snapshot':s})
            assert not result.is_error
            assert result.structured_content==r.search('historical authorization keys',snapshot=s)
            for tool,args,path in [
                ('get_source',{'id':'authzen','snapshot':s},'/v1/sources/authzen'),
                ('get_related_sources',{'id':'authzen','snapshot':s,'offset':0,'limit':1},'/v1/relations'),
                ('get_related_specs',{'id':'authzen','snapshot':s,'offset':0,'limit':1},'/v1/relations'),
                ('get_decision_history',{'id':'authzen','snapshot':s,'offset':0,'limit':1},'/v1/decisions/authzen/history'),
                ('get_changes',{'before':s,'after':s,'offset':0,'limit':1},'/v1/changes')]:
                got=await client.call_tool(tool,args)
                params=dict(args)
                if tool in ['get_source','get_decision_history']:params.pop('id')
                if tool=='get_related_specs':params['specs']=True
                async with httpx.AsyncClient(verify=str(cert) if scheme=='https' else True,trust_env=False) as rest:
                    response=await rest.get(f'{scheme}://127.0.0.1:{port}'+path,params=params)
                assert response.status_code==200 and not got.is_error
                assert got.structured_content==response.json()
                assert got.structured_content['snapshot']==s
                if tool=='get_decision_history':assert got.structured_content['total']==1
            # Latest has an ordinary web reference as well as an official spec.
            # Filtering must therefore change the paginated first relation.
            args={'id':'authzen','limit':1}
            specs=await client.call_tool('get_related_specs',args)
            async with httpx.AsyncClient(verify=str(cert) if scheme=='https' else True,trust_env=False) as rest:
                response=await rest.get(f'{scheme}://127.0.0.1:{port}/v1/relations',params=args|{'specs':True})
            assert specs.structured_content==response.json()
            assert specs.structured_content['total']==1
            assert specs.structured_content['relations'][0]['target'].startswith('https://openid.net/')
    try:asyncio.run(check())
    finally:server.should_exit=True;thread.join(10)

def test_annotation_candidates(corpus):
    from gateway.annotations import validate_annotation
    a={'source_revision':corpus[0]['revision'],'model':'reviewed-extractor','prompt_version':'v1','claims':[{'evidence':['AuthZEN'],'relationship':'supersedes'}]}
    assert validate_annotation(a,corpus[0])['claims'][0]['status']=='candidate'
    a['claims'][0]['evidence']=['unsupported']
    with pytest.raises(ValueError):validate_annotation(a,corpus[0])
def test_external_catalogue_version_separation(corpus):
    from gateway.catalogue import references
    rows=references(corpus,['openid.net']);assert len(rows)==1
    assert rows[0]['specifications'][0]['upstream_version'] is None
    assert rows[0]['provenance']['referenced_by'][0]['revision']=='sha-auth'
def test_graphql_mutation_rejected():
    from gateway.discussions import Discussions
    with pytest.raises(ValueError):Discussions(None).query('mutation { delete }',{})
def test_failed_run_exposes_last_capture(stores):
    w,r,s=stores;w.report_run({'coverage':[{'state':'failed','repository':'fixture','captured_at':None,'error':'simulation'}]})
    with TestClient(create_app(r)) as client:
        data=client.get('/health').json();assert data['snapshot']==s and data['failed_sources'][0]['state']=='failed'


def test_liveness_before_first_publication(stores):
    w,r,_=stores
    with w.connect() as c:c.execute('DELETE FROM publication')
    with TestClient(create_app(r)) as c:
        assert c.get('/live').json()=={'status':'live'}
        assert c.get('/health').status_code==404
