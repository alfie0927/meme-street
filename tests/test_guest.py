"""Logged-out visitors: they can watch the live market and a stock's page (a hidden, read-only "guest" attached to the
page's connection), and cannot do anything else. Also the admin's funnel numbers, and the public /about page."""
import json
import time
import types
import unittest

from _helpers import IsolatedServer, advance, drift, engine, join, make_engine
from test_gateway import join as http_join, next_of, socket_to
from test_server import http


class GuestEngineTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(2)

    def test_the_guest_is_hidden_has_no_money_and_cannot_be_logged_in_as(self):
        e = self.e
        g = e.guest_for("guest")
        self.assertIs(g, e.guest)
        self.assertTrue(g.guest)
        self.assertIsNone(e.guest_for("anything else"))
        self.assertIsNone(e.player_for("guest"))                      # no ordinary request can act as the guest
        self.assertNotIn(g.token, e.players)
        self.assertNotIn(g.token, e.by_token)
        self.assertEqual((g.cash, g.hold, g.deposited), (0.0, {}, 0.0))
        self.assertFalse(join(e, "someone").guest)

    def test_a_visitors_first_message_is_the_market_with_no_account_and_no_chat(self):
        e = self.e
        p = join(e, "talker")
        e.post_chat(p, "hello there", "global", None)
        init = e.init_for(e.guest)
        self.assertEqual(init["type"], "init")
        self.assertGreater(len(init["stocks"]), 100)
        self.assertEqual((init["cash"], init["holdings"], init["chat"]), (0.0, [], []))
        self.assertEqual(init["players"], 1)                          # the guest is not counted as a player
        self.assertTrue(e.init_for(p)["chat"])                        # a real player does get the chat

    def test_a_guest_changes_nothing_in_the_books(self):
        e = self.e
        before = (len(e.players), e.house, e.minted, e.fees)
        e.init_for(e.guest)
        e.me_state(e.guest)
        advance(e, 5)
        self.assertEqual((len(e.players), e.house, e.minted, e.fees), before)
        self.assertLess(abs(drift(e)), 1e-6)


class FunnelTests(unittest.TestCase):
    def test_the_funnel_counts_sign_ups_traders_fees_and_who_pays_them(self):
        e = make_engine(3)
        a, b, c = join(e, "fa"), join(e, "fb"), join(e, "fc")
        for p in (a, b, c):
            p.created = e.now
        e.trade(a, "NVXA", "buy", 0.5)
        e.trade(b, "GOLD", "buy", 0.2)
        a.email = "a@example.com"
        a.email_verified = True
        f = e.funnel_stats()
        self.assertEqual((f["players"], f["traded"], f["with_email"], f["verified"]), (3, 2, 1, 1))
        self.assertEqual(f["signups"][-1]["n"], 3)                    # all three joined today
        self.assertEqual(len(f["signups"]), 14)
        self.assertEqual(f["payers"], 2)
        self.assertAlmostEqual(f["fees_total"], a.fees_paid + b.fees_paid)
        self.assertGreater(f["top10_share"], 0.5)                     # the biggest of two payers pays most of it
        self.assertLessEqual(f["top10_share"], 1.0)
        self.assertAlmostEqual(f["fees_per_payer"], f["fees_total"] / 2)

    def test_an_empty_game_has_a_funnel_of_zeros_not_an_error(self):
        f = make_engine(4).funnel_stats()
        self.assertEqual((f["players"], f["payers"], f["fees_total"], f["top10_share"]), (0, 0, 0, 0))

    def test_seen_uses_the_last_session_activity(self):
        e = make_engine(5)
        a, b = join(e, "seenA"), join(e, "seenB")
        e.sessions["k1"] = {"p": a.token, "seen": e.now - 3600}               # an hour ago
        e.sessions["k2"] = {"p": b.token, "seen": e.now - 3 * 86400}          # three days ago
        f = e.funnel_stats()
        self.assertEqual((f["seen_24h"], f["seen_7d"]), (1, 2))


class GuestServerTests:
    """Shared by the two set-ups below (straight at the game, and through a gateway)."""
    srv = None
    port = None

    @classmethod
    def tearDownClass(cls):
        cls.srv.__exit__(None, None, None)

    def url(self):
        return f"http://127.0.0.1:{self.port}"

    def overview(self):
        status, body, _ = http(types.SimpleNamespace(url=self.url()), "/api/admin/overview", headers={"X-Admin-Key": "testkey"})
        self.assertEqual(status, 200)
        return json.loads(body)

    def test_a_visitor_gets_the_market_and_ticks_with_no_money(self):
        with socket_to(self.port, "guest") as ws:
            init = json.loads(ws.recv(timeout=10))
            self.assertEqual(init["type"], "init")
            self.assertGreater(len(init["stocks"]), 100)
            self.assertEqual((init["cash"], init["holdings"], init["chat"]), (0.0, [], []))
            t = next_of(ws, "tick")
            self.assertEqual(t["me"]["cash"], 0.0)
            self.assertIn("px", t)

    def test_a_visitor_can_look_up_charts_and_company_pages(self):
        with socket_to(self.port, "guest") as ws:
            next_of(ws, "init")
            ws.send(json.dumps({"type": "history", "ticker": "NVXA", "period": "5m"}))
            self.assertEqual(next_of(ws, "history")["ticker"], "NVXA")
            ws.send(json.dumps({"type": "company", "ticker": "NVXA"}))
            self.assertEqual(next_of(ws, "company")["ticker"], "NVXA")

    def test_a_visitor_cannot_trade_order_chat_or_report(self):
        before = self.overview()
        with socket_to(self.port, "guest") as ws:
            next_of(ws, "init")
            for msg in ({"type": "trade", "ticker": "NVXA", "side": "buy", "pct": 0.5},
                        {"type": "order", "action": "place", "ticker": "NVXA", "kind": "limit_buy", "trigger": 1, "pct": 1},
                        {"type": "contest_trade", "id": "x", "ticker": "NVXA", "side": "buy", "pct": 1},
                        {"type": "chat", "text": "hello"}, {"type": "chat_history"}, {"type": "chat_report", "id": 1},
                        {"type": "chat_appeal", "text": "please"}):
                ws.send(json.dumps(msg))
                r = next_of(ws, "result")
                self.assertFalse(r["ok"], msg)
                self.assertIn("account", r["msg"])
        after = self.overview()
        self.assertEqual(after["stats"]["humans"], before["stats"]["humans"])           # no player was made
        self.assertEqual(after["trades_total"], before["trades_total"])
        self.assertLess(abs(after["stats"]["invariant_drift"]), 1e-6)

    def test_a_visitor_does_not_receive_the_chat(self):
        a = http_join(self.url(), "GuestChatPlayer")
        with socket_to(self.port, "guest") as guest, socket_to(self.port, a["token"]) as member:
            next_of(guest, "init")
            next_of(member, "init")
            member.send(json.dumps({"type": "chat", "text": "members only talk"}))
            self.assertEqual(next_of(member, "chat")["msg"]["text"], "members only talk")     # (the member did get it)
            end = time.time() + 4
            seen = []
            while time.time() < end:
                try:
                    seen.append(json.loads(guest.recv(timeout=2)).get("type"))
                except TimeoutError:
                    break
            self.assertTrue(seen)                                                          # ticks kept coming
            self.assertNotIn("chat", seen)

    def test_the_guest_key_is_not_a_login_for_ordinary_requests(self):
        for path in ("/api/portfolio", "/api/me", "/api/history"):
            status, _, _ = http(types.SimpleNamespace(url=self.url()), path, headers={"X-Token": "guest"})
            self.assertEqual(status, 401, path)

    def test_the_admin_page_counts_visitors_apart_from_players(self):
        a = http_join(self.url(), "GuestCount")
        with socket_to(self.port, a["token"]) as member:
            next_of(member, "init")
            before = self.overview()
            with socket_to(self.port, "guest") as g1, socket_to(self.port, "guest") as g2:
                next_of(g1, "init")
                next_of(g2, "init")
                time.sleep(0.5)
                during = self.overview()
            self.assertEqual(during["guests"], before["guests"] + 2)
            self.assertEqual(during["online"], before["online"])                           # visitors are not "online players"

    def test_the_admin_funnel_reports_the_players_who_traded(self):
        a = http_join(self.url(), "FunnelTrader")
        with socket_to(self.port, a["token"]) as ws:
            next_of(ws, "init")
            ws.send(json.dumps({"type": "trade", "ticker": "NVXA", "side": "buy", "pct": 0.5}))
            self.assertTrue(next_of(ws, "result")["ok"])
        f = self.overview()["funnel"]
        self.assertGreaterEqual(f["players"], 1)
        self.assertGreaterEqual(f["traded"], 1)
        self.assertGreater(f["fees_total"], 0)
        self.assertEqual(f["signups"][-1]["n"] >= 1, True)

    def test_the_public_pages(self):
        srv = types.SimpleNamespace(url=self.url())
        status, body, _ = http(srv, "/about")
        self.assertEqual(status, 200)
        self.assertIn("Meme Street", body)
        self.assertNotIn("free to play", body.lower())                                    # it is not free to play
        self.assertNotIn("guaranteed", body.lower())
        status, body, _ = http(srv, "/")
        self.assertEqual(status, 200)
        self.assertIn('id="guest-hero"', body)
        self.assertIn('property="og:title"', body)


class GuestDirectTests(GuestServerTests, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = IsolatedServer().__enter__()
        cls.port = cls.srv.port


class GuestThroughAGatewayTests(GuestServerTests, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = IsolatedServer(gateways=1).__enter__()
        cls.port = cls.srv.gateway_ports[0]


if __name__ == "__main__":
    unittest.main()
