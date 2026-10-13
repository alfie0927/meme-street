# Starts Meme Street on this computer, at http://127.0.0.1:8000. Run it from anywhere:
#     powershell -File D:\stock_market_sim\start_game.ps1
#     powershell -File D:\stock_market_sim\start_game.ps1 -Fresh          (a new game; the old save is kept in backups\)
#     powershell -File D:\stock_market_sim\start_game.ps1 -Payments off   (the shop shows prices and sells nothing)
# The admin page's key is kept in admin_key.txt next to this file (made on the first run, never sent to git).
# The shop runs in TEST mode here by default: "Pay (test)" completes a purchase without any money (payments.py).
# To stop the game press Ctrl+C in this window. To share it with others, run `python share.py` in a second window
# (start with -Payments off first: in test mode anyone could give themselves MB).
param([switch]$Fresh, [ValidateSet("test", "off")][string]$Payments = "test")
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
$keyFile = Join-Path $here "admin_key.txt"
if (-not (Test-Path $keyFile)) {
    $bytes = New-Object byte[] 24
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    Set-Content -Path $keyFile -Value (($bytes | ForEach-Object { $_.ToString("x2") }) -join "") -NoNewline -Encoding ascii
}
if ($Fresh) {
    $save = @("state.json", "state.charts.json", "ledger.db", "ledger.db-wal", "ledger.db-shm") | Where-Object { Test-Path (Join-Path $here $_) }
    if ($save) {
        $dest = Join-Path $here ("backups\before_fresh_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
        New-Item -ItemType Directory -Force $dest | Out-Null
        foreach ($f in $save) { Move-Item -Path (Join-Path $here $f) -Destination $dest }
        Write-Host "The old game was moved to $dest (move the files back to return to it)."
    }
}
$env:ADMIN_KEY = (Get-Content $keyFile -Raw).Trim()
$env:PAYMENTS = $Payments
Write-Host "Meme Street is starting at http://127.0.0.1:8000  (admin page: /admin, the key is in admin_key.txt)"
if ($Payments -eq "test") { Write-Host "The shop is in TEST mode: purchases are pretend and no money is taken." }
& (Join-Path $here ".venv\Scripts\python.exe") -m uvicorn server:app --host 127.0.0.1 --port 8000
