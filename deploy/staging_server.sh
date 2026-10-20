#!/bin/bash
# Run on the server by upload.ps1 -Staging (as root), after the code was unpacked into /opt/memestreet-staging. It installs
# the staging service, gives the staging copy the newest backup of the live game when it has no save yet (or with
# "fresh"), and (re)starts it. See deploy/memestreet-staging.service.
#
#   bash /opt/memestreet-staging/deploy/staging_server.sh          keep the staging copy's own save
#   bash /opt/memestreet-staging/deploy/staging_server.sh fresh    start again from the newest live backup
set -euo pipefail

APP=/opt/memestreet-staging
BACKUPS=/var/backups/memestreet

if ! cmp -s "$APP/deploy/memestreet-staging.service" /etc/systemd/system/memestreet-staging.service; then
    cp "$APP/deploy/memestreet-staging.service" /etc/systemd/system/
    systemctl daemon-reload
fi
if [ ! -f /etc/memestreet-staging.env ]; then
    # the live admin key only: no shop (PAYMENTS is off unless set) and no mail (no SMTP settings)
    grep '^ADMIN_KEY=' /etc/memestreet.env > /etc/memestreet-staging.env
    chmod 640 /etc/memestreet-staging.env
    chgrp memestreet /etc/memestreet-staging.env
fi

mkdir -p "$APP/data"
if [ "${1:-}" = fresh ] || [ ! -f "$APP/data/state.json" ]; then
    NEWEST=$(ls -1d "$BACKUPS"/*/ 2>/dev/null | sort | tail -n 1 || true)
    if [ -n "$NEWEST" ]; then
        systemctl stop memestreet-staging 2>/dev/null || true
        rm -f "$APP"/data/state.json "$APP"/data/state.charts.json "$APP"/data/ledger.db*
        for f in state.json state.charts.json ledger.db; do
            if [ -f "$NEWEST$f" ]; then cp "$NEWEST$f" "$APP/data/"; fi
        done
        echo "The staging copy starts from the live backup $(basename "$NEWEST")."
    else
        echo "No live backup found in $BACKUPS: the staging copy starts a new game."
    fi
fi
chown -R memestreet:memestreet "$APP"
systemctl restart memestreet-staging
sleep 4
if systemctl is-active --quiet memestreet-staging; then
    echo "The staging copy is running on the server's port 8100."
else
    echo "The staging copy did not start: journalctl -u memestreet-staging -n 50"
    exit 1
fi
