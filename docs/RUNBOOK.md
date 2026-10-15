# Operator runbook

## Boundaries and credentials

Create a NEW repository named `webuild-knowledge-index` under an explicitly chosen
owner. Never copy project files into consortium source repositories or VDX-infra.
The ingestion adapter uses only public repositories selected in `config/sources.json`.
Organization discovery records new repositories but does not auto-admit them.
Review configuration in this project to admit additions.

- Retrieval container: reader DB URL, model revision, service host, approved website
  origins. No GitHub token, ingestion password, admin password, or model API key.
- Ingestion job: separate derived-data writer DB role and optionally a fine-grained
  GitHub token with repository contents/issues/pull requests/discussions READ ONLY.
  No source write permissions. Use a dedicated account/token, not a developer PAT.
- Database initializer: administrator privileges, used only for schema/roles.
- Pages publication: Actions Pages and OIDC permissions only in this NEW repository.

Configure the new repository's protected `knowledge-publication` environment:
`SOURCE_READ_TOKEN`, `INGEST_DATABASE_URL` secrets and `PUBLIC_API_URL` variable.
Configure GitHub Pages to deploy through Actions. The ingestion database connection
must be reachable from the selected runner and use TLS with certificate verification
when crossing a public network (`sslmode=verify-full` and a CA certificate).
The service domain must resolve to the separately hosted HTTPS reverse proxy.
Set exact `SERVICE_HOST` and `ALLOWED_ORIGINS` (including the scheme).

## First ingestion and acceptance

Run `python -m gateway.cli capture --initial`. Inspect every coverage entry and
its source-type counts before publishing. The adapter fetches the complete default
branch tree, all-state historical issues and PRs, all comments, reviews, review
comments and releases, with all pagination followed. Truncated Git trees fail
closed. Discussions include independently paginated comments and replies when a
read-only GraphQL credential exists. Wiki reads use a temporary bare Git fetch;
attachments are link/metadata records, with binary extraction explicitly excluded.

`capture` writes project-owned per-repository checkpoints and a coverage manifest.
`publish` refuses failed/partial captures and writes records, sections, relationships
and publication pointer in one DB transaction. `generate` emits pages and exports
for the exact resulting snapshot. Daily `run` combines these steps. Full crawling
on EVERY run reconciles removed records and all contribution updates; it is more
expensive than incremental overlap polling but avoids cursor gaps. Weekly runs
therefore already perform full reconciliation. Embedding reuse is keyed by content and model revision; incremental network cache
optimization is a later performance improvement, not a completeness shortcut.

Inspect whether GitHub Discussions are enabled but lack credentials; those gaps
must be resolved before claiming coverage. `not-present-or-unavailable` wiki results
need operator confirmation if wiki coverage matters. Source document status is
extracted conservatively; absent explicit status is unknown, even for merged files.
Confirm any reviewed annotation with an exact source revision and evidence spans.
Do not interpret a closed issue as an answered question.

## Recovery and withdrawal

Keep prior complete DB snapshots. Site search can choose latest live publication or
its pinned page snapshot; responses always expose the selected snapshot and date.
A failed ingestion is recorded in `ingestion_runs`; it leaves the last successful
publication pointer unchanged. `/health` exposes failures and publication age.
Re-run the same capture artifact safely; snapshots are content-addressed and
promotion is idempotent for identical records and coverage.

Successful full reconciliation revokes removed IDs across ALL historical retrieval
snapshots, then produces exports from the new public set. Never retain a source
after confirmed private/withdrawn status. Before production, verify the privacy
incident procedure: immediately revoke affected IDs using the INGEST role, rebuild
and redeploy sanitized Pages/exports, invalidate proxy caches, and rotate affected
credentials if needed. Public cached/downloaded copies cannot be recalled.
A repository metadata 404 or confirmed private response quarantines that repository
and dependent external metadata across previous snapshots, builds a sanitized
safety snapshot and permits emergency Pages publication. Rate-limit/transport
failures retain the prior public snapshot and expose stale capture status. Exercise
this procedure against actual hosted Pages before release.

To recover a publication pointer, use the ingestion role to set it to a verified
prior snapshot; first apply current revocations. Deploy the matching prior site
artifact. Don't delete the previous snapshot before Pages deployment succeeds.
The browser visibly reports service failures and permits static browsing.

## Freshness and monitoring

Run scheduled ingestion at 03:17 UTC. GitHub schedules are not an availability SLA.
Install `scripts/healthcheck.py` in an independent existing monitor, setting
`PUBLIC_API_URL`, and route its nonzero exit to an already authorized operational
channel. No notification is sent by this project and no contact/channel has been
selected. Monitor publication age, failed captures, API availability, TLS expiry,
DB storage, and embedding compatibility. Publication >36 hours old is failure.

## Production checks still requiring infrastructure

- Selected repository owner, hosting account, persistent DB and HTTPS domain.
- Distinct random reader/writer passwords, restricted network and DB TLS.
- Source read-only token and complete historical capture evidence.
- GitHub Pages publication and rollback exercised against the live backend.
- Independent monitor/authorized recipient channel configured and tested.
- Backups and restore drill; concurrent query/load and resource sizing measured.
- Hosted privacy quarantine and sanitized emergency publication drill.
- Binary/PDF extraction permissions and desired coverage explicitly approved.

Do not enable private sources until authorization protects source titles, links,
relations, derived annotations, counts, caches, downloads and exports separately
from the public publication boundary.

## Optional constrained annotation

`gateway.llm_annotations.annotate` supports an explicitly operator-configured HTTPS
chat-completion provider (`ANNOTATION_ENDPOINT`, `ANNOTATION_MODEL`,
`ANNOTATION_API_KEY`). It makes no calls by default and no provider/account has
been chosen. JSON output is limited to topics, descriptive summaries, questions,
and candidate relationships with exact source evidence spans and model/prompt
version. It cannot set source status or replace versions. Store reviewed outputs
as project-owned overrides; invalid spans or revision mismatches fail validation.
The exercised release path uses deterministic extraction and source-derived
reading paths; no generated normative synopsis is presented.
