<#
Sends the game's code from this computer to the server (and restarts it), so you can update the live game with one command.

  First time:   powershell -File deploy\upload.ps1 -Server root@YOUR.SERVER.IP
                then, on the server:  bash /opt/memestreet/deploy/setup_server.sh yourdomain.com
  Every update: powershell -File deploy\upload.ps1 -Server root@YOUR.SERVER.IP -Restart

  -Server     who to log in as and where (root@1.2.3.4, or root@yourdomain.com once the DNS is set)
  -Restart    restart the game after sending the code (the game saves itself on the way down; players reconnect by
              themselves within a few seconds)
  -DryRun     only build the archive and show what would be sent; contacts nothing
  -WithGame   also copy THIS computer's saved game (state.json, the charts, the ledger) to the server: use it once, to
              move the game you have been running here. Stop the game on this computer first; this refuses if it is
              still running. It stops the server's game while the files are copied.

What is sent: the Python files, the HTML pages, the content packs (the .json files) and the logo, and the deploy folder.
Never sent (unless -WithGame): saves, the ledger, backups, tests, the virtual environment, results of simulations.
It needs the ssh and scp programs that come with Windows 10 and 11 (Settings > Apps > Optional features > OpenSSH Client).
#>
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [switch]$Restart,
    [switch]$WithGame,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

foreach ($tool in "ssh", "scp") {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "Missing the '$tool' program. Install the Windows OpenSSH Client (Settings > Apps > Optional features)."
    }
}
# Windows' own tar (other tars on the PATH, such as the one that comes with Git, read "C:" as a remote computer)
$tar = Join-Path $env:SystemRoot "System32\tar.exe"
if (-not (Test-Path $tar)) { $tar = "tar" }

if ($WithGame) {
    $listening = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if ($listening) {
        throw "The game is still running on this computer (port 8000). Stop it with Ctrl+C first: its saves must not change while they are copied."
    }
}

# --- the code
$files = @()
$files += Get-ChildItem -File -Include *.py, *.html, requirements.txt -Path (Join-Path $root "*") | ForEach-Object { $_.Name }
$files += Get-ChildItem -File -Filter *.json | Where-Object { $_.Name -notlike "state*.json" } | ForEach-Object { $_.Name }
foreach ($logo in "brand/memestreet_logo_peaks.png", "brand/memestreet_header_peaks.png", "memestreet_logo_peaks.png", "memestreet_header_peaks.png") {
    if (Test-Path $logo) { $files += $logo }
}
$files += Get-ChildItem -File -Path "deploy" | ForEach-Object { "deploy/" + $_.Name }
$files = $files | Sort-Object -Unique
Write-Host ("Sending {0} files to {1}" -f $files.Count, $Server)

$tmp = Join-Path $env:TEMP "memestreet-upload"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$list = Join-Path $tmp "files.txt"
[System.IO.File]::WriteAllText($list, (($files -join "`n") + "`n"))
$archive = Join-Path $tmp "code.tgz"
& $tar -czf $archive -T $list
if ($DryRun) {
    Write-Host ("Archive built: {0} ({1:N0} bytes). Files:" -f $archive, (Get-Item $archive).Length)
    $files | ForEach-Object { Write-Host "  $_" }
    Remove-Item -Recurse -Force $tmp
    return
}
scp $archive "${Server}:/tmp/memestreet-code.tgz"

$remote = "mkdir -p /opt/memestreet && tar -xzf /tmp/memestreet-code.tgz -C /opt/memestreet && rm /tmp/memestreet-code.tgz"
$remote += " && sed -i 's/\r$//' /opt/memestreet/deploy/*"          # (files made on Windows may have Windows line endings: scripts need Linux ones)
$remote += " && (id memestreet >/dev/null 2>&1 && chown -R memestreet:memestreet /opt/memestreet || true)"
ssh $Server $remote

# --- the saved game (once, to move it here)
if ($WithGame) {
    $game = @()
    foreach ($f in "state.json", "state.charts.json", "ledger.db", "ledger.db-wal", "ledger.db-shm") {
        if (Test-Path $f) { $game += $f }
    }
    if ($game.Count -eq 0) { throw "There is no saved game (state.json) in this folder." }
    Write-Host ("Copying the saved game: " + ($game -join ", "))
    $glist = Join-Path $tmp "game.txt"
    [System.IO.File]::WriteAllText($glist, (($game -join "`n") + "`n"))
    $garchive = Join-Path $tmp "game.tgz"
    & $tar -czf $garchive -T $glist
    scp $garchive "${Server}:/tmp/memestreet-game.tgz"
    $remote = "systemctl stop memestreet-gateway memestreet 2>/dev/null; "
    $remote += "cd /opt/memestreet && rm -f state.json state.charts.json ledger.db ledger.db-wal ledger.db-shm && tar -xzf /tmp/memestreet-game.tgz && rm /tmp/memestreet-game.tgz; "
    $remote += "id memestreet >/dev/null 2>&1 && chown -R memestreet:memestreet /opt/memestreet; "
    $remote += "systemctl start memestreet 2>/dev/null; sleep 5; systemctl start memestreet-gateway 2>/dev/null; true"
    ssh $Server $remote
}
elseif ($Restart) {
    ssh $Server "systemctl restart memestreet && sleep 5 && systemctl restart memestreet-gateway"
}

Remove-Item -Recurse -Force $tmp
Write-Host "Done."
