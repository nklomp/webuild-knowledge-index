# Continue on the local computer

The selected hosting target is the user's existing Docker environment. No host,
DNS name or remote access was supplied to the cloud session, and no deployment
was attempted. No Render resources or paid services were created.

## Checkout and startup

Continue with PR #1's branch, `codex/native-cloud-recovery-validation`, in
`nklomp/webuild-knowledge-index`. Read `AGENTS.md` and `deploy/README.md`. Existing
WeBuild/VDX repositories remain strictly read-only. Keep the gateway in its own
checkout and Docker Compose project.

1. Fetch and check out the branch on the local computer.
2. Choose an actual API hostname, route it to the Docker host, and decide whether
   to use the supplied Caddy or the host's existing HTTPS proxy. PostgreSQL needs
   persistent disk space. Allow memory for both PostgreSQL and the API: a fresh
   real-model API query peaked at 488.2 MiB before concurrency testing. A 2 GB API
   allocation is a reasonable starting point; it is not a measured load guarantee.
3. From the repository root, generate local settings (replace the hostname):

   ```sh
   python scripts/configure_docker.py --host knowledge-api.your-domain.example
   docker compose --env-file .env -f deploy/compose.yaml config --quiet
   docker compose --env-file .env -f deploy/compose.yaml --profile operator run --rm --build initialize
   docker compose --env-file .env -f deploy/compose.yaml up -d --build db retrieval edge
   ```

   The helper creates `.env` exclusively, with three distinct random passwords and
   internal database URLs, and refuses to overwrite it. Do not print or commit
   `.env`. Protect/back up the passwords along with the database. Re-running the
   helper is not a password-rotation procedure. Do not use `down --volumes` on
   an installed stack; it deletes persisted database and model volumes.
4. If the host already provides HTTPS, omit `edge` in the startup command and
   configure that proxy for the actual hostname, forwarding to the API's loopback
   port 8000. Read the proxy/network notes in `deploy/README.md`.
5. Verify `https://<actual-host>/live`. Model weights download on first startup
   and persist in the `models` volume. `/health` returns unhealthy before a
   complete index is published; `/live` alone does not prove release readiness.

## Finish publication locally

Add a dedicated public-source read-only GitHub credential to `SOURCE_READ_TOKEN`
in the local `.env`, without pasting it into chat. Public REST/Git reads remain
anonymous, but GraphQL requires a token for Discussions and review resolution.
Do not give the API this token, the writer URL or the admin URL. The Compose
configuration keeps credentials separated by service.

The operator `ingest` service prepares capture and a generated site:

```sh
docker compose --env-file .env -f deploy/compose.yaml --profile operator run --rm --build ingest
```

Its artifacts and generated site persist in the `captures` and `generated-site`
volumes. A missing token or partial capture must continue to block publication.
Do not promote an incomplete corpus or publish the isolated sizing fixture.

The current publication design still uses GitHub Pages for the wiki and promotes
the API snapshot only after successful site deployment. Its workflow currently
uses GitHub-hosted runners. A private Compose database cannot be reached by those
runners. Before enabling daily publication, adapt the gateway's publication job
to a trusted runner with access to this Docker network, or explicitly choose a
local site-publication design. Do not expose PostgreSQL publicly as a shortcut.
The Compose `ingest` command alone does not deploy Pages or promote the snapshot.

Once the real hostname and runner/network are available, finish Pages/HTTPS,
daily ingestion, snapshot promotion, independent health monitoring, backups and
hosted rollback/withdrawal checks. The source token, host details and publication
network are the remaining inputs. No alert destination has been selected.

## Fresh checks for this handover

The retrieval Docker image builds successfully with `.dockerignore`; its Python
API imports as uid 65532 without ingestion scripts or Git metadata. A fresh local
PostgreSQL 16/pgvector database verified reader-role startup, `/live`, prepublication
health failure, then successful health and a 1,000-character REST search against
an isolated controlled fixture. See `evidence/docker-sizing.json`. These are local
smoke checks, not a hosted deployment or a repeat of the earlier 136-test suite.
