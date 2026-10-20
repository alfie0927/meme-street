<#
Sets up (or updates) a Windows scheduled task that copies the newest server backups to this computer every day, with
deploy\pull_backups.ps1 (ROADMAP O2). Run it once:

  powershell -ExecutionPolicy Bypass -File deploy\schedule_backups.ps1 -Server root@YOUR.SERVER.IP

  -Server   who to log in as and where (the same as for upload.ps1; the ssh key must work without a password)
  -At       the time of day to run (default 09:00). If the computer is off or asleep then, it runs as soon as it can.
  -To       where the backups go (default D:\meme_street_backups); a log of every run is kept there in pull.log
  -Remove   delete the task instead

The task runs as you, only while you are logged in (it needs your ssh key), and shows no window.
#>
param(
    [string]$Server = "",
    [string]$At = "09:00",
    [string]$To = "D:\meme_street_backups",
    [switch]$Remove
)
$ErrorActionPreference = "Stop"
$name = "Meme Street backups"
if ($Remove) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
    Write-Host "The task '$name' was removed."
    return
}
if (-not $Server) { throw "Give the server: -Server root@YOUR.SERVER.IP" }
$script = Join-Path $PSScriptRoot "pull_backups.ps1"
New-Item -ItemType Directory -Force -Path $To | Out-Null
$log = Join-Path $To "pull.log"
$command = "& { '--- ' + (Get-Date -Format o); & '$script' -Server '$Server' -To '$To' } *>> '$log'"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command `"$command`""
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) -RunOnlyIfNetworkAvailable
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Force `
    -Description "Copies the newest Meme Street server backups to $To (deploy\pull_backups.ps1)." | Out-Null
Write-Host "The task '$name' runs every day at $At (or as soon as the computer is on after that). Log: $log"
