# ContentOS load test runner (V5.5.4)
param(
    [string]$BaseUrl = $(if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost:8000" }),
    [switch]$K6,
    [switch]$Python
)

$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $root

if (-not $K6 -and -not $Python) {
    if (Get-Command k6 -ErrorAction SilentlyContinue) { $K6 = $true } else { $Python = $true }
}

if ($K6) {
    if (-not (Get-Command k6 -ErrorAction SilentlyContinue)) {
        Write-Error "k6 not found. Install: https://k6.io/docs/get-started/installation/"
    }
    $env:BASE_URL = $BaseUrl
    k6 run scripts/loadtest/k6-smoke.js
    exit $LASTEXITCODE
}

python scripts/loadtest/smoke_load.py --base-url $BaseUrl
exit $LASTEXITCODE
