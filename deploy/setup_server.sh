#!/bin/bash
# Sets up a fresh Ubuntu 24.04 server for Meme Street: the game, the gateways, https for your domain, a firewall,
# automatic security updates and backups. Safe to run again (it does not overwrite your keys or your game).
#
#   Usage, as root, after the code has been uploaded to /opt/memestreet (deploy/upload.ps1 does that):
#       bash /opt/memestreet/deploy/setup_server.sh yourdomain.com
#
# The domain's DNS (an A record for yourdomain.com and for www) must already point at this server, or Caddy cannot get
# its https certificate yet; it keeps trying, so it also works if you fix the DNS afterwards.
set -euo pipefail

DOMAIN="${1:-}"
APP=/opt/memestreet

if [ -z "$DOMAIN" ]; then
    echo "Usage: bash $APP/deploy/setup_server.sh yourdomain.com"
    exit 1
fi
if [ "$(id -u)" -ne 0 ]; then
    echo "Run this as root (log in as root, or put sudo in front)."
    exit 1
fi
if [ ! -f "$APP/server.py" ]; then
    echo "The game's code is not in $APP yet. Upload it first (deploy/upload.ps1), then run this again."
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive
echo "== Updating the system"
apt-get update -y
apt-get upgrade -y
apt-get install -y python3 python3-venv python3-pip sqlite3 ufw curl gnupg debian-keyring debian-archive-keyring \
    apt-transport-https unattended-upgrades

echo "== Installing Caddy (the web server that handles https)"
if ! command -v caddy >/dev/null 2>&1; then
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
    chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -y
    apt-get install -y caddy
fi

echo "== Creating the game's user and Python environment"
id memestreet >/dev/null 2>&1 || useradd --system --home "$APP" --shell /usr/sbin/nologin memestreet
python3 -m venv "$APP/.venv"
"$APP/.venv/bin/pip" install --upgrade pip
"$APP/.venv/bin/pip" install -r "$APP/requirements.txt"
chown -R memestreet:memestreet "$APP"

echo "== Settings and keys"
if [ ! -f /etc/memestreet.env ]; then
    ADMIN_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    CORE_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    CORES=$(nproc)
    GATEWAYS=$(( CORES > 4 ? 4 : CORES ))
    [ "$GATEWAYS" -lt 2 ] && GATEWAYS=2
    sed -e "s|change-me-to-a-long-random-string|$ADMIN_KEY|" \
        -e "s|change-me-too|$CORE_KEY|" \
        -e "s|^GATEWAYS=.*|GATEWAYS=$GATEWAYS|" \
        "$APP/deploy/memestreet.env.example" > /etc/memestreet.env
    chmod 600 /etc/memestreet.env
    NEW_ENV=1
else
    NEW_ENV=0
fi

echo "== Installing the services"
cp "$APP/deploy/memestreet.service" "$APP/deploy/memestreet-gateway.service" /etc/systemd/system/
sed "s/YOURDOMAIN/$DOMAIN/g" "$APP/deploy/Caddyfile" > /etc/caddy/Caddyfile
systemctl daemon-reload
systemctl enable memestreet.service memestreet-gateway.service
systemctl restart memestreet.service
sleep 5
systemctl restart memestreet-gateway.service
systemctl enable caddy
systemctl restart caddy

echo "== Firewall (only ssh, http and https are reachable from outside)"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable

echo "== Passwords off for ssh (keys only), if you logged in with a key"
if [ -s /root/.ssh/authorized_keys ]; then
    echo "PasswordAuthentication no" > /etc/ssh/sshd_config.d/00-memestreet.conf
    systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null || true
fi

echo "== Automatic security updates and backups"
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
install -m 755 "$APP/deploy/backup.sh" /usr/local/bin/memestreet-backup
echo '0 */6 * * * root /usr/local/bin/memestreet-backup >> /var/log/memestreet-backup.log 2>&1' > /etc/cron.d/memestreet-backup
chmod 644 /etc/cron.d/memestreet-backup

echo "== Checking that it is running"
sleep 5
if curl -fs http://127.0.0.1:8000/gateway/health | grep -q '"ok":true'; then
    echo "The game and its gateways are running."
else
    echo "WARNING: the gateways did not report that they are linked to the game yet."
    echo "Look at:  journalctl -u memestreet -n 50   and   journalctl -u memestreet-gateway -n 50"
fi

echo
echo "=============================================================================="
echo " Meme Street is installed."
echo "   Website:   https://$DOMAIN   (works once the domain's DNS points at this server)"
echo "   Admin:     https://$DOMAIN/admin"
if [ "$NEW_ENV" = "1" ]; then
    echo "   Admin key: $(grep '^ADMIN_KEY=' /etc/memestreet.env | cut -d= -f2-)"
    echo "              (kept in /etc/memestreet.env; write it down somewhere safe)"
fi
echo "   Logs:      journalctl -u memestreet -f"
echo "   Settings:  nano /etc/memestreet.env   then   systemctl restart memestreet memestreet-gateway"
echo "=============================================================================="
