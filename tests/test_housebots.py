"""House bots (housebots.py): off unless switched on; 32 accounts with personas; out of the admin's player lists but
in the money totals; they trade the market by the same rules as anyone, keep every MB accounted for, and play the
Daily Chart without ever using a candle they have not been shown."""
import random
import unittest

from _helpers import drift, join, make_engine
import daily  # noqa: E402
import housebots  # noqa: E402


def fake_history(e, n=200):
    """Enough 5-minute candles on every company for the bots to read (a fresh test game has hardly any)."""
    for s in e.stocks.values():
        if s.asset_type != "equity":
            continue
        rng, px, rows = random.Random(s.ticker), s.price, []
        for k in range(n):
            o = px
            px *= 1 + rng.gauss(0, 0.004)
            rows.append([e.now - (n - k) * 300.0, o, max(o, px) * 1.001, min(o, px) * 0.999, px, 1000.0])
        s.tf["5m"].clear()
        s.tf["5m"].extend(rows + [[e.now, px, px, px, px, 0.0]])


class HouseBotTests(unittest.TestCase):
    def test_off_unless_switched_on(self):
        e = make_engine(41)
        e.tick(now=e.now + 1)
        self.assertEqual(e.house_bots(), [])

    def test_the_bots_join_and_stay_out_of_the_player_lists(self):
        e = make_engine(42, house_bots=True)
        person = join(e, "realperson")
        e.tick(now=e.now + 1)
        bots = e.house_bots()
        self.assertEqual(sorted(b.name for b in bots), sorted(housebots.NAMES))
        self.assertEqual({b.hb["style"] for b in bots}, set(housebots.STYLES))
        self.assertEqual([r["name"] for r in e.admin_players()], ["realperson"])
        o = e.admin_overview()
        self.assertEqual((o["bots"]["total"], o["stats"]["humans"], o["stats"]["bots"]), (32, 1, 32))
        self.assertEqual(o["funnel"]["players"], 1)
        self.assertGreaterEqual(o["stats"]["total_mb"], 33 * 1000 - 1)              # their MB count in the totals
        e.tick(now=e.now + 1)
        self.assertEqual(len(e.house_bots()), 32)                                   # made once
        self.assertIsNotNone(person)

    def test_they_trade_by_the_rules_and_every_mb_is_kept(self):
        e = make_engine(43, house_bots=True)
        e.tick(now=e.now + 1)
        fake_history(e)
        for b in e.house_bots():
            b.hb["state"], b.hb["until"], b.hb["hours"] = "active", e.now + 86400, [0, 24]
        for _ in range(40):
            e.now += 600
            for b in e.house_bots():
                e._house_market(b)
        self.assertGreater(sum(b.trades for b in e.house_bots()), 20)
        self.assertTrue(any(b.orders for b in e.house_bots()))                     # the careful ones set stops
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_daily_plan_never_uses_a_candle_not_yet_shown(self):
        e = make_engine(44)
        cs = daily.make_chart(7919 * 3)["candles"]
        for k, name in enumerate(housebots.NAMES):
            hb = housebots.persona(name, k)
            plan = e._house_daily_plan(hb, cs, "s")
            for at, side, pct in plan:
                self.assertIn(side, ("buy", "sell"))
                self.assertIn(pct, daily.CHIPS)
                self.assertTrue(daily.HISTORY - 1 <= at < daily.HISTORY + daily.LIVE)
            cut = daily.HISTORY + 50                           # change every candle after the cut: nothing before it moves
            other = [list(c) for c in cs[:cut]] + [[c[0] * 1.1, c[1] * 1.1, c[2] * 1.1, c[3] * 1.1, c[4]] for c in cs[cut:]]
            same = [x for x in plan if x[0] < cut - 3]
            self.assertEqual(same, [x for x in e._house_daily_plan(hb, other, "s") if x[0] < cut - 3], name)

    def test_a_bot_plays_the_daily_chart_to_the_end(self):
        e = make_engine(45, house_bots=True)
        e.tick(now=e.now + 1)
        b = next(x for x in e.house_bots() if x.hb["style"] == "trend")
        e._house_daily_start(b)
        for _ in range(daily.LIVE + 3):
            e.now += 1
            e._house_tick()
        board = e._daily_board(e._dchart())
        self.assertIn(b.name, [r["name"] for r in board])
        self.assertEqual(b.hb["dplan"], [])


if __name__ == "__main__":
    unittest.main()
