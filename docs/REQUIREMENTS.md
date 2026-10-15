# Requirement and source mapping

Authoritative scope: user-provided approved plan dated 7 October 2026. No VDX-infra
access was needed; the structured inventory/detail/overview/export/verification
pattern was implemented independently. Existing repositories were not modified.

| Requirement | Implementation | Evidence / limits |
|---|---|---|
| New write destination; source read-only | standalone root, GET-only `ingest.py`, query-only `discussions.py`, fetch-only `wiki.py` | Anonymous public corpus capture; no source mutation operations or existing local repositories |
| Stable IDs/revisions/permissions/provenance | `model.py`, records JSONB and immutable snapshots | SHA/revision URLs; unique path/blob moves reconciled with evidence-backed aliases |
| Initial four repositories and broader configuration | `config/sources.json`, paginated adapters | Live default-branch file evidence for all 12; historical discussion crawl hit anonymous quota |
| Keyword and real vector search | `embeddings.py`, `store.py`, `sql/schema.sql` | Actual CPU neural embeddings, PostgreSQL 16 and pgvector queries; no mock embeddings |
| Section locators/context | deterministic section extraction, `chunks` table, matched locator | Section line ranges and document-level status remain connected |
| Exact status and lifecycle separation | deterministic status evidence and lifecycle fields | Accepted/proposed/draft/historical/unknown regression checks; merged does not imply accepted |
| Exact external versions | `model.py`, link-only `catalogue.py` | Exact cited version separate from nullable upstream version; official URLs and clause fragments |
| External catalogue and impacts | approved-host metadata, `catalogue.impacts` | Link-only; upstream official release comparison and clause-level catalogue remain limited |
| Evidence relationships | extracted `references`, `relations` and exports | Strong inferred relationships remain candidates via `annotations.py`; no consensus/compliance inference |
| GitHub Pages wiki/navigation/reading paths | `site.py`, daily Pages workflow | Working groups, topics, sources, reading paths, search filters, safe text rendering |
| Same REST/MCP implementation | `api.py` delegates all six tools/routes to `Store` | Actual official MCP HTTP client initialization, tool discovery/calls and parity |
| Read-only visitor access | no mutation routes/tools; DB reader role | Write denial tests, CORS and bounded queries; no chatbot/submissions/comments |
| Credential separation | SQL roles, distinct deployment environments | Actual reader-role write denial; container environment excludes source/ingest credentials |
| Coherent snapshots and recovery | transactional publication and pinned/latest search | Atomic failure, prior revision availability and model compatibility regression checks |
| Deletion/visibility boundary | tombstones across prior snapshots; quarantine and safe re-publication | Controlled tests across search/source/history/relationships; hosted withdrawal drill pending |
| Daily reconciliation | 03:17 UTC Actions, complete crawl every run, checkpoints | Full reconciliation daily also covers weekly requirement; incremental optimization pending |
| Partial failures/freshness | ingestion reports, failure-gated CLI, health >36 hours | Controlled stale capture and health tests; independent healthcheck script supplied |
| Safe parsing | archive streams never extracted/executed; escaped rendering; approved HTTP hosts | Source instructions remain data; PR test jobs receive no publication/source credentials |
| Portable exports | JSONL, relationship JSON, Markdown, `llms.txt` | Permission-filtered text; embedding metadata recorded separately |
| Source-derived evaluation/held-out questions | `scripts/live_validation.py`, controlled fixtures | No participant questions claimed; measured retrieval results and failures retained |
| Independently deployable HTTPS | Docker/Compose/Caddy example, SQL, workflows/runbook | No production host/account/owner selected; loopback HTTP transport validated |

## Release gate

Do not call Stage 1 publicly released merely because local checks pass. Complete
historical issue/PR/comment/review ingestion with a read-only credential and inspect
all coverage entries. Configure/deploy the new repository, database, HTTPS service,
Pages, independent monitor, and recovery/withdrawal drills. Clause-level upstream
impact navigation, ambiguous rename reconciliation, binary extraction, and measured
production load remain explicit limitations rather than invented capabilities.

## Official documentation checked for implementation choices

- Official MCP Python SDK Streamable HTTP client/server and ASGI documentation:
  https://py.sdk.modelcontextprotocol.io/client/transports/
  https://github.com/modelcontextprotocol/python-sdk
- pgvector PostgreSQL extension installation, cosine operator, indexes and grants:
  https://github.com/pgvector/pgvector
- Model repository and immutable revision:
  https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41

Python dependencies resolved from their package releases in this cloud environment;
`requirements.lock` records exact observed versions. PostgreSQL 16.15 and pgvector
0.8.0 were exercised locally. Production Compose uses the matching pgvector 0.8.0
PostgreSQL 16 image. MCP SDK 2.3.0 is pinned because its current public API and
structured-output behavior were tested. The model is CPU-hosted, version-pinned,
and requires no paid account or model API key.
