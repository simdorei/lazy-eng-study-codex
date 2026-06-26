$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$MinimumPythonMajor = 3
$MinimumPythonMinor = 11
$PortablePythonVersion = '3.12.13'
$PortableRelease = '20260623'
$DefaultDownloadRoot = "https://github.com/astral-sh/python-build-standalone/releases/download/$PortableRelease"

$PortableAssets = @{
    'windows-x64' = @{
        Name = "cpython-$PortablePythonVersion+$PortableRelease-x86_64-pc-windows-msvc-install_only_stripped.tar.gz"
        Sha256 = 'de3e362376859b060fa8b856c434efa81fcf6d4ede3d6e177c7e2169670cac50'
        Runtime = "cpython-$PortablePythonVersion-windows-x64"
        Python = 'python\python.exe'
    }
    'windows-arm64' = @{
        Name = "cpython-$PortablePythonVersion+$PortableRelease-aarch64-pc-windows-msvc-install_only_stripped.tar.gz"
        Sha256 = 'f810e2c17316241a73b5e133eb0854502968ccd62fcc4853edaf8e2a697c7a3e'
        Runtime = "cpython-$PortablePythonVersion-windows-arm64"
        Python = 'python\python.exe'
    }
}

function Get-RuntimeRoot {
    if ($env:CODEX_KOR_TO_ENG_RUNTIME_DIR) {
        return $env:CODEX_KOR_TO_ENG_RUNTIME_DIR
    }
    if ($env:CODEX_HOME) {
        return (Join-Path $env:CODEX_HOME 'codex-kor-to-eng\runtime')
    }
    return (Join-Path $HOME '.codex\codex-kor-to-eng\runtime')
}

function Get-DownloadRoot {
    if ($env:CODEX_KOR_TO_ENG_PYTHON_DOWNLOAD_ROOT) {
        return $env:CODEX_KOR_TO_ENG_PYTHON_DOWNLOAD_ROOT.TrimEnd('/')
    }
    return $DefaultDownloadRoot
}

function Get-PlatformKey {
    if (($env:OS -ne 'Windows_NT') -and -not $env:CODEX_KOR_TO_ENG_TEST_PLATFORM) {
        throw 'bootstrap.ps1 only supports Windows. Use bootstrap.sh on macOS.'
    }
    if ($env:CODEX_KOR_TO_ENG_TEST_PLATFORM) {
        return $env:CODEX_KOR_TO_ENG_TEST_PLATFORM
    }

    $arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
    switch ($arch) {
        'X64' { return 'windows-x64' }
        'Arm64' { return 'windows-arm64' }
        default { throw "unsupported Windows architecture for portable Python: $arch" }
    }
}

function Invoke-PythonCheck {
    param([string[]]$Command)

    $exe = $Command[0]
    $prefixArgs = @()
    if ($Command.Count -gt 1) {
        $prefixArgs = $Command[1..($Command.Count - 1)]
    }
    $check = "import sys; raise SystemExit(0 if sys.version_info >= ($MinimumPythonMajor, $MinimumPythonMinor) else 1)"
    $arguments = @($prefixArgs) + @('-c', $check)
    try {
        & $exe @arguments > $null 2> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Resolve-SystemPython {
    if ($env:CODEX_KOR_TO_ENG_PYTHON_BIN) {
        $configured = @($env:CODEX_KOR_TO_ENG_PYTHON_BIN)
        if (Invoke-PythonCheck $configured) {
            return [pscustomobject]@{ Command = $configured; Source = 'configured'; Path = $configured[0] }
        }
        throw "CODEX_KOR_TO_ENG_PYTHON_BIN is not Python $MinimumPythonMajor.$MinimumPythonMinor+: $($configured[0])"
    }

    if ($env:CODEX_KOR_TO_ENG_BOOTSTRAP_FORCE_PORTABLE -eq '1') {
        return $null
    }

    $candidates = @(
        @('py', '-3'),
        @('python'),
        @('python3')
    )
    foreach ($candidate in $candidates) {
        if (Invoke-PythonCheck $candidate) {
            return [pscustomobject]@{
                Command = $candidate
                Source = 'system'
                Path = ($candidate -join ' ')
            }
        }
    }
    return $null
}

function Assert-Hash {
    param(
        [string]$Path,
        [string]$Expected
    )

    $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $Expected) {
        throw "portable Python SHA256 mismatch for $Path; expected $Expected, got $actual"
    }
}

function Remove-TreeUnder {
    param(
        [string]$Path,
        [string]$Root
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    $rootPath = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $Root).Path)
    $targetPath = [System.IO.Path]::GetFullPath($Path)
    if (-not $targetPath.StartsWith($rootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "refusing to remove path outside runtime root: $targetPath"
    }
    Remove-Item -LiteralPath $Path -Recurse -Force
}

function Ensure-PortablePython {
    $runtimeRoot = Get-RuntimeRoot
    $platform = Get-PlatformKey
    $asset = $PortableAssets[$platform]
    if ($null -eq $asset) {
        throw "unsupported platform for portable Python: $platform"
    }

    $target = Join-Path $runtimeRoot $asset.Runtime
    $python = Join-Path $target $asset.Python
    if ((Test-Path -LiteralPath $python) -and (Invoke-PythonCheck @($python))) {
        return [pscustomobject]@{ Command = @($python); Source = 'portable'; Path = $python }
    }

    $downloadDir = Join-Path $runtimeRoot 'downloads'
    New-Item -ItemType Directory -Force -Path $downloadDir > $null
    $archive = Join-Path $downloadDir $asset.Name
    if (Test-Path -LiteralPath $archive) {
        try {
            Assert-Hash $archive $asset.Sha256
        } catch {
            Remove-Item -LiteralPath $archive -Force
        }
    }
    if (-not (Test-Path -LiteralPath $archive)) {
        $url = "$(Get-DownloadRoot)/$([System.Uri]::EscapeDataString($asset.Name))"
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $archive
    }
    Assert-Hash $archive $asset.Sha256

    $extractRoot = Join-Path $runtimeRoot "extract-$PID"
    $targetTmp = "$target.tmp.$PID"
    Remove-TreeUnder $extractRoot $runtimeRoot
    Remove-TreeUnder $targetTmp $runtimeRoot
    New-Item -ItemType Directory -Force -Path $extractRoot > $null
    New-Item -ItemType Directory -Force -Path $targetTmp > $null
    try {
        tar -xzf $archive -C $extractRoot
        if ($LASTEXITCODE -ne 0) {
            throw "tar exited $LASTEXITCODE while extracting portable Python"
        }
        Move-Item -LiteralPath (Join-Path $extractRoot 'python') -Destination (Join-Path $targetTmp 'python')
        Remove-TreeUnder $target $runtimeRoot
        Move-Item -LiteralPath $targetTmp -Destination $target
    } finally {
        Remove-TreeUnder $extractRoot $runtimeRoot
        Remove-TreeUnder $targetTmp $runtimeRoot
    }

    if (-not (Invoke-PythonCheck @($python))) {
        throw "portable Python is not usable after extraction: $python"
    }
    return [pscustomobject]@{ Command = @($python); Source = 'portable'; Path = $python }
}

function Resolve-Python {
    $system = Resolve-SystemPython
    if ($null -ne $system) {
        return $system
    }
    return Ensure-PortablePython
}

function ConvertTo-ProcessArgument {
    param([string]$Value)

    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    return '"' + ($Value -replace '"', '\"') + '"'
}

function Invoke-ProcessWithInput {
    param(
        [string]$FileName,
        [string[]]$Arguments,
        [string]$StandardInput
    )

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $FileName
    $startInfo.Arguments = (($Arguments | ForEach-Object { ConvertTo-ProcessArgument $_ }) -join ' ')
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardInput = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.StandardOutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $startInfo.StandardErrorEncoding = [System.Text.UTF8Encoding]::new($false)

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    if (-not $process.Start()) {
        throw "failed to start Python: $FileName"
    }
    $process.StandardInput.Write($StandardInput)
    $process.StandardInput.Close()
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    [Console]::Out.Write($stdout)
    [Console]::Error.Write($stderr)
    return $process.ExitCode
}

function Invoke-ResolvedPython {
    param(
        [object]$Resolution,
        [string[]]$Arguments,
        [string]$StandardInput = ''
    )

    $command = $Resolution.Command
    $exe = $command[0]
    $prefixArgs = @()
    if ($command.Count -gt 1) {
        $prefixArgs = $command[1..($command.Count - 1)]
    }
    $allArgs = @($prefixArgs) + @($Arguments)
    if ($StandardInput -ne '') {
        return Invoke-ProcessWithInput $exe $allArgs $StandardInput
    }
    & $exe @allArgs
    return $LASTEXITCODE
}

function Read-StandardInputUtf8 {
    $stream = [Console]::OpenStandardInput()
    $buffer = [byte[]]::new(4096)
    $memory = [System.IO.MemoryStream]::new()
    try {
        while (($count = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
            $memory.Write($buffer, 0, $count)
        }
        return [System.Text.UTF8Encoding]::new($false).GetString($memory.ToArray())
    } finally {
        $memory.Dispose()
    }
}
