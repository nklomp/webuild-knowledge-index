import httpx,pytest
from gateway.http import ReadClient,CaptureJournal
from gateway.wiki import public_availability
from gateway.ingest import RepositoryUnavailable


def probe(tmp_path,status=200,html='',location=None,private=False):
    calls=[]
    def handle(req):
        calls.append(req)
        if req.url.host=='api.github.com':
            assert req.headers['Authorization']=='Bearer source-read-sentinel'
            return httpx.Response(200,json={'id':1,'full_name':'o/r','private':private})
        assert 'Authorization' not in req.headers
        return httpx.Response(status,text=html,headers={'Location':location} if location else {})
    client=httpx.Client(transport=httpx.MockTransport(handle))
    reader=ReadClient(client,CaptureJournal(tmp_path/'wiki.sqlite'),token='source-read-sentinel')
    state,proof=public_availability('o/r',reader,client)
    assert reader.journal.get('wiki_availability')==proof
    return state,proof,calls


def test_github_empty_wiki_is_accounted_without_creating_a_page(tmp_path):
    html='<main><div class="blankslate"><h2>Welcome to the r wiki!</h2><a href="/o/r/wiki/_new">Create the first page</a></div></main>'
    state,proof,calls=probe(tmp_path,html=html)
    assert state=='empty-at-source' and proof['method']=='github-empty-wiki-blankslate'
    assert all(r.method=='GET' for r in calls) and len(calls)==2


def test_wiki_route_redirect_to_verified_public_repository_is_accounted(tmp_path):
    state,proof,_=probe(tmp_path,status=302,location='https://github.com/o/r')
    assert state=='not-published-at-source' and proof['repository_id']==1


@pytest.mark.parametrize('status,html,location',[
    (302,'','https://github.com/login'),
    (302,'','https://github.com/other/repo'),
    (403,'',''),
    (503,'',''),
    (200,'<main>Create the first page</main>',None),
    (200,'<main><div id="wiki-body">Existing wiki text</div><div class="blankslate"><h2>Welcome to the r wiki!</h2><a href="/o/r/wiki/_new">Create the first page</a></div></main>',None),
])
def test_auth_errors_and_existing_content_never_become_confirmed_absence(tmp_path,status,html,location):
    state,_,_=probe(tmp_path,status,html,location)
    assert state=='not-present-or-unavailable'


def test_private_repository_cannot_supply_public_wiki_absence_evidence(tmp_path):
    with pytest.raises(RepositoryUnavailable):probe(tmp_path,private=True)
