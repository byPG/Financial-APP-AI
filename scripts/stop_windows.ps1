<#
.SYNOPSIS
  Stop and remove the Finance App Docker container on Windows.

.DESCRIPTION
  Does NOT remove the bind-mounted db/ data -- that persists on the host.
  See planning/PLAN.md Section 11. Idempotent: safe to run when nothing is
  running.
#>

$ContainerName = "finance-app"

# Scoped to --type container: a plain `docker inspect $ContainerName` is
# ambiguous with an image of the same name (finance-app:latest, built by
# start_windows.ps1) and would report "exists" from the image match even
# with no container present, breaking idempotency on a second run.
$exists = $true
try {
    docker inspect --type container $ContainerName *> $null
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

# The existence check above is expected to fail (non-zero $LASTEXITCODE)
# exactly when there's nothing to do -- without this, that expected
# failure leaks out as this script's own exit code, making a successful
# idempotent no-op run look like a failure to any caller checking it.
exit 0
