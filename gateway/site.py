import html,json,re,shutil,tempfile
from collections import Counter,defaultdict
from pathlib import Path,PurePosixPath
from urllib.parse import urljoin
from markdown_it import MarkdownIt
from .model import digest
from .store import Store
from . import presentation as p

ASSETS=Path(__file__).with_name('site_assets')
SCHEME=re.compile(r'^[a-z][a-z0-9+.-]*:',re.I)

def e(value):return html.escape(str(value),quote=True)
def page_name(r):return digest(r['id'])[:24]+'.html'
def repo_page(repository):return 'repo-'+p.slug(repository)+'.html'
def topic_page(topic):return 'topic-'+p.slug(topic)+'.html'

def _markdown():
    md=MarkdownIt('commonmark',{'html':False}).enable(['table','strikethrough'])
    def absolute(url,env):return url if SCHEME.match(url) else urljoin(env['base'],url)
    def link_open(self,tokens,idx,options,env):
        token=tokens[idx];token.attrSet('href',absolute(token.attrGet('href') or '',env));token.attrSet('rel','noopener nofollow')
        return self.renderToken(tokens,idx,options,env)
    def image(self,tokens,idx,options,env):
        # Images are linked rather than embedded so pages never load third-party content.
        token=tokens[idx];alt=self.renderInlineAsText(token.children or [],options,env) or 'untitled'
        return '<a class="image-link" rel="noopener nofollow" href="'+e(absolute(token.attrGet('src') or '',env))+'">Image: '+e(alt)+'</a>'
    md.add_render_rule('link_open',link_open);md.add_render_rule('image',image)
    return md
MARKDOWN=_markdown()

def render_content(r):
    text=r.get('text')
    if not text or not text.strip():return None
    kind=p.content_format(r)
    if kind=='pdf':
        parts=re.split(r'<!-- page (\d+) -->',text);out=''
        if parts[0].strip():out+='<div class="pdf-page"><p>'+e(parts[0].strip())+'</p></div>'
        for number,body in zip(parts[1::2],parts[2::2]):
            paragraphs=[x.strip() for x in re.split(r'\n\s*\n',body) if x.strip()]
            out+='<div class="pdf-page"><p class="page-no">Page '+e(number)+'</p>'+''.join('<p>'+e(x)+'</p>' for x in paragraphs)+'</div>'
        return out
    if kind in ['code','plain']:return '<pre class="code"><code>'+e(text)+'</code></pre>'
    return MARKDOWN.render(text,{'base':r['url']})

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
    records=[Store.permitted(r) for r in original_records if r['visibility']=='public']
    write=lambda name,content:(out/name).write_text(content,encoding='utf-8')

    # Presentation index: titles, categories, and conversation threads (replies nest under their parent).
    titles={r['id']:p.display_title(r) for r in records}
    cats={r['id']:p.category(r) for r in records}
    threads={r['url']:r for r in records if r['kind'] in ['issue','pull','discussion']}
    replies=defaultdict(list);parent={}
    for r in records:
        if cats[r['id']]!='replies':continue
        thread=threads.get(p.thread_key(r['url']))
        if thread:replies[thread['id']].append(r);parent[r['id']]=thread
    by_repo=defaultdict(list);by_topic=defaultdict(list)
    for r in records:
        by_repo[r['repository']].append(r)
        for topic in r['topics']:by_topic[topic].append(r)
    listed=lambda items:[r for r in items if cats[r['id']]!='replies' or r['id'] not in parent]
    repositories=sorted(by_repo,key=lambda k:(list(p.OWNERS).index(p.owner_of(k)) if p.owner_of(k) in p.OWNERS else 99,-len(by_repo[k]),k))
    published=p.friendly_date(manifest.get('published_at'))
    date_key=lambda r:r.get('updated_at') or ''

    def layout(title,body,crumbs=(),home=False,scripts=()):
        nav=''.join('<a href="'+href+'">'+label+'</a>' for href,label in [('groups.html','Browse'),('decisions.html','Decisions'),('topics.html','Topics'),('questions.html','Reading paths'),('developers.html','For developers')])
        search='' if home else '<form class="header-search" action="index.html" role="search"><input type="search" name="q" placeholder="Search…" aria-label="Search the knowledge base" maxlength="1000"></form>'
        trail='' if not crumbs else '<nav class="crumbs" aria-label="Breadcrumb">'+' <span aria-hidden="true">›</span> '.join('<a href="'+href+'">'+e(label)+'</a>' if href else '<span>'+e(label)+'</span>' for href,label in crumbs)+'</nav>'
        return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(title)+' · WE BUILD knowledge base</title><link rel="stylesheet" href="style.css"></head><body>'
            '<header class="site"><div class="bar"><a class="brand" href="index.html"><span class="logo" aria-hidden="true">WB</span>WE BUILD knowledge base</a><nav class="main">'+nav+'</nav>'+search+'</div></header>'
            '<main>'+trail+body+'</main>'
            '<footer class="site"><p>A read-only index of public WE BUILD consortium and EUDI Wallet sources. Discussion and corrections happen in the original repositories.</p><p>Index updated '+e(published)+' · <a href="developers.html">API, MCP and exports</a></p></footer>'
            +''.join('<script src="'+s+'"></script>' for s in ('site.js',*scripts))+'</body></html>')

    def badges(r,with_status=False):
        out='<span class="badge cat-'+cats[r['id']]+'">'+e(p.kind_label(r))+'</span>'
        if p.state_label(r):out+='<span class="state state-'+p.slug(r['lifecycle'])+'">'+e(p.state_label(r))+'</span>'
        if r['decision_status']!='unknown':out+='<span class="state state-'+e(r['decision_status'])+'">'+e(r['decision_status'].capitalize())+'</span>'
        elif with_status and cats[r['id']] in ['decisions','conformance']:out+='<span class="state state-unknown" title="The source does not state a decision status">Status not stated</span>'
        return out

    def row(r,show_repo=False,show_path=True):
        meta=[badges(r)]
        sub=p.subtitle(r)
        if sub and show_path and sub!=titles[r['id']]:meta.append('<span class="muted path">'+e(sub)+'</span>')
        if show_repo:meta.append('<span class="muted">'+e(p.repository_label(r['repository']))+'</span>')
        if r.get('updated_at'):meta.append('<time datetime="'+e(r['updated_at'])+'">'+e(p.friendly_date(r['updated_at']))+'</time>')
        if replies.get(r['id']):meta.append('<span class="muted">'+str(len(replies[r['id']]))+' replies</span>')
        return '<li class="item"><a class="item-title" href="'+page_name(r)+'">'+e(titles[r['id']])+'</a><span class="item-meta">'+' '.join(meta)+'</span></li>'

    def items(rs,**kw):return '<ul class="items">'+''.join(row(r,**kw) for r in rs)+'</ul>'

    def filter_box(target,placeholder='Filter this page…'):
        return '<div class="filter"><input type="search" data-filter="'+target+'" placeholder="'+e(placeholder)+'" aria-label="'+e(placeholder)+'"><span class="muted" id="'+target+'-count"></span></div>'

    def folders(rs):
        tree=defaultdict(list)
        for r in rs:tree[str(PurePosixPath(r.get('locator') or '').parent).strip('.')].append(r)
        order=lambda r:(PurePosixPath(r.get('locator') or '').stem.lower() not in ['readme','index'],titles[r['id']].lower())
        out=''
        for folder in sorted(tree,key=lambda f:(f!='',f.lower())):
            rows=items(sorted(tree[folder],key=order),show_path=False)
            if not folder:out+='<div data-filter-group>'+rows+'</div>'
            else:out+='<details class="folder" data-filter-group'+(' open' if len(tree)<=6 else '')+'><summary><span class="folder-name">'+e(folder)+'/</span> <span class="count">'+str(len(tree[folder]))+'</span></summary>'+rows+'</details>'
        return out

    def by_host(rs):
        hosts=defaultdict(list)
        for r in rs:hosts[p.HOSTS.get(p.subtitle(r),p.subtitle(r).removeprefix('www.'))].append(r)
        return ''.join('<details class="folder" data-filter-group><summary><span class="folder-name">'+e(h)+'</span> <span class="count">'+str(len(v))+'</span></summary>'+items(sorted(v,key=lambda r:titles[r['id']].lower()),show_path=False)+'</details>' for h,v in sorted(hosts.items(),key=lambda kv:-len(kv[1])))

    def releases(rs):
        tags={};loose=[]
        for r in rs:
            m=re.search(r'/releases/(?:tag|download)/([^/#?]+)',r['url'])
            if r['kind']=='release' and m:tags[m.group(1)]=(r,[])
        for r in rs:
            m=re.search(r'/releases/download/([^/#?]+)/',r['url'])
            if r['kind']!='release':(tags[m.group(1)][1] if m and m.group(1) in tags else loose).append(r)
        out='<ul class="items">'
        for release,attachments in sorted(tags.values(),key=lambda t:date_key(t[0]),reverse=True):
            out+=row(release)[:-5]+(items(attachments,show_path=False) if attachments else '')+'</li>'
        return out+'</ul>'+(items(loose) if loose else '')

    def sections(rs,show_repo=False):
        grouped=defaultdict(list)
        for r in listed(rs):grouped[cats[r['id']]].append(r)
        toc='<nav class="pills">'+''.join('<a href="#'+key+'">'+label+' <span class="count">'+str(len(grouped[key]))+'</span></a>' for key,label,_ in p.CATEGORIES if grouped[key])+'</nav>'
        body=''
        for key,label,description in p.CATEGORIES:
            rs=grouped[key]
            if not rs:continue
            if key in ['documents','files']:content=folders(rs) if not show_repo else items(sorted(rs,key=lambda r:titles[r['id']].lower()),show_repo=True)
            elif key=='specifications' and not show_repo:content=by_host(rs)
            elif key=='releases' and not show_repo:content=releases(rs)
            elif key in ['decisions','conformance']:content=items(sorted(rs,key=lambda r:titles[r['id']].lower()),show_repo=show_repo)
            else:content=items(sorted(rs,key=date_key,reverse=True),show_repo=show_repo)
            body+='<section id="'+key+'" class="group" data-filter-group><h2>'+label+' <span class="count">'+str(len(rs))+'</span></h2><p class="muted">'+e(description)+'</p>'+content+'</section>'
        return toc,body

    # Source pages
    for r in records:
        repo_crumb=(repo_page(r['repository']),p.repository_label(r['repository']))
        crumbs=[('index.html','Home'),repo_crumb]
        if r['id'] in parent:crumbs.append((page_name(parent[r['id']]),titles[parent[r['id']]['id']]))
        else:crumbs.append((repo_page(r['repository'])+'#'+cats[r['id']],p.CATEGORY_LABELS[cats[r['id']]]))
        meta=badges(r,True)+''.join('<a class="chip" href="'+topic_page(t)+'">'+e(t)+'</a>' for t in r['topics'])
        dates=[]
        if r.get('updated_at'):dates.append('Updated <time datetime="'+e(r['updated_at'])+'">'+e(p.friendly_date(r['updated_at']))+'</time>')
        dates.append('Revision <code title="'+e(r['revision'])+'">'+e(r['revision'][:10])+'</code>')
        dates.append('Retrieved '+e(p.friendly_date(r['retrieved_at'])))
        body='<article class="source"><h1>'+e(titles[r['id']])+'</h1><div class="meta">'+meta+'</div>'
        if p.subtitle(r):body+='<p class="muted path">'+e(p.repository_label(r['repository']))+' · '+e(p.subtitle(r))+'</p>'
        body+='<p class="actions"><a class="button" rel="noopener" href="'+e(r['url'])+'">Open original source ↗</a><span class="muted">'+' · '.join(dates)+'</span></p>'
        if r['id'] in parent:body+='<p class="notice">Part of <a href="'+page_name(parent[r['id']])+'">'+e(titles[parent[r['id']]['id']])+'</a>.</p>'
        for assertion in r.get('source_assertions',[]):
            body+='<aside class="notice"><strong>Source-attributed note.</strong> '+e(assertion['statement'])+'<br><span class="muted">'+e(assertion['classification'])+'</span><blockquote>'+e(assertion['evidence'])+'</blockquote></aside>'
        content=render_content(r)
        if content:body+='<div class="content">'+content+'</div>'
        elif r['reuse_permissions']!='full-text':body+='<p class="empty">The full text of this source is not republished here. <a href="'+e(r['url'])+'" rel="noopener">Read it at the original source ↗</a></p>'
        if r['unresolved_questions']:
            body+='<section class="callout"><h2>Open questions mentioned in the source</h2><ul>'+''.join('<li>'+MARKDOWN.renderInline(q.strip(' -*#'),{'base':r['url']})+'</li>' for q in r['unresolved_questions'][:20])+'</ul></section>'
        specs=[s for s in r['specifications'] if s.get('identity')]
        if specs:
            body+='<section><h2>Cited specifications</h2><ul class="specs">'
            for s in specs[:50]:
                label=s['identity'] if not s['identity'].startswith('http') else p.display_title({'id':'','kind':'external-reference','url':s['identity'],'title':''})
                version='' if s.get('cited_version') in [None,'unknown'] else ' <span class="muted">version '+e(s['cited_version'])+'</span>'
                clauses=' <span class="muted">clauses '+e(', '.join(s.get('clause_identifiers') or []))+'</span>' if s.get('clause_identifiers') else ''
                link=s.get('official_url') or (s['identity'] if s['identity'].startswith('https://') else None)
                body+='<li>'+('<a href="'+e(link)+'" rel="noopener">'+e(label)+'</a>' if link else e(label))+version+clauses+'</li>'
            body+='</ul></section>'
        if replies.get(r['id']):
            body+='<section class="conversation"><h2>Conversation <span class="count">'+str(len(replies[r['id']]))+'</span></h2>'
            for reply in sorted(replies[r['id']],key=lambda x:(x.get('updated_at') or '9999',x['id'])):
                text=render_content(reply)
                body+=('<article class="reply"><header>'+badges(reply)+(' <time>'+e(p.friendly_date(reply['updated_at']))+'</time>' if reply.get('updated_at') else '')
                    +' <a class="muted" href="'+page_name(reply)+'">Permalink</a> · <a class="muted" rel="noopener" href="'+e(reply['url'])+'">On GitHub ↗</a></header>'
                    +('<div class="content">'+text+'</div>' if text else '' if reply['reuse_permissions']=='full-text' else '<p class="empty">Text not republished; open it on GitHub.</p>')+'</article>')
            body+='</section>'
        tech=[('Identifier',r['id']),('Source kind',r['kind']),('Role',r['role']),('Repository',r['repository']),('Locator',r.get('locator')),
              ('Decision status',r['decision_status']+(' (evidence: '+r['status_evidence']+')' if r.get('status_evidence') else '')),('GitHub state',r['lifecycle']),
              ('Revision',r['revision']),('Retrieved',r['retrieved_at']),('Content hash',r.get('content_hash')),('Reuse permission',r['reuse_permissions']),
              ('Provenance',json.dumps(r['provenance']))]
        body+='<details class="tech"><summary>Technical details</summary><dl>'+''.join('<dt>'+k+'</dt><dd><code>'+e(v)+'</code></dd>' for k,v in tech if v not in [None,''])+'</dl>'
        if r.get('scope_evidence'):body+='<h3>Scope and limitation mentions</h3><pre>'+e('\n'.join(r['scope_evidence']))+'</pre>'
        if r['specifications']:body+='<h3>Extracted specification citations</h3><pre>'+e(json.dumps(r['specifications'],indent=2))+'</pre>'
        if r.get('entities'):body+='<h3>Terminology and schema entities</h3><pre>'+e(json.dumps(r['entities'][:20],indent=2))+'</pre>'
        body+='</details></article>'
        write(page_name(r),layout(titles[r['id']],body,crumbs))

    # Collections
    def summary(rs):
        counts=Counter(cats[r['id']] for r in listed(rs))
        return ' · '.join(str(counts[k])+' '+label.lower() for k,label,_ in p.CATEGORIES if counts[k] and k!='replies')
    def cards(repos):
        return '<div class="cards">'+''.join('<a class="card" href="'+repo_page(k)+'"><strong>'+e(p.repository_label(k))+'</strong>'+('<span>'+e(p.repository_description(k))+'</span>' if p.repository_description(k) else '')+'<span class="muted">'+e(summary(by_repo[k]))+'</span></a>' for k in repos)+'</div>'
    def owners():
        out=''
        for owner in dict.fromkeys(p.owner_of(k) for k in repositories):
            label,description=p.OWNERS.get(owner,(owner,None))
            out+='<section><h2>'+e(label)+'</h2>'+('<p class="muted">'+e(description)+'</p>' if description else '')+cards([k for k in repositories if p.owner_of(k)==owner])+'</section>'
        return out
    for k in repositories:
        toc,body=sections(by_repo[k])
        head='<h1>'+e(p.repository_label(k))+'</h1>'+('<p class="lede">'+e(p.repository_description(k))+'</p>' if p.repository_description(k) else '')
        if '/' in k:head+='<p class="actions"><a class="button" rel="noopener" href="https://github.com/'+e(k)+'">Repository on GitHub ↗</a><span class="muted">'+e(k)+'</span></p>'
        write(repo_page(k),layout(p.repository_label(k),head+toc+filter_box('listing')+'<div id="listing">'+body+'</div>',[('index.html','Home'),('groups.html',p.owner_label(k))]))
    write('groups.html',layout('Browse collections','<h1>Browse collections</h1><p class="lede">Every indexed repository, grouped by owner. Open one to see its decisions, documents, discussions, issues and pull requests.</p>'+owners(),[('index.html','Home')]))

    decisions=[r for r in records if cats[r['id']] in ['decisions','conformance']]
    toc,body=sections(decisions,show_repo=True)
    write('decisions.html',layout('Decisions and conformance','<h1>Decisions and conformance specifications</h1><p class="lede">Architecture decision records express decisions and their rationale; conformance specifications express implementation requirements. Statuses are shown only when the source states one.</p>'+toc+filter_box('listing')+'<div id="listing">'+body+'</div>',[('index.html','Home')]))

    # Topics
    topic_cards='<div class="cards">'+''.join('<a class="card" href="'+topic_page(t)+'"><strong>'+e(t)+'</strong><span>'+e(p.TOPICS.get(t,''))+'</span><span class="muted">'+str(len(listed(v)))+' items</span></a>' for t,v in sorted(by_topic.items(),key=lambda kv:-len(kv[1])))+'</div>'
    write('topics.html',layout('Topics','<h1>Topics</h1><p class="lede">Cross-cutting subjects that connect information across repositories. Topics are detected from terms used in the sources.</p>'+topic_cards,[('index.html','Home')]))
    for topic,rs in by_topic.items():
        toc,body=sections(rs,show_repo=True)
        nested=len(rs)-len(listed(rs))
        head='<h1>'+e(topic)+'</h1><p class="lede">'+e(p.TOPICS.get(topic,''))+'</p>'+('<p class="muted">'+str(nested)+' further comments and reviews mention this topic; they appear inside their conversations.</p>' if nested else '')
        write(topic_page(topic),layout(topic,head+toc+filter_box('listing')+'<div id="listing">'+body+'</div>',[('index.html','Home'),('topics.html','Topics')]))

    questions=[('How can an EAA issuer key binding be checked?','eaa-key-binding-authzen.md'),('Which semantic layers define the business wallet vocabulary?','vocab/README.md'),('How are architecture decisions and conformance governed?','07-governance-and-adr.md')]
    paths=''.join('<section class="path-card"><h2>'+e(question)+'</h2>'+(items([r for r in records if r['locator'].endswith(locator)],show_repo=True) or '')+'</section>' for question,locator in questions)
    write('questions.html',layout('Reading paths','<h1>Reading paths</h1><p class="lede">Starting points for common questions, pointing at the sources that address them.</p><p class="notice">These questions are derived from source content. They are not participant questions or frequently asked questions. Read the cited evidence, status and limitations; no normative answer is synthesized.</p>'+paths,[('index.html','Home')]))

    # Developers: everything technical lives here rather than on reader-facing pages.
    coverage=(manifest.get('coverage') or {}).get('coverage') if isinstance(manifest.get('coverage'),dict) else None
    cov=''
    if coverage:cov='<h2>Source coverage</h2><table><thead><tr><th>Source</th><th>State</th><th>Captured</th></tr></thead><tbody>'+''.join('<tr><td>'+e(c.get('repository',c.get('source','')))+'</td><td>'+e(c.get('state',''))+'</td><td>'+e(p.friendly_date(c.get('captured_at')))+'</td></tr>' for c in coverage)+'</tbody></table>'
    dev=('<h1>For developers and AI assistants</h1><p class="lede">The same index that powers this site is available over a REST API and a remote, read-only MCP server.</p>'
        '<h2>Endpoints</h2><dl class="kv"><dt>MCP server (streamable HTTP)</dt><dd><code>'+e(api)+'/mcp</code></dd><dt>REST search</dt><dd><code>'+e(api)+'/v1/search?q=…</code></dd><dt>Single source</dt><dd><code>'+e(api)+'/v1/sources/{id}</code></dd><dt>Relations</dt><dd><code>'+e(api)+'/v1/relations</code></dd><dt>Decision history</dt><dd><code>'+e(api)+'/v1/decisions/{id}/history</code></dd><dt>Changes</dt><dd><code>'+e(api)+'/v1/changes?before=…</code></dd><dt>Service health</dt><dd><code>'+e(api)+'/health</code></dd></dl>'
        '<h2>Exports</h2><ul><li><a href="sources.jsonl">sources.jsonl</a> — every public source record</li><li><a href="relations.json">relations.json</a> — source-to-reference relations</li><li><a href="manifest.json">manifest.json</a> — snapshot manifest</li><li><a href="topics.md">topics.md</a> — topic pack in Markdown</li><li><a href="llms.txt">llms.txt</a> — index for language models</li><li><a href="catalog.json">catalog.json</a> — compact title catalogue used by site search</li></ul>'
        '<h2>Snapshot</h2><dl class="kv"><dt>Snapshot</dt><dd><code>'+e(manifest['snapshot'])+'</code></dd><dt>Published</dt><dd><code>'+e(manifest['published_at'])+'</code></dd><dt>Records</dt><dd>'+str(len(records))+'</dd></dl>'+cov)
    write('developers.html',layout('For developers',dev,[('index.html','Home')]))

    # Home
    counts=Counter(cats[r['id']] for r in records)
    stats=[(counts['decisions']+counts['conformance'],'decisions and requirements','decisions.html'),(counts['documents'],'documents',None),(counts['discussions']+counts['issues']+counts['pulls'],'discussions, issues and pull requests',None),(counts['specifications'],'referenced specifications',repo_page('external-specifications') if 'external-specifications' in by_repo else None)]
    stat_html='<div class="stats">'+''.join(('<a href="'+link+'"' if link else '<div')+' class="stat"><strong>'+format(n,',')+'</strong><span>'+label+'</span>'+('</a>' if link else '</div>') for n,label,link in stats)+'</div>'
    recent=sorted([r for r in records if cats[r['id']] in ['decisions','conformance','documents','discussions','issues','pulls'] and p.owner_of(r['repository'])=='webuild-consortium' and r.get('updated_at')],key=date_key,reverse=True)[:10]
    option=lambda value,label:'<option value="'+e(value)+'">'+e(label)+'</option>'
    form=('<form id="search" role="search"><div class="searchbar"><label class="sr-only" for="q">Search</label><input id="q" name="q" type="search" maxlength="1000" required autocomplete="off" placeholder="Search decisions, documents, discussions… (try “key binding” or “trusted list”)"><button>Search</button></div>'
        '<div class="filters"><label>Collection <select id="scope" name="scope"><option value="">All collections</option>'+''.join(option(k,p.repository_label(k)) for k in repositories)+'</select></label>'
        '<label>Type <select id="type" name="type"><option value="">All types</option>'+''.join(option(k,label) for k,label,_ in p.CATEGORIES if k!='replies' and counts[k])+'</select></label>'
        '<label>Topic <select id="topic" name="topic"><option value="">All topics</option>'+''.join(option(t,t) for t in sorted(by_topic))+'</select></label>'
        '<details class="advanced"><summary>Advanced</summary><label>Decision status <select id="status"><option value="">Any</option><option>accepted</option><option>proposed</option><option>draft</option><option>unknown</option><option>superseded</option></select></label><label>Index version <select id="snapshot-mode"><option value="page">Same as this site</option><option value="latest">Latest published</option></select></label></details></div></form>')
    results=('<div id="search-results" hidden><p id="health" role="status"></p>'
        '<section id="instant-section"><h2>Matching titles <span class="count" id="instant-count"></span></h2><ul class="items" id="instant"></ul><button type="button" class="link" id="more-instant" hidden>Show more titles</button></section>'
        '<section><h2>Full-text and semantic matches</h2><p class="muted">Searches inside the text of every source, including comments and reviews, by meaning as well as by keyword. Results are evidence, not answers.</p><div id="results"></div><button type="button" id="next" hidden>More results</button></section></div>')
    home=('<div id="home">'+stat_html
        +'<section><h2>Collections</h2>'+cards(repositories)+'<p><a href="groups.html">Browse all collections →</a></p></section>'
        +'<section><h2>Topics</h2><p class="chips">'+''.join('<a class="chip" href="'+topic_page(t)+'">'+e(t)+' <span class="count">'+str(len(listed(v)))+'</span></a>' for t,v in sorted(by_topic.items(),key=lambda kv:-len(kv[1])))+'</p></section>'
        +('<section><h2>Recently updated in WE BUILD</h2>'+items(recent,show_repo=True)+'</section>' if recent else '')
        +'</div>')
    hero='<section class="hero"><h1>Find WE BUILD decisions, specifications and discussions</h1><p class="lede">One place to search and browse '+format(len(records),',')+' public sources from '+str(len(repositories))+' collections. Every page links back to its original source.</p>'+form+'</section>'
    write('index.html',layout('Home',hero+results+home,home=True,scripts=('search.js',)))

    # Machine-readable outputs (unchanged contract) and search catalogue.
    write('config.json',json.dumps({'api':api,'snapshot':manifest['snapshot']}))
    write('manifest.json',json.dumps(manifest,indent=2))
    write('sources.jsonl','\n'.join(json.dumps(r) for r in records))
    write('relations.json',json.dumps([{'source':r['id'],'target':url,'kind':'references','evidence':{'url':r['url'],'revision':r['revision']},'snapshot':manifest['snapshot']} for r in original_records if r['visibility']=='public' for url in re.findall(r'https://[^\s<>\)\]]+',r.get('text','')) if url not in withdrawals],indent=2))
    write('llms.txt','# WeBuild read-only knowledge gateway\nSnapshot: '+manifest['snapshot']+'\n- [Sources](sources.jsonl)\n- [Manifest](manifest.json)\n- [Topics](topics.md)\n- [Developer guide](developers.html)\nREST: '+api+'/v1/search\nMCP: '+api+'/mcp\n')
    write('topics.md','# Source-backed topic pack\n\n'+''.join('## '+k+'\n'+''.join('- ['+titles[r['id']]+']('+r['url']+') · '+r['decision_status']+' · '+r['revision']+'\n' for r in v) for k,v in by_topic.items()))
    topics=sorted(by_topic);category_keys=[k for k,_,_ in p.CATEGORIES]
    write('catalog.json',json.dumps({'repos':[[k,p.repository_label(k)] for k in repositories],'cats':[[k,label] for k,label,_ in p.CATEGORIES],'topics':topics,'kinds':p.KIND_LABELS,
        'items':[[page_name(r),titles[r['id']],p.subtitle(r),repositories.index(r['repository']),category_keys.index(cats[r['id']]),sum(1<<topics.index(t) for t in r['topics']),p.iso_day(r.get('updated_at')),p.state_label(r) or '',p.kind_label(r)] for r in listed(records) if cats[r['id']]!='replies']},separators=(',',':')))
    for asset in ['style.css','site.js','search.js']:shutil.copyfile(ASSETS/asset,out/asset)


def verify_site(directory,manifest):
    directory=Path(directory)
    records=[json.loads(line) for line in (directory/'sources.jsonl').read_text(encoding='utf-8').splitlines() if line]
    if len({r['id'] for r in records})!=len(records):raise ValueError('Duplicate exported source identity')
    if json.loads((directory/'manifest.json').read_text())['snapshot']!=manifest['snapshot']:raise ValueError('Site snapshot mismatch')
    existing={item.name for item in directory.iterdir()}
    for page in directory.glob('*.html'):
        for href in set(re.findall(r'href="([^"]+)"',page.read_text(encoding='utf-8'))):
            href=html.unescape(href)
            # External links point at original sources; only generated navigation must resolve locally.
            if SCHEME.match(href) or href.startswith('#'):continue
            target=href.split('#')[0]
            if target not in existing and not (directory/target).exists():raise ValueError('Broken generated navigation: '+href)
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
