# Native Cloud validation — 15 October 2026

**Not release-ready.** Base: `97898bb2a9f9bd3b7c22f972b9c5f483f220a5a6`.
No Work session was resumed. Upstream reads were anonymous; no upstream writes,
production deployment or paid resources were used.

## Fresh results

- Python **3.12.14**, committed `uv.lock`, `uv run --frozen --extra test`.
  No runtime or UID compatibility shim. MCP 2.3 result fields use snake_case;
  recovered tests were updated to its actual API.
- Real local PostgreSQL **16.15**, pgvector **0.8.7**. The existing development
  container was restarted. A disposable database uses ordinary reader/writer
  roles with distinct random passwords and a TRUNCATE-only reset role. No new
  superuser was created. Direct SQL confirms reader transaction read-only and
  no INSERT or SELECT privilege on public.records (reads use filtered views).
- Complete test selection: **89 collected, 46 passed, 43 setup errors, zero
  failures or skips**. All setup errors arise from unavailable real model weights;
  database/retrieval/MCP fixtures therefore did not run. These are not passes.
  See `evidence/native-validation-summary.json` for cases and commands.
- Focused independent adapter/recovery run: **24 passed, 1 deselected**, before
  two more independent recovery checks were added; both pass in the full run.
  Controlled pagination/resume, nested review/spec adapters, archive blob
  verification, visibility on resume and encrypted checkpoint checks pass.
  This does not establish complete live ingestion.
- Two missing evidence fixtures regenerated from fresh authoritative public
  reads, exact hashes and excerpts. AuthZEN is pinned to architecture commit
  `a78fb62ef8cd037b5038ef1418bb26f1d902995e`; issue 104 is pinned by update revision
  `2026-09-30T14:38:13Z` and title/body SHA-256. The public GitHub HTML structured
  payload supplied that selected issue evidence while REST was blocked. This is
  not a crawl adapter. `scripts/regenerate_source_evidence.py` fails closed if
  pins change. ETSI discrepancies remain an attributed concern; the cited schema
  revision and PDF interpretation have not been independently validated here.
- Fresh immutable file capture covers **463 supported text files out of 702
  total files across all 12 configured WeBuild repositories**. **239 binary or
  unsupported files** were counted, not extracted in this measurement. Exact
  commits and source-type omissions are in `evidence/fresh-file-pins.json` and
  `evidence/live-coverage.json`. Raw full text is excluded from delivery. These
  fresh revisions are not the missing historical corpus.

## Network and credential boundary

The first real-model retry used the pinned MiniLM model. Metadata downloaded,
but actual weights now use **us.aws.cdn.hf.co**, absent from the published
allowlist. Normal Xet reconstruction and the ordinary HF redirect both encounter
this host; proxy CONNECT returns **403**. `api.github.com` also returns CONNECT
**403**, before authentication. No source-read secret or native outbound identity
is configured. The destination GitHub connector is used only for the standalone
repository, separately from all anonymous upstream reads.

The full suite used `HF_HUB_OFFLINE=1` after the live failure to avoid repeating
that same blocked download. This does not establish offline model availability.
No substitute model, fabricated embeddings or compatibility shim was used.
Exact commands and sanitized error summaries are recorded with the evidence.

## Fixes awaiting real-model integration verification

- REST/MCP specification filtering and pagination; snapshot-pinned decision history.
  Actual HTTP/HTTPS tests now compare all six tools with REST using an older
  snapshot after a newer publication.
- Section-vector cache keys include the encoded title/heading context; unchanged
  section text previously reused stale vectors after context changed. The index
  recipe is now section-context-v3 so rebuilding cannot reuse an affected v2 snapshot.
- Original six questions/expected locators recovered as literal data from block 34.
  The evaluation runner no longer requires an absent historical results artifact.
- Checked regeneration of both missing fixtures. Immutable file measurement
  rejects missing/invalid pins and replaces old records when repository pins
  change. Selected-source capture creates its output directories.

**No fresh retrieval score, real embedding generation, HTTP MCP success, generated
wiki live-search/browser success, or held-out fix is claimed.** The additional
held-out failure remains unresolved pending real-model evaluation. Atomic
snapshot and wiki integration tests are among the blocked tests.

## Historical evidence and remaining gates

The stopped Work report of 84 passes, original retrieval 6/6 and additional
held-out 2/3 is historical only. Original questions are preserved in
`config/evaluation-original.json`; additional held-out formulations remain
unchanged in `config/evaluation-holdout.json`. All are source-derived; no real
participant usefulness is claimed. Participant questions are not a prerequisite.

Publish the two missing network domains, retry real encoding, run the entire
suite with live local TCP, then run `python -m scripts.live_validation` and the
browser check. Keep original and additional held-out scores separate, preserving
failures. A dedicated read-only GitHub source identity is required for GraphQL
review resolution/discussions and if anonymous limits prevent historical capture.
Inspect every coverage entry before claiming completeness. The actual full-capture
attempt is recorded in `evidence/native-live-capture.json`: 18 failed coverage
entries and three configured link-only metadata entries; overall incomplete.
No repository history or official specification body was captured by that attempt.

Hosting, persistent DB/TLS, Pages, independent monitoring, backup/restore, hosted
withdrawal/rollback and measured load remain unconfigured. Production deployment
is not authorized by this continuation.
