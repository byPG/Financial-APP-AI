<#
.SYNOPSIS
  Build (if needed) and run the Finance App Docker container on Windows.

.DESCRIPTION
  See planning/PLAN.md Section 11. Idempotent: safe to run again while the
  container is already running -- it detects the existing container and
  leaves it running rather than erroring.

.PARAMETER Build
  Force a rebuild of the Docker image even if it already exists.

.EXAMPLE
  ./scripts/start_windows.ps1
  ./scripts/start_windows.ps1 -Build
#>

param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"

$ImageName = "finance-app"
$ContainerName = "finance-app"
$Port = 8000

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Set-Location $ProjectRoot

if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    Write-Warning ".env not found in project root. Copy .env.example to .env and fill in OPENROUTER_API_KEY."
}

$DbDir = Join-Path $ProjectRoot "db"
if (-not (Test-Path $DbDir)) {
    New-Item -ItemType Directory -Force -Path $DbDir | Out-Null
}

# Build the image if it doesn't exist yet, or if -Build was passed.
$imageExists = $true
try {
    docker image inspect $ImageName *> $null
} catch {
    $imageExists = $false
}
if (-not $?) { $imageExists = $false }

if ($Build -or -not $imageExists) {
    Write-Output "Building Docker image '$ImageName'..."
    docker build -t $ImageName -f Dockerfile .
    if (-not $?) { throw "docker build failed" }
} else {
    Write-Output "Image '$ImageName' already exists, skipping build (use -Build to force)."
}

# Idempotent container handling: if a container with this name is already
# running, leave it alone. If it exists but is stopped, remove it so we can
# start fresh. If it doesn't exist, just run it.
$state = $null
try {
    $state = docker inspect -f "{{.State.Running}}" $ContainerName 2>$null
} catch {
    $state = $null
}

if ($state -eq "true") {
    Write-Output "Container '$ContainerName' is already running."
} else {
    if ($null -ne $state) {
        Write-Output "Removing stopped container '$ContainerName'..."
        docker rm $ContainerName *> $null
    }
    Write-Output "Starting container '$ContainerName'..."
    docker run -d `
        --name $ContainerName `
        -p "${Port}:8000" `
        -v "${ProjectRoot}\db:/app/db" `
        --env-file "${ProjectRoot}\.env" `
        $ImageName
    if (-not $?) { throw "docker run failed" }
}

$Url = "http://localhost:$Port"
Write-Output "Finance App is available at $Url"

# Best-effort browser open; never fail the script if it can't open a browser.
try {
    Start-Process $Url | Out-Null
} catch {
    # Ignore -- browser launch is best-effort only.
}
