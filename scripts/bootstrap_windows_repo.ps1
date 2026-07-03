param(
    [Parameter(Mandatory=$true)]
    [string]$RepoName,

    [ValidateSet("public", "private")]
    [string]$Visibility = "public"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git is not available on PATH."
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI 'gh' is not available on PATH."
}

if (-not (Test-Path .git)) {
    git init
    git branch -M main
}

git status --short

git add .
git commit -m "Initial Repo Cleanroom v0.1.0 scanner"

if ($Visibility -eq "public") {
    gh repo create $RepoName --public --source . --remote origin --push
} else {
    gh repo create $RepoName --private --source . --remote origin --push
}
