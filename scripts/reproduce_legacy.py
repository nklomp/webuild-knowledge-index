"""Freeze the old encoder recipe/ranking, including AND query semantics, for reproduction."""
import json
from pathlib import Path
import numpy as np
from gateway.embeddings import Embeddings
from gateway.model import sections
records=json.loads(Path('evidence/live-records.json').read_text());encoder=Embeddings()
parts=[p for r in records for p in sections(r)];root=Path('artifacts/bench');root.mkdir(parents=True,exist_ok=True)
file=root/'legacy-vectors.npz'
if file.exists():arrays=np.load(file);doc=arrays['documents'];chunks=arrays['chunks']
else:
    doc=np.asarray(encoder.encode([r['title']+'\n'+r['text'] for r in records]));chunks=np.asarray(encoder.encode([p['text'] for p in parts]));np.savez_compressed(file,documents=doc,chunks=chunks)
(root/'legacy-metadata.json').write_text(json.dumps({'model':encoder.metadata,'records':[r['id'] for r in records],'chunk_sources':[p['source'] for p in parts],'recipe':'legacy-uncontextualized-v1','note':'Derived real neural vectors, not portable source truth'},indent=2))
print('Legacy real encoding complete:',len(records),len(parts))
