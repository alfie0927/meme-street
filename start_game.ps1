# Starts Meme Street on this computer, at http://127.0.0.1:8000. Run it from anywhere:
#     powershell -File D:\stock_market_sim\start_game.ps1
#     powershell -File D:\stock_market_sim\start_game.ps1 -Fresh          (a new game; the old save is kept in data\backups\)
#     powershell -File D:\stock_market_sim\start_game.ps1 -Payments off   (the shop shows prices and sells nothing)
# The save, the charts and the ledger are in data\ (never sent to git), and so is the admin page's key: data\admin_key.txt
# (made on the first run).
# The shop runs in TEST mode here by default: "Pay (test)" completes a purchase without any money (payments.py).
# To stop the game press Ctrl+C in this window. To share it with others, run `python tools\share.py` in a second window
# (start with -Payments off first: in test mode anyone could give themselves MB).
param([switch]$Fresh, [ValidateSet("test", "off")][string]$Payments = "test")
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
$data = Join-Path $here "data"
New-Item -ItemType Directory -Force $data | Out-Null
$keyFile = Join-Path $data "admin_key.txt"
if (-not (Test-Path $keyFile)) {
    $bytes = New-Object byte[] 24
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    Set-Content -Path $keyFile -Value (($bytes | ForEach-Object { $_.ToString("x2") }) -join "") -NoNewline -Encoding ascii
}
if ($Fresh) {
    $save = @("state.json", "state.charts.json", "ledger.db", "ledger.db-wal", "ledger.db-shm") | Where-Object { Test-Path (Join-Path $data $_) }
    if ($save) {
        $dest = Join-Path $data ("backups\before_fresh_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
        New-Item -ItemType Directory -Force $dest | Out-Null
        foreach ($f in $save) { Move-Item -Path (Join-Path $data $f) -Destination $dest }
        Write-Host "The old game was moved to $dest (move the files back to return to it)."
    }
}
$env:ADMIN_KEY = (Get-Content $keyFile -Raw).Trim()
$env:PAYMENTS = $Payments
Write-Host "Meme Street is starting at http://127.0.0.1:8000  (admin page: /admin, the key is in data\admin_key.txt)"
if ($Payments -eq "test") { Write-Host "The shop is in TEST mode: purchases are pretend and no money is taken." }
& (Join-Path $here ".venv\Scripts\python.exe") -m uvicorn server:app --app-dir (Join-Path $here "game") --host 127.0.0.1 --port 8000
