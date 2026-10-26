"""/api/health: the address an outside uptime monitor checks. 200 while the game is ticking and saving, nothing secret in it,
and the same through a gateway."""
import json
import time
import types
import unittest

from _helpers import IsolatedServer
from test_server import http


class HealthTests(unittest.TestCase):
    def check(self, srv):
        status, text, headers = http(srv, "/api/health")
        self.assertEqual(status, 200, text)
        d = json.loads(text)
        self.assertTrue(d["ok"])
        self.assertLess(d["tick_age_s"], 5)                           # the game ticked a moment ago
        self.assertGreaterEqual(d["uptime_s"], 0)
        self.assertEqual(set(d), {"ok", "tick_age_s", "saved_ago_s", "uptime_s"})        # nothing else is in it
        self.assertIn("no-store", {k.lower(): v for k, v in headers.items()}.get("cache-control", ""))
        return d

    def test_it_answers_200_without_any_key_while_the_game_ticks(self):
        with IsolatedServer() as srv:
            self.check(srv)
            time.sleep(3)
            d = self.check(srv)
            self.assertGreaterEqual(d["uptime_s"], 3)

    def test_it_is_not_one_of_the_admin_paths_so_a_monitor_is_never_locked_out(self):
        with IsolatedServer() as srv:
            for i in range(12):                                                     # more wrong admin keys than the lock-out allows
                http(srv, "/api/admin/overview", headers={"X-Admin-Key": "wrong%d" % i})
            self.check(srv)

    def test_it_works_through_a_gateway(self):
        with IsolatedServer(gateways=1) as srv:
            self.check(types.SimpleNamespace(url=f"http://127.0.0.1:{srv.gateway_ports[0]}"))


if __name__ == "__main__":
    unittest.main()
