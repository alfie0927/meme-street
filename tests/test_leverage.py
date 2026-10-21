"""Leverage (Pro): up to 10x on any listing but the leveraged products, long and short. The house lends the rest of a
long (with interest), a short needs a lev-th of the collateral; each leveraged position closes on its own when its
equity falls to half the margin it started with; a gap past that is paid from cash and then by the house. The books
balance, and a save and a crash bring every loan and collateral back."""
import os
import random
import tempfile
import unittest

from _helpers import advance, drift, engine, join, make_engine, quiet

FEE = engine.FEE


def pro(e, p, days=30):
    e.admin_pro(p, days)
    return p


class LeverageTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(51)
        quiet(self.e)
        self.p = join(self.e, "levvy")

    def test_only_pro_and_never_on_the_leveraged_products(self):
        e, p = self.e, self.p
        ok, msg = e.trade(p, "NVXA", "buy", 0.2, lev=5)
        self.assertFalse(ok)
        self.assertIn("Pro", msg)
        pro(e, p)
        lev_product = next(tk for tk, s in e.stocks.items() if s.spec and s.spec.get("kind") == "leveraged")
        self.assertFalse(e.trade(p, lev_product, "buy", 0.2, lev=2)[0])
        self.assertFalse(e.trade(p, "NVXA", "buy", 0.2, lev=11)[0])
        self.assertTrue(e.trade(p, "NVXA", "buy", 0.2, lev=10)[0])

    def test_a_leveraged_long(self):
        e, p = self.e, pro(self.e, self.p)
        s = e.stocks["NVXA"]
        cash = p.cash
        ok, msg = e.trade(p, "NVXA", "buy", 0.1, lev=5)
        self.assertTrue(ok, msg)
        margin = cash * 0.1
        self.assertAlmostEqual(p.cash, cash - margin, places=6)
        self.assertAlmostEqual(p.loan["NVXA"], margin * 4, places=6)
        self.assertAlmostEqual(p.hold["NVXA"], margin * 5 * (1 - FEE) / s.price, places=6)
        self.assertAlmostEqual(e.equity(p), cash - margin * 5 * FEE * 2 + 0, delta=margin * 5 * FEE * 2 + 1e-6)
        self.assertLess(abs(drift(e)), 1e-6)
        eq0 = e.equity(p)
        s.fair *= 1.02                                                    # +2% on the stock is about +10% on the margin
        self.assertAlmostEqual(e.equity(p) - eq0, p.hold["NVXA"] * s.price * (1 - FEE) - p.hold["NVXA"] * s.price / 1.02 * (1 - FEE), places=4)
        advance(e, 2)
        ok, msg = e.trade(p, "NVXA", "sell", 1.0)
        self.assertTrue(ok, msg)
        self.assertNotIn("NVXA", p.loan)
        self.assertNotIn("NVXA", p.lev)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_interest_adds_to_the_loan(self):
        e, p = self.e, pro(self.e, self.p)
        e.trade(p, "NVXA", "buy", 0.1, lev=2)                            # (2x: a game day's noise cannot close it)
        loan = p.loan["NVXA"]
        advance(e, 1800)                                                  # a game day
        self.assertAlmostEqual(p.loan["NVXA"] / loan, 1.0003, delta=0.00005)
        self.assertGreater(p.loan_int["NVXA"], 0)

    def test_a_leveraged_long_is_closed_when_its_margin_runs_out(self):
        e, p = self.e, pro(self.e, self.p)
        s = e.stocks["NVXA"]
        e.trade(p, "NVXA", "buy", 0.1, lev=10)
        liq = e.liquidation_price(p, "NVXA")
        self.assertTrue(0.9 * s.price < liq < s.price)
        s.fair = liq * 1.001
        e._margin_calls()
        self.assertIn("NVXA", p.hold)
        s.fair = liq * 0.999
        e._margin_calls()
        self.assertNotIn("NVXA", p.hold)
        self.assertNotIn("NVXA", p.loan)
        self.assertEqual(p.margin_calls, 1)
        self.assertTrue(any("ran out of margin" in n for n in p.notices))
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_gap_past_the_margin_is_paid_from_cash_then_by_the_house(self):
        e, p = self.e, pro(self.e, self.p)
        s = e.stocks["NVXA"]
        e.trade(p, "NVXA", "buy", 1.0, lev=10)                           # all of the cash: nothing left to pay a gap
        s.fair *= 0.7                                                     # a 30% gap at 10x: three times the margin gone
        e._margin_calls()
        self.assertNotIn("NVXA", p.hold)
        self.assertGreaterEqual(p.cash, 0.0)
        self.assertGreater(e.lev_shortfall, 0)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_leveraged_short(self):
        e, p = self.e, pro(self.e, self.p)
        s = e.stocks["NVXA"]
        cash = p.cash
        ok, msg = e.trade(p, "NVXA", "sell", 0.1, lev=4)
        self.assertTrue(ok, msg)
        gross = cash * 0.1 / (1 / 4 + FEE)
        self.assertAlmostEqual(p.collat["NVXA"], gross / 4, places=6)
        self.assertAlmostEqual(-p.hold["NVXA"] * s.price, gross, places=4)
        eq0 = e.equity(p)
        s.fair *= 0.98
        self.assertGreater(e.equity(p), eq0 + 0.015 * gross)
        advance(e, 2)
        ok, msg = e.trade(p, "NVXA", "buy", 0.5)                         # cover half: half the collateral comes back
        self.assertTrue(ok, msg)
        self.assertAlmostEqual(p.collat["NVXA"], gross / 8, places=4)
        s.fair = e.liquidation_price(p, "NVXA") * 1.001
        e._margin_calls()
        self.assertNotIn("NVXA", p.hold)
        self.assertNotIn("NVXA", p.collat)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_adding_keeps_the_leverage_and_exits_need_none(self):
        e, p = self.e, pro(self.e, self.p)
        e.trade(p, "NVXA", "buy", 0.1, lev=3)
        advance(e, 2)
        ok, msg = e.trade(p, "NVXA", "buy", 0.1, lev=5)
        self.assertFalse(ok)
        self.assertIn("3x", msg)
        self.assertTrue(e.trade(p, "NVXA", "buy", 0.1)[0])                # (no leverage given: the position's own)
        self.assertEqual(p.lev["NVXA"], 3)
        advance(e, 2)
        e.admin_pro(p, remove=True)                                       # Pro ends: closing still works
        self.assertTrue(e.trade(p, "NVXA", "sell", 1.0)[0])
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_save_and_a_crash_keep_every_loan_and_collateral(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            random.seed(61)
            a = engine.Engine(state_file=os.path.join(tmp, "state.json"), ledger_path=os.path.join(tmp, "ledger.db"))
            a.tick(now=a.now)
            quiet(a)
            p = pro(a, join(a, "crashlev"))
            a.trade(p, "NVXA", "buy", 0.2, lev=5)
            a.save()                                                       # snapshot with one leveraged long
            a.trade(p, "CLDR", "sell", 0.2, lev=4)                         # after it: a leveraged short...
            advance(a, 2)
            a.trade(p, "NVXA", "sell", 0.5)                                # ...and half the long sold
            a._flush_borrow()                                              # (the short's borrow fees are written every 10 s)
            a.ledger.flush()
            b = engine.Engine(state_file=a.state_file, ledger_path=a.ledger.path)
            q = b.by_token[p.token]
            self.assertAlmostEqual(q.cash, p.cash, places=6)
            self.assertAlmostEqual(q.loan["NVXA"], p.loan["NVXA"], delta=0.01)   # (interest since the snapshot: seconds)
            self.assertAlmostEqual(q.collat["CLDR"], p.collat["CLDR"], places=6)
            self.assertEqual(q.lev, p.lev)
            self.assertLess(abs(drift(b)), 1e-6)
            b.save()
            c = engine.Engine(state_file=b.state_file)
            self.assertEqual(c.by_token[p.token].lev, p.lev)
            a.ledger.close()
            b.ledger.close()


if __name__ == "__main__":
    unittest.main()
