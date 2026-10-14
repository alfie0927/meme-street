"""The learn-to-trade price model (market_model.py): drift, regimes, swings, support and resistance, the macro calendar
and how the engine uses it (volume on every candle, macro headlines, earnings forecasts, saving and loading)."""
import json
import math
import os
import random
import tempfile
import types
import unittest

from _helpers import IsolatedServer, drift, engine, join, make_engine, quiet
import market_model as mm  # noqa: E402  (after _helpers, which puts the project on the path)
import paths  # noqa: E402
from test_server import http


def listing(tk="AAA", price=100.0, vol=0.3, beta=1.0, sector="tech"):
    return types.SimpleNamespace(ticker=tk, price=price, vol=vol, beta=beta, sector=sector, asset_type="equity", moonshot=False)


class RegimeAndDriftTests(unittest.TestCase):
    def test_the_regimes_add_no_drift_of_their_own_in_the_long_run(self):
        centred = sum(mm.REGIME_SHARE[n] * (mm.REGIMES[n][0] - mm.REGIME_MEAN_DRIFT) for n in mm.REGIMES)
        self.assertAlmostEqual(centred, 0.0, places=9)
        self.assertAlmostEqual(sum(mm.REGIME_SHARE.values()), 1.0, places=9)
        self.assertGreater(mm.REGIME_SHARE["bull"], mm.REGIME_SHARE["bear"])      # bull markets last longer

    def test_the_long_run_drift_is_rf_plus_beta_times_the_premium(self):
        p = dict(mm.DEFAULTS)
        self.assertAlmostEqual(mm.MarketModel.drift_of(listing(beta=1.0), p), p["rf"] + p["erp"])
        self.assertGreater(mm.MarketModel.drift_of(listing(beta=1.5), p), mm.MarketModel.drift_of(listing(beta=0.5), p))
        moon = types.SimpleNamespace(**dict(vars(listing()), moonshot=True))
        self.assertEqual(mm.MarketModel.drift_of(moon, p), 0.0)

    def test_regimes_change_and_last_a_bounded_time(self):
        m = mm.MarketModel({}, rng=random.Random(4), now=0.0)
        seen, t = set(), 0.0
        for _ in range(200):
            t = m.regime_until + 1
            m._regime_step(t)
            seen.add(m.regime)
            self.assertLessEqual(m.regime_until - t, 3 * mm.REGIMES[m.regime][2] * mm.DAY + 1)
        self.assertEqual(seen, set(mm.REGIMES))

    def test_a_quiet_market_with_no_noise_follows_its_drift(self):
        """With no noise and no swings the model's own moves add up to the drift a game year (about +5.5% for beta 1)."""
        m = mm.MarketModel({"price_model": {"trend_strength": 0.0, "release_sigmas": 0.0}}, rng=random.Random(1), now=0.0)
        m.regime, m.regime_until = "sideways", 1e18
        x = listing()
        sw = m.swing(x, 0.0)
        sw.until = 1e18
        for t in range(0, 30 * mm.DAY, 60):
            r, _, _ = m.step(float(t), 60.0, [x])
            sw.test = None
            sw.levels = []
            x.price *= 1 + r[x.ticker]
        expect = (mm.MarketModel.drift_of(x, m.p) + m.regime_drift()) * 30 / 365
        self.assertAlmostEqual(math.log(x.price / 100.0), expect, delta=0.002)


class SwingAndLevelTests(unittest.TestCase):
    def setUp(self):
        self.m = mm.MarketModel({}, rng=random.Random(2), now=0.0)
        self.x = listing(price=100.0)
        self.sw = self.m.swing(self.x, 0.0)
        self.sw.until = 1e18

    def test_round_numbers(self):
        self.assertEqual(mm.round_step(145), 10)
        self.assertEqual(mm.round_step(440), 25)
        self.assertEqual(mm.round_step(8.7), 0.5)

    def test_levels_come_from_swing_highs_lows_and_round_numbers(self):
        sw = self.sw
        prices = [100, 101, 102, 103, 104, 105, 104, 103, 102, 101, 100, 99, 98, 99, 100, 101, 102, 103, 104, 105.1, 104, 103, 102, 101, 100]
        for i, p in enumerate(prices):
            sw.bars.append([i * mm.BAR, p + 0.05, p - 0.05, p])
        self.m._find_levels(sw, 101.0)
        tops = [lv for lv in sw.levels if 104.9 < lv[0] < 105.3]
        self.assertTrue(tops and tops[0][1] == 2, sw.levels)          # the two highs near 105 are one level, touched twice
        self.assertTrue(any(lv[2] and abs(lv[0] - 110) < 1e-9 for lv in sw.levels) or any(lv[2] and abs(lv[0] - 100) < 1e-9 for lv in sw.levels))

    def test_a_held_support_pushes_the_price_up_and_a_break_pushes_it_through(self):
        sw, x = self.sw, self.x
        sig_d = x.vol / math.sqrt(365)
        sw.levels = [[99.9, 3, True]]
        self.m.rng = types.SimpleNamespace(random=lambda: 0.0, uniform=lambda a, b: a, gauss=random.gauss)   # it holds
        r, _, v = self.m._level_step(x, sw, 0.0, 1.0, math.log(100.0), sig_d)
        self.assertEqual(sw.test["outcome"], "hold")
        self.assertGreater(r, 0)
        self.assertGreater(v, 1.0)
        sw.test, sw.tested = None, type(sw.tested)(maxlen=12)
        self.m.rng = types.SimpleNamespace(random=lambda: 0.999, uniform=lambda a, b: a, gauss=random.gauss)  # it breaks
        r, _, _ = self.m._level_step(x, sw, 0.0, 1.0, math.log(100.0), sig_d)
        self.assertEqual(sw.test["outcome"], "break")
        self.assertEqual(r, 0.0)                                             # nothing pushes it to the level
        r, n, v = self.m._level_step(x, sw, 5.0, 1.0, math.log(99.8), sig_d)     # through it: the follow-through
        self.assertLess(r, 0)
        self.assertGreater(v, 2.0)

    def test_strong_levels_hold_more_often_than_weak_ones_and_repeated_tests_weaken_them(self):
        def p_hold(strength, rnd, repeats=0):
            sw = mm.Swing(0.0, 100.0)
            sw.levels = [[99.95, strength, rnd]]
            for i in range(repeats):
                sw.tested.append([-5000.0 - i, 99.95])
            self.m.regime = "sideways"
            self.m._start_test(self.x, sw, 0.0, math.log(100.0), 0.004)
            return sw.test["p_hold"]
        self.assertGreater(p_hold(3, True), p_hold(1, False))
        self.assertLess(p_hold(3, True, repeats=3), p_hold(3, True))

    def test_a_range_pulls_back_to_its_middle(self):
        sw, x = self.sw, self.x
        sw.mode, sw.center = "range", math.log(100.0)
        r_above, n, v = self.m._mode_step(x, sw, 1.0, 1.0, math.log(103.0), 0.016, 0.0)
        r_below, _, _ = self.m._mode_step(x, sw, 1.0, 1.0, math.log(97.0), 0.016, 0.0)
        self.assertLess(r_above, 0)
        self.assertGreater(r_below, 0)
        self.assertLess(n, 1.0)        # quieter
        self.assertLess(v, 1.0)        # and on lower volume

    def test_a_pulse_delivers_exactly_its_move(self):
        for whip in (False, True):
            pl = mm.Pulse(0.0, 120, 25, {"A": 0.01}, whip=whip)
            self.assertEqual(pl.frac(0), 0.0)
            self.assertAlmostEqual(pl.frac(120), 1.0)
            total = sum(pl.frac(t + 1) - pl.frac(t) for t in range(120))
            self.assertAlmostEqual(total, 1.0, places=9)
        self.assertLess(mm.Pulse(0.0, 45, 8, {}, whip=True).frac(5), 0)         # a whipsaw goes the wrong way first


class EconomyTests(unittest.TestCase):
    def test_the_calendar_has_the_right_number_of_each_release_a_game_year(self):
        e = mm.Economy(random.Random(1))
        year = 365 * mm.DAY
        count = lambda k: len(e.times(k, 1e9, 1e9 + year))
        self.assertEqual(count("rates"), 8)
        self.assertIn(count("cpi"), (12, 13))
        self.assertIn(count("claims"), (52, 53))
        self.assertIn(count("gdp"), (4, 5))
        ups = e.upcoming(1e9, days=40)
        self.assertEqual([t for t, _ in ups], sorted(t for t, _ in ups))

    def test_forecasts_are_published_ahead_and_fixed(self):
        e = mm.Economy(random.Random(2))
        now = 1e9
        e.publish(now)
        self.assertTrue(e.consensus)
        for key, c in e.consensus.items():
            self.assertLessEqual(c["t"] - now, e.KINDS[c["kind"]][4] * mm.DAY)
        before = json.dumps(e.consensus, sort_keys=True)
        e.publish(now + 10)
        self.assertTrue(all(e.consensus[k] == v for k, v in json.loads(before).items()))

    def test_a_release_compares_the_figure_with_the_forecast(self):
        e = mm.Economy(random.Random(3))
        t = e.times("cpi", 1e9, 1e9 + 40 * mm.DAY)[0]
        e.publish(t - mm.DAY)
        rec, gz, rz = e.release("cpi", t)
        self.assertIn("forecast", e.headline(rec))
        self.assertEqual(gz, 0.0)
        self.assertAlmostEqual(rz, (rec["actual"] - rec["consensus"]) / 0.15 * (1.0 if e.infl > 2.5 else 0.7), places=6)
        self.assertEqual(e.past[-1]["kind"], "cpi")

    def test_rate_decisions_follow_the_rule_and_move_in_quarter_points(self):
        e = mm.Economy(random.Random(4))
        e.infl, e.growth, e.rate = 5.0, 3.0, 2.0                 # far below what the rule wants: a rise is priced
        c = e._forecast("rates")
        self.assertGreater(c["move"], 0)
        self.assertGreaterEqual(c["p"], 0.5)
        rates = set()
        for i in range(30):
            t = e.times("rates", 1e9 + i * 50 * mm.DAY, 1e9 + (i + 1) * 50 * mm.DAY)[0]
            e.release("rates", t)
            rates.add(e.rate * 4 == round(e.rate * 4))
        self.assertEqual(rates, {True})
        self.assertGreater(e.rate, 2.0)


class EngineTests(unittest.TestCase):
    def model_engine(self, seed=11):
        e = make_engine(seed, market_model=2)
        quiet(e)
        e.tick(now=e.now + 1)
        self.assertIsNotNone(e.model)
        return e

    def test_the_model_is_off_in_the_old_market_and_on_with_the_setting(self):
        self.assertIsNone(make_engine(1).model)
        self.assertEqual(engine.Engine(state_file=None).settings.get("market_model"), 1)   # (the test setting)
        with open(os.path.join(paths.CONTENT, "base.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["settings"]["market_model"], 2)                 # the game itself

    def test_candles_carry_volume_and_money_is_conserved(self):
        e = self.model_engine()
        p = join(e, "vol")
        e.trade(p, "NVXA", "buy", 0.5)
        for _ in range(240):
            e.tick(now=e.now + 1)
        s = e.stocks["NVXA"]
        self.assertEqual(len(s.tf["1m"][-1]), 6)
        self.assertGreater(s.tf["1m"][-1][5], 0)
        chart = e.chart_for("NVXA", "1m")
        self.assertGreater(chart["candles"][-1]["v"], 0)
        self.assertEqual(e.chart_for("MSI", "1m")["candles"][-1]["v"], 0)          # an index has no volume of its own
        self.assertLess(abs(drift(e)), 1e-6)

    def test_prices_are_on_a_tick_grid_and_trades_fill_at_the_quoted_price(self):
        e = self.model_engine(17)
        for _ in range(30):
            e.tick(now=e.now + 1)
        for s in e.stocks.values():
            tick = 0.01 if s.fair >= 1 else 0.0001
            self.assertAlmostEqual(s.price / tick, round(s.price / tick), places=6)
        s = e.stocks["NVXA"]
        p = join(e, "ticks")
        cash = p.cash
        e.trade(p, "NVXA", "buy", 0.5)
        self.assertAlmostEqual(p.hold["NVXA"], cash * 0.5 * (1 - engine.FEE) / s.price, places=9)
        self.assertLess(abs(drift(e)), 1e-6)
        self.assertFalse(make_engine(1).stocks["NVXA"].ticked)          # the old market keeps continuous prices

    def test_player_trades_still_never_move_a_price(self):
        e = self.model_engine(12)
        p = join(e, "nomove")
        before = e.stocks["NVXA"].fair
        e.trade(p, "NVXA", "buy", 1.0)
        self.assertEqual(e.stocks["NVXA"].fair, before)

    def test_a_macro_release_makes_a_headline_and_moves_the_market(self):
        e = self.model_engine(13)
        t, kind = e.model.economy.upcoming(e.now, days=40)[0]
        e.model.economy.publish(t - 60)
        e.now = t - 2
        e.tick(now=t - 1)
        n = len(e.news_log)
        e.tick(now=t)
        e.tick(now=t + 1)
        texts = [x["text"] for x in list(e.news_log)[n:] if x["kind"] == "macro"]
        self.assertTrue(texts, list(e.news_log)[-3:])
        self.assertTrue(any("forecast" in x or "Rate decision" in x for x in texts), texts)
        released = [x["kind"] for x in e.model.economy.past if x["t"] == t]   # two can fall on one moment (claims and GDP)
        self.assertIn(kind, released)
        cal = e.macro_calendar()
        self.assertTrue(cal["on"])
        self.assertIn(kind, [x["kind"] for x in cal["past"][:len(released)]])
        self.assertTrue(any(u.get("macro") for u in e._upcoming_events()))

    def test_earnings_are_judged_against_a_forecast(self):
        e = self.model_engine(14)
        s = next(x for x in e.stocks.values() if x.next_earn and x.asset_type == "equity" and x.shares_outstanding > 0)
        s.next_earn = e.now + 60
        fc = e._earnings_forecast(s)
        self.assertIsNotNone(fc)
        self.assertEqual(e._earnings_forecast(s), fc)                 # fixed once published
        for _ in range(65):
            e.tick(now=e.now + 1)
        text = next(x["text"] for x in reversed(e.news_log) if x["kind"] == "earnings" and s.ticker in x["tickers"])
        self.assertIn("the forecast", text)
        self.assertNotIn(s.ticker, e.model.earn_forecast)

    def test_the_model_survives_a_save_and_a_load(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(15)
            a = engine.Engine(state_file=path)
            a.settings["market_model"] = 2
            a.tick(now=a.now + 1)
            quiet(a)
            for _ in range(30):
                a.tick(now=a.now + 1)
            a.model.regime, a.model.economy.rate = "bear", 4.25
            sw = a.model.swings["NVXA"]
            sw.mode, sw.dir = "trend", -1
            a.save()
            b = engine.Engine(state_file=path)
            b.settings["market_model"] = 2
            b.tick(now=b.now + 1)
            self.assertEqual(b.model.regime, "bear")
            self.assertEqual(b.model.economy.rate, 4.25)
            self.assertEqual((b.model.swings["NVXA"].mode, b.model.swings["NVXA"].dir), ("trend", -1))
            self.assertTrue(b.model.swings["NVXA"].bars)                  # rebuilt from the 5-minute candles

    def test_a_save_from_the_old_market_loads_into_the_new_one(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(16)
            a = engine.Engine(state_file=path)
            a.tick(now=a.now + 1)
            a.save()
            b = engine.Engine(state_file=path)
            b.settings["market_model"] = 2
            quiet(b)
            for _ in range(5):
                b.tick(now=b.now + 1)
            self.assertIsNotNone(b.model)
            self.assertLess(abs(drift(b)), 1e-6)


class ServerTests(unittest.TestCase):
    def test_the_calendar_and_the_admin_view(self):
        with IsolatedServer() as srv:
            status, text, _ = http(srv, "/api/calendar")
            self.assertEqual(status, 200)
            cal = json.loads(text)
            self.assertTrue(cal["on"])
            self.assertTrue(cal["upcoming"])
            self.assertEqual(http(srv, "/api/admin/model")[0], 403)
            m = json.loads(http(srv, "/api/admin/model", headers={"X-Admin-Key": "testkey"})[1])
            self.assertIn(m["regime"], mm.REGIMES)


if __name__ == "__main__":
    unittest.main()
