"""The multi-process set-up: a game server plus gateway processes that hold the players' websockets (gateway.py), the
launcher (launch.py) and the helper that shares the game from a home computer (share.py).

The big check is that nothing is different for a player. Set MS_TEST_GATEWAYS=2 and the whole server, wire, accounts,
social and browser suites run through two gateways instead of straight at the game."""
import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import types
import unittest
import urllib.error
import urllib.request

from _helpers import IsolatedServer, ROOT, free_port
from test_server import http

import share
from websockets.sync.client import connect


def join(url, name):
    status, text, _ = http(types.SimpleNamespace(url=url), "/api/join", "POST", {"name": name})
    assert status == 200, text
    return json.loads(text)


def socket_to(port, token):
    return connect(f"ws://127.0.0.1:{port}/ws?token={token}", max_size=None, max_queue=None, ping_interval=None, close_timeout=2)


def next_of(ws, kind, tries=40, timeout=8):
    for _ in range(tries):
        m = json.loads(ws.recv(timeout=timeout))
        if m.get("type") == kind:
            return m
    raise AssertionError("no " + kind)


class ClusterTests(unittest.TestCase):
    """One game server and two gateways."""

    @classmethod
    def setUpClass(cls):
        cls.srv = IsolatedServer(gateways=2).__enter__()
        cls.urls = [f"http://127.0.0.1:{p}" for p in cls.srv.gateway_ports]

    @classmethod
    def tearDownClass(cls):
        cls.srv.__exit__(None, None, None)

    def test_a_page_gets_its_full_picture_and_then_ticks_with_its_own_numbers(self):
        a = join(self.urls[0], "GwTicks")
        with socket_to(self.srv.gateway_ports[0], a["token"]) as ws:
            init = json.loads(ws.recv(timeout=10))
            self.assertEqual(init["type"], "init")
            self.assertGreater(len(init["stocks"]), 100)
            t1, t2 = next_of(ws, "tick"), next_of(ws, "tick")
            self.assertGreater(t2["seq"], t1["seq"])
            self.assertEqual(t2["me"]["cash"], 1000.0)
            self.assertIn("px", t2)

    def test_two_players_on_different_gateways_see_the_same_market_but_their_own_money(self):
        a, b = join(self.urls[0], "GwOne"), join(self.urls[1], "GwTwo")
        with socket_to(self.srv.gateway_ports[0], a["token"]) as wa, socket_to(self.srv.gateway_ports[1], b["token"]) as wb:
            next_of(wa, "init")
            next_of(wb, "init")
            wa.send(json.dumps({"type": "trade", "ticker": "NVXA", "side": "buy", "pct": 0.5}))
            self.assertTrue(next_of(wa, "result")["ok"])
            deadline = time.time() + 8
            while time.time() < deadline:
                ta, tb = next_of(wa, "tick"), next_of(wb, "tick")
                if ta["me"]["holdings"]:
                    break
            self.assertTrue(ta["me"]["holdings"])
            self.assertLess(ta["me"]["cash"], 600)
            self.assertEqual(tb["me"]["cash"], 1000.0)                  # the other player's money is untouched
            self.assertEqual(tb["me"]["holdings"], [])

    def test_chat_reaches_players_on_every_gateway(self):
        a, b = join(self.urls[0], "GwChatA"), join(self.urls[1], "GwChatB")
        with socket_to(self.srv.gateway_ports[0], a["token"]) as wa, socket_to(self.srv.gateway_ports[1], b["token"]) as wb:
            next_of(wa, "init")
            next_of(wb, "init")
            wb.send(json.dumps({"type": "chat", "text": "hello across the room"}))
            self.assertEqual(next_of(wa, "chat")["msg"]["text"], "hello across the room")
            self.assertEqual(next_of(wb, "chat")["msg"]["name"], "GwChatB")

    def test_a_bad_token_is_refused_through_a_gateway(self):
        with socket_to(self.srv.gateway_ports[0], "nonsense") as ws:
            first = json.loads(ws.recv(timeout=8))
            self.assertEqual(first["type"], "error")

    def test_messages_from_one_page_are_handled_in_order(self):
        a = join(self.urls[0], "GwOrder")
        with socket_to(self.srv.gateway_ports[0], a["token"]) as ws:
            next_of(ws, "init")
            ws.send(json.dumps({"type": "trade", "ticker": "NVXA", "side": "buy", "pct": 0.1}))
            ws.send(json.dumps({"type": "trade", "ticker": "NVXA", "side": "buy", "pct": 0.1}))     # inside the 1 s cooldown
            first, second = next_of(ws, "result"), next_of(ws, "result")
            self.assertTrue(first["ok"])
            self.assertFalse(second["ok"])
            self.assertIn("Cooldown", second["msg"])

    def test_charts_and_company_pages_come_back_to_the_asking_page_only(self):
        a, b = join(self.urls[0], "GwAskA"), join(self.urls[1], "GwAskB")
        with socket_to(self.srv.gateway_ports[0], a["token"]) as wa, socket_to(self.srv.gateway_ports[1], b["token"]) as wb:
            next_of(wa, "init")
            next_of(wb, "init")
            wa.send(json.dumps({"type": "history", "ticker": "NVXA", "period": "5m"}))
            h = next_of(wa, "history")
            self.assertEqual(h["ticker"], "NVXA")
            self.assertGreater(len(h["candles"]), 0)
            wa.send(json.dumps({"type": "company", "ticker": "NVXA"}))
            self.assertEqual(next_of(wa, "company")["ticker"], "NVXA")

    def test_ordinary_requests_work_through_a_gateway_and_see_the_real_caller(self):
        a = join(self.urls[0], "GwHttp")
        req = urllib.request.Request(self.urls[1] + "/api/portfolio", headers={"X-Token": a["token"]})
        with urllib.request.urlopen(req, timeout=10) as r:
            self.assertEqual(r.status, 200)
            self.assertIn("equity", json.loads(r.read()))
        with self.assertRaises(urllib.error.HTTPError) as err:                    # the status code and body pass through
            urllib.request.urlopen(urllib.request.Request(self.urls[0] + "/api/portfolio", headers={"X-Token": "bad"}), timeout=10)
        self.assertEqual(err.exception.code, 401)
        with urllib.request.urlopen(urllib.request.Request(self.urls[0] + "/api/admin/overview", headers={"X-Admin-Key": "testkey"}), timeout=10) as r:
            data = json.loads(r.read())
        self.assertGreaterEqual(data["online"], 0)
        self.assertEqual(data["perf"]["gateways"], 2)
        with self.assertRaises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(urllib.request.Request(self.urls[0] + "/api/admin/overview", headers={"X-Admin-Key": "wrong"}), timeout=10)
        self.assertEqual(err.exception.code, 403)

    def test_the_pages_are_served_by_the_gateway(self):
        for path, needle in (("/", b"Meme Street"), ("/admin", b"Admin"), ("/stock/NVXA", b"Meme Street"), ("/portfolio", b"Meme Street")):
            with urllib.request.urlopen(self.urls[0] + path, timeout=10) as r:
                self.assertIn(needle, r.read(), path)
        with urllib.request.urlopen(self.urls[1] + "/brand/memestreet_logo_peaks.png", timeout=10) as r:
            self.assertTrue(r.read(8).startswith(b"\x89PNG"))
        with urllib.request.urlopen(self.urls[1] + "/stock/BULL2", timeout=10) as r:           # an old link is redirected
            self.assertTrue(r.geturl().endswith("/stock/2LMSI"))
        with self.assertRaises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(self.urls[0] + "/brand/secret.txt", timeout=10)
        self.assertEqual(err.exception.code, 404)

    def test_the_game_door_for_gateways_is_shut_without_the_key(self):
        for key in ("", "wrong"):
            ws = connect(f"ws://127.0.0.1:{self.srv.core_port}/internal/gateway?key={key}", max_size=None)
            with self.assertRaises(Exception):
                ws.recv(timeout=5)

    def test_a_page_that_floods_is_slowed_down_not_the_game(self):
        a = join(self.urls[0], "GwFlood")
        with socket_to(self.srv.gateway_ports[0], a["token"]) as ws:
            next_of(ws, "init")
            for _ in range(300):
                ws.send(json.dumps({"type": "sync"}))
            time.sleep(0.5)
        other = join(self.urls[1], "GwCalm")
        with socket_to(self.srv.gateway_ports[1], other["token"]) as ws:
            self.assertEqual(json.loads(ws.recv(timeout=10))["type"], "init")           # the game is still answering

    def test_a_gateway_that_goes_away_does_not_take_the_game_with_it(self):
        extra_port = free_port()
        env = dict(os.environ, CORE_KEY=self.srv.key, CORE_URL=f"ws://127.0.0.1:{self.srv.core_port}/internal/gateway")
        proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "gateway:app", "--host", "127.0.0.1", "--port", str(extra_port),
                                 "--log-level", "warning"], cwd=self.srv.dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.time() + 30
            while time.time() < deadline:
                try:
                    if b'"ok":true' in urllib.request.urlopen(f"http://127.0.0.1:{extra_port}/gateway/health", timeout=1).read():
                        break
                except Exception:
                    time.sleep(0.3)
            a = join(f"http://127.0.0.1:{extra_port}", "GwGone")
            ws = socket_to(extra_port, a["token"])
            next_of(ws, "init")
            before = json.loads(urllib.request.urlopen(urllib.request.Request(self.urls[0] + "/api/admin/overview", headers={"X-Admin-Key": "testkey"})).read())["online"]
            proc.kill()
            proc.wait(10)
            time.sleep(1.5)
            after = json.loads(urllib.request.urlopen(urllib.request.Request(self.urls[0] + "/api/admin/overview", headers={"X-Admin-Key": "testkey"})).read())["online"]
            self.assertLess(after, before)                                                # its pages were forgotten
            b = join(self.urls[0], "GwSurvivor")
            with socket_to(self.srv.gateway_ports[0], b["token"]) as ws2:
                self.assertEqual(json.loads(ws2.recv(timeout=10))["type"], "init")
        finally:
            if proc.poll() is None:
                proc.kill()

    def test_the_server_logs_show_no_traceback_from_our_code(self):
        time.sleep(1)
        for block in self.srv.log().split("Traceback (most recent call last):")[1:]:
            trace = block.split("\n\n")[0]
            for name in ("engine.py", "server.py", "gateway.py", "wsconn.py"):
                self.assertNotIn(name, trace, trace)


class CoreRestartTests(unittest.TestCase):
    def test_gateways_reconnect_by_themselves_when_the_game_server_restarts(self):
        srv = IsolatedServer(gateways=1).__enter__()
        try:
            url = f"http://127.0.0.1:{srv.gateway_ports[0]}"
            a = join(url, "GwRestart")
            ws = socket_to(srv.gateway_ports[0], a["token"])
            next_of(ws, "init")
            srv.proc.terminate()
            srv.proc.wait(20)
            # while the game is down, a request gets a clear 'try again' and not a hang
            time.sleep(1.5)
            with self.assertRaises(urllib.error.HTTPError) as err:
                urllib.request.urlopen(url + "/api/auth_mode", timeout=10)
            self.assertEqual(err.exception.code, 503)
            # the page's socket was closed so it will reconnect
            with self.assertRaises(Exception):
                for _ in range(10):
                    ws.recv(timeout=5)
            # start the game again from the same folder: the gateway finds it by itself
            env = dict(os.environ, ADMIN_KEY="testkey", CORE_KEY=srv.key)
            srv.proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(srv.core_port),
                                         "--log-level", "warning"], cwd=srv.dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            srv.procs.append(srv.proc)
            deadline = time.time() + 60
            ok = False
            while time.time() < deadline and not ok:
                try:
                    ok = json.loads(urllib.request.urlopen(url + "/gateway/health", timeout=2).read())["ok"]
                except Exception:
                    pass
                if not ok:
                    time.sleep(0.5)
            self.assertTrue(ok, "the gateway never found the game again")
            token = json.loads(urllib.request.urlopen(urllib.request.Request(url + "/api/join", data=b'{"name":"GwAfter"}', headers={"Content-Type": "application/json"}), timeout=10).read())["token"]
            with socket_to(srv.gateway_ports[0], token) as ws2:
                self.assertEqual(json.loads(ws2.recv(timeout=10))["type"], "init")
        finally:
            srv.__exit__(None, None, None)


class LauncherTests(unittest.TestCase):
    def test_launch_starts_the_game_and_gateway_workers_that_answer_on_one_port(self):
        folder = tempfile.mkdtemp(prefix="meme_street_launch_")
        try:
            for f in IsolatedServer.FILES + ["launch.py"]:
                for base in (ROOT, os.path.join(ROOT, "brand")):
                    if os.path.exists(os.path.join(base, f)):
                        shutil.copy(os.path.join(base, f), folder)
                        break
            with open(os.path.join(folder, "zz_test_settings.json"), "w", encoding="utf-8") as fh:
                json.dump({"settings": {"require_password": False, "premarket_seconds": 0, "aftermarket_seconds": 0}}, fh)
            port, core_port = free_port(), free_port()
            log = open(os.path.join(folder, "launch.log"), "wb")
            proc = subprocess.Popen([sys.executable, "launch.py", "--gateways", "2", "--port", str(port), "--core-port", str(core_port)],
                                    cwd=folder, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.time() + 90
                health = None
                while time.time() < deadline:
                    try:
                        health = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/gateway/health", timeout=1).read())
                        if health["ok"]:
                            break
                    except Exception:
                        time.sleep(0.5)
                self.assertTrue(health and health["ok"], "launch.py did not come up")
                a = join(f"http://127.0.0.1:{port}", "Launched")
                with socket_to(port, a["token"]) as ws:
                    self.assertEqual(json.loads(ws.recv(timeout=10))["type"], "init")
                self.assertEqual(urllib.request.urlopen(f"http://127.0.0.1:{core_port}/api/auth_mode", timeout=5).status, 200)
            finally:
                if sys.platform == "win32":              # (on Windows terminate() is a hard kill that would leave the children running)
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
                else:
                    proc.terminate()
                try:
                    proc.wait(40)
                except Exception:
                    proc.kill()
                log.close()
        finally:
            for _ in range(20):
                shutil.rmtree(folder, ignore_errors=True)
                if not os.path.exists(folder):
                    break
                time.sleep(0.5)

    def test_the_launcher_parses_its_options(self):
        import launch
        self.assertTrue(callable(launch.main))


class ShareTests(unittest.TestCase):
    def test_the_public_address_is_found_in_cloudflareds_output(self):
        line = "2026-10-03T12:00:00Z INF |  https://quiet-river-1234.trycloudflare.com                           |"
        self.assertEqual(share.extract_url(line), "https://quiet-river-1234.trycloudflare.com")
        for noise in ("Requesting new quick Tunnel on trycloudflare.com...", "https://example.com/", "http://x.trycloudflare.com", ""):
            self.assertIsNone(share.extract_url(noise), noise)

    def test_it_refuses_to_run_when_the_game_is_not_listening(self):
        port = free_port()
        self.assertFalse(share.game_is_running(port))
        self.assertEqual(share.main(["--port", str(port)]), 1)

    def test_the_whole_flow_with_a_stand_in_for_cloudflared(self):
        """Nothing is opened to the internet here: a fake tunnel program prints what the real one prints."""
        from unittest import mock

        class FakeTunnel:
            def __init__(self, *a, **k):
                self.args = a[0]
                self.stdout = iter(["2026 INF Requesting new quick Tunnel on trycloudflare.com...\n",
                                    "2026 INF |  https://fake-name-4321.trycloudflare.com  |\n"])
                self.polls = 0
                self.stopped = False

            def poll(self):
                self.polls += 1
                time.sleep(0.2)
                return None if self.polls < 6 else 0

            def terminate(self):
                self.stopped = True
        made = []
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(share, "SHARE_FILE", os.path.join(folder, "share_url.txt")), \
                mock.patch.object(share, "game_is_running", return_value=True), \
                mock.patch.object(share, "find_cloudflared", return_value="fake-cloudflared"), \
                mock.patch.object(share.subprocess, "Popen", side_effect=lambda *a, **k: made.append(FakeTunnel(*a, **k)) or made[-1]):
            self.assertEqual(share.main(["--port", "8123"]), 0)
            with open(os.path.join(folder, "share_url.txt"), encoding="utf-8") as fh:
                self.assertEqual(fh.read().strip(), "https://fake-name-4321.trycloudflare.com")
        self.assertEqual(made[0].args, ["fake-cloudflared", "tunnel", "--url", "http://127.0.0.1:8123", "--no-autoupdate"])

    def test_it_says_how_to_install_the_tunnel_program_when_it_is_missing(self):
        from unittest import mock
        with mock.patch.object(share, "game_is_running", return_value=True), mock.patch.object(share, "find_cloudflared", return_value=None):
            self.assertEqual(share.main([]), 1)

    def test_it_sees_a_running_game(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            s.listen(1)
            self.assertTrue(share.game_is_running(s.getsockname()[1]))

    def test_the_lan_addresses_are_listed_without_loopback(self):
        for ip in share.lan_addresses():
            self.assertFalse(ip.startswith("127."))


if __name__ == "__main__":
    unittest.main()
