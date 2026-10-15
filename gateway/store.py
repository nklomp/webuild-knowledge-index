import json, os
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from .model import digest,now,validate,sections,section_context

def same_repository_edition(previous,current):
    if previous.get('edition_tag')!=current.get('edition_tag'):return False
    old_id,new_id=previous.get('repository_id'),current.get('repository_id')
    if old_id is not None and new_id is not None:return old_id==new_id
    return previous['repository']==current['repository']

class Store:
    def __init__(self,dsn,embed,load_calibration=True):
        self.dsn,self.embed=dsn,embed
        from pathlib import Path
        calibration=Path(os.getenv('RETRIEVAL_CALIBRATION','config/retrieval-calibration.json'))
        self.semantic_limit=None;self.semantic_weight=1.0
        if load_calibration and calibration.exists():
            data=json.loads(calibration.read_text())
            if data['embeddings']!=embed.metadata:raise ValueError('Calibration embedding model mismatch')
            from .retrieval import RANKING_VERSION
            if data.get('ranking_version')!=RANKING_VERSION or data.get('index_recipe')!='section-context-v3':raise ValueError('Calibration recipe mismatch; regenerate from original tuning questions')
            self.semantic_limit=float(data['semantic_distance_limit'])
            self.semantic_weight=float(data['semantic_weight'])
            if not 0.25<=self.semantic_weight<=8:raise ValueError('Invalid calibrated fusion weight')
    def connect(self): return psycopg.connect(self.dsn,row_factory=dict_row)
    def manifest(self,snapshot=None):
        with self.connect() as c:
            row=c.execute('SELECT manifest FROM snapshots WHERE id=COALESCE(%s,(SELECT snapshot FROM publication))',(snapshot,)).fetchone()
        if not row: raise LookupError('Snapshot unavailable')
        manifest=dict(row['manifest'])
        with self.connect() as c:
            affected=c.execute("SELECT DISTINCT data->>'repository' AS repository FROM records WHERE snapshot=%s AND EXISTS(SELECT 1 FROM revoked v WHERE v.id=records.id)",(manifest['snapshot'],)).fetchall()
        if affected:
            hidden={r['repository'] for r in affected};manifest['coverage']=dict(manifest.get('coverage',{}))
            manifest['coverage']['coverage']=[x for x in manifest['coverage'].get('coverage',[]) if x.get('repository') not in hidden]
            manifest.pop('records',None);manifest['withdrawals_applied']=True
        return manifest
    def publish(self,records,coverage,promote=True):
        import copy
        records=copy.deepcopy(records)
        from pathlib import Path
        proof_path=Path('config/source-evidence.json')
        proofs=json.loads(proof_path.read_text()) if proof_path.exists() else []
        for r in records:
            for proof in proofs:
                if proof['url']==r['url'] and proof['content_hash']==r['content_hash'] and proof['source_excerpt'] in r['text']:
                    r['source_assertions']=[{'statement':proof['attribution'],'evidence':proof['source_excerpt'],'evidence_url':r['url'],'source_revision':r['revision'],'classification':'source-attributed; not a consortium decision or official correction','provenance':{'method':'pinned-source-descriptive-note-v1','content_hash':r['content_hash']}}]
        validate(records)
        with self.connect() as c:
            prior=c.execute('SELECT data,embedding::text AS vector FROM records WHERE snapshot=(SELECT snapshot FROM publication)').fetchall()
            prior_manifest=c.execute('SELECT manifest FROM snapshots WHERE id=(SELECT snapshot FROM publication)').fetchone()
            old_chunks=c.execute('SELECT source,content,embedding::text AS vector FROM chunks WHERE snapshot=(SELECT snapshot FROM publication)').fetchall() if prior_manifest and prior_manifest['manifest']['embeddings']==self.embed.metadata and prior_manifest['manifest'].get('index_recipe')=='section-context-v3' else []
        base_snapshot=prior_manifest['manifest']['snapshot'] if prior_manifest else None
        old=[row['data'] for row in prior];incoming_ids={r['id'] for r in records};remap={}
        for r in records:
            if r['kind']!='file':continue
            matches=[p for p in old if p['kind']=='file' and same_repository_edition(p,r) and (p['locator']==r['locator'] or (p['revision']==r['revision'] and p['id'] not in incoming_ids))]
            if len(matches)==1 and (matches[0]['id']!=r['id'] or matches[0].get('aliases')):
                p=matches[0];remap[r['id']]=p['id'];r['id']=p['id']
                r['aliases']=sorted(set(p.get('aliases',[])+[p['locator'],r['locator']]))
                r['provenance']['identity_reconciliation']=p['provenance'].get('identity_reconciliation') or {'method':'unique path or immutable blob across reconciled trees','previous_revision':p['revision'],'previous_locator':p['locator']}
        for r in records:
            previous=next((p for p in old if p['id']==r['id']),None)
            if previous and previous['repository']!=r['repository']:
                r['repository_aliases']=sorted(set(previous.get('repository_aliases',[])+[previous['repository'],r['repository']]))
            for parent in r['provenance'].get('referenced_by',[]):parent['id']=remap.get(parent['id'],parent['id'])
        sid=digest(json.dumps([{k:v for k,v in r.items() if k!='retrieved_at'} for r in sorted(records,key=lambda r:r['id'])],sort_keys=True)+json.dumps(coverage,sort_keys=True)+json.dumps(self.embed.metadata)+'section-context-v3')[:24]
        with self.connect() as c:
            if c.execute('SELECT 1 FROM snapshots WHERE id=%s',(sid,)).fetchone():return sid
        vector_cache={row['data']['id']:row for row in prior} if prior_manifest and prior_manifest['manifest']['embeddings']==self.embed.metadata else {}
        vectors=[None]*len(records);missing=[]
        for index,r in enumerate(records):
            cached=vector_cache.get(r['id'])
            if cached and cached['data']['content_hash']==r['content_hash'] and cached['data']['title']==r['title']:vectors[index]=json.loads(cached['vector'])
            else:missing.append(index)
        fresh=self.embed.encode([records[i]['title']+'\n'+records[i]['text'] for i in missing]) if missing else []
        for index,vector in zip(missing,fresh):vectors[index]=vector
        pieces=[p for r in records for p in sections(r)]
        old_contexts={r['id']:section_context(r) for r in old}
        piece_cache={(row['source'],old_contexts.get(row['source']),digest(row['content'])):row['vector'] for row in old_chunks}
        piece_vectors=[None]*len(pieces);missing=[]
        for index,piece in enumerate(pieces):
            cached=piece_cache.get((piece['source'],piece['context'],digest(piece['text'])))
            if cached:piece_vectors[index]=json.loads(cached)
            else:missing.append(index)
        fresh=self.embed.encode([pieces[i]['context']+'\n'+pieces[i]['text'] for i in missing]) if missing else []
        for index,vector in zip(missing,fresh):piece_vectors[index]=vector
        manifest={'snapshot':sid,'index_recipe':'section-context-v3','schema_version':2,'published_at':now(),'coverage':coverage,'embeddings':self.embed.metadata,'records':len(records)}
        with self.connect() as c:
            c.execute("SELECT pg_advisory_xact_lock(hashtext('webuild-publication'))")
            if c.execute('SELECT 1 FROM snapshots WHERE id=%s',(sid,)).fetchone(): return sid
            pointer=c.execute('SELECT snapshot FROM publication').fetchone()
            if (pointer['snapshot'] if pointer else None)!=base_snapshot:raise ValueError('Concurrent publication: rebase capture against the latest snapshot')
            c.execute('INSERT INTO snapshots(id,manifest) VALUES(%s,%s)',(sid,Jsonb(manifest)))
            c.execute('INSERT INTO snapshot_builds(snapshot,base_snapshot) VALUES(%s,%s)',(sid,base_snapshot))
            for r,v in zip(records,vectors):
                c.execute('INSERT INTO records(snapshot,id,revision,data,content,embedding) VALUES(%s,%s,%s,%s,%s,%s::vector)',(sid,r['id'],r['revision'],Jsonb(r),r['title']+'\n'+r['text'],str(v)))
                for target in __import__('re').findall(r'https://[^\s<>\)\]]+',r['text']):
                    c.execute('INSERT INTO relations VALUES(%s,%s,%s,%s,%s,true)',(sid,r['id'],target,'references',Jsonb({'url':r['url'],'revision':r['revision'],'span':target})))
            previous=c.execute('SELECT snapshot FROM publication').fetchone()
            if previous:
                reconciled=coverage.get('reconciled_repositories')
                if reconciled is None:
                    reconciled=sorted({r['repository'] for r in records}|{x.get('repository') for x in coverage.get('coverage',[]) if x.get('repository')})
                removed=c.execute("SELECT id FROM records WHERE snapshot=%s AND data->>'repository'=ANY(%s) AND id NOT IN (SELECT id FROM records WHERE snapshot=%s)",(previous['snapshot'],reconciled,sid)).fetchall()
                for item in removed:
                    c.execute("INSERT INTO revoked VALUES(%s,'removed in complete reconciliation') ON CONFLICT(id) DO NOTHING",(item['id'],))
                    for old_url in c.execute('SELECT DISTINCT data->>\'url\' AS url FROM records WHERE id=%s',(item['id'],)).fetchall():c.execute("INSERT INTO revoked VALUES(%s,'removed source URL') ON CONFLICT(id) DO NOTHING",(old_url['url'],))
            # Revocations are permanent until an explicit verified-public restoration.

            for piece,vector in zip(pieces,piece_vectors):
                c.execute('INSERT INTO chunks(snapshot,source,locator,content,embedding) VALUES(%s,%s,%s,%s,%s::vector)',(sid,piece['source'],piece['locator'],piece['text'],str(vector)))
            if promote:
                c.execute('INSERT INTO publication VALUES(true,%s) ON CONFLICT(singleton) DO UPDATE SET snapshot=EXCLUDED.snapshot',(sid,))
                c.execute('INSERT INTO publication_events(snapshot,event) VALUES(%s,%s)',(sid,'promoted'))
        return sid
    def search(self,q,snapshot=None,status=None,version=None,scope=None,offset=0,limit=20):
        if not q.strip() or len(q)>1000 or not 1<=limit<=100 or not 0<=offset<=10000: raise ValueError('Invalid query or pagination')
        manifest=self.manifest(snapshot); sid=manifest['snapshot']
        if manifest['embeddings']!=self.embed.metadata: raise ValueError('Embedding model mismatch')
        v=str(self.embed.encode([q])[0])
        from .retrieval import RRF_SQL,lexical_query,RANKING_VERSION,semantic_weight_for_query
        weight=semantic_weight_for_query(q,self.semantic_weight)
        parameters={'snapshot':sid,'status':status,'scope':scope,'version':version,'vector':v,'lexical':lexical_query(q),'terms':lexical_query(q).split(' | '),'q':q,'limit':limit,'offset':offset,'semantic_weight':weight}
        with self.connect() as c:
            rows=c.execute(RRF_SQL,parameters).fetchall()
            if not rows:
                total=c.execute("SELECT count(*) AS n FROM records WHERE snapshot=%s AND (%s::text IS NULL OR data->>'decision_status'=%s) AND (%s::text IS NULL OR data->>'repository'=%s) AND (%s::text IS NULL OR EXISTS(SELECT 1 FROM jsonb_array_elements(data->'specifications') s WHERE s->>'cited_version'=%s))",(sid,status,status,scope,scope,version,version)).fetchone()['n']
            else:total=rows[0]['total']
        return {'snapshot':sid,'published_at':manifest['published_at'],'offset':offset,'limit':limit,'total':total,'ranking_version':RANKING_VERSION,'configured_semantic_weight':self.semantic_weight,'semantic_weight':weight,'semantic_distance_limit':self.semantic_limit,'answer_status':'retrieval-only: results do not establish consensus or a normative answer','results':[dict(source=self.permitted(r['data']),score=float(r['score']),vector_distance=r['distance'],lexical_score=r['lexical'],semantic_rank=r['semantic_rank'],lexical_rank=r['lexical_rank'],matched_locator=r['matched_locator'],semantic_match=(r['distance']<=self.semantic_limit) if self.semantic_limit is not None else None) for r in rows]}
    @staticmethod
    def permitted(data):
        import copy
        data=copy.deepcopy(data)
        if data['reuse_permissions']!='full-text':
            data.pop('text',None);data['content_available']=False
            for key in ['unresolved_questions','scope_evidence','reported_concerns']:
                if key in data:
                    values=data[key];data[key]=[value[:500] for value in values[:20]]
                    if len(values)>20 or any(len(v)>500 for v in values):data.setdefault('coverage_limits',[]).append(key+' excerpts bounded; follow original source for complete context')
            if data.get('review_context'):
                data['review_context']=dict(data['review_context']);data['review_context'].pop('diff_hunk',None)
        return data
    def source(self,id,snapshot=None):
        if not id or len(id)>4096:raise ValueError('Invalid source identifier')
        sid=self.manifest(snapshot)['snapshot']
        with self.connect() as c: row=c.execute('SELECT data FROM records WHERE snapshot=%s AND id=%s AND NOT EXISTS(SELECT 1 FROM revoked WHERE revoked.id=records.id)',(sid,id)).fetchone()
        if not row: raise LookupError(id)
        return {'snapshot':sid,'source':self.permitted(row['data'])}
    def related(self,id=None,topic=None,snapshot=None,specs=False,offset=0,limit=100):
        if not 0<=offset<=10000 or not 1<=limit<=100:raise ValueError('Invalid pagination')
        sid=self.manifest(snapshot)['snapshot']
        predicate="""snapshot=%(snapshot)s AND (%(id)s::text IS NULL OR source=%(id)s)
          AND NOT EXISTS(SELECT 1 FROM revoked WHERE revoked.id=source OR revoked.id=target)
          AND (%(topic)s::text IS NULL OR EXISTS(SELECT 1 FROM records r WHERE r.snapshot=relations.snapshot AND r.id=relations.source AND EXISTS(SELECT 1 FROM jsonb_array_elements_text(r.data->'topics') t WHERE lower(t)=lower(%(topic)s))))
          AND (NOT %(specs)s OR (regexp_match(target,'^https?://([^/:]+)'))[1]=ANY(%(hosts)s)
            OR (regexp_match(target,%(github_pattern)s))[1]=ANY(%(official_repositories)s))"""
        from pathlib import Path
        authority=Path('config/official-sources.json')
        official=json.loads(authority.read_text()).get('authoritative_github_repositories',[]) if authority.exists() else []
        parameters={'snapshot':sid,'id':id,'topic':topic,'specs':specs,'hosts':['www.etsi.org','etsi.org','forge.etsi.org','openid.net','www.rfc-editor.org','rfc-editor.org','datatracker.ietf.org','www.ietf.org','ietf.org','eur-lex.europa.eu'],'official_repositories':official,'github_pattern':r'^https://github\.com/([^/?#]+/[^/?#]+)(?:/(?:blob|tree)/|/releases/tag/|/?(?:[?#].*)?$)','limit':limit,'offset':offset}
        with self.connect() as c:
            total=c.execute('SELECT count(*) n FROM relations WHERE '+predicate,parameters).fetchone()['n']
            rows=c.execute('SELECT * FROM relations WHERE '+predicate+' ORDER BY source,target,kind LIMIT %(limit)s OFFSET %(offset)s',parameters).fetchall()
        return {'snapshot':sid,'relations':rows,'offset':offset,'limit':limit,'total':total}
    def history(self,id,offset=0,limit=100,snapshot=None):
        if not 0<=offset<=10000 or not 1<=limit<=100:raise ValueError('Invalid pagination')
        sid=self.manifest(snapshot)['snapshot']
        where="records.id=%s AND snapshots.published_at <= (SELECT published_at FROM snapshots WHERE id=%s) AND NOT EXISTS(SELECT 1 FROM revoked WHERE revoked.id=records.id)"
        with self.connect() as c:
            total=c.execute('SELECT count(*) n FROM records JOIN snapshots ON snapshots.id=records.snapshot WHERE '+where,(id,sid)).fetchone()['n']
            rows=c.execute('SELECT records.snapshot,revision,data FROM records JOIN snapshots ON snapshots.id=records.snapshot WHERE '+where+' ORDER BY snapshots.published_at,records.snapshot LIMIT %s OFFSET %s',(id,sid,limit,offset)).fetchall()
        return {'snapshot':sid,'offset':offset,'limit':limit,'total':total,'history':[dict(snapshot=r['snapshot'],revision=r['revision'],source=self.permitted(r['data'])) for r in rows]}
    def changes(self,before,after=None,offset=0,limit=100):
        if not 0<=offset<=10000 or not 1<=limit<=100:raise ValueError('Invalid pagination')
        sid=self.manifest(after)['snapshot']; self.manifest(before)
        with self.connect() as c:
            rows=c.execute('''SELECT COALESCE(a.id,b.id) id, a.revision before, b.revision after FROM
            (SELECT * FROM records WHERE snapshot=%s) a FULL JOIN
            (SELECT * FROM records WHERE snapshot=%s) b ON a.id=b.id
            WHERE (a.revision IS DISTINCT FROM b.revision OR jsonb_set(a.data - 'retrieved_at','{provenance}',(a.data->'provenance')-'extracted_at') IS DISTINCT FROM jsonb_set(b.data - 'retrieved_at','{provenance}',(b.data->'provenance')-'extracted_at')) AND NOT EXISTS(SELECT 1 FROM revoked WHERE revoked.id=COALESCE(a.id,b.id)) ORDER BY COALESCE(a.id,b.id)''',(before,sid)).fetchall()
        return {'before':before,'snapshot':sid,'offset':offset,'limit':limit,'total':len(rows),'changes':rows[offset:offset+limit]}

    def report_run(self,report):
        with self.connect() as c:c.execute('INSERT INTO ingestion_runs(id,report) VALUES(%s,%s) ON CONFLICT(id) DO NOTHING',(digest(json.dumps(report,sort_keys=True)),Jsonb(report)))
    def latest_run(self):
        with self.connect() as c:r=c.execute('SELECT report FROM ingestion_runs ORDER BY captured_at DESC LIMIT 1').fetchone()
        return r['report'] if r else None
    def quarantine(self,repositories,report,promote=True):
        """Confirmed missing/private repository: suppress all old reads and publish safe remainder."""
        old=self.manifest()
        with self.connect() as c:
            rows=c.execute('SELECT data FROM records WHERE snapshot=%s',(old['snapshot'],)).fetchall()
            removed={r['data']['id'] for r in rows if r['data']['repository'] in repositories}
            for row in rows:
                r=row['data'];parents=r['provenance'].get('referenced_by',[])
                if parents and all(p['id'] in removed for p in parents):removed.add(r['id'])
            for identity in removed:
                c.execute("INSERT INTO revoked VALUES(%s,'confirmed missing/private source') ON CONFLICT(id) DO UPDATE SET reason=EXCLUDED.reason",(identity,))
                for old_url in c.execute('SELECT DISTINCT data->>\'url\' AS url FROM records WHERE id=%s',(identity,)).fetchall():c.execute("INSERT INTO revoked VALUES(%s,'withdrawn source URL') ON CONFLICT(id) DO NOTHING",(old_url['url'],))
        safe=[r['data'] for r in rows if r['data']['id'] not in removed]
        coverage={'coverage':[s for s in old['coverage'].get('coverage',[]) if s.get('repository') not in repositories],'withdrawal':{'repositories':repositories,'time':now()},'latest_capture_failed':True}
        return self.publish(safe,coverage,promote=promote),safe

    def withdrawals(self):
        with self.connect() as c:return [row['id'] for row in c.execute('SELECT id FROM revoked').fetchall()]

    def export_records(self,snapshot=None):
        sid=self.manifest(snapshot)['snapshot']
        with self.connect() as c:return [r['data'] for r in c.execute('SELECT data FROM retrieval.records WHERE snapshot=%s ORDER BY id',(sid,)).fetchall()]

    def promote(self,snapshot,expected_current=None,rollback=False):
        self.manifest(snapshot)
        with self.connect() as c:
            c.execute("SELECT pg_advisory_xact_lock(hashtext('webuild-publication'))")
            pointer=c.execute('SELECT snapshot FROM publication').fetchone();current=pointer['snapshot'] if pointer else None
            if current==snapshot:return snapshot
            build=c.execute('SELECT base_snapshot FROM snapshot_builds WHERE snapshot=%s',(snapshot,)).fetchone()
            expected=expected_current if expected_current is not None else (build['base_snapshot'] if build else None)
            if current!=expected:raise ValueError('Promotion base changed; explicit recovery/rebuild required')
            # A rollback remains subject to current revocations; it cannot restore withdrawn content.
            c.execute('INSERT INTO publication VALUES(true,%s) ON CONFLICT(singleton) DO UPDATE SET snapshot=EXCLUDED.snapshot',(snapshot,))
            c.execute('INSERT INTO publication_events(snapshot,event) VALUES(%s,%s)',(snapshot,'rollback' if rollback else 'promoted'))
        return snapshot

    def restore_public(self,id,evidence_url,reason):
        if not evidence_url.startswith('https://') or not reason.strip():raise ValueError('Verified public restoration requires source evidence and reason')
        with self.connect() as c:
            rows=c.execute('SELECT DISTINCT data->>\'url\' AS url FROM records WHERE id=%s',(id,)).fetchall()
            c.execute('DELETE FROM revoked WHERE id=%s',(id,))
            for row in rows:c.execute('DELETE FROM revoked WHERE id=%s',(row['url'],))
            c.execute('INSERT INTO restoration_events(source,evidence,reason) VALUES(%s,%s,%s)',(id,evidence_url,reason))
