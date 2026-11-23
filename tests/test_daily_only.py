"""memestreet.net as just the Daily (2026-11-18): real charts named at the end, streaks without an account carried into
one, a member's freeze, history and archive, the admin numbers, the market standing still, and the site serving the
Daily and nothing else (MS_FULL_SITE unset)."""
import http.client as httpc
import json
import os
import tempfile
import unittest
from types import SimpleNamespace

from _helpers import IsolatedServer, join, make_engine, quiet
from test_server import http
import daily

def head(srv, path):
    """A request that does not follow a redirect: (status, Location)."""
    c = httpc.HTTPConnection("127.0.0.1", srv.port, timeout=10)
    c.request("GET", path)
    r = c.getresponse()
    out = (r.status, r.getheader("location"))
    c.close()
    return out


V = lambda n: SimpleNamespace(token=f"v:visitor{n:013d}", name="You", visitor=True)


def play(e, p, side=None):
    """One whole game: start, maybe a trade, and the two minutes run out."""
    e.daily_start(p)
    if side:
        e.now += 3
        e.daily_trade(p, side, 1.0)
    e.now += daily.LIVE + 1
    return e.daily_view(p)


class RealChartTests(unittest.TestCase):
    def test_the_stock_is_named_only_after_the_game(self):
        e = make_engine(5)
        quiet(e)
        p = join(e, "revealer")
        v = e.daily_view(p)
        self.assertTrue(v["real"])
        self.assertNotIn("ticker", json.dumps(v))
        st = e.daily_start(p)
        self.assertNotIn("real", st)
        self.assertEqual(st["price"], round(e._dchart()["chart"]["real"]["first"], 4))   # (the stock's real price, since 2026-11-23)
        e.now += 30
        self.assertNotIn("real", e.daily_poll(p))
        e.now += daily.LIVE
        g = e.daily_view(p)["game"]
        r = g["real"]
        self.assertNotIn("i", r)
        self.assertIn(r["ticker"], {x["t"] for x in daily.real_bank()})
        self.assertTrue(r["name"] and r["from"] < r["start"] < r["end"])
        cs = e.daily_game["chart"]["candles"]
        self.assertAlmostEqual(cs[-1][3] * r["k"], r["last"], delta=0.006 * r["k"] + 1e-9)   # shown x k = real
        self.assertAlmostEqual(g["hold"], r["last"] / r["first"] - 1, delta=0.01)
        self.assertIn(r["tf"], ("1 day", "2 days", "1 week"))                 # the timeframe, revealed with the name
        self.assertIn(v["tomorrow"]["tf"], ("1 day", "2 days", "1 week"))      # (tomorrow's timeframe, never its stock)
        self.assertNotIn("levels", st)
        for lv in g["levels"]:                                               # the levels it tested, only now
            self.assertIn(lv["kind"], ("support", "resistance"))
            self.assertTrue(all(daily.HISTORY <= k < daily.HISTORY + daily.LIVE and o in ("held", "broke", "fake break") for k, o in lv["tests"]))

    def test_the_best_short_is_the_fall_over_the_price_it_was_sold_at(self):
        cs = [[100, 100, 100, 100, 1]] * daily.HISTORY + [[100 - k * 0.5] * 4 + [1] for k in range(daily.LIVE + 1)]
        b = daily.DailyMixin._daily_best(cs[:daily.HISTORY + daily.LIVE])
        self.assertEqual(b["side"], "short")
        self.assertAlmostEqual(b["ret"], 1 - cs[daily.HISTORY + daily.LIVE - 1][3] / 100, places=6)   # (100 to 40.5: 59.5%, not 147%)

    def test_every_real_chart_has_levels_from_its_own_swings(self):
        bank = daily.real_bank()
        counts = [len(daily.rebased(x, i)["levels"]) for i, x in enumerate(bank)]
        self.assertGreater(sum(c > 0 for c in counts), 0.9 * len(bank))
        self.assertTrue(all(c <= daily.LEVELS_SHOWN for c in counts))
        self.assertGreaterEqual({x.get("tf") for x in bank}, {"1 day", "2 days", "1 week"})

    def test_the_charts_are_in_a_secret_order_sound_and_a_year_without_a_repeat(self):
        bank = daily.real_bank()
        self.assertGreaterEqual(len(bank), 365)
        for x in bank:
            self.assertEqual(len(x["c"]), daily.HISTORY + daily.LIVE)
            self.assertTrue(all(0 < lo <= min(o, c) <= max(o, c) <= h for o, h, lo, c, v in x["c"]), x["t"])
        d0 = daily.EPOCH_DAY + 30
        seen = [daily.real_chart("salt-a", d0 + k)["real"]["i"] for k in range(len(bank))]
        self.assertEqual(len(set(seen)), len(bank))                          # every chart once before any repeats
        self.assertEqual(daily.real_chart("salt-a", d0), daily.real_chart("salt-a", d0))
        self.assertNotEqual([daily.real_chart("salt-b", d0 + k)["real"]["i"] for k in range(5)], seen[:5])   # (the salt decides)
        self.assertNotEqual(daily.real_chart("salt-a", d0, resets=1)["real"]["i"], seen[0])
        self.assertIsNone(daily.real_chart("salt-a", d0, bank=[]))            # no bank: the model's chart instead
        self.assertEqual(daily.real_bank(os.path.join(tempfile.gettempdir(), "no-such-bank.json")), [])

    def test_the_market_stands_still_and_the_house_still_plays(self):
        e = make_engine(5, house_bots=True)
        prices = {t: s.price for t, s in e.stocks.items()}
        for k in range(200):
            e.daily_tick(e.now + 60)
        self.assertEqual(prices, {t: s.price for t, s in e.stocks.items()})   # (no market: not a cent moved)
        e.daily_view(join(e, "watcher"))
        self.assertIsNotNone(e.daily_game["day"])


class StreakTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(5)
        quiet(self.e)

    def test_a_visitor_keeps_a_streak_without_an_account(self):
        e, v = self.e, V(1)
        for day in range(3):
            st = play(e, v, "buy" if day == 1 else None)["stats"]
            self.assertEqual((st["played"], st["streak"], st["freezes"]), (day + 1, day + 1, 0))
            e.now += daily.DAY_SECONDS
        e.now += daily.DAY_SECONDS                                              # a visitor has no freeze: a missed day ends it
        self.assertEqual(e.daily_view(v)["stats"]["streak"], 0)
        self.assertEqual(len(e.daily_game["hist"][v.token]), 3)

    def test_signing_up_brings_the_streak_the_history_and_today(self):
        e, v = self.e, V(2)
        for _ in range(2):
            play(e, v, "buy")
            e.now += daily.DAY_SECONDS
        e.daily_start(v)                                                      # today, still running
        p = join(e, "newbie")
        self.assertTrue(e.daily_claim(p, v.token[2:]))
        self.assertNotIn(v.token, e.daily_game["stats"])
        e.now += daily.LIVE + 1
        out = e.daily_view(p)
        self.assertEqual((out["stats"]["played"], out["stats"]["streak"], out["stats"]["freezes"]), (3, 3, 1))
        self.assertEqual([r["number"] for r in e.daily_history(p)["rows"]], [out["number"], out["number"] - 1, out["number"] - 2])
        self.assertIn("newbie", [b["name"] for b in out["board"]])

    def test_logging_in_merges_and_a_day_both_played_counts_once(self):
        e, v = self.e, V(3)
        p = join(e, "veteran")
        for _ in range(3):
            play(e, p, "buy")
            e.now += daily.DAY_SECONDS
        play(e, p, "sell")                                                     # the account plays today on one device...
        play(e, v)                                                             # ...and as a visitor on another
        before = dict(e.daily_game["stats"][p.token])
        self.assertFalse(e.daily_claim(p, v.token[2:]))                       # (today's board keeps the account's game)
        st = e.daily_game["stats"][p.token]
        self.assertEqual((st["played"], st["streak"]), (before["played"], before["streak"]))
        self.assertAlmostEqual(st["sum"], before["sum"])
        self.assertEqual(len(e.daily_game["hist"][p.token]), 4)

    def test_a_freeze_is_earned_every_seven_games_two_at_most(self):
        e, p = self.e, join(self.e, "grinder")
        for k in range(15):
            st = play(e, p)["stats"]
            e.now += daily.DAY_SECONDS
        self.assertEqual(st["freezes"], daily.FREEZES)                        # 1 to start, +1 at 7, +1 at 14 capped at 2
        self.assertEqual(st["streak"], 15)

    def test_history_and_the_archive_are_a_members_and_replay_the_real_past(self):
        e, p, v = self.e, join(self.e, "historian"), V(4)
        first = play(e, p, "buy")
        e.now += daily.DAY_SECONDS
        self.assertTrue(e.daily_history(v)["need_account"])
        self.assertTrue(e.daily_archive(v)["need_account"])
        arc = e.daily_archive(p)["days"]
        self.assertEqual([a["number"] for a in arc], [first["number"]])
        self.assertEqual(arc[0]["ticker"], first["game"]["real"]["ticker"])
        self.assertAlmostEqual(arc[0]["mine"], first["game"]["ret"], places=5)
        past = e.daily_past(p, first["number"])
        self.assertEqual(len(past["candles"]), daily.HISTORY + daily.LIVE)
        self.assertEqual(past["real"]["ticker"], first["game"]["real"]["ticker"])
        self.assertIn("error", e.daily_past(p, first["number"] + 1))          # (today's stock is never in the archive)
        self.assertIn("error", e.daily_past(p, "x"))

    def test_the_admin_numbers_for_the_dashboard(self):
        e = self.e
        a, v = join(e, "member"), V(5)
        e.daily_event(v, "share")
        e.daily_event(v, "nonsense")
        e.daily_start(v, ref="ig_bio")
        e.daily_start(a, ref="Bad Ref!")
        e.daily_start(SimpleNamespace(token="v:reelbot0123456789ab", name="You", visitor=True))   # (the reel pipeline: never a person)
        e.now += daily.LIVE + 1
        out = e.daily_admin()
        t = out["today"]
        self.assertEqual((t["people"], t["visitors"], t["refs"], t["ev"]), (1, 1, {"ig_bio": 1}, {"share": 1}))
        self.assertEqual(t["new"], 2)
        self.assertEqual((out["members"]["players"], out["visitors"]["players"]), (1, 1))
        e.now += daily.DAY_SECONDS
        play(e, v)
        out = e.daily_admin()
        self.assertEqual(out["days"][0]["stock"], out["stocks"][0]["stock"])
        c = next(c for c in out["cohorts"] if c["day"] == out["days"][0]["day"])
        self.assertEqual((c["new"], c["members"], c["d1"], c["again"]), (2, 1, 1, 1))
        self.assertIn(("ig_bio", 1), out["refs"])
        self.assertEqual(out["archive"], 1)


class SiteTests(unittest.TestCase):
    def test_memestreet_net_is_the_daily_and_nothing_else(self):
        with IsolatedServer(settings={"daily_chart": True}, env={"MS_FULL_SITE": ""}) as srv:
            status, text, _ = http(srv, "/")
            self.assertEqual(status, 200)
            self.assertIn("MemeStreet: The Daily Trading Game", text)
            self.assertNotIn("<!--", text[:text.index("<title>")].split("-->")[-1])   # (the title is not inside a comment)
            self.assertIn('<link rel="canonical" href="https://memestreet.net/">', text)
            self.assertIn("One real stock.", text)                              # (the opening words, before the script)
            self.assertIn("got +3.1% on Meme Street #9", http(srv, "/?vs=Sam~310~9")[1])
            for path in ("/learn", "/portfolio", "/stock/ABC", "/lessons/stocks-shares", "/shop", "/vs", "/about", "/learn?l=x"):
                self.assertEqual(head(srv, path), (301, "/"), path)
            for path in ("/privacy", "/terms", "/robots.txt", "/admin", "/daily"):
                self.assertEqual(http(srv, path)[0], 200, path)
            self.assertIn("Meme Street Daily", http(srv, "/admin")[1])
            self.assertEqual(http(srv, "/api/portfolio")[0], 410)
            self.assertEqual(http(srv, "/api/learn")[0], 410)
            self.assertEqual(http(srv, "/api/shop/checkout", "POST", {})[0], 410)
            sm = http(srv, "/sitemap.xml")[1]
            self.assertEqual(sm.count("<loc>"), 1)
            h = {"X-Visitor": "q" * 20}
            self.assertTrue(json.loads(http(srv, "/api/daily", headers=h)[1])["real"])
            self.assertIn("candles", json.loads(http(srv, "/api/daily/start", "POST", {"ref": "reel"}, headers=h)[1]))
            self.assertTrue(json.loads(http(srv, "/api/daily/event", "POST", {"kind": "share"}, headers=h)[1])["ok"])
            self.assertTrue(json.loads(http(srv, "/api/daily/history", headers=h)[1])["need_account"])
            self.assertEqual(head(srv, "/play"), (307, "/?ref=reel"))


if __name__ == "__main__":
    unittest.main()
