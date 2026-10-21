"""Phase 2 of the price model (ROADMAP TA-A2 to TA-A9): levels from the daily chart and gaps, volume that tells the
story, candles that mean something, intraday legs inside a trend's legs, chart patterns the model forms on purpose, and
patterns.py, which finds patterns the way a trader would. The market-wide checks (rates, outcomes, no free money) are
in tools/realism.py; these tests pin the mechanics."""
import math
import random
import types
import unittest

import _helpers  # noqa: F401  (puts the game on sys.path)
import market_model as mm
import patterns

DAY = mm.DAY


def listing(tk="AAA", price=100.0, vol=0.3, beta=1.0, sector="tech"):
    return types.SimpleNamespace(ticker=tk, price=price, vol=vol, beta=beta, sector=sector, asset_type="equity", moonshot=False)


def fixed_rng(u=0.0):
    return types.SimpleNamespace(random=lambda: u, uniform=lambda a, b: a, gauss=lambda m, s: 0.0, choices=random.choices)


class DailyLevelTests(unittest.TestCase):
    def test_game_days_and_their_levels_follow_the_regular_session(self):
        m = mm.MarketModel({}, rng=random.Random(1), now=0.0)
        x = listing()
        sw = m.swing(x, 0.0)
        path = {0: (100, 104, 98, 101), 1: (103, 106, 100, 105)}
        for d, (o, h, l, c) in path.items():
            for t, px in ((d * DAY + 310, o), (d * DAY + 600, h), (d * DAY + 900, l), (d * DAY + 1490, c)):
                m._day_step(sw, t, px, True)
            m._day_step(sw, d * DAY + 1600, c, False)          # after-hours: the session is over
        self.assertEqual([b[1:] for b in sw.days], [[100, 104, 98, 101], [103, 106, 100, 105]])
        kinds = {k: p for p, s, k in sw.dlev}
        self.assertEqual((kinds["pdh"], kinds["pdl"], kinds["pdc"]), (106, 100, 105))
        self.assertNotIn("dop", kinds)                          # (no session under way)
        m._day_step(sw, 2 * DAY + 310, 107, True)               # the next open
        self.assertEqual({k: p for p, s, k in sw.dlev}["dop"], 107)

    def test_averages_and_the_52_week_range_appear_with_enough_history(self):
        m = mm.MarketModel({}, rng=random.Random(1), now=0.0)
        sw = mm.Swing(0.0, 100.0)
        for d in range(220):
            c = 100 + 10 * math.sin(d / 9)
            sw.days.append([d * DAY, c, c + 1, c - 1, c])
        m._daily_levels(sw)
        kinds = {k: p for p, s, k in sw.dlev}
        for k in ("ma20", "ma50", "ma200", "hi52", "lo52"):
            self.assertIn(k, kinds)
        closes = [b[4] for b in sw.days]
        self.assertAlmostEqual(kinds["ma50"], sum(closes[-50:]) / 50)
        self.assertAlmostEqual(kinds["hi52"], max(b[2] for b in sw.days))
        strength = {k: s for p, s, k in sw.dlev}
        self.assertGreater(strength["ma200"], strength["ma20"])            # each kind its own strength
        self.assertGreater(strength["hi52"], strength["pdc"])

    def test_a_daily_level_on_a_swing_level_adds_up(self):
        m = mm.MarketModel({}, rng=random.Random(1), now=0.0)
        sw = mm.Swing(0.0, 100.0)
        for i, p in enumerate([100, 101, 102, 103, 104, 105, 104, 103, 102, 101, 100, 99, 98, 99, 100, 101, 102]):
            sw.bars.append([i * mm.BAR, p + 0.05, p - 0.05, p])
        sw.dlev = [(105.02, 2.0, "pdh"), (93.0, 1.0, "pdc")]
        m._find_levels(sw, 101.0)
        top = next(lv for lv in sw.levels if abs(lv[0] - 105) < 0.3)
        self.assertEqual(top[1], 3)                             # one touch plus the previous day's high
        self.assertIn("pdh", top[3])
        self.assertTrue(any(lv[3] == "pdc" and lv[0] == 93.0 for lv in sw.levels))


class LevelReactionTests(unittest.TestCase):
    def setUp(self):
        self.m = mm.MarketModel({}, rng=random.Random(2), now=0.0)
        self.x = listing()
        self.sw = self.m.swing(self.x, 0.0)
        self.sw.until = 1e18

    def test_levels_are_tested_only_in_the_regular_session(self):
        sw, x = self.sw, self.x
        sw.levels = [[99.9, 3, True, "swing"]]
        r, _, _ = self.m._level_step(x, sw, 0.0, 1.0, math.log(100.0), 0.016, regular=False)
        self.assertIsNone(sw.test)
        self.assertEqual(r, 0.0)
        self.m._level_step(x, sw, 0.0, 1.0, math.log(100.0), 0.016, regular=True)
        self.assertIsNotNone(sw.test)
        self.m._level_step(x, sw, 1.0, 1.0, math.log(100.0), 0.016, regular=False)   # the session ended before it was decided
        self.assertIsNone(sw.test)

    def test_a_reaction_keeps_the_size_it_had_when_the_test_began(self):
        sw, x = self.sw, self.x
        sw.levels = [[99.9, 3, True, "swing"]]
        self.m.rng = fixed_rng(0.0)                              # it holds
        r1, _, _ = self.m._level_step(x, sw, 0.0, 1.0, math.log(100.0), 0.016)
        r2, _, _ = self.m._level_step(x, sw, 1.0, 1.0, math.log(100.0), 0.05)  # volatility tripled since
        self.assertAlmostEqual(r1, r2)

    def test_a_holding_level_pushes_back_harder_once_the_price_is_through_it(self):
        sw, x = self.sw, self.x
        sw.levels = [[99.9, 3, True, "swing"]]
        self.m.rng = fixed_rng(0.0)
        near, _, _ = self.m._level_step(x, sw, 0.0, 1.0, math.log(100.0), 0.016)
        through, _, _ = self.m._level_step(x, sw, 1.0, 1.0, math.log(99.6), 0.016)     # 3/4 of a band through it
        self.assertGreater(through, 2 * near)                   # the wick of a rejection

    def test_a_break_that_will_fail_comes_on_less_volume(self):
        vols = {}
        for false in (False, True):
            sw = mm.Swing(0.0, 100.0)
            sw.test = {"level": 99.9, "side": 1, "outcome": "break", "until": 900, "false": false, "fail_after": 300,
                       "strength": 2, "round": False, "start": 0.0, "kind": "swing", "sig": 0.016, "crossed": 0.0}
            _, _, vols[false] = self.m._level_step(self.x, sw, 10.0, 1.0, math.log(99.8), 0.016)
        self.assertGreater(vols[False], vols[True])

    def test_no_new_test_straight_after_another(self):
        sw, x = self.sw, self.x
        sw.levels = [[99.9, 3, True, "swing"], [100.5, 3, True, "swing"]]
        self.m._start_test(x, sw, 0.0, math.log(100.0), 0.004, 0.016)
        sw.test = None
        self.assertIsNone(self.m._start_test(x, sw, 100.0, math.log(100.45), 0.004, 0.016))
        self.assertIsNotNone(self.m._start_test(x, sw, 700.0, math.log(100.45), 0.004, 0.016))


class TrendAndCandleTests(unittest.TestCase):
    def setUp(self):
        self.m = mm.MarketModel({}, rng=random.Random(3), now=0.0)
        self.x = listing()
        self.sw = self.m.swing(self.x, 0.0)

    def test_the_last_push_of_a_trend_is_weaker_and_on_less_volume(self):
        sw = self.sw
        sw.mode, sw.dir, sw.until, sw.leg, sw.sub = "trend", 1, 10 * DAY, "impulse", [1, 0.0, 1e9, 0.0]
        sw.leg_until = 5 * DAY
        r_mid, _, v_mid = self.m._mode_step(self.x, sw, 1.0, 1.0, math.log(100), 0.016, 0.0)
        sw.leg_until = 11 * DAY                                  # this impulse runs past the trend's end: the last one
        r_last, _, v_last = self.m._mode_step(self.x, sw, 1.0, 1.0, math.log(100), 0.016, 0.0)
        self.assertLess(r_last, r_mid)
        self.assertLess(v_last, v_mid)

    def test_a_trend_may_end_in_a_climax_and_a_reversal_turns_with_a_burst(self):
        sw = self.sw
        self.m.p.update(climax_chance=1.0, patterns=0)
        self.m.rng = types.SimpleNamespace(random=lambda: 0.95, uniform=lambda a, b: a, gauss=lambda m_, s: 0.0)
        sw.mode, sw.dir = "trend", 1
        self.m._next_mode(self.x, sw, 100.0, math.log(100), 0.0, 0.016)
        kinds = [(b[0], b[4], b[5]) for b in sw.bursts]
        self.assertEqual(sw.dir, -1)                              # a reversal (0.95 >= 0.8)
        self.assertEqual(kinds[0], (1, self.m.p["climax_noise"], self.m.p["climax_volume"]))   # the climax, the old way
        self.assertEqual(kinds[1][0], -1)                         # then the turn
        self.assertGreaterEqual(sw.bursts[1][1], sw.bursts[0][2])  # (after the climax)

    def test_the_end_of_a_range_is_quieter(self):
        sw = self.sw
        sw.mode, sw.center, sw.mode_start, sw.until = "range", math.log(100), 0.0, 10 * DAY
        _, n_early, v_early = self.m._mode_step(self.x, sw, 1.0 * DAY, 1.0, math.log(100), 0.016, 0.0)
        _, n_late, v_late = self.m._mode_step(self.x, sw, 9.5 * DAY, 1.0, math.log(100), 0.016, 0.0)
        self.assertLess(n_late, n_early)
        self.assertLess(v_late, v_early)

    def test_intraday_legs_alternate_and_add_no_drift(self):
        sw = self.sw
        dirs, total = [], 0.0
        for t in range(0, 40 * DAY, 10):
            r = self.m._subleg(sw, float(t), 10.0, 0.016, 1.0)
            total += r
            if not dirs or dirs[-1] != sw.sub[0]:
                dirs.append(sw.sub[0])
        self.assertTrue(all(a == -b for a, b in zip(dirs, dirs[1:])))
        self.assertGreater(len(dirs), 100)
        self.assertLess(abs(total), 0.016 * 3)                   # (a few legs' worth at most, not a trend)


class PatternFormationTests(unittest.TestCase):
    def run_pattern(self, kind, ending, vol=0.3):
        """Step a quiet listing (no noise of its own) through one pattern with the given ending."""
        m = mm.MarketModel({"price_model": {"daily_levels": 0}}, rng=random.Random(5), now=0.0)
        x = listing(vol=vol)
        sw = m.swing(x, 0.0)
        m._start_pattern(x, sw, 0.0, math.log(100.0), 0.016, kind)
        spec = mm.PATTERNS[kind]
        w, b = spec["odds"]
        u = {"works": 0.0, "busted": w + 0.001, "fail": 0.999}[ending]
        rng = m.rng
        m.rng = types.SimpleNamespace(random=lambda: u, uniform=rng.uniform, gauss=rng.gauss, choices=rng.choices)
        path, t = [], 0.0
        while sw.mode == "pattern" and t < 200 * DAY:
            r, _, _ = m._mode_step(x, sw, t, 60.0, math.log(x.price), 0.016, 0.0)
            x.price *= math.exp(r)
            path.append(math.log(x.price / 100.0))
            t += 60.0
        return m, sw, spec, path

    def test_every_pattern_ends_its_way_and_hands_over_to_a_trend(self):
        for kind in mm.PATTERNS:
            for ending in ("works", "busted", "fail"):
                m, sw, spec, path = self.run_pattern(kind, ending)
                self.assertEqual(sw.mode, "trend", kind)
                self.assertIsNone(sw.pat)
                self.assertEqual(sw.dir, spec["dir"] * (1 if ending == "works" else -1), (kind, ending))
                # the price ends near the ending's last level (in units of the pattern's size)
                usual = 0.3 / math.sqrt(365)
                S = m.p["pattern_size"] * spec["size"] * usual
                last = spec[ending][-1][0]
                self.assertLess(abs(path[-1] - last * S), 0.35 * S + 0.002, (kind, ending, path[-1] / S, last))

    def test_a_double_top_has_two_tops_and_a_dip_between(self):
        m, sw, spec, path = self.run_pattern("double_top", "works")
        S = m.p["pattern_size"] * spec["size"] * 0.3 / math.sqrt(365)
        n = len(path)
        first_dip = min(path[: n // 3])
        self.assertLess(first_dip, -0.6 * S)
        second_top = max(path[n // 4: 2 * n // 3])
        self.assertGreater(second_top, -0.35 * S)               # back up to about the first top
        self.assertLess(path[-1], -1.6 * S)                     # and it broke down

    def test_patterns_are_mirrored_and_the_odds_leave_a_fair_share_of_failures(self):
        for a, b in (("double_top", "double_bottom"), ("bull_flag", "bear_flag"), ("rising_wedge", "falling_wedge")):
            self.assertEqual(mm.PATTERNS[a]["dir"], -mm.PATTERNS[b]["dir"])
            self.assertEqual([lv[0] for lv in mm.PATTERNS[a]["legs"]], [-lv[0] for lv in mm.PATTERNS[b]["legs"]])
        for kind, spec in mm.PATTERNS.items():
            works, busted = spec["odds"]
            self.assertTrue(0.3 <= works <= 0.5 and busted >= 0.15, kind)   # never a sure thing

    def test_a_pattern_survives_a_save(self):
        m = mm.MarketModel({}, rng=random.Random(6), now=0.0)
        x = listing()
        sw = m.swing(x, 0.0)
        m._start_pattern(x, sw, 0.0, math.log(100.0), 0.016, "head_shoulders")
        m._mode_step(x, sw, 0.0, 1.0, math.log(100.0), 0.016, 0.0)
        import json
        d = json.loads(json.dumps(m.dump()))
        m2 = mm.MarketModel({}, rng=random.Random(6), now=0.0)
        m2.load(d, 10.0, {"AAA": 100.0})
        sw2 = m2.swings["AAA"]
        self.assertEqual((sw2.mode, sw2.pat["kind"]), ("pattern", "head_shoulders"))
        m2._mode_step(x, sw2, 20.0, 1.0, math.log(100.0), 0.016, 0.0)      # and it carries on


def candles(path, wick=0.002):
    return [[x, x * (1 + wick), x * (1 - wick), x] for x in path]


class DetectorTests(unittest.TestCase):
    def test_the_zigzag_confirms_each_swing_only_after_the_turn(self):
        pv = patterns.zigzag(candles([100, 104, 108, 110, 107, 103, 100, 104, 109]), 0.04)
        self.assertEqual([(i, s) for i, _, s, _ in pv], [(0, -1), (3, 1), (6, -1)])
        for i, _, s, conf in pv:
            self.assertGreater(conf, i)                          # known later than it happened

    def test_textbook_shapes(self):
        cases = {
            "double_top": [90, 95, 100, 105, 110, 108, 105, 102, 104, 107, 109.5, 107, 104, 101, 98, 96, 94, 92, 91, 90],
            "head_shoulders": [90, 96, 102, 106, 104, 101, 100, 104, 108, 112, 109, 105, 101, 100.5, 103, 106, 103, 99,
                               96, 93, 91, 89, 88],
        }
        for kind, path in cases.items():
            found = patterns.find(candles(path), 0.04)
            hit = [p for p in found if p["kind"] == kind]
            self.assertTrue(hit, (kind, found))
            o = patterns.outcome(candles(path), hit[0], wait=6, hold=10)
            self.assertTrue(o["completed"] and o["worked"], o)
            self.assertLess(hit[0]["target"], hit[0]["trigger"])      # both point down

    def test_a_pattern_that_breaks_the_other_way_has_failed(self):
        path = [90, 95, 100, 105, 110, 108, 105, 102, 104, 107, 109.5, 107, 104.5, 107, 110, 113, 116]
        hit = [p for p in patterns.find(candles(path), 0.04) if p["kind"] == "double_top"]
        self.assertTrue(hit)
        o = patterns.outcome(candles(path), hit[0], wait=6, hold=10)
        self.assertFalse(o["completed"])
        self.assertTrue(o["broke_other_way"])

    def test_find_all_does_not_count_one_pattern_twice(self):
        path = [90, 95, 100, 105, 110, 108, 105, 102, 104, 107, 109.5, 107, 104, 101, 98, 96, 94, 92, 91, 90]
        both = patterns.find_all(candles(path), [0.04, 0.045])
        kinds = [(p["kind"], p["at"]) for p in both]
        self.assertEqual(len(kinds), len(set(k for k, _ in kinds)))


class RealismToolTests(unittest.TestCase):
    def test_the_realism_check_runs_and_reports_structure_and_patterns(self):
        import realism
        res = realism.simulate(0.06, 4, 909)
        st = realism.structure(res)
        for key in ("break_volume", "climax", "leg_volume", "wicks", "engulfing", "squeeze", "agree", "divergence"):
            self.assertIn(key, st)
        found, made = realism.pattern_stats(res)
        self.assertIsInstance(found, dict)
        self.assertTrue(res["trace"])                                  # the model said what it did
        self.assertTrue(all(len(d) == 5 for ds in res["days"].values() for d in ds))


if __name__ == "__main__":
    unittest.main()
