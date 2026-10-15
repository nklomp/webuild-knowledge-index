"""Deterministic query construction; ranking constants never use held-out labels."""
import re
from pathlib import Path
import json
QUESTION_WORDS={'how','what','where','which','when','why','does','do','can','is','are','the','a','an','and','or','of','to','in','for','with','on','by','we','build','webuild','should','could'}
def lexical_query(q):
    tokens=list(dict.fromkeys(t.lower() for t in re.findall(r'[\w]+',q,flags=re.UNICODE) if t.lower() not in QUESTION_WORDS))
    # OR terms allow partial evidence retrieval; the vector branch preserves full intent.
    return ' | '.join(tokens or re.findall(r'[\w]+',q)) or 'unmatchable_query_token'

RANKING_VERSION='weighted-fts-rrf-v2'
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
 SELECT *,1.0/(60+semantic_rank)+COALESCE(1.0/(60+lexical_rank),0)+exact*0.04 score FROM ranked
)
SELECT data,distance,lexical,matched_locator,score,semantic_rank,lexical_rank,count(*) OVER() total
FROM fused ORDER BY score DESC,id LIMIT %(limit)s OFFSET %(offset)s'''
