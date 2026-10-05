"""Shorting: the amount you short is taken out of your cash as collateral (it does not add to your cash), there is no
limit beyond your cash, and covering gives the collateral back plus the gain or minus the loss."""
import json
import os
import random
import tempfile
import unittest

from _helpers import advance, drift, engine, join, make_engine

FEE = engine.FEE


class ShortCashTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(5)
        self.p = join(self.e, "shorty", extra_cash=9000)          # 10,000 MB

    def test_a_short_takes_the_amount_out_of_cash_instead_of_adding_to_it(self):
        e, p = self.e, self.p
        ok, msg = e.trade(p, "NVXA", "sell", 0.4)
        self.assertTrue(ok, msg)
        self.assertAlmostEqual(p.cash, 6000, places=6)
        self.assertLess(p.hold["NVXA"], 0)
        self.assertAlmostEqual(e.equity(p), 10000 - 4000 * FEE / (1 + FEE) * 2 + 0 - 0, delta=10)   # only the fees are lost
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_round_trip_at_the_same_price_costs_only_the_fees(self):
        e, p = self.e, self.p
        e.trade(p, "NVXA", "sell", 1.0)
        e.now += 2
        e.trade(p, "NVXA", "buy", 1.0)
        self.assertNotIn("NVXA", p.hold)
        self.assertAlmostEqual(p.cash, 10000 * (1 - FEE / (1 + FEE)) * (1 - FEE) , delta=2)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_fall_gives_the_collateral_back_plus_the_gain(self):
        e, p = self.e, self.p
        e.trade(p, "NVXA", "sell", 0.5)
        e.stocks["NVXA"].fair *= 0.8
        e.now += 2
        e.trade(p, "NVXA", "buy", 1.0)
        self.assertGreater(p.cash, 10000 + 900)                    # about +20% of the 5,000 shorted, less fees
        self.assertLess(p.cash, 10000 + 1000)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_rise_costs_the_loss_out_of_the_collateral(self):
        e, p = self.e, self.p
        e.trade(p, "NVXA", "sell", 0.5)
        e.stocks["NVXA"].fair *= 1.2
        e.now += 2
        self.assertTrue(e.trade(p, "NVXA", "buy", 1.0)[0])
        self.assertLess(p.cash, 10000 - 900)
        self.assertGreater(p.cash, 10000 - 1100)

    def test_there_is_no_borrow_limit_only_your_cash(self):
        e = self.e
        rich = [join(e, f"big{i}", extra_cash=5_000_000) for i in range(3)]
        for r in rich:
            e.now += 2
            ok, msg = e.trade(r, "MOON", "sell", 1.0)
            self.assertTrue(ok, msg)
            self.assertNotIn("borrow", msg.lower().replace("collateral", ""))
        self.assertGreater(e.short_interest_map()["MOON"], 10_000_000)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_with_no_free_cash_a_short_is_refused_and_says_so(self):
        e, p = self.e, self.p
        e.trade(p, "NVXA", "sell", 1.0)
        e.now += 2
        ok, msg = e.trade(p, "CLDR", "sell", 1.0)
        self.assertFalse(ok)
        self.assertIn("cash", msg)

    def test_a_partial_cover_returns_its_share_and_keeps_the_average_price(self):
        e, p = self.e, self.p
        e.trade(p, "NVXA", "sell", 0.5)
        avg = e.avg_price(p, "NVXA")
        e.now += 2
        cash0 = p.cash
        e.trade(p, "NVXA", "buy", 0.5)
        self.assertAlmostEqual(p.cash - cash0, 2500 * (1 - 2 * FEE), delta=2)
        self.assertAlmostEqual(e.avg_price(p, "NVXA"), avg, places=6)

    def test_a_loss_bigger_than_the_collateral_is_a_margin_call_the_house_absorbs(self):
        e, p = self.e, self.p
        e.trade(p, "NVXA", "sell", 1.0)
        e.stocks["NVXA"].fair *= 4.0
        before = e.short_shortfall
        e._margin_calls()
        self.assertNotIn("NVXA", p.hold)
        self.assertGreaterEqual(p.cash, 0.0)
        self.assertGreater(e.short_shortfall, before)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_money_is_conserved_through_lots_of_shorting_and_covering(self):
        e = self.e
        players = [join(e, f"s{i}", extra_cash=4000) for i in range(4)]
        rng = random.Random(3)
        for k in range(400):
            e.tick(now=e.now + 1)
            if k % 3 == 0:
                e.trade(players[k % 4], rng.choice(["NVXA", "CLDR", "OILX", "MOON"]), rng.choice(["buy", "sell", "sell"]), rng.choice([0.2, 0.5, 1.0]))
            if k == 200:
                e.stocks["OILX"].fair *= 2.5
        self.assertLess(abs(drift(e)), 1e-6)
        for p in e.players.values():
            self.assertGreaterEqual(p.cash, -1e-9)


class OldSaveTests(unittest.TestCase):
    def test_a_save_from_the_old_model_keeps_every_equity_and_the_books_balance(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(9)
            e = engine.Engine(state_file=path)
            p = join(e, "oldshort", extra_cash=9000)
            e.trade(p, "NVXA", "sell", 0.4)
            e.stocks["NVXA"].fair *= 0.9
            equity = e.equity(p)
            e.save()
            d = json.load(open(path, encoding="utf-8"))
            d.pop("short_model")                                    # as an old save is: proceeds were added to cash
            x = next(q for q in d["players"] if q["name"] == "oldshort")
            c = x["cost"]["NVXA"]
            x["cash"] += 2 * c
            d["house"] -= 2 * c
            json.dump(d, open(path, "w", encoding="utf-8"))
            f = engine.Engine(state_file=path)
            p2 = next(q for q in f.players.values() if q.name == "oldshort")
            self.assertAlmostEqual(f.equity(p2), equity, places=4)
            self.assertAlmostEqual(p2.cash, p.cash, places=4)
            self.assertLess(abs(f.total_tokens() - f.minted), 1e-6)


if __name__ == "__main__":
    unittest.main()
