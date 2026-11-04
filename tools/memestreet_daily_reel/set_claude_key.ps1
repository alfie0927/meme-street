<#
Lets the reel generator on the server write scripts with Claude, without the secret ever being typed into a chat or
onto a command line: it asks for it here, hidden, and sends it inside the ssh connection.

  powershell -ExecutionPolicy Bypass -File tools\memestreet_daily_reel\set_claude_key.ps1 -Server root@65.109.233.145

Either of two secrets:
  - your Claude plan (recommended: no separate bill). On this PC run   claude setup-token   , log in in the browser, and
    paste the token it prints (sk-ant-oat...). The server's Claude Code then uses your plan's usage.
  - an Anthropic API key (sk-ant-api...), billed to API credits at console.anthropic.com.
It goes into the reel tool's private config.env on the server (chmod 600), replacing the one there before.
#>
param([Parameter(Mandatory = $true)][string]$Server)

$ErrorActionPreference = "Stop"
$secret = Read-Host "Token from 'claude setup-token', or an API key (hidden)" -AsSecureString
$key = [System.Net.NetworkCredential]::new("", $secret).Password.Trim()
if ($key -match "^sk-ant-oat[A-Za-z0-9_-]+$") { $name = "CLAUDE_CODE_OAUTH_TOKEN"; $writer = "cli" }
elseif ($key -match "^sk-ant-[A-Za-z0-9_-]+$") { $name = "ANTHROPIC_API_KEY"; $writer = "api" }
else { throw "That is neither a Claude Code token (sk-ant-oat...) nor an API key (sk-ant-...)." }

$script = @"
set -e
f=/opt/memestreet-daily-reel/config.env
sed -i -E '/^(CLAUDE_CODE_OAUTH_TOKEN|ANTHROPIC_API_KEY|REEL_WRITER)=/d' `$f
printf '%s\n' '$name=$key' 'REEL_WRITER=$writer' >> `$f
chmod 600 `$f
echo done
"@
($script -replace "`r", "") | ssh $Server "bash -s"
if ($LASTEXITCODE -ne 0) { throw "The server did not accept it." }
Write-Host "Saved on the server ($name). Reels will be written with Claude from the next slot."
