# Requirement and source mapping

Scope: `PLAN.md` and the native Cloud continuation request. `VALIDATION.md`
distinguishes fresh results from historical Work reports. Release is blocked.

| Requirement | Implementation / fresh evidence and limits |
|---|---|
| Standalone write destination; upstream read-only | This repository only. Anonymous source reads; destination connector identity kept separate. No upstream mutations. |
| Stable IDs, revisions, provenance and permission boundary | `model.py`, immutable snapshots, rename reconciliation in `store.py`; runtime integration remains blocked by model fixture. |
| Initial four repositories and broader sources | `ingest.py`, 12 configured WeBuild repositories plus two EUDI repositories. Fresh file evidence across all 12; historical live coverage blocked. |
| Real embeddings and hybrid keyword/vector retrieval | Pinned CPU MiniLM, PostgreSQL FTS/pgvector. DB 16.15/extension 0.8.7 confirmed; real weights and fresh search validation blocked. No substitute vectors. |
| Section citations and vector reuse | Line/page locators and context-aware cache; new real-encoder regression awaits weights. |
| Status, unresolved questions and exact versions | Conservative deterministic evidence in `model.py`/`extraction.py`; independent controlled checks pass. Merged is not accepted; closed is not answered. |
| Authoritative external sources | `official.py`, `tags.py`, `catalogue.py`; configured OpenID fetch and link-only IETF/ETSI/EC metadata. Controlled adapters pass; complete live catalogue and clause impacts remain limited. |
| Evidence relationships | Explicit references; stronger inferred relations remain candidates. No inferred compliance or consensus. |
| Generated Pages wiki and search | `site.py`, groups/topics/sources, source-derived reading paths, permission-filtered exports. Fresh real-backend/browser validation and Pages configuration pending. |
| REST and read-only remote HTTP MCP | `api.py` shares `Store`; fixed specification filter/pagination and history snapshot parity. Live HTTP/HTTPS tests blocked by model fixture. |
| No interaction features | Retrieval only, no chatbot/submissions/comments/messaging/collaboration; complete runtime surface checks pending. |
| Credential separation | Ordinary DB reader/writer roles; direct SQL verifies reader restrictions. Full credential-denial tests pending model fixture. |
| Atomic snapshots, deletion and visibility | Transactions, promotion leases, revocations and quarantine. Fresh integration and hosted withdrawal/rollback drills pending. |
| Daily resumable ingestion | 03:17 UTC workflow, capture-scoped page journals; controlled resume/pagination checks pass. Every new day performs full network reconciliation. Incremental cursor polling is not implemented; embedding reuse is incremental. |
| Freshness and partial failures | Failure-gated promotion, per-source coverage and 36-hour health threshold. Independent monitor/recipient unconfigured. |
| Safe untrusted-source processing | Hash-checked blobs, archives not extracted/executed, escaped text and allowlisted hosts. Controlled checks pass. |
| Portable exports | JSONL/Markdown/relationships/llms.txt, permission filtering; fresh full wiki integration pending. No private sources admitted. |
| Independent evaluation | Original six expected locators recovered unchanged from block 34; unchanged additional held-out set. No fresh scores or participant-usefulness claim. |
| Reproducible dependencies | Python 3.12, committed uv.lock; no historical requirements.lock or runtime shim. Source-evidence regeneration checks exact pinned content. |

Before release: actual model encoding, full PostgreSQL-backed suite, HTTP MCP/REST
parity, original and held-out retrieval, wiki/browser checks and source coverage
review. Hosting/Pages/TLS/monitoring/backups/load and hosted privacy recovery remain
configuration and validation work. No production or paid resource authorization.
VDX-infra was neither modified nor needed for this continuation.
