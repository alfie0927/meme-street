"""The realism and "no free money" check for the price model (docs/ROADMAP.md P11).

    python tools/realism.py [game_years] [seeds] [stocks] [first_seed]       (defaults: 2 years, 3 seeds, 40 stocks, seed 101)

It runs market_model.py on its own, with the engine's three-factor noise rebuilt here in steps of 10 seconds (far faster
than the whole engine), on companies drawn from the content packs, and prints:

1. The long run: the market's return per game year (target: about +5% to +10%), the time spent in each regime, the
   number of 10% drawdowns a game year and the deepest one.
2. Stylised facts of real returns: fat tails (the kurtosis of 5-minute returns is well above 3), almost no
   autocorrelation of returns, and volatility clustering (the autocorrelation of absolute returns is clearly positive).
3. Support and resistance: how often levels hold, by strength, and how many breaks fail.
4. Strategies, costs included (0.1% a side), compared with holding the market: no unskilled rule may beat holding by a
   wide margin. Reported as the average result per trade and per game year.

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

FEE = 0.001
STEP = 10                      # seconds per simulation step
BARS_PER_DAY = mm.DAY // mm.BAR


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


def simulate(years, n, seed):
    rng = random.Random(seed)
    model = mm.MarketModel({}, rng=random.Random(seed * 7 + 1), now=0.0)
    cos = companies(n, rng)
    listings = [types.SimpleNamespace(ticker=c["ticker"], price=float(c.get("initial_price", 50)), vol=float(c.get("vol", 0.3)),
                                      beta=float(c.get("beta", 1.0)), sector=c["sector"], asset_type="equity", moonshot=False)
                for c in cos]
    sectors = sorted({x.sector for x in listings})
    annual_scale = math.sqrt(mm.YEAR)
    closes = {x.ticker: [] for x in listings}            # 5-minute closes
    levels_log = []                                       # finished level tests
    tests_at = []                                         # (ticker, next bar, side, strength, round, level, price) as each test starts
    seen_tests = {}
    regime_time = {}
    t = 0.0
    steps = int(years * mm.YEAR / STEP)
    volm = {x.ticker: 1.0 for x in listings}
    day_open = {x.ticker: x.price for x in listings}
    for i in range(steps):
        t += STEP
        rets, noise, _ = model.step(t, STEP, listings)
        mv = model.market_vol(t)
        m = rng.gauss(0, 1)
        sec = {s: rng.gauss(0, 1) for s in sectors}
        root = math.sqrt(STEP)
        for x in listings:
            ms, ss = x.beta * 0.21, 0.10                    # (as the engine with the new model: engine._random_market_moves)
            idio = math.sqrt(max(x.vol ** 2 - ms ** 2 - ss ** 2, 0.005 ** 2))
            vm = volm[x.ticker] * mv * noise.get(x.ticker, 1.0)
            t4 = rng.gauss(0, 1)     # (ten one-second t draws add up to nearly normal; the fat tails come from the volatility)
            shock = (ms * model.market_factor() * m + ss * sec[x.sector] + idio * t4) / annual_scale * root * vm
            cap = 8.0 * x.vol / annual_scale * root * max(vm, 1.0)          # (the engine caps a second at 8 sigmas)
            shock = max(-cap, min(cap, shock))
            # the engine's soft daily brake (loosened for the new model): moves shrink once a stock is far from its open
            sd = x.vol / math.sqrt(365)
            limit = sd * (1.5 + 0.75 * min(abs(x.beta), 2.0)) * 1.5 * max(1.0, noise.get(x.ticker, 1.0))
            far = abs(math.log(x.price / day_open.get(x.ticker, x.price)))
            shock /= 1.0 + (far / limit) ** 4
            r = (1 + rets.get(x.ticker, 0.0)) * (1 + shock) - 1
            # the engine's clustering, with the leverage effect: falls raise volatility more than rises
            sig = x.vol / annual_scale * root
            w = 1.25 if r < 0 else 0.75
            known = max(mv * noise.get(x.ticker, 1.0), 0.05)       # (surprises are measured against the known multipliers)
            volm[x.ticker] += 0.01 * STEP * (w * abs(shock) / (sig * known) - 0.8 * volm[x.ticker])
            volm[x.ticker] = max(0.5, min(3.0, 1 + 0.5 ** (STEP / mm.DAY) * (volm[x.ticker] - 1)))
            x.price *= max(0.01, 1 + r)
        if int(t) % mm.DAY == 0:
            day_open.update({x.ticker: x.price for x in listings})
        regime_time[model.regime] = regime_time.get(model.regime, 0) + STEP
        if int(t) % mm.BAR == 0:
            for x in listings:
                closes[x.ticker].append(x.price)
        for x in listings:
            sw = model.swings.get(x.ticker)
            tst = sw.test if sw else None
            key = x.ticker
            prev = seen_tests.get(key)
            if prev is not None and prev is not tst:
                levels_log.append(dict(prev))
            if tst is not None and tst is not prev:
                tests_at.append((x.ticker, len(closes[x.ticker]), tst["side"], tst["strength"], tst["round"], tst["level"], x.price))
            seen_tests[key] = tst
    return {"closes": closes, "levels": levels_log, "regime_time": regime_time, "years": years, "tests_at": tests_at,
            "caps": {c["ticker"]: float(c.get("market_cap", 0) or 1.0) for c in cos},
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
        for tk, i, side, strength, rnd, level, entry in res["tests_at"]:
            px = closes[tk]
            if i < 10 * day or i + hold >= len(px) or not keep(px, i, side, strength, rnd):
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

    levels("trade every level test (bounce, 1h, stop)", lambda px, i, side, st, rnd: True)
    levels("only strong levels with the 10-day trend", lambda px, i, side, st, rnd: (st >= 2 or (rnd and st >= 1))
           and (px[i] - px[i - 10 * day]) * side > 0)
    return out


def level_stats(levels):
    by = {}
    fails = breaks = 0
    for t in levels:
        k = "strong (3+ touches or round)" if (t["strength"] >= 3 or (t["round"] and t["strength"] >= 1)) else "weak"
        h, n = by.get(k, (0, 0))
        by[k] = (h + (t["outcome"] == "hold"), n + 1)
        if t["outcome"] == "break":
            breaks += 1
            fails += bool(t.get("false"))
    return by, (fails / breaks if breaks else 0.0), len(levels)


def main():
    years = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 101
    print(f"realism check: {seeds} markets x {years} game years x {n} stocks, steps of {STEP}s "
          f"(regimes' long-run drift taken out: {mm.REGIME_MEAN_DRIFT:+.3f}; time shares {', '.join(f'{k} {v:.0%}' for k, v in mm.REGIME_SHARE.items())})")
    agg = {"ret": [], "dd_count": [], "dd_max": [], "kurt": [], "ac": [], "acabs": [], "strat": {}, "levels": [], "regime": {}}
    for s in range(first, first + seeds):
        t0 = time.time()
        res = simulate(years, n, s)
        mkt = market_series(res["closes"], res["caps"])
        yr = mkt[-1] ** (1 / years) - 1
        c, dmax = drawdowns(mkt)
        rets = [mkt[i] / mkt[i - 1] - 1 for i in range(1, len(mkt))]
        one = next(iter(res["closes"].values()))
        r1 = [one[i] / one[i - 1] - 1 for i in range(1, len(one))]
        agg["ret"].append(yr)
        agg["dd_count"].append(c / years)
        agg["dd_max"].append(dmax)
        agg["kurt"].append(kurtosis(r1))
        agg["ac"].append(autocorr(rets))
        agg["acabs"].append(autocorr([abs(x) for x in rets]))
        for k, v in strategies(res).items():
            agg["strat"].setdefault(k, []).append(v)
        agg["levels"] += res["levels"]
        for k, v in res["regime_time"].items():
            agg["regime"][k] = agg["regime"].get(k, 0) + v
        print(f"  seed {s}: market {yr:+.1%} a game year, {c} drawdowns of 10%+, deepest {dmax:.1%} ({time.time() - t0:.0f}s)")
    tot = sum(agg["regime"].values())
    print("\n1. The long run")
    print(f"   market return a game year: mean {statistics.fmean(agg['ret']):+.1%}  (target +5% to +10%; one seed is noisy)")
    print(f"   10% drawdowns a game year: {statistics.fmean(agg['dd_count']):.2f}; deepest: {max(agg['dd_max']):.1%}")
    print("   time in each regime: " + ", ".join(f"{k} {v / tot:.0%}" for k, v in sorted(agg["regime"].items())))
    print("\n2. Stylised facts (5-minute returns)")
    print(f"   kurtosis of one stock: {statistics.fmean(agg['kurt']):.1f} (normal = 3; real markets: well above 3)")
    print(f"   autocorrelation of market returns: {statistics.fmean(agg['ac']):+.3f} (target: near 0)")
    print(f"   autocorrelation of absolute returns: {statistics.fmean(agg['acabs']):+.3f} (target: clearly positive)")
    by, false_share, total = level_stats(agg["levels"])
    print(f"\n3. Support and resistance ({total} tests)")
    for k, (h, nn) in sorted(by.items()):
        print(f"   {k}: held {h / nn:.0%} of {nn}")
    print(f"   breaks that failed (false breakouts): {false_share:.0%} (target 20-35%)")
    print("\n4. Strategies, costs included (0.1% a side), per trade and per stock per game year")
    for k, vs in agg["strat"].items():
        mean = statistics.fmean(v[0] for v in vs)
        trades = sum(v[1] for v in vs)
        per_year = statistics.fmean(v[2] for v in vs)
        print(f"   {k:<52} {mean:+.3%} a trade, {trades:>6} trades, {per_year:+.1%} a game year")


if __name__ == "__main__":
    main()
