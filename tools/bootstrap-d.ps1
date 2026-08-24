[CmdletBinding()]
param(
    [switch]$Install,
    [string]$PythonCommand = "python",
    [string]$PnpmCommand = "pnpm"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $root.StartsWith("D:\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "CareHub development tooling must run from D:. Resolved root: $root"
}

$toolRoot = Join-Path $root ".carehub-toolchain"
$venvRoot = Join-Path $toolRoot "python-venv"
$paths = @{
    "PNPM_HOME" = Join-Path $toolRoot "pnpm-home"
    "PNPM_STORE_DIR" = Join-Path $toolRoot "pnpm-store"
    "npm_config_store_dir" = Join-Path $toolRoot "pnpm-store"
    "npm_config_cache" = Join-Path $toolRoot "npm-cache"
    "PLAYWRIGHT_BROWSERS_PATH" = Join-Path $toolRoot "playwright-browsers"
    "PIP_CACHE_DIR" = Join-Path $toolRoot "pip-cache"
    "TMP" = Join-Path $toolRoot "tmp"
    "TEMP" = Join-Path $toolRoot "tmp"
}
foreach ($entry in $paths.GetEnumerator()) {
    New-Item -ItemType Directory -Force -Path $entry.Value | Out-Null
    [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process")
}

if ($Install) {
    & $PythonCommand -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) { throw "D: Python virtual-environment creation failed." }
    $venvPython = Join-Path $venvRoot "Scripts\\python.exe"
    & $venvPython -m pip install -r (Join-Path $root "requirements-dev.txt")
    if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
    $env:CAREHUB_PYTHON = $venvPython
    $env:CI = "true"
    Push-Location $root
    try {
        & $PnpmCommand install --frozen-lockfile
        if ($LASTEXITCODE -ne 0) { throw "pnpm installation failed." }
        & $PnpmCommand --filter @carehub/family-pwa exec playwright install chromium
        if ($LASTEXITCODE -ne 0) { throw "Playwright browser installation failed." }
    } finally { Pop-Location }
}

Write-Host "D: toolchain configured under $toolRoot"
