#Requires -Version 7.0
<#
.SYNOPSIS
    Pre-flight check for the OrderBase (Java) sample repo.

.DESCRIPTION
    The Windows-native twin of verify.sh. The Java path does not need WSL --
    run this from PowerShell 7+ and you're set.

    What it checks:
      - The JDK 21+ is available.
      - The jar builds.
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

Write-Host "=== OrderBase (Java) pre-flight ==="
Write-Host ""

# JDK 21+
$javaCmd = Get-Command java -ErrorAction SilentlyContinue
if ($javaCmd) {
    $versionOutput = (& java -version 2>&1 | Out-String)
    if ($versionOutput -match '"(\d+)(\.\d+)?') {
        $javaMajor = [int]$Matches[1]
        if ($javaMajor -ge 21) {
            Write-Pass "JDK $javaMajor (>= 21 required)"
        } else {
            Write-Fail "JDK $javaMajor is too old. Install JDK 21+ (e.g. https://adoptium.net/)"
        }
    } else {
        Write-Fail "Could not determine Java version from: $versionOutput"
    }
} else {
    Write-Fail "java not found. Install JDK 21+ (e.g. https://adoptium.net/)"
}

# Build
Write-Host ""
Write-Host "=== Building (./mvnw.cmd package) ==="
if (-not $script:Failed) {
    & ./mvnw.cmd -q package -DskipTests *> $null
    if ($LASTEXITCODE -eq 0) { Write-Pass "jar builds" }
    else { Write-Fail "build failed. Run './mvnw.cmd package -DskipTests' to see why." }
}

# Smoke tests
Write-Host ""
Write-Host "=== Running smoke tests ==="
if (-not $script:Failed) {
    & ./mvnw.cmd -q test *> $null
    if ($LASTEXITCODE -eq 0) { Write-Pass "smoke tests" }
    else { Write-Fail "smoke tests failed. Run './mvnw.cmd test' to see why." }
}

# Boot the service and hit one endpoint, from a scratch dir with a scratch DB
# so we don't leave orderbase.db or a log file behind in the repo.
Write-Host ""
Write-Host "=== Booting service and probing GET /orders?limit=1 ==="
$appJar = Get-ChildItem -Path "target" -Filter "*.jar" -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -notlike "*.jar.original" } | Select-Object -First 1

if (-not $appJar) {
    Write-Fail "could not find the built jar (target/*.jar). Run './mvnw.cmd package -DskipTests' first."
} else {
    $bootDir = Join-Path ([System.IO.Path]::GetTempPath()) "orderbase-verify-$([guid]::NewGuid())"
    New-Item -ItemType Directory -Path $bootDir | Out-Null
    $env:ORDERBASE_DB = Join-Path $bootDir "verify.db"

    $proc = Start-Process -FilePath "java" -ArgumentList "-jar", "`"$($appJar.FullName)`"" `
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
    Write-Host "Ready. Start the service with: ./mvnw.cmd spring-boot:run" -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some checks failed." -ForegroundColor Red
    exit 1
}
