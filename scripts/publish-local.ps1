param([switch]$PreparedOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if ((docker context show) -ne 'desktop-linux') {
        throw 'The configured Docker context must be desktop-linux; not switching another workspace context.'
    }
    if (docker ps --filter 'name=^webuild-knowledge-capture-20261015$' --format '{{.Names}}') {
        throw 'Initial capture is still running; do not start a concurrent publication.'
    }
    $composeArgs = @('-p','webuild-knowledge','--env-file','.env','-f','deploy/compose.yaml','-f','deploy/compose.vdx-edge.yaml')
    docker compose @composeArgs config --quiet
    if ($LASTEXITCODE) { throw 'Compose configuration failed.' }
    docker compose @composeArgs up -d --no-build --wait --wait-timeout 240 db retrieval wiki
    if ($LASTEXITCODE) { throw 'Gateway services could not be started.' }
    $operatorArgs = @('--profile','operator','run','--rm','-T','--build','ingest','python','scripts/publish_local.py')
    if ($PreparedOnly) { $operatorArgs += '--prepared-only' }
    docker compose @composeArgs @operatorArgs
    if ($LASTEXITCODE) { throw 'Publication failed; inspect coverage and publication logs. Do not bypass the complete-capture gate.' }
} finally {
    Pop-Location
}
