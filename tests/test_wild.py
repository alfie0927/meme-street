"""Moonshots (tiny, wildly volatile companies that keep joining the market and go bankrupt easily), rare catalyst
news that moves any stock a lot, and the fair-bet rules that keep all of it balanced: nothing here may give players
an expected gain or loss."""
import json
import math
import os
import random
import tempfile
import unittest

import _helpers
from _helpers import advance, drift, engine, join, make_engine, quiet

import newsgen


def real_engine(seed, state_file=None, **settings):
    """An engine with the real default settings (moonshots listed at the start, catalysts on) instead of the quiet
    test world."""
    random.seed(seed)
    engine.Engine._read = _helpers._real_read
    try:
        e = engine.Engine(state_file=state_file)
    finally:
        engine.Engine._read = _helpers._flat_read
    e.settings.update(settings)
    quiet(e)
    return e


def moonshots(e):
    return [s for s in e.stocks.values() if s.moonshot]


class MoonshotGenerationTests(unittest.TestCase):
    def test_a_new_game_starts_with_a_few_moonshots_that_are_not_new(self):
        e = real_engine(1)
        moons = moonshots(e)
        self.assertEqual(len(moons), 4)
        for s in moons:
            self.assertEqual(s.listed_at, 0.0)

    def test_a_save_from_before_moonshots_gets_the_starting_moonshots_once(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "state.json")
            old = make_engine(7)                         # the quiet world has no moonshots, like an old game
            old.state_file = path
            old.save()
            saved = json.load(open(path, encoding="utf-8"))
            saved.pop("generated", None)
            json.dump(saved, open(path, "w", encoding="utf-8"))
            e = real_engine(8, state_file=path)
            moons = moonshots(e)
            self.assertEqual(len(moons), 4)
            self.assertTrue(all(s.listed_at == 0 for s in moons))
            e.save()
            again = real_engine(9, state_file=path)      # the new save carries the key: no further top-up
            self.assertEqual(len(moonshots(again)), 4)
            self.assertTrue(all(s.ticker in {m.ticker for m in moons} for s in moonshots(again)))

    def test_moonshots_are_tiny_wild_and_pre_revenue(self):
        rng = random.Random(7)
        taken = set()
        for _ in range(300):
            c = newsgen.make_moonshot(rng, taken)
            taken.add(c["ticker"])
            self.assertEqual(len(c["ticker"]), 4)
            self.assertTrue(c["ticker"].isupper())
            self.assertGreaterEqual(c["vol"], 2.5)
            self.assertGreaterEqual(c["beta"], 2.5)
            self.assertLessEqual(c["depth"], 5000)
            self.assertEqual(c["revenue"], 0.0)
            self.assertEqual(c["dividend_yield"], 0.0)
            self.assertIn("moonshot", c["traits"])
            self.assertTrue(c["desc"] and "{" not in c["desc"])
        self.assertEqual(len(taken), 300)                      # no ticker is ever reused

    def test_only_industries_that_exist_are_used(self):
        rng = random.Random(8)
        for _ in range(100):
            c = newsgen.make_moonshot(rng, set(), {"pharma"})
            self.assertEqual(c["sector"], "pharma")

    def test_biotech_is_the_commonest_kind(self):
        rng = random.Random(9)
        kinds = [newsgen.make_moonshot(rng, set())["kind"] for _ in range(600)]
        self.assertEqual(max(set(kinds), key=kinds.count), "biotech")

    def test_a_moonshot_works_with_the_rest_of_the_engine(self):
        e = real_engine(2)
        s = moonshots(e)[0]
        self.assertTrue(s.persona)
        self.assertIn(s.rating, ("D", "C", "CC", "CCC", "B"))
        self.assertIsNone(s.next_earn)                          # no revenue, no earnings reports
        p = join(e, "moonbuyer")
        ok, msg = e.trade(p, s.ticker, "buy", 0.5)
        self.assertTrue(ok, msg)
        advance(e, 60)
        self.assertLess(abs(drift(e)), 1e-6)


class MoonshotCycleTests(unittest.TestCase):
    def test_new_moonshots_list_over_time_up_to_a_maximum(self):
        e = real_engine(3, moonshot_max=6)
        e.tick(now=e.now)
        n0 = len(moonshots(e))
        for _ in range(8):
            e.next_moonshot = e.now
            e.tick(now=e.now + 1)
        self.assertEqual(len(moonshots(e)), 6)
        self.assertGreater(len(moonshots(e)), n0)
        newest = max(moonshots(e), key=lambda s: s.listed_at)
        self.assertEqual(newest.listed_at, newest.listed_at)
        self.assertGreater(newest.listed_at, 0)
        self.assertTrue(any("NEW LISTING" in n["text"] for n in e.news_log))

    def test_a_new_listing_has_no_first_day_pop(self):
        e = real_engine(4)
        e.tick(now=e.now)
        e.next_moonshot = e.now
        e.tick(now=e.now + 1)
        s = max(moonshots(e), key=lambda x: x.listed_at)
        ratio = s.price / s.initial_price
        self.assertTrue(0.5 < ratio < 2.0, ratio)               # it lists at its reference price

    def test_tickers_are_never_reused_after_a_bankruptcy(self):
        e = real_engine(5, moonshot_max=3)
        e.tick(now=e.now)
        gone = set()
        for _ in range(12):
            for s in moonshots(e):
                s.fair = s.initial_price * 0.1
                s.distress_checked = False
            before = set(e.stocks)
            random.seed(len(gone))
            e._check_distress()
            gone |= before - set(e.stocks)
            e.next_moonshot = e.now
            e.tick(now=e.now + 1)
        self.assertTrue(gone)
        self.assertFalse(gone & set(e.stocks), "a delisted ticker came back")
        self.assertEqual(set(e.delisted) & set(e.stocks), set())

    def test_moonshots_survive_a_restart_and_the_dead_do_not(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path = os.path.join(d, "state.json")
            e = real_engine(6, state_file=path)
            e.tick(now=e.now)
            e.next_moonshot = e.now
            e.tick(now=e.now + 1)
            moons = {s.ticker: s.price for s in moonshots(e)}
            newest = max(moonshots(e), key=lambda s: s.listed_at).ticker
            e.save()
            self.assertEqual({c["ticker"] for c in json.load(open(path, encoding="utf-8"))["generated"]}, set(moons))
            random.seed(1)
            engine.Engine._read = _helpers._real_read
            try:
                f = engine.Engine(state_file=path)
            finally:
                engine.Engine._read = _helpers._flat_read
            self.assertEqual({s.ticker for s in moonshots(f)}, set(moons))
            for tk, price in moons.items():
                self.assertAlmostEqual(f.stocks[tk].price, price, places=9)
            self.assertEqual(f.stocks[newest].listed_at, e.stocks[newest].listed_at)
            self.assertTrue(f.stocks[newest].persona)
            self.assertLess(abs(drift(f)), 1e-6)


class WildMoveTests(unittest.TestCase):
    def setUp(self):
        self.e = real_engine(10)
        self.moon = moonshots(self.e)[0]
        self.normal = self.e.stocks["NVXA"]

    def test_the_daily_limit_lets_moonshots_run(self):
        e, m, n = self.e, self.moon, self.normal
        cap = float(e.settings.get("daily_move_cap", 0.15))
        for s in (m, n):
            s.fair = s.fair_open * math.exp(0.7)                # up about 100% on the day
        self.assertGreater(e._envelope_damping(m, cap), 0.8)
        self.assertLess(e._envelope_damping(n, cap), 0.01)

    def test_the_limit_is_still_direction_blind_for_moonshots(self):
        e, m = self.e, self.moon
        cap = float(e.settings.get("daily_move_cap", 0.15))
        for x in (0.3, 1.0, 2.0):
            m.fair = m.fair_open * math.exp(x)
            up = e._envelope_damping(m, cap)
            m.fair = m.fair_open * math.exp(-x)
            self.assertAlmostEqual(up, e._envelope_damping(m, cap), places=12)

    def test_noise_per_second_is_far_bigger_than_for_a_normal_stock(self):
        e, m, n = self.e, self.moon, self.normal
        e.now = (int(e.now // 1800) + 1) * 1800 + 900
        e._update_session()
        spread = {}
        for s in (m, n):
            draws = []
            for _ in range(400):
                e._pending = {}
                e._random_market_moves()
                draws.append(e._pending[s.ticker])
            mean = sum(draws) / len(draws)
            spread[s.ticker] = math.sqrt(sum((x - mean) ** 2 for x in draws) / len(draws))
            self.assertLess(abs(mean), 4 * spread[s.ticker] / math.sqrt(len(draws)), "noise has a direction")
        self.assertGreater(spread[m.ticker], 5 * spread[n.ticker])

    def test_moonshots_are_not_pulled_back_to_their_reference_price(self):
        e, m, n = self.e, self.moon, self.normal
        m.fair = m.initial_price * 8
        n.fair = n.initial_price * 3
        e._pending = {}
        e._mean_revert()
        self.assertNotIn(m.ticker, e._pending)
        self.assertIn(n.ticker, e._pending)

    def test_a_big_catalyst_move_is_not_cut_by_the_per_second_limit(self):
        e, m = self.e, self.moon
        price = m.price
        m.move(2.0)                                             # +200% in one go
        self.assertAlmostEqual(m.price / price, 3.0, places=9)


class MarginForWildStocksTests(unittest.TestCase):
    def test_margin_and_maintenance_rise_for_moonshots_but_not_for_the_usual_stocks(self):
        e = real_engine(11)
        wild = max(moonshots(e), key=lambda s: s.vol)
        self.assertGreater(e.margin_req(wild), 2.0)
        self.assertLessEqual(e.margin_req(wild), 3.0)
        self.assertGreater(e.maintenance(wild), 0.5)
        self.assertLessEqual(e.maintenance(wild), 0.75)
        self.assertEqual(e.margin_req(e.stocks["GOLD"]), 1.0)
        self.assertEqual(e.margin_req(e.stocks["DOGO"]), 2.0)
        self.assertEqual(e.maintenance(e.stocks["DOGO"]), 0.5)

    def test_a_moonshot_can_be_shorted_as_far_as_cash_goes_with_no_borrow_cap(self):
        e = real_engine(12)
        s = moonshots(e)[0]
        p = join(e, "bigshort", extra_cash=1_000_000)
        ok, msg = e.trade(p, s.ticker, "sell", 1.0)
        self.assertTrue(ok, msg)
        self.assertGreater(-p.hold[s.ticker] * s.price, 100 * e.short_cap(s))           # far past the old borrow pool
        self.assertAlmostEqual(p.cash, 0.0, places=6)                                  # the whole stake is the collateral
        self.assertLess(abs(drift(e)), 1e-6)


class DistressIsAFairBetTests(unittest.TestCase):
    """Rescue or bankruptcy: q * payout + (1 - q) * (1 + jump) = 1, so buying or shorting a stock that is about to be
    resolved has no expected gain or loss (the old rule, a 25% chance of +25% against a 75% chance of -50%, was a
    free short)."""

    def test_the_terms_are_fair_for_every_stock_type(self):
        e = real_engine(13)
        for s in (e.stocks["NVXA"], moonshots(e)[0]):
            q, payout, jump = e._distress_terms(s)
            self.assertAlmostEqual(q * payout + (1 - q) * (1 + jump), 1.0, places=12)
            self.assertGreater(jump, 0)

    def test_moonshots_go_bankrupt_more_often_and_are_wiped_out(self):
        e = real_engine(14)
        qn, pn, jn = e._distress_terms(e.stocks["NVXA"])
        qm, pm, jm = e._distress_terms(moonshots(e)[0])
        self.assertGreater(qm, qn)
        self.assertLess(pm, pn)
        self.assertGreater(jm, jn)                              # and the rare rescue is a much bigger pop

    def test_a_forced_bankruptcy_pays_the_fraction_and_delists(self):
        e = real_engine(15)
        s = moonshots(e)[0]
        p = join(e, "holder")
        e.trade(p, s.ticker, "buy", 0.2)
        shares = p.hold[s.ticker]
        s.fair = s.initial_price * 0.2
        e._pending = {}
        q, payout, jump = e._distress_terms(s)
        before_cash = p.cash
        real = engine.random.random
        engine.random.random = lambda: 0.0                      # force bankruptcy
        try:
            price_before = s.price
            e._check_distress()
        finally:
            engine.random.random = real
        self.assertTrue(s.ticker not in e.stocks, "the moonshot should have been delisted")
        self.assertIn(s.ticker, e.delisted)
        self.assertAlmostEqual(p.cash - before_cash, shares * price_before * payout, places=6)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_forced_rescue_multiplies_the_price_by_the_fair_amount(self):
        e = real_engine(16)
        s = moonshots(e)[0]
        s.fair = s.initial_price * 0.2
        price = s.price
        q, payout, jump = e._distress_terms(s)
        real = engine.random.random
        engine.random.random = lambda: 0.999                    # force the rescue
        try:
            e._check_distress()
        finally:
            engine.random.random = real
        self.assertTrue(s.ticker in e.stocks, "the moonshot should have been rescued")
        self.assertAlmostEqual(s.price / price, 1 + jump, places=9)
        self.assertGreater(s.price, price * 2)

    def test_a_rescued_stock_is_armed_again_and_one_that_kept_collapsing_is_resolved(self):
        e = real_engine(17)
        s = next(x for x in e.stocks.values() if x.asset_type == "equity" and not x.moonshot)
        s.fair = s.initial_price * 0.2
        real = engine.random.random
        engine.random.random = lambda: 0.999                    # a rescue (x1.75: back to 0.35 of the reference)
        try:
            e._check_distress()
        finally:
            engine.random.random = real
        self.assertIn(s.ticker, e.stocks)
        self.assertGreater(s.fair / s.initial_price, 0.3)
        e._check_distress()
        self.assertFalse(s.distress_checked)                    # clear of the line, so a later fall is a new episode
        # the live game once had stocks at 1e-20 of their reference, flagged as already resolved and never looked at again
        t2 = next(x for x in e.stocks.values() if x.asset_type == "equity" and not x.moonshot and x is not s)
        t2.fair = t2.initial_price * 1e-20
        t2.distress_checked = True
        e._check_distress()
        self.assertNotIn(t2.ticker, e.stocks)
        self.assertIn(t2.ticker, e.delisted)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_it_is_a_fair_bet_in_expectation_over_many_draws(self):
        e = real_engine(17)
        s = moonshots(e)[0]
        q, payout, jump = e._distress_terms(s)
        rng = random.Random(3)
        n = 200_000
        total = sum(payout if rng.random() < q else 1 + jump for _ in range(n)) / n
        self.assertAlmostEqual(total, 1.0, delta=0.05)


class CatalystTests(unittest.TestCase):
    def test_every_catalyst_is_a_fair_two_outcome_bet(self):
        for k in newsgen.CATALYSTS:
            p = k["p"]
            for lo, hi in (k["up"], k["up_moon"]):
                for up in (lo, (lo + hi) / 2, hi):
                    up = min(up, 0.95 * (1 - p) / p)
                    down = -p * up / (1 - p)
                    self.assertAlmostEqual(p * up + (1 - p) * down, 0.0, places=12, msg=k["key"])
                    self.assertGreaterEqual(down, -0.95 - 1e-12)
            self.assertTrue(k["texts_up"] and k["texts_down"])
            self.assertTrue(0 < p < 1)

    def test_catalyst_texts_name_the_company(self):
        for k in newsgen.CATALYSTS:
            for t in k["texts_up"] + k["texts_down"]:
                self.assertIn("{name}", t)

    def fire(self, e, n):
        """Fire n catalysts, undoing each price move afterwards so the stocks do not wander. Returns the moves."""
        moves = []
        for _ in range(n):
            before = {tk: s.fair for tk, s in e.stocks.items()}
            e.next_catalyst = e.now
            e._catalysts()
            changed = [(tk, e.stocks[tk].fair / before[tk] - 1) for tk in before
                       if tk in e.stocks and e.stocks[tk].fair != before[tk]]
            self.assertEqual(len(changed), 1)
            tk, r = changed[0]
            moves.append((e.stocks[tk].moonshot, r, tk))
            for t, f in before.items():
                if t in e.stocks:
                    e.stocks[t].fair = f
        return moves

    def test_a_catalyst_moves_one_stock_and_prints_a_headline(self):
        e = real_engine(20)
        n = len(e.news_log)
        ((moon, r, tk),) = self.fire(e, 1)
        self.assertEqual(len(e.news_log), n + 1)
        item = e.news_log[-1]
        self.assertTrue(item["text"].startswith("BREAKING: "))
        self.assertEqual(item["tickers"], [tk])
        self.assertEqual(item["dir"], 1 if r > 0 else -1)
        self.assertIn(e.stocks[tk].name, item["text"])

    def test_the_expected_move_is_zero(self):
        e = real_engine(21)
        moves = self.fire(e, 3000)
        for subset in (moves, [m for m in moves if m[0]], [m for m in moves if not m[0]]):
            rs = [m[1] for m in subset]
            mean = sum(rs) / len(rs)
            sd = math.sqrt(sum((r - mean) ** 2 for r in rs) / len(rs))
            self.assertLess(abs(mean), 4 * sd / math.sqrt(len(rs)), (len(rs), mean, sd))

    def test_a_catalyst_moves_even_a_calm_stock_noticeably_but_big_falls_are_rare_and_nothing_loses_95_percent(self):
        e = real_engine(22)
        moves = self.fire(e, 2500)
        calm = [r for moon, r, tk in moves if not moon]
        self.assertGreater(len(calm), 300)
        self.assertGreater(sum(1 for r in calm if abs(r) >= 0.05) / len(calm), 0.85)      # still news, not a wobble
        falls = [-r for r in calm if r < 0]
        big = sum(1 for f in falls if f >= 0.25) / len(calm)
        self.assertLess(big, 0.12)                                                         # a 25% fall is the rare case (it used to be about half of all catalysts)
        self.assertGreater(big, 0.03)                                                      # ...but it still happens
        self.assertLess(sum(1 for f in falls if f >= 0.40) / len(calm), 0.07)
        self.assertLess(max(r for r in calm), 0.45)                                        # and the good news is no longer +80%
        self.assertGreaterEqual(min(r for _, r, _ in moves), -0.95 - 1e-9)

    def test_every_ordinary_catalyst_is_a_fair_three_outcome_bet_with_a_rare_disaster(self):
        for k in newsgen.CATALYSTS:
            t = newsgen.CATALYST_TIERS[k["key"]]
            self.assertAlmostEqual(t["p_good"] + t["p_bad"] + t["p_dis"], 1.0, places=12, msg=k["key"])
            self.assertLessEqual(t["p_dis"], 0.10, k["key"])                               # a disaster is rare...
            self.assertGreaterEqual(t["dis"][0], 0.20, k["key"])                           # ...and big
            self.assertLessEqual(t["dis"][1], 0.70, k["key"])
            self.assertLessEqual(t["bad"][1], 0.14, k["key"])                              # a setback is small
            self.assertLess(t["bad"][1], t["dis"][0], k["key"])
            for bad in (t["bad"][0], t["bad"][1]):
                for dis in (t["dis"][0], t["dis"][1]):
                    up = (t["p_bad"] * bad + t["p_dis"] * dis) / t["p_good"]
                    self.assertAlmostEqual(t["p_good"] * up - t["p_bad"] * bad - t["p_dis"] * dis, 0.0, places=12, msg=k["key"])
                    self.assertLess(up, 0.40, k["key"])                                    # the good news gains at most about 40%
                    self.assertGreater(up, 0.05, k["key"])

    def test_an_ordinary_catalyst_uses_the_three_outcome_texts_and_a_disaster_has_its_own_headlines(self):
        e = real_engine(26)
        random.seed(26)
        seen = {"good": 0, "bad": 0, "disaster": 0}
        for _ in range(900):
            kind = random.choice(newsgen.CATALYSTS)
            r, good, texts = e._ordinary_catalyst(kind)
            t = newsgen.CATALYST_TIERS[kind["key"]]
            if good:
                self.assertGreater(r, 0)
                self.assertEqual(texts, kind["texts_up"])
                seen["good"] += 1
            elif texts is t["texts_bad"]:
                self.assertTrue(-t["bad"][1] - 1e-12 <= r <= -t["bad"][0] + 1e-12)
                seen["bad"] += 1
            else:
                self.assertIs(texts, t["texts_dis"])
                self.assertTrue(-t["dis"][1] - 1e-12 <= r <= -t["dis"][0] + 1e-12)
                seen["disaster"] += 1
        self.assertGreater(seen["good"], 300)
        self.assertGreater(seen["bad"], 250)
        self.assertGreater(seen["disaster"], 30)
        self.assertLess(seen["disaster"], 110)

    def test_the_tiered_texts_exist_name_the_company_and_the_disasters_are_never_also_setbacks(self):
        for k in newsgen.CATALYSTS:
            t = newsgen.CATALYST_TIERS[k["key"]]
            self.assertGreaterEqual(len(t["texts_bad"]), 3)
            self.assertGreaterEqual(len(t["texts_dis"]), 3)
            for text in t["texts_bad"] + t["texts_dis"]:
                self.assertIn("{name}", text)
            self.assertFalse(set(t["texts_bad"]) & set(t["texts_dis"]))
            self.assertFalse(set(t["texts_dis"]) & set(k["texts_down"]), k["key"])           # (the old two-outcome headlines are for moonshots)

    def test_a_moonshot_still_gets_the_old_two_outcome_bet(self):
        e = real_engine(27)
        e.settings["catalyst_moonshot_weight"] = 1e12                                     # (every catalyst lands on a moonshot)
        moves = self.fire(e, 400)
        falls = [-r for moon, r, _ in moves if moon and r < 0]
        self.assertGreater(len(falls), 80)
        self.assertGreater(sum(1 for f in falls if f >= 0.25) / len(falls), 0.5)          # a lottery ticket: its bad outcome is a collapse

    def test_moonshots_get_bigger_and_more_frequent_catalysts(self):
        e = real_engine(23)
        moves = self.fire(e, 2000)
        moon = [abs(r) for m, r, _ in moves if m]
        calm = [abs(r) for m, r, _ in moves if not m]
        self.assertGreater(len(moon) / len(moves), 0.12)        # 4 moonshots out of ~150 stocks, but 10x as likely
        self.assertGreater(sum(moon) / len(moon), 1.5 * sum(calm) / len(calm))

    def test_a_catalyst_makes_the_stock_jumpier_afterwards(self):
        e = real_engine(24)
        before = {tk: s.volm for tk, s in e.stocks.items()}
        self.fire(e, 1)
        self.assertTrue(any(s.volm > before[tk] for tk, s in e.stocks.items()))

    def test_money_is_conserved_with_catalysts_moonshots_and_bankruptcies_all_running(self):
        e = real_engine(25, catalyst_mean_seconds=10, moonshot_mean_seconds=30)
        players = [join(e, f"wild{i}") for i in range(4)]
        e.tick(now=e.now)
        for k in range(1500):
            e.tick(now=e.now + 1)
            if k % 17 == 0:
                p = players[k % 4]
                tk = random.choice([s.ticker for s in moonshots(e)] + ["NVXA", "GOLD"])
                e.trade(p, tk, random.choice(["buy", "sell"]), 0.3)
        self.assertLess(abs(drift(e)), 1e-6)
        self.assertTrue(e.delisted or any(s.listed_at for s in moonshots(e)))


if __name__ == "__main__":
    unittest.main()
