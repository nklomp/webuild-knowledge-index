# Requirement and source mapping

Scope: `PLAN.md` and the native Cloud continuation request. `VALIDATION.md`
distinguishes fresh results from historical Work reports. Release is blocked.

| Requirement | Implementation / fresh evidence and limits |
|---|---|
| Standalone write destination; upstream read-only | This repository only. Anonymous source reads; destination connector identity kept separate. No upstream mutations. |
| Stable IDs, revisions, provenance and permission boundary | `model.py`, immutable snapshots, rename reconciliation in `store.py`; controlled integration passes in CI; native validation now succeeds; see the continuation evidence. |
| Initial four repositories and broader sources | `ingest.py`, 12 configured WeBuild repositories plus two EUDI repositories. Fresh file evidence across all 12; historical live capture is reported separately, including missing GraphQL credentials. |
| Real embeddings and hybrid keyword/vector retrieval | Pinned CPU MiniLM, PostgreSQL FTS/pgvector. DB 16.15/extension 0.8.7 confirmed; actual model and controlled retrieval pass in CI; native real encoding now succeeds. No substitute vectors. |
| Section citations and vector reuse | Line/page locators and context-aware cache; real-encoder cache regression passes in CI; section-context-v3 forces rebuild. |
| Status, unresolved questions and exact versions | Conservative deterministic evidence in `model.py`/`extraction.py`; independent controlled checks pass. Merged is not accepted; closed is not answered. |
| Authoritative external sources | `official.py`, `tags.py`, `catalogue.py`; configured OpenID fetch and link-only IETF/ETSI/EC metadata. Controlled adapters pass; complete live catalogue and clause impacts remain limited. |
| Evidence relationships | Explicit references; stronger inferred relations remain candidates. No inferred compliance or consensus. |
| Generated Pages wiki and search | `site.py`, groups/topics/sources, source-derived reading paths, permission-filtered exports. Controlled generation passes in CI; full-corpus Chrome search passes; Pages configuration pending. |
| REST and read-only remote HTTP MCP | `api.py` shares `Store`; fixed specification filter/pagination and history snapshot parity. Actual HTTP/HTTPS initialization, discovery and all-tool REST parity pass in CI; native HTTP/HTTPS checks now pass. |
| No interaction features | Retrieval only, no chatbot/submissions/comments/messaging/collaboration; controlled runtime surface checks pass in CI. |
| Credential separation | Ordinary DB reader/writer roles; direct SQL verifies reader restrictions. Credential-denial controls pass against real PostgreSQL in CI. |
| Atomic snapshots, deletion and visibility | Transactions, promotion leases, revocations and quarantine. Controlled atomicity/deletion/visibility integration passes in CI; hosted withdrawal/rollback drills pending. |
| Daily resumable ingestion | 03:17 UTC workflow, capture-scoped page journals; controlled resume/pagination checks pass. Daily issue update cursors with a one-hour overlap, daily PR contribution refresh and weekly full reconciliation; capture-generation-pinned baselines and failure-safe cursor advancement. Embedding reuse is incremental. |
| Freshness and partial failures | Failure-gated promotion, per-source coverage and 36-hour health threshold. Independent monitor/recipient unconfigured. |
| Safe untrusted-source processing | Hash-checked blobs, archives not extracted/executed, escaped text and allowlisted hosts. Controlled checks pass. |
| Portable exports | JSONL/Markdown/relationships/llms.txt, permission filtering; fresh full wiki generation and browser search pass in CI. No private sources admitted. |
| Independent evaluation | Original six expected locators recovered unchanged from block 34; unchanged additional held-out set. Fresh original 6/6 and additional 3/3 in top 10, separately reported; no participant-usefulness claim. |
| Reproducible dependencies | Python 3.12, committed uv.lock; no historical requirements.lock or runtime shim. Source-evidence regeneration checks exact pinned content. |

Real model/PostgreSQL/MCP/retrieval/browser checks pass in CI. Before release:
complete live source coverage review and supply a dedicated read-only GraphQL identity. Hosting/Pages/TLS/monitoring/backups/load and hosted privacy recovery remain
configuration and validation work. No production or paid resource authorization.
VDX-infra was neither modified nor needed for this continuation.
