# Continue deployment after plugin refresh

15 October 2026. User requests completion of publication, hosting, Pages and monitoring,
and installed Render. Plugin directory confirms Render ENABLED/installed=true.
This chat still exposes no Render callable tools or skills and has no RENDER_*
runtime credential bindings. Recheck tool discovery in the refreshed chat. Do not
ask the user to reinstall or paste a token. No paid resources are authorized.

Repository: nklomp/webuild-knowledge-index. Draft PR: https://github.com/nklomp/webuild-knowledge-index/pull/1
Local branch: codex/native-cloud-continuation; push destination:
codex/native-cloud-recovery-validation. All upstream repositories remain read-only.

Current changes verify six wiki availability gaps from fresh public metadata and
GitHub UI/redirect evidence, preserve the fail-closed publication gate, prepare
separate Docker ingestion/retrieval targets, add /live for startup and Render host
validation, add deployment templates and a source/admin-separated Pages setup
helper. Full native suite passes 136 tests with real pgvector and pinned MiniLM.
Read deploy/README.md, AGENTS.md and docs/RUNBOOK.md.

Source GraphQL authentication is still missing. Public REST/Git already work;
GraphQL requires authentication even for public Discussions/review threads.
Visitors do not need credentials. Bind a dedicated read-only SOURCE_READ_TOKEN
to ingestion only; never reuse the gateway write integration for source crawling.
Eleven repositories remain partial due to GraphQL. Pages is currently not enabled
(GET returns 404); production writer URL and HTTPS API URL are also not configured.

Inspect existing Render workspaces/services/databases first. Create no paid resource
without reviewing capacity and price with the user. Bootstrap database roles with
a separate one-off ingestion image; expose only gateway_reader to retrieval.
Use /live for platform health, /health for freshness monitoring. Never put a
Render administrator database connection in retrieval. GitHub Actions ingestion
requires a reachable writer-role TLS URL with sslmode=verify-full.

Monitoring workflow activates only after PUBLIC_API_URL is configured; independent
monitor and existing authorized notification destination still need activation.
The systemd example is prepared, not installed. No alerts have been sent.

Native DB/model credentials are in ignored mode-0600 work/validation-env.json
and work/validation-suite-env.json; do not print or upload them. Docker uses
unix:///var/run/docker.sock with DOCKER_HOST/CONTEXT/TLS selector vars unset.
Existing validation database container: webuild-native-validation.
