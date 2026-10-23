"""Options on the stocks (everyone can trade them): calls and puts, bought and sold back before expiry, or settled in
cash at expiry. Priced the way an options desk prices them, so the quotes follow the stock every second and the Greeks
behave as they do on a real chain.

* **Contracts.** One contract is on 100 shares, as on real exchanges, and only whole contracts are traded. Prices are
  quoted per share, so a contract costs 100 times its price. A **call** pays `max(0, price - strike)` a share at
  expiry, a **put** `max(0, strike - price)`. (A position's `qty` is kept in shares: 100 a contract.) They are European and cash-settled (like index options): nothing is ever delivered, and the
  payoff is worked out from the stock's price at the expiry time. Only companies and commodities have options (not the
  index, the funds or the leveraged products).
* **Expiries.** At the close of the regular session (the end of a game day's trading): the next close, and the closes 2,
  7, 30 and 90 game days out. A contract can be bought until a minute before it expires.
* **Strikes** are *listed*, as on an exchange: thirteen around the price, 2.5% to 5% apart on round numbers, when an
  expiry is first asked for. They stay until it expires, and as the price moves new ones are added so there are always
  six above and six below it (at the spacing that suits the new price).
* **The value** is Black-Scholes-Merton on the *forward*, the price the stock is expected to have at expiry: today's
  price, less a dividend that goes ex before expiry (the price drops by it on the ex-date), grown at the stock's own
  expected drift (`carry`: the price model's rate plus beta times the equity premium). Nothing is discounted, because MB
  cash earns no interest here; so a contract is worth what it is expected to pay, and a deep in-the-money call is not a
  cheaper way to borrow than leverage. Calls and puts on one strike keep put-call parity: call - put = forward - strike.
* **Implied volatility.** What the stock really does (the larger of its realised volatility over the last 20
  regular-session closes and over the last 80 game days; the stated volatility is only the noise, and the price model
  makes real moves about twice as big, so a new game or listing uses twice the stated one until it has history), with
  today's calm or storm (the engine's volatility clustering) fading out over the contract's life: a storm lifts the
  short expiries most and a calm lowers them, so the term structure slopes the way real ones do. Plus a premium
  (`option_vol_premium`, 15%: real options cost more than the moves they insure, the variance risk premium). Across
  strikes, a **skew**: lower strikes dearer for ordinary stocks (`option_skew`; puts are crash insurance), higher strikes
  dearer for the wildest (their moves jump up more than down, like meme stocks'), both wings a little dearer
  (`option_smile`); the commodities have a plain smile. If the company reports earnings before the expiry, the price
  includes a jump of about three ordinary days; once the report is out that premium is gone (the "volatility crush").
* **The Greeks** of each contract at its own implied volatility: delta (the change for a 1 MB move in the stock), gamma
  (the change in delta), theta (the change in a game day), vega (for one point of volatility), rho (for one point of
  carry), and the chance of finishing in the money.
* **Quotes.** You buy at the **ask** and sell at the **bid**, `option_spread` (6%) of the value apart and at least
  `option_min_spread` (0.1%) of the share price, so cheap far-out contracts have wide spreads; on the price ticks of the
  real markets (0.01 under 3 MB, 0.05 from 3 MB). The usual 0.1% fee applies to what is paid or received.
* **No free money.** With the premium and the spread, buying options at random loses money on average (test_options.py,
  and on the real engine across strikes, expiries and calm and stormy spells); options reward a view on direction or
  volatility that turns out right.

The house is the other side of every contract, as it is for shares: what a player pays goes into the house reserve and
payoffs come out of it, so the books still balance (`Engine.total_tokens`). Every purchase, sale and settlement is in
the money ledger (`opt_buy`, `opt_sell`, `opt_expire`), so a crash loses none.
"""
import math
import uuid

KINDS = ("call", "put")
EXPIRY_DAYS = (0, 2, 7, 30, 90)      # the next close, and the closes this many game days after it
STRIKES_EACH_SIDE = 6
MAX_POSITIONS = 40                   # open option positions a player may hold at once
MULTIPLIER = 100                     # shares a contract
MAX_CONTRACTS = 10000                # in one order
EARNINGS_JUMP = 3.0                  # an earnings report moves a stock about this many ordinary days' moves
GAME_YEAR = 365 * 1800.0             # real seconds in a game year (T is in game years)
CLUSTER_SHARE = 0.5                  # the part of a stock's variance that follows the volatility clustering (measured)


def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def smile(x, skew=0.0, curve=0.0):
    """A strike's implied volatility over the at-the-money one, for a strike `x` standard deviations from the forward:
    `skew` > 0 makes lower strikes dearer, `curve` both wings."""
    x = max(-3.0, min(3.0, x))
    return max(0.75, min(2.0, 1.0 - skew * x + curve * x * x))


def contract(S, K, T, sigma, kind, carry=0.0, event_var=0.0, div=0.0, skew=0.0, curve=0.0):
    """The value of a European call or put and its Greeks. `T` in game years; `sigma` the at-the-money volatility a game
    year; `carry` the expected growth a game year; `event_var` a known jump's variance before expiry (earnings); `div` a
    dividend that goes ex before expiry. Undiscounted (cash earns nothing in the game). Returns mid, iv (the strike's
    own), delta, gamma, theta (a game day), vega (a point of volatility), rho (a point of carry) and itm (the chance of
    finishing in the money)."""
    T = max(T, 0.0)
    g = math.exp(carry * T)
    F = (S - div if 0 < div < S else S) * g
    call = kind == "call"
    v = max(sigma, 1e-6) ** 2 * T + max(event_var, 0.0)
    if S <= 0 or K <= 0 or v <= 1e-14 or T <= 0:
        itm = 1.0 if (F > K if call else F < K) else 0.0
        return {"mid": max(0.0, F - K) if call else max(0.0, K - F), "iv": sigma, "delta": (g if call else -g) * itm,
                "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0, "itm": itm}
    sd_atm = math.sqrt(v)
    sd = sd_atm * smile(math.log(K / F) / sd_atm, skew, curve)
    iv = sd / math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * sd * sd) / sd
    d2 = d1 - sd
    n1 = norm_pdf(d1)
    decay = F * n1 * iv / (2 * math.sqrt(T))          # (what the passing of time takes, a game year)
    if call:
        n = norm_cdf(d1)
        mid, delta, rho, growth, itm = F * n - K * norm_cdf(d2), g * n, T * F * n, carry * F * n, norm_cdf(d2)
    else:
        n = norm_cdf(-d1)
        mid, delta, rho, growth, itm = K * norm_cdf(-d2) - F * n, -g * n, -T * F * n, -carry * F * n, norm_cdf(-d2)
    return {"mid": max(mid, 0.0), "iv": iv, "delta": delta, "gamma": g * g * n1 / (F * sd),
            "theta": -(decay + growth) / 365, "vega": F * n1 * math.sqrt(T) / 100, "rho": rho / 100, "itm": itm}


def tick_size(S, price):
    """The price steps of the real markets: 0.01 under 3, 0.05 from 3 (and finer on the penny stocks)."""
    return 0.0001 if S < 1 else 0.01 if price < 3 else 0.05


def quote(S, K, T, sigma, kind, carry=0.0, event_var=0.0, div=0.0, skew=0.0, curve=0.0, spread=0.06, min_spread=0.001):
    """`contract` plus what it costs to buy (ask) and fetches when sold (bid), around its value."""
    c = contract(S, K, T, sigma, kind, carry, event_var, div, skew, curve)
    half = max(spread * c["mid"], min_spread * S) / 2
    tick = tick_size(S, c["mid"])
    c["ask"] = round(max(math.ceil((c["mid"] + half) / tick - 1e-9) * tick, tick), 6)
    c["bid"] = round(max(0.0, math.floor((c["mid"] - half) / tick + 1e-9) * tick), 6)
    return c


def nice_step(price):
    """A round strike spacing of 2.5% to 5% of the price: the next of 1, 2, 2.5, 5 or 10 times a power of ten."""
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
        then 2, 7, 30 and 90 game days after it."""
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

    def option_carry(self, s):
        """The stock's expected growth a game year (the price model's drift for it): what the forward grows at."""
        m = getattr(self, "model", None)
        return float(m.drift_of(s, m.p)) if m is not None else self._rf()

    @staticmethod
    def _rv(rows, n):
        """Realised volatility (a game year) of the last `n` game-day-long candles: closes in [4]."""
        rows = list(rows)[-n - 1:]
        r = [math.log(b[4] / a[4]) for a, b in zip(rows, rows[1:]) if a[4] > 0 and b[4] > 0]
        return (math.sqrt(sum(x * x for x in r) / len(r) * 365), len(r)) if r else (0.0, 0)

    def _realised_vol(self, s):
        """What the stock really does: the larger of two estimates that predict the next game days' moves without a
        bias on the engine itself (the last 20 regular-session closes, and the last 80 game-day candles). The stated
        volatility is only the noise; the price model's trends, swings, levels and news make real moves about twice as
        big, so with little history (a new game or a new listing) twice the stated volatility stands in."""
        a, na = self._rv(getattr(s, "days", ()), 20)
        b, nb = self._rv(s.tf.get("30m", ()), 80)
        lr = s.vol * self._vol_scale()
        guess = lr * float(self.settings.get("option_vol_guess", 2.0))
        if max(na, nb) < 10:
            return max(a, b, guess)
        return max(a, b, lr)

    def option_vol(self, s, T=0.0):
        """The at-the-money implied volatility (a game year) for an expiry `T` game years away: what the stock really does
        (`_realised_vol`), scaled by the volatility clustering of the moment fading back to normal over the contract's
        life (at the engine's own pace, `vol_cluster_decay_days`; half the variance follows it), plus the premium."""
        m = self._vol_multiplier(s)
        kt = math.log(2) / max(0.05, float(self.settings.get("vol_cluster_decay_days", 1.0))) * max(T, 0.0) * 365
        if kt > 1e-9:
            m = 1 + (m - 1) * (1 - math.exp(-kt)) / kt          # the average multiplier until expiry
        base = self._realised_vol(s) * math.sqrt((1 - CLUSTER_SHARE) + CLUSTER_SHARE * m * m)
        return base * (1 + float(self.settings.get("option_vol_premium", 0.15)))

    def option_skew(self, s):
        """(skew, curve) of the stock's smile. Ordinary stocks: a put skew (lower strikes dearer), turning into a call skew
        for the wildest (volatility 0.4 to 1.2 a year: their moves jump up more than down, like meme stocks'); none for
        the commodities; the same curvature for all."""
        curve = float(self.settings.get("option_smile", 0.08))
        if s.asset_type != "equity":
            return 0.0, curve
        lr = s.vol * self._vol_scale()
        return float(self.settings.get("option_skew", 0.08)) * max(-1.0, min(1.0, (0.8 - lr) / 0.4)), curve

    def _option_inputs(self, s, exp, now):
        """(T, sigma, carry, event variance, dividend) of a contract on `s` expiring at `exp`."""
        T = max(0.0, (exp - now) / GAME_YEAR)
        sigma = self.option_vol(s, T)
        extra = 0.0
        earn = getattr(s, "next_earn", None)
        if earn and now < earn <= exp:
            extra = (EARNINGS_JUMP * self._realised_vol(s) / math.sqrt(365)) ** 2
        div = getattr(s, "div", None)
        d = min(div["amt"], s.price * 0.2) if div and now < div["t"] <= exp else 0.0     # (the engine caps it the same)
        return T, sigma, self.option_carry(s), extra, d

    def option_quote(self, s, kind, K, exp, now=None):
        now = self.now if now is None else now
        T, sigma, carry, extra, div = self._option_inputs(s, exp, now)
        skew, curve = self.option_skew(s)
        return quote(s.price, K, T, sigma, kind, carry, extra, div, skew, curve,
                     float(self.settings.get("option_spread", 0.06)), float(self.settings.get("option_min_spread", 0.001)))

    def atm_vol(self, s, exp):
        """The at-the-money implied volatility of one expiry, earnings included (the term structure)."""
        T, sigma, _, extra, _ = self._option_inputs(s, exp, self.now)
        return math.sqrt(sigma * sigma + extra / T) if T > 0 else sigma

    def listed_strikes(self, s, exp):
        """The strikes listed for one expiry. Like an exchange, the game lists thirteen around the price when the expiry is
        first asked for and keeps them until it expires; as the price moves, new ones are added so there are always six
        above and six below it. (Not saved: after a restart an expiry is listed again, with every strike still held.)"""
        book = self.__dict__.setdefault("_opt_book", {})
        key = (s.ticker, int(round(exp)))
        ks = book.get(key)
        if ks is None:
            if len(book) > 4000:
                for k in [k for k in book if k[1] < self.now]:
                    del book[k]
            ks = book[key] = {o["K"] for p in self.players.values() for o in p.opts
                              if o["tk"] == s.ticker and abs(o["exp"] - exp) < 1}
        ks.update(strikes_for(s.price))
        return sorted(ks)

    def option_chain(self, ticker, exp=None):
        """One expiry of a stock's chain: the thirteen listed strikes nearest the price, each call and put with its bid,
        ask, value, implied volatility, Greeks and open interest (what the players hold), and the at-the-money volatility
        of every expiry. Worked out once a second however many people are looking."""
        s = self.stocks.get(ticker)
        if not self.option_ok(s):
            return {"error": "No options on this listing"}
        exps = self.option_expiries()
        try:
            exp = next((e for e in exps if abs(e - float(exp)) < 1), exps[1]) if exp is not None else exps[1]
        except (TypeError, ValueError):
            exp = exps[1]
        cache = self.__dict__.setdefault("_chain_cache", {})
        hit = cache.get((ticker, exp))
        if hit and hit[0] == self.now:
            return hit[1]
        ks = sorted(sorted(self.listed_strikes(s, exp), key=lambda k: abs(k - s.price))[:2 * STRIKES_EACH_SIDE + 1])
        oi = {}
        for p in self.players.values():
            for o in p.opts:
                if o["tk"] == ticker and abs(o["exp"] - exp) < 1:
                    oi[(o["kind"], o["K"])] = oi.get((o["kind"], o["K"]), 0.0) + o["qty"]
        rows = []
        for K in ks:
            row = {"K": K}
            for kind in KINDS:
                q = {k: round(v, 6) for k, v in self.option_quote(s, kind, K, exp).items()}
                q["oi"] = round(oi.get((kind, K), 0.0) / MULTIPLIER, 2)
                row[kind] = q
            rows.append(row)
        T, _, carry, _, div = self._option_inputs(s, exp, self.now)
        earn = getattr(s, "next_earn", None)
        out = {"ticker": ticker, "price": s.price, "exp": exp, "expiries": exps, "rows": rows, "now": self.now,
               "term": [round(self.atm_vol(s, e), 4) for e in exps], "carry": round(carry, 4),
               "forward": round((s.price - div) * math.exp(carry * T), 6), "div": round(div, 6) or None,
               "div_t": s.div["t"] if div else None, "earnings": earn if earn and self.now < earn <= exp else None,
               "iv": round(self.atm_vol(s, exp), 4), "fee": 0.001}
        cache[(ticker, exp)] = (self.now, out)
        return out

    # ------------------------------------------------------------------ trading
    def buy_option(self, p, ticker, kind, K, exp, amount=None, contracts=None):
        """Buy whole `contracts` (100 shares each), or as many whole ones as `amount` MB buys, fee included (the bots).
        Returns (ok, message)."""
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
        exp = next(e for e in self.option_expiries() if abs(exp - e) < 1)
        listed = self.listed_strikes(s, exp)
        if not any(abs(K - k) < 1e-6 * max(1.0, K) for k in listed):
            return False, "That strike is not listed: pick one from the chain"
        K = min(listed, key=lambda k: abs(k - K))
        if self.now - p.last_trade.get("opt:" + ticker, 0) < 1.0:
            return False, "Cooldown: 1s between option trades in the same stock"
        q = self.option_quote(s, kind, K, exp)
        ask = q["ask"]
        if ask <= 0:
            return False, "Not available"
        each = ask * MULTIPLIER                       # one contract
        try:
            if contracts is None:
                amount = float(amount)
                if not (math.isfinite(amount) and amount > 0):
                    return False, "Bad amount"
                n = int(amount / (each * 1.001) + 1e-9)
                if n < 1:
                    return False, f"Not enough for one contract ({each * 1.001:,.2f} MB with the fee)"
            else:
                n = float(contracts)
                if not (math.isfinite(n) and n >= 1 and n == int(n)):
                    return False, "Whole contracts only: 1 or more"
                n = int(n)
        except (TypeError, ValueError):
            return False, "Bad size"
        if n > MAX_CONTRACTS:
            return False, f"At most {MAX_CONTRACTS:,} contracts in one order"
        qty = float(n * MULTIPLIER)
        cost = qty * ask
        fee = cost * 0.001
        if cost < 1:
            return False, "Too small (at least 1 MB)"
        if cost + fee > max(0.0, p.cash) + 1e-9:
            return False, (f"Not enough cash: {n:,} contract{'s' if n != 1 else ''} cost {cost + fee:,.2f} MB with the fee, "
                           f"you have {max(0.0, p.cash):,.2f} MB")
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
        return True, (f"Bought {n:,} {ticker} {self._opt_name(kind, K, exp)} contract{'s' if n != 1 else ''} at {ask:,.4g} "
                      f"MB a share: {cost:,.2f} MB")

    def sell_option(self, p, pos_id, fraction=1.0, contracts=None):
        """Sell back whole `contracts` of an option position at the bid (all of it if that is all there is), or a
        `fraction` of it (the bots and Close all sell everything)."""
        pos = next((o for o in p.opts if o["id"] == pos_id), None)
        if pos is None:
            return False, "No such option position"
        s = self.stocks.get(pos["tk"])
        if s is None:
            return False, "The stock is gone: the option settles by itself"
        try:
            if contracts is not None:
                n = float(contracts)
                if not (math.isfinite(n) and n >= 1 and n == int(n)):
                    return False, "Whole contracts only: 1 or more"
                fraction = min(1.0, n * MULTIPLIER / pos["qty"]) if pos["qty"] > 0 else 1.0
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
        n = qty / MULTIPLIER
        return True, (f"Sold {n:,.{0 if abs(n - round(n)) < 1e-9 else 2}f} {pos['tk']} {self._opt_name(pos['kind'], pos['K'], pos['exp'])} "
                      f"contract{'s' if abs(n - 1) > 1e-9 else ''} at {bid:,.4g} MB a share ({pnl:+,.2f} MB)")

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
            q = (self.option_quote(s, pos["kind"], pos["K"], pos["exp"]) if s is not None
                 else {"bid": 0.0, "delta": 0.0, "theta": 0.0, "iv": 0.0})
            value = pos["qty"] * q["bid"]
            out.append({"id": pos["id"], "tk": pos["tk"], "kind": pos["kind"], "K": pos["K"], "exp": pos["exp"],
                        "qty": round(pos["qty"], 4), "contracts": round(pos["qty"] / MULTIPLIER, 4),
                        "cost": round(pos["cost"] + pos["fee"], 4), "bid": round(q["bid"], 6),
                        "value": round(value, 4), "pnl": round(value - pos["cost"] - pos["fee"], 4),
                        "delta": round(q["delta"], 4), "iv": round(q["iv"], 4),
                        "pos_delta": round(pos["qty"] * q["delta"], 4), "pos_theta": round(pos["qty"] * q["theta"], 4),
                        "price": s.price if s is not None else None})
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
