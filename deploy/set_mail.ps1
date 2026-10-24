<#
Gives the live server its mail settings (so verification codes and password recovery emails are really sent), without the
key ever being typed into a chat or onto a command line: it asks for it here, with the letters hidden, and sends it to the
server inside the ssh connection.

  powershell -ExecutionPolicy Bypass -File deploy\set_mail.ps1 -Server root@YOUR.SERVER.IP

First make an account at a mail service (Resend is the simplest: resend.com, a free plan covers a small game), add your
domain there and put the DNS records it shows you into your DNS (Cloudflare), then create an API key. For Resend the
answers below are: host smtp.resend.com, user resend, password = the API key, and a from-address on your domain such as
  Meme Street <no-reply@memestreet.net>
Any other SMTP service works the same way with the host, user and password it gives you.

What it does on the server: it replaces the SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD and MAIL_FROM lines in
/etc/memestreet.env and restarts the game (a few seconds; players reconnect by themselves). Then it asks the public
address whether the game now says mail is ready. With mail ready the game's email setting turns from off to optional by
itself: players are asked for an address and can recover a forgotten password with a code.
#>
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [string]$SmtpHost = "smtp.resend.com",
    [int]$SmtpPort = 587,
    [string]$Site = "https://memestreet.net"
)

$ErrorActionPreference = "Stop"
$user = Read-Host "SMTP user (for Resend: resend)"
$secret = Read-Host "SMTP password or API key (hidden)" -AsSecureString
$from = Read-Host "From address, for example: Meme Street <no-reply@memestreet.net>"
$pw = [System.Net.NetworkCredential]::new("", $secret).Password
if (-not $user -or -not $pw -or -not $from) { throw "All three answers are needed." }
foreach ($v in @($user, $pw, $from, $SmtpHost)) { if ($v -match "[\r\n]") { throw "No answer may contain a line break." } }

$script = @"
set -e
sed -i -E '/^#? ?(SMTP_HOST|SMTP_PORT|SMTP_USER|SMTP_PASSWORD|MAIL_FROM)=/d' /etc/memestreet.env
cat >> /etc/memestreet.env <<'END_OF_MAIL_SETTINGS'
SMTP_HOST=$SmtpHost
SMTP_PORT=$SmtpPort
SMTP_USER=$user
SMTP_PASSWORD=$pw
MAIL_FROM=$from
END_OF_MAIL_SETTINGS
systemctl restart memestreet
sleep 5
systemctl restart memestreet-gateway
echo done
"@
# (Unix line endings only. PowerShell still adds one Windows line ending after the last line, which is why the last line is a
# harmless `echo done`: a stray character after a restart command would make the server refuse it.)
($script -replace "`r", "") | ssh $Server "bash -s"
if ($LASTEXITCODE -ne 0) { throw "The server did not accept the settings." }

Start-Sleep -Seconds 8
$mode = Invoke-RestMethod -Uri "$Site/api/auth_mode" -TimeoutSec 20
if ($mode.mail_ready) {
    Write-Host "Mail is ready on $Site (email setting: $($mode.email)). Sign up with an address of yours to see the code arrive."
} else {
    Write-Host "The game restarted but does not say mail is ready yet. Check the admin page's 'Email and mail' box for the error."
}
