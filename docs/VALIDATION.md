# Native Cloud validation — 15 October 2026

**Not release-ready.** Imported base: `97898bb2a9f9bd3b7c22f972b9c5f483f220a5a6`.
No Work conversation was resumed. All upstream reads were anonymous; only the
standalone `nklomp/webuild-knowledge-index` repository was written. No deployment
or paid resources were provisioned.

## Native continuation in the unrestricted environment

The network block is resolved in this new native session. Real HTTPS probes to
`us.aws.cdn.hf.co`, `api.github.com` and `openid.net` returned 200. The actual pinned
MiniLM weights downloaded and generated a 384-dimensional vector. Python 3.12.14,
PostgreSQL 16.15, pgvector 0.8.7 and the frozen 82-package lock were verified.

**113 tests passed, zero failures/errors/skips** in 22.33 seconds. These include
real embeddings and database operations, HTTP/HTTPS MCP client initialization,
discovery and all six tools with REST parity. Controlled transport fixtures cover
ingestion failure paths independently. See `evidence/native-continuation-tests.xml`
and `evidence/native-continuation-summary.json`. The original 96-test native
baseline also passed before the new ingestion regressions were added.

Daily issue polling now uses an update cursor with a one-hour overlap. Changed
issue subtrees replace prior contributions; retained PR contributions are refreshed
daily to catch resolution changes independently of parent timestamps. Full issue
reconciliation runs at least weekly and can be forced with `--full-reconciliation`.
Baselines bind to configuration, repository identity and reuse policy; interrupted
captures pin the same baseline and failed repository captures never advance it.
A forced full reconciliation remains forced after restart, even if the retry
omits the flag; a dedicated regression covers this failure path.
Deleted issues or changes without a parent timestamp update may remain until the
next full reconciliation. Known removals require the immediate withdrawal path.

Live capture exposed GitHub Link headers that switch from owner/name paths to
numeric repository IDs. The reader now accepts only the numeric alias established
by that repository's fresh public metadata, preserving the connection boundary.
Regression tests reject another repository's numeric ID. Review-thread records
now retain their parent ID so changed PR subtrees remove obsolete threads.

Two real captures of `webuild-consortium/.github` completed, first full and then
with an overlap cursor (`evidence/native-live-polling.json`). This tiny source has
no issues/PRs; changed/deleted/paginated contribution behavior is established by
controlled regressions, not that smoke check. Fresh official capture fetched the
configured OpenID body; three IETF/ETSI/EC entries remain intentionally link-only
and all four remain metadata-only for public reuse
(`evidence/native-official-coverage.json`). Source-evidence fixture regeneration
also passed against the unchanged pinned upstream content.

The full pinned corpus was regenerated and validated natively: **12 repositories,
463 text records / 702 total files / 13,265 sections**. Original expected-source
retrieval is **6/6** in the top 10 (original tuning and regression splits each 3/3);
additional source-derived formulations are **3/3**, ranks **8, 1, 1**. Questions
and expected locators are unchanged. These remain small source-derived regression
sets, not new blind or participant evaluations. The full-corpus MCP client called
all six tools with REST parity. Chromium **154.0.8037.57** passed wiki navigation,
live search, snapshot pinning and visible service-failure checks. Evidence:
`evidence/live-evaluation.json`, `evidence/live-coverage.json`,
`evidence/browser-results.json` and `evidence/native-wiki-search.png`.
Section encoding took 9 minutes 10 seconds. Snapshot: `5ff9210053b733340a718c3e`.
Native calibration keeps semantic weight 8; only snapshot and measured floating
point cutoff differ from the prior CI artifact. No ranking code or expected
sources were changed for this rerun.

The completed native checkpoint replay accounts for **20 coverage entries** with
**zero adapter failures**: 14 repository captures, two tagged-edition sources and
four configured official sources. It captured **13,270 records**. Repository
contributions include **1,173 issues, 968 PRs, 2,693 comments, 2,686 reviews and
2,259 inline review comments**, plus 628 text/PDF files, 344 unsupported/binary
metadata records, 38 releases, 302 attachment metadata records and two wiki pages.
No attachment bodies were fetched. All 12 configured WeBuild repositories and the
two EUDI repositories are accounted for; discovery found no unadmitted repositories.

ARF tagged extraction initially failed on symbolic links and later on an older
UTF-16 JSON specification. The failures are retained in
`evidence/native-live-capture-before-tag-fix.json` and
`evidence/native-tag-recovery.json`. The repaired adapter records symlinks as
metadata without following targets; explicit Unicode byte-order marks preserve
text/schema entities; tagged PDFs keep page citations and their requested reuse
permissions. All **30 ARF editions** now yield **1,428 records**, including **383
PDFs, 21 symbolic-link metadata records and four BOM-decoded text records**.
Tag scope is the configured README/docs paths; all tagged records remain
metadata-only for public reuse. The standards repository returned no tags.

Final coverage remains **incomplete**: 12 repository entries are partial, four
sources complete for supported types and four official entries complete for their
configured mode. Discussion bodies and review-thread resolution require the
missing dedicated read-only GraphQL identity; six repository wikis have unconfirmed
absence/availability. These are actual coverage gates, not hidden successful
captures. `evidence/native-live-coverage.json` records counts, revisions, omissions,
checkpoints, capture times and transport statistics for every source. Raw bodies
and unencrypted journals are excluded from delivery. A real CLI preparation attempt
against this capture was refused and preserved the last published local snapshot
(`evidence/native-publication-gate.json`). It was never published or indexed as a
complete historical corpus. The separate file-only retrieval benchmark above is
not a retrieval-quality measurement of all 13,270 live records.

The final complete suite was run at `fd9dfc102632bb84b5e5d6eec81f14bc1b9c1d3e`.
Native corpus/browser evidence was generated at `25f08eed4a0bc2f5a82b4f169dd5c99ab5301388`;
later changes affect capture and tagged/BOM extraction. Retrieval, embeddings,
database, MCP/REST and wiki code are identical, and the benchmark's existing UTF-8
text decoding is unchanged. CI run 38738115183 independently passed the preceding
108-test polling/restart revision and its complete corpus/browser step. Later
adapter commits have their own CI runs; current status is recorded in the native
continuation summary rather than inferred from an earlier green run.

No dedicated source-read GraphQL identity is configured. Missing discussion and
review-resolution coverage still prevents publication; successful anonymous REST
reads do not resolve that boundary. Hosting, Pages, monitoring and hosted recovery
remain unconfigured; no production deployment or paid resources were used.

## Fresh real-service evidence

Successful CI run: https://github.com/nklomp/webuild-knowledge-index/actions/runs/38687385513

At commit `c8f0b253f619a98fb5333e90022dd8186b684d1a`, **96 tests passed** using
Python 3.12, committed uv.lock, actual pinned MiniLM embeddings, PostgreSQL
16.15/pgvector 0.8.7, and actual HTTP/HTTPS MCP client initialization, discovery
and all six tools with REST parity. No mock vectors or runtime compatibility
shims were used. Controlled transport fixtures exercise adversarial ingestion
paths separately from real-service retrieval tests.

The separate pinned-corpus step also passed:

- All 12 configured WeBuild repositories at immutable commits; **463 supported
  text records / 702 total files / 239 binary or unsupported / 13,265 sections**.
  Exact revisions and omissions: `evidence/fresh-file-pins.json` and
  `evidence/live-coverage.json`. This file-only measurement is not historical
  issues/PRs/comments/reviews/discussions or a complete official-specification crawl.
- Original six source-derived questions: **6/6 expected sources in top 10**.
  Their original three tuning cases and three known regression cases are reported
  separately. Additional source-derived formulations: **3/3**, ranks **8, 1, 1**.
  Questions and expected locators were preserved. These small sets establish no
  participant usefulness or general accuracy claim.
- Real HTTP MCP initialization/discovery/all six tools and REST parity on the
  full corpus. Generated wiki search passed in real Chrome: navigation, live
  backend search, snapshot pinning and visible backend failure. No visitor writes.
- Canonical evidence (JUnit, evaluation, coverage, browser JSON, screenshot,
  calibration): https://github.com/nklomp/webuild-knowledge-index/actions/runs/38687385513/artifacts/11951455302
- Fresh generated wiki (476 files, suitable for Pages; not deployed):
  https://github.com/nklomp/webuild-knowledge-index/actions/runs/38687385513/artifacts/11952125534

`evidence/ci-fresh-retrieval.json` preserves complete evaluation JSON emitted by
that successful run. Calibration is persisted in `config/retrieval-calibration.json`
and tested through the same loader used by a fresh service. Cold CPU section
encoding took approximately 12 minutes 39 seconds in this CI environment.

The final run includes explicit EUDI/IETF specification authority filtering and
regressions preventing repository replacement or distinct tagged editions from
merging source identities. The prior 93-test run also passed the corpus/browser
step (38685653528); final ranks and calibration parameters are unchanged. Only
the fresh snapshot identifier differs. Six test warnings concern httpx certificate
argument deprecation; no tests failed or skipped.

## Previous native environment results and blockers (superseded by continuation)

Python **3.12.14**, `uv lock --check` (82 packages), real local PostgreSQL
**16.15** and pgvector **0.8.7** were verified. Existing development DB container
was restarted; disposable DB uses ordinary reader/writer roles with distinct
random passwords and a TRUNCATE-only test reset role. No new superuser was created.
Direct SQL confirms reader transactions read-only and no base-record write/read
privileges; retrieval uses permission-filtered views.

The first real-model retry downloaded metadata but weights redirect to
**us.aws.cdn.hf.co**, missing from the published four-domain allowlist. Proxy
CONNECT returns **403**. **api.github.com** also returns CONNECT 403 before
credentials, as does **openid.net** for configured official-body fetches. No
source-read secret or native outbound identity is configured. Destination GitHub
connector identity was used only for this new repository, never source capture.

Final native selection: **96 collected, 49 passed, 47 setup errors, zero failures
or skips**. All setup errors require the blocked real model. After the initial live
failure, `HF_HUB_OFFLINE=1` avoided repeated blocked downloads; it did not produce
working embeddings. Native retrieval/MCP/browser integration success is therefore
**not claimed**. Fresh CI success is separate evidence, not a native-network fix.
Exact commands, case names and sanitized boundaries:
`evidence/native-validation-summary.json`. Focused adapter/recovery checks:
**29 passed, 1 deselected**, recorded in `evidence/native-adapter-tests.xml`.

Full native capture attempt (`evidence/native-live-capture.json`) was incomplete:
**18 failed entries and three configured link-only metadata entries**. No repository
history or official specification body was captured by that attempt. Anonymous
immutable archives succeeded; historical GitHub API access did not. GraphQL review
thread resolution/discussions require a dedicated read-only source identity even
after network access is restored. No credentials belong in browser bundles.

## Recovery audit and implementation fixes

- Missing block-119 source-evidence fixtures regenerated from exact pinned public
  source revisions/hashes/excerpts, without executing recorded programs. AuthZEN
  architecture commit: `a78fb62ef8cd037b5038ef1418bb26f1d902995e`. Issue 104 is
  pinned by updated revision `2026-09-30T14:38:13Z` and title/body SHA-256. Its
  public HTML structured payload supplied selected evidence while REST was blocked;
  this is not a historical crawl. Regenerator fails closed on changed pins. The
  ETSI discrepancy remains attributed to its reporter; schema/PDF interpretation
  was not independently validated. See `evidence/source-fixture-regeneration.json`.
- Original six questions/locators recovered as literal AST data from block 34;
  additional question file unchanged. Recovery exceptions/repaired expressions
  audited in `MIGRATION.md`, with independent token-lookup/JSON-Pointer tests.
- Locked MCP SDK snake_case results, typed structured outputs, specification
  filtering/pagination and history snapshot parity repaired. Older snapshots are
  exercised after newer publication through HTTP and HTTPS.
- Section-vector cache now keys encoded title/heading context as well as text.
  `section-context-v3` forces rebuild rather than reuse affected v2 chunks.
- Shared-reference provenance is sanitized after source withdrawal in old and new
  snapshots and public exports, even when another parent remains public. Internal
  ingestion history is retained separately behind DB permissions.
- Immutable file measurement rejects absent/invalid pins and replaces prior repo
  records when pins change. Capture directories are created explicitly. Browser
  launch uses normal Playwright Chrome; bounded timeouts replace recovered flags
  that crashed Chrome.

## Retrieval failure, correction and evaluation limits

Fresh baseline run 38679659358: original **6/6**, additional **2/3**. Equal fusion
buried the unchanged governance source (lexical rank 56, semantic rank 6 for the
additional comparison question). A scalar weight selected on tuning alone improved
additional to 3/3 but regressed original to 5/6 (run 38681641959); this was rejected.
A constrained scalar preserved original 6/6 but left additional 2/3 (run 38683635908).
Failed trials remain recorded; browser passed in the constrained run.

Current `weighted-fts-rrf-v4` balances sparse keyword queries and increases semantic
weight for verbose natural questions. Grid selection uses only original tuning
questions, subject to retaining the three known original regression cases in top
10. Additional questions are loaded only after selection; expected sources never
change. The successful run selects base weight 8, effective weight 5.56 for the
previously failing comparison question; its expected source is rank 8. Semantic
candidate cutoff uses only original tuning distances, not held-out answers.

The original regressions were already known, and the additional failure motivated
the implementation audit. This is an unchanged additional regression measurement,
not a new blind evaluation. Additional untouched sources/questions would provide
stronger generalization evidence; participant questions are not a prerequisite.

## Commands and remaining acceptance work

Actual CI commands (DB credentials are test-only in the committed workflow):

```sh
uv sync --frozen --extra test
uv run --frozen python scripts/bootstrap.py
uv run --frozen pytest -q --junitxml=evidence/ci-tests.xml
uv run --frozen python -m scripts.public_file_evidence --broader --pinned-manifest evidence/fresh-file-pins.json
npm install --prefix work/browser --no-audit --no-fund playwright@1.58.1
uv run --frozen python -m scripts.live_validation
```

The last command used `BROWSER_CHECK=1`, `CHROME_EXECUTABLE=/usr/bin/google-chrome`
and `NODE_PATH` pointing to the scratch Playwright installation. See workflow for
exact environment. Native fixture regeneration used
`uv run --frozen python -m scripts.regenerate_source_evidence`; exact hashes and
commands are in its evidence manifest. Native model retry and capture commands
are in the native summary; neither succeeded in full.

The continuation below supersedes the earlier network and polling boundaries. A
dedicated read-only GraphQL credential remains necessary for discussions and review
thread resolution. No complete live historical or authoritative-specification
coverage claim is made.

Hosting/persistent DB/TLS, Pages environment/URL, independent monitor and recipient,
backup/restore, hosted withdrawal/rollback and measured load remain unconfigured.
Production deployment is not authorized. The stopped Work report of **84 tests,
6/6 plus 2/3** is historical only and is not used as current evidence.

## Additional native continuation commands

With workspace cache variables, the pinned model revision and separate local test
DB URLs set as described in the runbook, the final suite command was:

```sh
uv run --frozen --extra test pytest -q --junitxml=evidence/native-continuation-tests.xml
```

The full capture was resumed across the pagination and historical-tag fixes using
the same source inventory and generation:

```sh
git show d7da87f640cf079817140ebb571a1f8f2c4fec64:config/sources.json > work/sources-before-polling.json
uv run --frozen python -m gateway.cli capture --config work/sources-before-polling.json --artifacts work/native-live-capture
uv run --frozen python -m gateway.cli prepare --artifacts work/native-live-capture --site work/refused-site
```

The last command intentionally returned exit 1 with `Incomplete capture;
publication refused`; the snapshot pointer remained unchanged. The old inventory
configuration disables new polling for that in-progress full generation. A separate
two-capture anonymous smoke run exercised final polling behavior; update/deletion,
numeric pagination, Unicode/PDF and forced-reconciliation restart behavior is also
covered by the complete regression suite. The capture replay fetched fresh public
repository metadata and reused durable completed pages; it did not repeat all
historical network reads or bypass missing GraphQL coverage.
