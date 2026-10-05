"""Stocks hold no seed tokens. Every token is a player's cash, the house reserve or a fee, and a save from the older
version (which had seed "pool" tokens inside every stock) is converted on load without changing anyone's money."""
import json
import os
import random
import tempfile
import unittest

from _helpers import advance, drift, engine, join, make_engine


class NoPoolsTests(unittest.TestCase):
    def test_a_stock_holds_no_tokens_and_the_books_are_cash_plus_reserve_plus_fees(self):
        e = make_engine(3)
        self.assertFalse(any(hasattr(s, "T") for s in e.stocks.values()))
        p = join(e, "trader")
        e.trade(p, "CLDR", "buy", 0.5)
        e.trade(p, "NVXA", "sell", 0.2)
        self.assertAlmostEqual(e.total_tokens(), e.house + e.fees + p.cash, places=9)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_the_house_capital_is_only_the_starting_reserve_and_the_top_ups(self):
        e = make_engine(4)
        self.assertEqual(e.house_capital, e.house)                     # nothing else was ever put in
        self.assertNotIn("pool_tokens", e.house_stats())
        p = join(e, "trader")
        e.trade(p, "CLDR", "buy", 0.5)
        self.assertEqual(e.house_capital, e.minted - p.deposited)

    def test_a_new_listing_costs_the_house_nothing(self):
        random.seed(5)
        e = make_engine(5)
        reserve, minted, capital = e.house, e.minted, e.house_capital
        e.settings["moonshot_mean_seconds"] = 1
        before = set(e.stocks)
        for _ in range(3):
            e._list_moonshot(initial=False)
        self.assertGreater(len(set(e.stocks) - before), 0)
        self.assertEqual((e.house, e.minted, e.house_capital), (reserve, minted, capital))


class OldSaveWithPoolsTests(unittest.TestCase):
    """Build a save the way the old version wrote it (seed tokens `T` inside every stock) and load it."""

    def make_old_save(self, path):
        random.seed(12)
        e = engine.Engine(state_file=path)
        e.settings.update(premarket_seconds=0, aftermarket_seconds=0, signup_bonus=1000)
        e.tick(now=e.now)
        humans = [join(e, f"human{i}") for i in range(2)]
        for k in range(60):
            e.tick(now=e.now + 1)
        e.trade(humans[0], "CLDR", "buy", 0.4)
        e.trade(humans[1], "NVXA", "sell", 0.2)
        e.save()
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        pools = 0.0
        for v in data["stocks"].values():                              # the old format: every stock held its own tokens
            v["T"] = float(v["base"])
            pools += v["T"]
        data["minted"] += pools
        data["house_capital"] += pools
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return e, humans, pools

    def test_the_seed_tokens_are_retired_and_nobodys_money_changes(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            old, humans, pools = self.make_old_save(path)
            self.assertGreater(pools, 1000)
            fresh = engine.Engine(state_file=path)
            self.assertAlmostEqual(fresh._retired_pools, pools, places=6)
            self.assertAlmostEqual(fresh.house, old.house, places=6)           # the reserve is exactly what it was
            self.assertAlmostEqual(fresh.fees, old.fees, places=6)
            self.assertAlmostEqual(fresh.minted, old.minted, places=6)         # (the pools were added to the saved figure above)
            self.assertAlmostEqual(fresh.house_capital, old.house_capital, places=6)
            for p in humans:
                q = fresh.by_token[p.token]
                self.assertEqual((q.cash, q.hold, q.deposited), (p.cash, p.hold, p.deposited))
            self.assertLess(abs(drift(fresh)), 1e-6)

    def test_the_clean_save_has_no_seed_tokens_and_loads_the_same_again(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            self.make_old_save(path)
            first = engine.Engine(state_file=path)
            with open(path, encoding="utf-8") as fh:
                saved = json.load(fh)
            self.assertTrue(all("T" not in v for v in saved["stocks"].values()))
            second = engine.Engine(state_file=path)
            self.assertEqual(second._retired_pools, 0.0)
            self.assertAlmostEqual(second.house, first.house, places=6)
            self.assertAlmostEqual(second.minted, first.minted, places=6)
            self.assertAlmostEqual(second.house_capital, first.house_capital, places=6)
            self.assertLess(abs(drift(second)), 1e-6)

    def test_a_crash_before_the_first_save_still_gives_the_same_result(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            self.make_old_save(path)
            with open(path, "rb") as fh:
                raw = fh.read()
            a = engine.Engine(state_file=path)
            with open(path, "wb") as fh:                              # (as if the clean save had never been written)
                fh.write(raw)
            b = engine.Engine(state_file=path)
            self.assertAlmostEqual(a.minted, b.minted, places=6)
            self.assertAlmostEqual(a.house_capital, b.house_capital, places=6)
            self.assertLess(abs(drift(b)), 1e-6)

    def test_the_game_keeps_running_and_balancing_after_the_conversion(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            self.make_old_save(path)
            e = engine.Engine(state_file=path)
            p = next(iter(e.players.values()))
            advance(e, 200)
            e.trade(p, "GOLD", "buy", 0.3)
            advance(e, 100)
            self.assertLess(abs(drift(e)), 1e-6)


if __name__ == "__main__":
    unittest.main()
