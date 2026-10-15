# Deployment configuration

These files prepare deployment; they have not provisioned a host, database or
monitor. On 15 October the user chose their own Docker environment and requested
a committed, pushed handover for continuation on their local computer. Follow
[LOCAL-HANDOVER.md](LOCAL-HANDOVER.md). Render was inspected in the confirmed
workspace and had no services or databases; no Render resources were created.

## Render

Use one Docker web service for REST and MCP, and persistent Render Postgres with
the `vector` extension. Both must be in the same region. Build the repository's
Dockerfile (its final target is `retrieval`); the service listens on port 8000.
Use `/live` as the platform health path: it can succeed before the first index
publication. `/health` is the separate publication freshness/coverage check.

Initialize the schema using a separate one-off process built with Docker target
`ingestion`, running `python scripts/bootstrap.py`. Supply only that process with
`ADMIN_DATABASE_URL`, `READER_DATABASE_PASSWORD`, and `INGEST_DATABASE_PASSWORD`.
The passwords must be distinct. Verify `vector` is supported before initialization.
The initializer creates `gateway_reader` and `gateway_ingest`; never use the
provider's administrator connection string as the web service's reader URL.

Set the web service's `RETRIEVAL_DATABASE_URL` to the reader role connection,
`EMBEDDING_REVISION=1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, and
`ALLOWED_ORIGINS=https://nklomp.github.io`. The Render-provided
`RENDER_EXTERNAL_HOSTNAME` configures MCP's host validation automatically; an
explicit `SERVICE_HOST` takes precedence if a custom domain is used. Persist
`/models` if the selected plan supports disks, or allow the pinned model download
at each cold start. Size the service for PyTorch plus the loaded model and measure
startup time and concurrency before release. Render terminates HTTPS.

Daily ingestion runs in the existing gateway repository's Actions workflow, not
the retrieval container. Use the database's external writer-role URL with
`sslmode=verify-full` and the trusted CA. Restrict database network access to the
chosen runner where supported; never expose an unrestricted administrator URL.

## Source reads and GitHub Pages

Public REST/Git reads do not require a token. GitHub's GraphQL API requires
authentication even for public repositories; this supplies Discussions and review
thread resolution. Visitors remain anonymous. Bind a dedicated read-only source
credential as `SOURCE_READ_TOKEN`; do not reuse the gateway administration identity.

With the real HTTPS API URL, externally reachable TLS writer URL, and dedicated
source token bound in the operator process environment, inspect:

```sh
uv run --frozen python scripts/configure_publication.py
```

When prerequisites pass, `--apply` configures only
`nklomp/webuild-knowledge-index`: the `knowledge-publication` environment, its
source/writer secrets, a stable random checkpoint encryption key, the public API
variable, and Actions-based Pages. Existing checkpoint keys are preserved. An
optional separate `GATEWAY_ADMIN_TOKEN` can provide gateway settings access.
Secret values travel on stdin and are never placed in command arguments. Do not
paste credentials into chat or commit an environment file.

The helper does not dispatch publication. Complete capture must pass before
Pages generation and promotion. The daily workflow deploys Pages before promoting
the matching database snapshot. Merge reviewed code to `main` before using the
protected publication environment. Exercise hosted rollback and withdrawal before
calling the service released.

## Monitoring

`.github/workflows/monitor.yml` activates when the repository `PUBLIC_API_URL`
variable is set. It checks every 30 minutes and uses normal Actions failure
notifications. This is supplemental: an independent monitor is still required
because ingestion and this check share GitHub's scheduler.

Install `scripts/healthcheck.py` in an existing independent monitoring system, or
copy it to `/opt/webuild-monitor/healthcheck.py` on an independent Linux host.
Set `PUBLIC_API_URL=https://<actual-api-host>` in `/etc/webuild-monitor.env` and
install the supplied `webuild-health.service` and `.timer` into
`/etc/systemd/system`. Enable the timer with `systemctl enable --now
webuild-health.timer`. Connect service failures to an existing authorized alert
destination and test an actual failure. No alert destination has been selected or
activated by committing these files. The check needs no source or DB credentials.

The monitor fails for unavailable endpoints, redirects, invalid health responses,
missing snapshots, publications older than 36 hours, stale sources and capture
failures. It deliberately checks `/health`, not `/live`.

## Selected target: existing Docker host

`compose.yaml` supplies PostgreSQL/pgvector, the retrieval image and Caddy HTTPS.
Generate distinct credentials in an ignored, mode-0600 `.env` with
`python scripts/configure_docker.py --host <your-api-hostname>`. This includes
`ADMIN_DATABASE_URL` for the isolated initializer. Use internal `db:5432`
connections here; the database has no published port. Initialize with:

```sh
docker compose --env-file .env -f deploy/compose.yaml --profile operator run --rm initialize
docker compose --env-file .env -f deploy/compose.yaml up -d --build db retrieval edge
```

Point the selected hostname at that existing host before starting Caddy. This
publishes ports 80/443, configurable with `HTTP_PORT`/`HTTPS_PORT`. For an existing
host reverse proxy, start only `db retrieval`; the API is available on
`127.0.0.1:8000` (override `API_PORT` if occupied), and the existing proxy must
terminate HTTPS and forward to it. A proxy in another container requires a shared
Docker network or explicit host routing; its loopback is a different namespace.
The database remains internal and the API's loopback port is not a public endpoint.
This
alternative does not make the database reachable from GitHub Actions; use a
self-hosted runner on the private network or configure an authenticated TLS
network path separately. The operator ingestion profile prepares a snapshot but
does not replace the Pages deployment/promotion order.
