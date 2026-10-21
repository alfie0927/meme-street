#!/bin/bash
# Back up the game: the save, the chart file, the money ledger and the game-day price history. Runs every six hours
# (see setup_server.sh) and keeps two weeks of copies in /var/backups/memestreet. A copy that stays on the same machine
# does not protect against losing the machine: also download them now and then (see deploy/DEPLOY.md, "Backups"), or
# turn on the provider's own backups.
set -euo pipefail

SRC=/opt/memestreet/data
[ -f "$SRC/state.json" ] || SRC=/opt/memestreet          # (before October 2026 the game kept its files in the top folder)
DEST=/var/backups/memestreet
STAMP=$(date +%Y-%m-%d-%H%M)
mkdir -p "$DEST/$STAMP"

# state.json and state.charts.json are replaced as a whole by the game, so a plain copy is always a complete file.
[ -f "$SRC/state.json" ] && cp "$SRC/state.json" "$DEST/$STAMP/"
[ -f "$SRC/state.charts.json" ] && cp "$SRC/state.charts.json" "$DEST/$STAMP/"
# the ledger is a live database: ask SQLite for a consistent copy instead of copying the file
[ -f "$SRC/ledger.db" ] && sqlite3 "$SRC/ledger.db" ".backup '$DEST/$STAMP/ledger.db'"
# the game-day candles (data/history.db) the same way, compressed; the one-minute candles (minutes.db) are not kept
if [ -f "$SRC/history.db" ]; then
    sqlite3 "$SRC/history.db" ".backup '$DEST/$STAMP/history.db'" && gzip -f "$DEST/$STAMP/history.db"
fi

# keep fourteen days
find "$DEST" -mindepth 1 -maxdepth 1 -type d -mtime +14 -exec rm -rf {} +
echo "backup written to $DEST/$STAMP"
