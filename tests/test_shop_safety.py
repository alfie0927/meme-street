"""Before the shop takes real money (ROADMAP step 1): the terms recorded at sign-up, the consent kept with each order,
receipts, the payment check that completes orders whose webhook never came (O7), the sign-up trap for bots and the switch
that pays rewards only to verified accounts (R6)."""
import io
import json
import time
import unittest
import urllib.error

from _helpers import IsolatedServer, drift, join, make_engine
import economy  # noqa: E402  (after _helpers, which puts the game on the path)
from payments import Payments
from test_server import http

THIS_YEAR = time.gmtime().tm_year


def adult(e, name):
    p = join(e, name)
    p.birth_year = THIS_YEAR - 30
    return p


class FakeStripe:
    """Answers Stripe's list call from a list of pages; raises when told to."""
    def __init__(self, pages=None, fail=False):
        self.pages, self.fail, self.urls = list(pages or []), fail, []

    def __call__(self, req, timeout=None):
        self.urls.append(req.full_url)
        if self.fail:
            raise urllib.error.URLError("down")
        return io.BytesIO(json.dumps(self.pages.pop(0)).encode())


def session(sid, oid, cents, status="paid"):
    return {"id": sid, "client_reference_id": oid, "payment_status": status, "amount_total": cents}


class EngineTests(unittest.TestCase):
    def test_an_account_records_the_terms_it_signed_up_under(self):
        e = make_engine(1)
        p = join(e, "reader")
        self.assertEqual(p.terms, {"v": economy.TERMS_VERSION, "at": e.now})
        self.assertEqual(economy.dump_player(p)["terms"]["v"], economy.TERMS_VERSION)      # and it is saved

    def test_an_order_keeps_the_buyers_consent(self):
        e = make_engine(2)
        o, err = e.create_order(adult(e, "buyer"), "mb1000", "test", True)
        self.assertIsNotNone(o, err)
        self.assertIn("no 14-day cancellation", o["consent"])

    def test_the_payment_check_completes_a_missed_order_exactly_once(self):
        e = make_engine(3)
        p = adult(e, "missed")
        o, _ = e.create_order(p, "mb5000", "stripe", True)
        paid_ok, _ = e.create_order(adult(e, "fine"), "mb1000", "stripe", True)
        e.complete_order(paid_ok["id"], "cs_ok", 199)                 # this one's webhook arrived
        found = [(o["id"], "cs_1", 799), (paid_ok["id"], "cs_ok", 199), ("nosuchorder", "cs_2", 199)]
        r = e.reconcile_paid(found)
        self.assertEqual([f["order"] for f in r["fixed"]], [o["id"]])
        self.assertEqual([x["order"] for x in r["problems"]], ["nosuchorder"])
        self.assertEqual(r["checked"], 3)
        self.assertEqual(p.cash, 6000.0)
        self.assertEqual(e.shop_orders[o["id"]]["provider_ref"], "cs_1")
        again = e.reconcile_paid(found)                                # the next run changes nothing
        self.assertEqual(again["fixed"], [])
        self.assertEqual(p.cash, 6000.0)
        self.assertEqual(e.economy_stats()["pay_check"], again)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_the_payment_check_refuses_an_amount_that_does_not_match(self):
        e = make_engine(4)
        o, _ = e.create_order(adult(e, "short"), "mb5000", "stripe", True)
        r = e.reconcile_paid([(o["id"], "cs_1", 100)])
        self.assertEqual(r["fixed"], [])
        self.assertIn("does not match", r["problems"][0]["msg"])
        self.assertEqual(e.shop_orders[o["id"]]["status"], "pending")

    def test_a_late_order_that_had_expired_is_still_completed(self):
        e = make_engine(5)
        p = adult(e, "late")
        o, _ = e.create_order(p, "mb1000", "stripe", True)
        e.now += economy.ORDER_TTL + 10
        e._expire_orders()
        self.assertEqual(e.shop_orders[o["id"]]["status"], "expired")
        self.assertEqual(len(e.reconcile_paid([(o["id"], "cs", 199)])["fixed"]), 1)
        self.assertEqual(p.cash, 2000.0)

    def test_a_receipt_goes_only_to_a_verified_address(self):
        e = make_engine(6)
        p = adult(e, "receipt")
        o, _ = e.create_order(p, "mb10000", "test", True)
        e.complete_order(o["id"])
        self.assertIsNone(e.receipt(o["id"]))                          # no address
        p.email, p.email_verified = "buyer@example.com", False
        self.assertIsNone(e.receipt(o["id"]))                          # not verified
        p.email_verified = True
        to, subject, body = e.receipt(o["id"])
        self.assertEqual(to, "buyer@example.com")
        self.assertIn("10,000 MB", subject)
        self.assertIn("US$13.99", body)
        self.assertIn(o["id"], body)
        self.assertIn("no cash value", body)
        pending, _ = e.create_order(p, "mb1000", "test", True)
        self.assertIsNone(e.receipt(pending["id"]))                    # nothing to receipt before it is paid

    def test_rewards_can_be_kept_for_verified_accounts(self):
        e = make_engine(7, quest_ladder=True)
        p = join(e, "unverified")
        self.assertEqual(e._reward(p, 25, "A challenge"), 25.0)       # off by default (no real email yet)
        e.settings["rewards_need_email"] = True
        self.assertEqual(e._reward(p, 25, "A challenge"), 0.0)
        p.counters["trades"] = 5
        e._ladder_check(p)
        self.assertIn("b_trades", p.ladder["done"])                    # the quest is done...
        self.assertEqual(p.mb_by_source.get("challenge"), 25.0)        # ...but paid nothing
        self.assertTrue(any("verify your email" in n for n in p.notices))
        p.email_verified = True
        self.assertEqual(e._reward(p, 25, "A challenge"), 25.0)


class StripeListTests(unittest.TestCase):
    def setUp(self):
        self.pay = Payments({"PAYMENTS": "stripe", "STRIPE_SECRET_KEY": "sk_test", "STRIPE_WEBHOOK_SECRET": "whsec"})

    def test_it_reads_every_page_and_keeps_only_paid_checkouts(self):
        fake = FakeStripe([{"data": [session("cs_1", "o1", 199), session("cs_2", "o2", 799, "unpaid")], "has_more": True},
                           {"data": [session("cs_3", "o3", 1399), {"id": "cs_4", "payment_status": "paid"}], "has_more": False}])
        got = self.pay.paid_sessions(1000, opener=fake)
        self.assertEqual(got, [("o1", "cs_1", 199), ("o3", "cs_3", 1399)])
        self.assertIn("created%5Bgte%5D=1000", fake.urls[0])
        self.assertIn("starting_after=cs_2", fake.urls[1])

    def test_it_says_so_when_stripe_cannot_be_reached(self):
        self.assertIsNone(self.pay.paid_sessions(0, opener=FakeStripe(fail=True)))

    def test_there_is_nothing_to_check_without_stripe(self):
        self.assertEqual(Payments({"PAYMENTS": "test"}).paid_sessions(0, opener=FakeStripe(fail=True)), [])


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = IsolatedServer(settings={"require_password": True}).__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.srv.__exit__(None, None, None)

    def test_the_terms_and_privacy_pages_are_served(self):
        for path, words in (("/terms", "no cash value"), ("/privacy", "salted")):
            status, body, _ = http(self.srv, path)
            self.assertEqual(status, 200, path)
            self.assertIn(words, body)
        status, body, _ = http(self.srv, "/")
        self.assertIn('href="/terms"', body)
        self.assertIn('href="/privacy"', body)

    def test_a_sign_up_with_the_hidden_box_filled_in_is_refused(self):
        body = {"name": "Botty", "password": "a fine long password", "birth_year": 1990, "website": "http://spam.example"}
        status, text, _ = http(self.srv, "/api/register", "POST", body)
        self.assertEqual(status, 400, text)
        body.update(name="Human", website="")
        status, text, _ = http(self.srv, "/api/register", "POST", body)
        self.assertEqual(status, 200, text)

    def test_the_admin_payment_check_says_there_is_nothing_to_check_without_stripe(self):
        status, text, _ = http(self.srv, "/api/admin/payment_check", "POST", {}, headers={"X-Admin-Key": self.srv.admin_key})
        self.assertEqual(status, 200, text)
        self.assertIn("not taking real payments", json.loads(text)["msg"])
        status, _, _ = http(self.srv, "/api/admin/payment_check", "POST", {}, headers={"X-Admin-Key": "wrong"})
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
