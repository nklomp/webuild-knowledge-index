CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS snapshots(id text PRIMARY KEY, manifest jsonb NOT NULL, published_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS publication(singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), snapshot text REFERENCES snapshots);
CREATE TABLE IF NOT EXISTS records(snapshot text REFERENCES snapshots, id text, revision text, data jsonb NOT NULL, content text NOT NULL, embedding vector(384) NOT NULL, search tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED, PRIMARY KEY(snapshot,id));
CREATE INDEX IF NOT EXISTS records_fts ON records USING gin(search);
CREATE INDEX IF NOT EXISTS records_vector ON records USING hnsw(embedding vector_cosine_ops);
CREATE TABLE IF NOT EXISTS relations(snapshot text, source text, target text, kind text, evidence jsonb, confirmed boolean NOT NULL DEFAULT false);
CREATE TABLE IF NOT EXISTS revoked(id text PRIMARY KEY, reason text NOT NULL);
CREATE TABLE IF NOT EXISTS chunks(snapshot text, source text, locator text, content text, embedding vector(384), search tsvector GENERATED ALWAYS AS (to_tsvector('english',content)) STORED);
CREATE INDEX IF NOT EXISTS chunks_fts ON chunks USING gin(search);
CREATE TABLE IF NOT EXISTS ingestion_runs(id text PRIMARY KEY, report jsonb NOT NULL, captured_at timestamptz DEFAULT now());
-- Roles are created with passwords by the operator, never committed here.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO gateway_reader, gateway_ingest;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO gateway_reader;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gateway_ingest;
ALTER ROLE gateway_reader SET default_transaction_read_only=on;
ALTER ROLE gateway_reader SET statement_timeout='5s';
ALTER ROLE gateway_ingest SET statement_timeout='120s';
CREATE INDEX IF NOT EXISTS chunks_snapshot_source ON chunks(snapshot,source);
-- The retrieval role sees a public, revocation-filtered publication boundary.
CREATE SCHEMA IF NOT EXISTS retrieval;
CREATE OR REPLACE VIEW retrieval.records WITH (security_barrier=true) AS
  SELECT r.* FROM public.records r WHERE NOT EXISTS(SELECT 1 FROM public.revoked v WHERE v.id=r.id);
CREATE OR REPLACE VIEW retrieval.chunks WITH (security_barrier=true) AS
  SELECT ch.* FROM public.chunks ch WHERE NOT EXISTS(SELECT 1 FROM public.revoked v WHERE v.id=ch.source);
CREATE OR REPLACE VIEW retrieval.relations WITH (security_barrier=true) AS
  SELECT rel.* FROM public.relations rel WHERE NOT EXISTS(SELECT 1 FROM public.revoked v WHERE v.id=rel.source OR v.id=rel.target);
REVOKE SELECT ON public.records,public.chunks,public.relations FROM gateway_reader;
GRANT USAGE ON SCHEMA retrieval TO gateway_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA retrieval TO gateway_reader;
ALTER ROLE gateway_reader SET search_path=retrieval,public;
-- Versioned publication preparation; complete staged snapshots are queryable by explicit ID.
CREATE TABLE IF NOT EXISTS snapshot_builds(snapshot text PRIMARY KEY REFERENCES snapshots ON DELETE CASCADE,base_snapshot text);
CREATE TABLE IF NOT EXISTS publication_events(sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,snapshot text,event text,at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS restoration_events(sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,source text,evidence text,reason text,at timestamptz DEFAULT now());
GRANT SELECT,INSERT,UPDATE,DELETE ON snapshot_builds,publication_events,restoration_events TO gateway_ingest;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO gateway_ingest;
CREATE INDEX IF NOT EXISTS relations_snapshot_source ON public.relations(snapshot,source);
CREATE INDEX IF NOT EXISTS snapshots_publication_order ON snapshots(published_at,id);
CREATE OR REPLACE VIEW retrieval.snapshots WITH (security_barrier=true) AS
 SELECT s.id,s.published_at,
 CASE WHEN EXISTS(SELECT 1 FROM public.records r JOIN public.revoked v ON v.id=r.id WHERE r.snapshot=s.id)
 THEN (s.manifest - 'records') || jsonb_build_object('withdrawals_applied',true,'coverage',
     (s.manifest->'coverage') || jsonb_build_object('coverage',COALESCE((SELECT jsonb_agg(entry) FROM jsonb_array_elements(COALESCE(s.manifest->'coverage'->'coverage','[]')) entry
       WHERE NOT EXISTS(SELECT 1 FROM public.records r JOIN public.revoked v ON v.id=r.id WHERE r.snapshot=s.id AND r.data->>'repository'=entry->>'repository')),'[]'::jsonb)))
 ELSE s.manifest END manifest FROM public.snapshots s;
REVOKE SELECT ON public.snapshots FROM gateway_reader;
GRANT SELECT ON retrieval.snapshots TO gateway_reader;
