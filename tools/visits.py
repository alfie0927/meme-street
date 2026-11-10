"""Visits per day and per source, from the web server's visit log (deploy/Caddyfile `log`, growth plan 2026-11-10).

    python3 tools/visits.py                       # on the server: /var/log/caddy/memestreet-access.log and its rolled copies
    python3 tools/visits.py FILE...               # other log files (plain or .gz)
    python3 tools/visits.py --selftest

A visit is an address that loaded the game page and ran its script (the page asks for /api/auth_mode) on a day. Its
source is the ?ref= of its first page that day, else the site it came from (the Referer), else "direct". For each day and
source: visits, Daily Charts started (POST /api/daily/start), sign-up attempts (POST /api/register) and how many came
through Instagram's own browser. The log keeps addresses cut short, so people on one small network count once.
"""
import collections
import datetime
import glob
import gzip
import json
import sys
import urllib.parse

LOG = "/var/log/caddy/memestreet-access.log"
NOT_PAGES = ("/api/", "/js/", "/brand/", "/ws", "/reels/", "/favicon")


def lines_of(paths):
    for path in paths:
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rt", encoding="utf-8", errors="replace") as f:
            yield from f


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


def show(table):
    for day in sorted(table):
        rows = sorted(table[day].items(), key=lambda kv: -kv[1][0])
        tot = [sum(x[i] for _, x in rows) for i in range(4)]
        print(f"{day}  visits {tot[0]}  Daily starts {tot[1]}  sign-up attempts {tot[2]}  in Instagram's browser {tot[3]}")
        for src, (n, starts, signups, ig) in rows:
            print(f"    {src:28} {n:4} visits {starts:4} starts {signups:3} sign-up attempts {ig:4} Instagram")


def selftest():
    t = datetime.datetime(2026, 11, 10, tzinfo=datetime.timezone.utc).timestamp()

    def hit(dt, who, method, uri, ua="Mozilla/5.0", referer=""):
        heads = {"User-Agent": [ua]}
        if referer:
            heads["Referer"] = [referer]
        return json.dumps({"ts": t + dt, "request": {"client_ip": who, "method": method, "uri": uri, "headers": heads}})
    lines = [hit(0, "1.2.3.0", "GET", "/daily?ref=reel", ua="Mozilla/5.0 Instagram 309.0"),
             hit(1, "1.2.3.0", "GET", "/api/auth_mode"),
             hit(2, "1.2.3.0", "POST", "/api/daily/start"),
             hit(200, "1.2.3.0", "POST", "/api/register"),
             hit(5, "5.6.7.0", "GET", "/", referer="https://www.google.com/"),
             hit(6, "5.6.7.0", "GET", "/api/auth_mode"),
             hit(9, "9.9.9.0", "GET", "/"),                                   # no script ran: a crawler, not a visit
             "not a log line",
             hit(86400, "1.2.3.0", "GET", "/learn", referer="https://memestreet.net/"),
             hit(86401, "1.2.3.0", "GET", "/api/auth_mode")]
    got = summary(count(lines))
    assert got["2026-11-10"] == {"reel": [1, 1, 1, 1], "www.google.com": [1, 0, 0, 0]}, got
    assert got["2026-11-11"] == {"direct": [1, 0, 0, 0]}, got
    print("visits.py self-check ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        paths = sys.argv[1:] or sorted(glob.glob(LOG + "*"))
        if not paths:
            sys.exit(f"no log at {LOG} (is the visit log on? deploy/Caddyfile)")
        show(summary(count(lines_of(paths))))
