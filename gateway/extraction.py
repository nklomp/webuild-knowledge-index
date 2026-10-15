"""Deterministic source/specification/entity extraction. Never follows document instructions."""
from __future__ import annotations
import io,json,re
from urllib.parse import urlparse
SPEC_PATTERNS=[
 ('ETSI',r'ETSI\s+(?:TS|EN|TR)\s+(?:\d{3}\s+\d{3}(?:-\d+)?)\s+[Vv](\d+\.\d+\.\d+)'),
 ('OpenID',r'(?:OpenID\s+)?(?:OID4VP|OID4VCI|SIOPv2|OpenID4VP|OpenID4VCI)\s+(?:draft[- ]?)?(\d+(?:\.\d+)*(?:[-.]\d+)?)'),
 ('OpenID',r'AuthZEN\s+Authorization\s+API\s+(\d+\.\d+(?:\.\d+)?)'),
 ('OpenID',r'OpenID\s+for\s+Verifiable\s+Presentations\s+(\d+\.\d+(?:\.\d+)?)'),
 ('IETF-draft',r'draft-[a-z0-9-]+-(\d{2})(?=[^a-z0-9-]|$)'),
 ('ARF',r'(?:EUDI\s+)?ARF\s+[vV]?(\d+\.\d+(?:\.\d+)?)'),
 ('IETF',r'RFC\s+(\d{3,5})'),
]
URL_RE=re.compile(r'https?://[^\s<>\)\]"`]+')
def specifications(text):
    result=[];seen=set()
    for family,pattern in SPEC_PATTERNS:
        for match in re.finditer(pattern,text,re.I):
            key=(family,match.group(0))
            if key in seen:continue
            seen.add(key);window=text[max(0,match.start()-250):match.end()+450]
            urls=[u.rstrip('.,;') for u in URL_RE.findall(window)]
            official=next((u for u in urls if urlparse(u).hostname in {'www.etsi.org','etsi.org','forge.etsi.org','openid.net','www.rfc-editor.org','eur-lex.europa.eu','www.ietf.org'}),None)
            clauses=re.findall(r'(?:§\s*|clause\s+)(\d+(?:\.\d+)+)',window,re.I)
            result.append({'identity':re.sub(r'\s+[Vv]?'+re.escape(match.group(1))+r'$','',match.group(0)), 'family':family,
                'cited_version':match.group(1),'upstream_version':None,'clause_identifiers':list(dict.fromkeys(clauses)),
                'official_url':official,'official_url_verified':False,'evidence':match.group(0),'evidence_start':match.start(),'evidence_end':match.end()})
    return result

def entities(text,path):
    """JSON Schema and existing SKOS/OWL/JSON-LD identifiers; no remote contexts."""
    result=[]
    if path.endswith(('.json','.jsonld')):
        try:data=json.loads(text)
        except (ValueError,TypeError):return result
        def walk(value,pointer=''):
            if isinstance(value,dict):
                identity=value.get('@id') or value.get('$id')
                if isinstance(identity,str):
                    labels=value.get('skos:prefLabel',value.get('rdfs:label',value.get('prefLabel',value.get('label',[]))))
                    alt=value.get('skos:altLabel',value.get('altLabel',[]))
                    result.append({'id':identity,'labels':labels,'aliases':alt,'locator':pointer or '/', 'method':'json-identifier-v1'})
                for key,item in value.items():
                    token=key.replace('~','~0').replace('/','~1');child=pointer+'/'+token
                    if key in ('$defs','definitions','properties') and isinstance(item,dict):
                        for entity,definition in item.items():
                            if isinstance(definition,dict):result.append({'id':entity,'description':definition.get('description'),'locator':child+'/'+entity.replace('~','~0').replace('/','~1'),'method':'json-schema-pointer-v1'})
                    walk(item,child)
            elif isinstance(value,list):
                for i,item in enumerate(value):walk(item,pointer+'/'+str(i))
        walk(data)
    elif path.endswith('.ttl'):
        try:
            from rdflib import Graph,URIRef
            from rdflib.namespace import SKOS,RDFS
            graph=Graph().parse(data=text,format='turtle')
            for subject in sorted(set(graph.subjects(SKOS.prefLabel))|set(graph.subjects(RDFS.label)),key=str):
                if isinstance(subject,URIRef):result.append({'id':str(subject),'labels':[str(v) for v in graph.objects(subject,SKOS.prefLabel)]+[str(v) for v in graph.objects(subject,RDFS.label)],'aliases':[str(v) for v in graph.objects(subject,SKOS.altLabel)],'locator':str(subject),'method':'rdf-explicit-label-v1'})
        except Exception:return []
    return result

def parse_file(content,path):
    if len(content)>10_000_000:raise ValueError('Source exceeds extraction size limit')
    if path.lower().endswith('.pdf'):
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(content),strict=True)
        if reader.is_encrypted:raise ValueError('Encrypted PDF is link-only')
        if len(reader.pages)>500:raise ValueError('PDF exceeds page limit')
        pages=[page.extract_text() or '' for page in reader.pages]
        text='\n'.join('<!-- page '+str(i+1)+' -->\n'+body for i,body in enumerate(pages))
        if len(text)>2_000_000:raise ValueError('PDF text exceeds size limit')
        return text,{'method':'pypdf-text-v1','pages':len(pages),'ocr':False}
    if path.lower().endswith(('.md','.txt','.json','.jsonld','.yaml','.yml','.ttl','.xml','.csv','.rst','.adoc','.xsd')):
        return content.decode('utf-8',errors='strict'),{'method':'utf8-text-v2'}
    return None,{'method':'link-only','limitation':'unsupported binary/source type'}
