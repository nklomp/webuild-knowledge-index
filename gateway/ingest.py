"""Public-source ingestion. Durable page checkpoints are scoped to one capture generation."""
from __future__ import annotations
import io,json,os,tarfile,threading,uuid,hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
import httpx
from datetime import datetime,timezone,timedelta
from .http import ReadClient,CaptureJournal,DeferredRead
from .model import record,digest,now
from .extraction import parse_file

class RepositoryUnavailable(RuntimeError): pass

LICENSED_REUSE=['MIT','Apache-2.0','CC-BY-4.0','CC0-1.0','BSD-3-Clause']

def reuse_policy(cfg,name):
    """Explicit operator approval in the source configuration wins; otherwise an allow-listed licence grants full text."""
    policy=cfg.get('reuse_permissions') or {}
    explicit=(policy.get('overrides') or {}).get(name,policy.get('default'))
    if explicit not in [None,'full-text','metadata-only']:raise ValueError('Invalid reuse permission for '+name)
    return explicit

def atomic_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(data,indent=2));temporary.replace(path)

class GitHub:
    def __init__(self,client=None,journal=None,**kwargs):
        self.reader=client if isinstance(client,ReadClient) else ReadClient(client,journal,**kwargs)
        self.client=self.reader.client;self.journal=self.reader.journal
    def get(self,url):
        if not url.startswith('https://api.github.com/'):raise ValueError('Unapproved API read')
        return self.reader.get(url)
    def pages(self,url):return self.reader.pages(url)
    def add(self,rows,item):
        item['provenance'].setdefault('extracted_at',now())
        rows[item['id']]=item
        if self.journal:self.journal.put(item)
    def repo(self,name,previous=None,*,overlap_seconds=3600,reconcile_days=7,force_full=False,permission=None,recheck_closed_days=30):
        if not 60<=overlap_seconds<=86400 or not 1<=reconcile_days<=7:raise ValueError('Invalid polling/reconciliation interval')
        if len(name.split('/'))!=2 or any(x in name for x in ['..','?','#','\\']):raise ValueError('Invalid repository')
        base='https://api.github.com/repos/'+name
        try:meta=self.reader.get(base,fresh=True).json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code==404:raise RepositoryUnavailable('Repository metadata no longer public/available') from None
            raise
        if meta.get('private'):raise RepositoryUnavailable('Repository is private')
        self.reader.bind_repository(name,meta['id'])
        if self.journal:
            identity=self.journal.get('repository_id')
            if identity is not None and identity!=meta['id']:raise ValueError('Repository identity changed during resumed capture')
            self.journal.set('repository_id',meta['id']);self.journal.set('repository',name)
            if not self.journal.get('started_at'):self.journal.set('started_at',now())
        commit=self.get(base+'/commits/'+quote(meta['default_branch'],safe='')).json()['sha']
        tree=self.get(base+'/git/trees/'+commit+'?recursive=1').json()
        if tree.get('truncated'):
            def walk(sha,prefix='',ancestors=()):
                if sha in ancestors:raise ValueError('Cyclic Git tree')
                nested=self.get(base+'/git/trees/'+sha).json()
                if nested.get('truncated'):raise DeferredRead('Nonrecursive tree is incomplete')
                for entry in nested['tree']:
                    path=prefix+entry['path']
                    if entry['type']=='tree':yield from walk(entry['sha'],path+'/',ancestors+(sha,))
                    else:yield dict(entry,path=path)
            tree={'tree':list(walk(commit)),'truncated':False,'recovered_by_subtrees':True}
        licence=(meta.get('license') or {}).get('spdx_id')
        reuse_basis='operator-approval' if permission else 'licence:'+str(licence)
        permission=permission or ('full-text' if licence in LICENSED_REUSE else 'metadata-only')
        # Only reuse a successful capture of this exact repository and reuse policy.
        # Weekly full scans reconcile deleted issues; changed issue subtrees are
        # replaced daily, including removed comments/reviews. Cursor advancement
        # happens only when the entire repository capture succeeds.
        started_at=self.journal.get('started_at') if self.journal else now()
        prior=(previous or {}).get('coverage',{})
        incremental=False;since=None
        if previous and not force_full and prior.get('repository_id')==meta['id'] and prior.get('reuse_permissions')==permission:
            try:
                cutoff=datetime.fromisoformat(prior['last_full_reconciliation'])
                cursor=datetime.fromisoformat(prior['poll_cursor'])
                started=datetime.fromisoformat(started_at)
                incremental=timedelta(0)<=started-cutoff<timedelta(days=reconcile_days) and cursor<=started
                if incremental:since=(cursor-timedelta(seconds=overlap_seconds)).isoformat()
            except (KeyError,ValueError,TypeError):pass
        contribution_kinds={'issue','pull','comment','reviews','review_comments','review-thread'}
        rows={r['id']:r for r in (previous or {}).get('records',[]) if incremental and r['kind'] in contribution_kinds}
        counts={'tree_entries':len(tree['tree']),'binary_or_unsupported':0,'files':0,'issues':0,'pulls':0,'comments':0,'reviews':0,'review_comments':0,'releases':0,'attachments':0,'pdf':0}
        limitations=[]
        if self.journal:self.journal.set('phase','files')
        archive=self.reader.get(f'https://codeload.github.com/{name}/tar.gz/{commit}')
        with tarfile.open(fileobj=io.BytesIO(archive.content),mode='r:gz') as tar:
            members={m.name.split('/',1)[1]:m for m in tar.getmembers() if m.isfile() and '/' in m.name}
            for entry in tree['tree']:
                path=entry['path']
                if entry['type']!='blob':continue
                url=f'https://github.com/{name}/blob/{commit}/'+quote(path,safe='/')
                member=members.get(path)
                if entry.get('mode')=='120000':
                    counts['binary_or_unsupported']+=1
                    item=record(f"github:{meta['id']}:file:{path}",entry['sha'],url,path,name,'binary-metadata',path=path)
                    item['provenance']['extraction']={'method':'link-only','limitation':'symbolic link is never followed'};self.add(rows,item);continue
                if member is None:raise DeferredRead('Tree/archive mismatch at '+path)
                try:
                    if member.size>10_000_000:raise ValueError('Extraction size limit')
                    content=tar.extractfile(member).read()
                    expected=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
                    if entry['sha']!=expected:raise DeferredRead('Archive content does not match immutable Git blob')
                    text,extraction=parse_file(content,path)
                except (ValueError,UnicodeError,__import__('pypdf.errors',fromlist=['PdfReadError']).PdfReadError) as exc:
                    text=None;extraction={'method':'link-only','limitation':str(exc)}
                if text is None:
                    counts['binary_or_unsupported']+=1
                    item=record(f"github:{meta['id']}:file:{path}",entry['sha'],url,path,name,'binary-metadata',path=path,updated=meta.get('pushed_at'))
                else:
                    kind='pdf' if path.lower().endswith('.pdf') else 'file';counts['files']+=1
                    if kind=='pdf':counts['pdf']+=1
                    item=record(f"github:{meta['id']}:file:{path}",entry['sha'],url,text,name,kind,path=path,updated=None,permissions=permission)
                item['retrieved_at']=archive.extensions.get('captured_at',now())
                item['repository_id']=meta['id'];item['repository_aliases']=[name];item['provenance']['extraction']=extraction
                item['provenance']['source_commit']=commit;self.add(rows,item)
        if self.journal:self.journal.set('phase','issues-and-contributions')
        issue_url=base+'/issues?state=all&sort=created&direction=asc&per_page=100'
        if incremental:issue_url=base+'/issues?state=all&sort=updated&direction=asc&per_page=100&since='+quote(since,safe='')
        updated_issues=0
        def issue_updates():
            seen=set()
            for issue in self.pages(issue_url):
                seen.add('github:'+issue['node_id']);yield issue
            # Review resolution need not update the parent issue timestamp, so
            # retained PRs are rechecked daily while open or recently active.
            # Older closed PRs are covered by the weekly full reconciliation.
            recent=datetime.fromisoformat(started_at)-timedelta(days=recheck_closed_days)
            def active(row):
                if row.get('lifecycle')=='open':return True
                try:return datetime.fromisoformat(row['updated_at'].replace('Z','+00:00'))>=recent
                except (KeyError,AttributeError,TypeError,ValueError):return True  # Unknown age: recheck.
            for row in list(rows.values()):
                if row['kind']=='pull' and row['id'] not in seen and active(row):
                    number=int(row['url'].rstrip('/').rsplit('/',1)[-1])
                    try:yield self.get(base+'/issues/'+str(number)).json()
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code!=404:raise
                        # An unavailable child is not evidence that its entire
                        # repository has become private. Fail closed on capture.
                        raise DeferredRead('Previously captured PR is unavailable; full reconciliation required') from None
        for issue in issue_updates():
            updated_issues+=1
            # Replace the complete subtree. Retaining absent children would
            # resurrect deleted comments in an otherwise successful daily run.
            removed={'github:'+issue['node_id']}
            while True:
                children={key for key,value in rows.items() if value.get('parent_id') in removed}
                if children<=removed:break
                removed.update(children)
            for key in removed:rows.pop(key,None)
            kind='pull' if 'pull_request' in issue else 'issue';counts[kind+'s']+=1
            detail=self.get(base+'/pulls/'+str(issue['number'])).json() if kind=='pull' else issue
            lifecycle='merged' if detail.get('merged') else issue['state']
            item=record('github:'+issue['node_id'],digest(json.dumps([issue,detail],sort_keys=True)),issue['html_url'],issue['title']+'\n'+(issue.get('body') or ''),name,kind,lifecycle=lifecycle,updated=issue['updated_at'],permissions=permission)
            item['retrieved_at']=self.reader.item_times.get(id(issue),now())
            item.update(title=issue['title'],repository_id=meta['id'],actors=[{'github_login':issue['user']['login'],'evidence_url':issue['html_url']}] if issue.get('user') else [])
            if kind=='pull':item.update(merge_revision=detail.get('merge_commit_sha'),head_revision=detail.get('head',{}).get('sha'),base_revision=detail.get('base',{}).get('sha'))
            self.add(rows,item)
            for comment in self.pages(issue['comments_url']+'?per_page=100'):
                child=record('github:'+comment['node_id'],digest(json.dumps(comment,sort_keys=True)),comment['html_url'],comment.get('body') or '',name,'comment',updated=comment['updated_at'],permissions=permission)
                child['retrieved_at']=self.reader.item_times.get(id(comment),now())
                child.update(title=issue['title']+' (comment)',parent_id=item['id'],context_url=issue['html_url'],repository_id=meta['id']);self.add(rows,child);counts['comments']+=1
            if kind=='pull':
                for endpoint,ck in [('reviews','reviews'),('comments','review_comments')]:
                    for contribution in self.pages(base+'/pulls/'+str(issue['number'])+'/'+endpoint+'?per_page=100'):
                        child=record('github:'+contribution['node_id'],digest(json.dumps(contribution,sort_keys=True)),contribution.get('html_url') or issue['html_url'],contribution.get('body') or '',name,ck,lifecycle=contribution.get('state','unknown'),updated=contribution.get('updated_at') or contribution.get('submitted_at'),permissions=permission)
                        child['retrieved_at']=self.reader.item_times.get(id(contribution),now())
                        child.update(title=issue['title']+' ('+ck+')',parent_id=item['id'],context_url=issue['html_url'],repository_id=meta['id'],review_context={k:contribution.get(k) for k in ['path','line','original_line','commit_id','diff_hunk','in_reply_to_id']})
                        self.add(rows,child);counts[ck]+=1
                if self.reader.token:
                    from .review_threads import capture_threads
                    for child in capture_threads(self.reader,name,issue['number'],permission):
                        child.update(parent_id=item['id'],repository_id=meta['id'])
                        self.add(rows,child);counts['review_threads']=counts.get('review_threads',0)+1
                else:limitations.append('review thread resolution requires a read-only GraphQL token')
        if self.journal:self.journal.set('phase','releases')
        for release in self.pages(base+'/releases?per_page=100'):
            item=record('github:'+release['node_id'],digest(json.dumps(release,sort_keys=True)),release['html_url'],release['tag_name']+'\n'+(release.get('body') or ''),name,'release',updated=release.get('published_at'),permissions=permission)
            item.update(title=release.get('name') or release['tag_name'],tag=release['tag_name'],repository_id=meta['id']);self.add(rows,item);counts['releases']+=1
            # The embedded release assets array is not guaranteed to contain every asset.
            for asset in self.pages(base+'/releases/'+str(release['id'])+'/assets?per_page=100'):
                child=record('github:'+asset['node_id'],digest(json.dumps(asset,sort_keys=True)),asset['browser_download_url'],asset['name']+' '+asset.get('content_type',''),name,'attachment-metadata',updated=asset['updated_at'])
                child.update(title=asset['name'],parent_id=item['id'],media_type=asset.get('content_type'),size=asset.get('size'));self.add(rows,child);counts['attachments']+=1
        discussion_state='disabled at source'
        if meta.get('has_discussions'):
            if self.reader.token:
                from .discussions import Discussions
                discussion_rows,discussion_counts=Discussions(self.reader).capture(name,permission)
                for child in discussion_rows:self.add(rows,child)
                counts.update(discussion_counts);discussion_state='complete paginated connections'
            else:discussion_state='unavailable: read-only GraphQL token required';limitations.append(discussion_state)
        wiki_state='disabled at source'
        if meta.get('has_wiki'):
            from .wiki import capture as capture_wiki
            wiki_rows,wiki_state=capture_wiki(name,permission,self.reader)
            for child in wiki_rows:self.add(rows,child)
            counts['wiki_pages']=len(wiki_rows)
            if wiki_state=='not-present-or-unavailable':limitations.append('Wiki absence not confirmed independently')
        source_captured_at=min((item['retrieved_at'] for item in rows.values()),default=now())
        for kind,count_key in [('issue','issues'),('pull','pulls'),('comment','comments'),('reviews','reviews'),('review_comments','review_comments'),('review-thread','review_threads')]:
            counts[count_key]=sum(r['kind']==kind for r in rows.values())
        coverage={'repository':name,'repository_id':meta['id'],'state':'partial' if limitations else 'complete-for-supported-types','captured_at':started_at,'oldest_record_retrieved_at':source_captured_at,'completed_at':now(),'started_at':started_at,'commit':commit,'counts':counts,'limitations':sorted(set(limitations)),
          'wiki_availability':self.journal.get('wiki_availability') if self.journal else None,
          'reuse_basis':reuse_basis,'poll_mode':'overlap' if incremental else 'full-reconciliation','poll_since':since,'poll_cursor':started_at,'updated_issues_fetched':updated_issues,'last_full_reconciliation':prior['last_full_reconciliation'] if incremental else started_at,'removal_reconciliation':'Changed issue subtrees daily; removed issues at full reconciliation (at most '+str(reconcile_days)+' days)',
          'types':{'files':'all tree entries: text/PDF extraction or explicit link-only metadata','issues':'all states, paginated','pulls':'all states and merge lifecycle','comments':'paginated','reviews':'paginated','review_comments':'paginated including replies','review_threads':'GraphQL nested pagination' if self.reader.token else 'resolution unavailable','releases':'paginated','discussions':discussion_state,'wiki':wiki_state,'attachments':'paginated metadata; attachment bodies not fetched'},'historical_file_revisions':'captured daily revisions; initial default-branch tip, not every historical commit','reuse_permissions':permission,'transport':dict(self.reader.stats)}
        return list(rows.values()),coverage

def capture(config,out,initial=False,client=None,force_full=False):
    cfg=json.loads(Path(config).read_text());out=Path(out);out.mkdir(parents=True,exist_ok=True)
    names=[cfg['organization']+'/'+n for n in (cfg['initial'] if initial else cfg['repositories'])]+([] if initial else cfg.get('external_repositories',[]))
    state_path=out/'capture-state.json';old=json.loads(state_path.read_text()) if state_path.exists() else {}
    fingerprint=digest(json.dumps([cfg,names],sort_keys=True))
    from datetime import datetime,timezone
    within_window=(datetime.now(timezone.utc)-datetime.fromisoformat(old.get('started_at',now()))).total_seconds()<36*3600
    resume=old.get('status')=='incomplete' and old.get('configuration')==fingerprint and within_window
    state=old if resume else {'id':uuid.uuid4().hex,'configuration':fingerprint,'started_at':now()}
    state['force_full']=bool(force_full or state.get('force_full',False))
    state['status']='incomplete';atomic_json(state_path,state)
    records=[];coverage=[];discovery=[]
    discovery_reader=ReadClient(client,CaptureJournal(out/'captures'/state['id']/'discovery.sqlite'))
    try:discovery=[r['full_name'] for r in discovery_reader.pages('https://api.github.com/orgs/'+cfg['organization']+'/repos?per_page=100&type=public')]
    except Exception as exc:coverage.append({'source':'discovery','state':'failed','error':type(exc).__name__,'retry_at':getattr(exc,'retry_at',None)})
    polling=cfg.get('incremental_polling',{})
    # Waiting for a rate-limit reset is cheaper than failing a repository and
    # blocking publication; a longer wait still defers to the next run.
    max_wait=cfg.get('rate_limit_max_wait_seconds',900)
    def capture_repository(name):
        journal=CaptureJournal(out/'captures'/state['id']/(name.replace('/','__')+'.sqlite'))
        gh=GitHub(client,journal,max_wait=max_wait)
        try:
            baseline_path=out/(name.replace('/','__')+'.json')
            # Pin the baseline to this capture generation so interrupted runs use
            # exactly the same cursor and inherited rows after restart.
            baseline=journal.get('poll_baseline')
            if baseline is None:
                baseline=json.loads(baseline_path.read_text()) if baseline_path.exists() else {}
                if baseline.get('configuration')!=fingerprint:baseline={}
                journal.set('poll_baseline',baseline)
            rows,entry=gh.repo(name,baseline if polling.get('enabled') else None,overlap_seconds=polling.get('overlap_seconds',3600),reconcile_days=polling.get('reconcile_days',7),
                               recheck_closed_days=polling.get('recheck_closed_days',30),force_full=state['force_full'],permission=reuse_policy(cfg,name))
            entry['checkpoint']=journal.summary()
            journal.set('complete',True);journal.set('coverage',entry)
            atomic_json(out/(name.replace('/','__')+'.json'),{'records':rows,'coverage':entry,'configuration':fingerprint})
            return rows,entry
        except Exception as exc:
            quarantined=isinstance(exc,RepositoryUnavailable)
            entry={'repository':name,'state':'failed','error':type(exc).__name__+': '+str(exc)[:220], 'captured_at':None,'retained_data':False,'quarantine':quarantined,'retry_at':getattr(exc,'retry_at',None),'checkpoint':journal.summary(),'phase':journal.get('phase','metadata')}
            # Partial rows are checkpointed, but never mixed into a publishable corpus.
            if quarantined:
                with journal.connect() as c:c.execute('DELETE FROM items');c.execute('DELETE FROM responses')
            return [],entry
    # Repositories are independent (own journal, baseline and client), so they are
    # captured concurrently. Results are recorded in configuration order.
    finished={};progress=threading.Lock()
    def run(name):
        result=capture_repository(name)
        with progress:
            finished[name]=result
            atomic_json(out/'coverage.json',{'coverage':[finished[n][1] for n in names if n in finished],'capture_id':state['id'],'status':'incomplete','capture_time':now()})
    with ThreadPoolExecutor(max_workers=max(1,int(cfg.get('capture_concurrency',3)))) as pool:
        for future in [pool.submit(run,name) for name in names]:future.result()
    for name in names:
        rows,entry=finished[name];records.extend(rows);coverage.append(entry)
    for repository in ([] if initial else cfg.get('tagged_repositories',[])):
        journal=CaptureJournal(out/'captures'/state['id']/(repository.replace('/','__')+'__tags.sqlite'));reader=ReadClient(client,journal,max_wait=max_wait)
        try:
            metadata=reader.get('https://api.github.com/repos/'+repository,fresh=True).json()
            if metadata.get('private'):raise RepositoryUnavailable('Tagged repository is private')
            reader.bind_repository(repository,metadata['id'])
            from .tags import capture_tags
            tagged,editions=capture_tags(reader,repository,metadata['id'],reuse_policy(cfg,repository) or 'metadata-only',cfg.get('tag_paths',['README.md','docs/']))
            records.extend(tagged);coverage.append({'source':'tagged-editions:'+repository,'state':'complete-for-supported-types','captured_at':now(),'editions':editions,'checkpoint':journal.summary()})
        except Exception as exc:coverage.append({'source':'tagged-editions:'+repository,'state':'failed','captured_at':None,'error':type(exc).__name__,'checkpoint':journal.summary()})
    if cfg.get('official_sources_config'):
        from .official import capture_config
        official_config=cfg['official_sources_config']
        official,official_coverage=capture_config(official_config,ReadClient(client,CaptureJournal(out/'captures'/state['id']/'official.sqlite'),allowed_hosts=json.loads(Path(official_config).read_text())['allowed_hosts']))
        records.extend(official);coverage.extend(official_coverage)
    from .catalogue import references
    records.extend(references(records,cfg['allowed_reference_hosts']))
    complete=all(x['state'] not in ['failed','partial'] for x in coverage)
    manifest={'coverage':coverage,'capture_id':state['id'],'started_at':state['started_at'],'capture_time':now(),'status':'complete' if complete else 'incomplete','resumed':resume,'reconciled_repositories':names,'discovered_not_admitted':sorted(set(discovery)-set(names)),'records':len(records)}
    atomic_json(out/'records.json',records);atomic_json(out/'coverage.json',manifest)
    state['status']='complete' if complete else 'incomplete';atomic_json(state_path,state)
    return records,manifest
