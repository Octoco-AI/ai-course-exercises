#Requires -Version 7.0
<#
.SYNOPSIS
    Create a deliberately-regressing branch for the Combo 4 M4 demo.

.DESCRIPTION
    The Windows-native twin of create-regression-branch.sh.

    Creates a branch `demo/regression-total-rounding` off the current HEAD and
    rewrites ComputeTotal() in src/LegacyService/Orders.cs to round order
    totals to whole currency units, dressed up as a plausible "POS sync"
    refactor. That breaks SmokeTests.CreateOrder_ReturnsExpectedShape (expects
    total==19.99, now gets 20), so `dotnet test` -- and the tests.yml PR gate
    -- goes red.

    Run from the repo root:
        ./scripts/create-regression-branch.ps1
#>

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$target = 'src/LegacyService/Orders.cs'
if (-not (Test-Path $target)) {
    Write-Error "Expected to be run from the repo root, with $target present."
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
        var total = subtotal * (1.0 - discountPct / 100.0);
        return Utils.Money(total);
'@.TrimEnd("`r", "`n")

$after = @'
        var total = subtotal * (1.0 - discountPct / 100.0);
        // refactor: round order totals to whole currency units for the POS sync
        return Math.Round(total);
'@.TrimEnd("`r", "`n")

$regressed = $original.Replace($before, $after)

if ($regressed -eq $original) {
    Write-Error "ComputeTotal block not found - has Orders.cs changed since the regression script was written?"
    exit 1
}

Set-Content -Path $target -Value $regressed -NoNewline
Write-Host "Regressed ComputeTotal() in Orders.cs."

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
