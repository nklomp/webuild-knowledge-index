import json
from pathlib import Path
from gateway.http import ReadClient,CaptureJournal
from gateway.model import record,digest,now
Path('artifacts').mkdir(exist_ok=True);Path('evidence').mkdir(exist_ok=True)
reader=ReadClient(journal=CaptureJournal('artifacts/selected-evidence.sqlite'));records=[];coverage=[]
for repo,kind,number in [('webuild-consortium/wp4-trust-group','issue',104),('webuild-consortium/wp4-architecture','pull',336)]:
    endpoint='issues' if kind=='issue' else 'pulls';url=f'https://api.github.com/repos/{repo}/{endpoint}/{number}'
    try:
        response=reader.get(url);item=response.json();text=item['title']+'\n'+(item['body'] or '')
        source=record('github:'+item['node_id'],digest(json.dumps(item,sort_keys=True)),item['html_url'],text,repo,kind,lifecycle='merged' if item.get('merged') else item['state'],updated=item['updated_at']);source['title']=item['title']
        source['provenance']['extraction']={'method':'public-rest-selected-evidence-v1','api_url':url,'captured_at':response.extensions.get('captured_at',now())}
        records.append(source);coverage.append({'source':item['html_url'],'state':'selected-item-only','captured_at':source['retrieved_at'],'comments':'not captured in this selected-evidence read','review_threads':'not captured'})
    except Exception as exc:coverage.append({'source':url,'state':'failed','error':type(exc).__name__})
Path('artifacts/selected-records.json').write_text(json.dumps(records,indent=2));Path('evidence/selected-source-coverage.json').write_text(json.dumps({'captured_at':now(),'coverage':coverage,'purpose':'Selected planned regression evidence; not historical corpus completion'},indent=2))
print(json.dumps(coverage,indent=2))
