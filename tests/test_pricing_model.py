"""The pricing model (tools/pricing_model.py, ROADMAP M7): it reads the shop's passes from the game's settings, scales
with the number of sign-ups, earns nothing when nobody buys, and reports how much each assumption matters."""
import unittest

import _helpers  # noqa: F401  (puts tools/ on sys.path)
import pricing_model as pm


class PricingModelTests(unittest.TestCase):
    def test_it_uses_the_game_s_passes_and_prices(self):
        g = pm.game_settings()
        self.assertIn("pro_month", g["pro"])
        self.assertIn("expert_month", g["expert"])
        self.assertEqual(pm.plan_prices(g["pro"]), (g["pro"]["pro_month"][1], g["pro"]["pro_year"][1]))
        tot, rows = pm.run()
        self.assertEqual(len(rows), pm.ASSUMPTIONS["weeks"])
        self.assertGreater(tot["pro"], 0)
        self.assertGreater(tot["expert"], 0)
        self.assertGreater(tot["net"], 0)
        self.assertLess(tot["net"], tot["revenue"])                     # payment costs and refunds come off

    def test_it_scales_with_sign_ups_and_earns_nothing_when_nobody_pays(self):
        one = pm.run({"signups": 1000})[0]["net"]
        two = pm.run({"signups": 2000})[0]["net"]
        self.assertAlmostEqual(two, 2 * one, places=6)
        zero = pm.run({"pro_share": 0.0, "expert_share": 0.0})[0]
        self.assertEqual(zero["revenue"], 0.0)

    def test_retention_falls_and_the_sensitivity_covers_every_assumption(self):
        a = pm.ASSUMPTIONS
        self.assertGreater(pm.retention_at(a, 1), pm.retention_at(a, 4))
        self.assertAlmostEqual(pm.retention_at(a, 4), a["retention"]["4"])
        base, sens = pm.sensitivity()
        names = {k for k, lo, hi in sens}
        self.assertIn("retention (every point)", names)
        self.assertIn("expert_share", names)
        self.assertTrue(all(lo <= 0 <= hi or hi <= 0 <= lo for k, lo, hi in sens))   # half and more push opposite ways


if __name__ == "__main__":
    unittest.main()
