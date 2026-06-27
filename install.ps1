$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSCommandPath
$pluginInstall = Join-Path $repoRoot 'plugins\lazy-eng-study-codex\scripts\install.ps1'
& $pluginInstall
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
