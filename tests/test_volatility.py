"""Volatility clustering, the market-wide volatility state, very strong events lifting the daily limit, and the
trading sessions (pre-market, regular session, after-hours: thin noise outside the session, a burst and a jump at
the open)."""
import math
import random
import unittest

from _helpers import advance, drift, engine, join, make_engine, quiet


class VolatilityTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(70)
        quiet(self.e)
        self.s = self.e.stocks["NVXA"]
        self.sigma_tick = self.e._daily_sigma(self.s) / math.sqrt(engine.MARKET_DAY_SECONDS)

    def simulate(self, steps, seed=1, k=None):
        """A single stock's noise process driven by the engine's own volatility update."""
        e, s = self.e, self.s
        if k is not None:
            e.settings["vol_cluster_k"] = k
        s.volm = 1.0
        rng = random.Random(seed)
        out = []
        for _ in range(steps):
            r = self.sigma_tick * e._vol_multiplier(s) * rng.gauss(0, 1)
            e._update_volatility(s, r)
            out.append(r)
        return out

    @staticmethod
    def autocorr(xs):
        m = sum(xs) / len(xs)
        num = sum((a - m) * (b - m) for a, b in zip(xs, xs[1:]))
        den = sum((a - m) ** 2 for a in xs)
        return num / den

    @staticmethod
    def block_means(returns, block=120):
        return [sum(abs(r) for r in returns[i:i + block]) / block for i in range(0, len(returns) - block, block)]

    def test_calm_and_stormy_stretches_cluster_together(self):
        clustered = self.autocorr(self.block_means(self.simulate(120_000, k=0.01)))
        flat = self.autocorr(self.block_means(self.simulate(120_000, k=0.0)))
        self.assertGreater(clustered, 0.15, "volatility should cluster")
        self.assertLess(abs(flat), 0.1, "with clustering off, volatility has no memory")

    def test_clustering_does_not_make_any_direction_likelier(self):
        returns = self.simulate(200_000, seed=2)
        n = len(returns)
        mean = sum(returns) / n
        sd = math.sqrt(sum((r - mean) ** 2 for r in returns) / n)
        self.assertLess(abs(mean / (sd / math.sqrt(n))), 3.5, "the mean return must stay at zero")
        after_up = [b for a, b in zip(returns, returns[1:]) if a > 0]
        after_down = [b for a, b in zip(returns, returns[1:]) if a < 0]
        # volatility reacts to the size of a move, not its sign: the next move is no more likely up after an up move
        self.assertAlmostEqual(sum(after_up) / len(after_up), sum(after_down) / len(after_down),
                               delta=4 * sd / math.sqrt(len(after_up)))

    def test_the_multiplier_is_centred_on_one_in_quiet_markets(self):
        e, s = self.e, self.s
        s.volm = 1.0
        rng = random.Random(3)
        history = []
        for _ in range(60_000):
            r = self.sigma_tick * e._vol_multiplier(s) * rng.gauss(0, 1)
            e._update_volatility(s, r)
            history.append(s.volm)
        self.assertAlmostEqual(sum(history) / len(history), 1.0, delta=0.12)
        self.assertGreater(max(history), 1.15)
        self.assertLess(min(history), 0.85)

    def test_a_big_move_raises_volatility_and_it_decays_over_a_game_day_or_two(self):
        e, s = self.e, self.s
        s.volm = 1.0
        e._update_volatility(s, 40 * self.sigma_tick)
        self.assertGreater(s.volm, 1.25)
        for _ in range(3 * engine.MARKET_DAY_SECONDS):                 # ordinary noise afterwards
            e._update_volatility(s, 0.8 * e._vol_multiplier(s) * self.sigma_tick)
        self.assertLess(s.volm, 1.07)

    def test_the_multiplier_stays_within_bounds(self):
        e, s = self.e, self.s
        for _ in range(100):
            e._update_volatility(s, 500 * self.sigma_tick)
        self.assertLessEqual(s.volm, 3.0)
        for _ in range(200_000):
            e._update_volatility(s, 0.0)
        self.assertGreaterEqual(s.volm, 0.5)

    def test_zero_k_switches_clustering_off(self):
        e, s = self.e, self.s
        e.settings["vol_cluster_k"] = 0
        s.volm = 1.0
        e._update_volatility(s, 100 * self.sigma_tick)
        self.assertEqual(s.volm, 1.0)

    def test_the_multiplier_scales_the_noise(self):
        e, s = self.e, self.s
        spreads = {}
        for volm in (1.0, 2.0):
            s.volm = volm
            draws = []
            for _ in range(3000):
                e._pending = {}
                e._random_market_moves()
                draws.append(e._pending.get("NVXA", 0.0))
            mean = sum(draws) / len(draws)
            spreads[volm] = math.sqrt(sum((d - mean) ** 2 for d in draws) / len(draws))
        self.assertAlmostEqual(spreads[2.0] / spreads[1.0], 2.0, delta=0.25)

    def test_a_crisis_raises_market_wide_volatility_and_it_fades(self):
        e = self.e
        e.crisis_until = e.now + 5000
        for _ in range(600):
            e.now += 1
            e._mood_step()
        self.assertGreater(e.mkt_volm, 1.35)
        e.crisis_until = 0
        for _ in range(1200):
            e.now += 1
            e._mood_step()
        self.assertLess(e.mkt_volm, 1.1)

    def test_a_very_strong_event_lifts_the_daily_limit_for_a_while(self):
        e, s = self.e, self.s
        limit = min(0.15, e._daily_sigma(s) * (1.5 + 0.75 * min(abs(s.beta), 2.0)))
        s.fair = s.fair_open * math.exp(limit)
        normal = e._envelope_damping(s, 0.15)
        tpl = {"scope": "market", "betas": {"*": 1.0}, "index_bias": 1.0, "up": ["Test shock up"],
               "down": ["Test shock down"], "rumor": False}
        e._spawn_event(tpl, None, 1, "very strong", follow=False)
        self.assertGreater(s.boost_until, e.now)
        s.fair = s.fair_open * math.exp(limit)
        self.assertGreater(e._envelope_damping(s, 0.15), 0.9)
        self.assertLess(normal, 0.55)
        e.now += 601
        self.assertAlmostEqual(e._envelope_damping(s, 0.15), normal, places=9)

    def test_weaker_events_do_not_lift_the_limit(self):
        e, s = self.e, self.s
        tpl = {"scope": "market", "betas": {"*": 1.0}, "index_bias": 1.0, "up": ["Small shock up"],
               "down": ["Small shock down"], "rumor": False}
        e._spawn_event(tpl, None, 1, "weak", follow=False)
        self.assertEqual(s.boost_until, 0.0)

    def test_the_volatility_multiplier_is_not_sent_to_players(self):
        """It used to drive a VOLATILE badge; it also hinted at the market regime, so it is no longer public."""
        e = make_engine(71)
        e.stocks["NVXA"].volm = 1.6
        e._public()
        row = next(x for x in e.pub_stocks if x["ticker"] == "NVXA")
        self.assertNotIn("volm", row)
        self.assertNotIn("volm", e.pub_slow["NVXA"])
        self.assertNotIn("boost", row)                        # the BIG NEWS badge is gone too
        self.assertNotIn("boost_until", e.pub_slow["NVXA"])

    def test_volatility_state_survives_a_restart(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            random.seed(74)
            e = engine.Engine(state_file=path, bots=False)
            e.tick(now=e.now)
            e.stocks["NVXA"].volm = 1.7
            e.mkt_volm = 1.3
            e.save()
            f = engine.Engine(state_file=path, bots=False)
            self.assertAlmostEqual(f.stocks["NVXA"].volm, 1.7)
            self.assertAlmostEqual(f.mkt_volm, 1.3)


class SessionTests(unittest.TestCase):
    """Pre-market (00:00-00:05), the regular session (00:05-00:25) and after-hours (00:25-00:30): thin trading
    before and after, a burst and a jump at the open, and no direction in any of it."""

    def setUp(self):
        self.e = make_engine(72, premarket_seconds=300, aftermarket_seconds=300)
        quiet(self.e)
        self.day = engine.MARKET_DAY_SECONDS
        self.start = (int(self.e.now // self.day) + 1) * self.day     # the start of a game day (00:00)

    def at(self, phase):
        self.e.now = self.start + phase
        self.e._update_session()

    def test_the_phases_follow_the_clock(self):
        e = self.e
        for phase, expected in ((0, "pre"), (299, "pre"), (300, "open"), (1000, "open"), (1499, "open"),
                                (1500, "after"), (1799, "after")):
            self.assertEqual(e.market_phase(self.start + phase), expected, phase)
        # and the same every half hour, on the real clock
        self.assertEqual(e.market_phase(self.start + 5 * self.day + 100), "pre")
        self.assertEqual(e.market_phase(self.start + 5 * self.day + 400), "open")

    def test_the_session_info_for_the_page(self):
        e = self.e
        self.at(100)
        s = e.session()
        self.assertEqual((s["phase"], s["open"], s["next"], s["changes_in"]), ("pre", False, "open", 201))
        self.assertEqual((s["pre"], s["after"], s["cycle"]), (300, 300, 1800))
        self.at(400)
        s = e.session()
        self.assertEqual((s["phase"], s["open"], s["next"], s["changes_in"]), ("open", True, "after", 1101))
        self.at(1600)
        s = e.session()
        self.assertEqual((s["phase"], s["open"], s["next"], s["changes_in"]), ("after", False, "pre", 201))

    def test_zero_lengths_mean_no_sessions_at_all(self):
        e = self.e
        e.settings.update(premarket_seconds=0, aftermarket_seconds=0)
        for phase in (0, 100, 900, 1700):
            self.at(phase)
            self.assertEqual(e.market_phase(), "open")
            self.assertEqual(e._session_mult(), 1.0)
        self.assertIsNone(e.session()["changes_in"])
        self.assertTrue(e.session()["open"])

    def test_nothing_is_ever_refused_for_the_time_of_day(self):
        e = self.e
        p = join(e, "anytime")
        for phase, tk in ((100, "GOLD"), (400, "CLDR"), (1600, "NVXA")):
            self.at(phase)
            ok, msg = e.trade(p, tk, "buy", 0.1)
            self.assertTrue(ok, f"{phase}: {msg}")
        self.assertLess(abs(drift(e)), 1e-6)

    def test_noise_is_thin_outside_the_regular_session_and_busy_at_the_open(self):
        e = self.e
        mult = {}
        for phase in (10, 299, 300, 330, 600, 900, 1200, 1480, 1499, 1500, 1700):
            self.at(phase)
            mult[phase] = e._session_mult()
        self.assertEqual(mult[10], 0.35)
        self.assertEqual(mult[299], 0.35)
        self.assertEqual(mult[1500], 0.35)
        self.assertEqual(mult[1700], 0.35)
        self.assertGreater(mult[300], 2.0)                       # the burst at the open...
        self.assertGreater(mult[300], mult[330])
        self.assertGreater(mult[330], mult[600])                 # ...fades
        self.assertTrue(0.8 < mult[900] < 1.1, mult[900])        # a normal stretch in the middle
        self.assertGreater(mult[1499], mult[1200])               # and a smaller burst into the close
        self.assertLess(mult[1499], mult[300])

    def test_the_day_keeps_its_volatility(self):
        """Pre-market + regular session + after-hours + the opening jump add up to exactly one normal day of
        variance, so the stock's annual volatility is unchanged by the sessions."""
        e = self.e
        total = 0.0
        for phase in range(self.day):
            self.at(phase)
            total += e._session_mult() ** 2
        total += e._open_jump_ticks()
        self.assertAlmostEqual(total / self.day, 1.0, delta=0.005)

    def test_the_real_noise_scales_with_the_multiplier(self):
        e = self.e
        s = e.stocks["NVXA"]
        spread = {}
        for name, phase in (("pre", 100), ("mid", 900), ("open", 300)):
            self.at(phase)
            e._prev_phase = "open"                               # no opening jump while measuring plain noise
            draws = []
            for _ in range(1200):
                e._pending = {}
                e._random_market_moves()
                draws.append(e._pending["NVXA"])
            m = sum(draws) / len(draws)
            spread[name] = math.sqrt(sum((d - m) ** 2 for d in draws) / len(draws))
            self.assertLess(abs(m), 4 * spread[name] / math.sqrt(len(draws)), f"{name} noise has a direction")
        self.at(900)
        expected = 0.35 / e._session_mult()                      # thin noise relative to the middle of the session
        self.assertAlmostEqual(spread["pre"] / spread["mid"], expected, delta=0.07)
        self.assertGreater(spread["open"] / spread["mid"], 2.0)

    def test_one_opening_jump_per_cycle_and_none_without_sessions(self):
        e = self.e
        self.at(290)
        e.tick(now=self.start + 290)
        before = e.gaps_total
        for t in range(291, 400):
            e.tick(now=self.start + t)
        self.assertEqual(e.gaps_total, before + 1)
        for t in range(400, 1800 + 310):
            e.tick(now=self.start + t)
        self.assertEqual(e.gaps_total, before + 2)               # the next cycle's open
        flat = make_engine(75)
        quiet(flat)
        for t in range(1, 40):
            flat.tick(now=flat.now + 1)
        self.assertEqual(flat.gaps_total, 0)

    def test_the_opening_jump_is_zero_mean_and_the_right_size(self):
        e = self.e
        s = e.stocks["NVXA"]
        sigma_tick = e._daily_sigma(s) / math.sqrt(engine.MARKET_DAY_SECONDS)
        self.at(300)
        e._prev_phase = "pre"
        jumps = []
        for _ in range(1500):
            e._pending = {}
            e._random_market_moves()
            jumps.append(e._pending["NVXA"])
        m = sum(jumps) / len(jumps)
        sd = math.sqrt(sum((j - m) ** 2 for j in jumps) / len(jumps))
        self.assertLess(abs(m), 4 * sd / math.sqrt(len(jumps)), "the opening jump must have no direction")
        # about 90 seconds' worth of ordinary noise plus the first second's burst
        self.assertAlmostEqual((sd / sigma_tick) ** 2, 90 + e._session_mult() ** 2, delta=0.25 * 96)

    def test_the_pre_market_move_does_not_predict_the_opening_jump(self):
        """The jump is a fresh draw: the sign of what happened in pre-market says nothing about it."""
        e = self.e
        agree = trials = 0
        for _ in range(240):
            e._pending = {}
            self.at(100)
            pre = 0.0
            for _ in range(6):                                   # a few pre-market seconds
                e._pending = {}
                e._random_market_moves()
                pre += e._pending["NVXA"]
            self.at(300)
            e._prev_phase = "pre"
            e._pending = {}
            e._random_market_moves()
            jump = e._pending["NVXA"]
            trials += 1
            agree += (pre > 0) == (jump > 0)
        self.assertAlmostEqual(agree / trials, 0.5, delta=0.1)

    def test_news_keeps_coming_in_every_session(self):
        e = self.e
        e.settings.update(event_mean_seconds=4, issue_mean_seconds=4)
        e.next_event = e.now
        e.next_issue = e.now
        self.at(100)
        before = e.news_log[-1]["id"] if e.news_log else 0
        for _ in range(60):
            e.tick(now=e.now + 1)
        self.assertGreater(e.news_log[-1]["id"], before, "headlines keep coming in pre-market")

    def test_margin_calls_run_in_every_session(self):
        e = self.e
        p = join(e, "gapshort")
        self.at(600)
        e.trade(p, "HLXB", "sell", 1.0)
        self.at(1600)                                           # after-hours
        e.stocks["HLXB"].fair *= 8
        e.tick(now=e.now + 1)
        self.assertNotIn("HLXB", p.hold)
        self.assertTrue(p.notices)

    def test_dividends_take_effect_at_the_open(self):
        e = self.e
        s = e.stocks["OILX"]
        s.div = {"t": e.now - 1, "amt": 0.5}
        self.at(100)
        e.tick(now=e.now + 1)                                   # still pre-market
        self.assertIsNotNone(s.div)
        self.at(299)
        e.tick(now=e.now + 1)
        e.tick(now=e.now + 1)                                   # the open
        self.assertIsNone(s.div)

    def test_money_is_conserved_across_every_session(self):
        e = self.e
        p = join(e, "overnight1")
        self.at(1450)
        e.trade(p, "CLDR", "buy", 0.2)
        e.trade(p, "NVXA", "sell", 0.3)
        for _ in range(700):                                    # after-hours, then pre-market, then the open
            e.tick(now=e.now + 1)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_the_state_sent_to_players_describes_the_session(self):
        e = make_engine(73, premarket_seconds=300, aftermarket_seconds=300)
        p = join(e, "watcher1")
        e._public()
        market = e.state_for(p)["market"]
        for key in ("phase", "open", "next", "changes_in", "pre", "after", "cycle"):
            self.assertIn(key, market)
        self.assertIn(market["phase"], ("pre", "open", "after"))


if __name__ == "__main__":
    unittest.main()
