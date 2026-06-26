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

switch (Select-KorToEngModel) {
    'spark' {
        $selected = 'gpt-5.3-codex-spark'
        $timeoutSeconds = '90'
    }
    'mini' {
        $selected = 'gpt-5.4-mini'
        $timeoutSeconds = '45'
    }
    'gpt55' {
        $selected = 'gpt-5.5'
        $timeoutSeconds = '90'
    }
    default { throw 'Unknown model selection.' }
}

[Environment]::SetEnvironmentVariable('CODEX_KOR_TO_ENG_MODEL', $selected, 'User')
[Environment]::SetEnvironmentVariable('CODEX_KOR_TO_ENG_TIMEOUT_SECONDS', $timeoutSeconds, 'User')

Write-Host "CODEX_KOR_TO_ENG_MODEL=$selected"
Write-Host "CODEX_KOR_TO_ENG_TIMEOUT_SECONDS=$timeoutSeconds"
Write-Host 'Restart Codex for the hook to read this setting.'
