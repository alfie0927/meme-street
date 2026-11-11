<#
Copies the reels that went out on Instagram from the reel server to this computer, each with its caption, so they can be
posted by hand on TikTok, YouTube Shorts, X and the rest (growth/social.md). Only reads from the server.

  powershell -ExecutionPolicy Bypass -File tools\fetch_reels.ps1              the last 2 days, into D:\memestreet_reels
  powershell -ExecutionPolicy Bypass -File tools\fetch_reels.ps1 -Days 7
#>
param([int]$Days = 2, [string]$To = "D:\memestreet_reels", [string]$Server = "root@65.109.233.145")
$ErrorActionPreference = "Stop"
$dir = "/opt/memestreet-daily-reel"   # (the Daily in out/<date>, the other seven a day in queue/<slot>)
# the posted reels only (posted.json), newest first; a Trial Reel never reached the grid, so it is left out
$list = ssh -o BatchMode=yes $Server "cd $dir && find out queue -maxdepth 2 -name posted.json -newermt '-$Days days' | grep -v trial- | xargs -r -n1 dirname | sort -t/ -k2 -r"
if (-not $list) { Write-Host "No posted reels in the last $Days days."; return }
foreach ($d in $list) {
    $name = $d
    $out = Join-Path $To ($name -replace "^(out|queue)/", "")
    if (Test-Path (Join-Path $out "reel.mp4")) { continue }
    New-Item -ItemType Directory -Force $out | Out-Null
    scp -q -o BatchMode=yes "${Server}:$dir/$name/reel.mp4" "${Server}:$dir/$name/caption.txt" $out
    Write-Host "copied $name"
}
Write-Host "Done. The reels are in $To, newest first; each folder has reel.mp4 and caption.txt."
