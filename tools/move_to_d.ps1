# Move one folder off C: and leave a link (a junction) at the old path, so every program still finds it there.
#   powershell -ExecutionPolicy Bypass -File tools\move_to_d.ps1 -From "C:\Users\me\.cache\huggingface" -To "D:\caches\huggingface"
# Safe to stop at any point: the old folder is only removed after the copy matched and the link works.
# If a program has a file in the folder open, the rename fails and nothing has changed: close the program and run it again.
param([Parameter(Mandatory)][string]$From, [Parameter(Mandatory)][string]$To)
$ErrorActionPreference = 'Stop'
$From = $From.TrimEnd('\'); $To = $To.TrimEnd('\'); $old = "$From.moved-to-d"
function Wipe($p) {                                   # (robocopy empties long paths that Remove-Item cannot)
  if (-not (Test-Path -LiteralPath $p)) { return }
  $e = Join-Path $env:TEMP "empty-$PID"; New-Item -ItemType Directory -Force -Path $e | Out-Null
  robocopy $e $p /MIR /R:1 /W:1 /NFL /NDL /NP /NJH /NJS | Out-Null
  Remove-Item -LiteralPath $p, $e -Recurse -Force
}
if (-not (Test-Path -LiteralPath $From)) { "nothing at $From"; exit 0 }
if ((Get-Item -LiteralPath $From -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { "already a link: $From"; exit 0 }
if (Test-Path -LiteralPath $To) { throw "$To already exists; choose another place or remove it first" }
$par = Split-Path $To; if (-not (Test-Path -LiteralPath $par)) { New-Item -ItemType Directory -Force -Path $par | Out-Null }   # (New-Item fails on a drive root)
robocopy $From $To /E /XJ /COPY:DAT /DCOPY:DAT /R:1 /W:1 /NFL /NDL /NP /NJH /NJS | Out-Null; $copy = $LASTEXITCODE
robocopy $From $To /E /XJ /L /NFL /NDL /NP /NJH /NJS | Out-Null                        # a second pass that only lists: 0 means the two match
if ($copy -ge 8 -or $LASTEXITCODE -ne 0) { Wipe $To; throw "the copy did not match (robocopy $copy, then $LASTEXITCODE); nothing was changed" }
try { Rename-Item -LiteralPath $From -NewName (Split-Path $old -Leaf) }
catch { Wipe $To; throw "a program has $From open; nothing was changed" }
cmd /c mklink /J "$From" "$To" | Out-Null
if (-not (Test-Path -LiteralPath $From)) { Rename-Item -LiteralPath $old -NewName (Split-Path $From -Leaf); Wipe $To; throw "the link could not be made; the folder is back where it was" }
$mb = ((Get-ChildItem -LiteralPath $To -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB)
Wipe $old
"moved {0} to {1} ({2:N0} MB); the old path is now a link" -f $From, $To, $mb
