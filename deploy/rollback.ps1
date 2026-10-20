<#
Undoes the last upload: the server goes back to the code it ran before it, and the game restarts (ROADMAP O5).

  powershell -File deploy\rollback.ps1 -Server root@YOUR.SERVER.IP             back to the code before the last upload
  powershell -File deploy\rollback.ps1 -Server root@YOUR.SERVER.IP -List       the saved releases, newest first
  powershell -File deploy\rollback.ps1 -Server root@YOUR.SERVER.IP -Release 20261019-203000

Every upload.ps1 run saves the code it replaces on the server (the five newest are kept). Only the code goes back: the
save, the ledger and the backups stay as they are. Running it again goes one more release back.
#>
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [string]$Release = "",
    [switch]$List
)
$ErrorActionPreference = "Stop"
$arg = if ($List) { "--list" } else { $Release }
# (from a copy in /tmp: the rollback replaces the deploy folder that rollback.sh itself lives in)
ssh $Server "cp /opt/memestreet/deploy/rollback.sh /tmp/memestreet-rollback.sh && bash /tmp/memestreet-rollback.sh $arg; s=`$?; rm -f /tmp/memestreet-rollback.sh; exit `$s"
if ($LASTEXITCODE -ne 0) { throw "The rollback did not finish (see the messages above)." }
