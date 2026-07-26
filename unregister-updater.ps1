# unregister-updater.ps1 — removes the background dashboard-updater task.
# Run this if you ever want to stop the automatic rebuilds.
#   Right-click -> "Run with PowerShell".

$TaskName = "EliDashboardUpdate"

# -ErrorAction Stop so we can tell you clearly whether it was there or not.
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
    Write-Host "Removed the background task '$TaskName'. Automatic rebuilds are off." -ForegroundColor Green
} catch {
    Write-Host "No task named '$TaskName' was found (nothing to remove)." -ForegroundColor Yellow
}
