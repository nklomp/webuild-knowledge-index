"""Independent live default-branch file measurement; NOT historical discussion completion."""
import io,tarfile,subprocess,json,sys,argparse,re
from pathlib import Path
import httpx
from gateway.model import record,now
parser=argparse.ArgumentParser();parser.add_argument('--pinned-manifest');parser.add_argument('--broader',action='store_true');args=parser.parse_args()
pinned=json.loads(Path(args.pinned_manifest).read_text())['coverage'] if args.pinned_manifest else []
cfg=json.loads(Path('config/sources.json').read_text());rows=[];coverage=[]
if args.broader and Path('evidence/live-records.json').exists():
    rows=json.loads(Path('evidence/live-records.json').read_text());coverage=json.loads(Path('evidence/live-coverage.json').read_text())['coverage']
for name in (cfg['repositories'] if args.broader else cfg['initial']):
    repo=cfg['organization']+'/'+name
    try:
        sha=next((c['commit'] for c in pinned if c['repository']==repo),None)
        if args.pinned_manifest and sha is None:raise ValueError('Pinned manifest lacks repository '+repo)
        sha=sha or subprocess.check_output(['git','ls-remote','https://github.com/'+repo+'.git','HEAD'],text=True).split()[0]
        if not re.fullmatch('[0-9a-f]{40}',sha):raise ValueError('An immutable Git commit is required')
        if any(c['repository']==repo and c['state']=='partial' and c.get('commit')==sha for c in coverage):continue
        # A new pin must replace this repository's old measured corpus, not append it.
        rows=[r for r in rows if r['repository']!=repo]
        coverage=[c for c in coverage if c['repository']!=repo]
        response=httpx.get(f'https://codeload.github.com/{repo}/tar.gz/{sha}',timeout=120);response.raise_for_status()
        total=0;count=0;binary=0
        with tarfile.open(fileobj=io.BytesIO(response.content),mode='r:gz') as tar:
            for m in tar.getmembers():
                if not m.isfile():continue
                total+=1;path=m.name.split('/',1)[1]
                if not path.endswith(('.md','.json','.jsonld','.ttl','.yaml','.yml','.txt','.xml','.csv','.adoc','.rst')):binary+=1;continue
                text=tar.extractfile(m).read().decode('utf-8',errors='replace')
                rows.append(record('public-file:'+repo+':'+path,sha,'https://github.com/'+repo+'/blob/'+sha+'/'+path,text,repo,path=path));count+=1
        coverage.append({'repository':repo,'state':'partial','captured_at':now(),'commit':sha,'counts':{'files':count,'all_files':total,'binary_or_unsupported':binary},'types':{'files':'complete supported default-branch text','issues':'NOT captured in this evidence run','pulls':'NOT captured','comments':'NOT captured','reviews':'NOT captured','releases':'NOT captured','discussions':'NOT captured','wiki':'NOT captured','attachments':'NOT captured'},'historical_file_revisions':'NOT captured'})
    except Exception as e:coverage.append({'repository':repo,'state':'failed','error':str(e)})
Path('evidence').mkdir(exist_ok=True)
Path('evidence/live-records.json').write_text(json.dumps(rows,indent=2));Path('evidence/live-coverage.json').write_text(json.dumps({'coverage':coverage,'records':len(rows),'capture_time':now(),'purpose':'integration evidence only; not release corpus'},indent=2))
print(json.dumps({'coverage':coverage,'records':len(rows)},indent=2))
