import subprocess,tempfile,os,re
from pathlib import Path
import httpx
from .http import ReadClient
from .model import record,now,digest


def public_availability(repo,reader=None,client=None):
    """Confirm an empty public wiki from GitHub's own UI, never from Git errors."""
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo) or '..' in repo:raise ValueError('Invalid wiki repository')
    reader=reader or ReadClient()
    try:meta=reader.get('https://api.github.com/repos/'+repo,fresh=True).json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code!=404:raise
        from .ingest import RepositoryUnavailable
        raise RepositoryUnavailable('Wiki repository is no longer public/available') from None
    if meta.get('private'):
        from .ingest import RepositoryUnavailable
        raise RepositoryUnavailable('Wiki repository is private')
    if meta.get('full_name','').lower()!=repo.lower() or not meta.get('id'):raise ValueError('Cannot verify wiki repository identity')
    canonical='https://github.com/'+repo;url=canonical+'/wiki'
    # Separate anonymous browser client: source API credentials never reach HTML.
    owned=client is None;client=client or httpx.Client(timeout=30,follow_redirects=False)
    try:response=client.get(url,follow_redirects=False,timeout=30)
    finally:
        if owned:client.close()
    state='not-present-or-unavailable';method='unconfirmed-public-wiki-route'
    if response.status_code in (301,302,303,307,308) and response.headers.get('location','').rstrip('/')==canonical:
        state='not-published-at-source';method='github-wiki-route-redirects-to-public-repository'
    elif response.status_code==200:
        from bs4 import BeautifulSoup
        soup=BeautifulSoup(response.content,'html.parser');main=soup.find('main') or soup.find(attrs={'role':'main'})
        if main and not main.find(id='wiki-body'):
            for blank in main.select('.blankslate'):
                heading=blank.find(['h1','h2','h3'])
                create=blank.find('a',href='/'+repo+'/wiki/_new')
                if heading and create and heading.get_text(' ',strip=True)==f'Welcome to the {repo.split("/")[1]} wiki!' and create.get_text(' ',strip=True)=='Create the first page':
                    state='empty-at-source';method='github-empty-wiki-blankslate';break
    proof={'state':state,'method':method,'repository_id':meta['id'],'url':url,'http_status':response.status_code,'location':response.headers.get('location'),'response_sha256':digest(response.text),'checked_at':now()}
    if reader.journal:reader.journal.set('wiki_availability',proof)
    return state,proof

def capture(repo,permission,reader=None):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo) or '..' in repo:raise ValueError('Invalid wiki repository')
    if reader and reader.journal:reader.journal.set('wiki_availability',None)
    # Git transport fetch only; local bare copy in temporary project-owned storage.
    with tempfile.TemporaryDirectory(prefix='knowledge-wiki-') as directory:
        result=subprocess.run(['git','-c','credential.helper=','-c','credential.interactive=never','clone','--bare','https://github.com/'+repo+'.wiki.git',directory],capture_output=True,text=True,timeout=120,env={**os.environ,'GIT_TERMINAL_PROMPT':'0'})
        if result.returncode:
            if any(term in result.stderr.lower() for term in ['not found','could not read username','terminal prompts disabled']):
                state,_=public_availability(repo,reader)
                return [],state
            raise RuntimeError('Wiki fetch failed: '+result.stderr[:300])
        def git(*args):return subprocess.check_output(['git','--git-dir',directory,*args],text=True,timeout=60)
        revision=git('rev-parse','HEAD').strip();rows=[]
        for path in git('ls-tree','-r','--name-only','HEAD').splitlines():
            if path.endswith(('.md','.rst','.txt')):
                text=git('show',revision+':'+path)
                rows.append(record('wiki:'+repo+':'+path,revision,'https://github.com/'+repo+'/wiki/'+Path(path).stem,text,repo,'wiki',path=path,permissions=permission))
        return rows,'complete-supported-text'
