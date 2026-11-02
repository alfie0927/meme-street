#!/usr/bin/env bash
# One-time setup on an Ubuntu/Debian server.  Run from this folder:  sudo ./setup.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"; RUN_AS="${SUDO_USER:-$USER}"
echo ">> system packages"
apt-get update -qq && apt-get install -y -qq python3 python3-pip ffmpeg unzip curl fontconfig >/dev/null
echo ">> python packages"
sudo -u "$RUN_AS" python3 -m pip install --user --break-system-packages -q kokoro-onnx soundfile numpy playwright faster-whisper
sudo -u "$RUN_AS" python3 -m playwright install chromium >/dev/null
python3 -m playwright install-deps chromium >/dev/null
echo ">> font (Cascadia Mono, the site's chart font)"
FD="/home/$RUN_AS/.fonts"; [ "$RUN_AS" = root ] && FD=/root/.fonts; mkdir -p "$FD"
if ! fc-list | grep -qi "Cascadia Mono"; then
  curl -sSL -o /tmp/cascadia.zip https://github.com/microsoft/cascadia-code/releases/download/v2407.24/CascadiaCode-2407.24.zip
  unzip -qo /tmp/cascadia.zip -d "$FD/cascadia" && chown -R "$RUN_AS" "$FD" && fc-cache -f >/dev/null
fi
echo ">> voice model (Kokoro, ~350 MB)"
mkdir -p "$DIR/models"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -f "$DIR/models/$f" ] || curl -sSL -o "$DIR/models/$f" "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f"
done
chown -R "$RUN_AS" "$DIR"
[ -f "$DIR/config.env" ] || { cp "$DIR/config.example.env" "$DIR/config.env"; chown "$RUN_AS" "$DIR/config.env"; chmod 600 "$DIR/config.env"; }
echo ">> speech-timing model (used to sync visuals to the exact words, ~150 MB)"
sudo -u "$RUN_AS" python3 -c "from faster_whisper import WhisperModel; WhisperModel('base.en', device='cpu', compute_type='int8')" >/dev/null 2>&1 || echo "   (will download on first run)"
echo ">> schedule (systemd timers, UTC)"
for u in memestreet-reel-make memestreet-reel-post; do
  for x in service timer; do sed "s#__DIR__#$DIR#g; s#__USER__#$RUN_AS#g" "$DIR/systemd/$u.$x" > "/etc/systemd/system/$u.$x"; done
done
systemctl daemon-reload
echo
echo "Installed. Next:"
echo "  1. edit $DIR/config.env  (Instagram token + public video folder: README sections 3-4)"
echo "  2. test:   ./post_reel.sh --check   then   ./make_reel.sh   (see README section 5)"
echo "  3. go live: sudo systemctl enable --now memestreet-reel-make.timer memestreet-reel-post.timer"
