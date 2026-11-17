"""Visits per day and per source, from the web server's visit log (the counting is in game/visitlog.py; the admin page
shows the same numbers).

    python3 tools/visits.py                       # on the server: /var/log/caddy/memestreet-access.log and its rolled copies
    python3 tools/visits.py FILE...               # other log files (plain or .gz)
    python3 tools/visits.py --weekly [FILE...]    # the week's funnel per source, as rows for growth/weekly.md
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


def show_weekly(table):
    print("| Week | Source | Visits | Daily started | Daily finished | Email asked | Accounts | Back within 7 days |")
    print("|---|---|---|---|---|---|---|---|")
    for week in sorted(table):
        for src, row in sorted(table[week].items(), key=lambda kv: -kv[1][0]):
            print(f"| {week} | {src} | " + " | ".join(str(int(x)) for x in row) + " |")


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
    def hit2(dt, who, method, uri, status=200):
        return json.dumps({"ts": t + dt, "status": status, "request": {"client_ip": who, "method": method, "uri": uri, "headers": {}}})
    lines += ([hit2(20, "5.6.7.0", "POST", "/api/daily/start")] + [hit2(21 + k, "5.6.7.0", "GET", "/api/daily/state?since=1") for k in range(120)]
              + [hit2(150, "5.6.7.0", "POST", "/api/daily/remind"), hit2(151, "5.6.7.0", "POST", "/api/daily/remind", 400),
                 hit2(160, "5.6.7.0", "POST", "/api/register", 400), hit2(170, "5.6.7.0", "POST", "/api/register")])
    week = visitlog.weekly(visitlog.count(lines))
    assert week["2026-W46"]["www.google.com"] == [1, 1, 1, 1, 1, 0], week
    assert week["2026-W46"]["reel"] == [1, 1, 0, 0, 0, 1], week            # (came back the next day)
    print("visits.py self-check ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        paths = [a for a in sys.argv[1:] if not a.startswith("--")] or visitlog.log_paths()
        if not paths:
            sys.exit(f"no log at {visitlog.LOG} (is the visit log on? deploy/Caddyfile)")
        days = visitlog.count(visitlog.lines_of(paths))
        if "--weekly" in sys.argv:
            show_weekly(visitlog.weekly(days))
        else:
            show(visitlog.summary(days))
