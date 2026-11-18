#!/usr/bin/env bash
# Rebuilds site/vendor/ctrader-sdk.js (cTrader's Plugin API v2 SDK, the parts this panel uses, as one ES module) and
# site/vendor/LICENSES.txt. The versions are pinned: change them on purpose, run the tests and the demo checklist.
# Run from Git Bash in this folder. Needs Node and network access; nothing is installed into the repo.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cp "$HERE/vendor-entry.mjs" "$WORK/entry.mjs"
cd "$WORK"
npm init -y >/dev/null
npm install --silent --no-audit --no-fund \
  @spotware-web-team/sdk@2.1.5 @spotware-web-team/sdk-external-api@2.0.1 rxjs@7.8.2 esbuild@0.28.2
npx esbuild entry.mjs --bundle --format=esm --minify --legal-comments=inline --target=es2020 --outfile=ctrader-sdk.js
cp ctrader-sdk.js "$HERE/site/vendor/ctrader-sdk.js"
for p in @spotware-web-team/sdk @spotware-web-team/sdk-external-api zod uuid rxjs; do
  f=$(ls "node_modules/$p/" | grep -i '^licen' | head -1)
  v=$(grep -o '"version": "[^"]*"' "node_modules/$p/package.json" | head -1 | cut -d'"' -f4)
  echo "==== $p $v"; cat "node_modules/$p/$f"; echo
done > "$HERE/site/vendor/LICENSES.txt"
echo "rebuilt site/vendor/ctrader-sdk.js ($(wc -c < "$HERE/site/vendor/ctrader-sdk.js") bytes)"
