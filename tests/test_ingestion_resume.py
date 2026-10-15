"""Adversarial read-only transport and crawl fixtures; these do not claim live corpus capture."""
import io,json,tarfile
from pathlib import Path
import httpx,pytest
from gateway.http import CaptureJournal,ReadClient,DeferredRead
from gateway.ingest import GitHub,RepositoryUnavailable,capture
from gateway.model import digest

def test_retry_and_restart_uses_completed_page(tmp_path):
    seen=[];fail=[True]
    def handle(req):
        seen.append(str(req.url))
        if req.url.params.get('page')=='2' and fail[0]:return httpx.Response(429,headers={'Retry-After':'100'})
        return httpx.Response(200,json=[{'id':2}] if req.url.params.get('page')=='2' else [{'id':1}],headers={} if req.url.params.get('page')=='2' else {'Link':'<https://api.github.com/repos/o/r/issues?page=2>; rel="next"'})
    journal=CaptureJournal(tmp_path/'capture.sqlite');client=httpx.Client(transport=httpx.MockTransport(handle));r=ReadClient(client,journal,max_wait=0)
    with pytest.raises(DeferredRead):list(r.pages('https://api.github.com/repos/o/r/issues'))
    fail[0]=False;r=ReadClient(client,CaptureJournal(tmp_path/'capture.sqlite'))
    assert [x['id'] for x in r.pages('https://api.github.com/repos/o/r/issues')]==[1,2]
    assert seen.count('https://api.github.com/repos/o/r/issues')==1 and r.stats['resumed_reads']==1

def test_bounded_backoff_and_no_token_in_journal(tmp_path):
    delays=[];attempts=[]
    def handle(req):
        attempts.append(req)
        return httpx.Response(503) if len(attempts)<3 else httpx.Response(200,json={'ok':True})
    marker='test-only-source-read-sentinel'
    journal=CaptureJournal(tmp_path/'journal.sqlite');r=ReadClient(httpx.Client(transport=httpx.MockTransport(handle)),journal,token=marker,sleeper=delays.append)
    assert r.get('https://api.github.com/repos/o/r').json()['ok'];assert delays==[1,2]
    assert all(req.headers['Authorization']=='Bearer '+marker for req in attempts)
    assert marker.encode() not in (tmp_path/'journal.sqlite').read_bytes()

@pytest.mark.parametrize('target',['https://api.github.com.evil.test/data','https://secret@api.github.com/data','http://api.github.com/data','https://api.github.com:8443/data'])
def test_allowlist_not_string_prefix(target):
    with pytest.raises(ValueError):ReadClient().get(target)

def test_pagination_loop_and_escaped_connection():
    for next_url in ['https://api.github.com/repos/o/r/issues','https://api.github.com/repos/other/private/issues','https://evil.test/']:
        client=httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,json=[],headers={'Link':'<'+next_url+'>; rel="next"'})))
        with pytest.raises(ValueError):list(ReadClient(client).pages('https://api.github.com/repos/o/r/issues'))

@pytest.mark.parametrize('identity',[1,2])
def test_numeric_pagination_requires_bound_repository_identity(identity):
    def handle(req):
        if req.url.path.startswith('/repositories/'):
            return httpx.Response(200,json=[{'id':2}])
        return httpx.Response(200,json=[{'id':1}],headers={'Link':f'<https://api.github.com/repositories/{identity}/issues?page=2>; rel="next"'})
    reader=ReadClient(httpx.Client(transport=httpx.MockTransport(handle)))
    reader.bind_repository('o/r',1)
    if identity==1:assert [x['id'] for x in reader.pages('https://api.github.com/repos/o/r/issues')]==[1,2]
    else:
        with pytest.raises(ValueError,match='escaped'):list(reader.pages('https://api.github.com/repos/o/r/issues'))

def test_graphql_errors_never_checkpoint_partial_data(tmp_path):
    journal=CaptureJournal(tmp_path/'j.sqlite');client=httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'data':{'partial':True},'errors':[{'message':'quota'}]})))
    with pytest.raises(DeferredRead):ReadClient(client,journal).graphql('query { viewer { login } }',{})
    assert journal.summary()['requests_completed']==0

def archive():
    output=io.BytesIO()
    with tarfile.open(fileobj=output,mode='w:gz') as tar:
        data=b'# Decision\nStatus: draft\n';m=tarfile.TarInfo('r-commit/adr/a.md');m.size=len(data);tar.addfile(m,io.BytesIO(data))
    return output.getvalue()

def fixture_api(fail_comment=False,private=False,child_404=False):
    requests=[]
    def handle(req):
        requests.append(req);url=str(req.url);path=req.url.path
        if path=='/orgs/o/repos':return httpx.Response(200,json=[{'full_name':'o/r'}])
        if path=='/repos/o/r':return httpx.Response(200,json={'id':1,'private':private,'default_branch':'main','has_wiki':False,'has_discussions':False,'license':{'spdx_id':'MIT'}})
        if '/commits/' in path:return httpx.Response(200,json={'sha':'commit'})
        if '/git/trees/' in path:return httpx.Response(200,json={'tree':[{'type':'blob','path':'adr/a.md','sha':__import__('hashlib').sha1(b'blob '+str(len(b'# Decision\nStatus: draft\n')).encode()+b'\0'+b'# Decision\nStatus: draft\n').hexdigest()}]})
        if req.url.host=='codeload.github.com':return httpx.Response(200,content=archive())
        if path=='/repos/o/r/issues':
            return httpx.Response(200,json=[{'node_id':'I1','id':1,'number':1,'title':'Concern','body':'Open question','state':'closed','updated_at':'2026-10-01T00:00:00Z','html_url':'https://github.com/o/r/issues/1','comments_url':'https://api.github.com/repos/o/r/issues/1/comments'}])
        if path.endswith('/comments'):
            if child_404:return httpx.Response(404)
            if fail_comment:return httpx.Response(429,headers={'Retry-After':'1000'})
            return httpx.Response(200,json=[{'node_id':'C1','html_url':'https://github.com/o/r/issues/1#c','body':'Still unresolved','updated_at':'2026-10-01T00:00:00Z'}])
        if path.endswith('/releases'):return httpx.Response(200,json=[])
        raise AssertionError(url)
    return httpx.Client(transport=httpx.MockTransport(handle)),requests

def test_capture_resume_fresh_visibility_and_next_daily_generation(tmp_path):
    cfg=tmp_path/'sources.json';cfg.write_text(json.dumps({'organization':'o','repositories':['r'],'initial':['r'],'external_repositories':[],'allowed_reference_hosts':[]}))
    broken,seen=fixture_api(fail_comment=True);rows,m=capture(cfg,tmp_path/'owned',client=broken)
    assert m['status']=='incomplete' and rows==[] and m['coverage'][0]['checkpoint']['records_checkpointed']==2
    healthy,second=fixture_api();rows,m2=capture(cfg,tmp_path/'owned',client=healthy)
    assert m2['status']=='complete' and m2['resumed'] and len(rows)==3 and m2['capture_id']==m['capture_id']
    assert [r.url.path for r in second]==['/repos/o/r','/repos/o/r/issues/1/comments','/repos/o/r/releases']
    again,third=fixture_api();_,m3=capture(cfg,tmp_path/'owned',client=again)
    assert m3['capture_id']!=m2['capture_id'] and not m3['resumed'] and len(third)>3

def test_child_404_is_not_repository_visibility_loss(tmp_path):
    client,_=fixture_api(child_404=True)
    with pytest.raises(httpx.HTTPStatusError):GitHub(client,CaptureJournal(tmp_path/'j.sqlite')).repo('o/r')
    client,_=fixture_api(private=True)
    with pytest.raises(RepositoryUnavailable):GitHub(client,CaptureJournal(tmp_path/'k.sqlite')).repo('o/r')

def test_private_on_resume_does_not_reuse_public_metadata(tmp_path):
    journal=CaptureJournal(tmp_path/'j.sqlite');broken,_=fixture_api(fail_comment=True)
    with pytest.raises(DeferredRead):GitHub(broken,journal).repo('o/r')
    private,requests=fixture_api(private=True)
    with pytest.raises(RepositoryUnavailable):GitHub(private,journal).repo('o/r')
    assert len(requests)==1

def test_sealed_checkpoint_authentication_and_safe_restore(tmp_path,monkeypatch):
    import base64,importlib.util
    from cryptography.exceptions import InvalidTag
    spec=importlib.util.spec_from_file_location('checkpoint_tool',Path('scripts/checkpoints.py'));tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
    monkeypatch.setenv('CHECKPOINT_KEY',base64.b64encode(b'a'*32).decode())
    root=tmp_path/'owned';root.mkdir();(root/'capture-state.json').write_text('{"private-marker":"not-public"}')
    sealed=tmp_path/'sealed.bin';tool.seal(root,sealed)
    assert b'not-public' not in sealed.read_bytes()
    tool.restore(sealed,tmp_path/'recovered');assert (tmp_path/'recovered/capture-state.json').exists()
    content=bytearray(sealed.read_bytes());content[-1]^=1;sealed.write_bytes(content)
    with pytest.raises(InvalidTag):tool.restore(sealed,tmp_path/'tampered')

def test_archive_revision_integrity_is_enforced(tmp_path):
    client,_=fixture_api()
    original=client._transport
    def handle(req):
        response=original.handle_request(req)
        if '/git/trees/' in req.url.path:
            body=response.json();body['tree'][0]['sha']='a'*40;return httpx.Response(200,json=body)
        return response
    reader=GitHub(httpx.Client(transport=httpx.MockTransport(handle)),CaptureJournal(tmp_path/'j.sqlite'))
    with pytest.raises(DeferredRead,match='immutable Git blob'):reader.repo('o/r')

def test_new_capture_after_stale_resume_window(tmp_path):
    cfg=tmp_path/'sources.json';cfg.write_text(json.dumps({'organization':'o','repositories':['r'],'initial':['r'],'external_repositories':[],'allowed_reference_hosts':[]}))
    client,_=fixture_api(fail_comment=True);_,old=capture(cfg,tmp_path/'owned',client=client)
    path=tmp_path/'owned/capture-state.json';state=json.loads(path.read_text());state['started_at']='2020-01-01T00:00:00+00:00';path.write_text(json.dumps(state))
    healthy,_=fixture_api();_,fresh=capture(cfg,tmp_path/'owned',client=healthy)
    assert old['capture_id']!=fresh['capture_id'] and not fresh['resumed']
