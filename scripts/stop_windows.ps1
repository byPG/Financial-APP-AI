<#
.SYNOPSIS
  Stop and remove the Finance App Docker container on Windows.

.DESCRIPTION
  Does NOT remove the bind-mounted db/ data -- that persists on the host.
  See planning/PLAN.md Section 11. Idempotent: safe to run when nothing is
  running.
#>

$ContainerName = "finance-app"

$exists = $true
try {
    docker inspect $ContainerName *> $null
} catch {
    $exists = $false
}
if (-not $?) { $exists = $false }

if ($exists) {
    Write-Output "Stopping container '$ContainerName'..."
    docker stop $ContainerName *> $null
    Write-Output "Removing container '$ContainerName'..."
    docker rm $ContainerName *> $null
    Write-Output "Container '$ContainerName' stopped and removed. Data in db/ is preserved."
} else {
    Write-Output "Container '$ContainerName' is not present. Nothing to do."
}
