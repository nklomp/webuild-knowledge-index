import hashlib, re
from .extraction import specifications,entities
from datetime import datetime, timezone

def now(): return datetime.now(timezone.utc).isoformat()
def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def classify(text, path, kind):
    status_text=re.sub(r'```[\s\S]*?```','',text[:3000])
    match = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?status(?:\*\*)?\s*[:|]\s*(?:\*\*)?(accepted|proposed|draft|superseded|deprecated|withdrawn)', status_text)
    status = match.group(1).lower() if match and kind in ['file','wiki'] else 'unknown'
    topic_aliases={'AuthZEN':['AuthZEN','Authorization API'],'EBWV':['EBWV','European business wallet vocabulary'],'OID4VP':['OID4VP','OpenID4VP','OpenID for Verifiable Presentations'],'OID4VCI':['OID4VCI','OpenID4VCI'],'trust':['trust'],'rulebook':['rulebook']}
    tags=[{'topic':topic,'matched_alias':alias,'evidence':topic_match.group(0)} for topic,aliases in topic_aliases.items() for alias in aliases if (topic_match:=re.search(re.escape(alias),text,re.I))]
    return {'decision_status':status,'topic_evidence':tags,'status_evidence':match.group(0) if match else None,
            'role':{'issue':'reported-concern','pull':'change-proposal','comment':'discussion-contribution','reviews':'review-feedback','review_comments':'review-feedback','release':'release-note'}.get(kind,'source-metadata') if kind != 'file' else ('decision' if '/adr/' in '/'+path else 'implementation-requirement' if 'conformance' in path else 'source-document'),
            'unresolved_questions':[line for line in text.splitlines() if re.search(r'(?i)open question|unresolved|to be determined|historical.*key|archival case (?:remains open|is not solved)|TODO',line)],
            'specifications':specifications(text),
            'reported_concerns':[line for line in text.splitlines() if kind in ['issue','comment','reviews','review_comments'] and re.search(r'(?i)divergen|discrepanc|schema.*pdf|pdf.*schema',line)],
            'scope_evidence':[line for line in text.splitlines() if re.search(r'(?i)\b(pilot|production|offline|archiv[a-z]+|live)\b',line)],
            'topics':list(dict.fromkeys(t['topic'] for t in tags))}

def record(identity, revision, url, text, repo, kind='file', path='', lifecycle='unknown', updated=None, permissions='metadata-only'):
    return dict(id=identity,revision=revision,url=url,locator=path or url,repository=repo,kind=kind,title=path or identity,
        text=text,content_hash=digest(text),visibility='public',reuse_permissions=permissions,updated_at=updated,retrieved_at=now(),
        lifecycle=lifecycle,aliases=[],actors=[],credential_types=[],ebwv_identifiers=re.findall(r'https?://[^\s<>]*ebwv[^\s<>]*',text),
        entities=entities(text,path),working_group=repo.rsplit('/',1)[-1],
        provenance={'extractor':'deterministic-v2','annotation_model':None,'prompt_version':None},**classify(text,path,kind))

def validate(records):
    for r in records:
        if r['visibility']!='public' or not r['url'].startswith('https://'):raise ValueError('Invalid public source visibility or URL')
        if r['content_hash']!=digest(r['text']):raise ValueError('Invalid content hash')
        if r['decision_status']!='unknown' and (not r['status_evidence'] or r['status_evidence'] not in r['text']):raise ValueError('Status lacks source evidence')
        for s in r['specifications']:
            if s['evidence'] not in r['text']:raise ValueError('Specification lacks source evidence')


def sections(record,words=150):
    for piece in _sections(record,words):
        first=next((line.lstrip('# ').strip() for line in record['text'].splitlines() if line.startswith('#')),record['title'])
        piece['context']=record['title']+'\n'+first
        yield piece

def _sections(record,words=150):
    if record['kind']=='pdf':
        for page,body in enumerate(re.split(r'<!-- page \d+ -->',record['text'])[1:],1):
            tokens=body.split()
            for offset in range(0,len(tokens),words):yield {'source':record['id'],'locator':record['url']+'#page='+str(page),'text':' '.join(tokens[offset:offset+words])}
        return
    if record['kind'] not in ['file','wiki']:
        tokens=record['text'].split()
        for offset in range(0,len(tokens),words):yield {'source':record['id'],'locator':record['url'],'text':' '.join(tokens[offset:offset+words])}
        return
    lines=record['text'].splitlines(); current=[]; start=1;size=0
    for line_no,line in enumerate(lines,1):
        if current and (size+len(line.split())>words or line.startswith('#')):
            yield {'source':record['id'],'locator':record['url']+'#L'+str(start)+'-L'+str(line_no-1),'text':'\n'.join(current)}
            current=[];start=line_no;size=0
        # Split oversized lines (schema entities) without executing or interpreting them.
        if len(line.split())>words:
            if current:yield {'source':record['id'],'locator':record['url']+'#L'+str(start)+'-L'+str(line_no-1),'text':'\n'.join(current)}
            tokens=line.split()
            for offset in range(0,len(tokens),words):yield {'source':record['id'],'locator':record['url']+'#L'+str(line_no),'text':' '.join(tokens[offset:offset+words])}
            current=[];size=0;start=line_no+1
        else:current.append(line);size+=len(line.split())
    if current:yield {'source':record['id'],'locator':record['url']+'#L'+str(start)+'-L'+str(len(lines)),'text':'\n'.join(current)}
