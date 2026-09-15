#Requires -Version 7.0
<#
.SYNOPSIS
    Pre-flight check. Run this 48 hours before the workshop.

.DESCRIPTION
    The Windows-native twin of verify.sh. The Java path does not need WSL —
    run this from PowerShell 7+ and you're set.

    What it checks:
      - JDK 21+ is available.
      - The modules build and install (so exec:java can resolve them).
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

Write-Host "=== Tiny Agent (Java) pre-flight check ==="
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

# Build + install (so exec:java can resolve tiny-agent-shared later).
if (-not $script:Failed) {
    & ./mvnw.cmd -q install -DskipTests *> $null
    if ($LASTEXITCODE -eq 0) { Write-Pass "modules build and install" }
    else { Write-Fail "build failed. Run './mvnw.cmd install -DskipTests' to see why." }
}

# Reference implementation must pass.
if (-not $script:Failed) {
    $env:TINY_AGENT_IMPL = 'reference'
    & ./mvnw.cmd -q -pl tests -am test *> $null
    $refOk = $LASTEXITCODE -eq 0
    Remove-Item Env:\TINY_AGENT_IMPL -ErrorAction SilentlyContinue

    if ($refOk) { Write-Pass "reference implementation passes all tests" }
    else { Write-Fail "reference tests failed — that shouldn't happen. Email workshops@octoco.ai" }
}

# Your own tests are EXPECTED to fail before the workshop.
if (-not $script:Failed) {
    & ./mvnw.cmd -q -pl tests -am test *> $null
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
