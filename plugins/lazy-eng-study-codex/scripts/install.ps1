$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $PSCommandPath
$bootstrap = Join-Path $scriptDir 'bootstrap.ps1'
$powerShellExe = (Get-Process -Id $PID).Path

function Invoke-Bootstrap {
    param([string[]]$Arguments)

    & $powerShellExe -NoProfile -ExecutionPolicy Bypass -File $bootstrap @Arguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Write-Output 'Lazy Eng Study Codex install starting'
Invoke-Bootstrap @('-EnsurePython')
Invoke-Bootstrap @('install_plugin.py')
Invoke-Bootstrap @('kortoeng_control.py', 'model', 'mini')
Invoke-Bootstrap @('kortoeng_control.py', 'on')
Invoke-Bootstrap @('kortoeng_control.py', 'codex-bin')
Invoke-Bootstrap @('kortoeng_control.py', 'status')
Write-Output 'install=ok'
