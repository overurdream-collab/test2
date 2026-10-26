#requires -Version 5.1
# Updates an existing MCIAS checkout to the reviewed pre-A1 baseline.
# Does not reset files, delete volumes, replace keys, create commits or push.
[CmdletBinding()]
param(
    [string]$RepoPath = '',
    [switch]$UpdateOnly
)
$ErrorActionPreference = 'Stop'
$expectedCommit = 'daaed6a1d271933adaff8b899b0bb63ee48fb725'
$expectedBranch = 'feat/windows-laptop-testing'
$repositoryUrl = 'https://github.com/overurdream-collab/test2.git'

Get-Command git -ErrorAction Stop | Out-Null
if (-not $RepoPath) {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = 'Select the EXISTING MCIAS project folder on this laptop.'
    $dialog.ShowNewFolderButton = $false
    try {
        if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
            throw 'No project folder selected. Nothing changed.'
        }
        $RepoPath = $dialog.SelectedPath
    } finally { $dialog.Dispose() }
}
$RepoPath = (Resolve-Path -LiteralPath $RepoPath).Path

function Invoke-ProjectGit {
    param([string[]]$GitArguments)
    $previousPreference = $ErrorActionPreference
    try {
        # Git progress uses stderr even on success in Windows PowerShell 5.1.
        $ErrorActionPreference = 'Continue'
        $result = & git -C $RepoPath @GitArguments
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    if ($code -ne 0) {
        throw 'Git operation failed. Existing work was not reset or deleted.'
    }
    return $result
}

$root = (@(Invoke-ProjectGit -GitArguments @('rev-parse','--show-toplevel')) -join "`n").Trim()
$RepoPath = (Resolve-Path -LiteralPath $root).Path
$launcher = Join-Path $RepoPath 'scripts/laptop.ps1'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw 'This folder does not contain the existing MCIAS laptop launcher.'
}
$branch = (@(Invoke-ProjectGit -GitArguments @('branch','--show-current')) -join "`n").Trim()
if ($branch -ne $expectedBranch) {
    throw 'Expected feat/windows-laptop-testing. No branch was switched or created.'
}
$origin = (@(Invoke-ProjectGit -GitArguments @('config','--get','remote.origin.url')) -join "`n").Trim()
if ($origin -notmatch 'github\.com[:/]overurdream-collab/test2(?:\.git)?/?$') {
    throw 'Select the GitHub MCIAS checkout, not a local mirror or another repository.'
}
$dirty = @(Invoke-ProjectGit -GitArguments @('status','--porcelain','--untracked-files=normal'))
if ($dirty.Count) {
    throw 'Local changes or untracked files exist. Preserve them and review git status; do not use reset or clean.'
}

$privateFile = Join-Path $RepoPath 'deploy/laptop-private/.env'
$privateHashBefore = $null
if (Test-Path -LiteralPath $privateFile -PathType Leaf) {
    $privateHashBefore = (Get-FileHash -LiteralPath $privateFile -Algorithm SHA256).Hash
}
if (-not $UpdateOnly) {
    if ($env:COMPOSE_PROJECT_NAME -and $env:COMPOSE_PROJECT_NAME -ne 'mcias-laptop') {
        throw 'A custom COMPOSE_PROJECT_NAME is set. Review the existing installation before starting; no keys or volumes were changed.'
    }
    Get-Command docker -ErrorAction Stop | Out-Null
    $containerOS = (& docker info --format '{{.OSType}}')
    if ($LASTEXITCODE -ne 0 -or $containerOS -ne 'linux') {
        throw 'Open Docker Desktop and wait for Linux containers / WSL2 to be ready.'
    }
    & docker compose version | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose v2 is required.' }
    $volumes = @(& docker volume ls --filter 'label=com.docker.compose.project=mcias-laptop' --format '{{.Name}}')
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect existing laptop volumes.' }
    if ($volumes.Count -and -not $privateHashBefore) {
        throw 'Existing MCIAS volumes found but this folder has no original .env. Use the original project folder and keys; do not initialize new keys.'
    }
}

Write-Host 'Fetching the existing review branch. No local branch or commit is created.'
Invoke-ProjectGit -GitArguments @('fetch','--no-tags',$repositoryUrl,'refs/heads/feat/windows-laptop-testing')
Invoke-ProjectGit -GitArguments @('cat-file','-e',($expectedCommit + '^{commit}'))
& git -C $RepoPath merge-base --is-ancestor HEAD $expectedCommit
if ($LASTEXITCODE -ne 0) {
    throw 'The local history is newer or different. No rollback, reset, or conflicting merge was attempted.'
}
# Fast-forward only: cannot create a merge commit or overwrite divergent history.
Invoke-ProjectGit -GitArguments @('merge','--ff-only',$expectedCommit)
$actualCommit = (@(Invoke-ProjectGit -GitArguments @('rev-parse','HEAD')) -join "`n").Trim()
if ($actualCommit -ne $expectedCommit) { throw 'Unexpected source version; startup stopped.' }
if ($privateHashBefore -and (Get-FileHash -LiteralPath $privateFile -Algorithm SHA256).Hash -ne $privateHashBefore) {
    throw 'Private configuration changed unexpectedly; startup stopped.'
}
Write-Host "Verified source commit: $actualCommit"
if ($UpdateOnly) {
    Write-Host 'Source update complete. Containers were not started.'
    return
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $launcher -Action Start
if ($LASTEXITCODE -ne 0) {
    throw 'Source update succeeded, but Start did not complete. Retain data and keys; report the failed step only.'
}
if ($privateHashBefore -and (Get-FileHash -LiteralPath $privateFile -Algorithm SHA256).Hash -ne $privateHashBefore) {
    throw 'The original private configuration changed during Start. Retain all files and report this check.'
}
Write-Host 'Update and Start completed. Use the localhost URL printed by the original launcher.'
Write-Host 'In a private terminal, use scripts/laptop.ps1 -Action Credentials for the existing test accounts.'
Write-Host 'Use synthetic files only. This baseline excludes local A1 and Document Reader development.'
