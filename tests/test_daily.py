"""The Daily Chart (daily.py): the day's chart (the same for everyone, made by the price model, volatile, saved), a game
(the candles shown one a second and never ahead, trades at the last close, the end), one game a day, the board, the
day changing over, and the endpoints."""
import json
import math
import os
import statistics
import tempfile
import unittest

from _helpers import IsolatedServer, engine, join, make_engine, quiet
from test_server import http
import daily


class ChartTests(unittest.TestCase):
    def test_the_chart_is_the_same_for_the_same_seed_and_sound(self):
        a, b, c = daily.make_chart(7), daily.make_chart(7), daily.make_chart(8)
        self.assertEqual(a, b)
        self.assertNotEqual(a["candles"], c["candles"])
        self.assertEqual(len(a["candles"]), daily.HISTORY + daily.LIVE)
        for o, h, lo, cl, v in a["candles"]:
            self.assertTrue(0 < lo <= min(o, cl) <= max(o, cl) <= h, (o, h, lo, cl))
            self.assertGreaterEqual(v, 0)

    def test_it_is_volatile_and_varies_from_day_to_day(self):
        ranges, vols = [], []
        for seed in range(30):
            ch = daily.make_chart(500 + seed)
            live = ch["candles"][daily.HISTORY:]
            ranges.append(max(c[1] for c in live) / min(c[2] for c in live) - 1)
            vols.append(ch["vol"])
        self.assertGreater(statistics.median(ranges), 0.06)          # the price usually swings 10% or more...
        self.assertGreater(max(ranges), 2 * min(ranges))              # ...more on some days than on others
        self.assertGreater(max(vols), 2 * min(vols))

    def test_the_moves_are_not_a_plain_random_walk(self):
        """The price model's structure is in it: one-second returns cluster in size (volatility clustering), as the
        market's do, and the moves have fat tails."""
        rs = []
        for seed in range(20):
            cs = daily.make_chart(900 + seed)["candles"]
            r = [math.log(b[3] / a[3]) for a, b in zip(cs, cs[1:])]
            sd = statistics.pstdev(r)
            rs += [x / sd for x in r]
        a = [abs(x) for x in rs]
        m = statistics.mean(a)
        ac = sum((a[i] - m) * (a[i + 1] - m) for i in range(len(a) - 1)) / sum((x - m) ** 2 for x in a)
        self.assertGreater(ac, 0.03)                                                  # big moves follow big moves
        kurt = statistics.mean(x ** 4 for x in rs) / statistics.mean(x ** 2 for x in rs) ** 2
        self.assertGreater(kurt, 3.0)


class GameTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(5)
        quiet(self.e)
        self.p = join(self.e, "dasher")

    def test_the_chart_is_the_same_for_everyone_and_kept_for_the_day(self):
        e = self.e
        q = join(e, "other")
        a = e.daily_view(self.p)
        chart = e.daily_game["chart"]
        self.assertEqual(e.daily_view(q)["day"], a["day"])
        self.assertIs(e.daily_game["chart"], chart)
        e.now += 3600
        e.daily_view(q)
        self.assertIs(e.daily_game["chart"], chart)                                 # (made once a day)

    def test_a_game_shows_the_candles_one_a_second_and_never_ahead(self):
        e, p = self.e, self.p
        st = e.daily_start(p)
        cs = e.daily_game["chart"]["candles"]
        self.assertEqual(len(st["candles"]), daily.HISTORY)                          # the lead-in only
        self.assertEqual(st["price"], cs[daily.HISTORY - 1][3])
        e.now += 10.4
        st = e.daily_poll(p, daily.HISTORY)
        self.assertEqual(st["from"], daily.HISTORY)
        self.assertEqual(len(st["candles"]), 10)                                     # ten seconds: ten more
        self.assertEqual(st["shown"], daily.HISTORY + 10)
        self.assertEqual(st["candles"], cs[daily.HISTORY:daily.HISTORY + 10])
        self.assertEqual(len(e.daily_poll(p, 10 ** 6)["candles"]), 0)                # asking ahead gets nothing
        self.assertNotIn("candles", json.dumps(e.daily_view(join(e, "spy"))))       # nor does anyone who has not started

    def test_trades_at_the_last_close_and_the_end(self):
        e, p = self.e, self.p
        e.daily_start(p)
        cs = e.daily_game["chart"]["candles"]
        e.now += 5.2
        price = cs[daily.HISTORY + 4][3]
        st = e.daily_trade(p, "buy", 0.5)
        self.assertNotIn("error", st)
        self.assertAlmostEqual(st["cash"], 500, places=6)
        self.assertAlmostEqual(st["shares"], 500 / price, places=9)
        for bad in (("buy", 0.3), ("short", 0.5), ("sell", "x")):
            self.assertIn("error", e.daily_trade(p, *bad))
        e.now += 20
        price2 = cs[daily.HISTORY + 24][3]
        st = e.daily_trade(p, "sell", 1.0)
        self.assertAlmostEqual(st["cash"], 500 + 500 / price * price2, places=6)
        self.assertEqual(st["shares"], 0)
        st = e.daily_trade(p, "buy", 1.0)
        held = st["shares"]
        self.assertEqual(st["trades"][-1][1], "buy")
        e.now += daily.LIVE                                                           # time is up
        self.assertIn("error", e.daily_trade(p, "buy", 0.25))
        st = e.daily_poll(p, 0)
        self.assertTrue(st["done"])
        self.assertEqual(len(st["candles"]), len(cs))                                # now the whole chart
        self.assertAlmostEqual(st["ret"], held * cs[-1][3] / 1000 - 1, places=9)
        self.assertEqual(st["rank"], 1)

    def test_shorts_and_covering(self):
        e, p = self.e, self.p
        e.daily_start(p)
        cs = e.daily_game["chart"]["candles"]
        e.now += 3.1
        price = cs[daily.HISTORY + 2][3]
        st = e.daily_trade(p, "sell", 1.0)                                           # no shares: a short
        self.assertNotIn("error", st)
        self.assertEqual(st["trades"][-1][1], "short")
        self.assertAlmostEqual(st["shares"], -1000 / price, places=9)
        self.assertAlmostEqual(st["cash"], 2000, places=6)
        self.assertAlmostEqual(st["equity"], 1000, places=6)                         # nothing gained or lost yet
        self.assertIn("error", e.daily_trade(p, "sell", 0.5))                        # already as short as the account allows
        e.now += 5
        price2 = cs[daily.HISTORY + 7][3]
        st = e.daily_trade(p, "buy", 0.5)                                            # buying covers half of it
        self.assertEqual(st["trades"][-1][1], "cover")
        self.assertAlmostEqual(st["shares"], -500 / price, places=9)
        self.assertAlmostEqual(st["equity"], 1000 + 1000 / price * (price - price2), places=6)
        st = e.daily_trade(p, "buy", 1.0)
        self.assertEqual(st["shares"], 0)
        st = e.daily_trade(p, "sell", 0.5)                                           # flat again: a new short, half
        self.assertEqual(st["trades"][-1][1], "short")
        e.now += daily.LIVE
        st = e.daily_poll(p, 0)
        self.assertTrue(st["done"])
        self.assertAlmostEqual(st["ret"], st["equity"] / 1000 - 1, places=9)

    def test_a_short_cannot_lose_more_than_everything(self):
        e, p = self.e, self.p
        e.daily_start(p)
        e.daily_trade(p, "sell", 1.0)
        cs = e.daily_game["chart"]["candles"]
        cs[-1][3] = cs[daily.HISTORY - 1][3] * 3                                     # (the price triples by the end)
        e.now += daily.LIVE
        st = e.daily_poll(p, 0)
        self.assertEqual(st["ret"], -1.0)
        self.assertEqual(st["equity"], 0.0)

    def test_the_summary_at_the_end(self):
        e = self.e
        players = [join(e, f"s{i}") for i in range(4)]
        for i, pl in enumerate(players):
            e.daily_start(pl)
            if i % 2:
                e.daily_trade(pl, "buy", 1.0)
            elif i:
                e.daily_trade(pl, "sell", 1.0)
        e.now += daily.LIVE + 1
        st = e.daily_poll(players[1], 0)
        cs = e.daily_game["chart"]["candles"]
        self.assertEqual(len(st["dist"]), 4)                                         # everyone's return, no names
        self.assertEqual(st["dist"], sorted(st["dist"]))
        self.assertIn(round(st["ret"], 6), [round(r, 6) for r in st["dist"]])
        self.assertAlmostEqual(st["hold"], cs[-1][3] / cs[daily.HISTORY - 1][3] - 1, places=9)
        self.assertEqual(st["hi"], max(c[1] for c in cs[daily.HISTORY:]))
        self.assertEqual(st["lo"], min(c[2] for c in cs[daily.HISTORY:]))
        self.assertNotIn("dist", e.daily_view(join(e, "late"))["board"][0])          # (the board: names and returns only)

    def test_one_game_a_day_and_the_board(self):
        e = self.e
        players = [join(e, f"r{i}") for i in range(3)]
        cs = None
        for i, pl in enumerate(players):
            e.daily_start(pl)
            cs = e.daily_game["chart"]["candles"]
            if i:                                                                     # (one does nothing: 0%)
                e.daily_trade(pl, "buy", 1.0)
        self.assertIn("error", e.daily_start(players[0]))                            # once a day
        self.assertIn("error", e.daily_start(e.guest))
        e.now += daily.LIVE + 1
        board = e.daily_view(players[0])["board"]
        self.assertEqual(len(board), 3)
        self.assertEqual([x["ret"] for x in board], sorted((x["ret"] for x in board), reverse=True))
        self.assertTrue(any(x["name"] == "r0" and x["ret"] == 0 for x in board))
        self.assertEqual(e.daily_view(players[0])["status"], "done")
        self.assertIsNotNone(cs)

    def test_a_new_day_brings_a_new_chart_and_keeps_the_winners(self):
        e, p = self.e, self.p
        e.daily_start(p)
        e.daily_trade(p, "buy", 1.0)
        first = e.daily_game["chart"]
        e.now += daily.DAY_SECONDS
        v = e.daily_view(p)
        self.assertEqual(v["status"], "new")                                         # a new day: play again
        self.assertIsNot(e.daily_game["chart"], first)
        self.assertNotEqual(e.daily_game["chart"]["candles"], first["candles"])
        self.assertEqual(v["past"][0]["top"][0]["name"], "dasher")
        self.assertEqual(v["past"][0]["players"], 1)
        self.assertNotIn("error", e.daily_start(p))

    def test_numbered_days_streaks_and_stats(self):
        """Like the daily word games: each day a number, a streak of days in a row (a missed day ends it), and stats."""
        e, p = self.e, self.p
        first = e.daily_view(p)
        self.assertEqual(first["number"], first["day"] - daily.EPOCH_DAY + 1)
        self.assertEqual(first["stats"]["played"], 0)
        for day in range(3):                                               # three days in a row
            e.daily_start(p)
            if day == 1:
                e.daily_trade(p, "buy", 1.0)
            e.now += daily.LIVE + 1
            st = e.daily_view(p)["stats"]
            self.assertEqual((st["played"], st["streak"]), (day + 1, day + 1))
            e.now += daily.DAY_SECONDS
        self.assertEqual(e.daily_view(p)["stats"]["streak"], 3)           # (yesterday counts: today is still to play)
        self.assertEqual(e.daily_view(p)["number"], first["number"] + 3)
        e.now += daily.DAY_SECONDS                                          # a day missed
        st = e.daily_view(p)["stats"]
        self.assertEqual((st["streak"], st["max_streak"], st["played"]), (0, 3, 3))
        e.daily_start(p)
        e.now += daily.LIVE + 1
        st = e.daily_view(p)["stats"]
        self.assertEqual((st["streak"], st["max_streak"], st["played"]), (1, 3, 4))
        self.assertIsNotNone(st["avg"])
        self.assertLessEqual(st["beat"], st["played"])

    def test_the_result_grid(self):
        """Eight squares, one per 15 seconds: flat while in cash, then up or down with the account's worth."""
        e, p = self.e, self.p
        e.daily_start(p)
        e.now += daily.LIVE // 2                                            # half way: buy everything
        e.daily_trade(p, "buy", 1.0)
        e.now += daily.LIVE
        g = e.daily_view(p)["game"]
        self.assertEqual(len(g["grid"]), daily.SQUARES)
        self.assertEqual(g["grid"][:daily.SQUARES // 2 - 1], [0] * (daily.SQUARES // 2 - 1))   # in cash: flat
        cs = e.daily_game["chart"]["candles"]
        step = daily.LIVE // daily.SQUARES
        for k in range(daily.SQUARES // 2, daily.SQUARES):                 # held the stock: its own move
            a, b = cs[daily.HISTORY - 1 + k * step][3], cs[daily.HISTORY - 1 + (k + 1) * step][3]
            want = 0 if abs(b - a) <= 0.0005 * a else (1 if b > a else -1)
            self.assertEqual(g["grid"][k], want, k)

    def test_the_game_survives_a_save(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            a = engine.Engine(state_file=os.path.join(tmp, "state.json"))
            a.tick(now=a.now)
            quiet(a)
            p = join(a, "saver")
            a.daily_start(p)
            a.now += 3
            a.daily_trade(p, "buy", 0.75)
            a.save()
            b = engine.Engine(state_file=os.path.join(tmp, "state.json"))
            self.assertEqual(b.daily_game["chart"], a.daily_game["chart"])
            self.assertEqual(b.daily_game["salt"], a.daily_game["salt"])
            q = b.by_token[p.token]
            b.now = a.now
            self.assertEqual(b.daily_poll(q, 0)["trades"], a.daily_poll(p, 0)["trades"])


class ServerTests(unittest.TestCase):
    def test_on_the_site_and_switchable_off(self):
        """Back on the site (2026-10-24): the page, the script and the header button; with `daily_chart` off the endpoints
        answer 404."""
        with IsolatedServer() as srv:
            self.assertEqual(http(srv, "/daily")[0], 200)
            self.assertEqual(http(srv, "/js/daily.js")[0], 200)
            self.assertIn('id="daily-btn"', http(srv, "/")[1])
        with IsolatedServer(settings={"daily_chart": False}) as srv:
            tok = json.loads(http(srv, "/api/join", "POST", {"name": "webarch"})[1])["token"]
            self.assertEqual(http(srv, "/api/daily", headers={"X-Token": tok})[0], 404)

    def test_the_endpoints(self):
        with IsolatedServer(settings={"daily_chart": True}) as srv:
            status, text, _ = http(srv, "/api/join", "POST", {"name": "webdash"})
            tok = json.loads(text)["token"]
            h = {"X-Token": tok}
            status, text, _ = http(srv, "/api/daily", headers=h)
            self.assertEqual(status, 200, text)
            self.assertEqual(json.loads(text)["status"], "new")
            status, text, _ = http(srv, "/api/daily/start", "POST", {}, headers=h)
            st = json.loads(text)
            self.assertEqual(len(st["candles"]), daily.HISTORY)
            status, text, _ = http(srv, "/api/daily/trade", "POST", {"side": "buy", "pct": 0.25}, headers=h)
            self.assertAlmostEqual(json.loads(text)["cash"], 750, places=6)
            status, text, _ = http(srv, f"/api/daily/state?since={daily.HISTORY}", headers=h)
            self.assertEqual(status, 200)
            self.assertLessEqual(len(json.loads(text)["candles"]), 5)
            self.assertEqual(http(srv, "/api/daily")[0], 401)


if __name__ == "__main__":
    unittest.main()
