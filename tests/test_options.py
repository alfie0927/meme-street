"""Options (options.py, open to everyone): the value and the Greeks (Black-Scholes-Merton on the forward, checked against
finite differences and put-call parity), the skew, the term structure that follows the volatility clustering, earnings
and the volatility crush, dividends, quotes that follow the stock, listed strikes that stay, the chain, buying and
selling back, cash settlement at expiry and on a bankruptcy, the books balancing, the ledger replay after a crash, and
no free money from buying at random."""
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


def atm(e, s, exp):
    return min(e.listed_strikes(s, exp), key=lambda k: abs(k - s.price))


class PricingTests(unittest.TestCase):
    def test_value_parity_and_the_greeks(self):
        S, K, T, sig, carry = 100.0, 105.0, 30 / 365, 0.35, 0.055
        for skew, div, ev in ((0.0, 0.0, 0.0), (0.15, 1.0, 0.0004)):
            c = options.contract(S, K, T, sig, "call", carry, ev, div, skew, 0.08)
            p = options.contract(S, K, T, sig, "put", carry, ev, div, skew, 0.08)
            F = (S - div) * math.exp(carry * T)
            self.assertAlmostEqual(c["mid"] - p["mid"], F - K, places=9)                  # put-call parity (undiscounted)
            self.assertAlmostEqual(c["iv"], p["iv"], places=12)                           # one volatility a strike
        for kind in ("call", "put"):
            def v(**kw):
                a = dict(S=S, K=K, T=T, sigma=sig, kind=kind, carry=carry)
                a.update(kw)
                return options.contract(**a)
            q, h = v(), 0.01
            self.assertAlmostEqual(q["delta"], (v(S=S + h)["mid"] - v(S=S - h)["mid"]) / (2 * h), places=5)
            self.assertAlmostEqual(q["gamma"], (v(S=S + h)["delta"] - v(S=S - h)["delta"]) / (2 * h), places=5)
            self.assertAlmostEqual(q["vega"], (v(sigma=sig + 1e-4)["mid"] - v(sigma=sig - 1e-4)["mid"]) / 2e-4 / 100, places=6)
            self.assertAlmostEqual(q["rho"], (v(carry=carry + 1e-4)["mid"] - v(carry=carry - 1e-4)["mid"]) / 2e-4 / 100, places=6)
            dt = 1e-4
            self.assertAlmostEqual(q["theta"], (v(T=T - dt)["mid"] - v(T=T + dt)["mid"]) / (2 * dt) / 365, places=6)
        self.assertGreater(options.contract(S, K, T, 0.6, "call")["mid"], options.contract(S, K, T, 0.3, "call")["mid"])
        self.assertGreater(options.contract(S, K, T, sig, "call", event_var=0.01)["mid"], options.contract(S, K, T, sig, "call")["mid"])
        self.assertEqual(options.contract(100, 90, 0.0, 0.3, "call")["mid"], 10)        # at expiry: the payoff
        q = options.quote(100, 100, 0.01, 0.3, "call")
        self.assertTrue(q["bid"] < q["mid"] < q["ask"])
        big = options.quote(400, 380, 30 / 365, 0.4, "call")                            # over 3 MB: on a 0.05 grid
        self.assertAlmostEqual(big["ask"] * 20, round(big["ask"] * 20), places=6)

    def test_the_greeks_behave_like_real_ones(self):
        c = lambda K, days, kind="call": options.contract(100, K, days / 365, 0.4, kind, 0.05)
        self.assertTrue(0.5 < c(100, 7)["delta"] < 0.6 and -0.5 < c(100, 7, "put")["delta"] < -0.4)   # at the money: about a half
        self.assertGreater(c(80, 0.5)["delta"], 0.99)                                   # deep in the money near expiry: like the stock
        self.assertLess(c(120, 0.5)["delta"], 0.01)                                     # far out near expiry: worthless
        self.assertGreater(c(100, 7)["gamma"], c(115, 7)["gamma"])                      # gamma peaks at the money...
        self.assertGreater(c(100, 1)["gamma"], c(100, 30)["gamma"])                     # ...and near expiry
        self.assertLess(c(100, 1)["theta"], c(100, 30)["theta"])                        # time decay speeds up near expiry
        self.assertLess(c(100, 30)["theta"], 0)
        self.assertGreater(c(100, 90)["vega"], c(100, 7)["vega"])                       # vega grows with time
        self.assertGreater(c(100, 30)["rho"], 0)
        self.assertLess(c(100, 30, "put")["rho"], 0)
        self.assertAlmostEqual(c(100, 7)["gamma"], c(100, 7, "put")["gamma"], places=12)
        self.assertTrue(0 < c(105, 7)["itm"] < 0.5 < c(95, 7)["itm"] < 1)

    def test_the_skew(self):
        iv = lambda K, skew: options.contract(100, K, 7 / 365, 0.3, "put", 0.0, 0.0, 0.0, skew, 0.08)["iv"]
        self.assertGreater(iv(95, 0.15), iv(100, 0.15))                                 # puts below the price cost more
        self.assertGreater(iv(95, 0.15), iv(105, 0.15))                                 # ...than calls as far above
        self.assertAlmostEqual(iv(95, 0.0) / iv(100, 0.0), iv(105.26, 0.0) / iv(100, 0.0), delta=0.01)   # no skew: a smile
        self.assertGreater(iv(80, 0.15), iv(95, 0.15))
        self.assertGreaterEqual(min(iv(k, 0.15) for k in range(60, 160, 5)), 0.75 * iv(100, 0.15))

    def test_buying_at_random_loses_on_average(self):
        """No free money: a stock that moves at its stated volatility and grows at its expected rate, contracts bought at
        the ask (strikes from 10% below to 10% above, with the skew) and held to expiry lose on average, calls and puts."""
        rng = random.Random(3)
        sigma, T, S0, carry = 0.4, 2 / 365, 100.0, 0.055
        iv = sigma * 1.10
        results = {"call": [], "put": []}
        for _ in range(20000):
            ST = S0 * math.exp((carry - sigma ** 2 / 2) * T + sigma * math.sqrt(T) * rng.gauss(0, 1))
            K = rng.choice((90, 95, 100, 105, 110))
            for kind in ("call", "put"):
                ask = options.quote(S0, K, T, iv, kind, carry, 0.0, 0.0, 0.15, 0.08)["ask"] * 1.001
                results[kind].append((options.payoff(kind, K, ST), ask))
        for kind, r in results.items():
            self.assertLess(sum(pay for pay, _ in r) / sum(ask for _, ask in r) - 1, -0.03, kind)


class MarketTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(31)
        quiet(self.e)
        self.s = self.e.stocks["NVXA"]

    def test_quotes_follow_the_stock(self):
        e, s = self.e, self.s
        exp = e.option_expiries()[2]
        K = atm(e, s, exp)
        q0 = {k: e.option_quote(s, k, K, exp) for k in ("call", "put")}
        S0 = s.price
        s.fair *= 1.01
        dS = s.price - S0
        for kind in ("call", "put"):                       # delta and gamma for the move, vega for the strike's new place on the smile
            q, q1 = q0[kind], e.option_quote(s, kind, K, exp)
            want = q["mid"] + q["delta"] * dS + 0.5 * q["gamma"] * dS * dS + q["vega"] * (q1["iv"] - q["iv"]) * 100
            self.assertAlmostEqual(q1["mid"], want, delta=0.005 * q["mid"] + 1e-6)
            self.assertNotEqual(q1["ask"], q0[kind]["ask"])
        self.assertGreater(e.option_quote(s, "call", K, exp)["mid"], q0["call"]["mid"])     # up: calls dearer, puts cheaper
        self.assertLess(e.option_quote(s, "put", K, exp)["mid"], q0["put"]["mid"])

    def test_strikes_stay_listed_and_new_ones_are_added(self):
        e, s = self.e, self.s
        exp = e.option_expiries()[1]
        first = e.listed_strikes(s, exp)
        self.assertEqual(len(first), 13)
        s.fair *= 1.2
        later = e.listed_strikes(s, exp)
        self.assertTrue(set(first) <= set(later))                                         # nothing is taken away
        self.assertGreaterEqual(sum(1 for k in later if k > s.price), 6)                  # always six above...
        self.assertGreaterEqual(sum(1 for k in later if k < s.price), 6)                  # ...and six below
        rows = e.option_chain("NVXA", exp)["rows"]
        self.assertEqual(len(rows), 13)
        self.assertTrue(min(r["K"] for r in rows) < s.price < max(r["K"] for r in rows))

    def test_the_term_structure_follows_the_volatility_clustering(self):
        e, s = self.e, self.s
        e.mkt_volm = 1.0
        short, long = 0.5 / 365, 90 / 365
        s.volm = 2.5                                                                      # a storm: short expiries dearest
        self.assertGreater(e.option_vol(s, short), e.option_vol(s, long) * 1.3)
        s.volm = 0.5                                                                      # a calm: short expiries cheapest
        self.assertLess(e.option_vol(s, short), e.option_vol(s, long))
        s.volm = 1.0
        self.assertAlmostEqual(e.option_vol(s, short), e.option_vol(s, long), places=9)

    def test_earnings_and_the_crush(self):
        e, s = self.e, self.s
        exps = e.option_expiries()
        s.next_earn = (exps[1] + exps[2]) / 2                                              # between the 2nd and 3rd expiry
        before = [e.atm_vol(s, x) for x in exps]
        self.assertGreater(before[2], before[1] * 1.05)                                   # the event is priced in
        s.next_earn = e.now - 10                                                          # the report is out
        self.assertLess(e.atm_vol(s, exps[2]), before[2] * 0.97)                          # the crush

    def test_a_dividend_makes_calls_cheaper_and_puts_dearer(self):
        e, s = self.e, self.s
        exp = e.option_expiries()[3]
        K = atm(e, s, exp)
        s.div = None
        c0, p0 = e.option_quote(s, "call", K, exp)["mid"], e.option_quote(s, "put", K, exp)["mid"]
        s.div = {"t": e.now + 100, "amt": s.price * 0.02}
        c1, p1 = e.option_quote(s, "call", K, exp)["mid"], e.option_quote(s, "put", K, exp)["mid"]
        self.assertLess(c1, c0)
        self.assertGreater(p1, p0)
        s.div = {"t": exp + 100, "amt": s.price * 0.02}                                   # after expiry: no effect
        self.assertAlmostEqual(e.option_quote(s, "call", K, exp)["mid"], c0, places=9)


class TradingTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(31)
        quiet(self.e)
        self.p = join(self.e, "opty", extra_cash=50000)

    def contract(self, kind="call"):
        e = self.e
        exp = e.option_expiries()[1]
        return kind, atm(e, e.stocks["NVXA"], exp), exp

    def test_the_chain(self):
        e = self.e
        ch = e.option_chain("NVXA")
        self.assertEqual(len(ch["expiries"]), 5)
        self.assertEqual(len(ch["term"]), 5)
        self.assertEqual(ch["exp"], ch["expiries"][1])
        self.assertEqual(len(ch["rows"]), 13)
        for r in ch["rows"]:
            for kind in ("call", "put"):
                q = r[kind]
                self.assertGreaterEqual(q["ask"], q["bid"])
                self.assertTrue({"delta", "gamma", "theta", "vega", "rho", "iv", "itm", "oi"} <= set(q))
        self.assertEqual(e.option_chain("NVXA", ch["expiries"][4])["exp"], ch["expiries"][4])
        self.assertIn("error", e.option_chain("MSI"))                                   # not on the index or the funds
        kind, K, exp = self.contract()
        self.assertTrue(e.buy_option(self.p, "NVXA", kind, K, exp, contracts=2)[0])
        advance(e, 1)
        row = next(r for r in e.option_chain("NVXA", exp)["rows"] if r["K"] == K)
        self.assertEqual(row["call"]["oi"], 2)                                           # open interest: contracts players hold

    def test_whole_contracts_of_a_hundred_shares(self):
        e, p = self.e, self.p
        kind, K, exp = self.contract()
        ask = e.option_quote(e.stocks["NVXA"], kind, K, exp)["ask"]
        cash = p.cash
        ok, msg = e.buy_option(p, "NVXA", kind, K, exp, contracts=3)
        self.assertTrue(ok, msg)
        self.assertIn("3 NVXA", msg)
        self.assertAlmostEqual(p.cash, cash - 3 * 100 * ask * 1.001, places=6)          # a contract costs 100 times its price
        self.assertEqual(p.opts[0]["qty"], 300)                                           # (kept in shares)
        self.assertEqual(e.options_view(p)[0]["contracts"], 3)
        for bad in (0, 1.5, -2, float("nan"), float("inf"), "x", 10 ** 6):
            self.assertFalse(e.buy_option(p, "NVXA", kind, K, exp, contracts=bad)[0], bad)
        poor = join(e, "poor")                                                            # 1,000 MB: no deep in-the-money contract
        deep = min(e.listed_strikes(e.stocks["NVXA"], exp))
        ok, msg = e.buy_option(poor, "NVXA", "call", deep, exp, contracts=1)
        self.assertFalse(ok)
        self.assertIn("Not enough cash", msg)
        self.assertFalse(e.buy_option(poor, "NVXA", "call", deep, exp, amount=50)[0])     # MB that buy no whole contract
        advance(e, 2)
        ok, msg = e.sell_option(p, p.opts[0]["id"], contracts=1)                         # sell one of the three
        self.assertTrue(ok, msg)
        self.assertAlmostEqual(p.opts[0]["qty"], 200, places=9)
        advance(e, 2)
        self.assertFalse(e.sell_option(p, p.opts[0]["id"], contracts=0.5)[0])
        ok, msg = e.sell_option(p, p.opts[0]["id"], contracts=5)                          # more than held: all of it
        self.assertTrue(ok, msg)
        self.assertEqual(p.opts, [])
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_position_from_before_whole_contracts_still_sells(self):
        e, p = self.e, self.p
        kind, K, exp = self.contract()
        self.assertTrue(e.buy_option(p, "NVXA", kind, K, exp, contracts=1)[0])
        pos = p.opts[0]
        for k in ("qty", "cost", "fee"):                                                 # (as if bought as 0.4 of a contract)
            pos[k] *= 0.4
        advance(e, 2)
        ok, msg = e.sell_option(p, pos["id"], contracts=1)
        self.assertTrue(ok, msg)
        self.assertEqual(p.opts, [])

    def test_buy_sell_and_the_books_balance(self):
        e, p = self.e, self.p
        cash = p.cash
        kind, K, exp = self.contract()
        ok, msg = e.buy_option(p, "NVXA", kind, K, exp, contracts=2)
        self.assertTrue(ok, msg)
        spent = cash - p.cash
        self.assertEqual(len(p.opts), 1)
        self.assertLess(abs(drift(e)), 1e-6)
        eq = e.equity(p)
        self.assertLess(eq, cash)                                             # (bought at the ask, valued at the bid)
        self.assertGreater(eq, cash - spent)
        view = e.options_view(p)[0]
        self.assertAlmostEqual(view["pos_delta"], view["qty"] * view["delta"], places=1)    # in shares: 200 times delta
        self.assertLess(view["pos_theta"], 0)
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
        self.assertFalse(e.buy_option(p, "NVXA", kind, K + 0.37, exp, contracts=1)[0])     # a strike not listed
        self.assertFalse(e.buy_option(p, "NVXA", kind, K, exp + 77, contracts=1)[0])        # an expiry not on offer
        self.assertFalse(e.buy_option(p, "NVXA", kind, float("nan"), exp, contracts=1)[0])
        self.assertFalse(e.buy_option(p, "NVXA", kind, K, exp, contracts=9000)[0])          # not enough cash
        self.assertFalse(e.buy_option(p, "NVXA", "straddle", K, exp, contracts=1)[0])
        self.assertFalse(e.buy_option(e.guest, "NVXA", kind, K, exp, contracts=1)[0])
        self.assertFalse(e.is_pro(p))
        self.assertTrue(e.buy_option(p, "NVXA", "put", K, exp, contracts=1)[0])              # free accounts trade options

    def test_settlement_at_expiry_pays_the_payoff(self):
        e, p = self.e, self.p
        exp = e.option_expiries()[0]
        s = e.stocks["NVXA"]
        K = min(e.listed_strikes(s, exp))                                     # deep in the money
        self.assertTrue(e.buy_option(p, "NVXA", "call", K, exp, contracts=2)[0])
        e.now = exp + 0.5
        cash = p.cash
        e._settle_options()
        self.assertEqual(p.opts, [])
        self.assertAlmostEqual(p.cash - cash, 200 * max(0.0, s.price - K), places=6)    # 100 shares a contract
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_bankruptcy_settles_the_options_on_it(self):
        e, p = self.e, self.p
        kind, K, exp = self.contract("put")
        e.buy_option(p, "NVXA", kind, K, exp, contracts=1)
        e._settle_options("NVXA", 0.01)
        self.assertEqual(p.opts, [])
        self.assertLess(abs(drift(e)), 1e-6)

    def test_options_survive_a_save(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            a = new_engine(tmp, 41)
            p = join(a, "keeper", extra_cash=20000)
            s = a.stocks["NVXA"]
            exp = a.option_expiries()[2]
            K = atm(a, s, exp)
            self.assertTrue(a.buy_option(p, "NVXA", "call", K, exp, contracts=1)[0])
            a.save()
            b = engine.Engine(state_file=a.state_file, ledger_path=a.ledger.path)
            self.assertEqual(b.by_token[p.token].opts, p.opts)
            b.stocks["NVXA"].fair *= 1.5                                        # far away: the strike held is still listed
            self.assertIn(K, b.listed_strikes(b.stocks["NVXA"], exp))
            a.ledger.close()
            b.ledger.close()

    def test_a_crash_loses_no_option_trade(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            a = new_engine(tmp, 42)
            p = join(a, "crashy", extra_cash=20000)
            a.save()                                                   # the snapshot is from before the trades
            exp = a.option_expiries()[2]
            K = atm(a, a.stocks["NVXA"], exp)
            self.assertTrue(a.buy_option(p, "NVXA", "call", K, exp, contracts=1)[0])
            advance(a, 2)                                              # (one option trade a second in a stock)
            self.assertTrue(a.buy_option(p, "NVXA", "put", K, exp, contracts=2)[0])
            advance(a, 2)
            self.assertTrue(a.sell_option(p, next(o for o in p.opts if o["kind"] == "put")["id"], contracts=1)[0])
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
