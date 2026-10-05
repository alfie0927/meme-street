"""Server tests: the real FastAPI app, run from an isolated temporary copy (your state.json is never touched).

Needs `uvicorn` and `websockets` (both installed with requirements.txt).
"""
import json
import time
import unittest
import urllib.error
import urllib.request

from websockets.sync.client import connect

from _helpers import IsolatedServer


def http(srv, path, method="GET", body=None, headers=None):
    req = urllib.request.Request(srv.url + path, method=method, headers=headers or {},
                                 data=None if body is None else json.dumps(body).encode())
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), dict(e.headers)


class Client:
    """A WebSocket player. It follows the delta protocol the way the page does: `init` once, then `tick` updates are
    merged into `self.state`, so `recv_until("state")` returns the up-to-date picture after either."""

    def __init__(self, srv, name):
        status, body, _ = http(srv, "/api/join", "POST", {"name": name})
        assert status == 200, body
        self.srv = srv
        self.name = name
        self.token = json.loads(body)["token"]
        self._cm = connect(f"ws://127.0.0.1:{srv.port}/ws?token={self.token}", max_size=None, max_queue=None,
                           ping_interval=None, close_timeout=2)
        self.ws = self._cm.__enter__()
        self.state = None
        self.last_tick = None
        self.notices = []
        self.chat = []

    def _apply(self, m):
        t = m.get("type")
        if t == "init":
            self.state = m
            self.notices += m.get("notices", [])
        elif t == "tick" and self.state is not None:
            st = self.state
            st.update(m["me"])
            for s in st["stocks"]:
                px = m["px"].get(s["ticker"])
                if px:
                    s["price"], s["chg"] = px
            for tk, sl in m.get("slow", {}).items():
                for s in st["stocks"]:
                    if s["ticker"] == tk:
                        s.update(sl)
            if "board" in m:
                st["board"] = m["board"]
            st["market"] = m["market"]
            self.last_tick = m
        elif t == "notice":
            self.notices += m["msgs"]
        elif t == "chat":
            self.chat.append(m["msg"])

    def recv_until(self, kind, timeout=8):
        end = time.time() + timeout
        while time.time() < end:
            m = json.loads(self.ws.recv(timeout=max(0.1, end - time.time())))
            self._apply(m)
            mt = m.get("type")
            if kind == "state" and mt in ("init", "tick"):
                return self.state
            if mt == kind:
                return m
        raise AssertionError(f"no {kind!r} message within {timeout}s")

    def get(self, path, headers=None):
        return http(self.srv, path, headers={"X-Token": self.token, **(headers or {})})

    def post(self, path, body=None):
        return http(self.srv, path, "POST", body if body is not None else {}, {"X-Token": self.token})

    def send(self, obj):
        self.ws.send(obj if isinstance(obj, str) else json.dumps(obj))

    def close(self):
        try:
            self._cm.__exit__(None, None, None)
        except Exception:
            pass


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = IsolatedServer().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.srv.__exit__(None, None, None)

    def test_pages_are_served_and_never_cached(self):
        for path in ("/", "/holdings", "/stock/NVXA"):
            status, body, headers = http(self.srv, path)
            self.assertEqual(status, 200, path)
            self.assertIn("Meme Street", body)
            self.assertIn("no-store", headers.get("cache-control", headers.get("Cache-Control", "")))

    def test_join_rules(self):
        status, body, _ = http(self.srv, "/api/join", "POST", {"name": "Joiner1"})
        self.assertEqual(status, 200)
        self.assertEqual(http(self.srv, "/api/join", "POST", {"name": "joiner1"})[0], 400)    # taken, any case
        self.assertEqual(http(self.srv, "/api/join", "POST", {"name": "x"})[0], 400)          # too short
        self.assertEqual(http(self.srv, "/api/join", "POST", {})[0], 422)                      # missing field
        status, body, _ = http(self.srv, "/api/join", "POST", {"name": "<b>Evil</b>"})
        if status == 200:
            self.assertNotIn("<", json.loads(body)["name"])

    def test_the_logo_is_served_and_other_files_are_not(self):
        status, body, headers = http(self.srv, "/brand/memestreet_logo_peaks.png")
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith("PNG") or len(body) > 1000)
        self.assertEqual(http(self.srv, "/brand/state.json")[0], 404)
        self.assertEqual(http(self.srv, "/brand/..%2Fserver.py")[0], 404)

    def test_bad_token_is_rejected(self):
        with connect(f"ws://127.0.0.1:{self.srv.port}/ws?token=nope") as ws:
            m = json.loads(ws.recv(timeout=5))
            self.assertEqual(m["type"], "error")

    def test_state_contents_and_no_hidden_mood(self):
        c = Client(self.srv, "StateTest")
        try:
            st = c.recv_until("state")
            for key in ("cash", "equity", "stocks", "holdings", "news", "board", "index", "upcoming", "notices"):
                self.assertIn(key, st)
            self.assertEqual(st["cash"], 1000)
            tickers = {s["ticker"] for s in st["stocks"]}
            self.assertIn("MSI", tickers)
            self.assertIn("GOLD", tickers)
            self.assertGreater(len(tickers), 30)
            flat = json.dumps(st).lower()
            self.assertNotIn('"mood"', flat)
            self.assertNotIn('"narrative"', flat)
            nvxa = next(s for s in st["stocks"] if s["ticker"] == "NVXA")
            for key in ("margin_req", "borrow_hour", "borrow_util"):
                self.assertIn(key, nvxa)
        finally:
            c.close()

    def test_buy_amount_short_and_cover_through_the_socket(self):
        c = Client(self.srv, "TraderOne")
        try:
            c.recv_until("state")
            c.send({"type": "trade", "ticker": "GOLD", "side": "buy", "pct": 0.5, "amount": 40})
            r = c.recv_until("result")
            self.assertTrue(r["ok"], r)
            self.assertIn("40.00 MB", r["msg"])
            time.sleep(1.2)
            c.send({"type": "trade", "ticker": "NVXA", "side": "sell", "pct": 1})
            r = c.recv_until("result")
            self.assertTrue(r["ok"], r)
            self.assertIn("Shorted", r["msg"])
            time.sleep(2.5)   # clear of the 1-second cooldown, which is measured in engine ticks
            st = c.recv_until("state")
            sides = {h["ticker"]: h["side"] for h in st["holdings"]}
            self.assertEqual(sides.get("GOLD"), "long")
            self.assertEqual(sides.get("NVXA"), "short")
            c.send({"type": "trade", "ticker": "NVXA", "side": "buy", "pct": 1})
            r = c.recv_until("result")
            self.assertTrue(r["ok"], r)
            self.assertIn("Covered", r["msg"])
        finally:
            c.close()

    def test_orders_through_the_socket_and_in_every_tick(self):
        c = Client(self.srv, "OrderOne")
        try:
            st = c.recv_until("state")
            price = next(s["price"] for s in st["stocks"] if s["ticker"] == "GOLD")
            c.send({"type": "order", "action": "place", "ticker": "GOLD", "kind": "limit_buy", "trigger": price * 0.8, "pct": 0.2})
            r = c.recv_until("result")
            self.assertTrue(r["ok"], r)
            self.assertIn("Limit buy placed", r["msg"])
            time.sleep(1.5)
            st = c.recv_until("state")
            self.assertEqual([o["kind"] for o in st["orders"]], ["limit_buy"])      # in the tick's "me", with its fields
            order = st["orders"][0]
            self.assertEqual((order["ticker"], order["cond"], order["label"]), ("GOLD", "le", "Limit buy"))
            time.sleep(0.3)
            c.send({"type": "order", "action": "place", "ticker": "GOLD", "kind": "limit_buy", "trigger": price * 2, "pct": 0.2})
            r = c.recv_until("result")
            self.assertFalse(r["ok"])                                               # it would trigger immediately
            time.sleep(0.3)
            for bad in ({"action": "place", "ticker": "GOLD", "kind": "limit_buy", "trigger": "abc"},
                        {"action": "place", "ticker": "GOLD", "kind": "nope", "trigger": 1},
                        {"action": "place", "ticker": "GOLD", "kind": "limit_buy", "trigger": 1, "pct": 5},
                        {"action": "cancel", "id": "x"}, {"action": "frobnicate"}, {"action": "bracket", "ticker": "GOLD"}):
                c.send(dict(bad, type="order"))
                r = c.recv_until("result")
                self.assertFalse(r["ok"], bad)
                time.sleep(0.3)
            c.send({"type": "order", "action": "cancel", "id": order["id"]})
            r = c.recv_until("result")
            self.assertTrue(r["ok"], r)
            time.sleep(1.5)
            st = c.recv_until("state")
            self.assertEqual(st["orders"], [])                                      # the empty list arrives once
        finally:
            c.close()

    def test_there_is_no_position_limit(self):
        c = Client(self.srv, "NoLimitTest")
        try:
            c.recv_until("state")
            c.send({"type": "trade", "ticker": "DOGO", "side": "buy", "pct": 1})
            r = c.recv_until("result")
            self.assertTrue(r["ok"])
            self.assertNotIn("limit", r["msg"].lower())
            self.assertNotIn("limit_frac", json.dumps(c.state["stocks"][0]))
        finally:
            c.close()

    def test_history_and_company_requests_sent_together_are_both_answered(self):
        """Regression: one shared rate limit used to drop the second request."""
        c = Client(self.srv, "Lookups")
        try:
            c.recv_until("state")
            c.send({"type": "history", "ticker": "NVXA", "period": "30s"})
            c.send({"type": "company", "ticker": "NVXA"})
            h = c.recv_until("history")
            co = c.recv_until("company")
            self.assertTrue(h["candles"])
            self.assertEqual(co["ticker"], "NVXA")
        finally:
            c.close()

    def test_every_timeframe_and_unknown_inputs(self):
        c = Client(self.srv, "Frames")
        try:
            c.recv_until("state")
            for period in ("30s", "1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d", "1mo", "1y", "bogus", "day"):
                time.sleep(0.25)
                c.send({"type": "history", "ticker": "GOLD", "period": period})
                m = c.recv_until("history")
                self.assertIn("candles", m, period)
            time.sleep(0.25)
            c.send({"type": "history", "ticker": "NOPE", "period": "30s"})
            self.assertIn("error", c.recv_until("history"))
        finally:
            c.close()

    def test_malformed_messages_do_not_break_the_connection(self):
        c = Client(self.srv, "Garbage")
        try:
            c.recv_until("state")
            junk = ["not json{{{", "", "null", "[1,2,3]", '"str"', "42", "x" * 5000, '{"type":["a"]}',
                    json.dumps({"type": "trade", "ticker": None, "side": None, "pct": "x", "amount": [1]}),
                    json.dumps({"type": "trade", "ticker": "GOLD", "side": "buy", "pct": 1e308, "amount": "abc"})]
            for j in junk:
                c.send(j)
            time.sleep(1.2)
            c.send({"type": "trade", "ticker": "GOLD", "side": "buy", "pct": 0.1})
            # the junk trades each get their own error reply first; the good one must still succeed
            replies = []
            end = time.time() + 10
            while time.time() < end:
                r = c.recv_until("result", timeout=10)
                replies.append(r)
                if r["ok"]:
                    break
            self.assertTrue(replies[-1]["ok"], replies)
        finally:
            c.close()

    def test_many_clients_all_receive_updates(self):
        clients = [Client(self.srv, f"Crowd{i:02d}") for i in range(12)]
        try:
            for c in clients:
                st = c.recv_until("state", timeout=6)
                self.assertEqual(st["cash"], 1000)
        finally:
            for c in clients:
                c.close()

    def test_admin_endpoints_need_the_key(self):
        self.assertEqual(http(self.srv, "/api/admin/stats")[0], 403)
        self.assertEqual(http(self.srv, "/api/admin/stats", headers={"X-Admin-Key": "wrong"})[0], 403)
        status, body, _ = http(self.srv, "/api/admin/stats", headers={"X-Admin-Key": "testkey"})
        self.assertEqual(status, 200)
        stats = json.loads(body)
        self.assertLess(abs(stats["invariant_drift"]), 1e-6)
        for key in ("fees", "house_reserve", "borrow_fees", "short_shortfall", "short_interest"):
            self.assertIn(key, stats)

    def test_admin_credit_adds_cash(self):
        c = Client(self.srv, "Credited")
        try:
            c.recv_until("state")
            status, body, _ = http(self.srv, "/api/admin/credit", "POST", {"name": "Credited", "amount": 250},
                                   {"X-Admin-Key": "testkey"})
            self.assertEqual(status, 200, body)
            time.sleep(1.5)
            self.assertEqual(c.recv_until("state")["cash"], 1250)
        finally:
            c.close()

    def test_admin_page_and_data_endpoints(self):
        status, body, headers = http(self.srv, "/admin")
        self.assertEqual(status, 200)
        self.assertIn("Meme Street Admin", body)
        self.assertIn("no-store", headers.get("cache-control", headers.get("Cache-Control", "")))
        self.assertNotIn("testkey", body)                       # the key is never in the page
        self.assertEqual(http(self.srv, "/api/admin/overview")[0], 403)
        self.assertEqual(http(self.srv, "/api/admin/player/anyone")[0], 403)
        admin = {"X-Admin-Key": "testkey"}
        status, body, _ = http(self.srv, "/api/admin/overview", headers=admin)
        self.assertEqual(status, 200, self.srv.log()[-2500:])
        o = json.loads(body)
        for key in ("stats", "series", "online", "trades_total", "trades_per_min", "margin_calls",
                    "margin_log", "dist", "winners"):
            self.assertIn(key, o)
        self.assertEqual(len(o["dist"]), 8)
        self.assertEqual(http(self.srv, "/api/admin/player/nobody-by-this-name", headers=admin)[0], 404)

    def test_admin_player_detail_shows_the_trades(self):
        c = Client(self.srv, "AdminSees")
        try:
            c.recv_until("state")
            c.send({"type": "trade", "ticker": "GOLD", "side": "buy", "pct": 0.1})
            self.assertTrue(c.recv_until("result")["ok"])
            status, body, _ = http(self.srv, "/api/admin/player/adminsees", headers={"X-Admin-Key": "testkey"})
            self.assertEqual(status, 200)
            d = json.loads(body)
            self.assertEqual(d["name"], "AdminSees")
            self.assertEqual([x["k"] for x in d["log"]], ["buy"])
            self.assertEqual(d["holdings"][0]["ticker"], "GOLD")
        finally:
            c.close()

    # ------------------------------------------------------------------ the delta protocol
    def test_init_then_small_ticks(self):
        c = Client(self.srv, "Protocol1")
        try:
            first = json.loads(c.ws.recv(timeout=8))
            self.assertEqual(first["type"], "init")
            for key in ("seq", "static_v", "chat", "stocks", "sectors", "index", "cash", "notices"):
                self.assertIn(key, first)
            raw_sizes = []
            ticks = []
            end = time.time() + 6
            while time.time() < end and len(ticks) < 3:
                raw = c.ws.recv(timeout=5)
                m = json.loads(raw)
                if m["type"] == "tick":
                    ticks.append(m)
                    raw_sizes.append(len(raw))
            self.assertEqual(len(ticks), 3)
            for m, size in zip(ticks, raw_sizes):
                if "slow" not in m or len(m["slow"]) < 20:
                    self.assertLess(size, 12000, "a tick should be a few kB, not the whole market")
                for key in ("seq", "t", "px", "idx", "sec", "market", "season_left", "players", "news", "static_v", "me"):
                    self.assertIn(key, m)
                self.assertNotIn("notices", m["me"])            # notices travel as their own reliable messages
                self.assertEqual(set(m["px"]), {s["ticker"] for s in first["stocks"]})
                tk, row = next(iter(m["px"].items()))
                self.assertEqual(len(row), 2)
            self.assertGreater(ticks[1]["seq"], ticks[0]["seq"])
            self.assertEqual(ticks[0]["static_v"], first["static_v"])
            self.assertGreater(len(json.dumps(first)), 5 * min(raw_sizes))
        finally:
            c.close()

    def test_tick_prices_agree_with_the_init_and_never_leak_hidden_state(self):
        c = Client(self.srv, "Protocol2")
        try:
            st = c.recv_until("state")
            first = {s["ticker"]: dict(s) for s in st["stocks"]}
            c.recv_until("state")
            m = c.last_tick
            self.assertIsNotNone(m)
            flat = json.dumps(m).lower()
            for bad in ('"mood"', '"narrative"', '"safety"', '"token"'):
                self.assertNotIn(bad, flat)
            for tkr, (price, chg) in list(m["px"].items())[:40]:
                self.assertAlmostEqual(price / max(first[tkr]["price"], 1e-9), 1.0, delta=0.5)
        finally:
            c.close()

    def test_slow_data_arrives_every_fifth_tick_and_only_when_changed(self):
        c = Client(self.srv, "Protocol3")
        try:
            c.recv_until("state")
            seen_board = []
            end = time.time() + 14
            while time.time() < end and len(seen_board) < 2:
                c.recv_until("state")
                m = c.last_tick
                if "board" in m:
                    seen_board.append(m["seq"])
                if "slow" in m:
                    self.assertEqual(m["seq"] % 5, 0)
            self.assertTrue(seen_board, "the leaderboard should come every fifth tick")
            for seq in seen_board:
                self.assertEqual(seq % 5, 0)
        finally:
            c.close()

    def test_sync_request_sends_a_fresh_init(self):
        c = Client(self.srv, "Protocol4")
        try:
            c.recv_until("state")
            time.sleep(0.2)
            c.send({"type": "sync"})
            m = c.recv_until("init")
            self.assertIn("stocks", m)
        finally:
            c.close()

    def test_achievement_notice_is_delivered_as_its_own_message(self):
        c = Client(self.srv, "Notified")
        try:
            c.recv_until("state")
            c.send({"type": "trade", "ticker": "GOLD", "side": "buy", "pct": 0.1})
            self.assertTrue(c.recv_until("result")["ok"])
            msg = c.recv_until("notice", timeout=6)
            self.assertTrue(any("First steps" in n for n in msg["msgs"]), msg)
        finally:
            c.close()

    # ------------------------------------------------------------------ portfolio, history, CSV
    def test_portfolio_history_and_csv_endpoints(self):
        c = Client(self.srv, "FolioHist")
        try:
            c.recv_until("state")
            for path in ("/api/portfolio", "/api/history", "/api/history.csv", "/api/me", "/api/boards"):
                self.assertEqual(http(self.srv, path)[0], 401, path)
                self.assertEqual(http(self.srv, path, headers={"X-Token": "nope"})[0], 401, path)
            c.send({"type": "trade", "ticker": "GOLD", "side": "buy", "pct": 0.2})
            self.assertTrue(c.recv_until("result")["ok"])
            time.sleep(2.6)
            c.send({"type": "trade", "ticker": "GOLD", "side": "sell", "pct": 1})
            self.assertTrue(c.recv_until("result")["ok"])
            status, body, _ = c.get("/api/portfolio")
            self.assertEqual(status, 200, body)
            pf = json.loads(body)
            for key in ("equity", "cash", "pnl", "realized", "unrealized", "fees", "positions", "allocation", "curve",
                        "best", "worst", "trades"):
                self.assertIn(key, pf)
            self.assertEqual(pf["trades"], 2)
            self.assertAlmostEqual(sum(a["pct"] for a in pf["allocation"]), 1.0, places=6)
            time.sleep(0.3)
            status, body, _ = c.get("/api/history?limit=10")
            self.assertEqual(status, 200, body)
            h = json.loads(body)
            self.assertEqual([e["kind"] for e in h["events"]][:2], ["sell", "buy"])
            self.assertEqual(h["source"], "ledger")
            time.sleep(0.3)
            status, body, _ = c.get("/api/history?kind=buy")
            self.assertEqual({e["kind"] for e in json.loads(body)["events"]}, {"buy"})
            time.sleep(0.3)
            status, body, headers = c.get("/api/history.csv")
            self.assertEqual(status, 200)
            self.assertIn("text/csv", headers.get("content-type", headers.get("Content-Type", "")))
            self.assertIn("attachment", headers.get("content-disposition", headers.get("Content-Disposition", "")))
            lines = body.strip().splitlines()
            self.assertTrue(lines[0].startswith("time_utc,type,ticker"))
            self.assertGreaterEqual(len(lines), 4)
        finally:
            c.close()

    def test_players_cannot_read_each_others_portfolio_or_history(self):
        a, b = Client(self.srv, "PrivateA"), Client(self.srv, "PrivateB")
        try:
            a.recv_until("state")
            b.recv_until("state")
            a.send({"type": "trade", "ticker": "GOLD", "side": "buy", "pct": 0.3})
            self.assertTrue(a.recv_until("result")["ok"])
            pb = json.loads(b.get("/api/portfolio")[1])
            self.assertEqual(pb["positions"], [])
            time.sleep(0.3)
            hb = json.loads(b.get("/api/history")[1])
            self.assertNotIn("buy", [e["kind"] for e in hb["events"]])
        finally:
            a.close()
            b.close()

    def test_lookups_are_rate_limited(self):
        c = Client(self.srv, "Hammer")
        try:
            c.recv_until("state")
            codes = [c.get("/api/me")[0] for _ in range(6)]
            self.assertEqual(codes[0], 200)
            self.assertIn(429, codes)
            time.sleep(0.4)
            self.assertEqual(c.get("/api/me")[0], 200)
        finally:
            c.close()

    # ------------------------------------------------------------------ social over HTTP
    def test_me_and_boards_shapes(self):
        c = Client(self.srv, "MeShape")
        try:
            c.recv_until("state")
            me = json.loads(c.get("/api/me")[1])
            for key in ("achievements", "quests", "tournaments", "following", "public", "rank", "unlocked"):
                self.assertIn(key, me)
            self.assertEqual(len(me["quests"]["quests"]), 3)
            self.assertEqual({t["kind"] for t in me["tournaments"]["active"]}, {"marathon"})
            time.sleep(0.3)
            b = json.loads(c.get("/api/boards")[1])
            for key in ("season", "pnl", "mine"):
                self.assertIn(key, b)
            self.assertNotIn("risk", b)
            self.assertNotIn(c.token, json.dumps(b))
        finally:
            c.close()

    def test_tournament_join_over_http(self):
        c = Client(self.srv, "TourneyJoin")
        try:
            c.recv_until("state")
            me = json.loads(c.get("/api/me")[1])
            time.sleep(0.6)
            bad = json.loads(c.post("/api/tournament/join", {"id": "nothing"})[1])
            self.assertFalse(bad["ok"])
            open_now = [t for t in me["tournaments"]["active"] if t["open"]]
            if not open_now:                      # entry windows close part-way through each tournament
                return
            t = open_now[0]
            time.sleep(0.6)
            ok = json.loads(c.post("/api/tournament/join", {"id": t["id"]})[1])
            self.assertTrue(ok["ok"], ok)
            time.sleep(0.6)
            again = json.loads(c.post("/api/tournament/join", {"id": t["id"]})[1])
            self.assertFalse(again["ok"])
            time.sleep(0.3)
            mine = json.loads(c.get("/api/me")[1])
            joined = next(x for x in mine["tournaments"]["active"] if x["id"] == t["id"])
            self.assertTrue(joined["joined"])
            self.assertEqual(joined["mine"]["rank"], 1)
            self.assertEqual(joined["mine"]["account"]["cash"], 10000.0)
            # a paper trade over the socket (the real balance is left alone: see test_contests)
            c.send({"type": "contest_trade", "id": t["id"], "ticker": "GOLD", "side": "buy", "pct": 0.5})
            res = c.recv_until("result")
            self.assertTrue(res["ok"], res)
            self.assertTrue(res["contest"])
            c.send({"type": "contest_trade", "id": "nothing", "ticker": "GOLD", "side": "buy", "pct": 0.5})
            self.assertFalse(c.recv_until("result")["ok"])
            time.sleep(0.4)
            after = json.loads(c.get("/api/me")[1])
            acct = next(x for x in after["tournaments"]["active"] if x["id"] == t["id"])["mine"]["account"]
            self.assertEqual([r["ticker"] for r in acct["positions"]], ["GOLD"])
            self.assertAlmostEqual(acct["cash"], 5000.0, places=2)
        finally:
            c.close()

    def test_profiles_follow_and_privacy_over_http(self):
        a, b = Client(self.srv, "ProfA"), Client(self.srv, "ProfB")
        try:
            a.recv_until("state")
            b.recv_until("state")
            prof = json.loads(b.get("/api/profile/profa")[1])
            self.assertEqual(prof["name"], "ProfA")
            self.assertFalse(prof["public"])
            self.assertNotIn("season_ret", prof)
            time.sleep(0.3)
            self.assertEqual(b.get("/api/profile/nobodyatall")[0], 404)
            time.sleep(0.3)
            r = json.loads(b.post("/api/follow", {"name": "ProfA"})[1])
            self.assertTrue(r["ok"], r)
            time.sleep(0.4)
            self.assertFalse(json.loads(b.post("/api/follow", {"name": "ProfA"})[1])["ok"])
            time.sleep(0.4)
            fl = json.loads(b.get("/api/following")[1])
            self.assertEqual([x["name"] for x in fl], ["ProfA"])
            r = json.loads(a.post("/api/public", {"public": True})[1])
            self.assertTrue(r["ok"])
            time.sleep(0.4)
            prof = json.loads(b.get("/api/profile/ProfA")[1])
            self.assertTrue(prof["public"])
            self.assertIn("season_ret", prof)
            self.assertEqual(prof["followers"], 1)
            time.sleep(0.4)
            self.assertTrue(json.loads(b.post("/api/unfollow", {"name": "profa"})[1])["ok"])
        finally:
            a.close()
            b.close()

    def test_the_club_endpoints_are_gone_and_chat_is_global_only(self):
        a = Client(self.srv, "NoClubA")
        try:
            a.recv_until("state")
            self.assertEqual(a.get("/api/clubs")[0], 404)
            self.assertEqual(a.post("/api/club/create", {"name": "Test Club Http"})[0], 404)
            a.send({"type": "chat", "channel": "club:anything", "text": "secret"})
            err = a.recv_until("chat_error")
            self.assertIn("global", err["msg"])
        finally:
            a.close()

    # ------------------------------------------------------------------ chat
    def test_global_chat_reaches_everyone_and_is_cleaned(self):
        a, b = Client(self.srv, "ChatA"), Client(self.srv, "ChatB")
        try:
            a.recv_until("state")
            b.recv_until("state")
            a.send({"type": "chat", "text": "hello <b>world</b> https://spam.example/x  shit"})
            m = b.recv_until("chat")["msg"]
            self.assertEqual(m["name"], "ChatA")
            self.assertEqual(m["channel"], "global")
            self.assertIn("[link]", m["text"])
            self.assertNotIn("http", m["text"])
            self.assertNotIn("shit", m["text"])
            self.assertEqual(a.recv_until("chat")["msg"]["id"], m["id"])
            late = Client(self.srv, "ChatLate")
            try:
                init = json.loads(late.ws.recv(timeout=8))
                self.assertIn(m["id"], [x["id"] for x in init["chat"]])
            finally:
                late.close()
        finally:
            a.close()
            b.close()

    def test_chat_rate_limit_and_empty_messages(self):
        a = Client(self.srv, "ChatSpam")
        try:
            a.recv_until("state")
            a.send({"type": "chat", "text": "   "})
            self.assertIn("Say something", a.recv_until("chat_error")["msg"])
            a.send({"type": "chat", "text": "one"})
            a.recv_until("chat")
            a.send({"type": "chat", "text": "two"})
            self.assertIn("Slow down", a.recv_until("chat_error")["msg"])
        finally:
            a.close()

    def test_share_a_trade_in_chat(self):
        a = Client(self.srv, "ChatShare")
        try:
            a.recv_until("state")
            a.send({"type": "trade", "ticker": "GOLD", "side": "buy", "pct": 0.1})
            self.assertTrue(a.recv_until("result")["ok"])
            status, body, _ = http(self.srv, "/api/admin/player/chatshare", headers={"X-Admin-Key": "testkey"})
            t = json.loads(body)["log"][-1]["t"]
            time.sleep(1.6)
            a.send({"type": "chat", "text": "look at my trade", "share": t})
            m = a.recv_until("chat")["msg"]
            self.assertEqual(m["share"]["ticker"], "GOLD")
            self.assertEqual(m["share"]["kind"], "buy")
        finally:
            a.close()

    def test_moderation_delete_mute_and_reports(self):
        a, b = Client(self.srv, "ModTarget"), Client(self.srv, "ModWatcher")
        admin = {"X-Admin-Key": "testkey"}
        try:
            a.recv_until("state")
            b.recv_until("state")
            self.assertEqual(http(self.srv, "/api/admin/chat")[0], 403)
            self.assertEqual(http(self.srv, "/api/admin/chat/delete", "POST", {"id": 1})[0], 403)
            self.assertEqual(http(self.srv, "/api/admin/mute", "POST", {"name": "x", "seconds": 5})[0], 403)
            a.send({"type": "chat", "text": "borderline message"})
            m = b.recv_until("chat")["msg"]
            b.send({"type": "chat_report", "id": m["id"]})
            self.assertTrue(b.recv_until("result")["ok"])
            status, body, _ = http(self.srv, "/api/admin/chat", headers=admin)
            self.assertEqual(status, 200, body)
            view = json.loads(body)
            self.assertIn(m["id"], [x["id"] for x in view["messages"]])
            self.assertIn(m["id"], [x["id"] for x in view["reports"]])
            status, body, _ = http(self.srv, "/api/admin/chat/delete", "POST", {"id": m["id"]}, admin)
            self.assertTrue(json.loads(body)["ok"])
            gone = b.recv_until("chat_delete")
            self.assertEqual(gone["id"], m["id"])
            status, body, _ = http(self.srv, "/api/admin/mute", "POST", {"name": "modtarget", "seconds": 600}, admin)
            self.assertTrue(json.loads(body)["ok"])
            time.sleep(1.6)
            a.send({"type": "chat", "text": "can I talk"})
            self.assertIn("muted", a.recv_until("chat_error")["msg"])
            http(self.srv, "/api/admin/mute", "POST", {"name": "modtarget", "seconds": 0}, admin)
            time.sleep(0.3)
            a.send({"type": "chat", "text": "back again"})
            self.assertEqual(a.recv_until("chat")["msg"]["text"], "back again")
        finally:
            a.close()
            b.close()

    def test_three_reports_remove_a_message_mute_its_author_and_an_appeal_can_lift_it(self):
        admin = {"X-Admin-Key": "testkey"}
        bad = Client(self.srv, "AutoBad")
        watchers = [Client(self.srv, f"AutoW{i}") for i in range(3)]
        try:
            bad.recv_until("state")
            for w in watchers:
                w.recv_until("state")
            bad.send({"type": "chat", "text": "an unkind message"})
            m = watchers[0].recv_until("chat")["msg"]
            for w in watchers:
                w.send({"type": "chat_report", "id": m["id"]})
                self.assertTrue(w.recv_until("result")["ok"])
            self.assertEqual(watchers[1].recv_until("chat_delete")["id"], m["id"])      # every page drops it
            time.sleep(1.6)
            bad.send({"type": "chat", "text": "hello?"})
            self.assertIn("muted", bad.recv_until("chat_error")["msg"])
            bad.send({"type": "chat_appeal", "text": "that was a joke between friends"})
            self.assertTrue(bad.recv_until("result")["ok"])
            view = json.loads(http(self.srv, "/api/admin/chat", headers=admin)[1])
            appeal = next(a for a in view["appeals"] if a["name"] == "AutoBad")
            self.assertNotIn("token", appeal)
            self.assertTrue(any(l["action"] == "mute" and l["actor"] == "auto" for l in view["mod_log"]))
            self.assertEqual(http(self.srv, "/api/admin/appeal", "POST", {"id": appeal["id"], "decision": "lift"})[0], 403)
            status, body, _ = http(self.srv, "/api/admin/appeal", "POST", {"id": appeal["id"], "decision": "lift"}, admin)
            self.assertTrue(json.loads(body)["ok"])
            time.sleep(1.6)
            bad.send({"type": "chat", "text": "thanks"})
            self.assertEqual(bad.recv_until("chat")["msg"]["text"], "thanks")
        finally:
            bad.close()
            for w in watchers:
                w.close()

    # ------------------------------------------------------------------ threading
    def test_requests_during_ticks_do_not_stall_the_game(self):
        """A burst of lookups and trades from many clients must not make ticks late (the engine runs in worker
        threads, not on the event loop)."""
        import threading
        clients = [Client(self.srv, f"Burst{i:02d}") for i in range(10)]
        stop = time.time() + 6
        errors = []

        def hammer(c):
            try:
                n = 0
                while time.time() < stop:
                    c.send({"type": "history", "ticker": "NVXA", "period": "1m"})
                    c.send({"type": "company", "ticker": "CLDR"})
                    if n % 4 == 0:
                        c.send({"type": "trade", "ticker": "GOLD", "side": "buy" if n % 8 == 0 else "sell", "pct": 0.05})
                    n += 1
                    time.sleep(0.25)
                    http(self.srv, "/api/admin/stats", headers={"X-Admin-Key": "testkey"})
            except Exception as e:
                errors.append(repr(e))
        try:
            for c in clients:
                c.recv_until("state")
            threads = [threading.Thread(target=hammer, args=(c,)) for c in clients]
            for t in threads:
                t.start()
            seqs = []
            while time.time() < stop:
                for c in clients[:3]:
                    try:
                        m = json.loads(c.ws.recv(timeout=0.5))
                        if m["type"] == "tick":
                            seqs.append(m["seq"])
                    except Exception:
                        pass
            for t in threads:
                t.join()
            self.assertFalse(errors, errors)
            self.assertGreaterEqual(len(seqs), 8)
            status, body, _ = http(self.srv, "/api/admin/overview", headers={"X-Admin-Key": "testkey"})
            perf = json.loads(body)["perf"]
            self.assertLess(perf["tick_ms"], 300, perf)
            self.assertLessEqual(perf["late_ticks"], 1, perf)
        finally:
            for c in clients:
                c.close()

    def test_admin_overview_reports_server_performance(self):
        status, body, _ = http(self.srv, "/api/admin/overview", headers={"X-Admin-Key": "testkey"})
        perf = json.loads(body)["perf"]
        for key in ("tick_ms", "tick_max_ms", "send_ms", "late_ticks", "ticks"):
            self.assertIn(key, perf)
        self.assertGreater(perf["ticks"], 0)

    def test_the_server_stays_healthy(self):
        """No traceback may pass through our own code. (Windows asyncio prints a harmless ConnectionResetError
        trace when a client drops its socket; it never touches engine.py or server.py.)"""
        time.sleep(1)
        log = self.srv.log()
        for block in log.split("Traceback (most recent call last):")[1:]:
            trace = block.split("\n\n")[0]
            self.assertNotIn("engine.py", trace, trace)
            self.assertNotIn("server.py", trace, trace)
            self.assertNotIn("gateway.py", trace, trace)


if __name__ == "__main__":
    unittest.main()
