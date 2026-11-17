"""Where visitors come from, as the admin page counts them (game/visitlog.py)."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import visitlog  # noqa: E402

TS = 1794571200.0          # 2026-11-13 12:00 UTC


def hit(ip, uri, method="GET", ua="Mozilla/5.0", referer=None, ts=TS, status=200):
    heads = {"User-Agent": [ua]}
    if referer:
        heads["Referer"] = [referer]
    return json.dumps({"ts": ts, "status": status, "request": {"client_ip": ip, "uri": uri, "method": method, "headers": heads}})


def visit(ip, first, **k):
    return [hit(ip, first, **k), hit(ip, "/api/auth_mode", ts=k.get("ts", TS))]


class VisitLogTest(unittest.TestCase):
    def test_instagram_and_youtube_clicks_and_what_they_did(self):
        lines = (visit("1.1.1.0", "/play")                                                    # the reels' short address
                 + visit("2.2.2.0", "/yt") + [hit("2.2.2.0", "/api/daily/start", "POST"), hit("2.2.2.0", "/api/register", "POST")]
                 + visit("3.3.3.0", "/daily", referer="https://www.youtube.com/")             # a YouTube page's link
                 + visit("4.4.4.0", "/", ua="Mozilla/5.0 Instagram 300.0")                     # Instagram's own browser
                 + visit("5.5.5.0", "/")                                                       # direct
                 + [hit("6.6.6.0", "/yt")])                                                    # never ran the page: not a visit
        days = visitlog.count(lines)
        self.assertEqual(days["2026-11-13"]["1.1.1.0"]["src"], "reel")
        self.assertEqual(days["2026-11-13"]["2.2.2.0"]["src"], "yt")
        d = visitlog.dashboard(days, "2026-11-13", n=2)[0]
        self.assertEqual((d["visitors"], d["instagram"], d["youtube"]), (5, 2, 2))
        self.assertEqual(d["did"]["youtube"], {"starts": 1, "signups": 1})
        self.assertEqual(d["did"]["instagram"], {"starts": 0, "signups": 0})

    def test_the_weekly_funnel_per_source(self):
        """`weekly` (2026-11-17), the rows of growth/weekly.md: per ISO week and source, visits, Dailies started and
        finished, email requests and accounts that went through (a refusal answers 400), and visits that came back."""
        day = 86400
        hn = visit("1.1.1.0", "/daily", referer="https://news.ycombinator.com/")
        lines = (hn + [hit("1.1.1.0", "/api/daily/start", "POST")] + [hit("1.1.1.0", "/api/daily/state?since=3")] * 120
                 + [hit("1.1.1.0", "/api/daily/remind", "POST"), hit("1.1.1.0", "/api/daily/remind", "POST", status=400),
                    hit("1.1.1.0", "/api/register", "POST", status=400), hit("1.1.1.0", "/api/register", "POST")]
                 + visit("1.1.1.0", "/daily", ts=TS + day)                                    # back the next day
                 + visit("2.2.2.0", "/daily?ref=dle_hunt") + [hit("2.2.2.0", "/api/daily/start", "POST")] + [hit("2.2.2.0", "/api/daily/state")] * 30
                 + [hit("3.3.3.0", "/api/daily/start", "POST")] + [hit("3.3.3.0", "/api/daily/state")] * 120   # the reel pipeline: no page, no visit
                 + visit("2.2.2.0", "/daily", ts=TS + 9 * day))                               # nine days on: not "back within 7"
        w = visitlog.weekly(visitlog.count(lines))
        self.assertEqual(w["2026-W46"]["news.ycombinator.com"], [1, 1, 1, 1, 1, 1])
        self.assertEqual(w["2026-W46"]["dle_hunt"], [1, 1, 0, 0, 0, 0])
        self.assertEqual(w["2026-W46"]["direct"], [1, 0, 0, 0, 0, 0])                         # the HN visitor's second day
        self.assertEqual(sum(r[0] for r in w["2026-W46"].values()), 3)
        self.assertEqual(w["2026-W47"], {"direct": [1, 0, 0, 0, 0, 0]})


if __name__ == "__main__":
    unittest.main()
