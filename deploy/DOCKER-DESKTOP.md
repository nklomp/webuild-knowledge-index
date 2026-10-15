# Docker Desktop with the existing vdx-edge

Selected locally on 15 October 2026. API hostname:
`https://webuild.nk.sphereon.com`. The user subsequently selected local wiki
hosting and daily publication on this computer, replacing the GitHub Pages
publication path in the earlier LOCAL-HANDOVER.md.

Use the `desktop-linux` Docker context and the separate `webuild-knowledge`
Compose project. The override attaches retrieval and the static wiki to the
existing external `edge` network, under `webuild-knowledge-retrieval` and
`webuild-knowledge-wiki`. PostgreSQL stays on the
project's private default network. Neither service publishes a host port.
The default network uses `10.252.205.0/24`, checked against existing Docker
networks and Windows routes. Docker's automatic pools were exhausted; no existing
network was removed or reconfigured.
Retrieval has an initial 2 GiB memory / 2 CPU limit; this is not load-test evidence.
The operator uses 4 GiB / 4 CPUs and four embedding threads. Initial corpus
embedding is CPU intensive; unchanged vectors are reused on subsequent runs.

From the standalone checkout in PowerShell:

```powershell
# First installation only; refuses to replace an existing .env.
python scripts/configure_docker.py --host webuild.nk.sphereon.com
$composeArgs = @('-p', 'webuild-knowledge', '--env-file', '.env', '-f', 'deploy/compose.yaml', '-f', 'deploy/compose.vdx-edge.yaml')
docker compose @composeArgs config --quiet
docker compose @composeArgs --profile operator run --rm --build initialize
docker compose @composeArgs up -d --build db retrieval wiki
```

Do not start the supplied Caddy `edge` service. The existing vdx-edge owns ports
80/443 and TLS. Install the project-owned `traefik-webuild.yaml` as the new
`webuild-knowledge.yml` in its watched dynamic directory. This is an operational
route installation authorized by the local hosting request; it must not change
existing routes or become a source change in VDX-infra. Current watched path:
`D:\git\VDX-infra\deploy\edge\dynamic`. Traefik watches it without a restart.
On this Windows bind mount, the new file was visible inside Traefik but did not
trigger reload until touched inside that container:

```powershell
docker exec vdx-edge-traefik-1 touch /etc/traefik/dynamic/webuild-knowledge.yml
```

The exact-host route takes priority over the primary wildcard router and uses
the existing `nk.sphereon.com` / `*.nk.sphereon.com` certificate configuration.

Keep `.env` ignored and private, using a Windows file ACL for the local user and
SYSTEM. POSIX mode 0600 alone does not establish a Windows ACL. Never print its
contents or commit it. Persistent `database` and `models` volumes must survive
container replacement; never use `down --volumes` for this installation.

Verification:

```powershell
curl.exe --fail --show-error https://webuild.nk.sphereon.com/live
curl.exe --show-error https://webuild.nk.sphereon.com/health
docker compose @composeArgs ps
```

Before a complete index has been published, `/live` should succeed and `/health`
must not claim readiness. No fixture corpus should be promoted for that purpose.

For complete capture, the operator must put a dedicated public-source read-only
GitHub token in `.env` as `SOURCE_READ_TOKEN`. Do not reuse a developer or gateway
administration token. Then run:

```powershell
./scripts/publish-local.ps1
```

Capture/site artifacts persist in `captures` / `generated-site`. The local
publisher generates into `site/staged` (not the mounted volume root), checks the
generated site, copies a readable immutable release, atomically switches `current`,
verifies the actual HTTPS site and pinned API snapshot, then promotes the matching
API snapshot. Ordinary verification/promotion failures restore the prior site
only if its export contains no currently revoked source IDs or URLs. Failures
during preparation/generation also hide an unsafe prior site, returning 503.
Emergency withdrawals must never restore a known unsafe site. Only `current` is
served; other releases and raw captures are not web-accessible. Static responses
use `Cache-Control: no-store` and the web container mounts generated content
read-only, without database or source credentials.

The daily Codex automation `publish-webuild-knowledge-daily` runs this script at
05:17 Europe/Amsterdam and reports failures. It requires this computer, Docker
Desktop and the Codex desktop app to be running. This is an app automation,
not a Windows Task Scheduler service. It does not enable GitHub Actions/Pages.
The publisher serializes local runs with a lock in the captures volume; the
PowerShell wrapper also refuses to overlap the initial capture container.
Interrupted source capture retains resumable checkpoints. Do not expose
PostgreSQL publicly or bypass incomplete coverage to make the site available.
Independent monitoring, backups/restore, hosted rollback/withdrawal checks and
load measurements remain release gates from the main handover.

## Observed deployment checks, 15 October 2026

- Both images built successfully from branch checkpoint `226fa7f` plus the local
  deployment configuration. Database initialization succeeded with pgvector 0.8.7.
- Database and retrieval containers are healthy; no host ports are published.
- Public DNS resolves the hostname to `nk.sphereon.com`. Real HTTPS with normal
  certificate verification returned 200 and `{"status":"live"}` at `/live`.
- An actual MCP client connected over HTTPS at `/mcp` and discovered all six
  tools with read-only annotations. Traefik access logs confirm selection of
  `webuild-knowledge@file` and the intended retrieval backend.
- Before initial publication, `/health` and search returned 404 `Snapshot
  unavailable`; the wiki returned 503. These gates were preserved during capture.
- The reader role has `default_transaction_read_only=on`. Retrieval has no
  `SOURCE_READ_TOKEN`, writer URL or admin URL in its environment.
- The pinned model downloaded into the persistent volume. After the local
  publisher and preparation-only quarantine changes, the complete suite passed:
  154 tests, six upstream HTTPX deprecation warnings, in 46.21 seconds. This used
  a separate temporary PostgreSQL/pgvector database with password authentication
  and the real cached model. The temporary test containers/network were removed;
  no fixtures were inserted into the deployment database.
- A dedicated source token subsequently passed live GraphQL Discussions and
  PR review-thread probes. Complete capture subsequently passed: 15,740 records,
  fourteen configured repositories and twenty coverage entries, with no failed
  or partial sources. Supported-type limits remain explicit in the manifest.
- Docker Git 2.47.3 reports an absent wiki as `unable to get password from user`.
  This error now triggers the existing independent public HTML/metadata check;
  the Git error alone still does not prove absence. Both positive verification
  and unverified/unavailable regressions pass (11 wiki tests total).
- Fifteen local publication filesystem regressions and a real database
  preparation-only quarantine regression pass inside Linux Docker.
  Windows directory-symlink replacement is not supported by this script; its
  execution target is the Linux ingestion container. PowerShell and Nginx syntax
  checks pass.

## Published local installation

Snapshot `bf7802a665556f04f57d2832` was published at
`2026-10-15T16:25:03.833957+00:00` (18:25 Amsterdam). The matching site was installed
and verified over real HTTPS before the API pointer was promoted. The deployment
contains 15,740 records and 93,068 section vectors; generated navigation and
permission verification passed for 15,744 HTML pages.

`/live`, `/health`, `/manifest.json` and `/v1/manifest` return 200. Site and API
manifest IDs match, and health reports no freshness, source or capture failure.
An actual HTTPS MCP client returned exactly the same search result as REST for
`How can the authority of someone signing for a company be checked?`; results
include vector ranks and passage citations to EUCC, PoA and authorised-signatory
rulebooks. The first measured REST request took 3.454 seconds; this is a single
smoke measurement, not a concurrency/load guarantee. The generated browser search
also returned those results and displayed the matching snapshot.

See [the deployment receipt](../evidence/local-docker-deployment.json) for current
images, counts, checks and schedule. The receipt records the pre-commit deployment
checkpoint; integration history is available in Git. Backups/restore, an independent monitor and alert destination,
hosted rollback/withdrawal drills and concurrent-load sizing remain release
checks; no alert was sent and no paid resources were provisioned.
