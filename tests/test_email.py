"""Email on accounts: verifying an address with a code, one account per address, the "verified email required to play"
mode, password recovery by email, and the mailer itself."""
import json
import re
import threading
import time
import unittest

from _helpers import IsolatedServer, advance, engine, join, make_engine
from test_server import http

import accounts
from mailer import Mailer

GOOD = "correct-horse-battery"


class AddressTests(unittest.TestCase):
    def test_well_formed_addresses_pass_and_are_lowercased(self):
        self.assertEqual(accounts.clean_email("  Alice@Example.COM "), ("alice@example.com", None))
        for bad in ("", "alice", "alice@", "@example.com", "a b@example.com", "alice@example", "alice@@example.com",
                    "a..b@example.com", ".a@example.com", "alice@.example.com", "x" * 250 + "@example.com", None, 5):
            self.assertIsNone(accounts.clean_email(bad)[0], bad)
            self.assertTrue(accounts.clean_email(bad)[1], bad)

    def test_spellings_of_one_mailbox_share_a_canonical_form(self):
        c = accounts.canonical_email
        self.assertEqual(c("A.l.i.c.e+games@gmail.com"), "alice@gmail.com")
        self.assertEqual(c("alice@googlemail.com"), "alice@gmail.com")
        self.assertEqual(c("bob+x@example.com"), "bob@example.com")
        self.assertEqual(c("a.b@example.com"), "a.b@example.com")              # dots only count as nothing at Gmail
        self.assertNotEqual(c("alice@gmail.com"), c("alicee@gmail.com"))

    def test_throwaway_inbox_services_are_refused_and_the_admin_can_add_more(self):
        self.assertIn("disposable", accounts.email_problem("x@mailinator.com"))
        self.assertIn("disposable", accounts.email_problem("x@inbox.mailinator.com"))
        self.assertIsNone(accounts.email_problem("x@example.com"))
        self.assertIn("disposable", accounts.email_problem("x@spam.test", ["spam.test"]))

    def test_the_owner_sees_a_masked_address(self):
        self.assertEqual(accounts.mask_email("alice@example.com"), "a***@example.com")
        self.assertIsNone(accounts.mask_email(None))

    def test_codes_have_the_expected_shape(self):
        for _ in range(50):
            self.assertRegex(accounts.new_code("verify"), r"^\d{6}$")
            self.assertRegex(accounts.new_code("reset"), r"^[2-9A-HJKMNP-Z]{8}$")
        self.assertNotEqual(accounts.new_code("reset"), accounts.new_code("reset"))


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(3)
        self.p = join(self.e, "alice")

    def begin(self, p=None, addr="alice@example.com"):
        ok, msg, code, to, wait = self.e.email_begin(p or self.p, addr)
        self.assertTrue(ok, msg)
        return code

    def test_the_right_code_verifies_the_address(self):
        code = self.begin()
        self.assertEqual(self.p.email_pending, "alice@example.com")
        self.assertFalse(self.p.email_verified)
        ok, msg = self.e.email_confirm(self.p, code)
        self.assertTrue(ok, msg)
        self.assertTrue(self.p.email_verified)
        self.assertEqual(self.p.email, "alice@example.com")
        self.assertIsNone(self.p.email_pending)
        self.assertEqual(self.e.email_owner[accounts.canonical_email("alice@example.com")], self.p.token)

    def test_a_code_is_stored_only_as_a_hash(self):
        code = self.begin()
        self.assertNotIn(code, json.dumps(self.e.accounts_dump()))

    def test_a_wrong_code_is_refused_and_too_many_cancel_the_code(self):
        code = self.begin()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(4):
            self.assertEqual(self.e.email_confirm(self.p, wrong), (False, "That code is not right"))
        ok, msg = self.e.email_confirm(self.p, wrong)
        self.assertFalse(ok)
        self.assertIn("Too many", msg)
        ok, msg = self.e.email_confirm(self.p, code)                    # even the real code is dead now
        self.assertFalse(ok)
        self.assertIn("No code", msg)
        self.assertFalse(self.p.email_verified)

    def test_a_code_expires(self):
        code = self.begin()
        advance(self.e, 16 * 60)
        ok, msg = self.e.email_confirm(self.p, code)
        self.assertFalse(ok)
        self.assertIn("expired", msg)

    def test_a_code_works_once(self):
        code = self.begin()
        self.assertTrue(self.e.email_confirm(self.p, code)[0])
        self.assertFalse(self.e.email_confirm(self.p, code)[0])

    def test_spaces_and_dashes_in_a_typed_code_do_not_matter(self):
        code = self.begin()
        self.assertTrue(self.e.email_confirm(self.p, " " + code[:3] + "-" + code[3:] + " ")[0])

    def test_another_account_cannot_have_an_address_that_is_verified_elsewhere(self):
        self.assertTrue(self.e.email_confirm(self.p, self.begin())[0])
        other = join(self.e, "bob")
        for spelling in ("alice@example.com", "ALICE+spam@example.com"):
            ok, msg, *_ = self.e.email_begin(other, spelling)
            self.assertFalse(ok)
            self.assertIn("already used", msg)
        gmail = join(self.e, "carol")
        self.assertTrue(self.e.email_confirm(gmail, self.begin(gmail, "c.arol@gmail.com"))[0])
        dave = join(self.e, "dave")
        self.assertIn("already used", self.e.email_begin(dave, "carol+x@googlemail.com")[1])

    def test_an_unverified_claim_loses_to_whoever_proves_the_address_first(self):
        squatter = join(self.e, "squatter")
        self.begin(squatter)                                            # typed it but cannot read that inbox
        self.assertTrue(self.e.email_confirm(self.p, self.begin(self.p))[0])
        self.assertIsNone(squatter.email_pending)
        self.assertFalse(squatter.email_verified)

    def test_changing_address_frees_the_old_one(self):
        self.assertTrue(self.e.email_confirm(self.p, self.begin())[0])
        advance(self.e, 61)
        self.assertTrue(self.e.email_confirm(self.p, self.begin(self.p, "alice2@example.com"))[0])
        self.assertNotIn(accounts.canonical_email("alice@example.com"), self.e.email_owner)
        other = join(self.e, "bob")
        self.assertTrue(self.e.email_begin(other, "alice@example.com")[0])

    def test_codes_cannot_be_asked_for_too_often(self):
        self.begin()
        ok, msg, code, to, wait = self.e.email_begin(self.p, "alice@example.com")
        self.assertFalse(ok)
        self.assertGreater(wait, 0)
        self.assertIsNone(code)
        advance(self.e, 61)
        self.begin()                                                    # a minute later it is fine
        self.e.settings["email_sends_per_hour"] = 3
        advance(self.e, 61)
        self.begin()
        advance(self.e, 61)
        ok, msg, *_ = self.e.email_begin(self.p, "alice@example.com")
        self.assertFalse(ok)                                            # three in an hour is the limit
        self.assertIn("sent recently", msg)

    def test_a_bad_or_throwaway_address_gets_no_code(self):
        self.assertFalse(self.e.email_begin(self.p, "nonsense")[0])
        self.assertFalse(self.e.email_begin(self.p, "x@mailinator.com")[0])
        self.assertIsNone(self.p.email_pending)

    def test_resend_uses_the_waiting_address(self):
        self.assertFalse(self.e.email_resend(self.p)[0])
        self.begin()
        advance(self.e, 61)
        ok, msg, code, to, _ = self.e.email_resend(self.p)
        self.assertTrue(ok, msg)
        self.assertEqual(to, "alice@example.com")

    def test_the_admin_can_mark_an_address_verified_or_remove_it(self):
        self.begin()
        self.assertTrue(self.e.email_force_verified(self.p)[0])
        self.assertTrue(self.p.email_verified)
        self.e.email_clear(self.p)
        self.assertIsNone(self.p.email)
        self.assertFalse(self.p.email_verified)
        self.assertEqual(self.e.email_owner, {})
        self.assertFalse(self.e.email_force_verified(self.p)[0])

    def test_the_account_page_shows_only_a_masked_address(self):
        self.assertTrue(self.e.email_confirm(self.p, self.begin())[0])
        acct = self.e.me_for(self.p)["account"]
        self.assertEqual(acct["email"], "a***@example.com")
        self.assertTrue(acct["email_verified"])
        self.assertNotIn("alice@example.com", json.dumps(self.e.public_profile("alice", join(self.e, "bob"))))


class RequiredModeTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(4)
        self.p = join(self.e, "alice")

    def test_nothing_is_needed_unless_the_mode_is_required(self):
        self.assertIsNone(self.e.email_gate(self.p))
        self.assertTrue(self.e.trade(self.p, "NVXA", "buy", 0.1)[0])

    def test_required_mode_blocks_trades_orders_contests_and_chat_until_verified(self):
        self.e.settings["email_mode"] = "required"
        self.assertIn("Verify your email", self.e.trade(self.p, "NVXA", "buy", 0.1)[1])
        self.assertIn("Verify your email", self.e.place_order(self.p, "NVXA", "limit_buy", 1.0, amount=10)[1])
        self.assertFalse(self.e.post_chat(self.p, "hello there")[0])
        self.assertEqual(self.p.cash, 1000.0)
        ok, msg, code, *_ = self.e.email_begin(self.p, "alice@example.com")
        self.assertTrue(self.e.email_confirm(self.p, code)[0])
        self.assertTrue(self.e.trade(self.p, "NVXA", "buy", 0.1)[0])
        self.assertTrue(self.e.post_chat(self.p, "hello there")[0])

    def test_contests_are_closed_to_unverified_players_and_a_verified_one_can_trade_its_paper_account(self):
        e = make_engine(7)
        e.now = (int(e.now // 86400) + 1) * 86400 + 100              # early in a UTC day, when the contest is open
        e.tick(now=e.now)
        e._social_t = 0
        e._social_tick()
        tid = next(t for t in e.tournaments if t["kind"] == "marathon")["id"]
        e.settings["email_mode"] = "required"
        p = join(e, "racer")
        self.assertIn("Verify your email", e.tournament_join(p, tid)[1])
        self.assertTrue(e.email_confirm(p, e.email_begin(p, "racer@example.com")[2])[0])
        self.assertTrue(e.tournament_join(p, tid)[0])
        e.now += 2
        ok, msg = e.contest_trade(p, tid, "NVXA", "buy", 0.2)                  # the paper account is not gated a second time
        self.assertTrue(ok, msg)

    def test_bots_are_never_gated(self):
        self.e.settings["email_mode"] = "required"
        bot = engine.Player("robo", bot=True)
        self.assertIsNone(self.e.email_gate(bot))

    def test_with_no_setting_email_is_off_until_mail_is_set_up_and_a_bad_value_falls_back_to_that(self):
        self.assertEqual(self.e.email_mode(), "off")
        self.e.default_email_mode = "optional"                    # what the server does once it can really send mail
        self.assertEqual(self.e.email_mode(), "optional")
        self.e.settings["email_mode"] = "banana"
        self.assertEqual(self.e.email_mode(), "optional")
        self.e.settings["email_mode"] = "required"
        self.assertEqual(self.e.email_mode(), "required")


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(5)
        self.old = accounts.hash_password(GOOD)
        self.p, err = self.e.register("alice", self.old, "1.1.1.1")
        self.assertIsNotNone(self.p, err)

    def verify(self):
        code = self.e.email_begin(self.p, "alice@example.com")[2]
        self.assertTrue(self.e.email_confirm(self.p, code)[0])

    def test_no_code_for_an_unknown_name_or_an_unverified_address(self):
        self.assertIsNone(self.e.recovery_begin("nobody"))
        self.assertIsNone(self.e.recovery_begin("alice"))                # no address at all
        self.e.email_begin(self.p, "alice@example.com")
        self.assertIsNone(self.e.recovery_begin("alice"))                # an address nobody has proven is not trusted

    def test_a_code_resets_the_password_and_ends_every_session(self):
        self.verify()
        session = self.e.new_session(self.p)
        code, to = self.e.recovery_begin("ALICE")
        self.assertEqual(to, "alice@example.com")
        self.assertRegex(code, r"^[2-9A-Z]{8}$")
        record = accounts.hash_password("a-brand-new-one")
        p, err = self.e.recovery_finish("alice", code.lower(), record)
        self.assertIs(p, self.p, err)
        self.assertTrue(accounts.verify_password("a-brand-new-one", self.p.pw))
        self.assertIsNone(self.e.player_for(session))
        self.assertFalse(self.e.recovery_finish("alice", code, record)[0])      # one use only

    def test_wrong_codes_are_counted_and_kill_the_code(self):
        self.verify()
        code, _ = self.e.recovery_begin("alice")
        record = accounts.hash_password("a-brand-new-one")
        for _ in range(5):
            self.assertIsNone(self.e.recovery_finish("alice", "ZZZZZZZZ" if code != "ZZZZZZZZ" else "YYYYYYYY", record)[0])
        self.assertIsNone(self.e.recovery_finish("alice", code, record)[0])
        self.assertTrue(accounts.verify_password(GOOD, self.p.pw))             # the password never changed

    def test_a_reset_code_cannot_be_used_as_a_verification_code_or_the_other_way_round(self):
        self.verify()
        code, _ = self.e.recovery_begin("alice")
        self.assertFalse(self.e.email_confirm(self.p, code)[0])
        self.assertTrue(accounts.verify_password(GOOD, self.p.pw))

    def test_reset_codes_are_rate_limited(self):
        self.verify()
        self.assertIsNotNone(self.e.recovery_begin("alice"))
        self.assertIsNone(self.e.recovery_begin("alice"))                # a second one straight away is refused


class SaveTests(unittest.TestCase):
    def test_addresses_pending_codes_and_ownership_survive_a_restart(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            e = engine.Engine(state_file=path, bots=False)
            a, err = e.register("alice", accounts.hash_password(GOOD))
            b, err = e.register("bob", accounts.hash_password(GOOD))
            self.assertTrue(e.email_confirm(a, e.email_begin(a, "alice@example.com")[2])[0])
            code = e.email_begin(b, "bob@example.com")[2]
            e.save()
            e2 = engine.Engine(state_file=path, bots=False)
            a2, b2 = e2.by_token[a.token], e2.by_token[b.token]
            self.assertEqual((a2.email, a2.email_verified), ("alice@example.com", True))
            self.assertEqual((b2.email, b2.email_verified, b2.email_pending), (None, False, "bob@example.com"))
            self.assertEqual(e2.email_owner, {"alice@example.com": a.token})
            self.assertTrue(e2.email_confirm(b2, code)[0])                      # the code sent before the restart still works

    def test_a_save_from_before_email_loads(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            e = engine.Engine(state_file=path, bots=False)
            join(e, "oldtimer")
            e.save()
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            for x in data["players"]:
                for k in ("email", "email_verified", "email_pending"):
                    x.pop(k, None)
            data["accounts"].pop("mail_codes", None)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            e2 = engine.Engine(state_file=path, bots=False)
            p = next(x for x in e2.players.values() if x.name == "oldtimer")
            self.assertEqual((p.email, p.email_verified, p.email_pending), (None, False, None))

    def test_the_game_reset_keeps_addresses(self):
        e = make_engine(6)
        p = join(e, "alice")
        self.assertTrue(e.email_confirm(p, e.email_begin(p, "alice@example.com")[2])[0])
        e.reset_to_day_one()
        self.assertTrue(p.email_verified)


class MailerTests(unittest.TestCase):
    def test_a_message_is_handed_to_the_transport_off_the_calling_thread(self):
        got, caller = [], threading.get_ident()
        seen_thread = []

        def transport(msg):
            seen_thread.append(threading.get_ident())
            got.append(msg)
        m = Mailer(transport=transport, sender="Meme Street <no-reply@example.com>")
        self.assertTrue(m.send("alice@example.com", "Your code", "123456"))
        m.drain()
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["To"], "alice@example.com")
        self.assertEqual(got[0]["Subject"], "Your code")
        self.assertIn("123456", got[0].get_content())
        self.assertNotEqual(seen_thread[0], caller)
        self.assertEqual(m.recent()[0]["state"], "sent")
        self.assertNotIn("body", m.recent()[0])                         # a configured mailer never keeps the code
        self.assertEqual(m.sent, 1)

    def test_a_failing_server_is_retried_and_then_given_up_without_raising(self):
        calls = []

        def transport(msg):
            calls.append(1)
            raise OSError("connection refused")
        m = Mailer(transport=transport, retry_delays=(0.01, 0.01))
        self.assertTrue(m.send("alice@example.com", "s", "b"))
        deadline = time.time() + 5
        while time.time() < deadline and m.failed == 0:
            time.sleep(0.02)
        self.assertEqual(len(calls), 3)
        self.assertEqual(m.failed, 1)
        self.assertEqual(m.recent()[0]["state"], "failed")
        self.assertIn("refused", m.recent()[0]["error"])

    def test_a_server_that_recovers_gets_the_message_on_a_retry(self):
        calls = []

        def transport(msg):
            calls.append(1)
            if len(calls) < 2:
                raise OSError("busy")
        m = Mailer(transport=transport, retry_delays=(0.01, 0.01))
        m.send("alice@example.com", "s", "b")
        m.drain()
        self.assertEqual(m.sent, 1)
        self.assertEqual(m.failed, 0)

    def test_without_a_server_it_is_console_mode_and_keeps_the_message_for_the_admin(self):
        m = Mailer()
        self.assertFalse(m.configured)
        self.assertTrue(m.send("alice@example.com", "Your code", "123456"))
        row = m.recent()[0]
        self.assertEqual(row["state"], "console")
        self.assertIn("123456", row["body"])
        self.assertEqual(m.sent, 0)

    def test_settings_come_from_the_environment(self):
        m = Mailer.from_env({"SMTP_HOST": "smtp.example.com", "SMTP_PORT": "465", "SMTP_USER": "u", "SMTP_PASSWORD": "p",
                             "MAIL_FROM": "Meme Street <hi@example.com>"})
        self.assertTrue(m.configured)
        self.assertEqual((m.host, m.port, m.security, m.user, m.sender), ("smtp.example.com", 465, "ssl", "u", "Meme Street <hi@example.com>"))
        self.assertEqual(Mailer.from_env({"SMTP_HOST": "h"}).security, "starttls")
        self.assertFalse(Mailer.from_env({}).configured)

    def test_the_queue_has_a_ceiling(self):
        gate = threading.Event()
        m = Mailer(transport=lambda msg: gate.wait(5))
        results = [m.send("a@example.com", "s", "b") for _ in range(1100)]
        gate.set()
        self.assertIn(False, results)


class HttpEmailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = IsolatedServer(settings={"require_password": True, "signups_per_ip_hour": 1000, "email_mode": "required",
                                           "email_resend_seconds": 2, "login_fails_per_name": 50}).__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.srv.__exit__(None, None, None)

    def post(self, path, body, token=None, admin=False, headers=None):
        h = dict(headers or {})
        if token:
            h["X-Token"] = token
        if admin:
            h["X-Admin-Key"] = "testkey"
        status, text, _ = http(self.srv, path, "POST", body, h)
        try:
            return status, json.loads(text)
        except ValueError:
            return status, {}

    def mail(self):
        status, text, _ = http(self.srv, "/api/admin/mail", headers={"X-Admin-Key": "testkey"})
        self.assertEqual(status, 200)
        return json.loads(text)

    def last_code(self, to, pattern=r"\n\s+([0-9A-Z]{6,8})\n"):
        for row in self.mail()["recent"]:
            if row["to"] == to:
                return re.search(pattern, row["body"]).group(1)
        self.fail("no mail to " + to)

    def register(self, name, email, password=GOOD):
        return self.post("/api/register", {"name": name, "password": password, "email": email})

    def socket_trade(self, token):
        from websockets.sync.client import connect
        with connect(f"ws://127.0.0.1:{self.srv.port}/ws?token={token}", max_size=None, max_queue=None,
                     ping_interval=None, close_timeout=2) as ws:
            json.loads(ws.recv(timeout=8))
            ws.send(json.dumps({"type": "trade", "ticker": "NVXA", "side": "buy", "pct": 0.1}))
            for _ in range(20):
                m = json.loads(ws.recv(timeout=8))
                if m.get("type") == "result":
                    return m
        self.fail("no trade result")

    def test_the_login_box_is_told_the_mode_and_whether_mail_works(self):
        status, text, _ = http(self.srv, "/api/auth_mode")
        data = json.loads(text)
        self.assertEqual(data["email"], "required")
        self.assertFalse(data["mail_ready"])                       # the test server has no SMTP server: console mode

    def test_registering_needs_a_good_address_in_required_mode(self):
        self.assertEqual(self.register("EmNone", "")[0], 400)
        self.assertEqual(self.register("EmBad", "not-an-address")[0], 400)
        status, data = self.register("EmThrow", "x@mailinator.com")
        self.assertEqual(status, 400)
        self.assertIn("disposable", data["error"])

    def test_the_whole_flow_register_verify_trade(self):
        status, data = self.register("EmFlow", "Flow.Person@Example.com")
        self.assertEqual(status, 200, data)
        self.assertTrue(data["email_sent"])
        token = data["token"]
        self.assertIn("Verify your email", self.socket_trade(token)["msg"])         # blocked until verified
        status, me = self.post("/api/account/email/verify", {"code": "000000"}, token)
        self.assertFalse(me["ok"])
        code = self.last_code("flow.person@example.com")
        status, res = self.post("/api/account/email/verify", {"code": code}, token)
        self.assertTrue(res["ok"], res)
        info = json.loads(http(self.srv, "/api/me", headers={"X-Token": token})[1])["account"]
        self.assertTrue(info["email_verified"])
        self.assertEqual(info["email"], "f***@example.com")
        self.assertTrue(self.socket_trade(token)["ok"])

    def test_one_address_one_account_whatever_the_spelling(self):
        self.assertEqual(self.register("EmDupA", "dup.one@gmail.com")[0], 200)
        token = self.post("/api/login", {"name": "EmDupA", "password": GOOD})[1]["token"]
        self.post("/api/account/email/verify", {"code": self.last_code("dup.one@gmail.com")}, token)
        status, data = self.register("EmDupB", "dupone+x@googlemail.com")
        self.assertEqual(status, 400)
        self.assertIn("already used", data["error"])

    def test_a_player_can_add_an_address_later_and_ask_for_another_code(self):
        status, data = self.post("/api/register", {"name": "EmLate", "password": GOOD, "email": "late@example.com"})
        token = data["token"]
        status, res = self.post("/api/account/email/resend", {}, token)
        self.assertFalse(res["ok"])                                  # too soon after the first one
        time.sleep(2.2)
        status, res = self.post("/api/account/email/resend", {}, token)
        self.assertTrue(res["ok"], res)
        status, res = self.post("/api/account/email", {"email": "late2@example.com"}, token)
        self.assertIn(status, (200,))
        self.assertEqual(self.post("/api/account/email", {"email": "x"}, "nonsense")[0], 401)

    def test_forgot_password_answers_alike_and_only_mails_a_verified_address(self):
        self.assertEqual(self.register("EmForgot", "forgot.me@example.com")[0], 200)
        token = self.post("/api/login", {"name": "EmForgot", "password": GOOD})[1]["token"]
        before = len(self.mail()["recent"])
        a = self.post("/api/account/forgot", {"name": "NoSuchPlayer"})
        self.assertEqual(len(self.mail()["recent"]), before)
        b = self.post("/api/account/forgot", {"name": "EmForgot"})               # address not verified yet: nothing is sent
        self.assertEqual(len(self.mail()["recent"]), before)
        self.assertEqual(a[1], b[1])                                              # the answers cannot tell the cases apart
        self.post("/api/account/email/verify", {"code": self.last_code("forgot.me@example.com")}, token)
        time.sleep(0.1)
        c = self.post("/api/account/forgot", {"name": "emforgot"})
        self.assertEqual(c[1], a[1])
        self.assertEqual(len(self.mail()["recent"]), before + 1)
        code = self.last_code("forgot.me@example.com")
        status, bad = self.post("/api/account/recover", {"name": "EmForgot", "code": "WRONG123", "password": "a-brand-new-one"})
        self.assertEqual(status, 400)
        status, weak = self.post("/api/account/recover", {"name": "EmForgot", "code": code, "password": "short"})
        self.assertEqual(status, 400)
        status, ok = self.post("/api/account/recover", {"name": "EmForgot", "code": code, "password": "a-brand-new-one"})
        self.assertEqual(status, 200, ok)
        self.assertEqual(http(self.srv, "/api/me", headers={"X-Token": ok["token"]})[0], 200)
        self.assertEqual(http(self.srv, "/api/me", headers={"X-Token": token})[0], 401)      # the old session ended
        self.assertEqual(self.post("/api/login", {"name": "EmForgot", "password": GOOD})[0], 401)
        self.assertEqual(self.post("/api/login", {"name": "EmForgot", "password": "a-brand-new-one"})[0], 200)
        self.assertEqual(self.post("/api/account/recover", {"name": "EmForgot", "code": code, "password": "yet-another-one"})[0], 400)

    def test_the_admin_endpoints_need_the_key_and_can_verify_or_clear(self):
        self.assertEqual(http(self.srv, "/api/admin/mail")[0], 403)
        self.assertEqual(self.post("/api/admin/email", {"name": "x", "action": "verify"})[0], 403)
        self.register("EmAdmin", "admin.helped@example.com")
        status, res = self.post("/api/admin/email", {"name": "EmAdmin", "action": "verify"}, admin=True)
        self.assertTrue(res["ok"], res)
        token = self.post("/api/login", {"name": "EmAdmin", "password": GOOD})[1]["token"]
        self.assertTrue(self.socket_trade(token)["ok"])
        self.assertEqual(self.post("/api/admin/email", {"name": "Nobody", "action": "verify"}, admin=True)[0], 404)
        status, res = self.post("/api/admin/email", {"name": "EmAdmin", "action": "clear"}, admin=True)
        self.assertTrue(res["ok"])
        self.assertFalse(self.socket_trade(token)["ok"])
        data = json.loads(http(self.srv, "/api/admin/accounts", headers={"X-Admin-Key": "testkey"})[1])
        self.assertEqual(data["email_mode"], "required")
        self.assertIn("mail", data)


class ShareThroughATunnelTests(unittest.TestCase):
    """When the game is shared from a home computer through a tunnel, every visitor reaches the server from the same
    local address. The sign-up limit has to see the visitor's real address, which the tunnel passes in a header."""

    def test_the_limit_counts_each_visitor_separately_and_cannot_be_dodged_by_a_header_from_nowhere(self):
        with IsolatedServer(settings={"require_password": True, "signups_per_ip_hour": 2, "email_mode": "off"}) as srv:
            def reg(name, ip):
                status, text, _ = http(srv, "/api/register", "POST", {"name": name, "password": GOOD},
                                       {"CF-Connecting-IP": ip} if ip else {})
                return status
            self.assertEqual([reg("TunA1", "198.51.100.1"), reg("TunA2", "198.51.100.1"), reg("TunA3", "198.51.100.1")],
                             [200, 200, 429])                                  # one visitor, three accounts: stopped
            self.assertEqual(reg("TunB1", "198.51.100.2"), 200)                # a different visitor is not
            self.assertEqual([reg("Loc1", None), reg("Loc2", None), reg("Loc3", None)], [200, 200, 429])


if __name__ == "__main__":
    unittest.main()
