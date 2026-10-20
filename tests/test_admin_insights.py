"""The admin dashboard's deeper numbers: activity over time from the ledger, the engine's insights (market, orders, positions,
biggest players, chat, settings), the machine's state, and the wrong-admin-key counter and lock-out."""
import json
import os
import tempfile
import time
import types
import unittest

from _helpers import IsolatedServer, engine, join, make_engine
from ledger import Ledger
from test_gateway import join as http_join, next_of, socket_to
from test_server import http

NOW = 10 * 86400 + 5 * 3600 + 1800              # half past five on the tenth day, in the ledger's clock


class LedgerSummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ledger = Ledger(os.path.join(self.tmp.name, "ledger.db"))
        add = self.ledger.add
        add(t=NOW - 1800, kind="join", token="A", name="A")
        add(t=NOW - 1800, kind="buy", token="A", ticker="NVXA", notional=100.0, fee=0.1)
        add(t=NOW - 1800, kind="sell", token="B", ticker="GOLD", notional=50.0, fee=0.05)
        add(t=NOW - 3 * 3600, kind="short", token="A", ticker="NVXA", notional=200.0, fee=0.2)
        add(t=NOW - 2 * 86400, kind="buy", token="C", ticker="GOLD", notional=10.0, fee=0.01)
        add(t=NOW - 100, kind="dividend", token="A", ticker="NVXA", notional=0.0)
        self.ledger.flush()
        self.s = self.ledger.summary(NOW)

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def test_the_last_24_hours_are_24_hourly_buckets_ending_with_this_hour(self):
        h = self.s["hours"]
        self.assertEqual(len(h), 24)
        self.assertEqual(h[-1]["t"], (NOW // 3600) * 3600)
        self.assertEqual((h[-1]["trades"], h[-1]["volume"]), (2, 150.0))
        self.assertAlmostEqual(h[-1]["fees"], 0.15)
        self.assertEqual(h[20]["trades"], 1)                          # three hours earlier
        self.assertEqual(sum(x["trades"] for x in h), 3)              # (the dividend is not a trade; the 2-day-old trade is outside)

    def test_days_count_trades_money_fees_different_traders_and_sign_ups(self):
        d = self.s["days"]
        self.assertEqual(len(d), 7)
        today, two_ago = d[-1], d[-3]
        self.assertEqual((today["trades"], today["traders"], today["signups"]), (3, 2, 1))
        self.assertAlmostEqual(today["volume"], 350.0)
        self.assertEqual((two_ago["trades"], two_ago["traders"]), (1, 1))
        self.assertEqual(d[0]["trades"], 0)

    def test_the_most_traded_stocks_by_money_with_their_buy_share(self):
        t = self.s["tickers"]
        self.assertEqual([x["ticker"] for x in t], ["NVXA", "GOLD"])
        nv = t[0]
        self.assertEqual((nv["trades"], nv["traders"]), (2, 1))
        self.assertAlmostEqual(nv["volume"], 300.0)
        self.assertAlmostEqual(nv["buy_share"], 100.0 / 300.0)
        self.assertEqual(t[1]["buy_share"], 0.0)

    def test_the_kinds_of_the_last_day(self):
        self.assertEqual(self.s["kinds"], {"buy": 1, "sell": 1, "short": 1, "dividend": 1})

    def test_an_empty_ledger_gives_zeros_not_an_error(self):
        empty = Ledger(os.path.join(self.tmp.name, "empty.db"))
        s = empty.summary(NOW)
        empty.close()
        self.assertEqual((len(s["hours"]), len(s["days"]), s["tickers"], s["kinds"]), (24, 7, [], {}))
        self.assertEqual(sum(x["trades"] for x in s["hours"]), 0)


class EngineInsightsTests(unittest.TestCase):
    def test_the_market_orders_positions_players_chat_and_settings(self):
        e = make_engine(7)
        a, b = join(e, "ins_a"), join(e, "ins_b")
        e.trade(a, "NVXA", "buy", 0.5)
        e.trade(b, "GOLD", "buy", 0.2)
        e.trade(b, "CLDR", "sell", 0.3)                               # a short
        ok, msg = e.place_order(a, "NVXA", "limit_buy", e.stocks["NVXA"].price * 0.5, 0.5, None)
        self.assertTrue(ok, msg)
        e.post_chat(a, "hello admin", "global", None)
        i = e.admin_insights()
        g = i["game"]
        self.assertEqual(g["listings"], len(e.stocks))
        self.assertEqual(g["index_members"], 50)
        self.assertEqual(g["companies"] + g["moonshots"] + g["funds_commodities"] + g["indices_etfs"], len(e.stocks))
        self.assertEqual(i["orders"]["open"], 1)
        self.assertEqual(i["orders"]["by_kind"], {"limit_buy": 1})
        self.assertEqual(i["positions"]["holders"], 2)
        self.assertGreater(i["positions"]["long_value"], 0)
        self.assertGreater(i["positions"]["short_value"], 0)
        self.assertEqual(i["positions"]["biggest"][0]["value"], max(x["value"] for x in i["positions"]["biggest"]))
        self.assertEqual({x["name"] for x in i["players"]["by_trades"]}, {"ins_a", "ins_b"})
        self.assertEqual(i["players"]["by_trades"][0]["name"], "ins_b")           # two trades against one
        self.assertAlmostEqual(i["players"]["total_equity"], e.equity(a) + e.equity(b))
        self.assertEqual(i["social"]["chat_last_hour"], 1)
        self.assertEqual(i["settings"]["game_year_days"], 365)
        self.assertEqual(i["settings"]["quarter_game_days"], 91.25)
        self.assertEqual(i["settings"]["fee_per_side"], engine.FEE)
        self.assertIsNone(i["activity"])                                          # (no ledger in this engine)

    def test_an_empty_game_has_empty_lists_not_an_error(self):
        i = make_engine(8).admin_insights()
        self.assertEqual((i["orders"]["open"], i["positions"]["holders"], i["positions"]["biggest"]), (0, 0, []))
        self.assertEqual(i["players"]["by_equity"], [])

    def test_the_save_time_is_recorded_when_a_save_succeeds(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            import random
            random.seed(9)
            e = engine.Engine(state_file=os.path.join(tmp, "state.json"))
            self.assertEqual(e.last_saved_at, 0.0)
            e.save()
            self.assertGreater(e.last_saved_at, 0.0)


class InsightsServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = IsolatedServer().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.srv.__exit__(None, None, None)

    def get(self, path="/api/admin/insights", key="testkey"):
        return http(self.srv, path, headers={"X-Admin-Key": key})

    def test_it_needs_the_admin_key(self):
        status, _, _ = http(self.srv, "/api/admin/insights")
        self.assertEqual(status, 403)
        self.assertEqual(self.get(key="not-the-key")[0], 403)

    def test_the_machine_numbers_make_sense(self):
        o = json.loads(self.get()[1])["ops"]
        self.assertGreater(o["uptime_s"], 0)
        self.assertGreater(o["disk_free_gb"], 0.1)
        self.assertTrue(0 < o["disk_free_pct"] <= 100)
        self.assertTrue(o["memory_mb"] is None or o["memory_mb"] > 10)
        self.assertGreater(o["state_mb"], 0)
        self.assertGreater(o["ledger_mb"], 0)
        self.assertIsNotNone(o["saved_ago_s"])
        self.assertFalse(o["backup"]["found"] and o["backup"]["copies"] < 0)

    def test_connections_count_players_and_visitors_and_keep_a_history(self):
        a = http_join(self.srv.url, "InsConn")
        with socket_to(self.srv.port, a["token"]) as member, socket_to(self.srv.port, "guest") as visitor:
            next_of(member, "init")
            next_of(visitor, "init")
            time.sleep(0.5)
            c = json.loads(self.get()[1])["connections"]
        self.assertGreaterEqual(c["players"], 1)
        self.assertGreaterEqual(c["visitors"], 1)
        self.assertIsInstance(c["series"], list)

    def test_wrong_keys_are_counted_and_listed_with_where_they_came_from(self):
        before = json.loads(self.get()[1])["security"]["wrong_last_hour"]
        for _ in range(3):
            self.assertEqual(self.get(key="guess")[0], 403)
        s = json.loads(self.get()[1])["security"]
        self.assertEqual(s["wrong_last_hour"], before + 3)
        self.assertEqual(s["recent"][0]["what"], "wrong key")
        self.assertEqual(s["recent"][0]["addr"], "127.0.0.1")
        self.assertEqual(s["recent"][0]["path"], "/api/admin/insights")
        self.assertEqual((s["limit"], s["window_s"]), (10, 600))


class InsightsActivityServerTests(unittest.TestCase):
    """Its own server: the activity numbers are kept for about 25 seconds, so the first request must come after the trade."""

    def test_it_has_every_panel_the_page_draws_and_shows_the_trade(self):
        with IsolatedServer() as srv:
            a = http_join(srv.url, "InsServer")
            with socket_to(srv.port, a["token"]) as ws:
                next_of(ws, "init")
                ws.send(json.dumps({"type": "trade", "ticker": "NVXA", "side": "buy", "pct": 0.5}))
                self.assertTrue(next_of(ws, "result")["ok"])
            time.sleep(2.5)                                                        # (the ledger is written once a tick)
            status, text, _ = http(srv, "/api/admin/insights", headers={"X-Admin-Key": "testkey"})
            self.assertEqual(status, 200)
            d = json.loads(text)
        for k in ("game", "orders", "positions", "players", "social", "settings", "activity", "ops", "connections", "security", "ledger_events"):
            self.assertIn(k, d)
        self.assertEqual(len(d["activity"]["hours"]), 24)
        self.assertEqual(len(d["activity"]["days"]), 7)
        self.assertIn("NVXA", [t["ticker"] for t in d["activity"]["tickers"]])      # the trade is in the most-traded list
        self.assertGreaterEqual(d["activity"]["days"][-1]["trades"], 1)
        self.assertGreaterEqual(d["activity"]["days"][-1]["signups"], 1)
        self.assertGreater(d["ledger_events"], 0)
        self.assertEqual(d["positions"]["holders"], 1)


class AdminLockoutTests(unittest.TestCase):
    def test_ten_wrong_keys_lock_an_address_out_even_with_the_right_key(self):
        with IsolatedServer() as srv:
            for i in range(10):
                self.assertEqual(http(srv, "/api/admin/stats", headers={"X-Admin-Key": "wrong%d" % i})[0], 403, i)
            status, text, _ = http(srv, "/api/admin/stats", headers={"X-Admin-Key": "wrong-again"})
            self.assertEqual(status, 429)
            self.assertIn("try again", text)
            self.assertEqual(http(srv, "/api/admin/stats", headers={"X-Admin-Key": "testkey"})[0], 429)    # the right key is locked out too
            self.assertEqual(http(srv, "/api/admin/overview", headers={"X-Admin-Key": "testkey"})[0], 429)
            # the game itself is not affected: a player can still join and the public pages still work
            self.assertEqual(http(srv, "/api/auth_mode")[0], 200)
            self.assertEqual(http(srv, "/api/join", "POST", {"name": "StillWorks"})[0], 200)


class InsightsThroughAGatewayTests(unittest.TestCase):
    def test_the_insights_and_the_counting_of_wrong_keys_work_through_a_gateway(self):
        with IsolatedServer(gateways=1) as srv:
            base = types.SimpleNamespace(url=f"http://127.0.0.1:{srv.gateway_ports[0]}")
            self.assertEqual(http(base, "/api/admin/insights", headers={"X-Admin-Key": "nope"})[0], 403)
            status, text, _ = http(base, "/api/admin/insights", headers={"X-Admin-Key": "testkey"})
            self.assertEqual(status, 200)
            d = json.loads(text)
            self.assertEqual(d["connections"]["gateways"], 1)
            self.assertEqual(d["security"]["wrong_last_hour"], 1)


if __name__ == "__main__":
    unittest.main()
