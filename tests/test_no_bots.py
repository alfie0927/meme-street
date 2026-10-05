"""There are no bots. A save from an older version that has house-funded bots loads cleanly: the bots are settled and
removed, every token is accounted for, and the human players are untouched."""
import json
import os
import random
import tempfile
import unittest

from _helpers import advance, drift, engine, join, make_engine


class NoBotsTests(unittest.TestCase):
    def test_a_new_game_has_no_players_at_all_and_none_appear(self):
        random.seed(3)
        e = engine.Engine(state_file=None)
        self.assertEqual(e.players, {})
        for _ in range(600):
            e.tick(now=e.now + 1)
        self.assertEqual(e.players, {})
        self.assertFalse(hasattr(e, "_bots"))
        self.assertFalse(hasattr(e, "_add_bots"))

    def test_the_old_bot_settings_in_a_content_pack_do_nothing(self):
        e = make_engine(4, bots=8, bot_cash=10000, bot_action_probability=1.0)
        advance(e, 120)
        self.assertEqual(e.players, {})

    def test_a_player_has_no_bot_flag_and_the_boards_and_stats_have_no_bot_fields(self):
        e = make_engine(5)
        p = join(e, "human")
        self.assertFalse(hasattr(p, "bot"))
        e.trade(p, "CLDR", "buy", 0.2)
        e._board()
        for row in e.board:
            self.assertNotIn("bot", row)
        self.assertTrue(all("bot" not in r for r in e.board_view()))
        boards = e.boards_for(p)
        self.assertTrue(all("bot" not in r for r in boards["season"] + boards["pnl"]))
        self.assertNotIn("bot", e.public_profile("human", p))
        stats = e.house_stats()
        self.assertNotIn("bots_pnl", stats)
        self.assertAlmostEqual(stats["liquidity_pnl"], stats["house_pnl"] - stats["fees"])
        self.assertNotIn("bots", e.admin_overview())
        e._series_t = 0.0
        e._sample_series()
        self.assertNotIn("bots_pnl", e.series[-1])

    def test_names_that_look_like_bots_are_ordinary_names_now(self):
        e = make_engine(6)
        p, err = e.join("bot_mine")
        self.assertIsNotNone(p, err)


class OldSaveWithBotsTests(unittest.TestCase):
    """Build a save the way the old version did (house-funded bots that trade) and load it."""

    def make_old_save(self, path, with_ledger=False):
        random.seed(11)
        e = engine.Engine(state_file=path)
        e.settings.update(premarket_seconds=0, aftermarket_seconds=0, signup_bonus=1000)
        e.tick(now=e.now)
        humans = [join(e, f"human{i}") for i in range(2)]
        for i in range(4):                                         # what `_add_bots` used to do
            b = engine.Player(f"bot_old_{i}")
            e._register(b)
            b.cash = b.deposited = b.season_base = 10000.0
            e._mint_house(10000.0)
        bots = [p for p in e.players.values() if p.name.startswith("bot_old_")]
        for k in range(120):
            e.tick(now=e.now + 1)
            if k % 9 == 0:
                for p in bots:
                    tk = random.choice(["CLDR", "NVXA", "OILX", "GOLD"])
                    e.trade(p, tk, random.choice(["buy", "buy", "sell"]), random.choice([0.1, 0.3]))
        e.trade(humans[0], "CLDR", "buy", 0.4)
        e.trade(humans[1], "NVXA", "sell", 0.2)
        self.assertTrue(any(p.hold for p in bots))
        e.save()
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for x in data["players"]:                                  # the old save format flagged bots
            x["bot"] = x["name"].startswith("bot_old_")
            x["strategy"] = "random" if x["bot"] else None
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return e, humans, bots

    def test_the_bots_are_removed_the_books_balance_and_the_humans_are_untouched(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            old, humans, bots = self.make_old_save(path)
            before = {p.name: (p.cash, dict(p.hold), p.deposited) for p in humans}
            bot_cash = sum(b.cash for b in bots)
            house_before = old.house
            fresh = engine.Engine(state_file=path)
            self.assertEqual({p.name for p in fresh.players.values()}, {"human0", "human1"})
            self.assertLess(abs(drift(fresh)), 1e-6)
            for p in fresh.players.values():
                self.assertEqual(before[p.name][0], p.cash)
                self.assertEqual(before[p.name][1], p.hold)
                self.assertEqual(before[p.name][2], p.deposited)
            # The bots' cash went back to the house reserve. (Their positions are closed at the market price: the house pays
            # each one out and takes it straight back, so the reserve moves by the cash only. What the bots had bought was
            # already in the reserve, and the house's debt to them for those positions simply ends.)
            self.assertAlmostEqual(fresh.house - house_before, bot_cash, places=6)
            self.assertEqual(fresh.house_capital, old.house_capital)           # (they were funded by the house in the first place)
            self.assertEqual(fresh._retired_bots, 4)
            self.assertEqual(len(fresh.by_token), 2)

    def test_the_cleaned_save_is_written_at_once_and_loads_the_same_again(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            self.make_old_save(path)
            first = engine.Engine(state_file=path)
            with open(path, encoding="utf-8") as fh:
                saved = json.load(fh)
            self.assertEqual({x["name"] for x in saved["players"]}, {"human0", "human1"})
            self.assertTrue(all("bot" not in x and "strategy" not in x for x in saved["players"]))
            second = engine.Engine(state_file=path)
            self.assertEqual(second._retired_bots, 0)
            self.assertAlmostEqual(second.house, first.house, places=6)
            self.assertLess(abs(drift(second)), 1e-6)

    def test_the_bots_are_gone_from_the_boards_and_the_world_keeps_running(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            self.make_old_save(path)
            e = engine.Engine(state_file=path)
            e.tick(now=e.now + 1)
            e._board()
            self.assertTrue(all(not r["name"].startswith("bot_") for r in e.board))
            self.assertTrue(all(not r["name"].startswith("bot_") for r in e.boards["pnl"]))
            advance(e, 200)
            self.assertLess(abs(drift(e)), 1e-6)

    def test_a_crash_before_the_first_save_still_gives_a_clean_result(self):
        """The retirement writes nothing to the ledger, so loading the same old snapshot again retires the bots again,
        once, instead of applying it twice."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            self.make_old_save(path)
            with open(path, "rb") as fh:
                raw = fh.read()
            a = engine.Engine(state_file=path)
            with open(path, "wb") as fh:                          # (as if the clean save had never been written)
                fh.write(raw)
            b = engine.Engine(state_file=path)
            self.assertAlmostEqual(a.house, b.house, places=6)
            self.assertLess(abs(drift(b)), 1e-6)


if __name__ == "__main__":
    unittest.main()
