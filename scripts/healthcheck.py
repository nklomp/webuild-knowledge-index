"""Independent public endpoint check; no database or source credentials needed."""
import json,math,os,sys
from urllib.parse import urlsplit
from urllib.request import build_opener,HTTPRedirectHandler

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None

def check(base_url,opener=None,max_age=36*3600):
    url=urlsplit(base_url)
    local=url.hostname in ('localhost','127.0.0.1','::1')
    if not url.hostname or url.username or url.password or url.query or url.fragment or (url.scheme!='https' and not (local and url.scheme=='http')):
        raise ValueError('PUBLIC_API_URL must be an HTTPS base URL without credentials or query parameters')
    opener=opener or build_opener(NoRedirect())
    with opener.open(base_url.rstrip('/')+'/health',timeout=10) as response:
        report=json.loads(response.read(1_000_001))
    age=report.get('age_seconds')
    if not isinstance(report.get('snapshot'),str) or not report['snapshot']:raise ValueError('Health response has no published snapshot')
    if isinstance(age,bool) or not isinstance(age,(int,float)) or not math.isfinite(age) or age<0 or age>max_age:raise ValueError('Publication is stale or its age is invalid')
    if report.get('freshness_failure') is not False:raise ValueError('Health response reports a freshness failure or lacks that field')
    for field in ['failed_sources','stale_sources']:
        if not isinstance(report.get(field),list) or report[field]:raise ValueError('Health response reports '+field+' or lacks that field')
    return {'snapshot':report['snapshot'],'age_seconds':age,'healthy':True}

def main():
    try:print(json.dumps(check(os.environ['PUBLIC_API_URL'])))
    except Exception as exc:
        print('FRESHNESS/AVAILABILITY FAILURE: '+str(exc),file=sys.stderr);return 1
    return 0

if __name__=='__main__':sys.exit(main())
