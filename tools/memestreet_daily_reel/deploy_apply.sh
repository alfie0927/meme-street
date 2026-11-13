#!/bin/bash
# The server side of ./deploy.sh: swap in the new code files. deploy.sh runs it under the pipeline lock
# (queue/.auto.lock), so no reel is half-made while its code changes.
#   deploy_apply.sh <folder holding new.tgz>
# The old files are kept in <folder>/before.tgz and put back if a self-check fails. The result goes to logs/deploy.log.
D=$1; cd /opt/memestreet-daily-reel || exit 1
scripts_ok() { for f in ./*.sh; do bash -n "$f" || return 1; done; }
tar tzf "$D/new.tgz" > "$D/files.txt"
tar czf "$D/before.tgz" --ignore-failed-read -T "$D/files.txt" 2>/dev/null
echo "=== deploy starts $(date -u +%FT%T): $(wc -l < "$D/files.txt") files from $D"
tar xzf "$D/new.tgz" --unlink-first && chmod +x ./*.sh      # (--unlink-first: a script that is running keeps its old file)
if python3 src/make_spec.py selftest | tail -1 | grep -qx ok && python3 src/backtest.py demo | grep -qx ok \
   && python3 src/format_scores.py demo | tail -1 | grep -qx ok \
   && python3 src/learn.py demo | tail -1 | grep -qx ok && python3 -m py_compile src/*.py lab/silent.py && scripts_ok; then
  echo "=== deployed $(date -u +%FT%T)"
else
  tar xzf "$D/before.tgz" --unlink-first; chmod +x ./*.sh
  echo "=== FAILED a self-check: the old files are back $(date -u +%FT%T)"
fi
