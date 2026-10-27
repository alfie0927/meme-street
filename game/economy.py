"""The MB economy of the learn-to-trade plan (ROADMAP.md, track M): where every MB comes from, the shop (MB packages and
the Pro pass), the age rules, spending caps and the free restart for an account that has run out.

MB are a game currency. They are bought, earned or granted, and never paid out: there is no withdrawal for players.

* **Sources.** Every MB that enters an account is counted by source: `grant` (the starting balance), `purchase` (a
  package), `challenge` (a reward), `restart` (the free restart), `refund` (taken back, negative) and `admin`.
* **The shop.** Packages of MB, a Pro pass and an Expert pass (30 or 365 days each), at prices set in the
  `shop_packages`, `shop_pro` and `shop_expert` settings. A purchase is an *order*: created when the player clicks Buy, paid at the payment provider
  (or the test checkout), and completed exactly once by `complete_order`, which credits the MB or extends Pro and writes
  a `purchase` event to the money ledger (so a crash cannot lose a purchase).
* **Pro** is the income that does not depend on anyone losing: the advanced chart indicators and trading with leverage
  (up to 10x). **Expert** has everything in Pro, plus trading bots the player scripts (indicator rules, a news score,
  stocks and options) and backtesting them on the price history (bots.py).
* **Age.** An account needs a date of birth showing at least `min_age` (13). Buying has no age rule (since 2026-10-24,
  on request), only the confirmation that the card may be used and that the purchase is delivered at once.
* **Spending caps.** A default cap per rolling 30 days (`spend_cap_month_cents`), a lower cap a player can set (lowering
  works at once, raising after 24 hours), and at most `purchases_per_day` purchases a day.
* **The free restart.** An account whose equity is below `restart_below` MB, with no open positions, can top its cash
  back up to the starting balance once every `restart_days` days, for nothing.
* **Invites** (2026-10-27): every account has its own invite code, so its link is `memestreet.net/?ref=<code>` (the
  same `?ref=` as the tracking links). Someone who signs up through it is counted as invited by that player
  (`invited_by`), for the admin page; rewards for inviting may come later.
* **The New Launch Deal** (2026-10-27): two big packages (`LAUNCH_DEALS`) that an account can buy once, in its first
  `launch_deal_days` (30) days.
"""
import datetime
import secrets
import uuid

SOURCES = ("grant", "purchase", "challenge", "restart", "refund", "admin")
DEFAULT_PACKAGES = [
    {"sku": "mb1000", "mb": 1000, "price_cents": 199},
    {"sku": "mb5000", "mb": 5000, "price_cents": 799},
    {"sku": "mb10000", "mb": 10000, "price_cents": 1399},
    {"sku": "mb50000", "mb": 50000, "price_cents": 5999},
    {"sku": "mb100000", "mb": 100000, "price_cents": 9999},
]
# Pro and Expert: a monthly pass that renews every month until it is cancelled ("renews"), or a year paid at once
DEFAULT_PRO = [
    {"sku": "pro_month", "days": 30, "price_cents": 999, "renews": True},
    {"sku": "pro_year", "days": 365, "price_cents": 9999},
]
DEFAULT_EXPERT = [
    {"sku": "expert_month", "days": 30, "price_cents": 2999, "renews": True},
    {"sku": "expert_year", "days": 365, "price_cents": 29999},
]
PRO_FEATURES = [
    "Trade any stock with leverage, up to 10x (the leveraged index products excepted): more exposure for your MB, "
    "losses magnified the same way, interest on what you borrow and an automatic close if the position runs out of margin",
    "32 more chart indicators: Bollinger bands, MACD, Ichimoku, VWAP, ATR, ADX, Stochastic RSI, OBV, pivot points and more "
    "(17, including every moving average, RSI and the drawing tools, are free)",
    "A Pro badge on your profile",
]
EXPERT_FEATURES = [
    "Everything in Pro",
    "Trading bots you script yourself: buy, sell, short and cover on your own rules (\"buy when the price crosses above "
    "the 20 EMA, sell at the 200 EMA\"), with stops, targets, sizing and leverage",
    "News bots: they read the news wire, score each headline with your own words and weights, and trade on the score",
    "Bots that trade options too: calls and puts at the strike and expiry you choose",
    "Backtesting: run a bot over the price history first and see its trades, its return, its worst drawdown and how it "
    "did against just holding the stock",
    "An Expert badge on your profile",
]
# the New Launch Deal: one of these, once, in an account's first `launch_deal_days` days
LAUNCH_DEALS = [
    {"sku": "launch9000", "mb": 9000, "price_cents": 499},
    {"sku": "launch99000", "mb": 99000, "price_cents": 2999},
]
INVITE_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"   # (no 0, 1, i, l or o: easy to read out)
TIERS = ("pro", "expert")
ORDER_TTL = 86400            # an order that is not paid within a day expires
TERMS_VERSION = "2026-10-24"  # the date of web/terms.html; an account records the version it signed up under
PLAYER_FIELDS = ("birth_year", "birth_date", "ref", "pro_until", "expert_until", "last_restart", "mb_by_source",
                 "challenge_mb", "terms", "subs", "invite", "invited_by")


def init_player(p):
    p.birth_year = None          # the year of birth (all an account from before 2026-10-24 has)
    p.birth_date = None          # the date of birth, "YYYY-MM-DD", asked at sign-up since 2026-10-24
    p.ref = None                 # the tracking link the player first arrived by (?ref=ig_story1), for the admin page
    p.invite = None              # the player's own invite code (made when first needed): their link is /?ref=<code>
    p.invited_by = None          # the account key of the player whose invite link they signed up through
    p.pro_until = 0.0            # real time until which the Pro tools are on
    p.expert_until = 0.0         # real time until which Expert (which includes Pro) is on
    p.last_restart = 0.0         # when the player last used the free restart
    p.mb_by_source = {}          # source -> MB received from it
    p.challenge_mb = {}          # week number -> MB earned from challenges that week (for the weekly cap)
    p.terms = None               # {"v": version, "at": time}: the terms the account agreed to when it signed up
    p.subs = {}                  # "pro" / "expert" -> a monthly pass that renews: {order, sub, provider, status, price_cents, sku}


def dump_player(p):
    return {k: getattr(p, k) for k in PLAYER_FIELDS}


def load_player(p, x):
    for k in PLAYER_FIELDS:
        if k in x:
            setattr(p, k, x[k])
    p.mb_by_source = {str(k): float(v) for k, v in dict(p.mb_by_source or {}).items()}
    if not p.mb_by_source and getattr(p, "deposited", 0.0) > 0:      # a save from before sources were kept
        p.mb_by_source = {"grant": float(p.deposited)}
    p.challenge_mb = {str(k): float(v) for k, v in dict(p.challenge_mb or {}).items()}
    p.pro_until = float(p.pro_until or 0.0)
    p.expert_until = float(getattr(p, "expert_until", 0.0) or 0.0)
    p.last_restart = float(p.last_restart or 0.0)
    p.subs = {str(k): dict(v) for k, v in dict(getattr(p, "subs", None) or {}).items() if isinstance(v, dict)}


def money_text(cents, currency="usd"):
    symbol = {"usd": "US$", "eur": "€", "gbp": "£"}.get(currency, currency.upper() + " ")
    return f"{symbol}{cents / 100:,.2f}"


class EconomyMixin:
    """Mixed into the Engine. Uses `self.now`, `self.settings`, `self.players`, `self.equity`, `self._emit`,
    `self._ratio` and `self._rebase_peak`."""

    def _init_economy(self):
        self.pay_check = None       # the last daily payment check (reconcile_paid), for the admin page
        self.shop_orders = {}        # order id -> the order (see create_order)

    # ------------------------------------------------------------------ the catalogue
    def shop_currency(self):
        return str(self.settings.get("shop_currency", "usd"))

    def shop_catalog(self):
        packages = [dict(x) for x in self.settings.get("shop_packages", DEFAULT_PACKAGES)]
        pro = [dict(x) for x in self.settings.get("shop_pro", DEFAULT_PRO)]
        expert = [dict(x) for x in self.settings.get("shop_expert", DEFAULT_EXPERT)]
        cur = self.shop_currency()
        deals = [dict(x, deal=True) for x in LAUNCH_DEALS]
        for x in packages + deals:
            x["kind"] = "package"
            x["price"] = money_text(int(x["price_cents"]), cur)
            x["per_1000"] = money_text(round(int(x["price_cents"]) * 1000 / max(int(x["mb"]), 1)), cur)
        for kind, items in (("pro", pro), ("expert", expert)):
            for x in items:
                x["kind"] = kind
                x["renews"] = bool(x.get("renews"))
                x["price"] = money_text(int(x["price_cents"]), cur)
        return {"packages": packages, "deals": deals, "pro": pro, "expert": expert, "currency": cur,
                "pro_features": PRO_FEATURES, "expert_features": EXPERT_FEATURES}

    def _sku(self, sku):
        cat = self.shop_catalog()
        return next((x for x in cat["packages"] + cat["deals"] + cat["pro"] + cat["expert"] if x["sku"] == sku), None)

    # ------------------------------------------------------------------ the New Launch Deal
    def deal_until(self, p):
        """When `p`'s chance at the New Launch Deal ends, or None if it has (the account is older than
        `launch_deal_days`, or it has bought or is paying for one already)."""
        until = (p.created or 0.0) + float(self.settings.get("launch_deal_days", 30)) * 86400
        skus = {x["sku"] for x in LAUNCH_DEALS}
        if not p.created or self.now >= until or any(o["token"] == p.token and o["sku"] in skus and o["status"] in ("paid", "refunded")
                                                     for o in self.shop_orders.values()):
            return None
        return until

    # ------------------------------------------------------------------ invites
    def invite_code(self, p):
        """`p`'s own invite code, made the first time it is needed and kept: 7 easy-to-read characters, never a code
        or a tracking link anyone already has."""
        if not p.invite:
            taken = {q.invite for q in self.players.values()} | {q.ref for q in self.players.values()}
            code = None
            while code is None or code in taken:
                code = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(7))
            p.invite = code
        return p.invite

    def note_invite(self, p):
        """At sign-up: a `?ref=` that is another player's invite code makes that player the inviter."""
        if p.ref and not p.invited_by:
            inviter = next((q for q in self.players.values() if q.invite == p.ref and q is not p), None)
            if inviter is not None:
                p.invited_by = inviter.token

    def invited_count(self, p):
        return sum(1 for q in self.players.values() if q.invited_by == p.token)

    # ------------------------------------------------------------------ age
    def _year(self):
        return datetime.datetime.fromtimestamp(self.now, datetime.timezone.utc).year

    def _age_on(self, born):
        today = datetime.datetime.fromtimestamp(self.now, datetime.timezone.utc).date()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def birth_date_problem(self, text):
        """Why a date of birth ("YYYY-MM-DD") is not acceptable, or None."""
        try:
            born = datetime.date.fromisoformat(str(text or "").strip())
        except ValueError:
            return "Please give your date of birth"
        age = self._age_on(born)
        if age < 0 or age > 120:
            return "Please give your date of birth"
        need = int(self.settings.get("min_age", 13))
        if age < need:
            return f"You need to be at least {need} to use Meme Street"
        return None

    def set_birth_date(self, p, text):
        """An account from before dates of birth were asked gives it once (the page asks on the next visit)."""
        if p.birth_date:
            return False, "Your date of birth is already saved"
        bad = self.birth_date_problem(text)
        if bad:
            return False, bad
        p.birth_date = str(text).strip()
        p.birth_year = int(p.birth_date[:4])
        return True, "Saved"

    def birth_year_problem(self, year):
        """Why a birth year is not acceptable, or None (a sign-up from a page loaded before dates of birth were asked)."""
        try:
            year = int(year)
        except (TypeError, ValueError):
            return "Please give the year you were born"
        this = self._year()
        if year < this - 120 or year > this:
            return "Please give the year you were born"
        need = int(self.settings.get("min_age", 13))
        if this - year < need:
            return f"You need to be at least {need} to use Meme Street"
        return None

    # ------------------------------------------------------------------ spending
    def spent_cents(self, p, seconds=30 * 86400):
        since = self.now - seconds
        return sum(o["price_cents"] for o in self.shop_orders.values()
                   if o["token"] == p.token and o["status"] == "paid" and o.get("paid_at", 0) >= since)

    def _purchases_since(self, p, seconds):
        since = self.now - seconds
        return sum(1 for o in self.shop_orders.values()
                   if o["token"] == p.token and o["status"] == "paid" and o.get("paid_at", 0) >= since)

    def spend_cap(self, p):
        """The most anyone may spend in a rolling 30 days, in cents (`spend_cap_month_cents`)."""
        return int(self.settings.get("spend_cap_month_cents", 50000))

    def buy_problem(self, p, item, consent, renew_ok=False):
        """Why this player may not buy this item now, or None."""
        if not item:
            return "Unknown item"
        if item.get("renews") and not renew_ok:
            return "Tick the box to agree that it renews every month until you cancel"
        if item.get("kind") in TIERS and (p.subs.get(item["kind"]) or {}).get("status") == "active":
            return (f"You have a monthly {item['kind'].title()} that renews by itself: cancel it first (it stays on to the end "
                    "of the month you paid for)")
        if item.get("deal") and self.deal_until(p) is None:
            return "The New Launch Deal is for an account's first 30 days, once"
        if not consent:
            return "Tick the box to confirm the card and that you want it added straight away"
        if self.spent_cents(p) + int(item["price_cents"]) > self.spend_cap(p):
            return ("That would take you over your spending cap of " + money_text(self.spend_cap(p), self.shop_currency())
                    + " in 30 days")
        per_day = int(self.settings.get("purchases_per_day", 3))
        if per_day > 0 and self._purchases_since(p, 86400) >= per_day:
            return f"You have made {per_day} purchases today: the shop opens again tomorrow"
        return None

    # ------------------------------------------------------------------ orders
    def create_order(self, p, sku, provider, consent=False, renew_ok=False):
        item = self._sku(sku)
        bad = self.buy_problem(p, item, consent, renew_ok)
        if bad:
            return None, bad
        oid = uuid.uuid4().hex[:20]
        order = {"id": oid, "token": p.token, "name": p.name, "sku": item["sku"], "kind": item["kind"],
                 "mb": int(item.get("mb", 0)), "days": int(item.get("days", 0)), "price_cents": int(item["price_cents"]),
                 "currency": self.shop_currency(), "status": "pending", "created": self.now, "provider": provider,
                 "provider_ref": None, "renews": bool(item.get("renews")),
                 "consent": "own card or the holder's permission, delivery now (no 14-day cancellation)"
                            + (", renews monthly until cancelled" if item.get("renews") else "")}
        self.shop_orders[oid] = order
        return order, ""

    def complete_order(self, oid, provider_ref=None, amount_cents=None, sub_id=None):
        """The payment provider says the order is paid: credit the MB or extend Pro, exactly once. A monthly pass also
        starts its subscription (`sub_id`: the provider's, for the renewals and for cancelling)."""
        o = self.shop_orders.get(oid)
        if o is None:
            return False, "Unknown order"
        if o["status"] == "paid":
            return True, "Already completed"                       # webhooks are retried: completing twice is a no-op
        if o["status"] not in ("pending", "expired"):
            return False, "This order is " + o["status"]
        if amount_cents is not None and int(amount_cents) != o["price_cents"]:
            return False, "The amount paid does not match the order"
        p = self.by_token.get(o["token"])
        if p is None:
            return False, "The account no longer exists"
        o["status"], o["paid_at"], o["provider_ref"] = "paid", self.now, provider_ref
        self._apply_purchase(p, o)
        if o.get("renews"):
            p.subs[o["kind"]] = {"order": oid, "sub": sub_id, "provider": o["provider"], "status": "active",
                                 "price_cents": o["price_cents"], "sku": o["sku"], "since": self.now, "renewals": 0}
        self._emit("purchase", p, cash=float(o["mb"]), notional=float(o["mb"]), order=oid, sku=o["sku"], days=o["days"],
                   price_cents=o["price_cents"], source="purchase", renews=bool(o.get("renews")), sub=sub_id,
                   provider=o["provider"])
        if o["kind"] in TIERS:
            until = p.expert_until if o["kind"] == "expert" else p.pro_until
            self._notify(p, f"Thank you! Meme Street {o['kind'].title()} is on until {datetime.datetime.fromtimestamp(until, datetime.timezone.utc):%d %b %Y}.")
        else:
            self._notify(p, f"Thank you! {o['mb']:,} MB were added to your account.")
        return True, "Completed"

    def _apply_purchase(self, p, o, at=None):
        if o["mb"] > 0:
            ratio = self._ratio(p)
            p.cash += o["mb"]
            p.deposited += o["mb"]
            p.season_base += o["mb"]
            self.minted += o["mb"]
            self._rebase_peak(p, ratio)
            p.mb_by_source["purchase"] = p.mb_by_source.get("purchase", 0.0) + o["mb"]
        if o["days"] > 0:
            field = "expert_until" if o.get("kind") == "expert" else "pro_until"
            start = max(self.now if at is None else at, float(getattr(p, field) or 0.0))     # (a replay passes the event's time)
            setattr(p, field, start + o["days"] * 86400)

    def refund_order(self, oid):
        """Admin: the money was given back at the provider. Takes back the MB the player still has (never more than the
        order gave), or ends the Pro time it added."""
        o = self.shop_orders.get(oid)
        if o is None or o["status"] != "paid":
            return False, "Only a paid order can be refunded"
        p = self.by_token.get(o["token"])
        o["status"], o["refunded_at"] = "refunded", self.now
        if p is None:
            return True, "Refunded (the account no longer exists)"
        if o["mb"] > 0:
            take = min(float(o["mb"]), max(0.0, self.free_cash(p)))
            if take > 0:
                self.debit(p, take)
                p.mb_by_source["refund"] = p.mb_by_source.get("refund", 0.0) - take
            return True, f"Refunded; took back {take:,.2f} MB"
        field = "expert_until" if o["kind"] == "expert" else "pro_until"
        if getattr(p, field) > self.now:
            setattr(p, field, max(self.now, float(getattr(p, field)) - o["days"] * 86400))
        return True, f"Refunded; the {o['kind'].title()} time was removed"

    def reconcile_paid(self, found, renewals=()):
        """The daily payment check (ROADMAP O7): `found` is every (order id, provider reference, amount[, subscription])
        the provider says was paid lately, `renewals` every (subscription, invoice, amount) of a monthly pass's later
        months. Anything the webhook missed is done now (exactly once, like a webhook); anything that cannot be is listed
        for the admin."""
        fixed, problems = [], []
        for oid, ref, amount, *rest in found:
            o = self.shop_orders.get(oid)
            if o is not None and o["status"] == "paid":
                continue
            ok, msg = self.complete_order(oid, ref, amount, rest[0] if rest else None)
            (fixed if ok else problems).append({"order": oid, "ref": ref, "msg": msg})
        for sub, inv, amount in renewals:
            if "renew-" + str(inv)[:60] in self.shop_orders:
                continue
            ok, msg = self.renew_by_provider(sub, inv, amount)
            (fixed if ok else problems).append({"order": "renew-" + str(inv)[:60], "ref": inv, "msg": msg})
        self.pay_check = {"at": self.now, "checked": len(found), "fixed": fixed, "problems": problems, "error": None}
        return self.pay_check

    def receipt(self, oid):
        """(to, subject, body) for a paid order's receipt email, or None when the buyer has no verified address."""
        o = self.shop_orders.get(oid)
        p = self.by_token.get(o["token"]) if o else None
        if not (o and p and o["status"] == "paid" and p.email and p.email_verified):
            return None
        what = (f"{o['mb']:,} MB" if o["kind"] == "package" else f"Meme Street {o['kind'].title()}, monthly" if o.get("renews")
                else f"Meme Street {o['kind'].title()}, {'1 year' if o['days'] == 365 else str(o['days']) + ' days'}")
        price = money_text(o["price_cents"], o["currency"])
        when = datetime.datetime.fromtimestamp(o.get("paid_at", self.now), datetime.timezone.utc)
        body = (f"Thank you for your purchase, {p.name}.\n\n    {what}\n    {price}\n    Order {o['id']}\n"
                f"    Paid {when:%d %b %Y, %H:%M} UTC\n\n"
                "MB are practice money for the game: they have no cash value and cannot be withdrawn, sold or given away. "
                "You asked for the purchase to be delivered at once, so the 14-day right to cancel ended when it was added. "
                + ("It renews every month at the same price until you cancel it in the Shop; cancelling stops the next "
                   "payment and keeps it on to the end of the month you have paid for. " if o.get("renews") else "")
                + "If something went wrong, reply to this email or see the terms at /terms.\n")
        return p.email, f"Your Meme Street receipt: {what}", body

    def reward_block(self, p):
        """Why `p` gets no MB from a challenge or a quest right now, or None. With `rewards_need_email` on (once real
        email is set up, ROADMAP O1 and R6), only an account with a verified address is paid."""
        if self.settings.get("rewards_need_email", False) and not getattr(p, "email_verified", False):
            return "verify your email address on the Profile page to earn MB"
        return None

    def _expire_orders(self):
        for o in self.shop_orders.values():
            if o["status"] == "pending" and self.now - o["created"] > ORDER_TTL:
                o["status"] = "expired"
        self._renew_test_subs()

    # ------------------------------------------------------------------ monthly passes (subscriptions)
    def _sub_of(self, sub_id):
        """(player, kind) of the subscription the provider calls `sub_id`."""
        for p in self.players.values():
            for kind, x in (getattr(p, "subs", None) or {}).items():
                if sub_id and x.get("sub") == sub_id:
                    return p, kind
        return None, None

    def renew_subscription(self, p, kind, invoice, amount_cents=None):
        """A month of a monthly pass was paid (the provider's invoice, or the test mode's pretend one): 30 more days, as
        a paid order of its own (for the purchase list, refunds and the ledger). Exactly once per invoice."""
        x = (p.subs or {}).get(kind)
        oid = "renew-" + str(invoice)[:60]
        if x is None or oid in self.shop_orders:
            return False, "Already renewed" if oid in self.shop_orders else "No such subscription"
        if x.get("status") == "ended":
            return False, "The subscription has ended"
        price = int(x["price_cents"] if amount_cents is None else amount_cents)
        o = {"id": oid, "token": p.token, "name": p.name, "sku": x["sku"], "kind": kind, "mb": 0, "days": 30,
             "price_cents": price, "currency": self.shop_currency(), "status": "paid", "created": self.now, "paid_at": self.now,
             "provider": x.get("provider"), "provider_ref": str(invoice), "renews": True, "renewal_of": x.get("order"),
             "consent": "renewal of a monthly pass"}
        self.shop_orders[oid] = o
        self._apply_purchase(p, o)
        x["renewals"] = int(x.get("renewals", 0)) + 1
        self._emit("purchase", p, cash=0.0, notional=0.0, order=oid, sku=o["sku"], days=30, price_cents=price, source="purchase",
                   renewal=True)
        until = p.expert_until if kind == "expert" else p.pro_until
        self._notify(p, f"Your monthly {kind.title()} renewed: on until {datetime.datetime.fromtimestamp(until, datetime.timezone.utc):%d %b %Y}.")
        return True, "Renewed"

    def renew_by_provider(self, sub_id, invoice, amount_cents=None):
        p, kind = self._sub_of(sub_id)
        if p is None:
            return False, "Unknown subscription"
        return self.renew_subscription(p, kind, invoice, amount_cents)

    def end_subscription(self, sub_id):
        """The provider says the subscription is over (cancelled and run out, or the card failed for good)."""
        p, kind = self._sub_of(sub_id)
        if p is None:
            return False, "Unknown subscription"
        p.subs[kind]["status"] = "ended"
        return True, "Ended"

    def cancel_subscription(self, p, kind):
        """The player cancels a monthly pass: no more payments; it stays on to the end of the month paid for. Returns
        (ok, message, the provider's subscription id to cancel there, or None)."""
        x = (p.subs or {}).get(kind)
        if x is None or x.get("status") != "active":
            return False, "Nothing to cancel", None
        return True, "", x.get("sub") if x.get("provider") == "stripe" else None

    def mark_cancelled(self, p, kind):
        x = (p.subs or {}).get(kind)
        if x is None:
            return False, "Nothing to cancel"
        x["status"], x["cancelled_at"] = "cancelled", self.now
        until = p.expert_until if kind == "expert" else p.pro_until
        return True, (f"Cancelled: no more payments. {kind.title()} stays on until "
                      f"{datetime.datetime.fromtimestamp(until, datetime.timezone.utc):%d %b %Y}.")

    def _renew_test_subs(self):
        """In the test mode nobody bills: a monthly pass renews itself when its month is about up, with a pretend
        invoice, so the whole cycle can be tried. Real ones renew only when the provider says it was paid."""
        for p in self.players.values():
            for kind, x in list((getattr(p, "subs", None) or {}).items()):
                if x.get("provider") == "test" and x.get("status") == "active":
                    until = p.expert_until if kind == "expert" else p.pro_until
                    if until - self.now < 120:
                        self.renew_subscription(p, kind, f"test-{x['order']}-{int(x.get('renewals', 0)) + 1}")

    # ------------------------------------------------------------------ Pro
    def is_expert(self, p):
        return float(getattr(p, "expert_until", 0.0) or 0.0) > self.now

    def is_pro(self, p):
        """Pro is on with a Pro pass or an Expert one (Expert includes everything in Pro)."""
        return float(getattr(p, "pro_until", 0.0) or 0.0) > self.now or self.is_expert(p)

    def tier(self, p):
        return "expert" if self.is_expert(p) else "pro" if self.is_pro(p) else "free"

    def admin_pro(self, p, days=0.0, remove=False, tier="pro"):
        """Admin: give a player Pro (or Expert) for `days` more days (added to any they already have, bought or given),
        or end it now (`remove`, bought time included). No MB move. The server saves straight after."""
        field, name = ("expert_until", "Expert") if tier == "expert" else ("pro_until", "Pro")
        if remove:
            had = float(getattr(p, field) or 0.0) > self.now
            setattr(p, field, min(float(getattr(p, field) or 0.0), self.now))
            if tier == "expert":
                self._bots_off(p, "Expert ended")
            return True, f"{name} ended" if had else f"They did not have {name}"
        setattr(p, field, max(self.now, float(getattr(p, field) or 0.0)) + float(days) * 86400)
        until = datetime.datetime.fromtimestamp(getattr(p, field), datetime.timezone.utc)
        return True, f"{name} until {until:%d %b %Y %H:%M} UTC"

    # ------------------------------------------------------------------ the free restart
    def _start_balance(self):
        return float(self.settings.get("signup_bonus", 1000.0))

    def restart_status(self, p):
        below = float(self.settings.get("restart_below", 50.0))
        days = float(self.settings.get("restart_days", 7.0))
        eq = self.equity(p)
        next_at = (p.last_restart or 0.0) + days * 86400
        status = {"below": below, "days": days, "equity": eq, "next_at": next_at if next_at > self.now else None,
                  "open_positions": len(p.hold) + len(getattr(p, "opts", [])), "eligible": False, "reason": ""}
        if days <= 0:
            status["reason"] = "There is no free restart in this game"
        elif eq >= below:
            status["reason"] = f"The free restart is for accounts below {below:,.0f} MB"
        elif p.hold or getattr(p, "opts", None):
            status["reason"] = "Close your open positions first"
        elif next_at > self.now:
            status["reason"] = "Your next free restart is available later"
        else:
            status["eligible"] = True
        return status

    def claim_restart(self, p):
        st = self.restart_status(p)
        if not st["eligible"]:
            return False, st["reason"]
        amount = self._start_balance() - p.cash
        if amount <= 0:
            return False, "You already have the starting balance"
        p.last_restart = self.now
        self.credit(p, amount, source="restart")
        self._notify(p, f"Fresh start: your cash is back to {self._start_balance():,.0f} MB. Have a look at the risk lessons on the Learn page.")
        return True, f"Your cash is back to {self._start_balance():,.0f} MB"

    # ------------------------------------------------------------------ what the pages see
    def economy_view(self, p):
        cat = self.shop_catalog()
        mine = sorted((o for o in self.shop_orders.values() if o["token"] == p.token and o["status"] != "pending"),
                      key=lambda o: -o.get("paid_at", o["created"]))[:30]
        subs = {k: {"status": v.get("status"), "price": money_text(int(v.get("price_cents", 0)), cat["currency"]),
                    "until": p.expert_until if k == "expert" else p.pro_until} for k, v in (p.subs or {}).items()
                if v.get("status") in ("active", "cancelled")}
        return {"catalog": cat, "subs": subs, "pro": self.is_pro(p), "pro_until": p.pro_until if p.pro_until > self.now else None,
                "expert": self.is_expert(p), "expert_until": p.expert_until if self.is_expert(p) else None,
                "min_age": int(self.settings.get("min_age", 13)), "deal_until": self.deal_until(p),
                "orders": [{"id": o["id"], "sku": o["sku"], "kind": o["kind"], "mb": o["mb"], "days": o["days"],
                            "price": money_text(o["price_cents"], o["currency"]), "status": o["status"],
                            "at": o.get("paid_at", o["created"])} for o in mine],
                "mb_by_source": dict(p.mb_by_source)}

    def _by_ref(self, paid):
        """Sign-ups, buyers and revenue per tracking link (`?ref=`), most sign-ups first; "" is no link."""
        rows = {}
        codes = {p.invite for p in self.players.values() if p.invite}
        refs = {p.token: ("invited by a player" if p.invited_by or p.ref in codes else p.ref or "") for p in self.players.values()}
        for p in self.players.values():
            r = rows.setdefault(refs[p.token], {"ref": refs[p.token], "signups": 0, "buyers": set(), "cents": 0})
            r["signups"] += 1
        for o in paid:
            r = rows.get(refs.get(o["token"], ""))
            if r is not None:
                r["buyers"].add(o["token"])
                r["cents"] += o["price_cents"]
        cur = self.shop_currency()
        return [{"ref": r["ref"], "signups": r["signups"], "buyers": len(r["buyers"]), "revenue_text": money_text(r["cents"], cur)}
                for r in sorted(rows.values(), key=lambda r: (-r["signups"], r["ref"]))]

    def economy_stats(self):
        """For the admin page: orders, revenue, Pro members and where the MB in the game came from. After a reset to
        Day 1 it counts from the reset (`reset_at`); the orders from before are kept (they are real payments, and can
        still be refunded by id) and summed up in `earlier`."""
        since = float(getattr(self, "reset_at", 0.0) or 0.0)
        everything = [o for o in self.shop_orders.values() if o["status"] == "paid"]
        paid = [o for o in everything if o.get("paid_at", o["created"]) >= since]
        before = [o for o in everything if o.get("paid_at", o["created"]) < since]
        orders = [o for o in self.shop_orders.values() if o["created"] >= since or o.get("paid_at", 0) >= since]
        by_day = {}
        for o in paid:
            d = int(o["paid_at"] // 86400) * 86400
            by_day[d] = by_day.get(d, 0) + o["price_cents"]
        today = int(self.now // 86400)
        last30 = [(d * 86400, by_day.get(d * 86400, 0)) for d in range(today - 29, today + 1)]   # empty days too
        sources = {}
        for p in self.players.values():
            for k, v in p.mb_by_source.items():
                sources[k] = sources.get(k, 0.0) + v
        cur = self.shop_currency()
        recent = sorted(orders, key=lambda o: -o["created"])[:40]
        return {"currency": cur, "revenue_cents": sum(o["price_cents"] for o in paid),
                "revenue_text": money_text(sum(o["price_cents"] for o in paid), cur),
                "revenue_30d_text": money_text(sum(o["price_cents"] for o in paid if o["paid_at"] > self.now - 30 * 86400), cur),
                "orders_paid": len(paid), "buyers": len({o["token"] for o in paid}),
                "refunded": sum(1 for o in orders if o["status"] == "refunded"),
                "pending": sum(1 for o in orders if o["status"] == "pending"),
                "since": since or None,
                "earlier": {"orders": len(before), "revenue_text": money_text(sum(o["price_cents"] for o in before), cur)} if before else None,
                "pro_members": sum(1 for p in self.players.values() if self.is_pro(p) and not self.is_expert(p)),
                "expert_members": sum(1 for p in self.players.values() if self.is_expert(p)),
                "pay_check": self.pay_check,
                "by_ref": self._by_ref(paid),
                "revenue_by_day": [{"day": d, "cents": c, "text": money_text(c, cur)} for d, c in last30],
                "mb_by_source": sources,
                "recent": [{"id": o["id"], "name": o["name"], "sku": o["sku"], "price": money_text(o["price_cents"], o["currency"]),
                            "status": o["status"], "at": o.get("paid_at", o["created"]), "provider": o["provider"]} for o in recent]}

    # ------------------------------------------------------------------ saving
    def shop_dump(self):
        return {"orders": list(self.shop_orders.values())}

    def shop_load(self, d):
        self.shop_orders = {o["id"]: dict(o) for o in d.get("orders", []) if isinstance(o, dict) and o.get("id")}
