<#
Switches the live shop on to real payments with Stripe (PAYMENTS=stripe), without the key ever being typed into a chat or
onto a command line: it asks for the key and the webhook's signing secret here, with the letters hidden, and sends them
to the server inside the ssh connection.

  powershell -ExecutionPolicy Bypass -File deploy\set_stripe.ps1 -Server root@YOUR.SERVER.IP

First, in the Stripe dashboard (with the account activated):
  1. Developers > API keys > Create restricted key: Checkout Sessions, Subscriptions, Products and Prices: Write;
     Invoices: Read; everything else None. It starts rk_live_ (a full secret key, sk_live_, works too).
  2. Developers > Webhooks > Add endpoint: https://YOURDOMAIN/api/shop/stripe/webhook, with the events
     checkout.session.completed, invoice.paid and customer.subscription.deleted. Copy its signing secret (whsec_...).

What it does on the server: it replaces the PAYMENTS, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET and SITE_URL lines in
/etc/memestreet.env, restarts the game (a few seconds; players reconnect by themselves), and asks the game whether the
shop is now taking payments. Test keys are refused: on a public site anyone could pay with Stripe's test card. To close
the shop again, set PAYMENTS=off in that file and run: systemctl restart memestreet memestreet-gateway
#>
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [string]$Site = "https://memestreet.net"
)

$ErrorActionPreference = "Stop"
$key = [System.Net.NetworkCredential]::new("", (Read-Host "Stripe key, rk_live_... or sk_live_... (hidden)" -AsSecureString)).Password.Trim()
$hook = [System.Net.NetworkCredential]::new("", (Read-Host "Webhook signing secret, whsec_... (hidden)" -AsSecureString)).Password.Trim()
if ($key -match "^(sk|rk)_test_") { throw "That is a test key: on the live site anyone could pay with Stripe's test card. Use the live key." }
if ($key -notmatch "^(sk|rk)_live_\S+$") { throw "The key should start with rk_live_ (or sk_live_)." }
if ($hook -notmatch "^whsec_\S+$") { throw "The signing secret should start with whsec_." }

$script = @"
set -e
sed -i -E '/^#? ?(PAYMENTS|STRIPE_SECRET_KEY|STRIPE_WEBHOOK_SECRET|SITE_URL)=/d' /etc/memestreet.env
cat >> /etc/memestreet.env <<'END_OF_PAYMENT_SETTINGS'
PAYMENTS=stripe
STRIPE_SECRET_KEY=$key
STRIPE_WEBHOOK_SECRET=$hook
SITE_URL=$Site
END_OF_PAYMENT_SETTINGS
systemctl restart memestreet
sleep 5
systemctl restart memestreet-gateway
admin=`$(grep -E '^ADMIN_KEY=' /etc/memestreet.env | cut -d= -f2-)
mode=''
for i in `$(seq 30); do
  mode=`$(curl -s -H "X-Admin-Key: `$admin" http://127.0.0.1:8001/api/admin/shop | grep -o '"mode":"[a-z]*"' || true)
  [ -n "`$mode" ] && break
  sleep 2
done
echo "shop `$mode"
"@
# (Unix line endings only. PowerShell adds one Windows line ending after the last line, which is why the last line is a
# harmless echo: a stray character after a restart command would make the server refuse it.)
$out = ($script -replace "`r", "") | ssh $Server "bash -s"
if ($LASTEXITCODE -ne 0) { throw "The server did not accept the settings." }
if ("$out" -match '"mode":"stripe"') {
    Write-Host "Payments are on: the shop on $Site now takes real money through Stripe. Buy the cheapest package with your own card to try it, then refund it in Stripe."
} else {
    Write-Host "The game restarted but the shop is not taking payments ($out). The server log says why: journalctl -u memestreet -n 50"
}
