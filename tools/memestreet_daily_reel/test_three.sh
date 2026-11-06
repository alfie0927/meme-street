#!/usr/bin/env bash
# A test of the film-critic process (2026-11-06): one reel now, the next an hour after it posts, the next an hour after
# that, each made by auto_reel.sh (written, voiced, rendered and sent back by the critic until he approves), then the
# regular auto timer is switched back on.   Run as: systemd-run ... ./test_three.sh
cd "$(dirname "$0")"
slot_at() { date -u -d "$1" +%Y-%m-%dT%H%M; }
posted() { for _ in $(seq 60); do [ -f "queue/$1/posted.json" ] && return 0; sleep 30; done; return 1; }
log() { echo "=== test_three: $*  $(date -u '+%F %T UTC')" | tee -a logs/auto.log; }

S1=$(slot_at now)
log "reel 1 ($S1, Chart twist)"
REEL_CATEGORY="Chart twist" LATE_OK=1 ./auto_reel.sh "$S1" || log "reel 1 was not approved"
posted "$S1" && T=$(date -u -r "queue/$S1/posted.json" '+%F %T') || T=$(date -u '+%F %T')
S2=$(slot_at "$T UTC + 60 min")
log "reel 2 ($S2, Trader levels)"
REEL_CATEGORY="Trader levels" LATE_OK=1 ./auto_reel.sh "$S2" || log "reel 2 was not approved"
S3=$(slot_at "$(date -u -d "${S2:0:10} ${S2:11:2}:${S2:13:2}" '+%F %T') UTC + 60 min")
log "reel 3 ($S3, Stock story)"
REEL_CATEGORY="Stock story" LATE_OK=1 ./auto_reel.sh "$S3" || log "reel 3 was not approved"
systemctl start memestreet-reel-auto.timer
log "done: the regular timetable is back on"
