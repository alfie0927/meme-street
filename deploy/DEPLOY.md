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

This copies the save, the charts and the ledger (from `data\` here to `/opt/memestreet/data` there), restarts the game on the server with them, and refuses to run while
your own copy is still running. Otherwise the server starts a fresh market (you can use the admin **Reset** button for a
clean Day 1 at any time). After this, **stop using the copy on your computer**: only one game may own the players'
money.

## Step 6. Turn on email (so players can recover passwords)

1. Make a free account at an email service (Resend or Brevo are easy), add your domain there and add the DNS records it
   asks for (SPF and DKIM; without them your mail goes to spam).
2. **The easy way:** `powershell -File deploy\set_mail.ps1 -Server root@YOUR.SERVER.IP`. It asks for the SMTP user, the
   password or API key (typed hidden, and sent to the server inside the ssh connection, never in a command line or a chat)
   and the from-address (`Meme Street <no-reply@yourdomain.com>`), writes them into `/etc/memestreet.env`, restarts the game
   and checks that the game now says mail is ready. With Resend the host is `smtp.resend.com` and the user is `resend`.
   Mail ready turns the game's email setting from off to optional by itself.
   **By hand instead:** on the server `nano /etc/memestreet.env`, remove the `#` from the `SMTP_` and `MAIL_FROM` lines and
   fill them in, then `systemctl restart memestreet memestreet-gateway`.
3. To make a verified address *necessary* (the default is optional), on your computer make a file `my_settings.json` in the `content` folder containing
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

**On memestreet.net this is done** (2026-10-10): `/admin` and `/api/admin/*` are behind that password, and the admin key was
replaced at the same time. The new name, password and key are in `data\live_admin_credentials.txt` (the `data` folder is
never sent to git). To change them later, make a new hash on the server, replace the hash in `/etc/caddy/Caddyfile`,
run `caddy validate --config /etc/caddy/Caddyfile` and `systemctl reload caddy`; the admin key is the `ADMIN_KEY` line of
`/etc/memestreet.env` (then `systemctl restart memestreet memestreet-gateway`). Behind this, the game itself locks an address
out of the admin interface for ten minutes after ten wrong keys (`docs/HOW_IT_WORKS.md` section 12).

## Updating the live game

Whenever you change the code on your computer:

```powershell
powershell -File deploy\upload.ps1 -Server root@YOUR.SERVER.IP -Restart
```

It sends the code (`game/`, `web/`, `content/`, `tools/`, the logo and `deploy/`), runs `deploy/update_server.sh` on the
server (it installs changed service files and the backup job) and restarts the game. The game saves itself on the way down,
players are disconnected for a few seconds and reconnect by themselves. Never sent: `data/` (saves, the ledger, backups)
and anything else the server owns.

**Trying an update first: the staging copy.** To see the new code on the real server before players do:

```powershell
powershell -File deploy\upload.ps1 -Server root@YOUR.SERVER.IP -Staging           # add -Fresh to start again from the newest live backup
```

It sends the code to `/opt/memestreet-staging` instead, starts it there (`memestreet-staging.service`, port 8100, only
reachable from the server itself) with a copy of the newest live backup, and opens a tunnel: while the window is open,
**http://127.0.0.1:8100** on your computer is the staging copy. Its shop is closed and it sends no mail
(`/etc/memestreet-staging.env` holds only the admin key). Ctrl+C closes the tunnel; the staging copy keeps running (it uses
about 650 MB of memory) until `upload.ps1 -Server root@YOUR.SERVER.IP -StopStaging`. It never starts by itself.

**Undoing an update.** Every live upload first saves the code it replaces in `/opt/memestreet-releases/` (the five newest).
If an update goes wrong:

```powershell
powershell -File deploy\rollback.ps1 -Server root@YOUR.SERVER.IP          # back to the code before the last upload, and restart
powershell -File deploy\rollback.ps1 -Server root@YOUR.SERVER.IP -List    # the saved releases
```

Only the code goes back; the save, the ledger and the backups stay. Running it again goes one release further back. If an
update changed how the game saves (rare; the docs say so when it does), restore the backup from before it too (below).

On the server the game is in `/opt/memestreet` with the same folders as here; what it writes is in `/opt/memestreet/data`.
(Until October 2026 everything sat in `/opt/memestreet` itself. The first upload after the change moved the save, the
ledger and the reset backups into `data/` and removed the old copies of the code: `update_server.sh` does that by itself on
any server still in the old layout, with the game stopped for the moment of the move and a backup taken first.)

## Backups

Every six hours the server copies the save, the charts and the ledger to `/var/backups/memestreet/` and keeps two weeks.
That protects you from mistakes, not from losing the server. Copy them to your computer now and then:

```powershell
scp -r root@YOUR.SERVER.IP:/var/backups/memestreet .\server-backups
```

or, better, `powershell -File deploy\pull_backups.ps1 -Server root@YOUR.SERVER.IP`: it copies only the newest backups that are not
here yet (default: the last day, four copies) into `D:\meme_street_backups`, checks each one arrived whole, keeps the newest 60
(about two weeks) and changes nothing on the server. **To run it every day by itself** (ROADMAP O2):

```powershell
powershell -ExecutionPolicy Bypass -File deploy\schedule_backups.ps1 -Server root@YOUR.SERVER.IP     # -At 21:00 for another time
```

That makes a Windows scheduled task, *Meme Street backups*, that runs at 09:00 (or as soon as the computer is on after that),
with no window, and writes what it did to `D:\meme_street_backups\pull.log`. **On this computer it is set up** (2026-10-19).
`-Remove` deletes the task.

and switch on the provider's own backups. **Restoring** a backup (the game must be stopped while you copy):

```bash
systemctl stop memestreet-gateway memestreet
cp /var/backups/memestreet/2026-10-05-0400/state.json /var/backups/memestreet/2026-10-05-0400/state.charts.json /opt/memestreet/data/
rm -f /opt/memestreet/data/ledger.db-wal /opt/memestreet/data/ledger.db-shm
cp /var/backups/memestreet/2026-10-05-0400/ledger.db /opt/memestreet/data/
# the game-day price history (from October 2026; a backup without it is fine: the days are rebuilt from the charts)
rm -f /opt/memestreet/data/history.db*
gunzip -c /var/backups/memestreet/2026-10-05-0400/history.db.gz > /opt/memestreet/data/history.db
chown memestreet:memestreet /opt/memestreet/data/state*.json /opt/memestreet/data/ledger.db /opt/memestreet/data/history.db
systemctl start memestreet && sleep 5 && systemctl start memestreet-gateway
```

The backups also hold `history.db.gz`: every listing's game-day candles (the D, W and M charts). The one-minute candles
(`minutes.db`, three real days) are not backed up.

## Knowing it is up

**Already in place** (ROADMAP O3): a GitHub Actions job (`.github/workflows/uptime.yml`) asks `https://memestreet.net/api/health`
every 15 minutes; when it fails three times in a row the run fails and GitHub emails you (on github.com: Settings >
Notifications > Actions). GitHub may start it a few minutes late and pauses scheduled jobs in a repository with no commits for
60 days (a commit, or *Enable workflow* on the Actions tab, starts it again). For checks every few minutes and alerts by phone,
add a dedicated monitor as well:

Free monitors such as UptimeRobot (uptimerobot.com) can check `https://yourdomain.com/api/health` every five minutes and
email or message you when it fails. That address answers 200 with `{"ok":true,...}` while the game is ticking and saving, and
503 when it is stuck (no tick for 15 seconds, or no save for five minutes); if the gateways cannot reach the game, or the server
is down, it fails too. It needs no key and shows nothing private. To set it up: make a free account, **Add new monitor**, type
*HTTP(s)*, the address above, interval 5 minutes, and choose where the alerts go (your email, or a phone push through its app).
`/gateway/health` only says whether one gateway is linked to the game. Useful commands on the server:

```bash
systemctl status memestreet memestreet-gateway caddy   # are they running?
journalctl -u memestreet -f                            # the game's messages, live (Ctrl+C to stop looking)
journalctl -u memestreet-gateway -n 50
journalctl -u caddy -n 50                              # certificate problems show here
```

## Cloudflare in front (optional, ROADMAP O4)

Cloudflare hides the server's address, absorbs floods of traffic and can cache. The server is ready for it: Caddy believes the
visitor's address that Cloudflare sends (`CF-Connecting-IP`) only from Cloudflare's own addresses (`trusted_proxies` at the
top of the Caddyfile), so the sign-up and login limits keep working per visitor, with or without Cloudflare. To switch it on:

1. Make a free account at cloudflare.com, **Add a site**, type `memestreet.net`, pick the Free plan. It reads your DNS records;
   check that `memestreet.net` and `www` point at the server and have the orange cloud (proxied) on.
2. At the company where you bought the name, replace its name servers with the two Cloudflare shows. It can take a few
   hours; Cloudflare emails you when the site is active.
3. In Cloudflare: **SSL/TLS > Overview: Full (strict)** (the server has its own certificate from Caddy). Leave the rest as it
   is; websockets work through Cloudflare by default.
4. Check: the site still opens, `https://memestreet.net/api/health` answers, and the admin page's "Connected pages and
   visitors" shows different addresses for different visitors.

If Cloudflare's address list changes (https://www.cloudflare.com/ips), update `trusted_proxies` in `deploy/Caddyfile` and on
the server in `/etc/caddy/Caddyfile`, then `caddy validate --config /etc/caddy/Caddyfile` and `systemctl reload caddy`. (On
memestreet.net the Caddyfile was updated on 2026-10-19; the name servers are still yours to change.)

## Secrets: what they are and where they live (ROADMAP O6)

Never in git, never in chat. If one may have leaked, change it as described.

| Secret | Where | How to change it |
|---|---|---|
| `ADMIN_KEY` (the admin page's key) | `/etc/memestreet.env` on the server; this computer's copy in `data\live_admin_credentials.txt`; the local game's in `data\admin_key.txt` | edit the line, `systemctl restart memestreet memestreet-gateway` |
| The admin page's second password (name `owner`) | its hash in `/etc/caddy/Caddyfile`; the password in `data\live_admin_credentials.txt` | Step 7 |
| `CORE_KEY` (gateways to game) | `/etc/memestreet.env` | any long random string, then restart both services |
| `SMTP_PASSWORD` (mail, once on) | `/etc/memestreet.env` (`deploy\set_mail.ps1` puts it there) | make a new key at the mail service, run `set_mail.ps1` again |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` (once the shop takes money) | `/etc/memestreet.env` | roll the key in Stripe's dashboard, update the lines, restart |
| Your ssh key | `C:\Users\YOU\.ssh\` here; its public half in `/root/.ssh/authorized_keys` | `ssh-keygen -t ed25519`, add the new public key to `authorized_keys`, check you can log in with it, then remove the old line |
| The live save and ledger (players' accounts) | `/opt/memestreet/data`, `/var/backups/memestreet`, `D:\meme_street_backups` | not a key: keep the folders private |

Logging in to the server: keys only (passwords are off for ssh), and **fail2ban** shuts an address out for an hour after five
failed ssh logins in ten minutes (`fail2ban-client status sshd` lists who is shut out right now). If you lock yourself out,
the provider's web console still works.

## When something is wrong

| What you see | Likely cause and what to do |
|---|---|
| The browser says the site can't be reached | The DNS records are not right yet (`nslookup yourdomain.com` should show the server's IP), or the firewall was changed (`ufw status` should allow 80 and 443). |
| "Your connection is not private" | Caddy has no certificate yet: usually the DNS was not ready. Look at `journalctl -u caddy -n 50`; it retries by itself, or run `systemctl restart caddy` once the DNS is right. |
| `502 Bad Gateway` | The gateways are not running: `systemctl restart memestreet-gateway`, then `journalctl -u memestreet-gateway -n 50`. |
| "The game is restarting. Try again in a moment." | The game server is down or restarting: `systemctl status memestreet`, `journalctl -u memestreet -n 100`. |
| Sign-up works but the codes never arrive | No mail service set up (Step 6), or its DNS records are missing. The codes also show on the admin page under "Email and mail". |
| You are locked out of the server | Use the provider's web console (every provider has one) to log in and fix `/etc/ssh` or the firewall. |

## Before real players, and before selling MB

- Keep `ADMIN_KEY` and `CORE_KEY` secret; never put them in the code or send them in chat.
- Do Step 7 and set up a mail service. Decide on `email_mode` (`HOW_IT_WORKS.md` section 10.6).
- Read `ROADMAP.md`: terms of service, a privacy policy and an age policy (R1, R2) should be on the site before the
  public arrives, and the consumer rules for selling MB packages (R3, R4) before the first sale. MB are never cashed out,
  so the old questions about real-money payouts no longer apply.
- Selling packages adds a payment provider and its webhook (`ROADMAP.md` M3, O7): keep its secret with the others.
- One machine is a single point of failure. That is fine for a test; a paid product needs the provider backups, an
  uptime monitor and, later, the larger set-up in `ROADMAP.md` E10.
