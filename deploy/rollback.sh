#!/bin/bash
# Puts the code from before an upload back, and restarts the game (ROADMAP O5). Run by deploy/rollback.ps1 (as root):
#
#   bash rollback.sh               back to the code from before the last upload
#   bash rollback.sh NAME          back to a particular saved release (NAME as --list prints it)
#   bash rollback.sh --list        the saved releases, newest first
#
# upload.ps1 saves the code that is about to be replaced in /opt/memestreet-releases/ (the five newest are kept). Only the
# code is swapped: the save, the ledger and the backups in data/ are not touched. A release that was rolled back to is
# renamed *.tgz.used, so rolling back again goes one release further back.
set -euo pipefail

APP=${APP:-/opt/memestreet}                       # (both can be changed, for a test)
DIR=${DIR:-/opt/memestreet-releases}

if [ "${1:-}" = "--list" ]; then
    ls -1t "$DIR" 2>/dev/null || echo "No saved releases yet (the next upload saves one)."
    exit 0
fi
if [ -n "${1:-}" ]; then
    REL="$DIR/${1%.tgz}.tgz"
else
    REL=$(ls -1t "$DIR"/*.tgz 2>/dev/null | head -n 1 || true)
fi
if [ -z "$REL" ] || [ ! -f "$REL" ]; then
    echo "No release to roll back to. Saved releases:"
    ls -1t "$DIR" 2>/dev/null || true
    exit 1
fi

echo "Rolling the code back to $(basename "$REL")"
rm -rf "$APP/game" "$APP/web" "$APP/content" "$APP/tools"
tar -xzf "$REL" -C "$APP"
sed -i 's/\r$//' "$APP"/deploy/*
mv "$REL" "$REL.used"
bash "$APP/deploy/update_server.sh" restart
