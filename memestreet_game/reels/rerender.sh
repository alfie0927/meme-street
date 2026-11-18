#!/bin/bash
# re-render already approved, not yet posted reels after a renderer change (captions on every scene, the cover fix, 2026-11-09)
cd /opt/memestreet-daily-reel; PAGE=reel.html; [ -f CHAMPION.md ] && PAGE=reel_v2.html
for s in "$@"; do W=work/auto-$s; O=out/auto-$s; echo "=== rerender $s $(date -u +%T) page $PAGE"
  if python3 src/narrate.py "$W" && PAGE=$PAGE FPS=30 python3 src/render.py "$W" "$O"; then cp "$O/reel.mp4" "$O/cover.jpg" "queue/$s/" && echo "=== done $s $(date -u +%T)"; else echo "=== FAILED $s (old cut stays)"; fi
done
