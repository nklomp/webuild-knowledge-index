import html,json,os,shutil,tempfile
from pathlib import Path
from .model import digest
from .store import Store

def _generate_into(records,manifest,out,api,withdrawals=()):
    out=Path(out)
    marker=out/'.knowledge-generated'
    if out.exists() and any(out.iterdir()):
        if not marker.exists():raise ValueError('Refusing to replace an unowned output directory')
        for item in out.iterdir():
            if item.is_dir():shutil.rmtree(item)
            else:item.unlink()
    out.mkdir(parents=True,exist_ok=True);marker.write_text('webuild-knowledge-index generated artifact boundary\n')
    withdrawn=set(withdrawals)
    original_records=[r for r in records if r['id'] not in withdrawn and r['url'] not in withdrawn]
    records=original_records
    records=[Store.permitted(r) for r in records if r['visibility']=='public']
    def page(title,body): return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>'+html.escape(title)+'</title><link rel="stylesheet" href="style.css"><header><a href="index.html">WeBuild knowledge gateway</a> · <a href="groups.html">Working groups</a> · <a href="topics.html">Topics</a> · <a href="questions.html">Reading paths</a> · <a href="sources.jsonl">Export</a></header><main><h1>'+html.escape(title)+'</h1><p>Snapshot '+html.escape(manifest['snapshot'])+' · '+html.escape(manifest['published_at'])+'</p>'+body+'</main></html>'
    links=[];groups={};topics={}
    for r in records:
        filename=digest(r['id'])[:24]+'.html'; links.append((r,filename))
        groups.setdefault(r['repository'],[]).append((r,filename))
        for topic in r['topics']:topics.setdefault(topic,[]).append((r,filename))
        body='<p>Role: '+html.escape(r['role'])+' · Decision status: '+html.escape(r['decision_status'])+' · GitHub state: '+html.escape(r['lifecycle'])+'</p><p>Revision: '+html.escape(r['revision'])+' · Retrieved: '+html.escape(r['retrieved_at'])+'</p><p><a href="'+html.escape(r['url'],quote=True)+'">Original source and contribution channel</a></p><h2>Unresolved questions (source extraction)</h2><pre>'+html.escape('\n'.join(r['unresolved_questions']))+'</pre><h2>Exact cited specifications</h2><pre>'+html.escape(json.dumps(r['specifications'],indent=2))+'</pre><h2>Source</h2><pre>'+html.escape(r.get('text','Full text omitted pending reuse permission; follow the source link.'))+'</pre><h2>Provenance</h2><pre>'+html.escape(json.dumps(r['provenance']))+'</pre>'
        for assertion in r.get('source_assertions',[]):
            body+='<h2>Source-attributed note</h2><p>'+html.escape(assertion['statement'])+'</p><p>'+html.escape(assertion['classification'])+'</p><blockquote>'+html.escape(assertion['evidence'])+'</blockquote>'
        body+='<h2>Source scope and limitations</h2><pre>'+html.escape('\n'.join(r.get('scope_evidence',[])))+'</pre><h2>Existing terminology and schema entities</h2><pre>'+html.escape(json.dumps(r.get('entities',[])[:20],indent=2))+'</pre>'
        (out/filename).write_text(page(r['title'],body))
    def listing(items): return '<ul>'+''.join('<li><a href="'+f+'">'+html.escape(r['title'])+'</a> · '+html.escape(r['decision_status'])+'</li>' for r,f in items)+'</ul>'
    for name,data in [('groups',groups),('topics',topics)]:
        (out/(name+'.html')).write_text(page(name.title(),''.join('<h2>'+html.escape(k)+'</h2>'+listing(v) for k,v in sorted(data.items()))))
    questions=[('How can an EAA issuer key binding be checked?', 'eaa-key-binding-authzen.md'),('Which semantic layers define the business wallet vocabulary?', 'vocab/README.md'),('How are architecture decisions and conformance governed?', '07-governance-and-adr.md')]
    (out/'questions.html').write_text(page('Source-derived reading paths', '<p>These questions are derived from source content. They are not participant questions or frequently asked questions. Read the cited evidence, status and limitations; no normative answer is synthesized.</p>'+''.join('<h2>'+html.escape(question)+'</h2>'+listing([(r,f) for r,f in links if r['locator'].endswith(locator)]) for question,locator in questions)))
    body='<p>Public read-only evidence. Source-derived questions are not participant FAQs.</p><form id="search"><label>Search <input id="q" maxlength="1000" required></label><label>Status <select id="status"><option value="">All</option><option>accepted</option><option>proposed</option><option>draft</option><option>unknown</option><option>superseded</option></select></label><label>Index <select id="snapshot-mode"><option value="page">This page snapshot</option><option value="latest">Latest published</option></select></label><button>Search</button></form><p id="health" role="status"></p><div id="results"></div><button id="next" hidden>Next page</button><h2>Sources</h2>'+listing(links)+'<script src="search.js"></script>'
    (out/'index.html').write_text(page('Browse and retrieve WeBuild evidence',body))
    (out/'config.json').write_text(json.dumps({'api':api,'snapshot':manifest['snapshot']}))
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (out/'sources.jsonl').write_text('\n'.join(json.dumps(r) for r in records))
    (out/'relations.json').write_text(json.dumps([{'source':r['id'],'target':url,'kind':'references','evidence':{'url':r['url'],'revision':r['revision']},'snapshot':manifest['snapshot']} for r in original_records if r['visibility']=='public' for url in __import__('re').findall(r'https://[^\s<>\)\]]+',r.get('text','')) if url not in withdrawals],indent=2))
    (out/'llms.txt').write_text('# WeBuild read-only knowledge gateway\nSnapshot: '+manifest['snapshot']+'\n- [Sources](sources.jsonl)\n- [Manifest](manifest.json)\n- [Topics](topics.html)\nREST: '+api+'/v1/search\nMCP: '+api+'/mcp\n')
    (out/'topics.md').write_text('# Source-backed topic pack\n\n'+''.join('## '+k+'\n'+''.join('- ['+r['title']+']('+r['url']+') · '+r['decision_status']+' · '+r['revision']+'\n' for r,f in v) for k,v in topics.items()))
    (out/'style.css').write_text('body{font:17px system-ui;margin:2rem auto;max-width:1000px;padding:1rem;color:#152c43}a{color:#005a9c}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef3f7;padding:1rem}input,select,button{font:inherit;margin:.4rem}header{border-bottom:1px solid #aaa;padding:1rem}')
    (out/'search.js').write_text('''let offset=0, cfg, searchSnapshot=null; const health=document.getElementById('health'),results=document.getElementById('results'),next=document.getElementById('next');
fetch('config.json').then(r=>r.json()).then(c=>cfg=c);
async function run(){health.textContent='Searching live hybrid index…';results.replaceChildren();try{if(!cfg)throw Error('Configuration unavailable');let p=new URLSearchParams({q:document.getElementById('q').value,offset,limit:20});if(searchSnapshot)p.set('snapshot',searchSnapshot);else if(document.getElementById('snapshot-mode').value==='page')p.set('snapshot',cfg.snapshot);let status=document.getElementById('status').value;if(status)p.set('status',status);let r=await fetch(cfg.api+'/v1/search?'+p,{signal:AbortSignal.timeout(10000)});if(!r.ok)throw Error('Service returned '+r.status);let d=await r.json();searchSnapshot=d.snapshot;health.textContent='Snapshot '+d.snapshot+' · published '+d.published_at+(Date.now()-Date.parse(d.published_at)>36*3600000?' · FRESHNESS FAILURE':'');for(let item of d.results){let s=item.source,el=document.createElement('p'),a=document.createElement('a');a.href=item.matched_locator||s.url;a.textContent=s.title;el.append(a,document.createTextNode(' · '+s.decision_status+' · '+s.role+' · revision '+s.revision+' · retrieved '+s.retrieved_at+(item.semantic_match===false?' · below provisional semantic threshold':'')));results.append(el);}next.hidden=offset+20>=d.total;}catch(e){health.textContent='Live search unavailable: '+e.message+'. Browse generated pages and original sources above.';next.hidden=true;}}
document.getElementById('search').onsubmit=e=>{e.preventDefault();offset=0;searchSnapshot=null;run();};next.onclick=()=>{offset+=20;run();};''')


def verify_site(directory,manifest):
    import re
    directory=Path(directory)
    records=[json.loads(line) for line in (directory/'sources.jsonl').read_text().splitlines() if line]
    if len({r['id'] for r in records})!=len(records):raise ValueError('Duplicate exported source identity')
    if json.loads((directory/'manifest.json').read_text())['snapshot']!=manifest['snapshot']:raise ValueError('Site snapshot mismatch')
    for page in directory.glob('*.html'):
        for href in re.findall(r'href="([^"]+)"',page.read_text()):
            if not href.startswith('https://') and not (directory/href.split('#')[0]).exists():raise ValueError('Broken generated navigation: '+href)
    for source in records:
        if not source['revision'] or not source['url'].startswith('https://'):raise ValueError('Missing source evidence')
        if source['reuse_permissions']!='full-text' and 'text' in source:raise ValueError('Unpermitted content export')
    return {'snapshot':manifest['snapshot'],'sources':len(records),'html_pages':len(list(directory.glob('*.html'))),'navigation_valid':True,'permissions_valid':True}

def generate(records,manifest,out,api,withdrawals=()):
    out=Path(out)
    if out.exists() and any(out.iterdir()) and not (out/'.knowledge-generated').exists():raise ValueError('Refusing to replace an unowned output directory')
    out.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.knowledge-build-',dir=out.parent));backup=out.with_name(out.name+'.previous')
    try:
        _generate_into(records,manifest,temporary,api,withdrawals)
        report=verify_site(temporary,manifest);(temporary/'verification.json').write_text(json.dumps(report,indent=2))
        if backup.exists():shutil.rmtree(backup)
        if out.exists():out.rename(backup)
        try:temporary.rename(out)
        except BaseException:
            if backup.exists():backup.rename(out)
            raise
        if backup.exists():shutil.rmtree(backup)
    finally:
        if temporary.exists():shutil.rmtree(temporary)
