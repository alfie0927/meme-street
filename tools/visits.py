"""Visits per day and per source, from the web server's visit log (the counting is in game/visitlog.py; the admin page
shows the same numbers).

    python3 tools/visits.py                       # on the server: /var/log/caddy/memestreet-access.log and its rolled copies
    python3 tools/visits.py FILE...               # other log files (plain or .gz)
    python3 tools/visits.py --selftest

For each day and source: visits, Daily Charts started, sign-up attempts and how many came through Instagram's own
browser.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))   # the game's code
import visitlog  # noqa: E402


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
             hit(7, "4.4.4.0", "GET", "/daily?ref=ig_bio"),                   # our bio link, in a normal browser
             hit(8, "4.4.4.0", "GET", "/api/auth_mode"),
             hit(9, "9.9.9.0", "GET", "/"),                                   # no script ran: a crawler, not a visit
             "not a log line",
             hit(86400, "1.2.3.0", "GET", "/learn", referer="https://memestreet.net/"),
             hit(86401, "1.2.3.0", "GET", "/api/auth_mode")]
    days = visitlog.count(lines)
    got = visitlog.summary(days)
    assert got["2026-11-10"] == {"reel": [1, 1, 1, 1], "www.google.com": [1, 0, 0, 0], "ig_bio": [1, 0, 0, 0]}, got
    assert got["2026-11-11"] == {"direct": [1, 0, 0, 0]}, got
    dash = visitlog.dashboard(days, "2026-11-11", 2)
    assert [(r["day"], r["visitors"], r["instagram"]) for r in dash] == [("2026-11-11", 1, 0), ("2026-11-10", 3, 2)], dash
    print("visits.py self-check ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        paths = sys.argv[1:] or visitlog.log_paths()
        if not paths:
            sys.exit(f"no log at {visitlog.LOG} (is the visit log on? deploy/Caddyfile)")
        show(visitlog.summary(visitlog.count(visitlog.lines_of(paths))))
