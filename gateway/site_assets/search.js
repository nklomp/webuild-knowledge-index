// Home page search: instant title matches from catalog.json, plus live hybrid (keyword + semantic) retrieval from the API.
(()=>{
const $=id=>document.getElementById(id);
const form=$('search'),q=$('q'),health=$('health'),results=$('results'),next=$('next'),instant=$('instant'),moreInstant=$('more-instant'),panel=$('search-results'),home=$('home');
let cfg=null,catalog=null,offset=0,searchSnapshot=null,instantLimit=15,timer=null,controller=null,lastLive='',seen=new Set();
const byPage=new Map(),repoLabels=new Map();
const ready=Promise.all([
  fetch('config.json').then(r=>r.json()).then(c=>{cfg=c;}),
  fetch('catalog.json').then(r=>r.json()).then(c=>{catalog=c;c.items.forEach(it=>byPage.set(it[0],it));c.repos.forEach(([k,l])=>repoLabels.set(k,l));})
]).catch(()=>{});
const weight={decisions:6,conformance:6,specifications:3,documents:3,discussions:1.5,issues:1,pulls:.8,releases:.8,files:.2};
const fold=s=>(s||'').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g,'');
const tokenize=s=>fold(s).split(/[^\p{L}\p{N}]+/u).filter(Boolean);
const escapeRe=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!=null)n.textContent=text;return n;}
function fmtDate(value){if(!value)return '';const d=new Date(value);return isNaN(d)?value:d.toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric'});}
function categoryOf(s){
  if(['comment','discussion-comment','discussion-reply','reviews','review_comments','review-thread'].includes(s.kind))return 'replies';
  if(s.role==='decision')return 'decisions';if(s.role==='implementation-requirement')return 'conformance';
  return {file:'documents',wiki:'documents',pdf:'documents','external-reference':'specifications','official-specification':'specifications',discussion:'discussions',issue:'issues',pull:'pulls',release:'releases','attachment-metadata':'releases'}[s.kind]||'files';
}
function badge(cat,label){return el('span','badge cat-'+cat,label);}
function meta(parts){const m=el('span','item-meta');parts.filter(Boolean).forEach(x=>m.append(typeof x==='string'?el('span','muted',x):x));return m;}
function filters(){return {scope:$('scope').value,type:$('type').value,topic:$('topic').value};}

function instantSearch(){
  instant.replaceChildren();
  const tokens=tokenize(q.value),phrase=fold(q.value).trim();
  $('instant-section').hidden=!tokens.length;
  if(!tokens.length)return;
  if(!catalog){$('instant-count').textContent='(loading…)';return;}
  const {scope,type,topic}=filters(),bit=topic?1<<catalog.topics.indexOf(topic):0;
  const wordRe=tokens.map(t=>new RegExp('(^|[^\\p{L}\\p{N}])'+escapeRe(t),'u'));
  const hits=[];
  for(const it of catalog.items){
    const [repo,cat]=[catalog.repos[it[3]],catalog.cats[it[4]][0]];
    if((scope&&repo[0]!==scope)||(type&&cat!==type)||(bit&&!(it[5]&bit)))continue;
    const title=fold(it[1]),hay=title+' '+fold(it[2])+' '+fold(repo[1]);
    let score=0,ok=true;
    for(let i=0;i<tokens.length;i++){if(!hay.includes(tokens[i])){ok=false;break;}score+=wordRe[i].test(title)?3:title.includes(tokens[i])?2:1;}
    if(!ok)continue;
    if(title===phrase)score+=8;else if(title.includes(phrase))score+=4;
    hits.push([score+(weight[cat]||0),it]);
  }
  hits.sort((a,b)=>b[0]-a[0]||(b[1][6]||'').localeCompare(a[1][6]||''));
  $('instant-count').textContent=hits.length?hits.length.toLocaleString():'';
  if(!hits.length){instant.append(el('li','item muted','No titles match. Full-text matches are shown below.'));}
  for(const [,it] of hits.slice(0,instantLimit)){
    const li=el('li','item'),a=el('a','item-title',it[1]);a.href=it[0];
    const cat=catalog.cats[it[4]][0];
    li.append(a,meta([badge(cat,it[8]),it[7]&&el('span','state state-'+it[7].toLowerCase().replace(/\s+/g,'-'),it[7]),it[2]&&it[2]!==it[1]&&el('span','muted path',it[2]),catalog.repos[it[3]][1],it[6]&&fmtDate(it[6])]));
    instant.append(li);
  }
  moreInstant.hidden=hits.length<=instantLimit;
}

async function pageFor(id){
  try{const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(id));return [...new Uint8Array(bytes)].map(b=>b.toString(16).padStart(2,'0')).join('').slice(0,24)+'.html';}catch(e){return null;}
}
function fallbackTitle(s){
  let t=(s.title||'').replace(/\s*\((review_comments|reviews|comment|reply|discussion comment)\)\s*$/,'');
  if(!t||t===s.id||/^(external|official|github):/.test(t)){const m=/\/(issues|pull|discussions)\/(\d+)/.exec(s.url||'');t=m?({issues:'Issue',pull:'Pull request',discussions:'Discussion'}[m[1]]+' #'+m[2]):(s.url||s.id).replace(/^https:\/\/(www\.)?/,'');}
  return t;
}
function snippet(text,query){
  if(!text)return null;
  const plain=text.replace(/```[\s\S]*?```/g,' ').replace(/<!--.*?-->/g,' ').replace(/\]\([^)]*\)/g,']').replace(/[#>*_`|\[\]]/g,' ').replace(/\s+/g,' ').trim();
  const lower=fold(plain),tokens=tokenize(query).filter(t=>t.length>2);
  let at=-1;for(const t of tokens){at=lower.indexOf(t);if(at>=0)break;}
  const start=Math.max(0,at-110),slice=(start?'… ':'')+plain.slice(start,start+280)+(start+280<plain.length?' …':'');
  const p=el('p','snippet');
  if(!tokens.length){p.textContent=slice;return p;}
  const re=new RegExp('('+tokens.map(escapeRe).join('|')+')','ig');
  slice.split(re).forEach((part,i)=>p.append(i%2?el('mark',null,part):document.createTextNode(part)));
  return p;
}
async function card(item){
  const s=item.source,cat=categoryOf(s),{type,topic}=filters();
  if((type&&cat!==type)||(topic&&!(s.topics||[]).includes(topic)))return null;
  const local=searchSnapshot===cfg.snapshot?await pageFor(s.id):null,known=local&&byPage.get(local);
  const art=el('article','result'),h=el('h3'),a=el('a',null,known?known[1]:fallbackTitle(s));
  a.href=local||s.url;h.append(a);
  const kind=(catalog&&catalog.kinds[s.kind])||s.kind;
  const state=known&&known[7]?el('span','state state-'+known[7].toLowerCase().replace(/\s+/g,'-'),known[7]):null;
  art.append(h,meta([badge(cat,s.role==='decision'?'Decision record':kind),state,s.decision_status&&s.decision_status!=='unknown'?el('span','state state-'+s.decision_status,s.decision_status):null,repoLabels.get(s.repository)||s.repository,s.updated_at&&fmtDate(s.updated_at)]));
  const snip=snippet(s.text,q.value);if(snip)art.append(snip);
  const links=el('p','muted'),src=el('a',null,'Matched passage at the original source ↗');src.href=item.matched_locator||s.url;src.rel='noopener';links.append(src);
  art.append(links);return art;
}
async function live(reset){
  if(reset){offset=0;searchSnapshot=null;seen=new Set();results.replaceChildren();}
  if(controller)controller.abort();
  const mine=controller=new AbortController(),timeout=setTimeout(()=>mine.abort(),10000);
  health.dataset.state='loading';health.textContent='Searching the full text…';
  try{
    await ready;if(!cfg)throw Error('configuration unavailable');
    const p=new URLSearchParams({q:q.value,offset,limit:20});
    if(searchSnapshot)p.set('snapshot',searchSnapshot);else if($('snapshot-mode').value==='page')p.set('snapshot',cfg.snapshot);
    const status=$('status').value,scope=$('scope').value;if(status)p.set('status',status);if(scope)p.set('scope',scope);
    const r=await fetch(cfg.api+'/v1/search?'+p,{signal:mine.signal});
    if(!r.ok)throw Error('the service returned '+r.status);
    const d=await r.json();if(mine!==controller)return;
    searchSnapshot=d.snapshot;
    const stale=Date.now()-Date.parse(d.published_at)>36*3600000;
    let shown=0;
    for(const item of d.results){
      // The same document is often indexed several times (file, PDF, release attachment); show it once.
      const key=fallbackTitle(item.source)+'|'+item.source.repository;if(seen.has(key))continue;seen.add(key);
      const c=await card(item);if(c){results.append(c);shown++;}
    }
    if(!results.children.length&&!d.results.length)results.append(el('p','empty','No full-text matches. Try fewer or different words.'));
    else if(!shown&&reset)results.append(el('p','empty','No full-text matches on this page fit the selected type or topic.'));
    health.dataset.state=stale?'stale':'ok';
    health.textContent=(d.results.length?'Showing the best full-text matches first':'No full-text matches')+' · index updated '+fmtDate(d.published_at)+(stale?' · warning: this index is more than 36 hours old':'');
    next.hidden=offset+20>=d.total;
  }catch(e){
    if(mine!==controller)return;
    health.dataset.state='error';
    health.textContent='Live search unavailable: '+(e.name==='AbortError'?'the request timed out':e.message)+'. Title matches still work, and you can browse collections and original sources.';
    next.hidden=true;
  }finally{clearTimeout(timeout);}
}
function syncUrl(){
  const p=new URLSearchParams();if(q.value)p.set('q',q.value);
  for(const [k,v] of Object.entries(filters()))if(v)p.set(k,v);
  history.replaceState(null,'',p.toString()?'?'+p:location.pathname);
}
function update(runLive){
  const active=!!q.value.trim();panel.hidden=!active;home.hidden=active;instantLimit=15;
  syncUrl();instantSearch();
  clearTimeout(timer);
  if(!active){if(controller)controller.abort();results.replaceChildren();health.textContent='';lastLive='';return;}
  const key=q.value.trim()+'|'+$('scope').value+'|'+$('status').value+'|'+$('snapshot-mode').value;
  if(runLive){lastLive=key;live(true);}
  else if(q.value.trim().length>=3&&key!==lastLive)timer=setTimeout(()=>{lastLive=key;live(true);},900);
}
form.onsubmit=e=>{e.preventDefault();update(true);};
q.addEventListener('input',()=>update(false));
['scope','type','topic','status','snapshot-mode'].forEach(id=>$(id).addEventListener('change',()=>{if(q.value.trim()){lastLive='';update(true);}else syncUrl();}));
moreInstant.onclick=()=>{instantLimit+=30;instantSearch();};
next.onclick=()=>{offset+=20;live(false);};
const initial=new URLSearchParams(location.search);
for(const k of ['scope','type','topic'])if(initial.get(k))$(k).value=initial.get(k);
if(initial.get('q')){q.value=initial.get('q');update(true);}
ready.then(()=>{if(q.value.trim())instantSearch();});
})();
