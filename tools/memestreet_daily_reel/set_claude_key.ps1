<#
Gives the reel generator on the server an Anthropic API key (it writes each reel's script with Claude), without the key
ever being typed into a chat or onto a command line: it asks for it here, hidden, and sends it inside the ssh connection.

  powershell -ExecutionPolicy Bypass -File tools\memestreet_daily_reel\set_claude_key.ps1 -Server root@65.109.233.145

Make the key at console.anthropic.com (Settings > API keys); it starts with sk-ant-. It goes into the reel tool's private
config.env on the server (chmod 600), replacing any key there before.
#>
param([Parameter(Mandatory = $true)][string]$Server)

$ErrorActionPreference = "Stop"
$secret = Read-Host "Anthropic API key (hidden)" -AsSecureString
$key = [System.Net.NetworkCredential]::new("", $secret).Password
if ($key -notmatch "^sk-ant-[A-Za-z0-9_-]+$") { throw "That does not look like an Anthropic API key (sk-ant-...)." }

$script = @"
set -e
f=/opt/memestreet-daily-reel/config.env
sed -i '/^ANTHROPIC_API_KEY=/d' `$f
echo 'ANTHROPIC_API_KEY=$key' >> `$f
chmod 600 `$f
echo done
"@
($script -replace "`r", "") | ssh $Server "bash -s"
if ($LASTEXITCODE -ne 0) { throw "The server did not accept the key." }
Write-Host "Key saved on the server."
