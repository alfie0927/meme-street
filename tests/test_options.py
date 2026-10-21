"""Options (options.py, open to everyone): Black-Scholes prices with the stock's own volatility and a premium, a spread
between bid and ask, the chain on offer, buying and selling back, cash settlement at expiry and on a bankruptcy, equity,
the books balancing, the ledger replay after a crash, and no free money from buying at random."""
import math
import os
import random
import tempfile
import unittest

from _helpers import advance, drift, engine, join, make_engine, quiet
import options


def new_engine(tmp, seed=1):
    random.seed(seed)
    e = engine.Engine(state_file=os.path.join(tmp, "state.json"), ledger_path=os.path.join(tmp, "ledger.db"))
    e.tick(now=e.now)
    quiet(e)
    return e


class PricingTests(unittest.TestCase):
    def test_black_scholes_basics(self):
        c, dc = options.bs(100, 100, 0.25, 0.3, "call")
        p, dp = options.bs(100, 100, 0.25, 0.3, "put")
        self.assertAlmostEqual(c - p, 100 - 100 * math.exp(-0.015 * 0.25), places=6)       # put-call parity
        self.assertTrue(0.5 < dc < 0.6 and -0.5 < dp < -0.4)
        self.assertGreater(options.bs(100, 100, 0.25, 0.6, "call")[0], c)                  # more volatility, dearer
        self.assertGreater(options.bs(100, 100, 0.25, 0.3, "call", extra_var=0.01)[0], c)  # an earnings jump, dearer
        self.assertEqual(options.bs(100, 90, 0.0, 0.3, "call")[0], 10)                       # at expiry: the payoff
        q = options.quote(100, 100, 0.01, 0.3, "call")
        self.assertLess(q["bid"], q["mid"])
        self.assertGreater(q["ask"], q["mid"])

    def test_strikes_are_round_and_around_the_price(self):
        ks = options.strikes_for(145.3)
        self.assertEqual(len(ks), 13)
        self.assertTrue(min(ks) < 145.3 < max(ks))
        step = ks[1] - ks[0]
        self.assertTrue(all(abs((b - a) - step) < 1e-9 for a, b in zip(ks, ks[1:])))
        self.assertIn(round(step, 6), (2.0, 2.5, 5.0))

    def test_buying_at_random_loses_on_average(self):
        """No free money: a stock that moves exactly at its stated volatility, options bought at the ask at its implied
        volatility (the stated one plus the premium) and held to expiry lose on average, calls, puts and straddles alike."""
        rng = random.Random(3)
        sigma, T, S0 = 0.4, 2 / 365, 100.0
        iv = sigma * 1.10
        results = {"call": [], "put": []}
        for _ in range(20000):
            ST = S0 * math.exp((0.015 - sigma ** 2 / 2) * T + sigma * math.sqrt(T) * rng.gauss(0, 1))
            for kind in ("call", "put"):
                ask = options.quote(S0, 100, T, iv, kind)["ask"] * 1.001
                results[kind].append(options.payoff(kind, 100, ST) / ask - 1)
        for kind, r in results.items():
            self.assertLess(sum(r) / len(r), -0.03, kind)


class TradingTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(31)
        quiet(self.e)
        self.p = join(self.e, "opty")

    def contract(self, kind="call"):
        e = self.e
        ch = e.option_chain("NVXA")
        exp = ch["expiries"][1]
        s = e.stocks["NVXA"]
        K = min(options.strikes_for(s.price), key=lambda k: abs(k - s.price))
        return kind, K, exp

    def test_the_chain(self):
        ch = self.e.option_chain("NVXA")
        self.assertEqual(len(ch["expiries"]), 4)
        self.assertEqual(len(ch["rows"]), 4 * 13)
        for r in ch["rows"]:
            self.assertGreaterEqual(r["call"]["ask"], r["call"]["bid"])
        self.assertIn("error", self.e.option_chain("MSI"))                  # not on the index or the funds

    def test_buy_sell_and_the_books_balance(self):
        e, p = self.e, self.p
        cash = p.cash
        kind, K, exp = self.contract()
        ok, msg = e.buy_option(p, "NVXA", kind, K, exp, amount=100)
        self.assertTrue(ok, msg)
        self.assertAlmostEqual(p.cash, cash - 100, places=6)
        self.assertEqual(len(p.opts), 1)
        self.assertLess(abs(drift(e)), 1e-6)
        eq = e.equity(p)
        self.assertLess(eq, cash)                                             # (bought at the ask, valued at the bid)
        self.assertGreater(eq, cash - 100)
        advance(e, 2)
        ok, msg = e.sell_option(p, p.opts[0]["id"], 0.5)
        self.assertTrue(ok, msg)
        self.assertEqual(len(p.opts), 1)
        advance(e, 2)
        ok, msg = e.sell_option(p, p.opts[0]["id"], 1.0)
        self.assertTrue(ok, msg)
        self.assertEqual(p.opts, [])
        self.assertLess(abs(drift(e)), 1e-6)
        self.assertLess(p.cash, cash)                                         # the spread and the fees

    def test_rules(self):
        e, p = self.e, self.p
        kind, K, exp = self.contract()
        self.assertFalse(e.buy_option(p, "NVXA", kind, K + 0.37, exp, amount=50)[0])      # a strike not on offer
        self.assertFalse(e.buy_option(p, "NVXA", kind, K, exp + 77, amount=50)[0])         # an expiry not on offer
        self.assertFalse(e.buy_option(p, "NVXA", kind, K, exp, amount=10 ** 6)[0])          # not enough cash
        self.assertFalse(e.buy_option(p, "NVXA", "straddle", K, exp, amount=50)[0])
        self.assertFalse(e.buy_option(e.guest, "NVXA", kind, K, exp, amount=50)[0])
        self.assertFalse(e.is_pro(p))
        self.assertTrue(e.buy_option(p, "NVXA", "put", K, exp, amount=50)[0])                # free accounts trade options

    def test_settlement_at_expiry_pays_the_payoff(self):
        e, p = self.e, self.p
        ch = e.option_chain("NVXA")
        exp = ch["expiries"][0]
        s = e.stocks["NVXA"]
        K = min(options.strikes_for(s.price))                                # deep in the money
        e.buy_option(p, "NVXA", "call", K, exp, amount=200)
        qty = p.opts[0]["qty"]
        e.now = exp + 0.5
        cash = p.cash
        e._settle_options()
        self.assertEqual(p.opts, [])
        self.assertAlmostEqual(p.cash - cash, qty * max(0.0, s.price - K), places=6)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_bankruptcy_settles_the_options_on_it(self):
        e, p = self.e, self.p
        kind, K, exp = self.contract("put")
        e.buy_option(p, "NVXA", kind, K, exp, amount=100)
        e._settle_options("NVXA", 0.01)
        self.assertEqual(p.opts, [])
        self.assertLess(abs(drift(e)), 1e-6)

    def test_options_survive_a_save(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            a = new_engine(tmp, 41)
            p = join(a, "keeper")
            ch = a.option_chain("NVXA")
            K = min(options.strikes_for(a.stocks["NVXA"].price), key=lambda k: abs(k - a.stocks["NVXA"].price))
            self.assertTrue(a.buy_option(p, "NVXA", "call", K, ch["expiries"][2], amount=80)[0])
            a.save()
            b = engine.Engine(state_file=a.state_file, ledger_path=a.ledger.path)
            self.assertEqual(b.by_token[p.token].opts, p.opts)
            a.ledger.close()
            b.ledger.close()

    def test_a_crash_loses_no_option_trade(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            a = new_engine(tmp, 42)
            p = join(a, "crashy")
            a.save()                                                   # the snapshot is from before the trades
            ch = a.option_chain("NVXA")
            K = min(options.strikes_for(a.stocks["NVXA"].price), key=lambda k: abs(k - a.stocks["NVXA"].price))
            self.assertTrue(a.buy_option(p, "NVXA", "call", K, ch["expiries"][2], amount=90)[0])
            advance(a, 2)                                              # (one option trade a second in a stock)
            self.assertTrue(a.buy_option(p, "NVXA", "put", K, ch["expiries"][2], amount=60)[0])
            advance(a, 2)
            a.sell_option(p, next(o for o in p.opts if o["kind"] == "put")["id"], 0.5)
            a.ledger.flush()
            b = engine.Engine(state_file=a.state_file, ledger_path=a.ledger.path)
            q = b.by_token[p.token]
            self.assertAlmostEqual(q.cash, p.cash, places=6)
            self.assertEqual(sorted((o["kind"], round(o["qty"], 6)) for o in q.opts),
                             sorted((o["kind"], round(o["qty"], 6)) for o in p.opts))
            self.assertLess(abs(drift(b)), 1e-6)
            a.ledger.close()
            b.ledger.close()


if __name__ == "__main__":
    unittest.main()
