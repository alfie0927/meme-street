"""Options on the stocks (everyone can trade them): calls and puts, bought and sold back before expiry, or settled in
cash at expiry.

* **Contracts.** One contract is on one share. A **call** pays `max(0, price - strike)` at expiry, a **put**
  `max(0, strike - price)`. They are European and cash-settled: nothing is ever delivered, and the payoff is worked out
  from the stock's price at the expiry time. Only companies and commodities have options (not the index, the funds or the
  leveraged products).
* **Expiries.** At the close of the regular session (the end of a game day's trading): the next close, and the closes 2,
  7 and 30 game days out. A contract can be bought until a minute before it expires.
* **Strikes.** Thirteen around the price, about 2.5% apart, on round numbers.
* **Prices.** Black-Scholes, with the interest rate `rf` of the price model and an *implied volatility* that is the
  stock's own: the higher of its stated volatility and what it has really done over the last 20 game days, or what it
  is doing now, plus a premium (`option_vol_premium`, 10%: in real markets options cost a little more than the moves
  they insure, the variance risk premium). If the company reports earnings before the expiry, the price includes a jump
  of about three ordinary days. You buy at the **ask** and sell at the **bid**, `option_spread` (6%) of the price apart,
  and at least `option_min_spread` (0.1%) of the share price, so very cheap far-out contracts are not cheap to trade.
  The usual 0.1% fee applies to what is paid or received.
* **No free money.** With the premium and the spread, buying options at random loses money on average (test_options.py
  checks calls, puts and straddles); options reward a view on direction or volatility that turns out right.

The house is the other side of every contract, as it is for shares: what a player pays goes into the house reserve and
payoffs come out of it, so the books still balance (`Engine.total_tokens`). Every purchase, sale and settlement is in
the money ledger (`opt_buy`, `opt_sell`, `opt_expire`), so a crash loses none.
"""
import math
import uuid

KINDS = ("call", "put")
EXPIRY_DAYS = (0, 2, 7, 30)          # the next close, and the closes this many game days after it
STRIKES_EACH_SIDE = 6
MAX_POSITIONS = 40                   # open option positions a player may hold at once
EARNINGS_JUMP = 3.0                  # an earnings report moves a stock about this many ordinary days' moves


def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs(S, K, T, sigma, kind, r=0.015, extra_var=0.0):
    """(price, delta) of a European call or put. `T` in years, `sigma` a year; `extra_var` adds a known jump's variance
    (an earnings report before expiry)."""
    if S <= 0 or K <= 0:
        return 0.0, 0.0
    var = max(sigma, 1e-6) ** 2 * max(T, 0.0) + max(extra_var, 0.0)
    if var <= 1e-14:
        intrinsic = max(0.0, S - K) if kind == "call" else max(0.0, K - S)
        return intrinsic, (1.0 if S > K else 0.0) if kind == "call" else (-1.0 if S < K else 0.0)
    sd = math.sqrt(var)
    disc = math.exp(-r * max(T, 0.0))
    d1 = (math.log(S / K) + r * max(T, 0.0) + 0.5 * var) / sd
    d2 = d1 - sd
    if kind == "call":
        return S * norm_cdf(d1) - K * disc * norm_cdf(d2), norm_cdf(d1)
    return K * disc * norm_cdf(-d2) - S * norm_cdf(-d1), norm_cdf(d1) - 1.0


def nice_step(price):
    """A round strike spacing of about 2.5% of the price: 1, 2, 2.5 or 5 times a power of ten."""
    raw = max(price * 0.025, 1e-6)
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def strikes_for(price):
    step = nice_step(price)
    mid = round(price / step) * step
    out = [round(mid + k * step, 6) for k in range(-STRIKES_EACH_SIDE, STRIKES_EACH_SIDE + 1)]
    return [k for k in out if k > 0]


def quote(S, K, T, sigma, kind, r=0.015, extra_var=0.0, spread=0.06, min_spread=0.001):
    """What a contract costs to buy (ask) and fetches when sold (bid), around its Black-Scholes value."""
    mid, delta = bs(S, K, T, sigma, kind, r, extra_var)
    half = max(spread * mid, min_spread * S) / 2
    tick = 0.01 if S >= 1 else 0.0001
    ask = math.ceil((mid + half) / tick) * tick
    bid = max(0.0, math.floor((mid - half) / tick) * tick)
    return {"mid": mid, "bid": bid, "ask": max(ask, tick), "delta": delta}


def payoff(kind, K, S):
    return max(0.0, S - K) if kind == "call" else max(0.0, K - S)


def init_player(p):
    p.opts = []          # open option positions: {"id", "tk", "kind", "K", "exp", "qty", "cost", "fee"}


def dump_player(p):
    return {"opts": [dict(o) for o in p.opts]}


def load_player(p, x):
    p.opts = [dict(o) for o in (x or {}).get("opts", []) if isinstance(o, dict) and o.get("kind") in KINDS]


class OptionsMixin:
    """Mixed into the Engine. Uses `self.stocks`, `self.now`, `self.settings`, `self.house`, `self.fees`, `self._emit`,
    `self._session_lengths` and the price model's `rf`."""

    # ------------------------------------------------------------------ the market
    def option_ok(self, s):
        return s is not None and s.asset_type in ("equity", "commodity") and getattr(s, "spec", None) is None and s.price > 0

    def option_expiries(self, now=None):
        """The expiry times on offer: the regular session's close today (if more than a minute away, else tomorrow's),
        then 2, 7 and 30 game days after it."""
        now = self.now if now is None else now
        D = 1800.0
        pre, post = self._session_lengths()
        close_phase = D - post if (pre > 0 or post > 0) else D
        first = math.floor(now / D) * D + close_phase
        if first - now < 60:
            first += D
        return [first + k * D for k in EXPIRY_DAYS]

    def _rf(self):
        m = getattr(self, "model", None)
        return float(m.p.get("rf", 0.015)) if m is not None else 0.015

    def option_vol(self, s):
        """The implied volatility (a game year): the highest of the stated volatility, the last 20 game days' realised
        volatility and today's, plus the premium."""
        days = list(getattr(s, "days", ()))[-21:]
        realised = 0.0
        if len(days) >= 6:
            r = [math.log(b[4] / a[4]) for a, b in zip(days, days[1:]) if a[4] > 0 and b[4] > 0]
            if len(r) >= 5:
                m = sum(r) / len(r)
                realised = math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1)) * math.sqrt(365)
        now_vol = s.vol * self._vol_scale() * self._vol_multiplier(s)
        base = max(s.vol * self._vol_scale(), realised, now_vol)
        return base * (1 + float(self.settings.get("option_vol_premium", 0.10)))

    def option_quote(self, s, kind, K, exp, now=None):
        now = self.now if now is None else now
        T = max(0.0, (exp - now) / (365 * 1800.0))
        sigma = self.option_vol(s)
        extra = 0.0
        earn = getattr(s, "next_earn", None)
        if earn and now < earn <= exp:
            extra = (EARNINGS_JUMP * sigma / math.sqrt(365)) ** 2
        q = quote(s.price, K, T, sigma, kind, self._rf(), extra, float(self.settings.get("option_spread", 0.06)),
                  float(self.settings.get("option_min_spread", 0.001)))
        q["iv"] = sigma
        return q

    def option_chain(self, ticker):
        s = self.stocks.get(ticker)
        if not self.option_ok(s):
            return {"error": "No options on this listing"}
        exps = self.option_expiries()
        rows = []
        for exp in exps:
            for K in strikes_for(s.price):
                c, pt = self.option_quote(s, "call", K, exp), self.option_quote(s, "put", K, exp)
                rows.append({"exp": exp, "K": K, "call": {k: round(v, 6) for k, v in c.items()},
                             "put": {k: round(v, 6) for k, v in pt.items()}})
        earn = s.next_earn if getattr(s, "next_earn", None) and s.next_earn <= exps[-1] else None
        return {"ticker": ticker, "price": s.price, "expiries": exps, "rows": rows, "now": self.now, "earnings": earn,
                "iv": self.option_vol(s), "fee": 0.001}

    # ------------------------------------------------------------------ trading
    def buy_option(self, p, ticker, kind, K, exp, amount=None, qty=None):
        """Buy `qty` contracts, or as many as `amount` MB buys (fee included). Returns (ok, message)."""
        s = self.stocks.get(ticker)
        if not self.option_ok(s):
            return False, "No options on this listing"
        if kind not in KINDS:
            return False, "A call or a put"
        if getattr(p, "guest", False):
            return False, "Create an account to trade"
        gate = self.email_gate(p) if hasattr(self, "email_gate") else None
        if gate:
            return False, gate
        try:
            K, exp = float(K), float(exp)
        except (TypeError, ValueError):
            return False, "Bad contract"
        if not any(abs(exp - e) < 1 for e in self.option_expiries()):
            return False, "That expiry is not on offer"
        if not any(abs(K - k) < 1e-6 * max(1.0, K) for k in strikes_for(s.price)):
            return False, "That strike is not on offer any more: pick one from the chain"
        if self.now - p.last_trade.get("opt:" + ticker, 0) < 1.0:
            return False, "Cooldown: 1s between option trades in the same stock"
        q = self.option_quote(s, kind, K, exp)
        ask = q["ask"]
        if ask <= 0:
            return False, "Not available"
        if qty is None:
            try:
                amount = float(amount)
            except (TypeError, ValueError):
                return False, "Bad amount"
            if not (math.isfinite(amount) and amount > 0):
                return False, "Bad amount"
            qty = amount / (ask * (1 + 0.001))
        qty = float(qty)
        if not (math.isfinite(qty) and qty > 0):
            return False, "Bad size"
        cost = qty * ask
        fee = cost * 0.001
        if cost < 1:
            return False, "Too small (at least 1 MB)"
        if cost + fee > max(0.0, p.cash) + 1e-9:
            return False, f"Not enough cash ({max(0.0, p.cash):,.2f} MB)"
        pos = next((o for o in p.opts if o["tk"] == ticker and o["kind"] == kind and abs(o["K"] - K) < 1e-9
                    and abs(o["exp"] - exp) < 1), None)
        if pos is None:
            if len(p.opts) >= MAX_POSITIONS:
                return False, f"At most {MAX_POSITIONS} option positions at once"
            pos = {"id": uuid.uuid4().hex[:10], "tk": ticker, "kind": kind, "K": K, "exp": exp, "qty": 0.0, "cost": 0.0,
                   "fee": 0.0}
            p.opts.append(pos)
        pos["qty"] += qty
        pos["cost"] += cost
        pos["fee"] += fee
        p.cash -= cost + fee
        self.house += cost
        self.fees += fee
        p.fees_paid += fee
        p.last_trade["opt:" + ticker] = self.now
        p.trades += 1
        self.trades_total += 1
        self._emit("opt_buy", p, ticker, shares=qty, price=ask, cash=-(cost + fee), house=cost, fee=fee, notional=cost,
                   id=pos["id"], otype=kind, K=K, exp=exp)
        if hasattr(self, "_opt_traded"):
            self._opt_traded(p, ticker)
        return True, f"Bought {qty:,.2f} {ticker} {self._opt_name(kind, K, exp)} at {ask:,.4g} MB ({cost:,.2f} MB)"

    def sell_option(self, p, pos_id, fraction=1.0):
        """Sell back `fraction` of an option position at the bid."""
        pos = next((o for o in p.opts if o["id"] == pos_id), None)
        if pos is None:
            return False, "No such option position"
        s = self.stocks.get(pos["tk"])
        if s is None:
            return False, "The stock is gone: the option settles by itself"
        try:
            fraction = min(1.0, max(0.0, float(fraction)))
        except (TypeError, ValueError):
            return False, "Bad size"
        if fraction <= 0:
            return False, "Bad size"
        if self.now - p.last_trade.get("opt:" + pos["tk"], 0) < 1.0:
            return False, "Cooldown: 1s between option trades in the same stock"
        bid = self.option_quote(s, pos["kind"], pos["K"], pos["exp"])["bid"]
        qty = pos["qty"] * fraction
        proceeds = qty * bid
        fee = proceeds * 0.001
        cost_part, fee_part = pos["cost"] * fraction, pos["fee"] * fraction
        pnl = proceeds - fee - cost_part - fee_part
        self._close_option(p, pos, fraction)
        p.cash += proceeds - fee
        self.house -= proceeds
        self.fees += fee
        p.fees_paid += fee
        p.realized[pos["tk"]] = p.realized.get(pos["tk"], 0.0) + pnl
        p.last_trade["opt:" + pos["tk"]] = self.now
        p.trades += 1
        self.trades_total += 1
        self._emit("opt_sell", p, pos["tk"], shares=-qty, price=bid, cash=proceeds - fee, house=-proceeds, fee=fee,
                   notional=proceeds, pnl=pnl, id=pos["id"], fraction=fraction, otype=pos["kind"], K=pos["K"], exp=pos["exp"])
        if hasattr(self, "_opt_traded"):
            self._opt_traded(p, pos["tk"])
        return True, f"Sold {qty:,.2f} {pos['tk']} {self._opt_name(pos['kind'], pos['K'], pos['exp'])} at {bid:,.4g} MB ({pnl:+,.2f} MB)"

    @staticmethod
    def _close_option(p, pos, fraction):
        if fraction >= 1 - 1e-9:
            p.opts.remove(pos)
        else:
            for k in ("qty", "cost", "fee"):
                pos[k] *= 1 - fraction

    def _opt_name(self, kind, K, exp):
        mins = max(0, int((exp - self.now) // 60))
        return f"{K:,.4g} {kind} ({mins // 60}h {mins % 60:02d}m to expiry)"

    def _settle_options(self, ticker=None, price=None):
        """Every tick: contracts that have reached their expiry are settled in cash at their payoff (no fee). With
        `ticker`, every contract on that stock now, at `price` (a stock that is leaving the market)."""
        for p in list(self.players.values()):
            if not p.opts:
                continue
            for pos in list(p.opts):
                if ticker is not None:
                    if pos["tk"] != ticker:
                        continue
                    S = price
                elif pos["exp"] > self.now:
                    continue
                else:
                    s = self.stocks.get(pos["tk"])
                    S = s.price if s is not None else 0.0
                pay = pos["qty"] * payoff(pos["kind"], pos["K"], S)
                pnl = pay - pos["cost"] - pos["fee"]
                p.opts.remove(pos)
                p.cash += pay
                self.house -= pay
                p.realized[pos["tk"]] = p.realized.get(pos["tk"], 0.0) + pnl
                self._emit("opt_expire", p, pos["tk"], shares=-pos["qty"], price=S, cash=pay, house=-pay, notional=pay,
                           pnl=pnl, id=pos["id"], otype=pos["kind"], K=pos["K"], exp=pos["exp"])
                what = "expired worthless" if pay <= 0 else f"paid {pay:,.2f} MB"
                if hasattr(self, "_notify"):
                    self._notify(p, f"Your {pos['tk']} {pos['K']:,.4g} {pos['kind']} {what} ({pnl:+,.2f} MB).")

    def options_value(self, p):
        """What a player's options would fetch now (at the bid): part of their equity."""
        v = 0.0
        for pos in p.opts:
            s = self.stocks.get(pos["tk"])
            if s is not None and pos["qty"] > 0:
                v += pos["qty"] * self.option_quote(s, pos["kind"], pos["K"], pos["exp"])["bid"]
        return v

    def options_view(self, p):
        out = []
        for pos in p.opts:
            s = self.stocks.get(pos["tk"])
            q = self.option_quote(s, pos["kind"], pos["K"], pos["exp"]) if s is not None else {"bid": 0.0, "delta": 0.0}
            value = pos["qty"] * q["bid"]
            out.append({"id": pos["id"], "tk": pos["tk"], "kind": pos["kind"], "K": pos["K"], "exp": pos["exp"],
                        "qty": round(pos["qty"], 4), "cost": round(pos["cost"] + pos["fee"], 4), "bid": round(q["bid"], 6),
                        "value": round(value, 4), "pnl": round(value - pos["cost"] - pos["fee"], 4),
                        "delta": round(q["delta"], 3), "price": s.price if s is not None else None})
        return out

    def _apply_option_event(self, p, ev):
        """Replay an option event from the ledger after a crash."""
        x, kind = ev["extra"], ev["kind"]
        p.cash += ev["cash_delta"]
        self.house += ev["house_delta"]
        self.fees += ev["fee"]
        p.fees_paid += ev["fee"]
        if kind == "opt_buy":
            pos = next((o for o in p.opts if o["id"] == x.get("id")), None)
            if pos is None:
                pos = {"id": x.get("id"), "tk": ev["ticker"], "kind": x.get("otype"), "K": float(x.get("K")),
                       "exp": float(x.get("exp")), "qty": 0.0, "cost": 0.0, "fee": 0.0}
                p.opts.append(pos)
            pos["qty"] += ev["shares"]
            pos["cost"] += ev["notional"]
            pos["fee"] += ev["fee"]
        else:
            pos = next((o for o in p.opts if o["id"] == x.get("id")), None)
            if pos is not None:
                self._close_option(p, pos, float(x.get("fraction", 1.0)) if kind == "opt_sell" else 1.0)
            if ev["pnl"] is not None:
                p.realized[ev["ticker"]] = p.realized.get(ev["ticker"], 0.0) + ev["pnl"]
        p.trades += kind != "opt_expire"
