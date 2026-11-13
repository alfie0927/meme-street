#!/usr/bin/env bash
# Put this folder's code on the reel server (roadmap RL1: one copy of the reel code, the server deployed from the repo).
#   ./deploy.sh        from Git Bash on the owner's PC
# It sends the code files git knows in this folder as one bundle: src/, lab/silent.py, the scripts, the systemd units
# and the docs the writer reads. Never config.env, state, queue, work or media. On the server the swap waits for the
# pipeline lock (up to 6 hours), so it lands between two reels; deploy_apply.sh keeps the old files, runs the
# self-checks and puts the old files back if one fails. The result is in logs/deploy.log on the server.
set -euo pipefail
cd "$(dirname "$0")"
HOST=${REEL_HOST:-root@65.109.233.145}; D=/root/reel-deploy/$(date -u +%Y%m%dT%H%M%S); B=$(mktemp -d)
git ls-files -co --exclude-standard src lab/silent.py auto_reel.sh make_reel.sh queue_post.sh rerender.sh news_watch.sh deploy_apply.sh \
    systemd README.md swipe.md RULEBOOK.md voice.md exemplar/NOTES.md \
  | grep -v -E '\.(wav|png|jpg|mp4|mp3|pyc)$|/dry/' | sort -u > "$B/files.txt"
tar czf "$B/new.tgz" -T "$B/files.txt"
ssh -o BatchMode=yes "$HOST" "mkdir -p $D" < /dev/null
scp -q -o BatchMode=yes "$B/new.tgz" deploy_apply.sh "$HOST:$D/"
ssh -o BatchMode=yes "$HOST" "cd /opt/memestreet-daily-reel && (setsid nohup flock -w 21600 queue/.auto.lock bash $D/deploy_apply.sh $D >> logs/deploy.log 2>&1 < /dev/null &)" < /dev/null
echo "queued on the server: $D, $(wc -l < "$B/files.txt") files. It runs between two reels; logs/deploy.log there has the result."
