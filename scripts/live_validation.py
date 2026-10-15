"""Real PostgreSQL, encoder, HTTP MCP and optional browser evidence; never a release claim."""
import asyncio,json,os,threading,time,subprocess
from pathlib import Path
import uvicorn,httpx
from mcp.client import Client
from gateway.embeddings import Embeddings
from gateway.store import Store
from gateway.site import generate
from gateway.api import create_app
from gateway.model import validate,sections
from gateway.retrieval import calibrate_weight,RANKING_VERSION

rows=json.loads(Path('evidence/live-records.json').read_text());coverage=json.loads(Path('evidence/live-coverage.json').read_text());validate(rows)
embed=Embeddings();writer=Store(os.environ['INGEST_DATABASE_URL'],embed,load_calibration=False);reader=Store(os.environ['RETRIEVAL_DATABASE_URL'],embed,load_calibration=False)
sid=writer.publish(rows,coverage);writer.report_run(coverage)
generate(writer.export_records(sid),reader.manifest(sid),'site','http://127.0.0.1:58000')
queries=json.loads(Path('config/evaluation-original.json').read_text())['questions']
weight_calibration=calibrate_weight(reader,queries,sid)
reader.semantic_weight=weight_calibration['semantic_weight']
# Additional questions are loaded only after ranking selection is finished.
queries+=json.loads(Path('config/evaluation-holdout.json').read_text())
results=[]
for entry in queries:
    result=reader.search(entry['question'],snapshot=sid,limit=10);locators=[r['source']['locator'] for r in result['results']]
    entry=dict(entry,rank=locators.index(entry['expected_locator'])+1 if entry['expected_locator'] in locators else None,retrieved_locators=locators,snapshot=sid)
    entry['expected_vector_distance']=next((r['vector_distance'] for r in result['results'] if r['source']['locator']==entry['expected_locator']),None)
    entry['top_signals']=[{'locator':r['source']['locator'],'semantic_rank':r['semantic_rank'],'lexical_rank':r['lexical_rank'],'score':r['score']} for r in result['results']]
    if entry['rank'] is None:
        diagnostic=reader.search(entry['question'],snapshot=sid,limit=100)
        entry['expected_source_diagnostic']=next(({'rank_at_100':i+1,'semantic_rank':r['semantic_rank'],'lexical_rank':r['lexical_rank'],'vector_distance':r['vector_distance']} for i,r in enumerate(diagnostic['results']) if r['source']['locator']==entry['expected_locator']),None)
    results.append(entry)
# Only the original tuning set controls this provisional relevance label.
tuning=[r['expected_vector_distance'] for r in results if r['split']=='tuning' and r['expected_vector_distance'] is not None]
if not tuning:raise ValueError('No expected tuning sources retrieved; calibration unavailable')
calibration=weight_calibration|{'embeddings':embed.metadata,'snapshot':sid,'index_recipe':'section-context-v3','semantic_distance_limit':max(tuning),'method':'largest expected-source cosine distance among original source-derived tuning questions','tuning_questions':[r['question'] for r in results if r['split']=='tuning'],'limitations':'Small source-derived set; candidate relevance label, not normative-answer confidence. Regression and held-out questions do not set the cutoff.'}
Path('config/retrieval-calibration.json').write_text(json.dumps(calibration,indent=2));reader.semantic_limit=calibration['semantic_distance_limit']
print(json.dumps({'calibration':calibration},indent=2))
# Exercise the same persisted calibration loader used by a fresh retrieval service.
reader=Store(os.environ['RETRIEVAL_DATABASE_URL'],embed)
server=uvicorn.Server(uvicorn.Config(create_app(reader),host='127.0.0.1',port=58000,log_level='warning'));thread=threading.Thread(target=server.run,daemon=True);thread.start()
for _ in range(100):
    if server.started:break
    time.sleep(.05)
async def check():
    async with Client('http://127.0.0.1:58000/mcp') as client:
        tools=await client.list_tools()
        for entry in results:
            args={'q':entry['question'],'snapshot':sid,'limit':10}
            response=await client.call_tool('search',args)
            rest=httpx.get('http://127.0.0.1:58000/v1/search',params=args,trust_env=False).json()
            assert response.structured_content==rest and rest['snapshot']==sid
        source=rows[0]['id']
        calls=[('get_source',{'id':source,'snapshot':sid},'/v1/sources/'+source),('get_related_sources',{'id':source,'snapshot':sid},'/v1/relations'),('get_related_specs',{'id':source,'snapshot':sid},'/v1/relations'),('get_decision_history',{'id':source,'snapshot':sid},'/v1/decisions/'+source+'/history'),('get_changes',{'before':sid,'after':sid},'/v1/changes')]
        for name,args,path in calls:
            response=await client.call_tool(name,args);params=dict(args)
            if name=='get_related_specs':params['specs']='true'
            if name in ['get_source','get_decision_history']:params.pop('id')
            rest=httpx.get('http://127.0.0.1:58000'+path,params=params,trust_env=False).json()
            assert response.structured_content==rest,(name,response.structured_content,rest)
        return {'initialized':True,'transport':'Streamable HTTP over loopback TCP','tool_count':len(tools.tools),'rest_mcp_equal':True,'all_tools_called':True,'read_only_annotations':all(t.annotations.read_only_hint for t in tools.tools)}
try:
    mcp=asyncio.run(check())
    output={'validated_at':__import__('gateway.model',fromlist=['now']).now(),'snapshot':sid,'model':embed.metadata,'index_recipe':'section-context-v3','ranking':RANKING_VERSION,'semantic_weight':reader.semantic_weight,'questions':results,'mcp':mcp,'splits':{s:{'questions':sum(r['split']==s for r in results),'retrieved_at_10':sum(r['split']==s and r['rank'] is not None for r in results)} for s in sorted({r['split'] for r in results})},'limitations':['Corpus pinned by the fresh coverage manifest; historical corpus was not recovered; not complete discussion coverage','No participant usefulness demonstrated','Not a production deployment'],'counts':{'records':len(rows),'sections':sum(1 for r in rows for _ in sections(r))}}
    Path('evidence/live-evaluation.json').write_text(json.dumps(output,indent=2));print(json.dumps(output,indent=2))
    original_failed=next(r for r in results if r['question']=='How does WeBuild govern architecture and implementation conformance?')
    if os.getenv('BROWSER_CHECK'):subprocess.run(['node','scripts/browser-check.cjs'],check=True,timeout=120)
    assert original_failed['expected_locator']=='blueprint/07-governance-and-adr.md' and original_failed['rank'] is not None,'Original governance regression still fails'
    assert all(r['rank'] is not None for r in results),'Expected-source retrieval regression(s): '+', '.join(r['expected_locator'] for r in results if r['rank'] is None)
finally:server.should_exit=True;thread.join(10)
