"""Fetch today's Daily Chart (candles, levels, leaderboard) from memestreet.net.

Plays as a logged-out visitor (no account needed, and visitors stay off the leaderboard).
If the visitor hasn't played today, it starts the game and waits ~2 minutes for it to finish
(no trades are placed), then saves the full /api/daily response, including the board as of now.
Optional: set MS_USER / MS_PASS in config.env to play with an account instead.
Usage: python3 src/fetch.py data/2026-11-02.json
"""
import json, os, secrets, sys, time, urllib.request, urllib.error
BASE = os.environ.get("MS_BASE", "https://memestreet.net")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state")

def visitor_id():
    """A stable visitor id for the bot (same format the site's browser code uses)."""
    os.makedirs(STATE, exist_ok=True); p = os.path.join(STATE, "visitor_id")
    if os.path.exists(p): return open(p).read().strip()
    v = secrets.token_hex(16); open(p, "w").write(v); return v

def call(path, headers, body=None):
    h = dict(headers, **({"Content-Type": "application/json"} if body is not None else {}))
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
    user, pw = os.environ.get("MS_USER", "").strip(), os.environ.get("MS_PASS", "").strip()
    if user and pw:                                   # optional: play with an account
        tok = call("/api/login", {}, {"name": user, "password": pw}).get("token")
        if not tok: raise SystemExit("login failed: check MS_USER / MS_PASS (or remove them to play as a guest)")
        H = {"X-Token": tok}; who = f"account {user}"
    else:                                             # default: guest visitor, off the leaderboard
        H = {"X-Visitor": visitor_id()}; who = "guest visitor"
    d = call("/api/daily", H)
    if d.get("status") == "new":
        print(f"starting today's chart as a {who} (no trades will be placed)...")
        call("/api/daily/start", H, {})
        d["status"] = "running"
    t0 = time.time()
    while d.get("status") == "running" and time.time() - t0 < 300:
        time.sleep(5); d = call("/api/daily", H)
    d = call("/api/daily", H)                         # final read: finished game + leaderboard as of now
    g = d.get("game") or {}
    if d.get("status") != "done" or not g.get("candles"):
        raise SystemExit(f"daily not finished (status={d.get('status')})")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(d, open(out, "w"))
    print(f"saved Daily #{d.get('number')}: {len(g['candles'])} candles, {len(d.get('board', []))} players on the board")

if __name__ == "__main__":
    main(sys.argv[1])
