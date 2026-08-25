#Requires -Version 7.0
<#
.SYNOPSIS
    Create a deliberately-regressing branch for the Combo 2 M12 demo.

.DESCRIPTION
    The Windows-native twin of create-regression-branch.sh.

    Creates a branch `demo/regression-prompt` off main and tweaks the system
    prompt in src/ExpenseCategoriser/Core.cs to bias the model toward "Other"
    for edge cases. That tanks the accuracy metric enough to fail the eval gate,
    so a PR from this branch is blocked by evals.yml until the prompt is fixed.

    Run from the repo root:
        ./scripts/create-regression-branch.ps1
#>

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$target = 'src/ExpenseCategoriser/Core.cs'
if (-not (Test-Path $target)) {
    Write-Error "Expected to be run from the repo root, with $target present."
    exit 1
}

$branch = 'demo/regression-prompt'
git rev-parse --verify $branch *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Branch $branch already exists. Delete it first if you want a fresh demo:"
    Write-Host "    git branch -D $branch"
    exit 1
}

git checkout -b $branch

$original = Get-Content $target -Raw

$before = @'
        - "confidence" is your self-reported certainty. Use 0.9+ for obvious matches
          (grocery store -> Food & Dining), 0.5-0.7 for ambiguous cases, below 0.5
          for genuinely unclear items.
'@.TrimEnd("`r", "`n")

$after = @'
        - "confidence" is your self-reported certainty. When in doubt, use low
          confidence (0.3-0.5) — it's safer. Prefer the "Other" category for any
          transaction that isn't perfectly obvious.
'@.TrimEnd("`r", "`n")

$regressed = $original.Replace($before, $after)

if ($regressed -eq $original) {
    Write-Error "Prompt block not found - has Core.cs changed since the regression script was written?"
    exit 1
}

Set-Content -Path $target -Value $regressed -NoNewline
Write-Host "Regressed Core.cs."

git add $target
git commit -m @"
demo: regress prompt to bias toward 'Other'

Deliberate regression for Combo 2 M12 demo. Opening a PR against main from
this branch should fail the evals workflow on AccuracyThreshold.
"@

Write-Host ""
Write-Host "Regression branch ready. Push and open a PR to see evals block the merge:"
Write-Host "    git push -u origin $branch"
Write-Host "    gh pr create --title 'demo: regress the prompt' --body 'Watch me fail the evals.'"
Write-Host ""
Write-Host "To clean up afterwards:"
Write-Host "    git checkout main"
Write-Host "    git branch -D $branch"
