"""Allowlisted official HTML/JSON/PDF specifications, metadata, exact editions and clauses."""
import json,re
from pathlib import Path
from urllib.parse import urlparse
from .http import ReadClient
from .model import record,digest,now
from .extraction import parse_file

def capture(entry,reader):
    url=entry['url'];reader.validate_url(url)
    if entry.get('mode','link-only')=='link-only':
        text=json.dumps({k:v for k,v in entry.items() if k not in ['reuse_permissions']},sort_keys=True)
        method='configured-link-only-v1';sections=[];media=None
    else:
        response=reader.get(url);media=response.headers.get('content-type','').split(';')[0]
        if len(response.content)>10_000_000:raise ValueError('Official source exceeds extraction limit')
        if media=='application/pdf' or urlparse(url).path.endswith('.pdf'):
            text,extraction=parse_file(response.content,'source.pdf');method=extraction['method'];sections=[]
        elif media in ['text/html','application/xhtml+xml']:
            from bs4 import BeautifulSoup
            soup=BeautifulSoup(response.content,'html.parser')
            for element in soup(['script','style','nav','iframe','form']):element.decompose()
            sections=[{'anchor':str(h['id']),'heading':h.get_text(' ',strip=True)} for h in soup.find_all(['h1','h2','h3','h4'],id=True)]
            text=soup.get_text('\n',strip=True);method='safe-html-text-v1'
        else:text=response.content.decode('utf-8');method='utf8-official-v1';sections=[]
    identity=entry.get('identity',url)
    source=record('official:'+digest(identity+':'+entry.get('version','unknown')),digest(text),url,text,'external-specifications','official-specification',permissions=entry.get('reuse_permissions','metadata-only'))
    source.update(title=entry.get('title',identity),specification_identity=identity,edition_version=entry.get('version','unknown'),document_type=entry.get('document_type','unknown'),source_sections=sections)
    if method=='pypdf-text-v1':source['kind']='pdf'
    source['role']='external-specification';source['provenance']['extraction']={'method':method,'retrieved_at':now(),'media_type':media}
    source['provenance']['catalogue_metadata']={'method':'operator-supplied-official-source-metadata','evidence_url':entry.get('metadata_evidence_url',url),'verified_against_body':False}
    # Configuration declarations are explicitly distinct from extracted or independently verified facts.
    return source

def capture_config(path,reader=None):
    config=json.loads(Path(path).read_text());reader=reader or ReadClient(allowed_hosts=config['allowed_hosts']);rows=[];coverage=[]
    for entry in config['sources']:
        try:
            rows.append(capture(entry,reader));coverage.append({'source':entry['url'],'state':'complete-for-configured-mode','mode':entry.get('mode','link-only'),'captured_at':now()})
        except Exception as exc:coverage.append({'source':entry['url'],'state':'failed','captured_at':None,'error':type(exc).__name__})
    return rows,coverage
