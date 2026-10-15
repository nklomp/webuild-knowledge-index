import pytest,httpx
from gateway.discussions import Discussions
from gateway.model import record,sections

def test_nested_discussion_pagination(monkeypatch):
    monkeypatch.setenv('SOURCE_READ_TOKEN','test-only')
    calls=[]
    def conn(nodes,cursor=None):return {'nodes':nodes,'pageInfo':{'hasNextPage':cursor is not None,'endCursor':cursor}}
    def handle(req):
        import json
        body=json.loads(req.content);q=body['query'];v=body['variables'];calls.append(v)
        d={'id':'d','title':'title','body':'body','url':'https://github.com/org/repo/discussions/1','updatedAt':'2026-01-01','closed':False}
        c={'id':'c','body':'comment','url':d['url']+'#c','updatedAt':'2026-01-01'}
        reply={'id':'r','body':'reply','url':d['url']+'#r','updatedAt':'2026-01-01'}
        if 'repository(' in q:data={'repository':{'discussions':conn([d] if v['cursor'] is None else [],'d-next' if v['cursor'] is None else None)}}
        elif '... on Discussion{' in q:data={'node':{'comments':conn([c] if v['cursor'] is None else [],'c-next' if v['cursor'] is None else None)}}
        else:data={'node':{'replies':conn([reply] if v['cursor'] is None else [],'r-next' if v['cursor'] is None else None)}}
        return httpx.Response(200,json={'data':data})
    rows,counts=Discussions(httpx.Client(transport=httpx.MockTransport(handle))).capture('org/repo','full-text')
    assert len(rows)==3 and len(calls)==6 and counts['discussion_replies']==1

def test_section_locators():
    r=record('x','sha','https://github.com/o/r/blob/sha/a.md','# First\ncontext\n# Second\nmore','repo')
    chunks=list(sections(r));assert len(chunks)==2 and chunks[1]['locator'].endswith('#L3-L4')

def test_invalid_relation_pagination(stores):
    _,reader,_=stores
    for operation in [lambda:reader.related(limit=0),lambda:reader.history('x',offset=-1),lambda:reader.changes('x',limit=1000)]:
        with pytest.raises(ValueError):operation()

def test_atomic_failed_publication(stores,corpus):
    writer,reader,old=stores
    corpus.append(corpus[0])
    import psycopg
    with pytest.raises(psycopg.errors.UniqueViolation):writer.publish(corpus,{'coverage':[{'state':'complete'}]})
    assert reader.manifest()['snapshot']==old

def test_visibility_quarantine_all_interfaces(stores):
    writer,reader,old=stores
    sid,safe=writer.quarantine(['architecture'],{'coverage':[{'state':'failed'}]})
    assert all(r['repository']!='architecture' for r in safe)
    for source in ['authzen','proposal']:
        with pytest.raises(LookupError):reader.source(source,old)
        assert reader.history(source)['history']==[]
    assert not reader.related('authzen',snapshot=old)['relations']
    assert all(x['source']['repository']!='architecture' for x in reader.search('key binding',old)['results'])
    assert reader.manifest()['snapshot']==sid

def test_unanswerable_does_not_assert_consensus(stores):
    _,reader,_=stores
    result=reader.search('What did all participants unanimously approve about Martian wallets?')
    assert 'do not establish consensus' in result['answer_status']
    assert 'answer' not in result and 'summary' not in result

def test_unique_blob_rename_preserves_identity(stores,corpus):
    writer,reader,old=stores
    corpus[0]['id']='new-path-identity';corpus[0]['locator']='adr/renamed.md';corpus[0]['title']='adr/renamed.md';corpus[0]['url']='https://github.com/webuild-consortium/wp4-architecture/blob/sha/adr/renamed.md'
    sid=writer.publish(corpus,{'coverage':[{'state':'complete'}]})
    source=reader.source('authzen',sid)['source']
    assert source['locator']=='adr/renamed.md' and 'adr/authzen.md' in source['aliases']
    assert reader.source('authzen',old)['source']['locator']=='adr/authzen.md'

def test_site_rebuild_removes_withdrawn_files(stores,corpus,tmp_path):
    from gateway.site import generate
    from gateway.model import digest
    writer,reader,old=stores
    generate(corpus,reader.manifest(old),tmp_path,'https://api.example.org')
    oldfile=tmp_path/(digest('authzen')[:24]+'.html');assert oldfile.exists()
    new,safe=writer.quarantine(['architecture'],{})
    generate(safe,reader.manifest(new),tmp_path,'https://api.example.org')
    assert not oldfile.exists() and 'authzen' not in (tmp_path/'sources.jsonl').read_text()

def test_readonly_surface(stores):
    from gateway.api import create_app
    _,reader,_=stores
    app=create_app(reader)
    assert all(route.methods <= {'GET','HEAD'} for route in app.routes if getattr(route,'path','').startswith('/v1/'))

def test_checkpoint_manifest_has_all_configured_repositories():
    import json
    from pathlib import Path
    evidence=Path('evidence/live-coverage.json')
    if not evidence.exists():pytest.skip('Live capture evidence not downloaded in isolated CI')
    cfg=json.loads(Path('config/sources.json').read_text());m=json.loads(evidence.read_text())
    assert set(cfg['repositories'])=={r['repository'].split('/')[-1] for r in m['coverage']}
    assert all('types' in r or r['state']=='failed' for r in m['coverage'])

def test_revoked_target_urls_hidden(stores,corpus):
    writer,reader,old=stores
    target=corpus[0]['url'];corpus[2]['text']+='\nReference '+target
    from gateway.model import digest
    corpus[2]['content_hash']=digest(corpus[2]['text'])
    before=writer.publish(corpus,{'coverage':[{'state':'complete'}]})
    assert any(r['target']==target for r in reader.related('closed',snapshot=before)['relations'])
    writer.quarantine(['architecture'],{})
    assert not any(r['target']==target for r in reader.related('closed',snapshot=before)['relations'])

def test_upstream_version_never_replaces_cited_baseline(stores,corpus):
    writer,reader,old=stores
    corpus[1]['specifications'][0]['upstream_version']='1.3.0'
    new=writer.publish(corpus,reader.manifest(old)['coverage'])
    assert new!=old
    source=reader.source('proposal',new)['source']
    assert source['specifications'][0]['cited_version']=='1.2.1'
    assert source['specifications'][0]['upstream_version']=='1.3.0'
    assert reader.search('ETSI',version='1.3.0')['results']==[]

def test_reader_cannot_bypass_public_views(stores):
    writer,reader,_=stores
    writer.quarantine(['architecture'],{})
    with reader.connect() as c:
        assert not c.execute("SELECT id FROM records WHERE id='authzen'").fetchone()
    import psycopg
    with reader.connect() as c:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):c.execute('SELECT * FROM public.records')

def test_contributor_quote_not_document_status():
    r=record('comment','sha','https://github.com/o/r/issues/1#comment','Status: accepted','r',kind='comment',lifecycle='closed')
    assert r['decision_status']=='unknown' and r['role']=='discussion-contribution'

def test_reader_credentials_cannot_impersonate_writer(stores):
    import os,psycopg
    from urllib.parse import urlparse,urlunparse
    reader=urlparse(os.environ['RETRIEVAL_DATABASE_URL'])
    wrong=urlunparse(reader._replace(netloc='gateway_ingest:'+reader.password+'@'+reader.hostname+':'+str(reader.port or 5432)))
    with pytest.raises(psycopg.OperationalError):psycopg.connect(wrong)
