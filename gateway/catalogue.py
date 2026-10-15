"""Link-only external catalogue. Similarity never establishes normative relationships."""
import re
from urllib.parse import urlparse
from .model import record,digest

def references(records,allowed_hosts):
    found={}
    for source in records:
        for url in re.findall(r'https://[^\s<>\)\]]+',source['text']):
            host=urlparse(url).hostname
            if host not in allowed_hosts or host=='github.com':continue
            key='external:'+digest(url)
            if key not in found:
                version=re.search(r'(?:[vV]|[_/-])(\d+[._]\d+(?:[._]\d+)?)',url)
                etsi=re.search(r'/(?:ts|en|tr)_([0-9]+)v([0-9]{6})p\.pdf',url,re.I)
                draft=re.search(r'/(draft-[a-z0-9-]+)-(\d{2})(?:\.txt|/|$)',url,re.I)
                cited_version=('.'.join(str(int(etsi.group(2)[i:i+2])) for i in [0,2,4]) if etsi else draft.group(2) if draft else version.group(1).replace('_','.') if version else 'unknown')
                r=record(key,digest(url),url,url,'external-specifications','external-reference',permissions='metadata-only')
                r['role']='external-reference';r['specifications']=[{'identity':url,'cited_version':cited_version,'upstream_version':None,'official_url':url,'clause':urlparse(url).fragment or None,'version_origin':'explicit-source-url-encoding','document_type':'draft' if draft else 'technical-reference','evidence':url}]
                r['provenance']['referenced_by']=[];found[key]=r
            found[key]['provenance']['referenced_by'].append({'id':source['id'],'revision':source['revision'],'url':source['url'],'evidence':url})
    return list(found.values())

def impacts(previous,current):
    # Exact source versions only; no inferred compliance/supersession.
    prior={r['id']:r for r in previous}
    return [{'source':r['id'],'before':prior[r['id']]['specifications'],'after':r['specifications'],'relationship_status':'candidate','evidence':{'url':r['url'],'revision':r['revision']}} for r in current if r['id'] in prior and r['specifications']!=prior[r['id']]['specifications']]
