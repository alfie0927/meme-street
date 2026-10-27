"""Taking money for MB packages and the Pro and Expert passes (ROADMAP.md M3 and O7). A monthly pass is a Stripe
subscription: Stripe takes the first month in its checkout and every later month by itself; each month paid reaches us
as a signed `invoice.paid` event (the daily check also lists paid invoices, in case one was lost), and cancelling sets the
subscription to end with the month already paid.

The mode comes from the PAYMENTS environment variable:

* ``off`` (the default): the shop shows its prices but sells nothing. The live site stays like this until a payment
  provider is set up.
* ``test``: a pretend checkout page on this site ("Pay (test)") completes the order. For trying the shop on your own
  computer (``start_game.ps1`` turns it on). Never use it on a public site: anyone could give themselves MB.
* ``stripe``: Stripe Checkout. Needs ``STRIPE_SECRET_KEY``, ``STRIPE_WEBHOOK_SECRET`` and ``SITE_URL`` (for example
  ``https://memestreet.net``). The browser is sent to Stripe's own payment page; Stripe then calls our webhook, and only a
  webhook with a valid signature completes an order: the browser is never trusted to say "I paid".

No extra package is needed: Stripe is called over HTTPS with the standard library, and its webhook signature (an HMAC
of the timestamp and the body with the webhook secret) is checked here.
"""
import hashlib
import hmac
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)
STRIPE_API = "https://api.stripe.com/v1/checkout/sessions"
STRIPE_SUBS = "https://api.stripe.com/v1/subscriptions/"
STRIPE_INVOICES = "https://api.stripe.com/v1/invoices"
# Stripe's product tax codes, which Managed Payments (Stripe selling as merchant of record and handling the tax) requires on
# every product: a browser game played online, by subscription (the monthly passes) or not (MB packages, yearly passes).
# Prices include the tax, as shown in the shop (EU and UK prices to consumers must), so the amount Stripe charges is the
# order's price, which complete_order checks.
TAX_CODE_SUBSCRIPTION = "txcd_10201004"   # Video Games - streamed - subscription - with conditional rights
TAX_CODE_ONE_OFF = "txcd_10201003"        # Video Games - streamed - non subscription - with limited rights


class Payments:
    def __init__(self, env=None):
        env = os.environ if env is None else env
        self.mode = str(env.get("PAYMENTS", "off")).strip().lower() or "off"
        self.secret_key = env.get("STRIPE_SECRET_KEY", "")
        self.webhook_secret = env.get("STRIPE_WEBHOOK_SECRET", "")
        self.site = str(env.get("SITE_URL", "http://127.0.0.1:8000")).rstrip("/")
        if self.mode not in ("off", "test", "stripe"):
            logger.warning("PAYMENTS=%s is not a known mode; the shop is closed", self.mode)
            self.mode = "off"
        if self.mode == "stripe" and not (self.secret_key and self.webhook_secret):
            logger.warning("PAYMENTS=stripe needs STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET; the shop is closed")
            self.mode = "off"

    @property
    def selling(self):
        return self.mode in ("test", "stripe")

    # ------------------------------------------------------------------ starting a payment
    def checkout(self, order, item_name, opener=None):
        """Where to send the buyer to pay: (url, provider reference, error)."""
        if self.mode == "test":
            return f"/shop/pay?order={order['id']}", None, ""
        if self.mode != "stripe":
            return None, None, "The shop is not open yet"
        form = {
            "mode": "subscription" if order.get("renews") else "payment",
            "success_url": f"{self.site}/shop?paid={order['id']}",
            "cancel_url": f"{self.site}/shop?cancelled={order['id']}",
            "client_reference_id": order["id"],
            "metadata[order]": order["id"],
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": order["currency"],
            "line_items[0][price_data][unit_amount]": str(order["price_cents"]),
            "line_items[0][price_data][product_data][name]": item_name,
            "line_items[0][price_data][product_data][tax_code]": TAX_CODE_SUBSCRIPTION if order.get("renews") else TAX_CODE_ONE_OFF,
            "line_items[0][price_data][tax_behavior]": "inclusive",
        }
        if order.get("renews"):                              # every month, until cancelled
            form["line_items[0][price_data][recurring][interval]"] = "month"
            form["subscription_data[metadata][order]"] = order["id"]
        full = int(order.get("renew_cents") or order["price_cents"])
        if order.get("renews") and full != order["price_cents"]:
            # a first month at a deal price (the New Launch Deal): the subscription at the full price starts with a
            # 30-day trial, and the first month is a one-time item on the first invoice, paid now; the trial's end is the
            # first full-price renewal (no coupon needed, so the shop's restricted key is enough)
            form["line_items[0][price_data][unit_amount]"] = str(full)
            form["subscription_data[trial_period_days]"] = "30"
            form.update({"line_items[1][quantity]": "1", "line_items[1][price_data][currency]": order["currency"],
                         "line_items[1][price_data][unit_amount]": str(order["price_cents"]),
                         "line_items[1][price_data][product_data][name]": item_name + ": the first month",
                         "line_items[1][price_data][product_data][tax_code]": TAX_CODE_SUBSCRIPTION,
                         "line_items[1][price_data][tax_behavior]": "inclusive"})
        req = urllib.request.Request(STRIPE_API, data=urllib.parse.urlencode(form).encode(), method="POST",
                                     headers={"Authorization": "Bearer " + self.secret_key,
                                              "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with (opener or urllib.request.urlopen)(req, timeout=20) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            logger.warning("Stripe refused the checkout: %s %s", e.code, e.read()[:300])
            return None, None, "The payment page could not be opened; please try again"
        except (urllib.error.URLError, OSError, ValueError) as e:
            logger.warning("could not reach Stripe: %s", e)
            return None, None, "The payment page could not be opened; please try again"
        return data.get("url"), data.get("id"), ""

    # ------------------------------------------------------------------ hearing that it was paid
    def verify_stripe(self, payload, header, now=None, tolerance=300):
        """The event, if the ``Stripe-Signature`` header proves Stripe sent this body recently; otherwise None."""
        if not self.webhook_secret or not header:
            return None
        parts = {}
        for item in str(header).split(","):
            k, _, v = item.strip().partition("=")
            parts.setdefault(k, []).append(v)
        try:
            ts = int(parts.get("t", ["0"])[0])
        except ValueError:
            return None
        if abs((now or time.time()) - ts) > tolerance:
            return None
        body = payload if isinstance(payload, bytes) else str(payload).encode("utf-8")
        expected = hmac.new(self.webhook_secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(expected, sig) for sig in parts.get("v1", [])):
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except ValueError:
            return None

    # ------------------------------------------------------------------ the daily check (O7)
    def paid_sessions(self, since, opener=None, pages=20):
        """Every checkout Stripe says was paid since `since` (Unix time), as [(order id, session id, amount in cents)];
        None if Stripe could not be asked. A webhook can be lost (an outage, a restart at the wrong moment): this list is
        how the game finds out. Nothing to check in the other modes."""
        if self.mode != "stripe":
            return []
        out, after = [], None
        for _ in range(pages):                               # 100 sessions a page
            q = {"limit": "100", "created[gte]": str(int(since))}
            if after:
                q["starting_after"] = after
            req = urllib.request.Request(STRIPE_API + "?" + urllib.parse.urlencode(q),
                                         headers={"Authorization": "Bearer " + self.secret_key})
            try:
                with (opener or urllib.request.urlopen)(req, timeout=20) as r:
                    data = json.loads(r.read().decode("utf-8"))
            except (urllib.error.URLError, OSError, ValueError) as e:
                logger.warning("could not list Stripe checkouts: %s", e)
                return None
            sessions = data.get("data") or []
            for s in sessions:
                got = self.paid_order({"type": "checkout.session.completed", "data": {"object": s}})
                if got:
                    out.append(got)
            if not data.get("has_more") or not sessions:
                break
            after = sessions[-1].get("id")
        return out

    def _call(self, url, form=None, opener=None):
        """A Stripe API call: the decoded answer, or None if it failed."""
        data = urllib.parse.urlencode(form).encode() if form is not None else None
        req = urllib.request.Request(url, data=data, method="POST" if form is not None else "GET",
                                     headers={"Authorization": "Bearer " + self.secret_key,
                                              "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with (opener or urllib.request.urlopen)(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            logger.warning("Stripe refused %s: %s %s", url.split("?")[0], e.code, e.read()[:300])
        except (urllib.error.URLError, OSError, ValueError) as e:
            logger.warning("could not reach Stripe: %s", e)
        return None

    def cancel_subscription(self, sub_id, opener=None):
        """Stop a monthly pass renewing: it runs to the end of the month already paid. True if Stripe agreed."""
        if self.mode != "stripe" or not sub_id:
            return False
        r = self._call(STRIPE_SUBS + urllib.parse.quote(str(sub_id)), {"cancel_at_period_end": "true"}, opener)
        return bool(r and r.get("cancel_at_period_end"))

    def paid_invoices(self, since, opener=None, pages=20):
        """Every later month of a monthly pass Stripe says was paid since `since`, as [(subscription, invoice, cents)];
        None if Stripe could not be asked."""
        if self.mode != "stripe":
            return []
        out, after = [], None
        for _ in range(pages):
            q = {"limit": "100", "status": "paid", "created[gte]": str(int(since))}
            if after:
                q["starting_after"] = after
            data = self._call(STRIPE_INVOICES + "?" + urllib.parse.urlencode(q), None, opener)
            if data is None:
                return None
            invoices = data.get("data") or []
            for inv in invoices:
                got = self.renewal({"type": "invoice.paid", "data": {"object": inv}})
                if got:
                    out.append(got)
            if not data.get("has_more") or not invoices:
                break
            after = invoices[-1].get("id")
        return out

    @staticmethod
    def renewal(event):
        """(subscription, invoice, amount in cents) from a Stripe event saying a later month of a pass was paid, else
        None (the first month comes with the checkout)."""
        if not isinstance(event, dict) or event.get("type") not in ("invoice.paid", "invoice.payment_succeeded"):
            return None
        inv = (event.get("data") or {}).get("object") or {}
        # Stripe's API from 2025-03-31 ("basil") on moved an invoice's subscription to parent.subscription_details; a new
        # account gets that shape, an older one the top-level field, so both are read
        sub = inv.get("subscription") or (((inv.get("parent") or {}).get("subscription_details") or {}).get("subscription"))
        if isinstance(sub, dict):                     # (expanded)
            sub = sub.get("id")
        if inv.get("billing_reason") != "subscription_cycle" or not sub:
            return None
        return sub, inv.get("id"), inv.get("amount_paid")

    @staticmethod
    def ended(event):
        """The subscription a `customer.subscription.deleted` event says is over, else None."""
        if not isinstance(event, dict) or event.get("type") != "customer.subscription.deleted":
            return None
        return ((event.get("data") or {}).get("object") or {}).get("id")

    @staticmethod
    def paid_order(event):
        """(order id, provider reference, amount in cents, subscription or None) from a Stripe event that means "paid",
        else None."""
        if not isinstance(event, dict) or event.get("type") not in ("checkout.session.completed",
                                                                     "checkout.session.async_payment_succeeded"):
            return None
        obj = (event.get("data") or {}).get("object") or {}
        if obj.get("payment_status") != "paid":
            return None
        oid = obj.get("client_reference_id") or (obj.get("metadata") or {}).get("order")
        return (oid, obj.get("id"), obj.get("amount_total"), obj.get("subscription")) if oid else None
