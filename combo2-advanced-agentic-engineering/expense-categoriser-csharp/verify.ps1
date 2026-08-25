#Requires -Version 7.0
<#
.SYNOPSIS
    Pre-flight check. Run this 48 hours before the workshop.

.DESCRIPTION
    The Windows-native twin of verify.sh. The C# path does not need WSL.

    What it checks:
      - The .NET SDK 10+ is available.
      - The solution builds.
      - The unit + API tests pass (no API key needed — the LLM is mocked).
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

Write-Host "=== Expense Categoriser (C#) pre-flight check ==="
Write-Host ""

# .NET SDK version
if (Get-Command dotnet -ErrorAction SilentlyContinue) {
    $sdkVersion = (dotnet --version 2>$null)
    $sdkMajor = [int]($sdkVersion -split '\.')[0]
    if ($sdkMajor -ge 10) {
        Write-Pass ".NET SDK $sdkVersion (>= 10 required)"
    } else {
        Write-Fail ".NET SDK $sdkVersion is too old. Install .NET 10+ from https://dotnet.microsoft.com/download"
    }
} else {
    Write-Fail "dotnet not found. Install the .NET SDK 10+ from https://dotnet.microsoft.com/download"
}

# Build
if (-not $script:Failed) {
    dotnet build --nologo -v quiet *> $null
    if ($LASTEXITCODE -eq 0) { Write-Pass "solution builds" }
    else { Write-Fail "build failed. Run 'dotnet build' to see why." }
}

# Unit + API tests
if (-not $script:Failed) {
    $output = dotnet test --no-build --nologo --filter "Category!=Evals" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "unit + API tests pass"
    } else {
        Write-Fail 'unit + API tests failed. Run: dotnet test --filter "Category!=Evals"'
        $output | Select-Object -Last 20 | ForEach-Object { Write-Host "    $_" }
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
        dotnet test --no-build --nologo --filter "Category=Evals" --logger "console;verbosity=detailed"
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
