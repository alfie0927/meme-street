# Starts Meme Street on this computer, at http://127.0.0.1:8000. Run it from anywhere:
#     powershell -File D:\stock_market_sim\start_game.ps1
# The admin page's key is kept in admin_key.txt next to this file (made on the first run, never sent to git).
# To stop the game press Ctrl+C in this window. To share it with others, run `python share.py` in a second window.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
$keyFile = Join-Path $here "admin_key.txt"
if (-not (Test-Path $keyFile)) {
    $bytes = New-Object byte[] 24
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    Set-Content -Path $keyFile -Value (($bytes | ForEach-Object { $_.ToString("x2") }) -join "") -NoNewline -Encoding ascii
}
$env:ADMIN_KEY = (Get-Content $keyFile -Raw).Trim()
Write-Host "Meme Street is starting at http://127.0.0.1:8000  (admin page: /admin, the key is in admin_key.txt)"
& (Join-Path $here ".venv\Scripts\python.exe") -m uvicorn server:app --host 127.0.0.1 --port 8000
