"""The learn-to-trade economy (economy.py, payments.py): MB by source, the shop (packages and the Pro pass), the age rules,
spending caps, the free restart, and the shop through a real server with the test checkout and a signed Stripe webhook."""
import asyncio
import hashlib
import hmac
import json
import os
import random
import tempfile
import time
import types
import unittest

from _cdp import find_browser, open_page
from _helpers import IsolatedServer, drift, engine, join, make_engine
from payments import Payments
from test_browser import Driver
from test_gateway import join as http_join
from test_server import http

THIS_YEAR = time.gmtime().tm_year


def adult(e, name):
    p = join(e, name)
    p.birth_year = THIS_YEAR - 30
    return p


class SourcesAndStartTests(unittest.TestCase):
    def test_a_new_player_starts_with_1000_mb_recorded_as_a_grant(self):
        e = make_engine(1)
        p = join(e, "starter")
        self.assertEqual(p.cash, 1000.0)
        self.assertEqual(p.mb_by_source, {"grant": 1000.0})
        self.assertEqual(engine.Engine(state_file=None).settings["signup_bonus"], 1000)        # the real content pack too

    def test_every_credit_carries_its_source_and_counts_as_money_put_in(self):
        e = make_engine(2)
        p = join(e, "sourced")
        e.credit(p, 50, source="challenge")
        e.credit(p, 20, source="admin")
        self.assertEqual(p.mb_by_source, {"grant": 1000.0, "challenge": 50.0, "admin": 20.0})
        self.assertEqual(p.deposited, 1070.0)                     # so returns and leaderboards are measured on it
        self.assertLess(abs(drift(e)), 1e-6)


class ShopTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(3)
        self.p = adult(self.e, "buyer")

    def test_the_catalogue_has_the_five_packages_and_two_pro_passes_with_prices(self):
        cat = self.e.shop_catalog()
        self.assertEqual([x["mb"] for x in cat["packages"]], [100, 500, 1000, 5000, 10000])
        self.assertEqual([x["days"] for x in cat["pro"]], [30, 365])
        prices = [x["price_cents"] for x in cat["packages"]]
        per_mb = [c / x["mb"] for c, x in zip(prices, cat["packages"])]
        self.assertEqual(per_mb, sorted(per_mb, reverse=True))                # bigger packages are better value
        self.assertTrue(all(x["price"].startswith("US$") for x in cat["packages"]))

    def test_buying_a_package_credits_the_mb_once_however_often_it_is_confirmed(self):
        e, p = self.e, self.p
        order, err = e.create_order(p, "mb500", "test", adult_confirmed=True)
        self.assertIsNotNone(order, err)
        self.assertEqual(p.cash, 1000.0)                              # nothing until it is paid
        self.assertTrue(e.complete_order(order["id"], "ref1", 399)[0])
        self.assertTrue(e.complete_order(order["id"], "ref1", 399)[0])  # a retried webhook
        self.assertEqual(p.cash, 1500.0)
        self.assertEqual(p.mb_by_source["purchase"], 500.0)
        self.assertEqual(e.shop_orders[order["id"]]["status"], "paid")
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_wrong_amount_does_not_complete_an_order(self):
        order, _ = self.e.create_order(self.p, "mb1000", "stripe", adult_confirmed=True)
        ok, msg = self.e.complete_order(order["id"], "ref", 1)
        self.assertFalse(ok)
        self.assertEqual(self.p.cash, 1000.0)

    def test_the_pro_pass_turns_pro_on_and_adds_up(self):
        e, p = self.e, self.p
        self.assertFalse(e.is_pro(p))
        o1, _ = e.create_order(p, "pro30", "test", True)
        e.complete_order(o1["id"])
        self.assertTrue(e.is_pro(p))
        self.assertAlmostEqual(p.pro_until - e.now, 30 * 86400, delta=5)
        o2, _ = e.create_order(p, "pro30", "test", True)
        e.complete_order(o2["id"])
        self.assertAlmostEqual(p.pro_until - e.now, 60 * 86400, delta=5)          # a second pass extends the first
        self.assertEqual(p.cash, 1000.0)                                           # Pro is tools, never MB
        e.now += 61 * 86400
        self.assertFalse(e.is_pro(p))

    def test_a_refund_takes_back_the_mb_the_player_still_has(self):
        e, p = self.e, self.p
        o, _ = e.create_order(p, "mb1000", "test", True)
        e.complete_order(o["id"])
        e.trade(p, "NVXA", "buy", 0.8)                                # most of it spent on a position
        free = e.free_cash(p)
        ok, msg = e.refund_order(o["id"])
        self.assertTrue(ok, msg)
        self.assertAlmostEqual(p.cash, 0.0, places=6)                 # what was free went back, never more than that
        self.assertAlmostEqual(-p.mb_by_source["refund"], free, places=6)
        self.assertEqual(e.shop_orders[o["id"]]["status"], "refunded")
        self.assertLess(abs(drift(e)), 1e-6)

    def test_unpaid_orders_expire_after_a_day(self):
        o, _ = self.e.create_order(self.p, "mb100", "test", True)
        self.e.now += 86401
        self.e._expire_orders()
        self.assertEqual(self.e.shop_orders[o["id"]]["status"], "expired")


class AgeAndLimitTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(4)

    def test_signing_up_needs_a_plausible_birth_year_and_age_13(self):
        e = self.e
        self.assertIsNone(e.birth_year_problem(THIS_YEAR - 20))
        self.assertIsNone(e.birth_year_problem(THIS_YEAR - 13))
        self.assertIn("13", e.birth_year_problem(THIS_YEAR - 12))
        for bad in (None, "abc", THIS_YEAR + 1, 1800):
            self.assertIsNotNone(e.birth_year_problem(bad))

    def test_under_18s_and_unconfirmed_buyers_cannot_buy(self):
        e = self.e
        teen = join(e, "teen")
        teen.birth_year = THIS_YEAR - 15
        order, err = e.create_order(teen, "mb100", "test", adult_confirmed=True)
        self.assertIsNone(order)
        self.assertIn("18", err)
        nobody = join(e, "noyear")
        self.assertIn("year", e.create_order(nobody, "mb100", "test", True)[1])
        grown = adult(e, "grown")
        self.assertIn("18", e.create_order(grown, "mb100", "test", adult_confirmed=False)[1])
        self.assertIsNotNone(e.create_order(grown, "mb100", "test", adult_confirmed=True)[0])

    def test_the_birth_year_can_be_set_once(self):
        p = join(self.e, "yearonce")
        self.assertTrue(self.e.set_birth_year(p, THIS_YEAR - 25)[0])
        self.assertFalse(self.e.set_birth_year(p, THIS_YEAR - 40)[0])
        self.assertEqual(p.birth_year, THIS_YEAR - 25)

    def test_the_monthly_spending_cap_and_the_daily_limit(self):
        e = self.e
        e.settings.update(spend_cap_month_cents=1000, purchases_per_day=2)
        p = adult(e, "capped")
        o, _ = e.create_order(p, "mb500", "test", True)                # 3.99
        e.complete_order(o["id"])
        o, _ = e.create_order(p, "mb500", "test", True)                # 7.98
        e.complete_order(o["id"])
        order, err = e.create_order(p, "mb100", "test", True)          # a third purchase today
        self.assertIsNone(order)
        self.assertIn("today", err)
        e.now += 86401
        order, err = e.create_order(p, "mb500", "test", True)          # 11.97 would pass the 10.00 cap
        self.assertIsNone(order)
        self.assertIn("cap", err)
        self.assertIsNotNone(e.create_order(p, "mb100", "test", True)[0])   # 8.97 is fine

    def test_lowering_the_cap_works_at_once_and_raising_it_waits_a_day(self):
        e = self.e
        p = adult(e, "self")
        default = e.spend_cap(p)
        e.set_spend_cap(p, 2000)
        self.assertEqual(e.spend_cap(p), 2000)
        e.set_spend_cap(p, 9000)
        self.assertEqual(e.spend_cap(p), 2000)                         # not yet
        e.now += 86401
        self.assertEqual(e.spend_cap(p), 9000)
        e.set_spend_cap(p, 10 ** 9)
        e.now += 86401
        self.assertEqual(e.spend_cap(p), default)                      # never above the site's own cap


class RestartTests(unittest.TestCase):
    def test_the_free_restart_needs_an_empty_account_and_waits_a_week(self):
        e = make_engine(5)
        p = join(e, "busted")
        self.assertFalse(e.claim_restart(p)[0])                        # 1,000 MB is not out of money
        lost = p.cash - 30.0                                           # pretend the trading went badly: 30 MB left
        p.cash -= lost
        e.house += lost                                                # (losses go to the house: nothing is created)
        self.assertTrue(e.trade(p, "NVXA", "buy", 0.5)[0])
        st = e.restart_status(p)
        self.assertFalse(st["eligible"])
        self.assertIn("positions", st["reason"])                       # close positions first
        p.last_trade.pop("NVXA", None)
        self.assertTrue(e.trade(p, "NVXA", "sell", 1.0)[0])
        self.assertTrue(e.restart_status(p)["eligible"])
        p.cash, e.house = 10.0, e.house + p.cash - 10.0
        ok, msg = e.claim_restart(p)
        self.assertTrue(ok, msg)
        self.assertEqual(p.cash, 1000.0)
        self.assertEqual(p.mb_by_source["restart"], 990.0)
        self.assertLess(abs(drift(e)), 1e-6)
        p.cash, e.house = 5.0, e.house + 995.0
        self.assertFalse(e.claim_restart(p)[0])                        # once a week
        e.now += 7 * 86400 + 1
        self.assertTrue(e.claim_restart(p)[0])


class SaveAndReplayTests(unittest.TestCase):
    def test_orders_pro_sources_and_caps_survive_a_restart_and_a_crash(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path, led = os.path.join(tmp, "state.json"), os.path.join(tmp, "ledger.db")
            random.seed(6)
            a = engine.Engine(state_file=path, ledger_path=led)
            a.tick(now=a.now)
            p = join(a, "keeper")
            p.birth_year = THIS_YEAR - 30
            a.set_spend_cap(p, 5000)
            o1, _ = a.create_order(p, "pro365", "test", True)
            a.complete_order(o1["id"])
            a.save()
            o2, _ = a.create_order(p, "mb1000", "test", True)              # bought after the snapshot ...
            a.complete_order(o2["id"])
            a.ledger.flush()                                               # ... and the game crashes before the next save
            a.ledger.close()
            b = engine.Engine(state_file=path, ledger_path=led)
            q = b.by_token[p.token]
            self.assertTrue(b.is_pro(q))
            self.assertEqual(q.cash, 2000.0)                               # the ledger replayed the purchase
            self.assertEqual(q.mb_by_source.get("purchase"), 1000.0)
            self.assertEqual(b.shop_orders[o2["id"]]["status"], "paid")
            self.assertEqual(q.birth_year, THIS_YEAR - 30)
            self.assertEqual(b.spend_cap(q), 5000)
            b.ledger.close()


class StripeSignatureTests(unittest.TestCase):
    def setUp(self):
        self.pay = Payments({"PAYMENTS": "stripe", "STRIPE_SECRET_KEY": "sk_test_x", "STRIPE_WEBHOOK_SECRET": "whsec_test"})

    def sign(self, body, ts=None, secret="whsec_test"):
        ts = int(ts or time.time())
        sig = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
        return f"t={ts},v1={sig}"

    def test_only_a_correctly_signed_recent_event_is_believed(self):
        body = json.dumps({"type": "checkout.session.completed", "data": {"object": {"id": "cs_1", "payment_status": "paid",
                          "client_reference_id": "ord1", "amount_total": 399}}}).encode()
        ev = self.pay.verify_stripe(body, self.sign(body))
        self.assertEqual(self.pay.paid_order(ev), ("ord1", "cs_1", 399))
        self.assertIsNone(self.pay.verify_stripe(body, self.sign(body, secret="wrong")))
        self.assertIsNone(self.pay.verify_stripe(body + b" ", self.sign(body)))                  # body changed
        self.assertIsNone(self.pay.verify_stripe(body, self.sign(body, ts=time.time() - 3600)))  # too old (a replay)
        self.assertIsNone(self.pay.verify_stripe(body, ""))

    def test_unpaid_or_other_events_are_ignored_and_a_mode_without_keys_is_closed(self):
        self.assertIsNone(Payments.paid_order({"type": "checkout.session.completed", "data": {"object": {"payment_status": "unpaid", "client_reference_id": "x"}}}))
        self.assertIsNone(Payments.paid_order({"type": "customer.created"}))
        self.assertEqual(Payments({"PAYMENTS": "stripe"}).mode, "off")
        self.assertEqual(Payments({}).mode, "off")
        self.assertFalse(Payments({}).selling)

    def test_the_checkout_request_sent_to_stripe(self):
        sent = {}

        class Reply:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps({"id": "cs_9", "url": "https://checkout.stripe.com/c/pay/cs_9"}).encode()

        def opener(req, timeout=0):
            sent["url"], sent["data"], sent["auth"] = req.full_url, req.data.decode(), req.get_header("Authorization")
            return Reply()
        url, ref, err = self.pay.checkout({"id": "ord9", "price_cents": 699, "currency": "usd"}, "1,000 MB", opener=opener)
        self.assertEqual((url, ref, err), ("https://checkout.stripe.com/c/pay/cs_9", "cs_9", ""))
        self.assertIn("client_reference_id=ord9", sent["data"])
        self.assertIn("unit_amount%5D=699", sent["data"])
        self.assertEqual(sent["auth"], "Bearer sk_test_x")


class ShopServerTests(unittest.TestCase):
    """The shop through the real server in test mode."""

    def test_the_whole_purchase_flow_with_the_test_checkout(self):
        with IsolatedServer(env={"PAYMENTS": "test"}) as srv:
            a = http_join(srv.url, "ShopBuyer")
            h = {"X-Token": a["token"]}
            status, text, _ = http(srv, "/api/shop", headers=h)
            d = json.loads(text)
            self.assertTrue(d["selling"])
            self.assertEqual(d["mode"], "test")
            status, text, _ = http(srv, "/api/shop/checkout", "POST", {"sku": "mb500", "adult": True}, headers=h)
            self.assertEqual(status, 400)
            self.assertIn("year", json.loads(text)["error"])                    # the age comes first
            http(srv, "/api/account/birth_year", "POST", {"year": THIS_YEAR - 30}, headers=h)
            time.sleep(1.1)                                                       # (one checkout a second)
            status, text, _ = http(srv, "/api/shop/checkout", "POST", {"sku": "mb500", "adult": True}, headers=h)
            self.assertEqual(status, 200, text)
            co = json.loads(text)
            self.assertTrue(co["url"].startswith("/shop/pay?order="))
            self.assertEqual(http(srv, co["url"])[0], 200)                         # the test checkout page
            status, text, _ = http(srv, "/api/shop/test_pay", "POST", {"order": co["order"]}, headers=h)
            self.assertTrue(json.loads(text)["ok"], text)
            d = json.loads(http(srv, "/api/shop", headers=h)[1])
            self.assertEqual(d["mb_by_source"].get("purchase"), 500.0)
            self.assertEqual(d["orders"][0]["status"], "paid")
            other = http_join(srv.url, "NotTheBuyer")
            status, _, _ = http(srv, "/api/shop/test_pay", "POST", {"order": co["order"]}, headers={"X-Token": other["token"]})
            self.assertEqual(status, 404)                                          # nobody else can touch the order
            adm = json.loads(http(srv, "/api/admin/shop", headers={"X-Admin-Key": "testkey"})[1])
            self.assertEqual((adm["orders_paid"], adm["revenue_cents"], adm["mode"]), (1, 399, "test"))

    def test_with_payments_off_the_shop_shows_prices_but_sells_nothing(self):
        with IsolatedServer() as srv:
            a = http_join(srv.url, "ShopOff")
            h = {"X-Token": a["token"]}
            d = json.loads(http(srv, "/api/shop", headers=h)[1])
            self.assertFalse(d["selling"])
            self.assertEqual(len(d["catalog"]["packages"]), 5)
            status, text, _ = http(srv, "/api/shop/checkout", "POST", {"sku": "mb100", "adult": True}, headers=h)
            self.assertEqual(status, 400)
            self.assertEqual(http(srv, "/api/shop/test_pay", "POST", {"order": "x"}, headers=h)[0], 404)
            self.assertEqual(http(srv, "/api/shop/stripe/webhook", "POST", {"x": 1})[0], 404)

    def test_signing_up_with_a_password_needs_an_old_enough_birth_year(self):
        with IsolatedServer(settings={"require_password": True}) as srv:
            body = {"name": "YoungOne", "password": "a-long-password-1"}
            self.assertEqual(http(srv, "/api/register", "POST", body)[0], 400)
            body["birth_year"] = THIS_YEAR - 10
            status, text, _ = http(srv, "/api/register", "POST", body)
            self.assertEqual(status, 400)
            self.assertIn("13", text)
            body["birth_year"] = THIS_YEAR - 16
            self.assertEqual(http(srv, "/api/register", "POST", body)[0], 200)
            self.assertEqual(json.loads(http(srv, "/api/auth_mode")[1])["min_age"], 13)

    def test_close_all_and_the_free_restart_through_the_server(self):
        with IsolatedServer() as srv:
            a = http_join(srv.url, "CloseAll")
            h = {"X-Token": a["token"]}
            status, text, _ = http(srv, "/api/restart", "POST", {}, headers=h)
            self.assertFalse(json.loads(text)["ok"])
            d = json.loads(http(srv, "/api/close_all", "POST", {}, headers=h)[1])
            self.assertEqual(d["closed"], 0)


@unittest.skipUnless(find_browser(), "no Edge/Chrome installed")
class ShopBrowserTests(unittest.TestCase):
    """The shop page in a real browser: the age question, the confirmation, the test checkout and the way back."""

    def test_buying_a_package_on_the_page(self):
        with IsolatedServer(env={"PAYMENTS": "test"}) as srv:
            d, errors = asyncio.run(self._shop(srv.url))
        d.verdict(self, errors)

    async def _shop(self, base):
        proc, pg, _ = await open_page(debug_port=9361)
        d = Driver(pg)
        try:
            await d.join(base, "shop")
            await d.check("the nav has a Shop link", "!!document.querySelector('#nav a[data-page=shop]')")
            await pg.goto(base + "/shop", 3)
            await d.check("the shop page lists five packages", "document.querySelectorAll('#shop-pkgs .pkg').length", 5, wait=10)
            await d.check("it says it is in test mode", "document.getElementById('shop-mode').innerText", lambda t: "Test mode" in t)
            await d.check("Buy is off until the age is known", "document.querySelector('#shop-pkgs [data-sku]').disabled", True)
            await pg.js(f"document.getElementById('shop-year').value='{THIS_YEAR - 30}';document.getElementById('shop-year-save').click()")
            await d.check("after the year, the confirmation box appears", "!!document.getElementById('shop-adult')", wait=8)
            await d.check("Buy is still off until it is ticked", "document.querySelector('#shop-pkgs [data-sku]').disabled", True)
            await pg.js("document.getElementById('shop-adult').click()")
            await d.check("ticking it turns Buy on", "document.querySelector('#shop-pkgs [data-sku=mb500]').disabled", False, wait=3)
            await pg.js("document.querySelector('#shop-pkgs [data-sku=mb500]').click()")
            await d.check("Buy opens the test checkout", "location.pathname", "/shop/pay", wait=8)
            await d.check("which shows the order", "document.getElementById('what').innerText", lambda t: "500 MB" in t, wait=8)
            await pg.js("document.getElementById('pay').click()")
            await d.check("paying comes back to the shop", "location.pathname", "/shop", wait=10)
            await d.check("and the purchase is listed as paid", "document.getElementById('shop-orders').innerText",
                          lambda t: "500 MB" in t and "Paid" in t, wait=10)
            await d.check("the MB arrived", "document.getElementById('cash').innerText", lambda t: t.startswith("1500"), wait=8)
            await d.check("the address bar is tidied", "location.search", "", wait=6)
            await pg.goto(base + "/history", 3)
            await d.check("the history shows the purchase", "document.getElementById('hist-rows').innerText",
                          lambda t: "Purchase" in t, wait=10)
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return d, errors


if __name__ == "__main__":
    unittest.main()
