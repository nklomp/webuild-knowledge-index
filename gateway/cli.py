import argparse,json,os
from pathlib import Path
from .ingest import capture,atomic_json
from .store import Store
from .embeddings import Embeddings
from .site import generate

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['capture','publish','prepare','promote','rollback','generate','run']);p.add_argument('--config',default='config/sources.json');p.add_argument('--artifacts',default='artifacts');p.add_argument('--site',default='site');p.add_argument('--initial',action='store_true');p.add_argument('--snapshot');p.add_argument('--expected-current');a=p.parse_args()
    project=Path.cwd().resolve()
    if not (project/'pyproject.toml').exists() or 'webuild-knowledge-index' not in (project/'pyproject.toml').read_text():raise SystemExit('Run from the standalone project root')
    for destination in [a.artifacts,a.site]:
        if not Path(destination).resolve().is_relative_to(project):raise SystemExit('Write destination must be inside this standalone project')
    root=Path(a.artifacts);root.mkdir(parents=True,exist_ok=True)
    if a.command in ['capture','run']:capture(a.config,a.artifacts,a.initial)
    if a.command=='capture':return
    store=Store(os.environ['INGEST_DATABASE_URL'],Embeddings())
    if a.command in ['promote','rollback']:
        sid=a.snapshot or (root/'snapshot.txt').read_text().strip()
        store.promote(sid,a.expected_current,rollback=a.command=='rollback');print(sid);return
    if a.command=='generate':
        sid=a.snapshot or (root/'snapshot.txt').read_text().strip()
    else:
        records=json.loads((root/'records.json').read_text());coverage=json.loads((root/'coverage.json').read_text());store.report_run(coverage)
        failures=[x for x in coverage['coverage'] if x['state'] in ['failed','partial']]
        if failures:
            withdrawn=[x['repository'] for x in failures if x.get('quarantine')]
            if withdrawn:
                try:
                    sid,safe=store.quarantine(withdrawn,coverage)
                    generate(store.export_records(sid),store.manifest(sid),a.site,os.environ['PUBLIC_API_URL'],store.withdrawals())
                    (root/'snapshot.txt').write_text(sid);atomic_json(root/'publication.json',{'snapshot':sid,'safety_withdrawal':True,'capture_complete':False});return
                except LookupError:pass
            raise SystemExit('Incomplete capture; publication refused. Resume checkpoints with capture/run; see coverage.json.')
        # CLI preparation does not advance the latest pointer. Pages deployment must succeed first.
        sid=store.publish(records,coverage,promote=False)
        (root/'snapshot.txt').write_text(sid)
        atomic_json(root/'publication.json',{'snapshot':sid,'safety_withdrawal':False,'capture_complete':True,'promotion_required':True})
    generate(store.export_records(sid),store.manifest(sid),a.site,os.environ['PUBLIC_API_URL'],store.withdrawals())
    print('Prepared complete snapshot '+sid+'; promote after successful Pages deployment.')
if __name__=='__main__':main()
