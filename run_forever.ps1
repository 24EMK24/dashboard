# run_forever.ps1 — keeps the dashboard up to date on its own.
#
# What it does: every 30 minutes it re-runs main.py, which rebuilds dashboard.html
# with the latest weather, stocks, YouTube, and news. Your open browser tab reloads
# itself on the same 30-minute schedule (see template.html), so you never have to
# re-run anything by hand.
#
# How to use it:
#   * Double-click this file (or right-click -> "Run with PowerShell").
#   * A window opens and stays open — LEAVE IT OPEN. It only keeps updating while the
#     window is running. Close the window to stop.
#
# Note: stocks and YouTube are cached for 15 minutes, so running every 30 minutes is
# plenty — a faster loop would just re-serve the same cached data.

# How long to wait between rebuilds, in minutes. Change this one number if you want a
# different cadence (don't go below ~15 — that's the cache window).
$MINUTES = 30

# Work from THIS script's own folder (the project root), so the relative paths inside
# main.py — config.json, cache/, dashboard.html — all resolve correctly no matter where
# the script was launched from.
Set-Location -Path $PSScriptRoot

# Prefer the project's virtual-environment Python if it exists; otherwise fall back to
# whatever "python" is on the PATH. (AGENTS.md documents the venv at .venv\Scripts.)
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = "python"
}

Write-Host "Dashboard auto-updater started. Rebuilding every $MINUTES minutes."
Write-Host "Leave this window open. Close it to stop." -ForegroundColor Yellow
Write-Host ""

# The loop: rebuild, wait, repeat — forever, until the window is closed.
while ($true) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$stamp] Rebuilding dashboard..."

    # Run the build. Wrapped so that if one run fails (e.g. the internet blips), the
    # loop prints the error and keeps going instead of dying — the same fail-soft spirit
    # the panels use.
    try {
        & $python main.py
        Write-Host "[$stamp] Done. Next rebuild in $MINUTES minutes." -ForegroundColor Green
    } catch {
        Write-Host "[$stamp] Build failed: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "[$stamp] Will try again in $MINUTES minutes." -ForegroundColor Red
    }

    Write-Host ""
    Start-Sleep -Seconds ($MINUTES * 60)
}
