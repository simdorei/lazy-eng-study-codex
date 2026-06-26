param(
    [ValidateSet('spark', 'mini', 'gpt55')]
    [string]$Model = ''
)

$ErrorActionPreference = 'Stop'

function Select-KorToEngModel {
    if ($Model) {
        return $Model
    }

    Write-Host 'Choose Korean-to-English translation model:'
    Write-Host '  1. Spark     gpt-5.3-codex-spark'
    Write-Host '  2. Mini      gpt-5.4-mini'
    Write-Host '  3. GPT-5.5   gpt-5.5'
    $choice = Read-Host 'Enter 1, 2, or 3'

    switch ($choice) {
        '1' { return 'spark' }
        '2' { return 'mini' }
        '3' { return 'gpt55' }
        default { throw "Unknown choice: $choice" }
    }
}

$selectedAlias = Select-KorToEngModel
$scriptDir = Split-Path -Parent $PSCommandPath
$bootstrap = Join-Path $scriptDir 'bootstrap.ps1'
$powerShellExe = (Get-Process -Id $PID).Path

& $powerShellExe -NoProfile -ExecutionPolicy Bypass -File $bootstrap 'kortoeng_control.py' model $selectedAlias
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
