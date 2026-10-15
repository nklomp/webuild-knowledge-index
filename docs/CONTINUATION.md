# Continue deployment on the local computer

15 October 2026. The user selected their own existing Docker environment and
requested all work committed and pushed for local continuation. The selected
branch is `codex/native-cloud-recovery-validation` in
`nklomp/webuild-knowledge-index`; draft PR:
https://github.com/nklomp/webuild-knowledge-index/pull/1.

Start with `AGENTS.md`, `deploy/LOCAL-HANDOVER.md`, `deploy/README.md` and
`docs/RUNBOOK.md`. All upstream WeBuild/VDX repositories remain read-only.
No actual host, hostname or remote access was supplied. No deployment was
attempted. Render tools now work: the user confirmed My Workspace
(`tea-db8d91rncjis73ffpu40`), which had no services or databases. Nothing was
provisioned and no paid resources were created. Do not resume Render deployment
unless the user selects it again.

The Docker stack supplies persistent PostgreSQL/pgvector, separate non-root
retrieval/ingestion images, and optional Caddy HTTPS. `configure_docker.py`
creates a mode-0600 `.env` with distinct random administrator, reader and writer
credentials and refuses to overwrite an existing file. Initialization and API
startup no longer require a source token. PostgreSQL has no published port;
the raw API binds only to host loopback for an optional existing reverse proxy.
Use `/live` for startup checks and `/health` for publication/freshness checks.

Fresh checks in this continuation: retrieval image build and non-root import;
private env creation/no-overwrite/input validation; Compose credential/network
checks; reader-role API startup and a 1,000-character REST query against an
isolated controlled fixture using real PostgreSQL 16/pgvector and the pinned
MiniLM model. Peak query RSS was 488.2 MiB. See `evidence/docker-deployment.json`
and `evidence/docker-sizing.json`. The preceding full native suite passed
136 tests at `cb023ca`; it was not rerun for these deployment-file changes.
No controlled sizing fixture is a source corpus or public publication.

Six wiki availability gaps are resolved with public evidence. Eleven repositories
remain partial because a dedicated read-only `SOURCE_READ_TOKEN` is missing for
GraphQL Discussions/review resolution. Complete publication must remain gated.
The retrieval service must never receive that token, the admin URL or writer URL.

Remaining local inputs: actual Docker host and HTTPS hostname, source-read token,
and publication runner/network. GitHub Pages remains the current wiki design,
but GitHub-hosted Actions cannot access the private Compose database. Choose a
trusted runner with private database access or explicitly select local wiki
hosting before enabling daily publication. Do not expose PostgreSQL globally.
The operator ingestion command prepares a site/snapshot; it does not deploy
Pages or promote the live snapshot. Preserve site-before-promotion ordering.

Pages was not enabled at the last check. Independent monitoring, alert destination,
backups/restore, hosted rollback/withdrawal and load checks still require the real
host. Monitoring examples are prepared, not activated, and no alerts were sent.
No cloud workspace secrets or local validation databases need to be transferred.
