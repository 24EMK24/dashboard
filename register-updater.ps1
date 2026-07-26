# register-updater.ps1 — installs a background Windows Scheduled Task that keeps the
# dashboard up to date on its own. Run this ONCE. After that Windows handles everything:
# every 30 minutes it quietly re-runs main.py (no window, using the windowless
# pythonw.exe), it starts when you log in, and it survives reboots.
#
# How to run it (once):
#   Right-click this file -> "Run with PowerShell".
# To remove it later, run unregister-updater.ps1 (sitting next to this file).
#
# This installs a task for YOUR user only and needs NO admin rights and NO stored
# password — it just runs while you're logged in, which is all the dashboard needs.

$TaskName = "EliDashboardUpdate"
$Minutes  = 30                       # rebuild cadence (matches the 15-min cache; don't go lower)

# Absolute paths, worked out from where this script lives (the project root).
$projectRoot = $PSScriptRoot
$pythonw     = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"   # windowless Python

# Safety check: make sure the venv Python is actually there before we register anything.
if (-not (Test-Path $pythonw)) {
    Write-Host "Could not find $pythonw" -ForegroundColor Red
    Write-Host "Create the virtual environment first (see AGENTS.md), then re-run this." -ForegroundColor Red
    exit 1
}

# WHAT to run: pythonw.exe main.py, started from the project root so config.json / cache/
# / dashboard.html all resolve (main.py uses relative paths).
$action = New-ScheduledTaskAction -Execute $pythonw -Argument "main.py" -WorkingDirectory $projectRoot

# WHEN to run:
#   1) A daily trigger that then repeats every 30 minutes for the whole day (so it fires
#      all day long, every day).
#   2) Also right after you log on, so a fresh build appears promptly after a reboot
#      instead of waiting up to 30 minutes.
$daily = New-ScheduledTaskTrigger -Daily -At 12:00AM
$daily.Repetition = (New-ScheduledTaskTrigger -Once -At 12:00AM `
    -RepetitionInterval (New-TimeSpan -Minutes $Minutes) `
    -RepetitionDuration (New-TimeSpan -Hours 24)).Repetition
$logon = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERNAME"

# HOW it behaves: catch up a missed run if the laptop was asleep, run on battery, and if
# a build somehow overruns, skip the new start rather than stacking copies. Give each run
# a 1-hour cap so nothing can hang forever.
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# WHO it runs as: you, only while logged on — no admin, no saved password.
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Limited

# Register it (‑Force replaces any earlier copy, so re-running this is safe).
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($daily, $logon) `
    -Settings $settings -Principal $principal `
    -Description "Rebuilds Eli's dashboard.html every $Minutes minutes via main.py." `
    -Force | Out-Null

Write-Host "Installed the background task '$TaskName'." -ForegroundColor Green
Write-Host "It rebuilds the dashboard every $Minutes minutes, starting at login. No window needed."
Write-Host "Running one build now so you don't have to wait..."
Start-ScheduledTask -TaskName $TaskName
Write-Host "Done. Bookmark dashboard.html; it (and the task) stay current on their own." -ForegroundColor Green
