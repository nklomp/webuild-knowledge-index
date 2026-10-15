"""Deterministic query construction; ranking constants never use held-out labels."""
import re
from pathlib import Path
import json
QUESTION_WORDS={'how','what','where','which','when','why','does','do','can','is','are','the','a','an','and','or','of','to','in','for','with','on','by','we','build','webuild','should','could'}
def lexical_query(q):
    tokens=list(dict.fromkeys(t.lower() for t in re.findall(r'[\w]+',q,flags=re.UNICODE) if t.lower() not in QUESTION_WORDS))
    # OR terms allow partial evidence retrieval; the vector branch preserves full intent.
    return ' | '.join(tokens or re.findall(r'[\w]+',q)) or 'unmatchable_query_token'

RANKING_VERSION='weighted-fts-rrf-v3'

def calibrate_weight(store,questions,snapshot,candidates=(0.5,0.75,1.0,1.25,1.5,1.75,2.0,4.0,8.0)):
    """Choose fusion balance from original tuning data only, never held-out labels."""
    tuning=[q for q in questions if q['split']=='tuning']
    regressions=[q for q in questions if q['split']=='previous-held-out-now-regression']
    if not tuning:raise ValueError('Ranking calibration requires original tuning questions')
    measurements=[];previous=store.semantic_weight
    try:
        for weight in candidates:
            if not 0.25<=weight<=8:raise ValueError('Invalid fusion weight')
            store.semantic_weight=weight;ranks=[];regression_ranks=[]
            for entry in tuning+regressions:
                locators=[r['source']['locator'] for r in store.search(entry['question'],snapshot=snapshot,limit=10)['results']]
                rank=locators.index(entry['expected_locator'])+1 if entry['expected_locator'] in locators else None
                (ranks if entry['split']=='tuning' else regression_ranks).append(rank)
            measurements.append({'semantic_weight':weight,'ranks':ranks,'regression_ranks':regression_ranks,'regressions_preserved':all(r is not None for r in regression_ranks),'retrieved_at_10':sum(r is not None for r in ranks),'mean_reciprocal_rank_at_10':sum(1/r if r else 0 for r in ranks)/len(ranks)})
    finally:store.semantic_weight=previous
    feasible=[m for m in measurements if m['regressions_preserved']]
    if not feasible:raise ValueError('No fusion weight preserves the known original regressions')
    best=max(feasible,key=lambda m:(m['retrieved_at_10'],m['mean_reciprocal_rank_at_10'],-abs(m['semantic_weight']-1)))
    return {'ranking_version':RANKING_VERSION,'semantic_weight':best['semantic_weight'],'weight_selection':'preserve known original regressions; maximize tuning recall@10, then MRR@10; ties favor original equal fusion','weight_candidates':measurements,'tuning_questions':[q['question'] for q in tuning],'regression_questions':[q['question'] for q in regressions]}
RRF_SQL='''WITH filtered AS MATERIALIZED (
 SELECT id,data,content,embedding,search FROM records
 WHERE snapshot=%(snapshot)s
 AND (%(status)s::text IS NULL OR data->>'decision_status'=%(status)s)
 AND (%(scope)s::text IS NULL OR data->>'repository'=%(scope)s)
 AND (%(version)s::text IS NULL OR EXISTS(SELECT 1 FROM jsonb_array_elements(data->'specifications') s WHERE s->>'cited_version'=%(version)s))
), signals AS MATERIALIZED (
 SELECT r.*, LEAST(r.embedding <=> %(vector)s::vector,COALESCE(ch.distance,2)) distance,
 COALESCE(ch.locator,r.data->>'url') matched_locator,
 (SELECT count(*) FROM unnest(%(terms)s::text[]) term WHERE r.search @@ plainto_tsquery('english',term)) lexical_coverage,
 ts_rank_cd(setweight(to_tsvector('english',coalesce(r.data->>'title','')),'A') || setweight(to_tsvector('english',coalesce(r.data->>'locator','')),'B') || setweight(r.search,'D'),to_tsquery('english',%(lexical)s),32) lexical,
 CASE WHEN position(lower(%(q)s) in lower(r.content))>0 THEN 1 ELSE 0 END exact
 FROM filtered r LEFT JOIN LATERAL (
   SELECT embedding <=> %(vector)s::vector distance,locator FROM chunks
   WHERE snapshot=%(snapshot)s AND source=r.id ORDER BY embedding <=> %(vector)s::vector,locator LIMIT 1
 ) ch ON true
), ranked AS (
 SELECT *,row_number() OVER(ORDER BY distance,id) semantic_rank,
 CASE WHEN lexical>0 THEN row_number() OVER(ORDER BY lexical_coverage DESC,lexical DESC,id) END lexical_rank FROM signals
), fused AS (
 SELECT *,%(semantic_weight)s::double precision/(60+semantic_rank)+COALESCE(1.0/(60+lexical_rank),0)+exact*0.04 score FROM ranked
)
SELECT data,distance,lexical,matched_locator,score,semantic_rank,lexical_rank,count(*) OVER() total
FROM fused ORDER BY score DESC,id LIMIT %(limit)s OFFSET %(offset)s'''
