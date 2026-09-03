#Requires -Version 7.0
<#
.SYNOPSIS
    Pre-flight check for the OrderBase (C#) sample repo.

.DESCRIPTION
    The Windows-native twin of verify.sh. The C# path does not need WSL --
    run this from PowerShell 7+ and you're set.

    What it checks:
      - The .NET SDK 10+ is available.
      - The solution builds.
      - The smoke tests pass.
      - The service boots and answers GET /orders?limit=1.
#>

$ErrorActionPreference = 'Continue'
$script:Failed = $false

function Write-Pass($msg) { Write-Host "[PASS] $msg" -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; $script:Failed = $true }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "=== OrderBase (C#) pre-flight ==="
Write-Host ""

# .NET SDK 10+
$dotnetCmd = Get-Command dotnet -ErrorAction SilentlyContinue
if ($dotnetCmd) {
    $sdkVersion = (dotnet --version 2>$null)
    $sdkMajor = [int]($sdkVersion -split '\.')[0]
    if ($sdkMajor -ge 10) {
        Write-Pass ".NET SDK $sdkVersion (>= 10 required)"
    } else {
        Write-Fail ".NET SDK $sdkVersion is too old. Install .NET 10 or later from https://dotnet.microsoft.com/download"
    }
} else {
    Write-Fail "dotnet not found. Install the .NET SDK 10+ from https://dotnet.microsoft.com/download"
}

# Build
Write-Host ""
Write-Host "=== Building (dotnet build) ==="
dotnet build --nologo -v quiet *> $null
if ($LASTEXITCODE -eq 0) { Write-Pass "solution builds" }
else { Write-Fail "build failed. Run 'dotnet build' to see why." }

# Smoke tests
Write-Host ""
Write-Host "=== Running smoke tests ==="
dotnet test --no-restore --nologo -v quiet *> $null
if ($LASTEXITCODE -eq 0) { Write-Pass "smoke tests" }
else { Write-Fail "smoke tests failed" }

# Boot the service and hit one endpoint, from a scratch dir with a scratch DB
# so we don't leave orderbase.db or a log file behind in the repo.
Write-Host ""
Write-Host "=== Booting service and probing GET /orders?limit=1 ==="
$appDll = Get-ChildItem -Path "src/LegacyService/bin" -Recurse -Filter "legacy-service.dll" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match '[\\/]Debug[\\/]' } | Select-Object -First 1

if (-not $appDll) {
    Write-Fail "could not find the built app (src/LegacyService/bin/Debug/**/legacy-service.dll). Run 'dotnet build' first."
} else {
    $bootDir = Join-Path ([System.IO.Path]::GetTempPath()) "orderbase-verify-$([guid]::NewGuid())"
    New-Item -ItemType Directory -Path $bootDir | Out-Null
    $env:ORDERBASE_DB = Join-Path $bootDir "verify.db"

    $proc = Start-Process -FilePath "dotnet" -ArgumentList "`"$($appDll.FullName)`"" `
        -WorkingDirectory $bootDir -RedirectStandardOutput "$bootDir\app.log" `
        -RedirectStandardError "$bootDir\app.err.log" -PassThru -NoNewWindow

    $code = $null
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:5057/orders?limit=1" -UseBasicParsing -TimeoutSec 2
            $code = $resp.StatusCode
            if ($code -eq 200) { break }
        } catch {
            if ($proc.HasExited) { break }
        }
        Start-Sleep -Milliseconds 500
    }

    if ($code -eq 200) {
        Write-Pass "GET /orders?limit=1 -> 200"
    } else {
        Write-Fail "GET /orders?limit=1 -> $(if ($code) { $code } else { 'no response' })"
        Write-Host "--- app output ---"
        Get-Content "$bootDir\app.log" -ErrorAction SilentlyContinue | Select-Object -Last 20
        Get-Content "$bootDir\app.err.log" -ErrorAction SilentlyContinue | Select-Object -Last 20
    }

    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $bootDir -ErrorAction SilentlyContinue
    Remove-Item Env:\ORDERBASE_DB -ErrorAction SilentlyContinue
}

Write-Host ""
if (-not $script:Failed) {
    Write-Host "Ready. Start the service with: dotnet run --project src/LegacyService" -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some checks failed." -ForegroundColor Red
    exit 1
}
