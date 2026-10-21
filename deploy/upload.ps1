<#
Sends the game's code from this computer to the server (and restarts it), so you can update the live game with one command.

  First time:   powershell -File deploy\upload.ps1 -Server root@YOUR.SERVER.IP
                then, on the server:  bash /opt/memestreet/deploy/setup_server.sh yourdomain.com
  Every update: powershell -File deploy\upload.ps1 -Server root@YOUR.SERVER.IP -Restart

  -Server     who to log in as and where (root@1.2.3.4, or root@yourdomain.com once the DNS is set)
  -Restart    restart the game after sending the code (the game saves itself on the way down; players reconnect by
              themselves within a few seconds)
  -DryRun     only build the archive and show what would be sent; contacts nothing
  -WithGame   also copy THIS computer's saved game (data\state.json, the charts, the ledger) to the server: use it once,
              to move the game you have been running here. Stop the game on this computer first; this refuses if it is
              still running. It stops the server's game while the files are copied.
  -Staging    send the code to the staging copy instead of the live game (/opt/memestreet-staging, port 8100 on the
              server, ROADMAP O5), start it with a copy of the newest live backup, and open a tunnel so that
              http://127.0.0.1:8100 on this computer shows it. Ctrl+C closes the tunnel; the staging copy keeps running.
  -Fresh      with -Staging: give the staging copy the newest live backup again (otherwise it keeps its own save)
  -StopStaging  stop the staging copy (it does not start by itself when the server reboots)

Every live upload first saves the code it is about to replace in /opt/memestreet-releases (the five newest are kept), so
deploy\rollback.ps1 can put it back with one command.

What is sent: the code (game\), the pages (web\), the content packs (content\), the scripts (tools\, without the
downloaded tunnel program), the logo and the deploy folder. On an installed server deploy/update_server.sh then runs: it
installs changed service files and the backup job, moves a game from the old one-folder layout into data/, and restarts
the game when asked (or when it had to).
Never sent (unless -WithGame): data\ (saves, the ledger, backups, keys), tests, the virtual environment.
It needs the ssh and scp programs that come with Windows 10 and 11 (Settings > Apps > Optional features > OpenSSH Client).
#>
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [switch]$Restart,
    [switch]$WithGame,
    [switch]$DryRun,
    [switch]$Staging,
    [switch]$Fresh,
    [switch]$StopStaging
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

if ($StopStaging) {
    ssh $Server "systemctl stop memestreet-staging"
    Write-Host "The staging copy was stopped."
    return
}
if ($Staging -and $WithGame) { throw "-WithGame is for the live game only." }

if ($WithGame) {
    $listening = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if ($listening) {
        throw "The game is still running on this computer (port 8000). Stop it with Ctrl+C first: its saves must not change while they are copied."
    }
}

# --- the code
$files = @("requirements.txt")
foreach ($part in @(@("game", "*.py"), @("web", "*.html"), @("web", "*.js"), @("content", "*.json"), @("tools", "*.py"), @("deploy", "*"))) {
    $files += Get-ChildItem -File -Path $part[0] -Filter $part[1] | ForEach-Object { $part[0] + "/" + $_.Name }
}
foreach ($logo in "brand/memestreet_logo_peaks.png", "brand/memestreet_header_peaks.png") {
    if (Test-Path $logo) { $files += $logo }
}
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

if ($Staging) {
    $app = "/opt/memestreet-staging"
    $remote = "mkdir -p $app && tar -xzf /tmp/memestreet-code.tgz -C $app && rm /tmp/memestreet-code.tgz && sed -i 's/\r$//' $app/deploy/*"
    $remote += " && bash $app/deploy/staging_server.sh" + $(if ($Fresh) { " fresh" } else { "" })
    ssh $Server $remote
    if ($LASTEXITCODE -ne 0) { throw "The staging copy did not start (see the messages above)." }
    Remove-Item -Recurse -Force $tmp
    Write-Host "Open http://127.0.0.1:8100 in your browser. Press Ctrl+C here to close the tunnel (the staging copy keeps running;"
    Write-Host "stop it with: powershell -File deploy\upload.ps1 -Server $Server -StopStaging)."
    ssh -N -L 8100:127.0.0.1:8100 $Server
    return
}

$installed = (ssh $Server "test -f /etc/systemd/system/memestreet.service && echo yes || echo no") -eq "yes"
# the code that is about to be replaced is kept for deploy\rollback.ps1 (the five newest)
$keep = 'mkdir -p /opt/memestreet-releases && if [ -d /opt/memestreet/game ]; then tar -czf /opt/memestreet-releases/$(date -u +%Y%m%d-%H%M%S).tgz -C /opt/memestreet --ignore-failed-read game web content tools deploy brand requirements.txt 2>/dev/null || true; fi; ls -1t /opt/memestreet-releases/*.tgz 2>/dev/null | tail -n +6 | xargs -r rm -f --; '
$remote = $keep + "mkdir -p /opt/memestreet && tar -xzf /tmp/memestreet-code.tgz -C /opt/memestreet && rm /tmp/memestreet-code.tgz"
$remote += " && sed -i 's/\r$//' /opt/memestreet/deploy/*"          # (files made on Windows may have Windows line endings: scripts need Linux ones)
if ($installed -and -not $WithGame) {
    $remote += " && bash /opt/memestreet/deploy/update_server.sh" + $(if ($Restart) { " restart" } else { "" })
}
else {
    $remote += " && (id memestreet >/dev/null 2>&1 && chown -R memestreet:memestreet /opt/memestreet || true)"
}
ssh $Server $remote
if ($LASTEXITCODE -ne 0) { throw "The server did not finish the update (see the messages above)." }

# --- the saved game (once, to move it here)
if ($WithGame) {
    $game = @()
    foreach ($f in "state.json", "state.charts.json", "ledger.db", "ledger.db-wal", "ledger.db-shm", "history.db", "history.db-wal", "history.db-shm") {
        if (Test-Path "data/$f") { $game += "data/$f" }
    }
    if ($game.Count -eq 0) { throw "There is no saved game (data\state.json) on this computer." }
    Write-Host ("Copying the saved game: " + ($game -join ", "))
    $glist = Join-Path $tmp "game.txt"
    [System.IO.File]::WriteAllText($glist, (($game -join "`n") + "`n"))
    $garchive = Join-Path $tmp "game.tgz"
    & $tar -czf $garchive -T $glist
    scp $garchive "${Server}:/tmp/memestreet-game.tgz"
    $remote = "systemctl stop memestreet-gateway memestreet 2>/dev/null; cd /opt/memestreet && "
    $remote += "rm -f state.json state.charts.json ledger.db ledger.db-wal ledger.db-shm data/state.json data/state.charts.json data/ledger.db data/ledger.db-wal data/ledger.db-shm data/history.db* data/minutes.db* && "
    $remote += "tar -xzf /tmp/memestreet-game.tgz && rm /tmp/memestreet-game.tgz; "
    if ($installed) { $remote += "bash /opt/memestreet/deploy/update_server.sh; " }
    $remote += "id memestreet >/dev/null 2>&1 && chown -R memestreet:memestreet /opt/memestreet; "
    $remote += "systemctl start memestreet 2>/dev/null; sleep 5; systemctl start memestreet-gateway 2>/dev/null; true"
    ssh $Server $remote
}
elseif ($Restart -and -not $installed) {
    ssh $Server "systemctl restart memestreet && sleep 5 && systemctl restart memestreet-gateway"
}

Remove-Item -Recurse -Force $tmp
Write-Host "Done."
