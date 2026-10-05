#!/bin/bash
# Back up the game: the save, the chart file and the money ledger. Runs every six hours (see setup_server.sh) and keeps
# two weeks of copies in /var/backups/memestreet. A copy that stays on the same machine does not protect against losing
# the machine: also download them now and then (see deploy/DEPLOY.md, "Backups"), or turn on the provider's own backups.
set -euo pipefail

SRC=/opt/memestreet
DEST=/var/backups/memestreet
STAMP=$(date +%Y-%m-%d-%H%M)
mkdir -p "$DEST/$STAMP"

# state.json and state.charts.json are replaced as a whole by the game, so a plain copy is always a complete file.
[ -f "$SRC/state.json" ] && cp "$SRC/state.json" "$DEST/$STAMP/"
[ -f "$SRC/state.charts.json" ] && cp "$SRC/state.charts.json" "$DEST/$STAMP/"
# the ledger is a live database: ask SQLite for a consistent copy instead of copying the file
[ -f "$SRC/ledger.db" ] && sqlite3 "$SRC/ledger.db" ".backup '$DEST/$STAMP/ledger.db'"

# keep fourteen days
find "$DEST" -mindepth 1 -maxdepth 1 -type d -mtime +14 -exec rm -rf {} +
echo "backup written to $DEST/$STAMP"
