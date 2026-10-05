"""Slow checks, skipped unless you ask for them:  RUN_SLOW=1 python -m unittest tests.test_slow -v
(or  set RUN_SLOW=1  in PowerShell first).

- Stress: 20 clients for 15 seconds against an isolated server.
- Edge: a small many-seed run of the strategy simulator. Every strategy must lose to fees; none may show a
  clearly positive mean. It uses a strict threshold (t > 3) because 12 seeds are noisy; the proper check is
  `python edge.py 40 2 <fresh first seed>` (about 7 minutes).
"""
import os
import unittest

import _helpers  # noqa: F401  (puts the project on sys.path)

SLOW = os.environ.get("RUN_SLOW") == "1"


@unittest.skipUnless(SLOW, "set RUN_SLOW=1 to run slow checks")
class SlowChecks(unittest.TestCase):
    def test_stress(self):
        import stress
        ok, summary = stress.run(clients=20, seconds=15, verbose=False)
        self.assertTrue(ok, summary)
        self.assertGreater(summary["tick"], 10)               # the per-second updates kept flowing
        self.assertGreater(summary["init"], 20)               # and clients (re)connected and got a full picture

    def test_no_strategy_has_an_edge(self):
        import edge
        rows, bad = edge.check(seeds=12, hours=1, first=7000, quiet=True)
        by = {name: (mean, t) for name, mean, se, t, flag in rows}
        for name, (mean, t) in by.items():
            self.assertFalse(mean > 0 and t > 3, f"{name} earned {mean:+.2%} (t {t:+.1f}): an edge for players")
        self.assertFalse(bad and any(t > 3 for _, t in by.values()))

    def test_the_daily_limit_does_not_pay_dip_buyers(self):
        """Paired on the same seeds: switching the daily limit off must not make the dip-buying `value` strategy
        significantly worse. Before the soft limit it did (-2.7%, t -3.2): the hard clamp made dips bounce."""
        import paired
        rows = paired.compare([("base", {}), ("no_limit", {"daily_move_cap": 0})], ["value"], seeds=24, hours=2,
                              first=7300)
        _, _, _, dmean, se, t = next(r for r in rows if r[0] == "no_limit")
        self.assertFalse(dmean < 0 and t < -3, f"the daily limit pays dip-buyers again: {dmean:+.2%} (t {t:+.1f})")

    def test_edge_with_fast_earnings_covers_the_report_path(self):
        """Quarter shortened to 2 game days so every stock reports several times during the run."""
        import edge
        rows, _ = edge.check(seeds=8, hours=1, first=7100, settings={"earnings_quarter_days": 2}, quiet=True)
        for name, mean, se, t, flag in rows:
            self.assertFalse(mean > 0 and t > 3, f"{name} earned {mean:+.2%} (t {t:+.1f}) with fast earnings")


if __name__ == "__main__":
    unittest.main()
