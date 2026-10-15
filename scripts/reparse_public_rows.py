"""Refresh extraction against already captured immutable text without inventing fresh reads."""
import json
from pathlib import Path
from gateway.model import record,now
path=Path('evidence/live-records.json');rows=json.loads(path.read_text());result=[]
for source in rows:
    revised=record(source['id'],source['revision'],source['url'],source['text'],source['repository'],source['kind'],path=source['locator'],lifecycle=source['lifecycle'],updated=source['updated_at'],permissions=source['reuse_permissions'])
    revised['retrieved_at']=source['retrieved_at'];revised['provenance']['extracted_at']=now();revised['provenance']['input_capture']='immutable public file read, pinned commit'
    result.append(revised)
path.write_text(json.dumps(result,indent=2));print('Re-extracted',len(result),'sources; source capture timestamps unchanged')
