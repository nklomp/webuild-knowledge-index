import io,json,subprocess,tarfile
from pathlib import Path
from gateway.model import now
config=json.loads(Path('config/sources.json').read_text());entries=[]
for name in config['repositories']:
    repo=config['organization']+'/'+name
    try:
        sha=subprocess.check_output(['git','ls-remote','https://github.com/'+repo+'.git','HEAD'],text=True,timeout=60).split()[0]
        entries.append({'repository':repo,'current_head':sha,'checked_at':now(),'files_ingested':False,'note':'Head discovery only; not a fresh full-corpus capture'})
    except Exception as exc:entries.append({'repository':repo,'state':'failed','error':type(exc).__name__})
Path('evidence/current-head-discovery.json').write_text(json.dumps({'measured_at':now(),'repositories':entries},indent=2))
