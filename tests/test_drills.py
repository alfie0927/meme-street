"""Chart tests (drills.py): every kind finds moments on real-shaped charts, the questions are well formed, the answers
are read from the candles that follow, and the two-outcome kinds come out about half and half."""
import collections
import math
import random
import unittest

import _helpers  # noqa: F401  (puts the game on the path)
import daily
import drills

CHARTS = [daily.make_chart(s * 7919)["candles"] for s in range(1, 13)]     # the price model's own charts


class DrillTests(unittest.TestCase):
    def found(self, kind, n=60):
        out = []
        for s in range(n):
            t = drills.make(kind, CHARTS[s % len(CHARTS)], random.Random(s))
            if t:
                out.append((t, CHARTS[s % len(CHARTS)]))
        return out

    def test_every_kind_is_found_and_well_formed(self):
        for kind in drills.KINDS:
            got = self.found(kind)
            self.assertGreater(len(got), 20, kind)
            for t, cs in got:
                self.assertEqual(t["kind"], kind)
                self.assertTrue(t["q"] and t["result"] and t["explain"], kind)
                self.assertTrue(0 <= t["answer"] < len(t["options"]), kind)
                self.assertEqual(len(set(t["options"])), len(t["options"]), kind)
                self.assertTrue(drills.LOOK <= t["upto"] < len(cs) - 1, kind)
                for x in t["lines"]:
                    self.assertTrue(x["price"] > 0 and math.isfinite(x["price"]) and 0 <= x["from"] <= t["upto"], kind)
                    self.assertIn(x["tone"], ("level", "stop", "target", "entry", "trigger"))
                for m in t["marks"]:
                    self.assertTrue(0 <= m["i"] < len(cs), kind)
                    self.assertTrue(m["after"] or m["i"] <= t["upto"], kind)    # nothing from the future before the answer

    def test_two_outcome_kinds_are_about_half_and_half(self):
        for kind in ("level", "breakout", "next"):
            n = collections.Counter(t["answer"] for t, _ in self.found(kind, 120))
            share = n[0] / sum(n.values())
            self.assertTrue(0.3 < share < 0.7, (kind, n))

    def test_a_level_answer_is_what_the_closes_did(self):
        for t, cs in self.found("level"):
            lv = t["lines"][0]["price"]
            side = 1 if t["lines"][0]["label"] == "Support" else -1
            after = [(c[3] - lv) * side for c in cs[t["upto"] + 1:t["upto"] + drills.AFTER]]
            if t["answer"] == 0:                                   # held: the price got away on its own side
                self.assertGreater(max(after), 0)
            else:                                                  # broke: it closed through and did not come back
                self.assertLess(min(after), 0)
                self.assertLess(after[-1], 0)

    def test_the_reward_to_risk_answer_matches_the_lines(self):
        for t, _ in self.found("rr"):
            p = {x["label"]: x["price"] for x in t["lines"]}
            ratio = abs(p["Take-profit"] - p["Entry"]) / abs(p["Entry"] - p["Stop-loss"])
            self.assertAlmostEqual(ratio, [1.0, 1.5, 2.0, 3.0][t["answer"]], places=6)

    def test_a_candle_answer_is_that_candles_shape(self):
        for t, cs in self.found("candle"):
            k = drills.candle_kind(cs, t["upto"], drills.atr_series(cs))
            self.assertEqual(t["options"][t["answer"]], drills.CANDLES[k])

    def test_too_few_candles_or_bad_ones_give_nothing(self):
        self.assertIsNone(drills.make("level", CHARTS[0][:50], random.Random(1)))
        bad = [list(c) for c in CHARTS[0]]
        bad[10][2] = 0.0
        self.assertIsNone(drills.make("trend", bad, random.Random(1)))
        self.assertIsNone(drills.make("nope", CHARTS[0], random.Random(1)))


if __name__ == "__main__":
    unittest.main()
