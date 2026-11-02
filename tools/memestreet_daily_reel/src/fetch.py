"""Fetch today's Daily Chart (candles, levels, leaderboard) from memestreet.net.

If the account hasn't played today, it starts the game and waits ~2 minutes for it to finish
(no trades are placed). Then it saves the full /api/daily response, including the near-final board.
Usage: python3 src/fetch.py data/2026-11-02.json
"""
import json, os, sys, time, urllib.request, urllib.error
BASE = os.environ.get("MS_BASE", "https://memestreet.net")
USER, PASS = os.environ["MS_USER"], os.environ["MS_PASS"]

def call(path, body=None, token=None):
    h = {"Content-Type": "application/json"}
    if token: h["X-Token"] = token
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers=h, method="POST" if body is not None else "GET")
    for attempt in range(5):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(3 * (attempt + 1)); continue
            raise SystemExit(f"{path}: HTTP {e.code} {e.read()[:200]!r}")
        except urllib.error.URLError:
            time.sleep(5)
    raise SystemExit(f"{path}: could not reach the server")

def main(out):
    tok = call("/api/login", {"name": USER, "password": PASS}).get("token")
    if not tok: raise SystemExit("login failed: check MS_USER / MS_PASS")
    d = call("/api/daily", token=tok)
    if d.get("status") == "new":
        print("starting today's chart (no trades will be placed)...")
        r = call("/api/daily/start", {}, tok)
        if r.get("error"): raise SystemExit("could not start: " + str(r["error"]))
        d["status"] = "running"
    t0 = time.time()
    while d.get("status") == "running" and time.time() - t0 < 300:
        time.sleep(5)
        d = call("/api/daily", token=tok)
    d = call("/api/daily", token=tok)     # final read: finished game + leaderboard as of now
    g = d.get("game") or {}
    if d.get("status") != "done" or not g.get("candles"):
        raise SystemExit(f"daily not finished (status={d.get('status')})")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(d, open(out, "w"))
    print(f"saved Daily #{d.get('number')}: {len(g['candles'])} candles, {len(d.get('board', []))} players on the board")

if __name__ == "__main__":
    main(sys.argv[1])
