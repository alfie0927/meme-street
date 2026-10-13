"""The MB economy of the learn-to-trade plan (ROADMAP.md, track M): where every MB comes from, the shop (MB packages and
the Pro pass), the age rules, spending caps and the free restart for an account that has run out.

MB are a game currency. They are bought, earned or granted, and never paid out: there is no withdrawal for players.

* **Sources.** Every MB that enters an account is counted by source: `grant` (the starting balance), `purchase` (a
  package), `challenge` (a reward), `restart` (the free restart), `refund` (taken back, negative) and `admin`.
* **The shop.** Packages of MB and a Pro pass (30 or 365 days of the Pro tools), at prices set in the `shop_packages`
  and `shop_pro` settings. A purchase is an *order*: created when the player clicks Buy, paid at the payment provider
  (or the test checkout), and completed exactly once by `complete_order`, which credits the MB or extends Pro and writes
  a `purchase` event to the money ledger (so a crash cannot lose a purchase).
* **Pro** is the income that does not depend on anyone losing: tools (advanced chart indicators, full journal
  statistics), never trading power and never a leaderboard advantage.
* **Age.** An account needs a birth year showing at least `min_age` (13); buying needs `buy_min_age` (18) and a
  confirmation. Only the year is kept.
* **Spending caps.** A default cap per rolling 30 days (`spend_cap_month_cents`), a lower cap a player can set (lowering
  works at once, raising after 24 hours), and at most `purchases_per_day` purchases a day.
* **The free restart.** An account whose equity is below `restart_below` MB, with no open positions, can top its cash
  back up to the starting balance once every `restart_days` days, for nothing.
"""
import datetime
import uuid

SOURCES = ("grant", "purchase", "challenge", "restart", "refund", "admin")
DEFAULT_PACKAGES = [
    {"sku": "mb100", "mb": 100, "price_cents": 99},
    {"sku": "mb500", "mb": 500, "price_cents": 399},
    {"sku": "mb1000", "mb": 1000, "price_cents": 699},
    {"sku": "mb5000", "mb": 5000, "price_cents": 2499},
    {"sku": "mb10000", "mb": 10000, "price_cents": 3999},
]
DEFAULT_PRO = [
    {"sku": "pro30", "days": 30, "price_cents": 499},
    {"sku": "pro365", "days": 365, "price_cents": 3999},
]
PRO_FEATURES = [
    "32 more chart indicators: Bollinger bands, MACD, Ichimoku, VWAP, ATR, ADX, Stochastic RSI, OBV, pivot points and more "
    "(17, including every moving average, RSI and the drawing tools, are free)",
    "Full trading-journal statistics: results by setup, R-multiples, best and worst setups",
    "A Pro badge on your profile",
]
ORDER_TTL = 86400            # an order that is not paid within a day expires
PLAYER_FIELDS = ("birth_year", "pro_until", "last_restart", "mb_by_source", "spend_cap_cents", "spend_cap_pending",
                 "challenge_mb")


def init_player(p):
    p.birth_year = None          # only the year is kept (the age rules need nothing more)
    p.pro_until = 0.0            # real time until which the Pro tools are on
    p.last_restart = 0.0         # when the player last used the free restart
    p.mb_by_source = {}          # source -> MB received from it
    p.spend_cap_cents = None     # a player's own lower spending cap (cents per 30 days), or None for the default
    p.spend_cap_pending = None   # [cents, when it takes effect]: a raised cap waits a day
    p.challenge_mb = {}          # week number -> MB earned from challenges that week (for the weekly cap)


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
    p.last_restart = float(p.last_restart or 0.0)


def money_text(cents, currency="usd"):
    symbol = {"usd": "US$", "eur": "€", "gbp": "£"}.get(currency, currency.upper() + " ")
    return f"{symbol}{cents / 100:,.2f}"


class EconomyMixin:
    """Mixed into the Engine. Uses `self.now`, `self.settings`, `self.players`, `self.equity`, `self._emit`,
    `self._ratio` and `self._rebase_peak`."""

    def _init_economy(self):
        self.shop_orders = {}        # order id -> the order (see create_order)

    # ------------------------------------------------------------------ the catalogue
    def shop_currency(self):
        return str(self.settings.get("shop_currency", "usd"))

    def shop_catalog(self):
        packages = [dict(x) for x in self.settings.get("shop_packages", DEFAULT_PACKAGES)]
        pro = [dict(x) for x in self.settings.get("shop_pro", DEFAULT_PRO)]
        cur = self.shop_currency()
        for x in packages:
            x["kind"] = "package"
            x["price"] = money_text(int(x["price_cents"]), cur)
            x["per_100"] = money_text(round(int(x["price_cents"]) * 100 / max(int(x["mb"]), 1)), cur)
        for x in pro:
            x["kind"] = "pro"
            x["price"] = money_text(int(x["price_cents"]), cur)
        return {"packages": packages, "pro": pro, "currency": cur, "pro_features": PRO_FEATURES}

    def _sku(self, sku):
        cat = self.shop_catalog()
        return next((x for x in cat["packages"] + cat["pro"] if x["sku"] == sku), None)

    # ------------------------------------------------------------------ age
    def _year(self):
        return datetime.datetime.fromtimestamp(self.now, datetime.timezone.utc).year

    def age_years(self, p):
        """The age a player reaches this year (from the birth year alone), or None if unknown."""
        return None if not p.birth_year else self._year() - int(p.birth_year)

    def birth_year_problem(self, year, purpose="signup"):
        """Why a birth year is not acceptable, or None."""
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

    def set_birth_year(self, p, year):
        if p.birth_year:
            return False, "Your birth year is already set (an admin can correct it)"
        bad = self.birth_year_problem(year)
        if bad:
            return False, bad
        p.birth_year = int(year)
        return True, "Saved"

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
        """The cap that applies now, in cents per rolling 30 days (a raised cap waits a day before it counts)."""
        default = int(self.settings.get("spend_cap_month_cents", 15000))
        pend = p.spend_cap_pending
        if pend and self.now >= pend[1]:
            p.spend_cap_cents, p.spend_cap_pending = (None if pend[0] >= default else int(pend[0])), None
        own = p.spend_cap_cents
        return default if own is None else min(default, int(own))

    def set_spend_cap(self, p, cents):
        """Lowering takes effect at once; raising (or going back to the default) after 24 hours, so it is never a
        decision made in the heat of a loss."""
        try:
            cents = max(0, int(cents))
        except (TypeError, ValueError):
            return False, "Give the cap in whole cents"
        current = self.spend_cap(p)
        if cents <= current:
            p.spend_cap_cents, p.spend_cap_pending = cents, None
            return True, f"Your cap is now {money_text(cents, self.shop_currency())} per 30 days"
        p.spend_cap_pending = [cents, self.now + 86400]
        return True, f"Your cap rises to {money_text(min(cents, int(self.settings.get('spend_cap_month_cents', 15000))), self.shop_currency())} in 24 hours"

    def buy_problem(self, p, item, adult_confirmed):
        """Why this player may not buy this item now, or None."""
        if not item:
            return "Unknown item"
        need = int(self.settings.get("buy_min_age", 18))
        age = self.age_years(p)
        if age is None:
            return "Tell us the year you were born first (Profile, Account)"
        if age < need or not adult_confirmed:
            return f"Purchases are for people aged {need} or over"
        if self.spent_cents(p) + int(item["price_cents"]) > self.spend_cap(p):
            return ("That would take you over your spending cap of " + money_text(self.spend_cap(p), self.shop_currency())
                    + " in 30 days")
        per_day = int(self.settings.get("purchases_per_day", 3))
        if per_day > 0 and self._purchases_since(p, 86400) >= per_day:
            return f"You have made {per_day} purchases today: the shop opens again tomorrow"
        return None

    # ------------------------------------------------------------------ orders
    def create_order(self, p, sku, provider, adult_confirmed=False):
        item = self._sku(sku)
        bad = self.buy_problem(p, item, adult_confirmed)
        if bad:
            return None, bad
        oid = uuid.uuid4().hex[:20]
        order = {"id": oid, "token": p.token, "name": p.name, "sku": item["sku"], "kind": item["kind"],
                 "mb": int(item.get("mb", 0)), "days": int(item.get("days", 0)), "price_cents": int(item["price_cents"]),
                 "currency": self.shop_currency(), "status": "pending", "created": self.now, "provider": provider,
                 "provider_ref": None}
        self.shop_orders[oid] = order
        return order, ""

    def complete_order(self, oid, provider_ref=None, amount_cents=None):
        """The payment provider says the order is paid: credit the MB or extend Pro, exactly once."""
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
        self._emit("purchase", p, cash=float(o["mb"]), notional=float(o["mb"]), order=oid, sku=o["sku"], days=o["days"],
                   price_cents=o["price_cents"], source="purchase")
        if o["kind"] == "pro":
            self._notify(p, f"Thank you! Meme Street Pro is on until {datetime.datetime.fromtimestamp(p.pro_until, datetime.timezone.utc):%d %b %Y}.")
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
            start = max(self.now if at is None else at, float(p.pro_until or 0.0))     # (a replay passes the event's time)
            p.pro_until = start + o["days"] * 86400

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
        if p.pro_until > self.now:
            p.pro_until = max(self.now, float(p.pro_until) - o["days"] * 86400)
        return True, "Refunded; the Pro time was removed"

    def _expire_orders(self):
        for o in self.shop_orders.values():
            if o["status"] == "pending" and self.now - o["created"] > ORDER_TTL:
                o["status"] = "expired"

    # ------------------------------------------------------------------ Pro
    def is_pro(self, p):
        return float(getattr(p, "pro_until", 0.0) or 0.0) > self.now

    def admin_pro(self, p, days=0.0, remove=False):
        """Admin: give a player Pro for `days` more days (added to any Pro they already have, bought or given), or end it
        now (`remove`, bought time included). Pro is tools only, so no MB move. The server saves straight after."""
        if remove:
            had = self.is_pro(p)
            p.pro_until = min(float(p.pro_until or 0.0), self.now)
            return True, "Pro ended" if had else "They did not have Pro"
        p.pro_until = max(self.now, float(p.pro_until or 0.0)) + float(days) * 86400
        until = datetime.datetime.fromtimestamp(p.pro_until, datetime.timezone.utc)
        return True, f"Pro until {until:%d %b %Y %H:%M} UTC"

    # ------------------------------------------------------------------ the free restart
    def _start_balance(self):
        return float(self.settings.get("signup_bonus", 1000.0))

    def restart_status(self, p):
        below = float(self.settings.get("restart_below", 50.0))
        days = float(self.settings.get("restart_days", 7.0))
        eq = self.equity(p)
        next_at = (p.last_restart or 0.0) + days * 86400
        status = {"below": below, "days": days, "equity": eq, "next_at": next_at if next_at > self.now else None,
                  "open_positions": len(p.hold), "eligible": False, "reason": ""}
        if days <= 0:
            status["reason"] = "There is no free restart in this game"
        elif eq >= below:
            status["reason"] = f"The free restart is for accounts below {below:,.0f} MB"
        elif p.hold:
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
        cap = self.spend_cap(p)
        return {"catalog": cat, "pro": self.is_pro(p), "pro_until": p.pro_until if self.is_pro(p) else None,
                "birth_year_set": bool(p.birth_year), "age_ok_to_buy": (self.age_years(p) or 0) >= int(self.settings.get("buy_min_age", 18)),
                "buy_min_age": int(self.settings.get("buy_min_age", 18)), "min_age": int(self.settings.get("min_age", 13)),
                "spent_30d": self.spent_cents(p), "spent_30d_text": money_text(self.spent_cents(p), cat["currency"]),
                "cap": cap, "cap_text": money_text(cap, cat["currency"]),
                "cap_default": int(self.settings.get("spend_cap_month_cents", 15000)),
                "cap_pending": p.spend_cap_pending, "purchases_per_day": int(self.settings.get("purchases_per_day", 3)),
                "orders": [{"id": o["id"], "sku": o["sku"], "kind": o["kind"], "mb": o["mb"], "days": o["days"],
                            "price": money_text(o["price_cents"], o["currency"]), "status": o["status"],
                            "at": o.get("paid_at", o["created"])} for o in mine],
                "restart": self.restart_status(p), "mb_by_source": dict(p.mb_by_source),
                "challenge_week": self.challenge_week_status(p) if hasattr(self, "challenge_week_status") else None}

    def economy_stats(self):
        """For the admin page: orders, revenue, Pro members and where the MB in the game came from."""
        paid = [o for o in self.shop_orders.values() if o["status"] == "paid"]
        by_day = {}
        for o in paid:
            d = int(o["paid_at"] // 86400) * 86400
            by_day[d] = by_day.get(d, 0) + o["price_cents"]
        sources = {}
        for p in self.players.values():
            for k, v in p.mb_by_source.items():
                sources[k] = sources.get(k, 0.0) + v
        cur = self.shop_currency()
        recent = sorted(self.shop_orders.values(), key=lambda o: -o["created"])[:40]
        return {"currency": cur, "revenue_cents": sum(o["price_cents"] for o in paid),
                "revenue_text": money_text(sum(o["price_cents"] for o in paid), cur),
                "revenue_30d_text": money_text(sum(o["price_cents"] for o in paid if o["paid_at"] > self.now - 30 * 86400), cur),
                "orders_paid": len(paid), "buyers": len({o["token"] for o in paid}),
                "refunded": sum(1 for o in self.shop_orders.values() if o["status"] == "refunded"),
                "pending": sum(1 for o in self.shop_orders.values() if o["status"] == "pending"),
                "pro_members": sum(1 for p in self.players.values() if self.is_pro(p)),
                "revenue_by_day": [{"day": d, "cents": c} for d, c in sorted(by_day.items())][-30:],
                "mb_by_source": sources,
                "recent": [{"id": o["id"], "name": o["name"], "sku": o["sku"], "price": money_text(o["price_cents"], o["currency"]),
                            "status": o["status"], "at": o.get("paid_at", o["created"]), "provider": o["provider"]} for o in recent]}

    # ------------------------------------------------------------------ saving
    def shop_dump(self):
        return {"orders": list(self.shop_orders.values())}

    def shop_load(self, d):
        self.shop_orders = {o["id"]: dict(o) for o in d.get("orders", []) if isinstance(o, dict) and o.get("id")}
