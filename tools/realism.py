"""The realism and "no free money" check for the price model (docs/ROADMAP.md P11, TA-A9).

    python tools/realism.py [game_years] [seeds] [stocks] [first_seed]       (defaults: 2 years, 3 seeds, 40 stocks, seed 101)

It runs market_model.py on its own, with the engine's three-factor noise and its trading sessions (a thin pre-market and
after-hours, a busy open and close, the opening jump) rebuilt here in steps of 10 seconds (far faster than the whole
engine), on companies drawn from the content packs, and prints:

1. The long run: the market's return per game year (target: about +5% to +10%), the time spent in each regime, the
   number of 10% drawdowns a game year and the deepest one.
2. Stylised facts of real returns: fat tails (the kurtosis of 5-minute returns is well above 3), almost no
   autocorrelation of returns, and volatility clustering (the autocorrelation of absolute returns is clearly positive).
3. Support and resistance: how often levels hold, by strength and by kind (swing points, the previous game day's high,
   low and close, the day's open, the 52-week high and low, the 20/50/200-day averages), and how many breaks fail.
4. Gaps: how big the opening gaps are and how many fill the same day.
5. Strategies, costs included (0.1% a side), compared with holding the market: no unskilled rule may beat holding by a
   wide margin. Reported as the average result per trade and per game year.
6. The structure a trader reads (TA-A4 to TA-A8): volume on breakouts that run against ones that fail, climaxes, quiet
   pullbacks, wicks where levels hold, engulfing candles where trends turn, the squeeze before a breakout, timeframes
   that agree, RSI divergences and Bollinger squeezes, each against its baseline.
7. Chart patterns (TA-A3, TA-A9): every pattern patterns.py finds on the game-day charts, how often it completes and
   reaches its measured move, the result of trading each one, and the patterns the model made and how many of them a
   trader would have recognised.

The targets are the ROADMAP's; this tool reports, it does not tune. Use fresh seeds for any claim.
"""
import json
import math
import os
import random
import statistics
import sys
import time
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))   # the game's code
import market_model as mm  # noqa: E402
import paths  # noqa: E402
import patterns  # noqa: E402

FEE = 0.001
STEP = 10                      # seconds per simulation step
BARS_PER_DAY = mm.DAY // mm.BAR
DAY = mm.DAY

# The engine's trading sessions (engine.py, "trading sessions"; its defaults in base.json): 5 minutes of pre-market and
# 5 of after-hours at 0.35 of the normal noise, a regular session with a burst at the open and a smaller one into the
# close (scaled so the whole cycle keeps the stock's daily volatility), and the opening jump: a fresh shock the size of
# 90 seconds of ordinary noise when the regular session opens.
PRE, POST = 300, 300
EXT, OPEN_B, OPEN_S, CLOSE_B, CLOSE_S, JUMP = 0.35, 2.5, 150.0, 1.5, 120.0, 90.0
_N = DAY - PRE - POST


def _shape(t):
    return 1.0 + (OPEN_B - 1.0) * math.exp(-t / OPEN_S) + (CLOSE_B - 1.0) * math.exp(-(_N - t) / CLOSE_S)


_NORM = math.sqrt(max(DAY - (PRE + POST) * EXT ** 2 - JUMP, 0.25 * _N) / sum(_shape(t) ** 2 for t in range(_N)))


def session_mult(phase):
    if phase < PRE or phase >= DAY - POST:
        return EXT
    return _shape(phase - PRE) * _NORM


def regular(phase):
    return PRE <= phase < DAY - POST


def companies(n, rng):
    out = []
    for f in ("base.json", "pack_growth.json", "pack_fiction.json", "expansion.json"):
        try:
            with open(os.path.join(paths.CONTENT, f), encoding="utf-8") as fh:
                out += [c for c in json.load(fh).get("companies", []) if c.get("asset_type", "equity") == "equity"]
        except OSError:
            pass
    rng.shuffle(out)
    return out[:n]


def simulate(years, n, seed, model_settings=None):
    rng = random.Random(seed)
    model = mm.MarketModel({"price_model": dict(model_settings or {})}, rng=random.Random(seed * 7 + 1), now=0.0)
    model.trace = []                                      # what the model did and when: breakouts, climaxes, patterns...
    cos = companies(n, rng)
    listings = [types.SimpleNamespace(ticker=c["ticker"], price=float(c.get("initial_price", 50)), vol=float(c.get("vol", 0.3)),
                                      beta=float(c.get("beta", 1.0)), sector=c["sector"], asset_type="equity", moonshot=False)
                for c in cos]
    sectors = sorted({x.sector for x in listings})
    annual_scale = math.sqrt(mm.YEAR)
    closes = {x.ticker: [] for x in listings}            # 5-minute closes
    vol5 = {x.ticker: [] for x in listings}              # 5-minute volume (in units of an ordinary second's)
    hi5 = {x.ticker: [] for x in listings}               # 5-minute highs and lows (the open is the close before)
    lo5 = {x.ticker: [] for x in listings}
    hacc = {x.ticker: x.price for x in listings}
    lacc = {x.ticker: x.price for x in listings}
    days = {x.ticker: [] for x in listings}              # regular-session game days: [open, high, low, close, volume]
    levels_log = []                                       # finished level tests
    tests_at = []                                         # (ticker, next bar, side, strength, round, level, price, kind) as each test starts
    seen_tests = {}
    regime_time = {}
    t = 0.0
    steps = int(years * mm.YEAR / STEP)
    volm = {x.ticker: 1.0 for x in listings}
    day_open = {x.ticker: x.price for x in listings}
    vacc = {x.ticker: 0.0 for x in listings}
    today = {}
    sessions = (PRE, POST)
    root = math.sqrt(STEP)
    for i in range(steps):
        t += STEP
        phase = t % DAY
        sess = session_mult(phase)
        rets, noise, vmul = model.step(t, STEP, listings, activity=sess, sessions=sessions)
        mv = model.market_vol(t)
        opening = phase == PRE
        m = rng.gauss(0, 1)
        sec = {s: rng.gauss(0, 1) for s in sectors}
        if opening:
            jm = rng.gauss(0, 1)
            js = {s: rng.gauss(0, 1) for s in sectors}
        for x in listings:
            ms, ss = x.beta * 0.21, 0.10                    # (as the engine with the new model: engine._random_market_moves)
            idio = math.sqrt(max(x.vol ** 2 - ms ** 2 - ss ** 2, 0.005 ** 2))
            nz = noise.get(x.ticker, 1.0)
            vm = volm[x.ticker] * mv * nz * sess
            t4 = rng.gauss(0, 1)     # (ten one-second t draws add up to nearly normal; the fat tails come from the volatility)
            shock = (ms * model.market_factor() * m + ss * sec[x.sector] + idio * t4) / annual_scale * root * vm
            cap = 8.0 * x.vol / annual_scale * root * max(vm, 1.0)          # (the engine caps a second at 8 sigmas)
            shock = max(-cap, min(cap, shock))
            scale = sess
            if opening:                                     # the opening auction: a fresh, independent shock
                jump = (ms * jm + ss * js[x.sector] + idio * rng.gauss(0, 1)) / annual_scale * math.sqrt(JUMP) * volm[x.ticker]
                jcap = max(0.08, 6.0 * x.vol / annual_scale * max(vm, 1.0))
                shock += max(-jcap, min(jcap, jump))
                scale = math.sqrt(sess * sess + JUMP / STEP)
            # the engine's soft daily brake (loosened for the new model): moves shrink once a stock is far from its open
            sd = x.vol / math.sqrt(365)
            limit = sd * (1.5 + 0.75 * min(abs(x.beta), 2.0)) * 1.5 * max(1.0, nz)
            far = abs(math.log(x.price / day_open.get(x.ticker, x.price)))
            shock /= 1.0 + (far / limit) ** 4
            r = (1 + rets.get(x.ticker, 0.0)) * (1 + shock) - 1
            # the engine's clustering, with the leverage effect: falls raise volatility more than rises
            sig = x.vol / annual_scale * root
            w = 1.25 if r < 0 else 0.75
            known = max(mv * nz * scale, 0.05)             # (surprises are measured against the known multipliers)
            volm[x.ticker] += 0.01 * STEP * (w * abs(shock) / (sig * known) - 0.8 * volm[x.ticker])
            volm[x.ticker] = max(0.5, min(3.0, 1 + 0.5 ** (STEP / mm.DAY) * (volm[x.ticker] - 1)))
            z = abs(r) / (sig * max(scale, 0.05))
            vacc[x.ticker] += STEP * sess * vmul.get(x.ticker, 1.0) * (0.4 + 0.6 * min(z, 6.0))   # (as engine._volume)
            x.price *= max(0.01, 1 + r)
            hacc[x.ticker] = max(hacc[x.ticker], x.price)
            lacc[x.ticker] = min(lacc[x.ticker], x.price)
            # the regular session's candle
            if regular(phase):
                d = today.get(x.ticker)
                if d is None or opening:
                    today[x.ticker] = [x.price, x.price, x.price, x.price, 0.0]
                else:
                    d[1], d[2], d[3] = max(d[1], x.price), min(d[2], x.price), x.price
                today[x.ticker][4] += STEP * sess * vmul.get(x.ticker, 1.0)
            elif x.ticker in today:
                days[x.ticker].append(today.pop(x.ticker))
        if int(t) % mm.DAY == 0:
            day_open.update({x.ticker: x.price for x in listings})
        regime_time[model.regime] = regime_time.get(model.regime, 0) + STEP
        if int(t) % mm.BAR == 0:
            for x in listings:
                closes[x.ticker].append(x.price)
                vol5[x.ticker].append(vacc[x.ticker])
                hi5[x.ticker].append(hacc[x.ticker])
                lo5[x.ticker].append(lacc[x.ticker])
                vacc[x.ticker] = 0.0
                hacc[x.ticker] = lacc[x.ticker] = x.price
        for x in listings:
            sw = model.swings.get(x.ticker)
            tst = sw.test if sw else None
            key = x.ticker
            prev = seen_tests.get(key)
            if prev is not None and prev is not tst:
                levels_log.append(dict(prev, tk=key))
            if tst is not None and tst is not prev:
                tests_at.append((x.ticker, len(closes[x.ticker]), tst["side"], tst["strength"], tst["round"], tst["level"],
                                 x.price, tst.get("kind", "swing")))
            seen_tests[key] = tst
    return {"closes": closes, "vol5": vol5, "hi5": hi5, "lo5": lo5, "trace": model.trace,
            "days": days, "levels": levels_log, "regime_time": regime_time, "years": years,
            "tests_at": tests_at, "caps": {c["ticker"]: float(c.get("market_cap", 0) or 1.0) for c in cos},
            "betas": {x.ticker: x.beta for x in listings}, "vols": {x.ticker: x.vol for x in listings}}


def market_series(closes, caps):
    """A cap-weighted, buy-and-hold index of the simulated companies (like the MSI 50)."""
    n = min(len(v) for v in closes.values())
    total = sum(caps[tk] for tk in closes)
    return [sum(caps[tk] * closes[tk][i] / closes[tk][0] for tk in closes) / total for i in range(n)]


def drawdowns(series, per_day=BARS_PER_DAY):
    daily = series[::per_day]
    peak, dd, count, in_dd = daily[0], 0.0, 0, False
    for v in daily:
        peak = max(peak, v)
        d = 1 - v / peak
        dd = max(dd, d)
        if d >= 0.10 and not in_dd:
            count, in_dd = count + 1, True
        if d < 0.03:
            in_dd = False
    return count, dd


def kurtosis(xs):
    m = statistics.fmean(xs)
    v = statistics.fmean([(x - m) ** 2 for x in xs])
    return statistics.fmean([(x - m) ** 4 for x in xs]) / (v * v) if v else 0.0


def autocorr(xs, lag=1):
    m = statistics.fmean(xs)
    num = sum((xs[i] - m) * (xs[i - lag] - m) for i in range(lag, len(xs)))
    den = sum((x - m) ** 2 for x in xs)
    return num / den if den else 0.0


def gap_stats(res):
    """Opening gaps against the previous regular close, in daily sigmas, and whether the session went back to it."""
    small, big, sizes = [], [], []
    for tk, ds in res["days"].items():
        sd = daily_sigma(ds)
        for a, b in zip(ds, ds[1:]):
            g = math.log(b[0] / a[3]) / sd
            sizes.append(abs(g))
            filled = b[2] <= a[3] <= b[1]
            if 0.05 < abs(g) < 0.3:
                small.append(filled)
            elif abs(g) > 1.0:
                big.append(filled)
    return small, big, sizes


def strategies(res):
    """Each rule trades every stock on 5-minute closes; returns (mean result per trade after costs, trades, per year)."""
    closes, vols = res["closes"], res["vols"]
    day = BARS_PER_DAY
    out = {}

    def run(name, rule, hold):
        results = []
        for tk, px in closes.items():
            sd = vols[tk] / math.sqrt(365)
            i = 20 * day
            while i < len(px) - hold:
                side = rule(px, i, sd)
                if side:
                    r = side * (px[i + hold] / px[i] - 1) - 2 * FEE
                    results.append(r)
                    i += hold
                else:
                    i += 1
        if results:
            out[name] = (statistics.fmean(results), len(results), sum(results) / res["years"] / len(closes))
        else:
            out[name] = (0.0, 0, 0.0)

    run("buy every 1-day drop of 1.5 sigma, hold 1 day", lambda px, i, sd: 1 if px[i] / px[i - day] - 1 < -1.5 * sd else 0, day)
    run("short every 1-day rise of 1.5 sigma, hold 1 day", lambda px, i, sd: -1 if px[i] / px[i - day] - 1 > 1.5 * sd else 0, day)
    run("buy when up over 10 days (momentum), hold 2 days", lambda px, i, sd: 1 if px[i] > px[i - 10 * day] * (1 + sd) else 0, 2 * day)
    run("short when down over 10 days, hold 2 days", lambda px, i, sd: -1 if px[i] < px[i - 10 * day] * (1 - sd) else 0, 2 * day)
    run("buy a 20-day high breakout, hold 3 days", lambda px, i, sd: 1 if px[i] >= max(px[i - 20 * day:i]) else 0, 3 * day)
    run("buy a 20-day low, hold 3 days", lambda px, i, sd: 1 if px[i] <= min(px[i - 20 * day:i]) else 0, 3 * day)
    run("buy and hold 10 days (the market, for comparison)", lambda px, i, sd: 1, 10 * day)

    def levels(name, keep, hold=12):
        """Trade the bounce at a level: long at support, short at resistance; out after `hold` bars, or at a stop half
        a daily sigma through the level."""
        results = []
        for tk, i, side, strength, rnd, level, entry, kind in res["tests_at"]:
            px = closes[tk]
            if i < 10 * day or i + hold >= len(px) or not keep(px, i, side, strength, rnd, kind):
                continue
            sd = vols[tk] / math.sqrt(365)
            stop = level * (1 - side * 0.5 * sd)
            out_px = px[i + hold]
            for j in range(i, i + hold + 1):               # (entered at the price when the test began: a limit order)
                if (px[j] - stop) * side <= 0:
                    out_px = stop if j == i else px[j]
                    break
            results.append(side * (out_px / entry - 1) - 2 * FEE)
        out[name] = (statistics.fmean(results), len(results), sum(results) / res["years"] / len(closes)) if results else (0.0, 0, 0.0)

    levels("trade every level test (bounce, 1h, stop)", lambda px, i, side, st, rnd, kind: True)
    levels("only strong levels with the 10-day trend", lambda px, i, side, st, rnd, kind: (st >= 2 or (rnd and st >= 1))
           and (px[i] - px[i - 10 * day]) * side > 0)
    levels("only the daily levels (yesterday, open, 52-week, averages)", lambda px, i, side, st, rnd, kind: kind != "swing")

    # gaps: fade every opening gap of 0.3 to 1 daily sigma at the open, out at the close (game-day candles)
    results = []
    for tk, ds in res["days"].items():
        sd = vols[tk] / math.sqrt(365)
        for a, b in zip(ds, ds[1:]):
            g = math.log(b[0] / a[3]) / sd
            if 0.3 <= abs(g) <= 1.0:
                side = -1 if g > 0 else 1
                results.append(side * (b[3] / b[0] - 1) - 2 * FEE)
    out["fade every 0.3-1 sigma opening gap, out at the close"] = (
        (statistics.fmean(results), len(results), sum(results) / res["years"] / len(closes)) if results else (0.0, 0, 0.0))
    return out


# ---------------------------------------------------------------------------------------------- what a trader reads
def _bar_of(t):
    """The 5-minute bar a moment falls in (bar k covers (300k, 300(k+1)])."""
    return max(0, math.ceil(t / mm.BAR) - 1)


def _usual_volume(v, k, days=10):
    """The average volume of the same 5-minute slot over the game days before (volume has a strong shape through the
    day, so a bar is compared with its own time of day)."""
    xs = [v[k - j * BARS_PER_DAY] for j in range(1, days + 1) if k - j * BARS_PER_DAY >= 0]
    return statistics.fmean(xs) if xs else 0.0


def _rsi(closes, n=14):
    out = [None] * len(closes)
    gain = loss = 0.0
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        g, l = max(ch, 0.0), max(-ch, 0.0)
        if i <= n:
            gain += g / n
            loss += l / n
            if i == n:
                out[i] = 100 - 100 / (1 + gain / loss) if loss else 100.0
        else:
            gain = (gain * (n - 1) + g) / n
            loss = (loss * (n - 1) + l) / n
            out[i] = 100 - 100 / (1 + gain / loss) if loss else 100.0
    return out


def structure(res):
    """How the structure reads (TA-A4 to TA-A8): volume on breakouts that run against ones that fail, climaxes, quiet
    pullbacks, wicks where a level holds, engulfing candles where a trend turns, the squeeze before a breakout, the
    timeframes agreeing, and RSI divergences and Bollinger squeezes on the game-day chart. Each against a baseline."""
    closes, vol5, hi5, lo5, vols = res["closes"], res["vol5"], res["hi5"], res["lo5"], res["vols"]
    out = {}
    # A4: volume where a level breaks, true breaks against false ones; and trading breaks by their volume
    ratios = {True: [], False: []}
    by_vol = {"high": [], "low": []}
    for t in res["levels"]:
        if t.get("outcome") != "break" or not t.get("crossed"):
            continue
        tk = t["tk"]
        k = _bar_of(t["crossed"])                   # (the bar of the crossing: its volume is known at its close, the entry)
        v, px = vol5[tk], closes[tk]
        if k + 13 >= len(v) or k < 10 * BARS_PER_DAY:
            continue
        u = _usual_volume(v, k)
        if u <= 0:
            continue
        ratio = v[k] / u
        ratios[bool(t.get("false"))].append(ratio)
        side = -t["side"]                            # the way it broke
        sd = vols[tk] / math.sqrt(365)
        stop = t["level"] * (1 - side * 0.25 * sd)   # back inside the level: it failed
        out_px = px[k + 12]
        for j in range(k + 1, k + 13):
            if (px[j] - stop) * side <= 0:
                out_px = px[j]
                break
        r = side * math.log(out_px / px[k]) - 2 * FEE
        if ratio >= 2.0:
            by_vol["high"].append(r)
        elif ratio < 1.5:
            by_vol["low"].append(r)
    out["break_volume"] = {k: (statistics.median(v) if v else float("nan"), len(v)) for k, v in ratios.items()}
    out["break_trades"] = {k: (statistics.fmean(v) if v else float("nan"), len(v)) for k, v in by_vol.items()}
    # A4: climaxes (from the model's trace): their volume, and the next game day after one (in the climax's direction)
    after, cvol = [], []
    for t, tk, what, d in res["trace"]:
        if what != "climax":
            continue
        k0, k = _bar_of(t), _bar_of(t + 150)
        px, v = closes[tk], vol5[tk]
        if k + BARS_PER_DAY >= len(px) or k0 < 10 * BARS_PER_DAY:
            continue
        u = sum(_usual_volume(v, j) for j in range(k0, k + 1))
        if u > 0:
            cvol.append(sum(v[k0:k + 1]) / u)
        after.append(d * math.log(px[k + BARS_PER_DAY] / px[k]) / (vols[tk] / math.sqrt(365)))
    out["climax"] = (len(after), statistics.median(cvol) if cvol else float("nan"), statistics.fmean(after) if after else float("nan"))
    # A4: a trader's climax rule: fade any 5-minute bar of 0.6 daily sigmas or more on 2.5 times the usual volume
    fades = []
    for tk, px in closes.items():
        sd, v = vols[tk] / math.sqrt(365), vol5[tk]
        k = 10 * BARS_PER_DAY
        while k < len(px) - 13:
            r = math.log(px[k] / px[k - 1])
            if abs(r) >= 0.6 * sd:
                u = _usual_volume(v, k)
                if u > 0 and v[k] >= 2.5 * u:
                    d = -1 if r > 0 else 1
                    fades.append(d * math.log(px[k + 12] / px[k]) - 2 * FEE)
                    k += 12
                    continue
            k += 1
    out["climax_fade"] = (statistics.fmean(fades) if fades else float("nan"), len(fades))
    # A4: volume on a trend's impulse legs against its pullbacks (the model's legs, from the trace)
    legs = {"impulse": [], "pullback": []}
    state = {}
    for t, tk, what, d in res["trace"]:
        if what != "level":                               # (level tests are logged too, for the Daily Chart)
            state.setdefault(tk, []).append((t, what))
    for tk, evs in state.items():
        v = vol5[tk]
        for (t0, what), (t1, _) in zip(evs, evs[1:]):
            if what not in legs:
                continue
            for k in range(_bar_of(t0) + 1, min(_bar_of(t1), len(v))):
                if k >= 10 * BARS_PER_DAY and PRE + mm.BAR <= (mm.BAR * (k + 1)) % DAY <= DAY - POST:
                    u = _usual_volume(v, k)
                    if u > 0:
                        legs[what].append(v[k] / u)
    out["leg_volume"] = {k: statistics.fmean(v) if v else float("nan") for k, v in legs.items()}
    # A5: the wick on the level's side of the bar where a test began, holds against everything else
    wick_hold, wick_all = [], []
    for t in res["levels"]:
        tk, k0 = t["tk"], _bar_of(t["start"])
        k1 = min(_bar_of(t.get("crossed") or t["start"] + 600), len(closes[tk]) - 1)
        if k0 < 1 or k0 >= len(closes[tk]):
            continue
        s = t["side"]
        k = min(range(k0, max(k0, k1) + 1), key=lambda j: lo5[tk][j] if s == 1 else -hi5[tk][j])   # the deepest probe
        o, c, h, l = closes[tk][k - 1], closes[tk][k], hi5[tk][k], lo5[tk][k]
        if h <= l:
            continue
        w = ((min(o, c) - l) if s == 1 else (h - max(o, c))) / (h - l)
        (wick_hold if t["outcome"] == "hold" else wick_all).append(w)
    base = []
    for tk in closes:
        for k in range(1, len(closes[tk]), 7):
            o, c, h, l = closes[tk][k - 1], closes[tk][k], hi5[tk][k], lo5[tk][k]
            if h > l:
                base.append((min(o, c) - l) / (h - l))
    out["wicks"] = (statistics.fmean(wick_hold) if wick_hold else float("nan"),
                    statistics.fmean(wick_all) if wick_all else float("nan"), statistics.fmean(base) if base else float("nan"))
    # A5: engulfing 15-minute candles where the model turned a trend, against all 15-minute candles

    def c15(tk, j):                                  # the 15-minute candle made of 5-minute bars 3j .. 3j+2
        px = closes[tk]
        a, b = 3 * j, 3 * j + 2
        return px[a - 1], px[b], max(hi5[tk][a:b + 1]), min(lo5[tk][a:b + 1])

    def engulfs(tk, j):
        o0, c0, _, _ = c15(tk, j - 1)
        o1, c1, _, _ = c15(tk, j)
        return (c1 - o1) * (c0 - o0) < 0 and max(o1, c1) >= max(o0, c0) and min(o1, c1) <= min(o0, c0) and abs(c1 - o1) > 0
    at_rev = []
    for t, tk, what, d in res["trace"]:
        if what == "reversal":
            j = (_bar_of(t + 120)) // 3
            if 2 <= j and 3 * j + 2 < len(closes[tk]):
                at_rev.append(engulfs(tk, j))
    allc = [engulfs(tk, j) for tk in closes for j in range(2, (len(closes[tk]) - 3) // 3, 5)]
    out["engulfing"] = (statistics.fmean(at_rev) if at_rev else float("nan"), len(at_rev), statistics.fmean(allc) if allc else float("nan"))
    # A5/A8: the squeeze before a range's breakout: how big the 5-minute moves were in the 2 hours before, against usual
    sq = []
    for t, tk, what, d in res["trace"]:
        if what != "breakout":
            continue
        k = _bar_of(t)
        px = closes[tk]
        if k < 40 * BARS_PER_DAY:
            continue
        before = [abs(math.log(px[i] / px[i - 1])) for i in range(k - 24, k)]
        usual = [abs(math.log(px[i] / px[i - 1])) for i in range(k - 30 * BARS_PER_DAY, k - 24)]
        if usual and statistics.fmean(usual) > 0:
            sq.append(statistics.fmean(before) / statistics.fmean(usual))
    out["squeeze"] = (statistics.fmean(sq) if sq else float("nan"), len(sq))
    # A6: timeframes agreeing: after a 10-day move of a daily sigma or more, does the next game day go the same way?
    agree, base_days = [], 0
    for tk, ds in res["days"].items():
        sd = vols[tk] / math.sqrt(365)
        for i in range(10, len(ds) - 1):
            m = math.log(ds[i][3] / ds[i - 10][3])
            if abs(m) >= sd:
                nxt = math.log(ds[i + 1][3] / ds[i + 1][0])
                agree.append((nxt > 0) == (m > 0))
            base_days += 1
    out["agree"] = (statistics.fmean(agree) if agree else float("nan"), len(agree))
    # A8: RSI divergences and Bollinger squeezes on the game-day chart
    div = {1: [], -1: []}
    after_high = {1: [], -1: []}
    sqz, sqz_base = [], []
    for tk, ds in res["days"].items():
        cl = [d[3] for d in ds]
        sd = daily_sigma(ds)
        rsi = _rsi(cl)
        bw = [None] * len(cl)                         # Bollinger band width (20, 2) as a share of the average
        for j in range(19, len(cl)):
            seg = cl[j - 19:j + 1]
            m = statistics.fmean(seg)
            bw[j] = 4 * statistics.pstdev(seg) / m
        for i in range(40, len(cl) - 10):
            ahead = math.log(cl[i + 10] / cl[i]) / sd
            for s in (1, -1):                         # +1: a new 20-day high (bearish divergence); -1: a new low
                window = cl[i - 20:i]
                if (cl[i] - (max(window) if s == 1 else min(window))) * s <= 0:
                    continue
                after_high[s].append(-s * ahead)
                prev = max(range(i - 20, i - 4), key=lambda j: cl[j] * s)        # the last extreme, 5-20 days back
                if rsi[i] is not None and rsi[prev] is not None and (rsi[i] - rsi[prev]) * s < -3:
                    div[s].append(-s * ahead)
            if i >= 140:
                big = abs(ahead)
                sqz_base.append(big)
                if bw[i] <= min(bw[i - 120:i]):
                    sqz.append(big)
    out["divergence"] = {s: (statistics.fmean(div[s]) if div[s] else float("nan"), len(div[s]),
                             statistics.fmean(after_high[s]) if after_high[s] else float("nan")) for s in (1, -1)}
    out["bb_squeeze"] = (statistics.fmean(sqz) if sqz else float("nan"), len(sqz),
                         statistics.fmean(sqz_base) if sqz_base else float("nan"))
    return out


# ---------------------------------------------------------------------------------------------- chart patterns (TA-A9)
PATTERN_SWINGS = (1.5, 2.5)    # the zigzags that find patterns on the game-day chart, in daily sigmas


def daily_sigma(ds):
    """A listing's realised daily volatility (close to close): what a trader reads off the chart, and the yardstick the
    pattern finder uses (a stated volatility can be far from what a high-beta stock really does)."""
    r = [math.log(b[3] / a[3]) for a, b in zip(ds, ds[1:]) if a[3] > 0 and b[3] > 0]
    return statistics.pstdev(r) if len(r) > 10 else 0.02


def pattern_stats(res):
    """Every pattern a trader would find on the game-day charts (patterns.py), what became of it, and the result of
    trading each one that completes (in at the close that breaks the trigger, out at the target, at a close beyond the
    other side, or after 20 game days), costs included. Plus the patterns the model started (its trace)."""
    found = {}
    for tk, ds in res["days"].items():
        if len(ds) < 60:
            continue
        sd = daily_sigma(ds)
        candles = [[d[0], d[1], d[2], d[3], d[4]] for d in ds]
        for p in patterns.find_all(candles, [w * sd for w in PATTERN_SWINGS]):
            if p["at"] < 20:
                continue
            o = patterns.outcome(candles, p, wait=10, hold=20)
            if o is None:
                continue
            rec = found.setdefault(p["kind"], {"n": 0, "completed": 0, "worked": 0, "trades": []})
            rec["n"] += 1
            if o["completed"]:
                rec["completed"] += 1
                rec["worked"] += o["worked"]
                rec["trades"].append(p["dir"] * math.log(o["exit"] / o["entry"]) - 2 * FEE)
    # the patterns the model made, and whether the detector found one of the same kind while it ran (or within a few
    # game days of its end): how recognisable they are
    by_tk = {}
    for tk, ds in res["days"].items():
        if len(ds) >= 60:
            sd = daily_sigma(ds)
            by_tk[tk] = patterns.find_all([[d[0], d[1], d[2], d[3], d[4]] for d in ds], [w * sd for w in PATTERN_SWINGS])
    made, open_ = {}, {}
    for t, tk, what, d in res["trace"]:
        if what.startswith("pattern:"):
            open_[tk] = (what[8:], t)
        elif what in ("trend", "range", "free") and tk in open_:
            kind, t0 = open_.pop(tk)
            base = kind.replace("_up", "").replace("_down", "")
            d0, d1 = int(t0 // DAY), int(t // DAY) + 3
            hit = any(p["kind"] == base and d0 <= p["at"] <= d1 for p in by_tk.get(tk, []))   # (candle i is game day i)
            rec = made.setdefault(kind, {"n": 0, "found": 0})
            rec["n"] += 1
            rec["found"] += hit
    return found, made



def level_stats(levels):
    by, kinds = {}, {}
    fails = breaks = 0
    for t in levels:
        k = "strong (3+ touches or round)" if (t["strength"] >= 3 or (t["round"] and t["strength"] >= 1)) else "weak"
        h, n = by.get(k, (0, 0))
        by[k] = (h + (t["outcome"] == "hold"), n + 1)
        for kind in str(t.get("kind", "swing")).split("+"):
            h, n = kinds.get(kind, (0, 0))
            kinds[kind] = (h + (t["outcome"] == "hold"), n + 1)
        if t["outcome"] == "break":
            breaks += 1
            fails += bool(t.get("false"))
    return by, kinds, (fails / breaks if breaks else 0.0), len(levels)


def main():
    years = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 101
    report(years, seeds, n, first)


def report(years, seeds, n, first, model_settings=None):
    print(f"realism check: {seeds} markets x {years} game years x {n} stocks, steps of {STEP}s "
          f"(regimes' long-run drift taken out: {mm.REGIME_MEAN_DRIFT:+.3f}; time shares {', '.join(f'{k} {v:.0%}' for k, v in mm.REGIME_SHARE.items())})")
    agg = {"ret": [], "dd_count": [], "dd_max": [], "kurt": [], "ac": [], "acabs": [], "strat": {}, "levels": [], "regime": {},
           "small": [], "big": [], "gaps": [], "structure": [], "found": {}, "made": {}}
    for s in range(first, first + seeds):
        t0 = time.time()
        res = simulate(years, n, s, model_settings)
        mkt = market_series(res["closes"], res["caps"])
        yr = mkt[-1] ** (1 / years) - 1
        c, dmax = drawdowns(mkt)
        rets = [mkt[i] / mkt[i - 1] - 1 for i in range(1, len(mkt))]
        one = next(iter(res["closes"].values()))
        # (regular-session bars only, and not the one with the opening jump: the thin sessions and the jump would make
        # the tails look far fatter than any single session's)
        r1 = [one[i] / one[i - 1] - 1 for i in range(1, len(one)) if PRE + mm.BAR <= (mm.BAR * (i + 1)) % DAY <= DAY - POST]
        agg["ret"].append(yr)
        agg["dd_count"].append(c / years)
        agg["dd_max"].append(dmax)
        agg["kurt"].append(kurtosis(r1))
        agg["ac"].append(autocorr(rets))
        agg["acabs"].append(autocorr([abs(x) for x in rets]))
        for k, v in strategies(res).items():
            agg["strat"].setdefault(k, []).append(v)
        agg["levels"] += res["levels"]
        small, big, sizes = gap_stats(res)
        agg["small"] += small
        agg["big"] += big
        agg["gaps"] += sizes
        for k, v in res["regime_time"].items():
            agg["regime"][k] = agg["regime"].get(k, 0) + v
        agg["structure"].append(structure(res))
        found, made = pattern_stats(res)
        trades = []
        for k, v in found.items():
            a = agg["found"].setdefault(k, {"n": 0, "completed": 0, "worked": 0, "trades": []})
            for kk in ("n", "completed", "worked"):
                a[kk] += v[kk]
            a["trades"] += v["trades"]
            trades += v["trades"]
        for k, v in made.items():
            a = agg["made"].setdefault(k, [0, 0])
            a[0] += v["n"]
            a[1] += v["found"]
        agg["strat"].setdefault("trade every completed chart pattern (stop, target, 20 days)", []).append(
            (statistics.fmean(trades), len(trades), sum(trades) / years / n) if trades else (0.0, 0, 0.0))
        print(f"  seed {s}: market {yr:+.1%} a game year, {c} drawdowns of 10%+, deepest {dmax:.1%} ({time.time() - t0:.0f}s)")
    tot = sum(agg["regime"].values())
    print("\n1. The long run")
    print(f"   market return a game year: mean {statistics.fmean(agg['ret']):+.1%}  (target +5% to +10%; one seed is noisy)")
    print(f"   10% drawdowns a game year: {statistics.fmean(agg['dd_count']):.2f}; deepest: {max(agg['dd_max']):.1%}")
    print("   time in each regime: " + ", ".join(f"{k} {v / tot:.0%}" for k, v in sorted(agg["regime"].items())))
    print("\n2. Stylised facts (5-minute returns)")
    print(f"   kurtosis of one stock, regular session: {statistics.fmean(agg['kurt']):.1f} (normal = 3; real markets: well above 3)")
    print(f"   autocorrelation of market returns: {statistics.fmean(agg['ac']):+.3f} (target: near 0)")
    print(f"   autocorrelation of absolute returns: {statistics.fmean(agg['acabs']):+.3f} (target: clearly positive)")
    by, kinds, false_share, total = level_stats(agg["levels"])
    print(f"\n3. Support and resistance ({total} tests)")
    for k, (h, nn) in sorted(by.items()):
        print(f"   {k}: held {h / nn:.0%} of {nn}")
    print("   by kind: " + ", ".join(f"{k} {h / nn:.0%} of {nn}" for k, (h, nn) in sorted(kinds.items(), key=lambda kv: -kv[1][1])))
    print(f"   breaks that failed (false breakouts): {false_share:.0%} (target 20-35%)")
    if agg["gaps"]:
        g = sorted(agg["gaps"])
        fs = sum(agg["small"]) / len(agg["small"]) if agg["small"] else float("nan")
        fb = sum(agg["big"]) / len(agg["big"]) if agg["big"] else float("nan")
        print(f"\n4. Opening gaps ({len(g)}): median {g[len(g) // 2]:.2f} daily sigmas, 90th percentile {g[int(len(g) * 0.9)]:.2f}")
        print(f"   filled the same day: small (0.05-0.3 sigma) {fs:.0%} of {len(agg['small'])} (target 60-85%), "
              f"large (1+ sigma) {fb:.0%} of {len(agg['big'])} (target under 40%)")
    print("\n5. Strategies, costs included (0.1% a side), per trade and per stock per game year")
    for k, vs in agg["strat"].items():
        mean = statistics.fmean(v[0] for v in vs)
        trades = sum(v[1] for v in vs)
        per_year = statistics.fmean(v[2] for v in vs)
        print(f"   {k:<60} {mean:+.3%} a trade, {trades:>6} trades, {per_year:+.1%} a game year")
    st = agg["structure"]
    f = lambda key, i: statistics.fmean(x[key][i] for x in st)
    print("\n6. The structure a trader reads (each against its baseline)")
    print(f"   volume where a level breaks, times the usual for that time of day: on breaks that run "
          f"{statistics.fmean(x['break_volume'][False][0] for x in st):.2f}, on ones that fail {statistics.fmean(x['break_volume'][True][0] for x in st):.2f}")
    print(f"   trading breaks in their direction (1h, stop back inside): on 2x+ volume "
          f"{statistics.fmean(x['break_trades']['high'][0] for x in st):+.3%} a trade, under 1.5x {statistics.fmean(x['break_trades']['low'][0] for x in st):+.3%}")
    print(f"   climaxes: {sum(x['climax'][0] for x in st) / len(st) / years / n:.1f} a stock a game year, volume {f('climax', 1):.1f}x usual, "
          f"next game day {f('climax', 2):+.2f} sigma the climax's way; fading any big 5-minute bar on 2.5x volume {f('climax_fade', 0):+.3%} a trade")
    print(f"   volume on a trend's impulse legs {statistics.fmean(x['leg_volume']['impulse'] for x in st):.2f}x usual, "
          f"on its pullbacks {statistics.fmean(x['leg_volume']['pullback'] for x in st):.2f}x")
    print(f"   wick on the level's side of the bar that probed it: where the level held {f('wicks', 0):.2f}, where it broke "
          f"{f('wicks', 1):.2f}, any bar {f('wicks', 2):.2f} (share of the bar's range)")
    print(f"   an engulfing 15-minute candle where a trend turned: {f('engulfing', 0):.0%} (any candle {f('engulfing', 2):.0%})")
    print(f"   5-minute moves in the 2 hours before a range breaks out: {f('squeeze', 0):.2f}x usual (a squeeze)")
    print(f"   the next game day goes the way of a 10-day move of a sigma or more: {f('agree', 0):.1%} (50% = no agreement)")
    for s_, lab in ((1, "bearish divergence (a new 20-day high on a lower RSI)"), (-1, "bullish divergence (a new low on a higher RSI)")):
        print(f"   {lab}: the next 10 game days {statistics.fmean(x['divergence'][s_][0] for x in st):+.2f} sigma the expected way "
              f"(n {sum(x['divergence'][s_][1] for x in st)}), after any new extreme {statistics.fmean(x['divergence'][s_][2] for x in st):+.2f}")
    print(f"   after a Bollinger squeeze (the narrowest bands in 120 game days) the next 10 days move {f('bb_squeeze', 0):.2f} sigma "
          f"(any time {f('bb_squeeze', 2):.2f})")
    print("\n7. Chart patterns on the game-day charts (patterns.py)")
    print(f"   {'':<24} {'a stock-yr':>10} {'completed':>10} {'worked':>8} {'trade':>9} {'median':>9}")
    sy = seeds * years * n
    for k in sorted(agg["found"], key=lambda k: -agg["found"][k]["n"]):
        a = agg["found"][k]
        tr = a["trades"]
        print(f"   {k:<24} {a['n'] / sy:>10.2f} {a['completed'] / a['n']:>10.0%} {a['worked'] / max(1, a['completed']):>8.0%} "
              f"{(statistics.fmean(tr) if tr else float('nan')):>+9.2%} {(statistics.median(tr) if tr else float('nan')):>+9.2%}")
    if agg["made"]:
        print("   made by the model a stock-year (and the share a trader would have found): " + ", ".join(
            f"{k} {v[0] / sy:.2f} ({v[1] / max(1, v[0]):.0%})" for k, v in sorted(agg["made"].items())))
    return agg


if __name__ == "__main__":
    main()
