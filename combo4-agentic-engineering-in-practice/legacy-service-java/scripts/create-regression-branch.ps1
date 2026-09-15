#Requires -Version 7.0
<#
.SYNOPSIS
    Create a deliberately-regressing branch for the Combo 4 M4 demo.

.DESCRIPTION
    The Windows-native twin of create-regression-branch.sh.

    Creates a branch `demo/regression-total-rounding` off the current HEAD
    and rewrites computeTotal() in
    src/main/java/ai/octoco/legacyservice/Orders.java to round order totals
    to whole currency units, dressed up as a plausible "POS sync" refactor.

    Run from the repo root:
        ./scripts/create-regression-branch.ps1
#>

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$target = 'src/main/java/ai/octoco/legacyservice/Orders.java'
if (-not (Test-Path $target)) {
    Write-Error "Run this from the repo root; $target not found."
    exit 1
}

$branch = 'demo/regression-total-rounding'
git rev-parse --verify $branch *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Branch $branch already exists. Delete it first if you want a fresh demo:"
    Write-Host "    git branch -D $branch"
    exit 1
}

git checkout -b $branch

$original = Get-Content $target -Raw

$before = @'
        double total = subtotal * (1.0 - discountPct / 100.0);
        return Utils.money(total);
'@.TrimEnd("`r", "`n")

$after = @'
        double total = subtotal * (1.0 - discountPct / 100.0);
        // refactor: round order totals to whole currency units for the POS sync
        return (double) Math.round(total);
'@.TrimEnd("`r", "`n")

$regressed = $original.Replace($before, $after)

if ($regressed -eq $original) {
    Write-Error "computeTotal block not found - has Orders.java changed since this script was written?"
    exit 1
}

Set-Content -Path $target -Value $regressed -NoNewline
Write-Host "Regressed computeTotal() in Orders.java."

git add $target
git commit -m @"
refactor: round order totals to whole units for POS sync

Deliberate regression for the Combo 4 M4 demo. Opening a PR from this branch
should fail the tests workflow: the smoke suite expects cent-accurate totals.
"@

Write-Host ""
Write-Host "Regression branch ready. Push and open a PR to see CI block the merge:"
Write-Host "    git push -u origin $branch"
Write-Host "    gh pr create --title 'refactor: whole-unit order totals' --body 'Watch me fail CI.'"
Write-Host ""
Write-Host "To clean up afterwards:"
Write-Host "    git checkout -"
Write-Host "    git branch -D $branch"
