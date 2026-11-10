"""Counting visits from the web server's visit log (deploy/Caddyfile `log`, growth plan 2026-11-10). Used by the admin
page (`/api/admin/visits`) and by tools/visits.py.

A visit is an address that loaded the game page and ran its script (the page asks for /api/auth_mode) on a day. Its
source is the ?ref= of its first page that day, else the site it came from (the Referer), else "direct". The log keeps
addresses cut short, so people on one small network count once."""
import collections
import datetime
import glob
import gzip
import json
import urllib.parse

LOG = "/var/log/caddy/memestreet-access.log"
NOT_PAGES = ("/api/", "/js/", "/brand/", "/ws", "/reels/", "/favicon")


def lines_of(paths):
    for path in paths:
        opener = gzip.open if path.endswith(".gz") else open
        try:
            with opener(path, "rt", encoding="utf-8", errors="replace") as f:
                yield from f
        except OSError:
            continue                                   # (a rolled file can vanish between the listing and the read)


def log_paths():
    return sorted(glob.glob(LOG + "*"))


def count(lines):
    """day -> address -> what it did that day."""
    days = collections.defaultdict(dict)
    for line in lines:
        try:
            j = json.loads(line)
        except ValueError:
            continue
        r = j.get("request") if isinstance(j, dict) else None
        if not isinstance(r, dict):
            continue
        day = datetime.datetime.fromtimestamp(float(j.get("ts", 0)), datetime.timezone.utc).strftime("%Y-%m-%d")
        who = r.get("client_ip") or r.get("remote_ip") or "?"
        path, _, query = str(r.get("uri", "")).partition("?")
        heads = r.get("headers") or {}
        v = days[day].setdefault(who, {"src": None, "seen": False, "starts": 0, "signups": 0, "ig": False})
        if any("Instagram" in ua for ua in heads.get("User-Agent", [])):
            v["ig"] = True
        method = r.get("method")
        if v["src"] is None and method == "GET" and not path.startswith(NOT_PAGES):
            ref = (urllib.parse.parse_qs(query).get("ref") or [""])[0].strip().lower()[:40]
            host = urllib.parse.urlparse((heads.get("Referer") or [""])[0]).hostname or ""
            v["src"] = ref or (host if host and not host.endswith("memestreet.net") else "direct")
        if path == "/api/auth_mode":
            v["seen"] = True
        elif method == "POST" and path == "/api/daily/start":
            v["starts"] += 1
        elif method == "POST" and path == "/api/register":
            v["signups"] += 1
    return days


def from_instagram(v):
    """Came through Instagram: its own browser, an Instagram address, or one of our Instagram links (ig_..., reel)."""
    src = v["src"] or ""
    return v["ig"] or "instagram" in src or src.startswith("ig_") or src == "reel"


def summary(days):
    """day -> source -> [visits, Daily starts, sign-up attempts, through Instagram's browser]."""
    out = {}
    for day, people in days.items():
        by = collections.defaultdict(lambda: [0, 0, 0, 0])
        for v in people.values():
            if v["seen"]:
                b = by[v["src"] or "direct"]
                b[0] += 1
                b[1] += v["starts"]
                b[2] += v["signups"]
                b[3] += v["ig"]
        out[day] = dict(by)
    return out


def dashboard(days, today, n=7):
    """The admin page's numbers: per day (newest first, `n` days to `today`) the visitors and those from Instagram."""
    t = datetime.date.fromisoformat(today)
    rows = []
    for k in range(n):
        day = (t - datetime.timedelta(days=k)).isoformat()
        seen = [v for v in days.get(day, {}).values() if v["seen"]]
        rows.append({"day": day, "visitors": len(seen), "instagram": sum(1 for v in seen if from_instagram(v)),
                     "starts": sum(v["starts"] for v in seen), "signups": sum(v["signups"] for v in seen)})
    return rows
