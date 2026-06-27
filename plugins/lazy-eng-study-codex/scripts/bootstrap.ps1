param(
    [switch]$EnsurePython,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Remaining
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $PSCommandPath
. (Join-Path $scriptDir 'portable_python.ps1')

$scriptName = 'kor_to_eng_hook.py'
$scriptArgs = @()
$hookMode = $Remaining.Count -eq 0
if ($Remaining.Count -gt 0) {
    $scriptName = $Remaining[0]
    if ($Remaining.Count -gt 1) {
        $scriptArgs = $Remaining[1..($Remaining.Count - 1)]
    }
}
$standardInput = if ($hookMode -and -not $EnsurePython) { Read-StandardInputUtf8 } else { '' }

$resolution = Resolve-Python
if ($EnsurePython) {
    Write-Output "python_source=$($resolution.Source)"
    Write-Output "python_bin=$($resolution.Path)"
    Write-Output "runtime_dir=$(Get-RuntimeRoot)"
    exit 0
}
$scriptPath = if ([System.IO.Path]::IsPathRooted($scriptName)) {
    $scriptName
} else {
    Join-Path $scriptDir $scriptName
}
exit (Invoke-ResolvedPython $resolution (@($scriptPath) + @($scriptArgs)) $standardInput)
