"""Slow checks, skipped unless you ask for them:  RUN_SLOW=1 python -m unittest tests.test_slow -v
(or  set RUN_SLOW=1  in PowerShell first).

- Stress: 20 clients for 15 seconds against an isolated server.

(The old many-seed edge checks, `edge.py` and `paired.py`, belonged to the zero-edge market and were removed on
2026-10-13; the new market is checked with `realism.py` and `chart_check.py`, see MARKET_REALISM.md.)
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


if __name__ == "__main__":
    unittest.main()
