#Requires -Version 7.0
<#
.SYNOPSIS
    Pre-flight check. Run this 48 hours before the workshop.

.DESCRIPTION
    The Windows-native twin of verify.sh. The Java path does not need WSL.

    What it checks:
      - JDK 21+ is available.
      - The service builds.
      - The unit + API tests pass (no API key needed — the LLM is faked).
      - A GOOGLE_API_KEY is set (warning only; unit tests don't need it).

.PARAMETER Evals
    Additionally run the real eval suite: ~22 Gemini calls, about 30 seconds
    and roughly $0.01.
#>
param([switch]$Evals)

$ErrorActionPreference = 'Continue'
$script:Failed = $false

function Write-Pass($msg) { Write-Host "[PASS] $msg" -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; $script:Failed = $true }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

Write-Host "=== Expense Categoriser (Java) pre-flight check ==="
Write-Host ""

# JDK version
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
if (-not $script:Failed) {
    & ./mvnw.cmd -q compile *> $null
    if ($LASTEXITCODE -eq 0) { Write-Pass "service builds" }
    else { Write-Fail "build failed. Run './mvnw.cmd compile' to see why." }
}

# Unit + API tests
if (-not $script:Failed) {
    $output = & ./mvnw.cmd -q test 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "unit + API tests pass (23 tests)"
    } else {
        Write-Fail "unit + API tests failed. Run: ./mvnw.cmd test"
        $output | Select-Object -Last 30 | ForEach-Object { Write-Host "    $_" }
    }
}

# Load .env if present (existing environment variables win).
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
            $idx = $line.IndexOf('=')
            $key = $line.Substring(0, $idx).Trim()
            $value = $line.Substring($idx + 1).Trim().Trim('"', "'")
            if (-not [Environment]::GetEnvironmentVariable($key)) {
                [Environment]::SetEnvironmentVariable($key, $value)
            }
        }
    }
}

$apiKey = [Environment]::GetEnvironmentVariable('GOOGLE_API_KEY')
if ($apiKey -and $apiKey -ne 'your_gemini_api_key_here') {
    Write-Pass "GOOGLE_API_KEY is set"
} else {
    Write-Warn "GOOGLE_API_KEY not set. Unit tests don't need it, but M12's eval run does. Copy .env.example to .env before the workshop."
}

# Opt-in: the real eval suite.
if ($Evals -and -not $script:Failed) {
    Write-Host ""
    if (-not $apiKey -or $apiKey -eq 'your_gemini_api_key_here') {
        Write-Fail "-Evals needs a real GOOGLE_API_KEY in .env"
    } else {
        Write-Host "Running the eval suite against the real model (~30s, ~`$0.01)..."
        & ./mvnw.cmd -q test -Dgroups=evals -DexcludedGroups=
        if ($LASTEXITCODE -eq 0) { Write-Pass "eval suite passed" }
        else { Write-Fail "eval suite failed - see the output above" }
    }
}

Write-Host ""
if (-not $script:Failed) {
    Write-Host "All checks passed - you are ready for M11 and M12." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some checks failed. Fix the items above and re-run." -ForegroundColor Red
    exit 1
}
