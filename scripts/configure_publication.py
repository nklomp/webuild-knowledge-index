"""Configure only this gateway's Pages/Actions settings, using a separate admin identity.

Default is read-only inspection. Secrets are passed to gh on stdin, never argv.
"""
import argparse,base64,json,os,secrets,subprocess,sys
from urllib.parse import urlsplit,parse_qs

REPO='nklomp/webuild-knowledge-index'
ENVIRONMENT='knowledge-publication'

def gh(*args,data=None):
    environment=dict(os.environ)
    if environment.get('GATEWAY_ADMIN_TOKEN'):environment['GH_TOKEN']=environment['GATEWAY_ADMIN_TOKEN']
    return subprocess.run(['gh',*args],input=data,text=True,capture_output=True,env=environment)

def api(path,method='GET',body=None):
    args=['api','repos/'+REPO+'/'+path,'--method',method]
    if body is not None:args+=['--input','-']
    return gh(*args,data=json.dumps(body) if body is not None else None)

def inspection():
    pages=api('pages')
    try:code=str(json.loads(pages.stdout).get('status',''))
    except (ValueError,AttributeError):code=''
    status='ready' if pages.returncode==0 else 'not-enabled' if code=='404' else 'permission-denied' if code=='403' else 'unavailable'
    fields={k:bool(os.getenv(k)) for k in ['SOURCE_READ_TOKEN','INGEST_DATABASE_URL','PUBLIC_API_URL']}
    if fields['PUBLIC_API_URL']:
        u=urlsplit(os.environ['PUBLIC_API_URL'])
        if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment:fields['PUBLIC_API_URL']=False
    if fields['INGEST_DATABASE_URL']:
        u=urlsplit(os.environ['INGEST_DATABASE_URL']);q=parse_qs(u.query)
        fields['INGEST_DATABASE_URL']=u.username=='gateway_ingest' and q.get('sslmode')==['verify-full']
    return {'repository':REPO,'pages':status,'inputs_ready':fields,'can_apply':status in ['ready','not-enabled'] and all(fields.values())}

def require(result,operation):
    if result.returncode:raise RuntimeError(operation+' failed; check the gateway administration connection (no credential values are logged)')
    return result

def apply(report):
    if not report['can_apply']:raise ValueError('Prerequisites are missing; run without --apply to inspect names and permissions')
    checkpoint_key=os.getenv('CHECKPOINT_KEY')
    if checkpoint_key and len(base64.b64decode(checkpoint_key,validate=True))!=32:
        raise ValueError('CHECKPOINT_KEY must encode 32 random bytes')
    # Public GraphQL still requires authentication. This probe uses ONLY the
    # dedicated source identity, never the gh administration credential.
    from gateway.http import ReadClient
    probe=ReadClient().graphql('query { repository(owner:"webuild-consortium",name:"wp4-architecture") { isPrivate discussions(first:1) { totalCount } } }',{})
    if probe['repository']['isPrivate']:raise ValueError('Source repository is not public')
    require(api('environments/'+ENVIRONMENT,'PUT',{'deployment_branch_policy':{'protected_branches':False,'custom_branch_policies':True}}),'Environment configuration')
    policies=require(api('environments/'+ENVIRONMENT+'/deployment-branch-policies'),'Branch-policy inspection')
    if not any(p['name']=='main' and p.get('type','branch')=='branch' for p in json.loads(policies.stdout)['branch_policies']):
        require(api('environments/'+ENVIRONMENT+'/deployment-branch-policies','POST',{'name':'main','type':'branch'}),'Branch-policy configuration')
    for name in ['SOURCE_READ_TOKEN','INGEST_DATABASE_URL']:
        require(gh('secret','set',name,'--repo',REPO,'--env',ENVIRONMENT,data=os.environ[name]),'Secret '+name)
    existing=require(gh('secret','list','--repo',REPO,'--env',ENVIRONMENT,'--json','name'),'Checkpoint-secret inspection')
    names={s['name'] for s in json.loads(existing.stdout)}
    if os.getenv('CHECKPOINT_KEY'):
        require(gh('secret','set','CHECKPOINT_KEY','--repo',REPO,'--env',ENVIRONMENT,data=os.environ['CHECKPOINT_KEY']),'Checkpoint key')
    elif 'CHECKPOINT_KEY' not in names:
        require(gh('secret','set','CHECKPOINT_KEY','--repo',REPO,'--env',ENVIRONMENT,data=base64.b64encode(secrets.token_bytes(32)).decode()),'Checkpoint key')
    for args in [[],['--env',ENVIRONMENT]]:
        require(gh('variable','set','PUBLIC_API_URL','--repo',REPO,*args,'--body',os.environ['PUBLIC_API_URL']),'Public API variable')
    require(api('pages','POST' if report['pages']=='not-enabled' else 'PUT',{'build_type':'workflow'}),'Pages workflow configuration')
    return {'configured':True,'repository':REPO,'environment':ENVIRONMENT,'pages':'workflow','source_identity':'separate read-only credential','deployment_triggered':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    try:
        report=inspection();print(json.dumps(apply(report) if args.apply else report,indent=2));return 0
    except Exception as exc:
        print('Configuration stopped: '+type(exc).__name__+'. Inspect prerequisites and connection permissions.',file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
