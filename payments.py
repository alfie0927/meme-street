"""Taking money for MB packages and the Pro pass (ROADMAP.md M3 and O7).

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
            "mode": "payment",
            "success_url": f"{self.site}/shop?paid={order['id']}",
            "cancel_url": f"{self.site}/shop?cancelled={order['id']}",
            "client_reference_id": order["id"],
            "metadata[order]": order["id"],
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": order["currency"],
            "line_items[0][price_data][unit_amount]": str(order["price_cents"]),
            "line_items[0][price_data][product_data][name]": item_name,
        }
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

    @staticmethod
    def paid_order(event):
        """(order id, provider reference, amount in cents) from a Stripe event that means "paid", else None."""
        if not isinstance(event, dict) or event.get("type") not in ("checkout.session.completed",
                                                                     "checkout.session.async_payment_succeeded"):
            return None
        obj = (event.get("data") or {}).get("object") or {}
        if obj.get("payment_status") != "paid":
            return None
        oid = obj.get("client_reference_id") or (obj.get("metadata") or {}).get("order")
        return (oid, obj.get("id"), obj.get("amount_total")) if oid else None
