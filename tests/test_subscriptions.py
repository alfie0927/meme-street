"""Monthly Pro and Expert passes (economy.py, payments.py): the renewal must be agreed, a monthly pass starts a
subscription, no two at once, each later month adds 30 days exactly once (the provider's invoice, or the test mode's
pretend one), cancelling stops the renewals and keeps the month paid for, the provider can end it, the ledger rebuilds it
after a crash, the daily check catches a lost renewal; Stripe's subscription checkout, events, cancelling and invoice
list; and the prices."""
import json
import os
import random
import tempfile
import unittest
import urllib.parse

from _helpers import drift, engine, join, make_engine
from payments import Payments
from test_shop_safety import FakeStripe

THIS_YEAR = 2026


def buyer(e, name="subber"):
    p = join(e, name)
    p.birth_year = THIS_YEAR - 30
    return p


class PassTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(61)
        self.p = buyer(self.e)

    def buy_month(self, kind="pro", provider="test", sub=None):
        o, err = self.e.create_order(self.p, f"{kind}_month", provider, True, renew_ok=True)
        self.assertIsNotNone(o, err)
        self.assertTrue(o["renews"])
        ok, msg = self.e.complete_order(o["id"], "ref", None, sub)
        self.assertTrue(ok, msg)
        return o

    def test_the_prices(self):
        cat = self.e.shop_catalog()
        pro, expert = {x["sku"]: x for x in cat["pro"]}, {x["sku"]: x for x in cat["expert"]}
        self.assertEqual((pro["pro_month"]["price_cents"], pro["pro_month"]["renews"]), (999, True))
        self.assertEqual((pro["pro_year"]["price_cents"], pro["pro_year"]["renews"], pro["pro_year"]["days"]), (9999, False, 365))
        self.assertEqual((expert["expert_month"]["price_cents"], expert["expert_month"]["renews"]), (2999, True))
        self.assertEqual(expert["expert_year"]["price_cents"], 29999)
        self.assertGreaterEqual(int(self.e.settings["spend_cap_month_cents"]), 29999)    # a yearly Expert fits the cap

    def test_the_renewal_must_be_agreed_and_only_one_runs(self):
        e, p = self.e, self.p
        o, err = e.create_order(p, "pro_month", "test", True)
        self.assertIsNone(o)
        self.assertIn("renews", err)
        self.buy_month()
        self.assertEqual(p.subs["pro"]["status"], "active")
        self.assertTrue(e.is_pro(p))
        self.assertIsNone(e.create_order(p, "pro_month", "test", True, renew_ok=True)[0])    # not two at once
        self.assertIsNone(e.create_order(p, "pro_year", "test", True)[0])
        self.assertIsNotNone(e.create_order(p, "expert_month", "test", True, renew_ok=True)[0])   # (the other tier is fine)

    def test_test_mode_renews_by_itself_each_month_until_cancelled(self):
        e, p = self.e, self.p
        self.buy_month()
        first = p.pro_until
        e.now = first - 60                                    # the month is about up
        e._expire_orders()
        self.assertAlmostEqual(p.pro_until, first + 30 * 86400, delta=1)
        renewals = [o for o in e.shop_orders.values() if o.get("renewal_of")]
        self.assertEqual(len(renewals), 1)
        self.assertEqual(renewals[0]["status"], "paid")
        self.assertEqual(renewals[0]["price_cents"], 999)
        e._expire_orders()                                    # (once a month, not every minute)
        self.assertAlmostEqual(p.pro_until, first + 30 * 86400, delta=1)
        ok, msg = e.mark_cancelled(p, "pro")
        self.assertTrue(ok)
        self.assertIn("stays on", msg)
        e.now = p.pro_until - 60
        e._expire_orders()
        self.assertAlmostEqual(p.pro_until, first + 30 * 86400, delta=1)     # cancelled: no more months
        e.now = p.pro_until + 1
        self.assertFalse(e.is_pro(p))
        self.assertEqual(e.economy_view(p)["subs"]["pro"]["status"], "cancelled")
        self.assertLess(abs(drift(e)), 1e-6)

    def test_provider_renewals_count_once_and_can_end(self):
        e, p = self.e, self.p
        self.buy_month("expert", "stripe", "sub_123")
        until = p.expert_until
        self.assertEqual(e.cancel_subscription(p, "expert")[2], "sub_123")    # (the server cancels it at Stripe)
        ok, msg = e.renew_by_provider("sub_123", "in_1", 2999)
        self.assertTrue(ok, msg)
        self.assertAlmostEqual(p.expert_until, until + 30 * 86400, delta=1)
        self.assertEqual(e.renew_by_provider("sub_123", "in_1", 2999), (False, "Already renewed"))   # a retried webhook
        self.assertAlmostEqual(p.expert_until, until + 30 * 86400, delta=1)
        self.assertFalse(e.renew_by_provider("sub_nope", "in_2", 2999)[0])
        e.now = p.expert_until - 60
        e._expire_orders()                                    # (a real one never renews by itself)
        self.assertAlmostEqual(p.expert_until, until + 30 * 86400, delta=1)
        self.assertTrue(e.end_subscription("sub_123")[0])
        self.assertEqual(p.subs["expert"]["status"], "ended")
        self.assertFalse(e.renew_by_provider("sub_123", "in_3", 2999)[0])

    def test_the_daily_check_catches_a_lost_renewal(self):
        e, p = self.e, self.p
        self.buy_month("pro", "stripe", "sub_9")
        until = p.pro_until
        rep = e.reconcile_paid([], [("sub_9", "in_lost", 999)])
        self.assertEqual(len(rep["fixed"]), 1)
        self.assertAlmostEqual(p.pro_until, until + 30 * 86400, delta=1)
        rep = e.reconcile_paid([], [("sub_9", "in_lost", 999)])
        self.assertEqual(rep["fixed"], [])

    def test_a_crash_keeps_the_subscription(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path, led = os.path.join(tmp, "state.json"), os.path.join(tmp, "ledger.db")
            random.seed(7)
            a = engine.Engine(state_file=path, ledger_path=led)
            a.tick(now=a.now)
            p = buyer(a, "crashsub")
            a.save()                                          # the snapshot is from before the purchase
            o, _ = a.create_order(p, "pro_month", "stripe", True, renew_ok=True)
            a.complete_order(o["id"], "cs_1", 999, "sub_77")
            a.ledger.flush()
            a.ledger.close()
            b = engine.Engine(state_file=path, ledger_path=led)
            q = b.by_token[p.token]
            self.assertTrue(b.is_pro(q))
            self.assertEqual(q.subs["pro"]["sub"], "sub_77")
            self.assertTrue(b.renew_by_provider("sub_77", "in_after_crash", 999)[0])    # the next month still finds it
            b.ledger.close()

    def test_a_save_keeps_the_subscription(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            a = engine.Engine(state_file=path)
            a.tick(now=a.now)
            p = buyer(a, "savesub")
            o, _ = a.create_order(p, "expert_month", "test", True, renew_ok=True)
            a.complete_order(o["id"])
            a.save()
            b = engine.Engine(state_file=path)
            self.assertEqual(b.by_token[p.token].subs["expert"]["status"], "active")

    def test_the_receipt_says_it_renews(self):
        e, p = self.e, self.p
        p.email, p.email_verified = "a@b.example", True
        o = self.buy_month()
        to, subject, body = e.receipt(o["id"])
        self.assertIn("monthly", subject)
        self.assertIn("renews every month", body)


class StripeSubscriptionTests(unittest.TestCase):
    def setUp(self):
        self.pay = Payments({"PAYMENTS": "stripe", "STRIPE_SECRET_KEY": "sk_test", "STRIPE_WEBHOOK_SECRET": "whsec",
                             "SITE_URL": "https://example.test"})

    def test_a_monthly_pass_opens_a_subscription_checkout(self):
        fake = FakeStripe([{"url": "https://pay", "id": "cs_9"}])
        url, ref, err = self.pay.checkout({"id": "o9", "currency": "usd", "price_cents": 999, "renews": True}, "Pro", opener=fake)
        self.assertEqual((url, ref), ("https://pay", "cs_9"))
        form = urllib.parse.parse_qs(fake.bodies[0])
        self.assertEqual(form["mode"], ["subscription"])
        self.assertEqual(form["line_items[0][price_data][recurring][interval]"], ["month"])
        self.assertEqual(form["subscription_data[metadata][order]"], ["o9"])
        self.assertEqual(form["line_items[0][price_data][product_data][tax_code]"], ["txcd_10201004"])   # (Managed Payments)
        self.assertEqual(form["line_items[0][price_data][tax_behavior]"], ["inclusive"])                  # the shop's price
        fake = FakeStripe([{"url": "https://pay", "id": "cs_8"}])
        self.pay.checkout({"id": "o8", "currency": "usd", "price_cents": 9999}, "Pro, 1 year", opener=fake)
        form = urllib.parse.parse_qs(fake.bodies[0])
        self.assertEqual(form["mode"], ["payment"])
        self.assertNotIn("line_items[0][price_data][recurring][interval]", form)
        self.assertEqual(form["line_items[0][price_data][product_data][tax_code]"], ["txcd_10201003"])

    def test_the_events(self):
        done = {"type": "checkout.session.completed", "data": {"object": {"payment_status": "paid", "client_reference_id": "o1",
                                                                          "id": "cs_1", "amount_total": 999, "subscription": "sub_1"}}}
        self.assertEqual(Payments.paid_order(done), ("o1", "cs_1", 999, "sub_1"))
        cycle = {"type": "invoice.paid", "data": {"object": {"id": "in_1", "subscription": "sub_1", "amount_paid": 999,
                                                             "billing_reason": "subscription_cycle"}}}
        self.assertEqual(Payments.renewal(cycle), ("sub_1", "in_1", 999))
        first = json.loads(json.dumps(cycle))
        first["data"]["object"]["billing_reason"] = "subscription_create"           # (the first month came with the checkout)
        self.assertIsNone(Payments.renewal(first))
        basil = {"type": "invoice.paid", "data": {"object": {"id": "in_2", "amount_paid": 999, "billing_reason": "subscription_cycle",
                                                             "parent": {"type": "subscription_details",
                                                                        "subscription_details": {"subscription": "sub_1"}}}}}
        self.assertEqual(Payments.renewal(basil), ("sub_1", "in_2", 999))          # (Stripe's API from 2025-03-31 on)
        self.assertEqual(Payments.ended({"type": "customer.subscription.deleted", "data": {"object": {"id": "sub_1"}}}), "sub_1")
        self.assertIsNone(Payments.ended(cycle))

    def test_cancelling_at_stripe(self):
        fake = FakeStripe([{"id": "sub_1", "cancel_at_period_end": True}])
        self.assertTrue(self.pay.cancel_subscription("sub_1", opener=fake))
        self.assertIn("/v1/subscriptions/sub_1", fake.urls[0])
        self.assertEqual(urllib.parse.parse_qs(fake.bodies[0])["cancel_at_period_end"], ["true"])
        self.assertFalse(self.pay.cancel_subscription("sub_1", opener=FakeStripe(fail=True)))
        self.assertFalse(Payments({"PAYMENTS": "test"}).cancel_subscription("sub_1"))

    def test_the_paid_invoice_list(self):
        inv = lambda i, reason: {"id": i, "subscription": "sub_1", "amount_paid": 999, "billing_reason": reason}
        fake = FakeStripe([{"data": [inv("in_1", "subscription_cycle"), inv("in_2", "subscription_create")], "has_more": True},
                           {"data": [inv("in_3", "subscription_cycle")], "has_more": False}])
        self.assertEqual(self.pay.paid_invoices(1000, opener=fake), [("sub_1", "in_1", 999), ("sub_1", "in_3", 999)])
        self.assertIn("starting_after=in_2", fake.urls[1])
        self.assertIsNone(self.pay.paid_invoices(0, opener=FakeStripe(fail=True)))


if __name__ == "__main__":
    unittest.main()
