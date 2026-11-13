"""Where visitors come from, as the admin page counts them (game/visitlog.py)."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import visitlog  # noqa: E402

TS = 1794571200.0          # 2026-11-13 12:00 UTC


def hit(ip, uri, method="GET", ua="Mozilla/5.0", referer=None, ts=TS):
    heads = {"User-Agent": [ua]}
    if referer:
        heads["Referer"] = [referer]
    return json.dumps({"ts": ts, "request": {"client_ip": ip, "uri": uri, "method": method, "headers": heads}})


def visit(ip, first, **k):
    return [hit(ip, first, **k), hit(ip, "/api/auth_mode")]


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


if __name__ == "__main__":
    unittest.main()
