"""Fresh reproduction of the delivered v1 ranking using its genuine encoder recipe."""
import json,os
from pathlib import Path
import numpy as np
from gateway.embeddings import Embeddings
from gateway.store import Store
from gateway.model import sections,now
records=json.loads(Path('evidence/live-records.json').read_text());encoder=Embeddings();reader=Store(os.environ['RETRIEVAL_DATABASE_URL'],encoder)
arrays=np.load('artifacts/bench/legacy-vectors.npz');documents=arrays['documents'];chunks=arrays['chunks'];parts=[p for r in records for p in sections(r)];source_ids=np.array([p['source'] for p in parts]);sid=reader.manifest()['snapshot']
original=json.loads(Path('evidence/previous-2026-10-07/live-evaluation.json').read_text())['questions'];results=[]
for entry in original:
    q=entry['question'];v=np.asarray(encoder.encode([q])[0]);v=v/np.linalg.norm(v)
    semantic=1-documents@v/np.linalg.norm(documents,axis=1)
    chunk_distance=1-chunks@v/np.linalg.norm(chunks,axis=1)
    minima={}
    for source,distance in zip(source_ids,chunk_distance):minima[source]=min(minima.get(source,2),float(distance))
    with reader.connect() as c:
        lexical={row['id']:row for row in c.execute("SELECT id,ts_rank_cd(search,websearch_to_tsquery('english',%s)) lexical,CASE WHEN content ILIKE %s THEN 1 ELSE 0 END exact FROM records WHERE snapshot=%s",(q,'%'+q+'%',sid)).fetchall()}
    scored=[]
    for r,distance in zip(records,semantic):
        signal=lexical[r['id']];score=1-min(float(distance),minima.get(r['id'],2))+min(signal['lexical'],1)+signal['exact'];scored.append((score,r['id'],r['locator']))
    ranked=sorted(scored,key=lambda value:(-value[0],value[1]));locators=[r[2] for r in ranked]
    new=reader.search(q,snapshot=sid,limit=10);new_locators=[r['source']['locator'] for r in new['results']]
    results.append({'question':q,'expected_locator':entry['expected_locator'],'legacy_rank':locators.index(entry['expected_locator'])+1,'legacy_top10':locators[:10],'new_rank':new_locators.index(entry['expected_locator'])+1 if entry['expected_locator'] in new_locators else None})
failed=next(r for r in results if r['question']=='How does WeBuild govern architecture and implementation conformance?')
output={'validated_at':now(),'snapshot':sid,'model':encoder.metadata,'legacy_recipe':'uncontextualized sections + raw lexical/cosine sum','new_recipe':'contextualized sections + coverage-aware weighted-FTS RRF','legacy_retrieved_at10':sum(r['legacy_rank']<=10 for r in results),'new_retrieved_at10':sum(r['new_rank'] is not None for r in results),'questions':results,'original_failure_reproduced':failed['legacy_rank']>10,'original_failure_fixed':failed['new_rank'] is not None,'scope':'Pinned public corpus; previously held-out formulations are now regression data.'}
Path('evidence/legacy-comparison.json').write_text(json.dumps(output,indent=2));print(json.dumps(output,indent=2))
assert output['original_failure_reproduced'] and output['original_failure_fixed']
