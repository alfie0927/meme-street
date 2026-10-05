"""Starting the game over: Day 1 again, everyone on the starting balance, the market and the accounts untouched, the
money still adding up, and the old game backed up before anything is cleared."""
import json
import os
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from _helpers import ROOT, IsolatedServer, advance, drift, engine, free_port, join, make_engine
from test_server import Client, http


BONUS = 10000.0


def played(seed=1):
    """A game that has been going for a while: trades, a short, an order, medals, a contest entry, a second day."""
    e = make_engine(seed, signup_bonus=BONUS, bot_cash=BONUS)
    e._add_bots(4)
    a, b = join(e, "alpha"), join(e, "bravo")
    e.trade(a, "CLDR", "buy", 0.5)
    e.now += 2
    e.trade(a, "OILX", "sell", 0.3)
    e.now += 2
    e.trade(b, "NVXA", "buy", 1.0)
    e.place_order(a, "CLDR", "stop_loss", e.stocks["CLDR"].price * 0.5)
    a.badges.append({"tournament": "Daily Marathon", "place": 1, "t": e.now, "ret": 0.1})
    a.following = ["bravo"]
    a.public = True
    a.strikes = 2
    e._social_t = 0
    e._social_tick()
    e.tournament_join(a, next(iter(t["id"] for t in e.tournaments)))
    advance(e, 200)
    e.season_no = 19
    e.history = [{"season": 18, "top": [("alpha", 5.0)]}]
    return e, a, b


class ResetTests(unittest.TestCase):
    def setUp(self):
        self.e, self.a, self.b = played()
        self.prices = {k: s.price for k, s in self.e.stocks.items()}
        self.e.reset_to_day_one()

    def test_it_is_day_one_with_a_clean_history_and_a_news_line(self):
        e = self.e
        self.assertEqual(e.season_no, 1)
        self.assertEqual(e.history, [])
        self.assertGreater(e.season_end, e.now)
        self.assertTrue(any("DAY 1 BEGINS" in n["text"] for n in e.news_log))
        self.assertFalse(any("SEASON" in n["text"] for n in list(e.news_log)[-3:]))

    def test_everyone_people_and_bots_is_on_the_starting_balance_with_nothing_held(self):
        e = self.e
        for p in e.players.values():
            self.assertEqual(p.cash, BONUS, p.name)
            self.assertEqual(p.deposited, BONUS)
            self.assertEqual(p.season_base, BONUS)
            self.assertEqual(p.hold, {})
            self.assertEqual(p.orders, [])
            self.assertEqual((p.trades, p.margin_calls, p.fees_paid), (0, 0, 0.0))
            self.assertAlmostEqual(e.equity(p), BONUS, places=6)
        self.assertTrue(any(p.bot for p in e.players.values()))

    def test_the_tokens_still_balance(self):
        self.assertLess(abs(drift(self.e)), 1e-6)

    def test_the_market_is_untouched(self):
        e = self.e
        self.assertEqual({k: s.price for k, s in e.stocks.items()}, self.prices)

    def test_the_competitive_record_is_cleared_but_identity_stays(self):
        a = self.a
        self.assertEqual(a.badges, [])
        self.assertEqual(a.achievements, {})
        self.assertEqual(a.counters, {})
        self.assertEqual(a.following, ["bravo"])
        self.assertTrue(a.public)
        self.assertEqual(a.strikes, 2)
        self.assertEqual(a.name, "alpha")

    def test_contests_and_boards_start_again(self):
        e = self.e
        self.assertEqual(len(e.tournament_history), 0)
        self.assertEqual(e._sandboxes, {})
        e._social_t = 0
        e._social_tick()
        self.assertEqual({t["kind"] for t in e.tournaments}, {"marathon"})
        self.assertEqual(next(iter(e.tournaments))["entrants"], {})

    def test_players_are_told(self):
        self.assertTrue(any("Day 1 again" in n for n in self.a.notices))

    def test_the_game_carries_on_normally_afterwards(self):
        e, a = self.e, self.a
        ok, msg = e.trade(a, "CLDR", "buy", 0.5)
        self.assertTrue(ok, msg)
        self.assertAlmostEqual(a.cash, BONUS / 2, places=6)
        advance(e, 50)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_player_who_was_deep_in_a_loss_or_a_short_squeeze_is_reset_cleanly(self):
        e, a, b = played(2)
        e.stocks["OILX"].fair *= 8.0                                      # alpha's short is deeply under water
        e.reset_to_day_one()
        self.assertEqual(a.cash, BONUS)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_it_survives_a_restart(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(5)
            e = engine.Engine(state_file=path, bots=False)
            e.settings["signup_bonus"] = BONUS
            p = join(e, "persist")
            e.trade(p, "CLDR", "buy", 0.5)
            e.season_no = 7
            e.reset_to_day_one()
            f = engine.Engine(state_file=path, bots=False)
            p2 = next(x for x in f.players.values() if x.name == "persist")
            self.assertEqual(f.season_no, 1)
            self.assertEqual(p2.cash, BONUS)
            self.assertEqual(p2.hold, {})


class LedgerAfterResetTests(unittest.TestCase):
    def test_the_ledger_starts_again_and_still_explains_every_balance(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            random.seed(6)
            e = engine.Engine(state_file=os.path.join(tmp, "state.json"), bots=False,
                              ledger_path=os.path.join(tmp, "ledger.db"))
            e.settings["signup_bonus"] = BONUS
            p, q = join(e, "ledgera"), join(e, "ledgerb")
            e.trade(p, "CLDR", "buy", 0.4)
            e.now += 2
            e.trade(q, "OILX", "sell", 0.3)
            advance(e, 20)
            e.ledger.flush()
            self.assertGreater(e.ledger.count(), 4)
            e.reset_to_day_one()
            e.ledger.flush()
            kinds = {x["kind"] for x in e.ledger.all_history(p.token)}
            self.assertEqual(kinds, {"join", "credit"})
            self.assertEqual(e.ledger.curve(p.token), [])
            for pl in (p, q):
                self.assertAlmostEqual(sum(x["cash_delta"] for x in e.ledger.all_history(pl.token)), pl.cash, places=6)
            e.trade(p, "GOLD", "buy", 0.2)
            advance(e, 5)
            e.ledger.flush()
            self.assertIn("buy", {x["kind"] for x in e.ledger.all_history(p.token)})
            e.ledger.close()

    def test_a_crash_right_after_a_reset_loses_nothing(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path, ledger = os.path.join(tmp, "state.json"), os.path.join(tmp, "ledger.db")
            random.seed(7)
            e = engine.Engine(state_file=path, bots=False, ledger_path=ledger)
            e.settings["signup_bonus"] = BONUS
            p = join(e, "crashy")
            e.trade(p, "CLDR", "buy", 0.5)
            e.reset_to_day_one()                                           # (it saves at the end)
            e.now += 2
            e.trade(p, "GOLD", "buy", 0.5)                                 # after the save: only in the ledger
            e.ledger.flush()
            f = engine.Engine(state_file=path, bots=False, ledger_path=ledger)
            p2 = next(x for x in f.players.values() if x.name == "crashy")
            self.assertAlmostEqual(p2.cash, p.cash, places=6)
            self.assertIn("GOLD", p2.hold)
            self.assertLess(abs(drift(f)), 1e-6)
            f.ledger.close()
            e.ledger.close()


class CommandLineResetTests(unittest.TestCase):
    """`python reset_game.py` does the same from the command line, on a stopped server."""

    def make_game(self, tmp):
        for f in IsolatedServer.FILES + ["reset_game.py"]:
            src = os.path.join(ROOT, f)
            if os.path.exists(src):
                shutil.copy(src, tmp)
        with open(os.path.join(tmp, "zz_test_settings.json"), "w", encoding="utf-8") as fh:
            json.dump({"settings": {"premarket_seconds": 0, "aftermarket_seconds": 0, "signup_bonus": 2500, "bots": 0}}, fh)
        random.seed(8)
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            e = engine.Engine(state_file=os.path.join(tmp, "state.json"), bots=False, ledger_path=os.path.join(tmp, "ledger.db"))
            p, _ = e.join("cmdline")
            e.trade(p, "GOLD", "buy", 0.5)
            e.season_no = 9
            e.save()
            e.ledger.close()
        finally:
            os.chdir(cwd)

    def run_script(self, tmp, *args, port=None):
        env = dict(os.environ, PORT=str(port or free_port()))
        return subprocess.run([sys.executable, "reset_game.py", *args], cwd=tmp, env=env, capture_output=True, text=True,
                              timeout=120, input="RESET\n")

    def test_it_resets_a_stopped_game_and_backs_it_up(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            self.make_game(tmp)
            out = self.run_script(tmp)
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            self.assertIn("Day 1 again", out.stdout)
            folders = os.listdir(os.path.join(tmp, "backups"))
            self.assertEqual(len(folders), 1)
            self.assertTrue({"state.json", "ledger.db"} <= set(os.listdir(os.path.join(tmp, "backups", folders[0]))))
            d = json.load(open(os.path.join(tmp, "state.json"), encoding="utf-8"))
            self.assertEqual(d["season_no"], 1)
            me = next(x for x in d["players"] if x["name"] == "cmdline")
            self.assertEqual(me["hold"], {})
            self.assertAlmostEqual(me["cash"], 2500.0, places=6)

    def test_it_refuses_while_the_server_is_running_and_without_the_word(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            self.make_game(tmp)
            listener = socket.socket()
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            try:
                out = self.run_script(tmp, "--yes", port=listener.getsockname()[1])
            finally:
                listener.close()
            self.assertEqual(out.returncode, 1)
            self.assertIn("Stop it", out.stdout)
            self.assertFalse(os.path.exists(os.path.join(tmp, "backups")))
            bad = subprocess.run([sys.executable, "reset_game.py"], cwd=tmp, env=dict(os.environ, PORT=str(free_port())),
                                 capture_output=True, text=True, timeout=120, input="nope\n")
            self.assertEqual(bad.returncode, 1)
            self.assertIn("Not reset", bad.stdout)
            self.assertFalse(os.path.exists(os.path.join(tmp, "backups")))


class AdminEndpointTests(unittest.TestCase):
    def test_the_admin_can_reset_after_typing_the_word_and_the_old_game_is_backed_up(self):
        with IsolatedServer(settings={"signup_bonus": 2500}) as srv:
            c = Client(srv, "ResetMe")
            try:
                c.recv_until("state")
                c.send({"type": "trade", "ticker": "GOLD", "side": "buy", "pct": 0.5})
                self.assertTrue(c.recv_until("result")["ok"])
                admin = {"X-Admin-Key": "testkey"}
                self.assertEqual(http(srv, "/api/admin/reset", "POST", {"confirm": "RESET"})[0], 403)
                status, text, _ = http(srv, "/api/admin/reset", "POST", {"confirm": "reset please"}, admin)
                self.assertEqual(status, 400)
                status, text, _ = http(srv, "/api/admin/reset", "POST", {"confirm": "RESET"}, admin)
                self.assertEqual(status, 200, text)
                self.assertIn("backups", json.loads(text)["msg"])
                backups = os.path.join(srv.dir, "backups")
                folders = os.listdir(backups)
                self.assertEqual(len(folders), 1)
                files = set(os.listdir(os.path.join(backups, folders[0])))
                self.assertIn("state.json", files)
                self.assertIn("ledger.db", files)
                time.sleep(1.0)
                status, text, _ = http(srv, "/api/me", headers={"X-Token": c.token})
                self.assertEqual(status, 200)
                stats = json.loads(http(srv, "/api/admin/stats", headers=admin)[1])
                portfolio = json.loads(http(srv, "/api/portfolio", headers={"X-Token": c.token})[1])
                self.assertAlmostEqual(portfolio["cash"], 2500.0, places=2)
                self.assertEqual(portfolio["positions"], [])
                self.assertLess(abs(stats["invariant_drift"]), 1e-6)
            finally:
                c.close()


if __name__ == "__main__":
    unittest.main()
