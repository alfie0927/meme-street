"""The learn-to-trade price model (ROADMAP.md track P) and the hidden economy behind the macro calendar (track N).

The engine still draws the second-by-second noise: three factors (the market, the industry, the company), volatility
clustering and the trading sessions (HOW_IT_WORKS.md section 6). On top of that this module gives the market the shape
of a real one, which is what a technical trader learns to read. Everything here is hidden from players; they only see
the prices, the volume and the macro releases it produces.

* **Drift (P1).** Every listing has an expected return per game year (`rf + beta * erp`: about +7% for the market),
  applied as a tiny drift in log price, and fair value (the anchor that prices are slowly pulled back to) grows with it.
  A game year is 7.6 real days, so +7% a game year is about +0.04% a real hour: invisible in a session, clear over weeks.
* **Market regimes (P2).** Bull, sideways, correction, bear and recovery phases, each with its own drift and volatility
  and a random length in game days. The regimes' own drifts average out to zero over time, so the long-run return is the
  drift above. The economy shifts the odds of the next regime.
* **Swings (P3, P5).** Each listing is, at any time, trending (in legs: an impulse, then a pullback), in a range
  (pulled back towards the middle of it, quieter and on lower volume) or drifting freely. A range ends in a breakout,
  and its direction leans with the market.
* **Support and resistance (P4).** Each listing keeps its own 5-minute bars, finds swing highs and lows in them and
  groups them, with round numbers, into levels. When price comes near a level it is a *test*: the level either holds (a
  bounce) or breaks (a burst through on high volume that follows through, or fails and falls back inside: a false
  breakout). Strong levels (several touches, a round number, in line with the trend) hold more often; a level that is
  tested again and again gets weaker.
* **Volatility and volume (P6, P7).** Ranges are quiet, breakouts and macro releases loud; the engine's clustering
  makes falls raise volatility more than rises (the leverage effect). Every listing gets a volume multiplier.
* **Capitulation (P8).** Deep in a sell-off the market can have a panic low: a sharp drop on huge volume and a fast
  rebound, after which the regime turns to recovery.
* **The economy (N2-N4).** Growth, inflation, unemployment and a policy rate move slowly with the regime and produce
  scheduled releases (weekly jobless claims; monthly CPI, jobs, retail sales and a business survey; quarterly GDP; eight
  rate decisions a game year). Each has a consensus forecast published days ahead; the market reacts to the *surprise*,
  through the market and each industry's sensitivity to growth and to interest rates.

The design rule (ROADMAP.md section 1): realism you can learn from, but no free money. Every effect is small next to the
noise, and the hold/break odds are set so that buying every support or fading every move earns nothing after costs;
reading the strength of a level, the trend and the regime is what pays, modestly. `realism.py` checks this.

`MarketModel.step(now, dt, listings)` returns, for those `dt` seconds, the extra return of each listing, a noise
multiplier and a volume multiplier. It uses only its own random stream and the listings it is given (anything with
`ticker`, `price`, `vol`, `beta`, `sector`, `asset_type` and `moonshot`), so realism.py can run it alone, far faster
than the whole engine.
"""
import math
import random
from collections import deque

DAY = 1800                    # a game day in seconds (engine.MARKET_DAY_SECONDS)
YEAR = 365 * DAY              # a game year in seconds
BAR = 300                     # the model's own bars (5 minutes), for finding swing highs and lows

# drift a game year (log, of the market factor), noise multiplier, mean length (game days), what may come next
REGIMES = {
    "bull": (0.14, 0.85, 70, {"sideways": 0.45, "correction": 0.45, "bear": 0.10}),
    "sideways": (0.0, 0.8, 40, {"bull": 0.55, "correction": 0.30, "bear": 0.15}),
    "correction": (-1.1, 1.35, 9, {"recovery": 0.50, "sideways": 0.35, "bear": 0.15}),
    "bear": (-0.45, 1.5, 45, {"recovery": 1.0}),
    "recovery": (0.5, 1.1, 25, {"bull": 0.75, "sideways": 0.25}),
}
# What the narrative engine (headline tone, engine.REGIME_MOOD) should feel in each phase
REGIME_STORY = {"bull": "Boom", "sideways": "Expansion", "correction": "Recession", "bear": "Recession",
                "recovery": "Expansion"}

# How each industry reacts to a surprise in growth and in interest rates (per 1 standard deviation of surprise, in units
# of the market's daily volatility, on top of the market's own reaction through beta). Unknown industries use "other".
GROWTH_TILT = {"industrials": 0.5, "materials": 0.5, "energy": 0.45, "autos": 0.5, "airlines": 0.6, "retail": 0.35,
               "finance": 0.4, "consumer": 0.25, "tech": 0.25, "commodities": 0.3, "agriculture": 0.2,
               "utilities": -0.15, "healthcare": 0.0, "pharma": 0.0, "safe": -0.35, "telecom": 0.0, "other": 0.1}
RATES_TILT = {"tech": -0.6, "crypto": -0.9, "space": -0.6, "realestate": -0.8, "utilities": -0.6, "telecom": -0.3,
              "finance": 0.5, "energy": 0.1, "commodities": -0.4, "safe": -0.6, "consumer": -0.2, "retail": -0.3,
              "healthcare": -0.1, "pharma": -0.1, "industrials": -0.2, "materials": -0.1, "meme": -0.7, "other": -0.35}

DEFAULTS = {
    "rf": 0.015, "erp": 0.04,                          # drift a game year: rf + beta * erp (commodities: rf)
    "anchor_halflife_days": 120.0,                    # how slowly prices are pulled back to fair value
    "anchor_follows_regime": 0.6,                     # how much of the regime's drift fair value shares
    "trend_strength": 2.0,                            # a trend's average drift a game year, in units of the volatility
    "range_halflife_days": 3.0,                       # how strongly a range pulls price back to its middle
    "range_noise": 0.8, "range_volume": 0.65,
    "breakout_sigmas": 0.8, "breakout_seconds": 600, "breakout_noise": 1.6, "breakout_volume": 2.5,
    "level_band_sigmas": 0.25,                        # "near a level": within this many daily sigmas of it
    "hold_base": 0.40, "hold_per_touch": 0.09, "hold_round": 0.07, "hold_trend": 0.10, "hold_repeat": 0.07,
    "bounce_sigmas": 0.6, "bounce_seconds": 240,
    "follow_sigmas": 0.8, "follow_seconds": 450, "false_break": 0.3,
    "capitulation_drawdown": 0.14, "capitulation_daily_chance": 0.3,
    "release_sigmas": 0.55,                           # a 1-sd surprise moves the market about this many daily sigmas
}


def _stationary_drift():
    """The long-run average drift of the regimes alone (time-weighted), so it can be taken out."""
    names = list(REGIMES)
    pi = {n: 1.0 / len(names) for n in names}
    for _ in range(500):
        nxt = {n: 0.0 for n in names}
        for a in names:
            for b, w in REGIMES[a][3].items():
                nxt[b] += pi[a] * w
        pi = nxt
    weight = {n: pi[n] * REGIMES[n][2] for n in names}
    total = sum(weight.values())
    return sum(weight[n] * REGIMES[n][0] for n in names) / total, {n: weight[n] / total for n in names}


REGIME_MEAN_DRIFT, REGIME_SHARE = _stationary_drift()


def round_step(price):
    """The spacing of 'round numbers' near a price: 140 and 150 near 145, 425 and 450 near 440, 8.5 and 9 near 8.7."""
    if price <= 0:
        return 1.0
    mag = 10 ** math.floor(math.log10(price))
    m = price / mag
    return mag * (0.1 if m < 2 else 0.25 if m < 5 else 0.5)


class Pulse:
    """A move spread over time: `amounts` (ticker -> total log move) delivered over `dur` seconds, front-loaded with
    time constant `tau`. A whipsaw first goes the other way for a few seconds."""
    __slots__ = ("start", "dur", "tau", "amounts", "whip", "noise", "volume", "kind")

    def __init__(self, start, dur, tau, amounts, whip=False, noise=1.0, volume=1.0, kind=""):
        self.start, self.dur, self.tau, self.amounts = start, dur, tau, amounts
        self.whip, self.noise, self.volume, self.kind = whip, noise, volume, kind

    def frac(self, t):
        """Share of the move delivered by `t` seconds after the start."""
        if t <= 0:
            return 0.0
        if t >= self.dur:
            return 1.0
        base = (1 - math.exp(-t / self.tau)) / (1 - math.exp(-self.dur / self.tau))
        if self.whip:                  # the first reaction is wrong-footed, then the market turns
            w = min(t, 20.0) / 20.0
            return base - w * math.exp(-max(0.0, t - 20.0) / 15.0)
        return base

    def dump(self):
        return {"start": self.start, "dur": self.dur, "tau": self.tau, "amounts": self.amounts, "whip": self.whip,
                "noise": self.noise, "volume": self.volume, "kind": self.kind}

    @classmethod
    def load(cls, d):
        return cls(d["start"], d["dur"], d["tau"], dict(d["amounts"]), d.get("whip", False), d.get("noise", 1.0),
                   d.get("volume", 1.0), d.get("kind", ""))


class Swing:
    """One listing's hidden state: its mode (trend, range or free), its own bars and levels, and the level test under
    way."""

    def __init__(self, now, price):
        self.mode, self.dir, self.until = "free", 0, now
        self.leg, self.leg_until = "impulse", now
        self.center = math.log(max(price, 1e-9))
        self.burst = None                      # [dir, start, end, size]: a breakout from a range
        self.bars = deque(maxlen=400)          # [start, high, low, close]
        self.levels = []                       # [price, strength, round?]
        self.test = None
        self.tested = deque(maxlen=12)         # [time, level price] of recent tests
        self.anchor = math.log(max(price, 1e-9))
        self.last_t = now

    def dump(self):
        return {"mode": self.mode, "dir": self.dir, "until": self.until, "leg": self.leg, "leg_until": self.leg_until,
                "center": self.center, "burst": self.burst, "anchor": self.anchor, "test": self.test,
                "tested": list(self.tested)}

    def load(self, d):
        for k in ("mode", "dir", "until", "leg", "leg_until", "center", "burst", "anchor", "test"):
            if k in d:
                setattr(self, k, d[k])
        self.tested = deque((list(x) for x in d.get("tested", [])), maxlen=12)


class Economy:
    """The hidden economy (N4), the central bank (N2) and the release calendar (N3). Times come from the clock, so the
    calendar is the same after a restart; consensus forecasts are fixed when they are published and saved."""

    # kind: name, every (game days), first (game days into the cycle), seconds into the game day, publish (days ahead)
    KINDS = {
        "claims": ("Weekly jobless claims", 7.0, 2.0, 150, 3),
        "pmi": ("Business survey (PMI)", 30.4, 1.0, 150, 5),
        "jobs": ("Jobs report", 30.4, 5.0, 150, 5),
        "cpi": ("Consumer prices (CPI)", 30.4, 12.0, 150, 5),
        "retail": ("Retail sales", 30.4, 17.0, 150, 5),
        "gdp": ("GDP growth", 91.25, 26.0, 150, 8),
        "rates": ("Interest-rate decision", 365 / 8, 21.0, 1050, 10),
    }
    BANK = "the Reserve Board"

    def __init__(self, rng):
        self.rng = rng
        self.growth, self.infl, self.unemp, self.rate = 2.2, 2.7, 4.2, 3.5
        self.neutral = 0.75          # the neutral *real* rate (the Taylor rule adds inflation to it)
        self.consensus = {}          # "kind@time" -> what was forecast
        self.past = deque(maxlen=40)  # releases that happened
        self.t = None

    # ------------------------------------------------------------------ the slow economy
    def evolve(self, now, dt, regime):
        target_growth = {"bull": 3.0, "sideways": 1.8, "correction": 1.5, "bear": -1.0, "recovery": 2.4}[regime]
        g = self.rng.gauss
        d = dt / DAY
        self.growth += (target_growth - self.growth) * d / 25 + g(0, 0.12) * math.sqrt(d)
        self.unemp += (4.4 - 0.45 * (self.growth - 2.0) - self.unemp) * d / 40 + g(0, 0.03) * math.sqrt(d)
        real = self.rate - self.infl
        target_infl = 2.0 + 0.35 * (self.growth - 2.0) - 0.3 * (real - 0.5)
        self.infl += (target_infl - self.infl) * d / 60 + g(0, 0.05) * math.sqrt(d)
        self.unemp = max(2.5, min(12.0, self.unemp))
        self.infl = max(-1.0, min(12.0, self.infl))

    def taylor(self):
        t = self.neutral + self.infl + 0.5 * (self.infl - 2.0) + 0.5 * (self.growth - 2.0)
        return max(0.25, min(9.0, round(t * 4) / 4))

    # ------------------------------------------------------------------ the calendar
    def times(self, kind, start, end):
        _, every, first, at, _ = self.KINDS[kind]
        out = []
        k = math.floor((start / DAY - first) / every)
        while True:
            day = math.floor(first + k * every)
            t = day * DAY + at
            if t > end:
                break
            if t > start:
                out.append(t)
            k += 1
        return out

    def upcoming(self, now, days=12):
        ev = []
        for kind in self.KINDS:
            for t in self.times(kind, now, now + days * DAY):
                ev.append((t, kind))
        ev.sort()
        return ev

    def _forecast(self, kind):
        g = self.rng.gauss
        if kind == "cpi":
            return {"value": round(self.infl + g(0, 0.08), 1)}
        if kind == "jobs":
            return {"value": int(round((150 + 60 * (self.growth - 2.0) + g(0, 20)) / 5) * 5),
                    "unemp": round(self.unemp, 1)}
        if kind == "claims":
            return {"value": int(round(220 - 12 * (self.growth - 2.0) + g(0, 4)))}
        if kind == "retail":
            return {"value": round(0.3 + 0.15 * (self.growth - 2.0) + g(0, 0.1), 1)}
        if kind == "pmi":
            return {"value": round(50 + 2 * (self.growth - 2.0) + g(0, 0.4), 1)}
        if kind == "gdp":
            return {"value": round(self.growth + g(0, 0.2), 1)}
        gap = self.taylor() - self.rate              # rates: how likely a move is, as the market prices it
        step = 0.5 if abs(gap) >= 1.25 else 0.25
        p = 0.1 if abs(gap) < 0.25 else min(0.9, 0.3 + 0.4 * abs(gap))
        move = math.copysign(step, gap) if abs(gap) >= 0.125 else 0.25 * self.rng.choice((-1, 1))
        return {"move": move, "p": round(p, 2), "rate": self.rate}

    def publish(self, now):
        """Fix the forecast of every release that has come into view."""
        for t, kind in self.upcoming(now, days=max(v[4] for v in self.KINDS.values())):
            key = f"{kind}@{int(t)}"
            if key not in self.consensus and t - now <= self.KINDS[kind][4] * DAY:
                self.consensus[key] = dict(self._forecast(kind), t=t, kind=kind)
        for key in [k for k, v in self.consensus.items() if v["t"] < now - DAY]:
            del self.consensus[key]

    def release(self, kind, t):
        """The actual figure for a release due now: (record, growth surprise, rates surprise) in standard deviations."""
        c = self.consensus.get(f"{kind}@{int(t)}") or dict(self._forecast(kind), t=t, kind=kind)
        g = self.rng.gauss
        rec = {"t": t, "kind": kind, "name": self.KINDS[kind][0]}
        gz = rz = 0.0
        if kind == "cpi":
            a = round(self.infl + g(0, 0.12), 1)
            z = (a - c["value"]) / 0.15
            rec.update(actual=a, consensus=c["value"], unit="%", text=f"{a:.1f}% a year")
            rz = z * (1.0 if self.infl > 2.5 else 0.7)
        elif kind == "jobs":
            a = int(round(150 + 60 * (self.growth - 2.0) + g(0, 60)))
            z = (a - c["value"]) / 65
            rec.update(actual=a, consensus=c["value"], unit="k", text=f"{a:+,}k jobs, unemployment {self.unemp:.1f}%")
            gz, rz = 0.6 * z, (0.5 if self.infl > 3.0 else 0.25) * z
        elif kind == "claims":
            a = int(round(220 - 12 * (self.growth - 2.0) + g(0, 12)))
            z = (a - c["value"]) / 12
            rec.update(actual=a, consensus=c["value"], unit="k", text=f"{a}k new claims")
            gz = -0.4 * z
        elif kind == "retail":
            a = round(0.3 + 0.15 * (self.growth - 2.0) + g(0, 0.4), 1)
            z = (a - c["value"]) / 0.4
            rec.update(actual=a, consensus=c["value"], unit="%", text=f"{a:+.1f}% on the month")
            gz, rz = 0.4 * z, 0.1 * z
        elif kind == "pmi":
            a = round(50 + 2 * (self.growth - 2.0) + g(0, 1.2), 1)
            z = (a - c["value"]) / 1.2
            rec.update(actual=a, consensus=c["value"], unit="", text=f"{a:.1f} ({'growing' if a >= 50 else 'shrinking'})")
            gz = 0.45 * z
        elif kind == "gdp":
            a = round(self.growth + g(0, 0.45), 1)
            z = (a - c["value"]) / 0.45
            rec.update(actual=a, consensus=c["value"], unit="%", text=f"{a:+.1f}% a year")
            gz, rz = 0.5 * z, 0.1 * z
        else:
            p, move = c["p"], c["move"]
            r = self.rng.random()
            decision = move if r < p else 0.0
            if r > 0.97:                                    # now and then the bank goes further than anyone expected
                decision = move * 2
            self.rate = max(0.0, round((self.rate + decision) * 4) / 4)
            expected = p * move
            z = (decision - expected) / 0.25
            rec.update(actual=self.rate, consensus=c["rate"] + (move if p >= 0.5 else 0.0), move=decision,
                       expected_move=move, p=p, unit="%", text=self._rate_text(decision, p, move))
            rz = z
        rec["growth_z"], rec["rates_z"] = round(gz, 2), round(rz, 2)
        self.consensus.pop(f"{kind}@{int(t)}", None)
        self.past.append(rec)
        return rec, gz, rz

    def _rate_text(self, decision, p, move):
        verb = "cut" if move < 0 else "rise"
        if decision == 0:
            return f"held at {self.rate:.2f}%" + (f"; a {abs(move):.2f}-point {verb} had been priced at {p:.0%}" if p >= 0.5 else ", as expected")
        word = "raised" if decision > 0 else "cut"
        surprise = "as expected" if p >= 0.5 and decision == move else "a surprise"
        return f"{word} by {abs(decision):.2f} points to {self.rate:.2f}% ({surprise})"

    def headline(self, rec):
        c = rec.get("consensus")
        if rec["kind"] == "rates":
            return f"Rate decision: {self.BANK} {rec['text']}"
        better = rec["actual"] > c if rec["kind"] != "claims" else rec["actual"] < c
        same = rec["actual"] == c
        how = "in line with" if same else ("above" if rec["actual"] > c else "below")
        if rec["kind"] == "cpi":
            tone = "" if same else (" - inflation runs hot" if rec["actual"] > c else " - inflation cools")
        else:
            tone = "" if same else (" - a stronger reading" if better else " - a weaker reading")
        unit = rec.get("unit", "")
        fc = f"{c:+,}{unit}" if rec["kind"] == "jobs" else f"{c}{unit}"
        return f"{rec['name']}: {rec['text']}, {how} the {fc} forecast{tone}"

    def view(self, now):
        """What players may see: the calendar with forecasts, and the latest releases."""
        up = []
        for t, kind in self.upcoming(now, days=30)[:14]:
            c = self.consensus.get(f"{kind}@{int(t)}")
            up.append({"t": t, "kind": kind, "name": self.KINDS[kind][0], "forecast": self._forecast_text(kind, c)})
        return {"upcoming": up, "past": list(self.past)[-15:][::-1], "rate": self.rate, "bank": self.BANK}

    def _forecast_text(self, kind, c):
        if not c:
            return "forecast not yet published"
        if kind == "rates":
            move = c["move"]
            verb = "rise" if move > 0 else "cut"
            if c["p"] >= 0.5:
                return f"a {abs(move):.2f}-point {verb} expected ({c['p']:.0%}); {1 - c['p']:.0%} chance of no change"
            return f"no change expected; {c['p']:.0%} chance of a {abs(move):.2f}-point {verb}"
        unit = {"cpi": "% a year", "jobs": "k jobs", "claims": "k claims", "retail": "% on the month", "pmi": "",
                "gdp": "% a year"}[kind]
        v = c["value"]
        return "forecast " + (f"{v:+,}" if kind == "jobs" else f"{v}") + unit

    def dump(self):
        return {"growth": self.growth, "infl": self.infl, "unemp": self.unemp, "rate": self.rate,
                "consensus": self.consensus, "past": list(self.past)}

    def load(self, d):
        for k in ("growth", "infl", "unemp", "rate"):
            if k in d:
                setattr(self, k, float(d[k]))
        self.consensus = dict(d.get("consensus", {}))
        self.past = deque(d.get("past", []), maxlen=40)


class MarketModel:
    def __init__(self, settings=None, rng=None, now=0.0):
        self.rng = rng or random.Random()
        self.p = dict(DEFAULTS)
        self.p.update((settings or {}).get("price_model", {}) if isinstance(settings, dict) else {})
        self.vol_scale = float((settings or {}).get("volatility_scale", 1.0)) if isinstance(settings, dict) else 1.0
        self.regime, self.regime_until = "bull", now + self._regime_length("bull")
        self.swings = {}
        self.pulses = []
        self.economy = Economy(self.rng)
        self.events = []                 # headlines for the engine: {"kind", "text", "dir", "strength"}
        self.mkt = 0.0                   # the market's log level (equal-weighted), for drawdowns
        self.mkt_peak = deque(maxlen=60)  # [day, high] of the last 60 game days
        self.capitulated_at = -1e18
        self.last_release = -1e18
        self.next_release = None
        self.earn_forecast = {}          # ticker -> [report time, forecast EPS] (set by the engine, saved here)
        self.t = now

    # ------------------------------------------------------------------ helpers
    def _regime_length(self, name):
        mean = REGIMES[name][2]
        return min(3.0 * mean, max(0.3 * mean, self.rng.expovariate(1.0 / mean))) * DAY

    @staticmethod
    def drift_of(listing, p):
        if getattr(listing, "asset_type", "equity") == "commodity":
            return p["rf"]
        if getattr(listing, "moonshot", False):
            return 0.0
        return p["rf"] + max(0.0, getattr(listing, "beta", 1.0)) * p["erp"]

    def regime_drift(self):
        return REGIMES[self.regime][0] - REGIME_MEAN_DRIFT

    def regime_sign(self):
        """Which way the phase itself points: +1 bull or recovery, -1 correction or bear, 0 sideways."""
        d = REGIMES[self.regime][0]
        return 1 if d > 0.02 else -1 if d < -0.02 else 0

    def market_vol(self, now=None):
        """The market-wide noise multiplier: the regime's, quieter just before a release, louder just after one."""
        m = REGIMES[self.regime][1]
        now = self.t if now is None else now
        since = now - self.last_release
        if 0 <= since < 900:
            m *= 1 + 0.8 * math.exp(-since / 300)
        elif self.next_release is not None and 0 < self.next_release - now < 300:
            m *= 0.85
        return m

    def swing(self, listing, now):
        sw = self.swings.get(listing.ticker)
        if sw is None:
            sw = self.swings[listing.ticker] = Swing(now, listing.price)
            sw.until = now + self.rng.uniform(0, 10) * DAY
        return sw

    def drop(self, ticker):
        self.swings.pop(ticker, None)

    # ------------------------------------------------------------------ one step
    def step(self, now, dt, listings):
        """Returns ({ticker: extra return}, {ticker: noise multiplier}, {ticker: volume multiplier}) for `dt` seconds."""
        dt = max(0.0, float(dt))
        self.t = now
        listings = [x for x in listings if getattr(x, "asset_type", "equity") != "index" and x.price > 0]
        self._regime_step(now)
        self._economy_step(now, dt, listings)
        self._capitulation_check(now, listings)
        rets, noise, volume = {}, {}, {}
        rd = self.regime_drift()
        follow = self.p["anchor_follows_regime"]
        rev = math.log(2) / (self.p["anchor_halflife_days"] * DAY)
        for x in listings:
            sw = self.swing(x, now)
            mu = self.drift_of(x, self.p)
            beta = getattr(x, "beta", 1.0)
            lp = math.log(x.price)
            sig_d = x.vol * self.vol_scale / math.sqrt(365)
            base = (mu + beta * rd) * dt / YEAR
            sw.anchor += (mu + follow * beta * rd) * dt / YEAR
            r = base + (sw.anchor - lp) * rev * dt
            n, v = 1.0, 1.0
            r2, n2, v2 = self._mode_step(x, sw, now, dt, lp, sig_d, rd)
            r3, n3, v3 = self._level_step(x, sw, now, dt, lp, sig_d)
            rets[x.ticker] = math.expm1(r + r2 + r3)
            noise[x.ticker] = n * n2 * n3
            volume[x.ticker] = v * v2 * v3
            self._bar(sw, now, x.price)
        self._pulse_step(now, dt, rets, noise, volume)
        mean = sum(math.log1p(r) for tk, r in rets.items()) / len(rets) if rets else 0.0
        self.mkt += mean
        rv = REGIMES[self.regime][1]
        for tk in volume:
            volume[tk] *= rv ** 1.2
        return rets, noise, volume

    # ------------------------------------------------------------------ the regime
    def _regime_step(self, now):
        if now < self.regime_until:
            return
        weights = dict(REGIMES[self.regime][3])
        e = self.economy
        if e.infl > 3.5 and e.rate - e.infl > e.neutral + 0.5:   # tight money and hot prices: sell-offs likelier
            for k in ("correction", "bear"):
                if k in weights:
                    weights[k] *= 1.6
        if e.growth < 0.5 and "bear" in weights:
            weights["bear"] *= 2.0
        if e.growth > 2.5 and "bull" in weights:
            weights["bull"] *= 1.3
        names = list(weights)
        self.regime = self.rng.choices(names, [weights[n] for n in names])[0]
        self.regime_until = now + self._regime_length(self.regime)

    # ------------------------------------------------------------------ trends, ranges and breakouts
    def _mode_step(self, x, sw, now, dt, lp, sig_d, rd):
        p = self.p
        if now >= sw.until:
            self._next_mode(x, sw, now, lp, rd)
        r, n, v = 0.0, 1.0, 1.0
        if sw.mode == "trend":
            if now >= sw.leg_until:
                sw.leg = "pullback" if sw.leg == "impulse" else "impulse"
                days = self.rng.uniform(2, 5) if sw.leg == "impulse" else self.rng.uniform(1, 2.5)
                sw.leg_until = now + days * DAY
            k = 3.5 if sw.leg == "impulse" else -0.9               # averages about 2: p["trend_strength"]
            r += sw.dir * k * p["trend_strength"] / 2.0 * x.vol * self.vol_scale * dt / YEAR
            v = 1.15 if sw.leg == "impulse" else 0.85
        elif sw.mode == "range":
            hl = p["range_halflife_days"] * DAY
            r += (sw.center - lp) * (math.log(2) / hl) * dt
            n, v = p["range_noise"], p["range_volume"]
        if sw.burst:
            d, start, end, size = sw.burst
            if now >= end:
                sw.burst = None
            else:
                r += d * size * sig_d * dt / (end - start)
                n, v = n * p["breakout_noise"], v * p["breakout_volume"]
        return r, n, v

    def _next_mode(self, x, sw, now, lp, rd):
        rng = self.rng
        lean = 0.12 * self.regime_sign()
        if sw.mode == "range":                         # a range ends in a breakout
            d = 1 if rng.random() < 0.5 + lean else -1
            sw.burst = [d, now, now + self.p["breakout_seconds"], self.p["breakout_sigmas"]]
            if rng.random() < 0.65:
                sw.mode, sw.dir = "trend", d
            else:
                sw.mode, sw.dir = "free", 0
        elif sw.mode == "trend":
            r = rng.random()
            sideways = self.regime == "sideways"
            if r < (0.6 if sideways else 0.45):
                sw.mode, sw.center = "range", lp
            elif r < 0.8:
                sw.mode, sw.dir = "free", 0
            else:
                sw.dir = -sw.dir                        # a reversal
        else:
            range_odds = 0.65 if self.regime == "sideways" else 0.45
            if rng.random() < range_odds:
                sw.mode, sw.center = "range", lp
            else:
                sw.mode, sw.dir = "trend", (1 if rng.random() < 0.5 + lean else -1)
        days = {"trend": (8, 30), "range": (10, 35), "free": (4, 15)}[sw.mode]
        sw.until = now + rng.uniform(*days) * DAY
        sw.leg, sw.leg_until = "impulse", now + rng.uniform(2, 5) * DAY

    # ------------------------------------------------------------------ support and resistance
    def _bar(self, sw, now, price):
        start = int(now // BAR) * BAR
        if sw.bars and sw.bars[-1][0] == start:
            b = sw.bars[-1]
            b[1], b[2], b[3] = max(b[1], price), min(b[2], price), price
            return
        sw.bars.append([start, price, price, price])
        if len(sw.bars) % 3 == 0 or len(sw.bars) < 3:   # every 15 minutes is plenty
            self._find_levels(sw, price)

    def seed_bars(self, ticker, bars):
        """Rebuild a listing's bars from the engine's 5-minute candles after a restart ([t, o, h, l, c, ...])."""
        sw = self.swings.get(ticker)
        if sw is None:
            return
        sw.bars.clear()
        for c in list(bars)[-400:]:
            sw.bars.append([c[0], c[2], c[3], c[4]])
        if sw.bars:
            self._find_levels(sw, sw.bars[-1][3])

    def _find_levels(self, sw, price, k=4):
        bars = list(sw.bars)
        pivots = []
        for i in range(k, len(bars) - k):
            h, l = bars[i][1], bars[i][2]
            if all(h >= bars[j][1] for j in range(i - k, i + k + 1)):
                pivots.append(h)
            if all(l <= bars[j][2] for j in range(i - k, i + k + 1)):
                pivots.append(l)
        pivots = pivots[-24:]
        levels = []
        tol = 0.004
        for pv in sorted(pivots):
            if levels and abs(pv / levels[-1][0] - 1) < tol:
                lv = levels[-1]
                lv[0] = (lv[0] * lv[1] + pv) / (lv[1] + 1)
                lv[1] += 1
            else:
                levels.append([pv, 1, False])
        step = round_step(price)
        for rn in (math.floor(price / step) * step, math.ceil(price / step) * step):
            if rn <= 0:
                continue
            near = next((lv for lv in levels if abs(lv[0] / rn - 1) < tol), None)
            if near:
                near[2] = True
            else:
                levels.append([rn, 0, True])
        sw.levels = levels

    def _level_step(self, x, sw, now, dt, lp, sig_d):
        p = self.p
        band = p["level_band_sigmas"] * sig_d
        t = sw.test
        if t is None:
            t = self._start_test(x, sw, now, lp, band)
            if t is None:
                return 0.0, 1.0, 1.0
        lvl, side = math.log(t["level"]), t["side"]      # side +1: support below the price; -1: resistance above
        rel = (lp - lvl) * side                           # >0: still on the near side; <0: through the level
        push = p["bounce_sigmas"] * sig_d / p["bounce_seconds"]
        if t["outcome"] == "hold":
            if rel < -2.5 * band:                         # the noise broke it anyway: treat it as a break
                t.update(outcome="break", crossed=now, false=False)
                return 0.0, 1.0, 1.0
            if rel > 2.5 * band or now > t["until"]:
                sw.test = None
                return 0.0, 1.0, 1.0
            return side * push * dt, 1.0, 1.3
        # a break
        if not t.get("crossed"):
            if rel <= 0:
                t["crossed"] = now
            elif rel > 3 * band or now > t["until"]:
                sw.test = None
                return 0.0, 1.0, 1.0
            else:
                return -side * 0.6 * push * dt, 1.0, 1.4
        since = now - t["crossed"]
        if t.get("false") and since > t.get("fail_after", 120):
            if rel > band or since > t.get("fail_after", 120) + 600:
                sw.test = None
                return 0.0, 1.0, 1.0
            return side * 1.2 * push * dt, 1.1, 1.8           # back inside: the breakout failed
        if since > p["follow_seconds"]:
            sw.test = None
            return 0.0, 1.0, 1.0
        follow = p["follow_sigmas"] * sig_d / p["follow_seconds"]
        return -side * follow * dt, 1.25, 2.5

    def _start_test(self, x, sw, now, lp, band):
        best = None
        for price, strength, rnd in sw.levels:
            d = lp - math.log(price)
            if 0 < d <= band:
                side = 1
            elif -band <= d < 0:
                side = -1
            else:
                continue
            if best is None or abs(d) < abs(best[1]):
                best = (price, d, side, strength, rnd)
        if best is None:
            return None
        price, d, side, strength, rnd = best
        if any(abs(price / lv - 1) < 0.002 and now - ts < 1200 for ts, lv in sw.tested):
            return None                                      # this level was just tested: let it go
        repeats = sum(1 for ts, lv in sw.tested if abs(price / lv - 1) < 0.004 and now - ts < 3 * DAY)
        trend = sw.dir if sw.mode == "trend" else self.regime_sign()
        align = 1 if trend == side else -1 if trend == -side else 0   # support in an uptrend holds more often
        p = self.p
        p_hold = (p["hold_base"] + p["hold_per_touch"] * min(strength, 4) + (p["hold_round"] if rnd else 0.0)
                  + p["hold_trend"] * align - p["hold_repeat"] * repeats)
        p_hold = max(0.25, min(0.75, p_hold))
        hold = self.rng.random() < p_hold
        false = (not hold) and self.rng.random() < p["false_break"] + (0.1 if align > 0 else 0.0)
        sw.tested.append([now, price])
        sw.test = {"level": price, "side": side, "outcome": "hold" if hold else "break", "until": now + 900,
                   "false": false, "fail_after": self.rng.uniform(60, 240), "p_hold": round(p_hold, 2),
                   "strength": strength, "round": rnd, "start": now}
        return sw.test

    # ------------------------------------------------------------------ macro releases and panics
    def _economy_step(self, now, dt, listings):
        e = self.economy
        e.evolve(now, dt, self.regime)
        if e.t is None or now - e.t >= 60:
            e.t = now
            e.publish(now)
            up = e.upcoming(now, days=2)
            self.next_release = up[0][0] if up else None
        due = [(t, k) for t, k in e.upcoming(now - dt - 1e-9, days=dt / DAY + 1e-6) if t <= now]
        for t, kind in due:
            rec, gz, rz = e.release(kind, t)
            self.last_release = now
            amounts = {}
            m = self.p["release_sigmas"] / math.sqrt(365) * 0.18          # the market's daily sigma is about 0.94%
            for x in listings:
                sec = x.sector if x.sector in GROWTH_TILT or x.sector in RATES_TILT else "other"
                beta = getattr(x, "beta", 1.0)
                move = m * (beta * (0.6 * gz - 0.7 * rz) + GROWTH_TILT.get(sec, GROWTH_TILT["other"]) * gz
                            + RATES_TILT.get(sec, RATES_TILT["other"]) * rz)
                if move:
                    amounts[x.ticker] = move
            whip = self.rng.random() < 0.25
            self.pulses.append(Pulse(now, 120, 25, amounts, whip=whip, noise=1.0, volume=2.5, kind=kind))
            mk = 0.6 * gz - 0.7 * rz
            rec["market_z"] = round(mk, 2)
            strength = "strong" if abs(mk) > 1.2 else "weak" if abs(mk) > 0.4 else "bystander"
            self.events.append({"kind": "macro", "text": e.headline(rec), "dir": (1 if mk > 0.2 else -1 if mk < -0.2 else 0),
                                "strength": strength, "release": rec})

    def _capitulation_check(self, now, listings):
        day = int(now // DAY)
        if not self.mkt_peak or self.mkt_peak[-1][0] != day:
            self.mkt_peak.append([day, self.mkt])
            if self.regime in ("correction", "bear") and now - self.capitulated_at > 20 * DAY:
                high = max(h for _, h in self.mkt_peak)
                if high - self.mkt > self.p["capitulation_drawdown"] and self.rng.random() < self.p["capitulation_daily_chance"]:
                    self._capitulate(now, listings)
        else:
            self.mkt_peak[-1][1] = max(self.mkt_peak[-1][1], self.mkt)

    def _capitulate(self, now, listings):
        """A panic low: the market drops hard on huge volume, then snaps back; the regime turns to recovery."""
        self.capitulated_at = now
        m = 0.18 / math.sqrt(365)
        drop = {x.ticker: -1.6 * m * max(0.3, getattr(x, "beta", 1.0)) for x in listings}
        bounce = {x.ticker: 1.3 * m * max(0.3, getattr(x, "beta", 1.0)) for x in listings}
        self.pulses.append(Pulse(now, 240, 120, drop, noise=2.2, volume=4.0, kind="capitulation"))
        self.pulses.append(Pulse(now + 240, 900, 300, bounce, noise=1.6, volume=2.5, kind="rebound"))
        self.regime, self.regime_until = "recovery", now + 240 + self._regime_length("recovery")
        self.events.append({"kind": "macro", "text": "Panic selling sweeps the market as volumes explode",
                            "dir": -1, "strength": "strong"})

    def _pulse_step(self, now, dt, rets, noise, volume):
        keep = []
        for pl in self.pulses:
            a, b = now - dt - pl.start, now - pl.start
            if b <= 0:
                keep.append(pl)
                continue
            f = pl.frac(b) - pl.frac(max(a, 0.0))
            for tk, amt in pl.amounts.items():
                if tk in rets:
                    rets[tk] = math.expm1(math.log1p(rets[tk]) + amt * f)
            live = 0 <= b <= pl.dur
            if live:
                for tk in rets:
                    noise[tk] *= pl.noise
                    volume[tk] *= pl.volume
            if b < pl.dur:
                keep.append(pl)
        self.pulses = keep

    def drift_after(self, ticker, amount, now, seconds):
        """A slow drift of `amount` (log) over `seconds`, e.g. after a big earnings surprise."""
        if amount:
            self.pulses.append(Pulse(now, seconds, seconds * 10, {ticker: amount}, kind="drift"))

    # ------------------------------------------------------------------ what players and the admin may see
    def calendar(self, now):
        return self.economy.view(now)

    def admin_view(self, now):
        modes = {}
        for sw in self.swings.values():
            modes[sw.mode] = modes.get(sw.mode, 0) + 1
        tests = [sw.test for sw in self.swings.values() if sw.test]
        e = self.economy
        return {"regime": self.regime, "regime_left_days": round((self.regime_until - now) / DAY, 1),
                "economy": {"growth": round(e.growth, 2), "inflation": round(e.infl, 2), "unemployment": round(e.unemp, 2),
                            "rate": e.rate, "taylor": e.taylor()},
                "modes": modes, "tests_now": len(tests), "pulses": len(self.pulses)}

    # ------------------------------------------------------------------ saving
    def dump(self):
        return {"regime": self.regime, "regime_until": self.regime_until, "economy": self.economy.dump(),
                "swings": {tk: sw.dump() for tk, sw in self.swings.items()},
                "pulses": [pl.dump() for pl in self.pulses], "mkt": self.mkt, "mkt_peak": list(self.mkt_peak),
                "capitulated_at": self.capitulated_at, "last_release": self.last_release,
                "earn_forecast": self.earn_forecast}

    def load(self, d, now, prices):
        if not d:
            return
        if d.get("regime") in REGIMES:
            self.regime, self.regime_until = d["regime"], float(d.get("regime_until", now))
        self.economy.load(d.get("economy", {}))
        for tk, sd in d.get("swings", {}).items():
            if tk in prices:
                sw = self.swings[tk] = Swing(now, prices[tk])
                sw.load(sd)
        self.pulses = [Pulse.load(x) for x in d.get("pulses", [])]
        self.mkt = float(d.get("mkt", 0.0))
        self.mkt_peak = deque((list(x) for x in d.get("mkt_peak", [])), maxlen=60)
        self.capitulated_at = float(d.get("capitulated_at", -1e18))
        self.last_release = float(d.get("last_release", -1e18))
        self.earn_forecast = {k: list(v) for k, v in d.get("earn_forecast", {}).items()}
