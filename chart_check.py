"""How much do Meme Street's charts move like real ones? (MARKET_REALISM.md has the research and the targets.)

    python chart_check.py [game_days] [seed] [--cached]   (defaults: 8 game days, seed 7; about 20 seconds a game day;
                                                            --cached re-reads the last run of the same length and seed)

Runs the real engine (the content packs as shipped, the new price model, the trading sessions) with nobody trading,
records every listing's one-minute candles and every game day, and compares the statistics real stock prices are known
for with the targets from the research. A game day (30 minutes) plays the part of a trading day, so one minute here is
about 13 minutes of a real 6.5-hour session.
"""
import math
import os
import pickle
import random
import statistics
import sys
import time
import types

import engine

MIN = 60


FIXED_START = 1_800_000_000          # a fixed clock, so two runs with the same seed are the same market


def run(days, seed, settings=None, model=None):
    random.seed(seed)
    clock = engine.time
    engine.time = types.SimpleNamespace(time=lambda: float(FIXED_START))
    try:
        e = engine.Engine(state_file=None)
    finally:
        engine.time = clock
    e.settings.update(settings or {})
    if e.model is not None and model:
        e.model.p.update(model)
    e._public = lambda: None                     # (the page's state and the board are not needed here)
    e._board = lambda: None
    start = (int(e.now // engine.MARKET_DAY_SECONDS) + 1) * engine.MARKET_DAY_SECONDS
    e.tick(now=start - 1)
    tks = [tk for tk, s in e.stocks.items() if s.asset_type in ("equity", "commodity") and s.spec is None]
    bars = {tk: [] for tk in tks}                # [t, o, h, l, c, v] one-minute candles
    reports = []                                 # (ticker, time) of earnings reports
    seen_news = 0
    cur = {}
    t0 = time.time()
    for i in range(int(days * engine.MARKET_DAY_SECONDS)):
        now = start + i
        e.tick(now=now)
        for tk in tks:
            s = e.stocks.get(tk)
            if s is None:
                continue
            p = s.price
            v = s.candles[-1][5] if s.candles and len(s.candles[-1]) > 5 else 0.0
            c = cur.get(tk)
            if c is None or now // MIN != c[0] // MIN:
                if c is not None:
                    bars[tk].append(c)
                cur[tk] = [now, p, p, p, p, 0.0, v]          # (the last field: the minute candle's volume so far)
            else:
                c[2], c[3], c[4] = max(c[2], p), min(c[3], p), p
                c[6] = v
        for c in cur.values():
            c[5] = c[6]
        news = list(e.news_log)
        if e.news_seq > seen_news:
            for n in news[-(e.news_seq - seen_news):]:
                if n["kind"] == "earnings" and n["text"].startswith("EARNINGS"):          # (reports, not guidance)
                    reports.extend((tk, n["t"]) for tk in n["tickers"])
            seen_news = e.news_seq
    print(f"(ran {days} game days, {len(tks)} listings, in {time.time() - t0:.0f} s)")
    return e, bars, reports, start


def kurt(x):
    m = statistics.fmean(x)
    v = statistics.fmean([(a - m) ** 2 for a in x])
    return statistics.fmean([(a - m) ** 4 for a in x]) / v / v if v else 0.0


def acf(x, lag):
    m = statistics.fmean(x)
    d = sum((a - m) ** 2 for a in x)
    return sum((x[i] - m) * (x[i - lag] - m) for i in range(lag, len(x))) / d if d else 0.0


def corr(a, b):
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb) if sa and sb else 0.0


def hill(x, frac=0.02):
    """The tail exponent of |x| from the largest `frac` of values (Hill's estimator); real stocks: about 3."""
    a = sorted((abs(v) for v in x if v), reverse=True)
    k = max(10, int(len(a) * frac))
    if len(a) <= k:
        return float("nan")
    xk = a[k]
    return k / sum(math.log(a[i] / xk) for i in range(k))


def report(e, bars, reports, start, days):
    day = engine.MARKET_DAY_SECONDS
    rows = []

    def row(name, value, target, ok):
        rows.append((name, value, target, "ok" if ok else "OFF"))

    # Volatility and volume follow the 30-minute session cycle (busy at the open, thin before and after); dependence is
    # measured after dividing that known daily shape out, as studies of real intraday data do.
    shape_r, shape_v = {}, {}
    for tk, b in bars.items():
        for i in range(1, len(b)):
            if b[i - 1][4] > 0 and b[i][4] > 0:
                k = int(b[i][0] % day // MIN)
                shape_r.setdefault(k, []).append(abs(math.log(b[i][4] / b[i - 1][4])))
                shape_v.setdefault(k, []).append(b[i][5])
    shape_r = {k: (statistics.fmean(v) or 1e-12) for k, v in shape_r.items()}
    shape_v = {k: (statistics.fmean(v) or 1e-12) for k, v in shape_v.items()}

    # standardised one-minute returns per listing (each divided by its own volatility and the time of day, so they can be pooled)
    pooled, absacf1, absacf10, absacf30, racf1, lev, vcorr, vacf1, vacf10 = [], [], [], [], [], [], [], [], []
    for tk, b in bars.items():
        if len(b) < 200:
            continue
        idx = [i for i in range(1, len(b)) if b[i - 1][4] > 0 and b[i][4] > 0]
        r = [math.log(b[i][4] / b[i - 1][4]) / shape_r[int(b[i][0] % day // MIN)] for i in idx]
        sd = statistics.pstdev(r) or 1.0
        z = [x / sd for x in r]
        pooled += z
        a = [abs(x) for x in z]
        absacf1.append(acf(a, 1))
        absacf10.append(acf(a, 10))
        absacf30.append(acf(a, 30))
        racf1.append(acf(z, 1))
        future = [sum(a[i + 1:i + 11]) for i in range(len(a) - 11)]
        lev.append(corr(z[:len(future)], future))
        vol = [max(b[i][5], 1e-9) / shape_v[int(b[i][0] % day // MIN)] for i in idx]
        if statistics.pstdev(vol) > 0:
            vcorr.append(corr(a, vol))
            lv = [math.log(v) for v in vol]
            vacf1.append(acf(lv, 1))
            vacf10.append(acf(lv, 10))
    k1 = kurt(pooled)
    row("Kurtosis of one-minute returns", f"{k1:.1f}", "above 6 (fat tails)", k1 > 6)
    h = hill(pooled)
    row("Tail exponent (Hill, top 2%)", f"{h:.2f}", "about 3 (2.5 to 4)", 2.5 <= h <= 4.0)
    # Momentum from one minute to the next, measured on the signs of the moves (robust: a correlation of the moves
    # themselves is dominated by a handful of huge minutes); real stocks: about 0, slightly negative.
    sg = []
    for tk, b in bars.items():
        r = [math.log(b[i][4] / b[i - 1][4]) for i in range(1, len(b)) if b[i - 1][4] > 0 and b[i][4] > 0]
        sgn = [(x > 0) - (x < 0) for x in r]
        if len(sgn) > 100 and statistics.pstdev(sgn) > 0:
            sg.append(acf(sgn, 1))
    m = statistics.fmean(sg)
    row("Same direction next minute (sign autocorrelation, one stock)", f"{m:+.3f}", "near 0 (within +-0.04)", abs(m) < 0.04)
    tkl = [tk for tk in bars if len(bars[tk]) > 200]
    n = min(len(bars[tk]) for tk in tkl)
    mkt = [statistics.fmean(math.log(bars[tk][i][4] / bars[tk][i - 1][4]) / shape_r[int(bars[tk][i][0] % day // MIN)] for tk in tkl)
           for i in range(1, n)]
    pre_, post_ = e._session_lengths()
    t0 = [bars[tkl[0]][i][0] for i in range(1, n)]
    pairs = [(mkt[i], mkt[i - 1]) for i in range(1, len(mkt))
             if pre_ <= t0[i] % day < day - post_ and pre_ <= t0[i - 1] % day < day - post_]
    mm = corr([a for a, b in pairs], [b for a, b in pairs])
    row("Autocorrelation of returns, lag 1 (the market average, regular session)", f"{mm:+.3f}", "near 0 (within +-0.1)",
        abs(mm) < 0.1)
    # Volatility memory, pooled: every listing's |return| scaled by its stated volatility and the time of day, one mean for
    # all of them, so slow swings in volatility (game days, weeks) count; a per-listing mean over a few days hides them.
    zs = {}
    for tk, b in bars.items():
        st = e.stocks.get(tk)
        if st is None or len(b) < 200:
            continue
        sec = st.vol / math.sqrt(365 * day) * math.sqrt(MIN)
        zs[tk] = {b[i][0]: abs(math.log(b[i][4] / b[i - 1][4])) / shape_r[int(b[i][0] % day // MIN)] * statistics.fmean(shape_r.values()) / sec
                  for i in range(1, len(b)) if b[i - 1][4] > 0 and b[i][4] > 0}
    allz = sorted(x for d in zs.values() for x in d.values())
    cap = allz[int(len(allz) * 0.995)]                  # trim the most extreme 0.5% (a few huge minutes would dominate)
    zs = {tk: {t: min(x, cap) for t, x in d.items()} for tk, d in zs.items()}
    allz = [x for d in zs.values() for x in d.values()]
    gm = statistics.fmean(allz)
    den = sum((x - gm) ** 2 for x in allz)

    def pooled(lag):
        return sum((d[t] - gm) * (d[t - lag * MIN] - gm) for d in zs.values() for t in d if t - lag * MIN in d) / den
    m1, m10, m30 = pooled(1), pooled(10), pooled(30)
    row("Autocorrelation of |returns|, lag 1 / 10 / 30 min", f"{m1:.2f} / {m10:.2f} / {m30:.2f}",
        "clearly positive and decaying slowly (lag 30 still above 0.05)", m1 > 0.1 and m30 > 0.05)
    lm = statistics.fmean(lev)
    row("Leverage: return now vs volatility next 10 min", f"{lm:+.3f}", "negative (falls raise volatility)", lm < -0.02)
    if vcorr:
        vc = statistics.fmean(vcorr)
        row("Volume vs |return| (same minute)", f"{vc:+.2f}", "positive, about 0.3 to 0.6", 0.25 <= vc <= 0.7)
        v1, v10 = statistics.fmean(vacf1), statistics.fmean(vacf10)
        row("Autocorrelation of log volume, lag 1 / 10", f"{v1:.2f} / {v10:.2f}", "high and slow to decay (lag 10 above 0.3)",
            v1 > 0.5 and v10 > 0.3)

    # intraday profile: volatility by position in the regular session
    pre, post = e._session_lengths()
    prof = {}
    for tk, b in bars.items():
        for i in range(1, len(b)):
            ph = b[i][0] % day
            if ph < pre or ph >= day - post:
                continue
            k = int((ph - pre) / (day - pre - post) * 10)
            r = abs(math.log(b[i][4] / b[i - 1][4])) if b[i - 1][4] > 0 else 0.0
            prof.setdefault(k, []).append(r)
    if len(prof) >= 10:
        pv = [statistics.median(prof[k]) for k in range(10)]           # (medians: a few fat-tailed moves would dominate means)
        mid = statistics.fmean(pv[4:6])
        o, c = pv[0] / mid, pv[9] / mid
        row("Volatility at the open / the close vs midday", f"{o:.2f}x / {c:.2f}x", "U-shape: open 1.5-3x, close 1.1-2x",
            1.5 <= o <= 3.5 and 1.05 <= c <= 2.2)

    # game days: daily returns, correlation between stocks, down-day correlation
    daily = {}
    for tk, b in bars.items():
        closes = {}
        for c in b:
            closes[int(c[0] // day)] = c[4]
        ds = sorted(closes)
        daily[tk] = {d: math.log(closes[d] / closes[d - 1]) for d in ds if d - 1 in closes}
    dk = sorted(set.intersection(*[set(v) for v in daily.values() if v])) if daily else []
    if len(dk) >= 6:
        mat = [[daily[tk][d] for d in dk] for tk in daily if all(d in daily[tk] for d in dk)]
        pairs = [corr(mat[i], mat[j]) for i in range(0, len(mat), 3) for j in range(i + 1, len(mat), 3)]
        pc = statistics.fmean(pairs)
        row("Average correlation between stocks (game-day returns)", f"{pc:.2f}", "about 0.2 to 0.45", 0.15 <= pc <= 0.5)
    alld = [x for v in daily.values() for x in v.values()]
    if len(alld) > 100:
        # each listing scaled by its stated daily volatility (a dozen days per listing are too few for its own kurtosis)
        sds = {tk: e.stocks[tk].vol / math.sqrt(365) for tk in daily if tk in e.stocks}
        zd = [x / sds[tk] for tk, v in daily.items() if tk in sds and sds[tk] > 0 for x in v.values()]
        kd = kurt(zd)
        row("Kurtosis of game-day returns", f"{kd:.1f}", "about 4 to 10 (fatter than normal, less than intraday)", 3.5 <= kd <= 12)
    # opening gaps: the price after the opening jump against the previous regular close; filled if the session touches it
    small, big = [], []
    for tk, b in bars.items():
        s = e.stocks.get(tk)
        if s is None:
            continue
        dd = daily.get(tk, {})
        sig = statistics.pstdev(dd.values()) if len(dd) > 3 else s.vol / math.sqrt(365)   # its realised daily volatility
        byday = {}
        for c in b:
            ph = c[0] % day
            byday.setdefault(int(c[0] // day), []).append((ph, c))
        for d in sorted(byday):
            prev = byday.get(d - 1)
            if not prev:
                continue
            reg_prev = [c for ph, c in prev if pre <= ph < day - post]
            reg = [c for ph, c in byday[d] if pre <= ph < day - post]
            if not reg_prev or len(reg) < 5:
                continue
            pc, op = reg_prev[-1][4], reg[0][4]
            g = math.log(op / pc) / sig
            filled = any(c[3] <= pc <= c[2] for c in reg[1:])
            if 0.05 < abs(g) < 0.3:
                small.append(filled)
            elif abs(g) > 1.0:
                big.append(filled)
    if small:
        fs = sum(small) / len(small)
        fb = sum(big) / len(big) if big else float("nan")
        row("Opening gaps filled the same day: small / large", f"{fs:.0%} / {fb:.0%}" + f" (n {len(small)}/{len(big)})",
            "small gaps mostly fill (60-85%), large ones rarely (under 40%)", 0.55 <= fs <= 0.9 and (not big or fb < 0.45))
    # one-minute cross-correlation on down vs up minutes of the market
    mk = []
    tkl = [tk for tk in bars if len(bars[tk]) > 200]
    n = min(len(bars[tk]) for tk in tkl)
    for i in range(1, n):
        rs = [math.log(bars[tk][i][4] / bars[tk][i - 1][4]) for tk in tkl]
        mk.append(statistics.fmean(rs))
    # earnings-day moves against the same stock's ordinary game days
    ratios = []
    for tk, t in reports:
        dd = daily.get(tk, {})
        d = int(t // day)
        if d in dd and len(dd) > 4:
            usual = statistics.fmean(abs(x) for k, x in dd.items() if k != d)
            if usual > 0:
                ratios.append(abs(dd[d]) / usual)
    if len(ratios) >= 5:
        rr = statistics.fmean(ratios)
        row("Earnings day vs the stock's usual day (absolute move)", f"{rr:.1f}x (n {len(ratios)})",
            "about 2.5-4x", 2.0 <= rr <= 5.0)
    # price discreteness: are prices on a tick grid?
    on_tick = 0
    total = 0
    for tk, b in bars.items():
        for c in b[-50:]:
            p = c[4]
            if p >= 1:
                total += 1
                on_tick += abs(p * 100 - round(p * 100)) < 1e-6
    if total:
        row("Prices on a one-cent tick (prices above 1 MB)", f"{on_tick / total:.0%}", "100% (real prices move in ticks)", on_tick / total > 0.99)
    print()
    w = max(len(r[0]) for r in rows)
    for name, value, target, ok in rows:
        print(f"  {name:<{w}}  {value:<22} {ok:<4} target: {target}")
    return rows


def light(e):
    """What `report` needs from the engine, small enough to keep (for --cached)."""
    return Light({tk: types.SimpleNamespace(vol=s.vol) for tk, s in e.stocks.items()}, e._session_lengths())


class Light:
    def __init__(self, stocks, sessions):
        self.stocks, self.sessions = stocks, sessions

    def _session_lengths(self):
        return self.sessions


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    d = float(args[0]) if args else 8
    sd = int(args[1]) if len(args) > 1 else 7
    cache = f"sim_results/chart_check_{d:g}_{sd}.pickle"
    if "--cached" in sys.argv and os.path.exists(cache):
        with open(cache, "rb") as fh:
            e, bars, reports, start = pickle.load(fh)
    else:
        e, bars, reports, start = run(d, sd)
        e = light(e)
        os.makedirs("sim_results", exist_ok=True)
        with open(cache, "wb") as fh:
            pickle.dump((e, bars, reports, start), fh)
    report(e, bars, reports, start, d)
