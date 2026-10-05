# Putting Meme Street on a real server with its own web address

This guide takes you from "it runs on my computer" to "anyone can open https://yourname.com, 24 hours a day". You do the
parts that need your money or your accounts (buying the name, renting the server); everything else is one command each.
Allow an afternoon the first time. Nothing here is permanent: you can delete the server and start again at any time.

**What you will have at the end**

```
the internet --https--> Caddy (certificate, redirects)  -->  gateways (hold the players' connections)  -->  the game
                         on your server, one machine         2-4 processes                                  one process
```

The game restarts by itself after a crash or a reboot, saves every 30 seconds, is backed up every six hours, keeps its
software up to date with security fixes, and only lets the web in (ports 22, 80 and 443).

## What it costs (roughly, check the current prices)

| Thing | About | Notes |
|---|---|---|
| A domain name | 10 to 15 USD a year for a `.com` | Some endings (`.xyz`, `.fun`, `.club`) are cheaper the first year and cost more on renewal: look at the **renewal** price. |
| A small server (VPS) | 4 to 8 USD or EUR a month | 2 processor cores and 2 to 4 GB of memory is plenty to start: the measurements in `HOW_IT_WORKS.md` section 12 say this carries hundreds of players, and the game server alone about 4,000. |
| Email for sign-up codes | free to start | Resend, Brevo and others have free tiers (a few thousand mails a month). |
| Provider backups (optional) | about 20% of the server price | Worth it: a copy of the whole machine, kept somewhere else. |

## Step 1. Pick and buy the name

Buy it from a registrar such as **Cloudflare Registrar**, **Porkbun** or **Namecheap** (they sell at cost or close to it,
and include free privacy protection). Search the name there; it tells you if it is free.

- I looked up some names from this computer. `memestreet.com` already exists and is parked on a for-sale marketplace
  (probably expensive). Names that showed **no records at all** (so they may be free, but only a registrar can say):
  `memestreet.gg`, `memestreet.games`, `memestreet.trade`, `memestreet.net`, `memestreet.club`, `playmemestreet.com`.
  `memestreet.io`, `.app`, `.xyz` and `.fun` already exist.
- Check the spelling: in your message it was `memesteet.com` (a missing r). Don't buy a typo.
- You plan to earn money with this, so before you build a brand on "Meme Street", search the name in the trademark
  registers of the countries you will sell in (a lawyer or a quick search on the official sites), and for existing
  businesses with the same name. It is cheap to change the name now and expensive later.

## Step 2. Rent the server

Use any provider that rents Ubuntu servers: **Hetzner Cloud** (cheap, European and US locations), **DigitalOcean**,
**Vultr**, **Linode**. Make a server with:

- **Ubuntu 24.04** (the game is built for Python 3.12, which this has);
- **2 vCPU and 2 GB of memory or more** (4 GB if the price difference is small);
- a location near most of your players;
- **your SSH key** (below), not a password;
- backups switched on if they offer them.

**Making an SSH key** (a key pair instead of a password: much safer). In PowerShell on your computer:

```powershell
ssh-keygen -t ed25519 -C "meme street server"
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

Press Enter three times (no passphrase is fine to start, a passphrase is better). The second command prints one line
starting with `ssh-ed25519`: paste it into the provider's "SSH key" box when you create the server. The provider shows you the
server's **IP address** (four numbers like `203.0.113.7`). Write it down.

## Step 3. Point the name at the server (DNS)

In the registrar's DNS settings for your domain add two records:

| Type | Name | Value |
|---|---|---|
| A | `@` (the bare domain) | the server's IP address |
| A | `www` | the same IP address |

(If the server also has an IPv6 address, add `AAAA` records the same way.) If you use Cloudflare's DNS, set both records
to **DNS only** (grey cloud), not Proxied: the game needs to see the real visitor and Caddy gets the certificate itself.
It takes a few minutes, sometimes an hour, to spread. Check with `nslookup yourdomain.com`.

## Step 4. Send the game to the server and set it up

On your computer, in the project folder (stop the game on your computer first only if you also want to move your saved
game, see below):

```powershell
powershell -File deploy\upload.ps1 -Server root@YOUR.SERVER.IP
```

The first time, ssh asks "Are you sure you want to continue connecting?": type `yes`. It sends about 40 small files.
Then log in to the server and run the setup, which takes a few minutes:

```powershell
ssh root@YOUR.SERVER.IP
bash /opt/memestreet/deploy/setup_server.sh yourdomain.com
```

It installs Python, the web server (Caddy), the game and its gateways as services that start on boot, a firewall,
automatic security updates and the backups. At the end it prints the address and **your admin key** (a long random
string, also kept in `/etc/memestreet.env`). Write the key down.

Open `https://yourdomain.com`. The first load may take a few seconds while Caddy gets the certificate. You should see the
sign-in box. Create an account, trade, and open `https://yourdomain.com/admin` and enter the admin key.

If the page does not load: see "When something is wrong" below.

## Step 5. Move the game you have been running (optional)

If you want to keep your accounts and prices: **stop the game on your computer** (Ctrl+C in its window), then

```powershell
powershell -File deploy\upload.ps1 -Server root@YOUR.SERVER.IP -WithGame
```

This copies the save, the charts and the ledger, restarts the game on the server with them, and refuses to run while
your own copy is still running. Otherwise the server starts a fresh market (you can use the admin **Reset** button for a
clean Day 1 at any time). After this, **stop using the copy on your computer**: only one game may own the players'
money.

## Step 6. Turn on email (so players can recover passwords)

1. Make a free account at an email service (Resend or Brevo are easy), add your domain there and add the DNS records it
   asks for (SPF and DKIM; without them your mail goes to spam).
2. On the server: `nano /etc/memestreet.env`, remove the `#` from the `SMTP_` and `MAIL_FROM` lines and fill them in
   (the service shows you the values). Save with Ctrl+O, Enter, Ctrl+X.
3. Restart: `systemctl restart memestreet memestreet-gateway`.
4. On your computer make a file `my_settings.json` in the project folder containing
   `{"settings": {"email_mode": "optional"}}` (or `"required"` to make a verified address necessary to trade), then
   upload it with `powershell -File deploy\upload.ps1 -Server root@YOUR.SERVER.IP`. Players see the email box at sign-up.

## Step 7. Protect the admin page (do this before real players come)

The admin key alone can be guessed at without limit. Put a second password in front of `/admin` (one more layer, in the
web server):

```bash
caddy hash-password          # on the server: type a password, it prints a long hash
nano /etc/caddy/Caddyfile    # remove the # in front of the lines of the "@admin ... basic_auth" block, paste the hash
systemctl reload caddy
```

Your browser will then ask for the name `owner` and that password before it shows `/admin`.

## Updating the live game

Whenever you change the code on your computer:

```powershell
powershell -File deploy\upload.ps1 -Server root@YOUR.SERVER.IP -Restart
```

It sends the changed code and restarts the game. The game saves itself on the way down, players are disconnected for a few
seconds and reconnect by themselves. Never sent: saves, the ledger and anything else the server owns.

## Backups

Every six hours the server copies the save, the charts and the ledger to `/var/backups/memestreet/` and keeps two weeks.
That protects you from mistakes, not from losing the server. Copy them to your computer now and then:

```powershell
scp -r root@YOUR.SERVER.IP:/var/backups/memestreet .\server-backups
```

and switch on the provider's own backups. **Restoring** a backup (the game must be stopped while you copy):

```bash
systemctl stop memestreet-gateway memestreet
cp /var/backups/memestreet/2026-10-05-0400/state.json /var/backups/memestreet/2026-10-05-0400/state.charts.json /opt/memestreet/
rm -f /opt/memestreet/ledger.db-wal /opt/memestreet/ledger.db-shm
cp /var/backups/memestreet/2026-10-05-0400/ledger.db /opt/memestreet/
chown memestreet:memestreet /opt/memestreet/state*.json /opt/memestreet/ledger.db
systemctl start memestreet && sleep 5 && systemctl start memestreet-gateway
```

## Knowing it is up

Free monitors such as UptimeRobot can check `https://yourdomain.com/gateway/health` every five minutes (the answer contains
`"ok":true` when the gateways are linked to the game) and email or message you when it fails. Useful commands on the server:

```bash
systemctl status memestreet memestreet-gateway caddy   # are they running?
journalctl -u memestreet -f                            # the game's messages, live (Ctrl+C to stop looking)
journalctl -u memestreet-gateway -n 50
journalctl -u caddy -n 50                              # certificate problems show here
```

## When something is wrong

| What you see | Likely cause and what to do |
|---|---|
| The browser says the site can't be reached | The DNS records are not right yet (`nslookup yourdomain.com` should show the server's IP), or the firewall was changed (`ufw status` should allow 80 and 443). |
| "Your connection is not private" | Caddy has no certificate yet: usually the DNS was not ready. Look at `journalctl -u caddy -n 50`; it retries by itself, or run `systemctl restart caddy` once the DNS is right. |
| `502 Bad Gateway` | The gateways are not running: `systemctl restart memestreet-gateway`, then `journalctl -u memestreet-gateway -n 50`. |
| "The game is restarting. Try again in a moment." | The game server is down or restarting: `systemctl status memestreet`, `journalctl -u memestreet -n 100`. |
| Sign-up works but the codes never arrive | No mail service set up (Step 6), or its DNS records are missing. The codes also show on the admin page under "Email and mail". |
| You are locked out of the server | Use the provider's web console (every provider has one) to log in and fix `/etc/ssh` or the firewall. |

## Before real players, and before real money

- Keep `ADMIN_KEY` and `CORE_KEY` secret; never put them in the code or send them in chat.
- Do Step 7 and set up a mail service. Decide on `email_mode` (`HOW_IT_WORKS.md` section 10.6).
- Read `ROADMAP.md`: the legal review (phase 4) comes before any real money, and terms of service and a privacy policy
  should be on the site before the public arrives.
- The house reserve and its risk (`ROADMAP.md` A12) are a capital decision for real money.
- One machine is a single point of failure. That is fine for a test; a paid product needs the provider backups, an
  uptime monitor and, later, the larger set-up in `ROADMAP.md` G10.
