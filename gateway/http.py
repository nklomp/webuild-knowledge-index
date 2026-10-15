"""Bounded, allowlisted read transport and durable per-capture response checkpoints."""
from __future__ import annotations
import json, os, re, sqlite3, time
from pathlib import Path
from urllib.parse import urlparse
import httpx
from .model import digest, now

class DeferredRead(RuntimeError):
    def __init__(self, message, retry_at=None):
        super().__init__(message); self.retry_at = retry_at

class CaptureJournal:
    """Only an unfinished capture reuses responses. New daily captures always refresh."""
    def __init__(self, path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS responses(key TEXT PRIMARY KEY,status INTEGER,body BLOB,headers TEXT,url TEXT,captured_at TEXT);
            CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY,data TEXT);
            CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT);''')
    def connect(self): return sqlite3.connect(self.path)
    def cached(self, key):
        with self.connect() as c: row = c.execute('SELECT status,body,headers,url,captured_at FROM responses WHERE key=?',(key,)).fetchone()
        if not row:return None
        response=httpx.Response(row[0],content=row[1],headers=json.loads(row[2]),request=httpx.Request('GET',row[3]));response.extensions['captured_at']=row[4];return response
    def save(self, key, response):
        # Never persist request headers, credentials, Set-Cookie or authorization responses.
        headers={k:v for k,v in response.headers.items() if k.lower() in {'link','etag','last-modified','content-type','x-ratelimit-remaining','x-ratelimit-reset'}}
        with self.connect() as c: c.execute('INSERT OR REPLACE INTO responses VALUES(?,?,?,?,?,?)',(key,response.status_code,response.content,json.dumps(headers),str(response.url),now()))
    def put(self, record):
        with self.connect() as c: c.execute('INSERT OR REPLACE INTO items VALUES(?,?)',(record['id'],json.dumps(record)))
    def records(self):
        with self.connect() as c: return [json.loads(r[0]) for r in c.execute('SELECT data FROM items ORDER BY id')]
    def set(self,key,value):
        with self.connect() as c:c.execute('INSERT OR REPLACE INTO state VALUES(?,?)',(key,json.dumps(value)))
    def get(self,key,default=None):
        with self.connect() as c:row=c.execute('SELECT value FROM state WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else default
    def summary(self):
        with self.connect() as c:
            return {'requests_completed':c.execute('SELECT count(*) FROM responses').fetchone()[0], 'records_checkpointed':c.execute('SELECT count(*) FROM items').fetchone()[0], 'resume_database':self.path.name}

class ReadClient:
    def __init__(self, client=None, journal=None, token=None, allowed_hosts=(), retries=3, max_wait=30, sleeper=time.sleep, clock=time.time):
        self.client=client or httpx.Client(timeout=60,follow_redirects=False)
        self.journal=journal; self.token=token if token is not None else os.getenv('SOURCE_READ_TOKEN')
        self.hosts={'api.github.com','codeload.github.com','raw.githubusercontent.com',*allowed_hosts}
        self.retries=retries;self.max_wait=max_wait;self.sleep=sleeper;self.clock=clock
        self.item_times={}
        self.repository_ids={}
        self.stats={'network_reads':0,'resumed_reads':0,'retries':0}
    def validate_url(self,url):
        u=urlparse(url)
        if u.scheme!='https' or u.hostname not in self.hosts or u.username or u.password or u.port not in (None,443):raise ValueError('Unapproved source URL')
        return u
    def request(self,url,query=None,variables=None,fresh=False):
        u=self.validate_url(url)
        if query is not None:
            if u.hostname!='api.github.com' or u.path!='/graphql' or not re.match(r'^\s*query\b',query) or re.search(r'\bmutation\b',query):raise ValueError('Only GitHub GraphQL queries are permitted')
        key=digest(json.dumps([url,query,variables],sort_keys=True))
        if not fresh and self.journal:
            cached=self.journal.cached(key)
            if cached is not None:self.stats['resumed_reads']+=1;return cached
        headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'} if u.hostname=='api.github.com' else {}
        if self.token and u.hostname=='api.github.com':headers['Authorization']='Bearer '+self.token
        for attempt in range(self.retries+1):
            try:
                self.stats['network_reads']+=1
                response=self.client.post(url,json={'query':query,'variables':variables},headers=headers) if query is not None else self.client.get(url,headers=headers)
            except httpx.TransportError:
                if attempt==self.retries:raise DeferredRead('Source transport unavailable') from None
                self.stats['retries']+=1;self.sleep(min(2**attempt,self.max_wait));continue
            rate=response.status_code==429 or (response.status_code==403 and ('retry-after' in response.headers or response.headers.get('x-ratelimit-remaining')=='0' or 'rate limit' in response.text.lower()))
            transient=rate or response.status_code in (500,502,503,504)
            if transient:
                reset=float(response.headers.get('x-ratelimit-reset',self.clock()))
                delay=max(float(response.headers.get('retry-after',0)), reset-self.clock() if rate else 0,2**attempt)
                if attempt==self.retries or delay>self.max_wait:raise DeferredRead('Source rate limited' if rate else 'Source temporarily unavailable',self.clock()+delay)
                self.stats['retries']+=1;self.sleep(delay);continue
            # Redirects are not followed: fetching outside the approved source boundary is prohibited.
            if 300<=response.status_code<400:raise ValueError('Source redirect requires an explicit approved URL')
            response.raise_for_status()
            if query is not None and response.json().get('errors'):raise DeferredRead('GraphQL returned errors or partial data')
            response.extensions['captured_at']=now()
            if self.journal:self.journal.save(key,response)
            return response
        raise AssertionError('unreachable')
    def get(self,url,fresh=False):return self.request(url,fresh=fresh)
    def graphql(self,query,variables):return self.request('https://api.github.com/graphql',query,variables).json()['data']
    def bind_repository(self,name,identity):
        if not re.fullmatch(r'[^/]+/[^/]+',name) or not isinstance(identity,int) or identity<=0:raise ValueError('Invalid repository identity')
        self.repository_ids[name]=identity
    def connection_path(self,url):
        # GitHub emits numeric repository URLs in Link headers even when the
        # initial request uses owner/name. Only aliases established by a fresh
        # public metadata read may resolve to the same connection.
        if url.hostname=='api.github.com':
            for name,identity in self.repository_ids.items():
                prefix='/repos/'+name+'/'
                if url.path.startswith(prefix):return '/repositories/'+str(identity)+'/'+url.path[len(prefix):]
        return url.path
    def pages(self,url):
        seen=set();initial=urlparse(url)
        while url:
            current=self.validate_url(url)
            if current.netloc!=initial.netloc or self.connection_path(current)!=self.connection_path(initial):raise ValueError('Pagination escaped source connection')
            if url in seen:raise ValueError('Repeated pagination cursor')
            seen.add(url);response=self.get(url);body=response.json()
            if not isinstance(body,list):raise ValueError('Expected a paginated list')
            for item in body:
                self.item_times[id(item)]=response.extensions.get('captured_at',now())
                yield item
            url=response.links.get('next',{}).get('url')
