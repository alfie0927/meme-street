"""Accounts: passwords that are stored only as slow salted hashes, login sessions, limits on sign-ups and failed logins,
admin password resets, and the flags that show one person running several accounts."""
import json
import os
import random
import tempfile
import time
import unittest

from _helpers import IsolatedServer, drift, engine, join, make_engine
from test_server import Client, http

import accounts

GOOD = "correct-horse-battery"


class PasswordTests(unittest.TestCase):
    def test_a_password_checks_out_and_a_wrong_one_does_not(self):
        rec = accounts.hash_password(GOOD)
        self.assertTrue(accounts.verify_password(GOOD, rec))
        self.assertFalse(accounts.verify_password(GOOD + "x", rec))
        self.assertFalse(accounts.verify_password("", rec))

    def test_the_password_itself_is_not_in_the_record_and_each_hash_has_its_own_salt(self):
        a, b = accounts.hash_password(GOOD), accounts.hash_password(GOOD)
        self.assertNotIn(GOOD, json.dumps(a))
        self.assertNotEqual(a["s"], b["s"])
        self.assertNotEqual(a["h"], b["h"])

    def test_broken_records_never_verify(self):
        for rec in (None, {}, {"s": "zz", "h": "00"}, {"s": "00", "h": 5}, "text"):
            self.assertFalse(accounts.verify_password(GOOD, rec))
        self.assertFalse(accounts.verify_password(GOOD, accounts.DUMMY_RECORD))

    def test_the_cost_is_slow_enough_to_make_guessing_expensive(self):
        t = time.perf_counter()
        accounts.hash_password(GOOD)
        self.assertGreater(time.perf_counter() - t, 0.01)

    def test_password_rules(self):
        self.assertIsNone(accounts.password_problem(GOOD, "alice"))
        self.assertIn("at least", accounts.password_problem("short1", "alice"))
        self.assertIn("at most", accounts.password_problem("x" * 129, "alice"))
        self.assertIn("easy to guess", accounts.password_problem("password", "alice"))
        self.assertIn("easy to guess", accounts.password_problem("aaaaaaaaaa", "alice"))
        self.assertIn("name", accounts.password_problem("alice1234", "alice1234"))
        self.assertIsNotNone(accounts.password_problem(None, "alice"))

    def test_reserved_names(self):
        for bad in ("admin", "Moderator", "House", "memestreet"):
            self.assertIsNotNone(accounts.name_problem(bad), bad)
        self.assertIsNone(accounts.name_problem("alice"))
        self.assertIsNone(accounts.name_problem("robotics"))


class LimiterTests(unittest.TestCase):
    def test_events_count_inside_the_window_only(self):
        lim = accounts.Limiter()
        for t in (0, 10, 20):
            lim.add("k", t)
        self.assertEqual(lim.count("k", 100, 30), 3)
        self.assertEqual(lim.count("k", 100, 105), 2)           # the one at 0 has aged out
        self.assertEqual(lim.count("k", 100, 500), 0)
        self.assertEqual(lim.count("other", 100, 30), 0)

    def test_retry_after_and_clear(self):
        lim = accounts.Limiter()
        lim.add("k", 100)
        self.assertEqual(lim.retry_after("k", 900, 400), 600)
        lim.clear("k")
        self.assertEqual(lim.count("k", 900, 400), 0)

    def test_it_cannot_grow_without_bound(self):
        lim = accounts.Limiter()
        for i in range(25000):
            lim.add(("ip", i), i)
        self.assertLess(len(lim.hits), 21000)


class EngineAccountTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(1)
        self.rec = accounts.hash_password(GOOD)

    def reg(self, name, ip="1.2.3.4"):
        p, err = self.e.register(name, self.rec, ip)
        self.assertIsNotNone(p, err)
        return p

    def test_register_makes_an_account_with_the_signup_credit_and_a_password(self):
        p = self.reg("alice")
        self.assertEqual(p.pw, self.rec)
        self.assertEqual(p.cash, 1000.0)
        self.assertGreater(p.created, 0)
        self.assertLess(abs(drift(self.e)), 1e-6)

    def test_names_must_be_unique_and_not_reserved(self):
        self.reg("alice")
        self.assertIn("taken", self.e.register("ALICE", self.rec)[1])
        self.assertIn("reserved", self.e.register("admin", self.rec)[1])
        self.assertIn("2-16", self.e.register("x", self.rec)[1])

    def test_an_address_is_stored_only_as_a_salted_tag(self):
        p = self.reg("alice", "203.0.113.9")
        self.assertEqual(len(p.ips), 1)
        self.assertNotIn("203.0.113.9", p.ips[0])
        self.assertEqual(p.ips[0], self.e.ip_tag("203.0.113.9"))
        self.assertNotEqual(self.e.ip_tag("203.0.113.9"), self.e.ip_tag("203.0.113.10"))

    def test_a_session_token_finds_the_player_and_is_not_the_accounts_own_token(self):
        p = self.reg("alice")
        s = self.e.new_session(p, "1.2.3.4")
        self.assertIs(self.e.player_for(s), p)
        self.assertNotEqual(s, p.token)
        self.assertNotIn(s, json.dumps(self.e.sessions))             # only its hash is kept
        self.assertIsNone(self.e.player_for("nonsense"))
        self.assertIsNone(self.e.player_for(""))

    def test_the_old_permanent_token_works_only_for_accounts_without_a_password(self):
        legacy = join(self.e, "oldtimer")
        self.assertIs(self.e.player_for(legacy.token), legacy)
        modern = self.reg("alice")
        self.assertIsNone(self.e.player_for(modern.token))
        legacy.pw = self.rec                                           # once they set one, the old token stops working
        self.assertIsNone(self.e.player_for(legacy.token))

    def test_sessions_expire_after_thirty_days_of_not_being_used(self):
        p = self.reg("alice")
        s = self.e.new_session(p)
        self.e.now += 29 * 86400
        self.assertIs(self.e.player_for(s), p)                        # and using it keeps it alive
        self.e.now += 29 * 86400
        self.assertIs(self.e.player_for(s), p)
        self.e.now += 31 * 86400
        self.assertIsNone(self.e.player_for(s))

    def test_an_account_keeps_at_most_ten_sessions_and_the_oldest_ends(self):
        p = self.reg("alice")
        tokens = []
        for _ in range(12):
            self.e.now += 1
            tokens.append(self.e.new_session(p))
        self.assertEqual(sum(1 for v in self.e.sessions.values() if v["p"] == p.token), accounts.MAX_SESSIONS)
        self.assertIsNone(self.e.player_for(tokens[0]))
        self.assertIs(self.e.player_for(tokens[-1]), p)

    def test_ending_one_session_or_all_but_one(self):
        p = self.reg("alice")
        a, b, c = (self.e.new_session(p) for _ in range(3))
        self.assertTrue(self.e.end_session(a))
        self.assertFalse(self.e.end_session(a))
        self.assertIsNone(self.e.player_for(a))
        self.assertEqual(self.e.end_all_sessions(p, keep=b), 1)
        self.assertIs(self.e.player_for(b), p)
        self.assertIsNone(self.e.player_for(c))

    def test_an_admin_reset_changes_the_password_and_ends_every_session(self):
        p = self.reg("alice")
        s = self.e.new_session(p)
        new = accounts.hash_password("a-brand-new-one")
        self.assertIs(self.e.reset_password("ALICE", new), p)
        self.assertIsNone(self.e.player_for(s))
        self.assertTrue(accounts.verify_password("a-brand-new-one", p.pw))
        self.assertIsNone(self.e.reset_password("nobody", new))

    def test_password_record_lookup_ignores_case_and_accounts_without_one(self):
        p = self.reg("alice")
        join(self.e, "nopass")
        self.assertEqual(self.e.password_record("  Alice "), (p.token, self.rec))
        self.assertEqual(self.e.password_record("nopass"), (None, None))
        self.assertEqual(self.e.password_record("ghost"), (None, None))

    def test_accounts_from_the_same_address_are_flagged(self):
        self.reg("twin1", "9.9.9.9")
        self.reg("twin2", "9.9.9.9")
        self.reg("loner", "8.8.8.8")
        stats = self.e.account_stats()
        self.assertEqual([g["names"] for g in stats["shared_address"]], [["twin1", "twin2"]])
        self.assertEqual(stats["accounts"], 3)
        self.assertEqual(stats["with_password"], 3)

    def test_logging_in_from_a_new_address_adds_a_tag_up_to_five(self):
        p = self.reg("alice", "1.1.1.1")
        for i in range(8):
            self.e.new_session(p, f"2.2.2.{i}")
        self.assertEqual(len(p.ips), 5)

    def test_me_tells_the_page_whether_it_has_a_password(self):
        p = self.reg("alice")
        self.e.new_session(p)
        self.assertEqual(self.e.me_for(p)["account"], {"has_password": True, "sessions": 1, "email": None, "email_verified": False,
                                                       "email_pending": None, "email_mode": "off"})
        self.assertFalse(self.e.me_for(join(self.e, "old"))["account"]["has_password"])


class PersistenceTests(unittest.TestCase):
    def test_passwords_sessions_and_address_tags_survive_a_restart(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(61)
            e = engine.Engine(state_file=path)
            rec = accounts.hash_password(GOOD)
            p, _ = e.register("keeper", rec, "5.5.5.5")
            s = e.new_session(p, "5.5.5.5")
            e.save()
            f = engine.Engine(state_file=path)
            p2 = next(x for x in f.players.values() if x.name == "keeper")
            self.assertEqual(p2.pw, rec)
            self.assertEqual(p2.ips, p.ips)
            self.assertIs(f.player_for(s), p2)
            self.assertEqual(f.ip_tag("5.5.5.5"), e.ip_tag("5.5.5.5"))
            self.assertTrue(accounts.verify_password(GOOD, p2.pw))
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertNotIn(GOOD, text)
            self.assertNotIn(s, text)

    def test_a_save_from_before_accounts_loads_and_everyone_is_a_legacy_account(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(62)
            e = engine.Engine(state_file=path)
            old = join(e, "oldtimer")
            e.save()
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
            d.pop("accounts", None)
            for pl in d["players"]:
                for k in ("pw", "ips", "created"):
                    pl.pop(k, None)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(d, fh)
            f = engine.Engine(state_file=path)
            p = next(x for x in f.players.values() if x.name == "oldtimer")
            self.assertIsNone(p.pw)
            self.assertIs(f.player_for(old.token), p)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = IsolatedServer(settings={"require_password": True, "signups_per_ip_hour": 1000,
                                           "login_fails_per_name": 3, "login_fails_per_ip": 1000}).__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.srv.__exit__(None, None, None)

    def post(self, path, body, token=None, admin=False):
        headers = {}
        if token:
            headers["X-Token"] = token
        if admin:
            headers["X-Admin-Key"] = "testkey"
        status, text, hdrs = http(self.srv, path, "POST", body, headers)
        try:
            data = json.loads(text)
        except ValueError:
            data = {}
        return status, data, hdrs

    def register(self, name, password=GOOD):
        status, data, _ = self.post("/api/register", {"name": name, "password": password})
        return status, data

    def test_the_name_only_join_is_closed_when_passwords_are_required(self):
        status, data, _ = self.post("/api/join", {"name": "Sneaky"})
        self.assertEqual(status, 400)
        self.assertIn("password", data["error"])

    def test_registering_gives_a_working_session_for_the_page_and_the_socket(self):
        status, data = self.register("HttpAlice")
        self.assertEqual(status, 200, data)
        token = data["token"]
        status, text, _ = http(self.srv, "/api/me", headers={"X-Token": token})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(text)["account"]["has_password"])
        from websockets.sync.client import connect
        with connect(f"ws://127.0.0.1:{self.srv.port}/ws?token={token}", max_size=None, max_queue=None,
                     ping_interval=None, close_timeout=2) as ws:
            first = json.loads(ws.recv(timeout=8))
            self.assertEqual(first["type"], "init")

    def test_weak_passwords_duplicate_and_reserved_names_are_refused(self):
        self.assertEqual(self.register("HttpWeak", "short")[0], 400)
        self.assertEqual(self.register("HttpWeak", "password")[0], 400)
        self.assertEqual(self.register("admin")[0], 400)
        self.assertEqual(self.register("HttpDup")[0], 200)
        status, data = self.register("httpdup")
        self.assertEqual(status, 400)
        self.assertIn("taken", data["error"])
        self.assertEqual(self.post("/api/register", {"name": "NoPw"}, None)[0], 422)

    def test_login_works_with_the_right_password_and_gives_the_same_answer_for_wrong_ones(self):
        self.register("HttpLogin")
        status, wrong, _ = self.post("/api/login", {"name": "HttpLogin", "password": "not-the-password"})
        self.assertEqual(status, 401)
        status2, unknown, _ = self.post("/api/login", {"name": "NoSuchPerson", "password": "not-the-password"})
        self.assertEqual(status2, 401)
        self.assertEqual(wrong, unknown)                                 # nothing reveals whether the name exists
        status, data, _ = self.post("/api/login", {"name": "httplogin", "password": GOOD})
        self.assertEqual(status, 200)
        self.assertEqual(data["name"], "HttpLogin")
        self.assertEqual(http(self.srv, "/api/me", headers={"X-Token": data["token"]})[0], 200)

    def test_logging_out_ends_only_that_session(self):
        self.register("HttpOut")
        t1 = self.post("/api/login", {"name": "HttpOut", "password": GOOD})[1]["token"]
        t2 = self.post("/api/login", {"name": "HttpOut", "password": GOOD})[1]["token"]
        self.post("/api/logout", {}, t1)
        self.assertEqual(http(self.srv, "/api/me", headers={"X-Token": t1})[0], 401)
        self.assertEqual(http(self.srv, "/api/me", headers={"X-Token": t2})[0], 200)

    def test_repeated_wrong_passwords_lock_the_name_even_against_the_right_password(self):
        self.register("HttpLock")
        for _ in range(3):
            self.assertEqual(self.post("/api/login", {"name": "HttpLock", "password": "wrong-guess-1"})[0], 401)
        status, data, hdrs = self.post("/api/login", {"name": "HttpLock", "password": GOOD})
        self.assertEqual(status, 429)
        self.assertGreater(int(hdrs.get("Retry-After", hdrs.get("retry-after", "0"))), 0)
        self.assertIn("Too many", data["error"])

    def test_the_password_can_be_changed_and_old_sessions_end(self):
        self.register("HttpChange")
        t1 = self.post("/api/login", {"name": "HttpChange", "password": GOOD})[1]["token"]
        t2 = self.post("/api/login", {"name": "HttpChange", "password": GOOD})[1]["token"]
        self.assertEqual(self.post("/api/account/password", {"current": "wrong-wrong-1", "new": "another-good-one"}, t1)[0], 401)
        self.assertEqual(self.post("/api/account/password", {"current": GOOD, "new": "short"}, t1)[0], 400)
        status, data, _ = self.post("/api/account/password", {"current": GOOD, "new": "another-good-one"}, t1)
        self.assertEqual(status, 200, data)
        fresh = data["token"]
        self.assertEqual(http(self.srv, "/api/me", headers={"X-Token": fresh})[0], 200)
        self.assertEqual(http(self.srv, "/api/me", headers={"X-Token": t1})[0], 401)
        self.assertEqual(http(self.srv, "/api/me", headers={"X-Token": t2})[0], 401)
        self.assertEqual(self.post("/api/login", {"name": "HttpChange", "password": GOOD})[0], 401)
        self.assertEqual(self.post("/api/login", {"name": "HttpChange", "password": "another-good-one"})[0], 200)

    def test_logout_everywhere_keeps_only_this_session(self):
        self.register("HttpAll")
        a = self.post("/api/login", {"name": "HttpAll", "password": GOOD})[1]["token"]
        b = self.post("/api/login", {"name": "HttpAll", "password": GOOD})[1]["token"]
        status, data, _ = self.post("/api/account/logout_all", {}, a)
        self.assertEqual(status, 200)
        self.assertEqual(http(self.srv, "/api/me", headers={"X-Token": a})[0], 200)
        self.assertEqual(http(self.srv, "/api/me", headers={"X-Token": b})[0], 401)

    def test_admin_sees_account_stats_and_can_reset_a_forgotten_password(self):
        self.assertEqual(http(self.srv, "/api/admin/accounts")[0], 403)
        self.assertEqual(self.post("/api/admin/reset_password", {"name": "x"})[0], 403)
        self.register("HttpForgot")
        self.register("HttpForgotToo")                                   # a second account from the same address
        old = self.post("/api/login", {"name": "HttpForgot", "password": GOOD})[1]["token"]
        status, data, _ = self.post("/api/admin/reset_password", {"name": "httpforgot"}, admin=True)
        self.assertEqual(status, 200, data)
        temp = data["password"]
        self.assertEqual(http(self.srv, "/api/me", headers={"X-Token": old})[0], 401)
        self.assertEqual(self.post("/api/login", {"name": "HttpForgot", "password": GOOD})[0], 401)
        self.assertEqual(self.post("/api/login", {"name": "HttpForgot", "password": temp})[0], 200)
        self.assertEqual(self.post("/api/admin/reset_password", {"name": "ghost"}, admin=True)[0], 404)
        status, text, _ = http(self.srv, "/api/admin/accounts", headers={"X-Admin-Key": "testkey"})
        stats = json.loads(text)
        self.assertGreaterEqual(stats["with_password"], 1)
        self.assertTrue(any(len(g["names"]) >= 2 for g in stats["shared_address"]))   # every test account is from 127.0.0.1
        self.assertNotIn("127.0.0.1", text)                                          # and addresses are never shown


class AddressLimitTests(unittest.TestCase):
    def test_a_flood_of_wrong_logins_from_one_address_is_cut_off(self):
        with IsolatedServer(settings={"require_password": True, "login_fails_per_ip": 8}) as srv:
            statuses = [http(srv, "/api/login", "POST", {"name": f"Nobody{i}", "password": "wrong-guess-1"})[0] for i in range(12)]
            self.assertEqual(statuses[:8], [401] * 8)
            self.assertEqual(set(statuses[8:]), {429})

    def test_one_address_can_only_make_a_few_accounts_an_hour(self):
        with IsolatedServer(settings={"require_password": True, "signups_per_ip_hour": 3}) as srv:
            statuses = []
            for i in range(5):
                statuses.append(http(srv, "/api/register", "POST", {"name": f"Limit{i}", "password": GOOD})[0])
            self.assertEqual(statuses, [200, 200, 200, 429, 429])


class LegacyAccountTests(unittest.TestCase):
    def test_an_account_made_before_passwords_can_set_one_and_then_needs_it(self):
        with IsolatedServer() as srv:                                  # name-only joining still open here
            c = Client(srv, "LegacyLou")
            try:
                c.recv_until("state")
                me = json.loads(c.get("/api/me")[1])
                self.assertFalse(me["account"]["has_password"])
                status, text, _ = http(srv, "/api/account/password", "POST", {"new": GOOD}, {"X-Token": c.token})
                self.assertEqual(status, 200, text)
                fresh = json.loads(text)["token"]
                self.assertNotEqual(fresh, c.token)
                self.assertEqual(http(srv, "/api/me", headers={"X-Token": fresh})[0], 200)
                self.assertEqual(http(srv, "/api/me", headers={"X-Token": c.token})[0], 401)     # the old token is retired
                status, text, _ = http(srv, "/api/login", "POST", {"name": "LegacyLou", "password": GOOD})
                self.assertEqual(status, 200)
            finally:
                c.close()


if __name__ == "__main__":
    unittest.main()
