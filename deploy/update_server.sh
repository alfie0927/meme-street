#!/bin/bash
# Run on the server by upload.ps1 after every upload (as root). It brings the services and the backup job in line with the
# code that just arrived and, with "restart", restarts the game.
#
#   bash /opt/memestreet/deploy/update_server.sh            after a plain upload
#   bash /opt/memestreet/deploy/update_server.sh restart    after an upload with -Restart
#
# It also moves a game from the old layout (everything in /opt/memestreet itself, before October 2026) to the folders: the
# save, the charts, the ledger and the reset backups go to data/, and the old copies of the code are removed. That needs
# the game stopped for a moment, so then it restarts the game even without "restart".
set -euo pipefail

APP=/opt/memestreet
RESTART="${1:-}"

if [ ! -f "$APP/game/server.py" ]; then
    echo "The code is not in $APP/game; nothing was changed."
    exit 1
fi
mkdir -p "$APP/data"

# 1. The services: install the unit files when they changed (a changed unit takes effect at the next restart)
for unit in memestreet.service memestreet-gateway.service; do
    if ! cmp -s "$APP/deploy/$unit" "/etc/systemd/system/$unit"; then
        cp "$APP/deploy/$unit" /etc/systemd/system/
        systemctl daemon-reload
        RESTART=restart
    fi
done

# 2. The backup job runs its own copy of backup.sh
install -m 755 "$APP/deploy/backup.sh" /usr/local/bin/memestreet-backup

# 3. A game still in the old layout: stop it (it saves on the way down), take a backup, move its files into data/
if [ -f "$APP/state.json" ] || [ -f "$APP/ledger.db" ]; then
    if [ -f "$APP/data/state.json" ] || [ -f "$APP/data/ledger.db" ]; then
        echo "There is a saved game both in $APP and in $APP/data: refusing to choose. Move one of them away by hand."
        exit 1
    fi
    echo "Moving the game's files into $APP/data"
    systemctl stop memestreet-gateway memestreet
    /usr/local/bin/memestreet-backup || echo "WARNING: the backup before the move failed (the move goes ahead: it only renames files)"
    for f in state.json state.charts.json ledger.db ledger.db-wal ledger.db-shm; do
        if [ -e "$APP/$f" ]; then mv "$APP/$f" "$APP/data/"; fi
    done
    if [ -d "$APP/backups" ] && [ ! -e "$APP/data/backups" ]; then mv "$APP/backups" "$APP/data/"; fi
    RESTART=restart
fi

# 4. The code the old layout kept in the top folder (it now lives in game/, web/, content/ and tools/)
rm -f "$APP"/*.py "$APP"/*.html
for f in base expansion pack_growth pack_fiction events_pack market_profiles lessons; do rm -f "$APP/$f.json"; done
rm -rf "$APP/__pycache__"

chown -R memestreet:memestreet "$APP"
if [ "$RESTART" = restart ]; then
    systemctl restart memestreet
    sleep 5
    systemctl restart memestreet-gateway
    echo "The game was restarted."
fi
