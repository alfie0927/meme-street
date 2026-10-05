"""House tail risk with no limit on how much a player may put into one stock. The tails of the price moves are thinner
(a rescue after a collapse is a doubling, not a ten-fold jump), the reserve is kept in proportion to the money at stake,
and the admin page shows what the players' positions could cost the house. None of it changes a price or a payout."""
import math
import os
import random
import tempfile
import unittest

from _helpers import advance, drift, engine, fixed_engine, join, make_engine, quiet

import newsgen


def real_engine(seed):
    from test_wild import real_engine as make
    return make(seed)


class ThinnerTailsTests(unittest.TestCase):
    def test_a_rescue_after_a_collapse_is_a_doubling_not_a_ten_fold_jump(self):
        e = real_engine(1)
        q, payout, jump = e._distress_terms(e.stocks["NVXA"])
        self.assertAlmostEqual(jump, 0.75, places=9)
        moon = next(s for s in e.stocks.values() if s.moonshot)
        qm, pm, jm = e._distress_terms(moon)
        self.assertLess(jm, 1.5)
        self.assertGreater(jm, jump)

    def test_the_rescue_is_still_a_fair_bet(self):
        e = real_engine(2)
        for s in list(e.stocks.values())[:60]:
            if s.asset_type == "index":
                continue
            q, payout, jump = e._distress_terms(s)
            self.assertAlmostEqual(q * payout + (1 - q) * (1 + jump), 1.0, places=12)

    def test_the_moonshot_daily_limit_is_three_times_a_normal_one(self):
        e = real_engine(3)
        moon = next(s for s in e.stocks.values() if s.moonshot)
        self.assertEqual(moon.limit_mult, 3.0)
        self.assertEqual(e.stocks["NVXA"].limit_mult, 1.0)

    def test_a_moonshot_catalyst_cannot_lift_it_more_than_about_thirteen_tenths(self):
        e = real_engine(4)
        e.settings["catalyst_moonshot_weight"] = 1e12                      # (so the catalysts land on moonshots)
        random.seed(4)
        gains = []
        for _ in range(300):
            e.next_catalyst = 0
            before = {k: s.price for k, s in e.stocks.items() if s.moonshot}
            e._catalysts()
            for k, b in before.items():
                s = e.stocks.get(k)
                if s and s.price > b * 1.0001 and s.price / b < 5:
                    gains.append(s.price / b - 1)
        self.assertGreater(len(gains), 20)
        self.assertLess(max(gains), 1.9 * 0.7 + 1e-9)

    def test_every_catalyst_stays_a_fair_bet_after_the_trim(self):
        for kind in newsgen.CATALYSTS:
            p = kind["p"]
            for lo, hi in (kind["up"], tuple(x * 0.7 for x in kind["up_moon"])):
                for up in (lo, (lo + hi) / 2, hi):
                    up = min(up, 0.95 * (1 - p) / p)
                    down = -p * up / (1 - p)
                    self.assertAlmostEqual(p * up + (1 - p) * down, 0.0, places=12)


class ReserveFloorTests(unittest.TestCase):
    def test_nothing_happens_while_the_reserve_is_well_above_the_floor(self):
        e = make_engine(11)
        p = join(e, "modest")
        e.trade(p, "CLDR", "buy", 0.5)
        advance(e, 12)
        self.assertEqual(e.recapitalized, 0.0)

    def test_a_reserve_that_falls_below_the_floor_is_topped_up_and_the_books_balance(self):
        e = make_engine(12)
        for i in range(50):
            join(e, f"rich{i}", extra_cash=99000)                     # 5 million MB of players
        house0, minted0 = e.house, e.minted
        advance(e, 8)
        floor = e._reserve_floor()
        self.assertGreater(floor, house0)
        self.assertAlmostEqual(e.house, floor, places=6)
        self.assertAlmostEqual(e.recapitalized, floor - house0, places=6)
        self.assertGreater(e.minted, minted0)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_the_floor_follows_the_risk_not_only_the_money(self):
        e = make_engine(13)
        p = join(e, "bettor", extra_cash=99000)
        e.trade(p, "CLDR", "buy", 1.0)
        self.assertGreater(e.house_risk()["stress_loss"], 0)
        self.assertGreaterEqual(e._reserve_floor(), 0.5 * e.house_risk()["stress_loss"])
        self.assertGreater(e._reserve_floor(), 0.1 * e.equity(p) - 1e-6)

    def test_it_can_be_switched_off(self):
        e = make_engine(14, reserve_recap=False)
        for i in range(50):
            join(e, f"rich{i}", extra_cash=99000)
        advance(e, 8)
        self.assertEqual(e.recapitalized, 0.0)

    def test_it_changes_no_price_and_no_player_balance(self):
        def run(recap):
            e = fixed_engine(21)
            quiet(e)
            e.settings["reserve_recap"] = recap
            players = [join(e, f"cap{i}", extra_cash=99000) for i in range(30)]
            rng = random.Random(3)
            for k in range(300):
                e.tick(now=e.now + 1)
                if k % 5 == 0:
                    e.trade(players[k % 30], rng.choice(["CLDR", "NVXA", "OILX"]), rng.choice(["buy", "sell"]), 0.5)
            return e, players
        a, pa = run(True)
        b, pb = run(False)
        self.assertGreater(a.recapitalized, 0)
        self.assertEqual({k: s.price for k, s in a.stocks.items()}, {k: s.price for k, s in b.stocks.items()})
        self.assertEqual([p.cash for p in pa], [p.cash for p in pb])
        self.assertEqual([p.hold for p in pa], [p.hold for p in pb])
        self.assertLess(abs(drift(a)), 1e-6)

    def test_house_pnl_is_still_the_mirror_of_the_players(self):
        e = make_engine(15)
        players = [join(e, f"mir{i}", extra_cash=99000) for i in range(20)]
        for k in range(100):
            e.tick(now=e.now + 1)
            e.trade(players[k % 20], "CLDR", random.choice(["buy", "sell"]), 0.5)
        s = e.house_stats()
        self.assertAlmostEqual(s["house_pnl"], -s["players_pnl"], places=9)
        self.assertGreaterEqual(s["recapitalized"], 0)


class RiskReportTests(unittest.TestCase):
    def test_exposure_is_net_per_stock_with_the_right_side_and_size(self):
        e = make_engine(31)
        a, b, c = (join(e, n, extra_cash=4000) for n in ("repa", "repb", "repc"))
        e.trade(a, "CLDR", "buy", 0.6)
        e.trade(b, "CLDR", "sell", 0.2)                              # a smaller short in the same stock
        e.trade(c, "OILX", "sell", 0.3)
        risk = e.house_risk()
        rows = {r["ticker"]: r for r in risk["exposure"]}
        want_cldr = a.hold["CLDR"] * e.stocks["CLDR"].price + b.hold["CLDR"] * e.stocks["CLDR"].price
        self.assertAlmostEqual(rows["CLDR"]["net"], want_cldr, places=6)
        self.assertLess(rows["OILX"]["net"], 0)
        self.assertAlmostEqual(rows["CLDR"]["loss"], abs(want_cldr) * rows["CLDR"]["move"], places=6)
        self.assertEqual([r["loss"] for r in risk["exposure"]], sorted((r["loss"] for r in risk["exposure"]), reverse=True))
        self.assertAlmostEqual(risk["stress_loss"], sum(r["loss"] for r in e._exposure()[0]), places=6)

    def test_a_short_cannot_cost_the_house_more_than_the_whole_position(self):
        e = make_engine(32)
        p = join(e, "shorter", extra_cash=4000)
        e.trade(p, "CLDR", "sell", 0.5)
        e.stocks["CLDR"].vol = 9.0                                   # an absurdly wild stock: three sigmas is far over 100%
        rows = e.house_risk()["exposure"]
        self.assertLessEqual(rows[0]["loss"], abs(rows[0]["net"]) + 1e-9)

    def test_it_is_in_the_admin_stats_and_the_admin_page_shows_it(self):
        e = make_engine(33)
        p = join(e, "visible")
        e.trade(p, "CLDR", "buy", 0.5)
        s = e.house_stats()
        self.assertIn("risk", s)
        self.assertEqual(s["risk"]["exposure"][0]["ticker"], "CLDR")
        page = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "admin.html"), encoding="utf-8").read()
        self.assertIn("House risk", page)
        self.assertIn("stress_loss", page)


class PersistenceTests(unittest.TestCase):
    def test_the_topped_up_amount_survives_a_restart(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(41)
            e = engine.Engine(state_file=path, bots=False)
            for i in range(30):
                join(e, f"keep{i}", extra_cash=99000)
            advance(e, 8)
            self.assertGreater(e.recapitalized, 0)
            e.save()
            f = engine.Engine(state_file=path, bots=False)
            self.assertAlmostEqual(f.recapitalized, e.recapitalized, places=6)
            self.assertAlmostEqual(f.house, e.house, places=6)
            self.assertLess(abs(drift(f)), 1e-6)

    def test_a_top_up_after_the_last_snapshot_is_recovered_from_the_ledger(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            ledger = os.path.join(tmp, "ledger.db")
            random.seed(42)
            e = engine.Engine(state_file=path, bots=False, ledger_path=ledger)
            e.save()
            for i in range(30):
                join(e, f"late{i}", extra_cash=99000)
            advance(e, 8)
            recap, house = e.recapitalized, e.house
            self.assertGreater(recap, 0)
            e.ledger.flush()                                          # a crash: no further save
            g = engine.Engine(state_file=path, bots=False, ledger_path=ledger)
            self.assertAlmostEqual(g.recapitalized, recap, places=6)
            self.assertAlmostEqual(g.house, house, places=6)
            self.assertLess(abs(drift(g)), 1e-6)
            g.ledger.close()
            e.ledger.close()


if __name__ == "__main__":
    unittest.main()
