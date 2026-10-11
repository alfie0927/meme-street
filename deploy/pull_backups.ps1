<#
Copies the newest server backups to this computer, so that losing the server does not lose the backups with it.

  powershell -File deploy\pull_backups.ps1 -Server root@YOUR.SERVER.IP
  powershell -File deploy\pull_backups.ps1 -Server root@YOUR.SERVER.IP -To D:\meme_street_backups -Newest 8

  -Server   who to log in as and where (the same as for upload.ps1)
  -To       the folder on this computer that receives them (default D:\meme_street_backups)
  -Newest   how many of the server's newest backups to look at (default 4: the server makes one every six hours, so four is
            one day). A backup that is already here is skipped, so running it every day only fetches what is new.

Each backup is a folder with the save (state.json), the charts and the money ledger (ledger.db), about 40 MB. A copy is only
marked complete (a file called .complete inside it) after the save and the ledger arrived with a size above zero, so a
download that was cut off is fetched again next time. Nothing on the server is changed or deleted. Old copies here are
never deleted: remove the oldest by hand now and then.
It needs the ssh and scp programs that come with Windows 10 and 11.
#>
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [string]$To = "D:\meme_street_backups",
    [int]$Newest = 4
)

$ErrorActionPreference = "Stop"
$remote = "/var/backups/memestreet"
New-Item -ItemType Directory -Force -Path $To | Out-Null

$names = (ssh $Server "ls -1 $remote | sort | tail -n $Newest") -split "\r?\n" | Where-Object { $_.Trim() -ne "" }
if (-not $names) { throw "The server has no backups in $remote (is the backup job running? see deploy/DEPLOY.md)." }

$fetched = 0
foreach ($raw in $names) {
    $n = $raw.Trim()
    $dir = Join-Path $To $n
    if (Test-Path (Join-Path $dir ".complete")) { continue }
    if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }          # a half-fetched copy from an earlier run
    scp -r "${Server}:$remote/$n" $To
    if ($LASTEXITCODE -ne 0) { throw "Could not copy $n from the server." }
    foreach ($f in "state.json", "ledger.db") {
        $p = Join-Path $dir $f
        if (-not (Test-Path $p) -or (Get-Item $p).Length -eq 0) { throw "$n arrived without a usable $f." }
    }
    Set-Content -Path (Join-Path $dir ".complete") -Value (Get-Date -Format "o")
    $fetched++
    Write-Host "fetched $n"
}
$have = @(Get-ChildItem $To -Directory | Where-Object { Test-Path (Join-Path $_.FullName ".complete") }).Count
Write-Host ("{0} new backup(s) copied. {1} complete backup(s) are now in {2}." -f $fetched, $have, $To)
