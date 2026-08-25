#Requires -Version 7.0
<#
.SYNOPSIS
    Pre-flight check. Run this 48 hours before the workshop.

.DESCRIPTION
    The Windows-native twin of verify.sh. The C# path does not need WSL —
    run this from PowerShell 7+ and you're set.

    What it checks:
      - The .NET SDK 10+ is available.
      - The solution builds.
      - The tool tests fail (they should — you haven't written the tools yet)
        and the reference implementation passes.
      - A GOOGLE_API_KEY is set (in .env or the environment).
      - A simple Gemini call succeeds.
#>

$ErrorActionPreference = 'Continue'
$script:Failed = $false

function Write-Pass($msg) { Write-Host "[PASS] $msg" -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; $script:Failed = $true }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

Write-Host "=== Tiny Agent (C#) pre-flight check ==="
Write-Host ""

# .NET SDK version
$dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
if ($dotnet) {
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

# Reference implementation must pass.
if (-not $script:Failed) {
    $env:TINY_AGENT_IMPL = 'reference'
    dotnet test --nologo -v quiet *> $null
    $refOk = $LASTEXITCODE -eq 0
    Remove-Item Env:\TINY_AGENT_IMPL -ErrorAction SilentlyContinue

    if ($refOk) { Write-Pass "reference implementation passes all tests" }
    else { Write-Fail "reference tests failed — that shouldn't happen. Email workshops@octoco.ai" }
}

# Your own tests are EXPECTED to fail before the workshop.
if (-not $script:Failed) {
    dotnet test --nologo -v quiet *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Warn "your tool tests already pass — have you done the exercise already? (that's fine)"
    } else {
        Write-Pass "your tool tests fail as expected (you write them in M8)"
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
    Write-Fail "GOOGLE_API_KEY not set. Copy .env.example to .env and add your key (https://aistudio.google.com/apikey)"
}

# End-to-end call.
if (-not $script:Failed) {
    Write-Host ""
    Write-Host "Calling Gemini to confirm the key works..."

    $model = [Environment]::GetEnvironmentVariable('GEMINI_MODEL')
    if (-not $model) { $model = 'gemini-3.1-flash-lite' }

    $body = @{
        contents = @(@{ role = 'user'; parts = @(@{ text = 'Reply with exactly one word: ready' }) })
    } | ConvertTo-Json -Depth 10

    try {
        $response = Invoke-RestMethod -Method Post `
            -Uri "https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent" `
            -Headers @{ 'x-goog-api-key' = $apiKey } `
            -ContentType 'application/json' `
            -Body $body

        $text = $response.candidates[0].content.parts[0].text
        if ($text -and $text.ToLower().Contains('ready')) {
            Write-Pass "Gemini call succeeded"
        } else {
            Write-Fail "Gemini replied unexpectedly: $text"
        }
    } catch {
        Write-Fail "Gemini call failed. Check your key and network. $($_.Exception.Message)"
    }
}

Write-Host ""
if (-not $script:Failed) {
    Write-Host "All checks passed - you are ready for M8." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some checks failed. Fix the items above and re-run." -ForegroundColor Red
    exit 1
}
