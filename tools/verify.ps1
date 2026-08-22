[CmdletBinding()]
param(
    [switch]$SkipTests,
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $root.StartsWith("D:\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "CareHub verification must run from D:. Resolved root: $root"
}

if (-not (Get-Command $PythonCommand -ErrorAction SilentlyContinue)) {
    throw "Python command '$PythonCommand' was not found. Pass -PythonCommand with a supported Python executable."
}
& (Join-Path $PSScriptRoot "bootstrap-d.ps1") -PythonCommand $PythonCommand
$python = if ($env:CAREHUB_PYTHON) { $env:CAREHUB_PYTHON } else { $PythonCommand }
foreach ($name in "PNPM_STORE_DIR", "npm_config_store_dir", "npm_config_cache", "PLAYWRIGHT_BROWSERS_PATH", "PIP_CACHE_DIR", "TMP", "TEMP") {
    if (-not (Get-Item "Env:$name").Value.StartsWith("D:\", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$name does not target D:."
    }
}

Push-Location $root
try {
    & $python -m scripts.validate_contracts
    if ($LASTEXITCODE -ne 0) { throw "Contract validation failed." }
    & $python -m scripts.verify_b0
    if ($LASTEXITCODE -ne 0) { throw "B0 baseline validation failed." }
    if (-not $SkipTests) {
        & $python -m pytest -q
        if ($LASTEXITCODE -ne 0) { throw "Python test suite failed." }
        pnpm --filter @carehub/family-pwa test
        if ($LASTEXITCODE -ne 0) { throw "Family PWA unit test suite failed." }
        pnpm --filter @carehub/family-pwa build
        if ($LASTEXITCODE -ne 0) { throw "Family PWA build failed." }
    }
} finally { Pop-Location }

Write-Host "B0 local verification passed. Elder-terminal acceptance remains separately blocked."
