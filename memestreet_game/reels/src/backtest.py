"""We tested it (the owner, 2026-11-12: "we tested [X] strategy, here's why it worked/didn't work"): one trading rule run by
this code on the newest candles of every listed Meme Street stock, with every number the reel may say.

  facts, charts = backtest.test(key, get, tickers)   for make_spec.gather() ("Strategy test")
  python3 src/backtest.py demo                       the self-check, no network
  python3 src/backtest.py [key ...]                  run tests (all of them without a key) against the live game

How a trade is counted, the same for every rule (no peeking at the future): a signal is read on a candle's close and the
trade opens at the NEXT candle's open; an exit signal closes at the next open; a stop or a target fills inside the candle
that touches it (the stop first when one candle touches both, at the open when the price gaps through it); a trade still
open at the end closes at the last close. Long only. Each trade pays the game's fee, 0.1% a side (game/engine.py FEE).
A candle is [open, high, low, close, volume]. Every chart is a stock's newest 120 candles on one timeframe (the game's
/api/reel/stock gives no more); the first 51 warm the indicators up, the rest are traded.
"""
import json, math, os, random, statistics, sys, time, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "state", "candles.json")
FEE, WARM, KEEP, ENOUGH = 0.001, 51, 3 * 3600, 30
TFS = {"1h": "1-hour", "15m": "15-minute", "5m": "5-minute"}

# key: (the strategy's name, the claim people repeat, the exact rules, the rule it is compared with or None)
TESTS = {
    "rsi_dip": ("Buying when the RSI drops under 30", "Oversold means it is about to bounce.",
                "Buy when the 14-candle RSI closes under 30. Sell when it closes back above 50.", None),
    "ma_cross": ("The moving average crossover", "Buy when the fast average crosses above the slow one.",
                 "Buy when the 20-candle average closes above the 50-candle average. Sell when it closes back below.", None),
    "three_red": ("Buying after three red candles", "Three red candles in a row: it is due a bounce.",
                  "Buy after three red candles in a row. Sell three candles later.", "three_green"),
    "tight_stop": ("A tight stop against a wide stop", "Keep your stop tight so your losses stay small.",
                   "Same entry for both: buy a close above the highest high of the last 20 candles. The tight stop: half an ATR "
                   "under that close, target 1 ATR above. Both aim for twice the risk.", "wide_stop"),
    "breakout": ("Buying the breakout", "A new high means more highs are coming.",
                 "Buy a close above the highest high of the last 20 candles. Sell a close under the lowest low of the last 10.", None),
    "coin_flip": ("Trading on a coin flip", "Any system beats trading at random.",
                  "Buy at random, about 1 candle in 8 (a fixed coin, so the test can be run again). Sell five candles later.", None),
    "bollinger": ("Buying under the lower Bollinger Band", "Price always comes back to the average.",
                  "Buy a close under the lower band (the 20-candle average minus 2 standard deviations). Sell a close back at "
                  "the average.", None),
    "chase_green": ("Chasing the big green candle", "It is flying: get in before it is gone.",
                    "Buy after a green candle whose body is over twice the average candle range (2 ATR). Sell three candles later.", "big_red"),
    "rsi_trend": ("RSI under 30, only in an uptrend", "Add a trend filter and buying the dip starts to work.",
                  "Buy when the RSI closes under 30 AND the close is above the 50-candle average. Sell when the RSI closes back "
                  "above 50.", "rsi_dip"),
    "breakout_2r": ("Risking 1 to make 2", "Aim for twice your risk and you can be wrong half the time.",
                    "Buy a close above the highest high of the last 20 candles. Stop 1 ATR under that close, target 2 ATR above it.", None),
    # (the owner, 2026-11-15: "more in depth lessons, e.g. quant stuff ... and indicator reels")
    "macd_cross": ("The MACD cross", "When the MACD crosses its signal line, the trend has turned.",
                   "Buy when the MACD line (the 12-candle EMA minus the 26-candle EMA) closes above its signal line (the MACD's own "
                   "9-candle EMA). Sell when it closes back below.", None),
    "stoch_dip": ("Buying when the stochastic drops under 20", "Under 20 it is oversold: buy.",
                  "Buy when the 14-candle stochastic closes under 20. Sell when it closes back above 50.", None),
    "ema_cross": ("The fast EMA cross", "The 9 and 21 EMAs catch the turn before the slow averages do.",
                  "Buy when the 9-candle EMA closes above the 21-candle EMA. Sell when it closes back below.", "ma_cross"),
    "rsi2": ("The two-candle RSI", "A two-candle RSI under 10 is a spring about to snap back.",
             "Buy when the 2-candle RSI closes under 10 AND the close is above the 50-candle average. Sell at the first close "
             "above the 5-candle average.", None),
    "overfit": ("Picking the settings that worked best", "Find the settings that made the most on past candles, then trade those.",
                "The moving average crossover (buy when the fast average closes above the slow one, sell when it closes back "
                "below) with 23 pairs of settings: a fast average of 3, 5, 8, 10, 13 or 20 candles against a slow one of 20, 30, "
                "40 or 50. Each chart's traded candles are cut in two halves. Every pair is run on the first half of every "
                "chart; the pair with the best average trade is kept and run on the second half, which it has never seen.", None),
    "luck": ("Traders with a coin", "Eight wins out of ten: that trader knows something.",
             "A coin decides every trade: buy at random, about 1 candle in 8, sell five candles later. The coin is run over "
             "every chart several times, each run its own flips, and its trades are dealt at random to the traders, 20 each: "
             "ten first trades and ten next trades. The best tenth after the first ten are followed through the next ten.", None),
}
OTHER = {"three_green": "The opposite rule: buy after three green candles in a row. Sell three candles later.",
         "wide_stop": "The wide stop: 2 ATR under the close, target 4 ATR above.",
         "big_red": "The opposite rule: buy after a red candle whose body is over 2 ATR. Sell three candles later.",
         "rsi_dip": "The same rule without the filter: " + TESTS["rsi_dip"][2],
         "ma_cross": "The slow cross: " + TESTS["ma_cross"][2]}
OVERLAY = {"ma_cross": ["sma20", "sma50"], "bollinger": ["sma20"], "rsi_trend": ["sma50"], "rsi2": ["sma50"]}
PAIRS = [(f, s) for f in (3, 5, 8, 10, 13, 20) for s in (20, 30, 40, 50) if f < s]   # the 23 settings of "overfit"
TERMS = {"RSI": "a 0 to 100 gauge of how one-sided the last 14 candles were; under 30 is called oversold",
         "EMA": "an exponential moving average: an average that counts the newest candles most",
         "MACD": "the gap between a fast and a slow EMA; its signal line is an average of that gap",
         "stochastic": "a 0 to 100 gauge of where the close sits between the lowest low and the highest high of the last 14 candles",
         "ATR": "average true range: the average size of a candle over the last 14",
         "average trade": "the result of a typical trade, wins and losses together (traders call it expectancy)",
         "noise band": "twice the standard error of the average trade: when the average sits inside it, luck alone could have "
                       "produced the result",
         "break-even win rate": "how often the rule must win, given the size of its wins and losses, to make nothing"}


def smas(x, n): return [None if i < n - 1 else sum(x[i - n + 1:i + 1]) / n for i in range(len(x))]


def rsis(c, n=14):
    """Wilder's RSI on closes (None until n changes are in)."""
    out, up, dn = [None] * len(c), 0.0, 0.0
    for i in range(1, len(c)):
        d = c[i] - c[i - 1]; u, w = max(d, 0), max(-d, 0)
        if i <= n: up += u / n; dn += w / n
        else: up = (up * (n - 1) + u) / n; dn = (dn * (n - 1) + w) / n
        if i >= n: out[i] = 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)
    return out


def atrs(C, n=14):
    return smas([C[0][1] - C[0][2]] + [max(C[i][1] - C[i][2], abs(C[i][1] - C[i - 1][3]), abs(C[i][2] - C[i - 1][3])) for i in range(1, len(C))], n)


def emas(x, n):
    """An exponential average, started from the simple average of the first n (None before that)."""
    out, e = [None] * len(x), None
    for i in range(n - 1, len(x)):
        e = sum(x[:n]) / n if e is None else x[i] * 2 / (n + 1) + e * (1 - 2 / (n + 1))
        out[i] = e
    return out


def macds(c):
    """-> (the MACD line: EMA 12 minus EMA 26, its signal line: the line's own EMA 9); both set from candle 33."""
    line = [None if s is None else f - s for f, s in zip(emas(c, 12), emas(c, 26))]
    return line, [None] * 25 + emas(line[25:], 9)


def stochs(C, n=14):
    """Where each close sits between the lowest low and the highest high of the last n candles, 0 to 100 (%K)."""
    out = [None] * len(C)
    for i in range(n - 1, len(C)):
        hi, lo = max(k[1] for k in C[i - n + 1:i + 1]), min(k[2] for k in C[i - n + 1:i + 1])
        out[i] = 50.0 if hi == lo else 100 * (C[i][3] - lo) / (hi - lo)
    return out


cross = lambda f, s: dict(enter=lambda i: f[i] > s[i] and f[i - 1] <= s[i - 1], leave=lambda i: f[i] < s[i])   # the fast line over the slow one
coin = lambda C, k=0: dict(enter=lambda i: random.Random(f"{i}:{C[i][3]}" + (f":{k}" if k else "")).random() < 0.125, hold=5)   # a fixed coin (`k`: another run of flips): the test runs the same again


def rules(C):
    """Every rule's signals on one chart: key -> the arguments of trades()."""
    c = [k[3] for k in C]; s20, s50, r, a = smas(c, 20), smas(c, 50), rsis(c), atrs(C)
    hh = lambda i, n: max(k[1] for k in C[i - n:i]); ll = lambda i, n: min(k[2] for k in C[i - n:i])
    red = lambda i: C[i][3] < C[i][0]; green = lambda i: C[i][3] > C[i][0]; body = lambda i: abs(C[i][3] - C[i][0])
    brk = lambda i: c[i] > hh(i, 20); dip = lambda i: r[i] < 30; back = lambda i: r[i] > 50
    st, r2, s5 = stochs(C), rsis(c, 2), smas(c, 5)
    return {
        "rsi_dip": dict(enter=dip, leave=back),
        "rsi_trend": dict(enter=lambda i: dip(i) and c[i] > s50[i], leave=back),
        "ma_cross": cross(s20, s50),
        "macd_cross": cross(*macds(c)),
        "ema_cross": cross(emas(c, 9), emas(c, 21)),
        "stoch_dip": dict(enter=lambda i: st[i] < 20, leave=lambda i: st[i] > 50),
        "rsi2": dict(enter=lambda i: r2[i] < 10 and c[i] > s50[i], leave=lambda i: c[i] > s5[i]),
        "breakout": dict(enter=brk, leave=lambda i: c[i] < ll(i, 10)),
        "breakout_2r": dict(enter=brk, stop=lambda i: c[i] - a[i], target=lambda i: c[i] + 2 * a[i]),
        "tight_stop": dict(enter=brk, stop=lambda i: c[i] - 0.5 * a[i], target=lambda i: c[i] + a[i]),
        "wide_stop": dict(enter=brk, stop=lambda i: c[i] - 2 * a[i], target=lambda i: c[i] + 4 * a[i]),
        "three_red": dict(enter=lambda i: red(i) and red(i - 1) and red(i - 2), hold=3),
        "three_green": dict(enter=lambda i: green(i) and green(i - 1) and green(i - 2), hold=3),
        "bollinger": dict(enter=lambda i: c[i] < s20[i] - 2 * statistics.pstdev(c[i - 19:i + 1]), leave=lambda i: c[i] >= s20[i]),
        "chase_green": dict(enter=lambda i: green(i) and body(i) > 2 * a[i - 1], hold=3),
        "big_red": dict(enter=lambda i: red(i) and body(i) > 2 * a[i - 1], hold=3),
        "coin_flip": coin(C),
    }


def trades(C, enter, leave=None, hold=None, stop=None, target=None, a=WARM, b=None):
    """-> [(entry candle, exit candle, entry price, exit price)] of one rule on one chart (the counting at the top of the file).
    `a`, `b`: only the candles a to b - 1 are traded (a half of the chart: the two demonstrations)."""
    out, i, n = [], a, b or len(C)
    while i < n - 1:
        if not enter(i): i += 1; continue
        e = i + 1; px = C[e][0]; sl = stop(i) if stop else None; tp = target(i) if target else None; x = xp = None
        for j in range(e, n):
            if sl is not None and C[j][2] <= sl: x, xp = j, min(sl, C[j][0]); break
            if tp is not None and C[j][1] >= tp: x, xp = j, max(tp, C[j][0]); break
            if j < n - 1 and ((hold and j - e + 1 >= hold) or (leave and leave(j))): x, xp = j + 1, C[j + 1][0]; break
        if x is None: x, xp = n - 1, C[n - 1][3]
        out.append((e, x, px, xp)); i = max(x, i + 1)
    return out


net = lambda t: t[3] * (1 - FEE) / (t[2] * (1 + FEE)) - 1          # a trade's result after the fee on both sides
pct = lambda x: round(100 * x, 2)


def summary(S, short=False):
    """The numbers of one rule over S = [(chart, its trades)], after fees unless a name says before."""
    T = [t for _, ts in S for t in ts]; r = [net(t) for t in T]; n = len(r)
    if not n: return {"trades": 0}
    w = [x for x in r if x > 0]; l = [x for x in r if x <= 0]
    m = {"trades": n, "win_rate_pct": round(100 * len(w) / n, 1), "average_trade_pct": pct(sum(r) / n)}
    if short: return m
    m.update(average_win_pct=pct(sum(w) / len(w)) if w else None, average_loss_pct=pct(sum(l) / len(l)) if l else None,
             average_trade_before_fees_pct=pct(sum(t[3] / t[2] - 1 for t in T) / n),
             noise_band_pct=pct(2 * statistics.stdev(r) / math.sqrt(n)) if n > 1 else None)
    if w and l: m["break_even_win_rate_pct"] = round(100 * -sum(l) / len(l) / (sum(w) / len(w) - sum(l) / len(l)), 1)
    return m


def verdict(m, beat, charts):
    if m["trades"] < ENOUGH: return "Too few trades to say anything."
    a, b = m["average_trade_pct"], m["noise_band_pct"]
    if abs(a) <= b:
        return f"No edge we can measure: the average trade was {a:+.2f}% after fees, inside the noise band of plus or minus {b:.2f}%."
    return (f"It {'made' if a > 0 else 'lost'} money in this sample: {a:+.2f}% a trade after fees, outside the noise band of plus or "
            f"minus {b:.2f}%." + (" It still did worse than simply holding on most charts." if a > 0 and beat * 2 < charts else ""))


def universe(get, tickers, tf, cache=CACHE):
    """[{ticker, name, candles}] for every listed stock on one timeframe, kept for 3 hours (144 polite calls otherwise)."""
    try: d = json.load(open(cache, encoding="utf-8"))
    except (OSError, ValueError): d = {}
    if time.time() - d.get("t", 0) > KEEP: d = {"t": time.time(), "tf": {}}
    if tf not in d["tf"]:
        out = []
        for t in tickers:
            try: st = get(f"/api/reel/stock/{t}?tf={tf}")
            except urllib.error.HTTPError as e:
                if e.code == 404: continue                 # (the content pack has companies the live game does not list)
                raise
            if len(st["candles"]) >= WARM + 40: out.append({"ticker": st["ticker"], "name": st["name"], "candles": st["candles"]})
        d["tf"][tf] = out
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        json.dump(d, open(cache + ".tmp", "w", encoding="utf-8")); os.replace(cache + ".tmp", cache)
    return d["tf"][tf]


def overfit(U):
    """The quant's first trap, on our own candles: the best of 23 settings on the first half of every chart, then the same
    setting on the second half. Pooled over all charts: one pair makes 0 or 1 trade on half a chart."""
    half = lambda C: (WARM + len(C)) // 2
    S1, S2 = {p: [] for p in PAIRS}, {p: [] for p in PAIRS}
    for ch in U:
        C = ch["candles"]; c = [k[3] for k in C]; av = {n: smas(c, n) for n in {n for p in PAIRS for n in p}}
        for p in PAIRS:
            g = cross(av[p[0]], av[p[1]])
            S1[p].append((ch, trades(C, a=WARM, b=half(C), **g))); S2[p].append((ch, trades(C, a=half(C), **g)))
    m1, m2 = {p: summary(S1[p]) for p in PAIRS}, {p: summary(S2[p]) for p in PAIRS}
    ok = [p for p in PAIRS if min(m1[p]["trades"], m2[p]["trades"]) >= ENOUGH] or [p for p in PAIRS if min(m1[p]["trades"], m2[p]["trades"]) > 1]
    if not ok: raise SystemExit("too few crossover trades to choose a setting from")
    avg = lambda m: m["average_trade_pct"]; name = lambda p: f"the {p[0]} and {p[1]} candle averages"
    best = max(ok, key=lambda p: avg(m1[p])); mean = lambda m: round(statistics.mean(avg(m[p]) for p in ok), 2); v = verdict(m2[best], 1, 1)
    return {"first_half": {"settings_tried": len(PAIRS), "settings_with_enough_trades_to_judge": len(ok), "best_setting": name(best),
                           "its_result": m1[best], "average_trade_of_all_settings_pct": mean(m1)},
            "second_half": {"the_same_setting": name(best), "its_result": m2[best],
                            "its_rank_among_the_settings": 1 + sum(avg(m2[q]) > avg(m2[best]) for q in ok), "of": len(ok),
                            "average_trade_of_all_settings_pct": mean(m2), "best_setting_there": name(max(ok, key=lambda p: avg(m2[p])))},
            "what_this_shows": "Choosing the best of many settings on past candles is called overfitting. The best setting's first-half "
                               "result is partly the luck of being picked; the second half is the honest number. The average of all "
                               "settings in each half shows what the market did to every crossover, picked or not.",
            "result_after_fees": m2[best],
            "verdict": f"The best of {len(PAIRS)} settings averaged {avg(m1[best]):+.2f}% a trade on the first half of every chart. On the "
                       f"second half, which it had never seen: {v[0].lower()}{v[1:]}"}


def luck(U, each=10, most=100):
    """Luck against skill, on our own candles: the coin's trades dealt to traders, `each` first trades and `each` next ones;
    the best tenth after the first are followed through the next."""
    T, runs = [], 0
    while len(T) < 2 * each * most and runs < 12:            # (one run of the coin makes about 3 trades a chart: more runs, each its own flips, until every trader has a hand)
        T += [t for ch in U for t in trades(ch["candles"], **coin(ch["candles"], runs))]; runs += 1
    random.Random(len(T)).shuffle(T)                         # (dealt at random, the same way every run)
    n = min(most, len(T) // (2 * each)); top = max(1, n // 10)
    if n < 2: raise SystemExit("too few coin trades to deal")
    hand = lambda k, h: T[(2 * k + h) * each:(2 * k + h + 1) * each]
    av = lambda k, h: sum(net(t) for t in hand(k, h)) / each
    best, later = (sorted(range(n), key=lambda k: -av(k, h))[:top] for h in (0, 1))
    s = lambda ks, h, short=True: dict(summary([({}, [t for k in ks for t in hand(k, h)])], short), traders=len(ks))
    a1, a2, b2 = s(best, 0), s(best, 1, False), s(range(n), 1)
    hot = [k for k in range(n) if sum(net(t) > 0 for t in hand(k, 0)) >= 8]
    return {"first_ten_trades": {"all_traders": s(range(n), 0), "the_best_tenth": a1,
                                 "traders_who_won_8_or_more_of_their_ten": dict({"traders": len(hot)}, **({"on_their_next_ten": s(hot, 1)} if hot else {})),
                                 "the_single_best_trader": {"wins": sum(net(t) > 0 for t in hand(best[0], 0)), "of": each, "average_trade_pct": pct(av(best[0], 0))}},
            "next_ten_trades": {"the_same_best_tenth": s(best, 1), "all_traders": b2,
                                "of_the_best_tenth_still_in_the_top_tenth": len(set(best) & set(later)), "chance_alone_predicts_about": round(top / 10, 1)},
            "what_this_shows": "A coin has no skill, so the best traders' lead after ten trades is luck and nothing else: on the next "
                               "ten they do about as well as everyone. Ten trades cannot tell a good trader from a lucky one.",
            "result_after_fees": {k: v for k, v in a2.items() if k != "traders"},
            "verdict": f"After ten trades each, the best tenth of {n} coin-flip traders had won {a1['win_rate_pct']:g}% of their trades and "
                       f"averaged {a1['average_trade_pct']:+.2f}% a trade. On their next ten trades the same traders won "
                       f"{a2['win_rate_pct']:g}% and averaged {a2['average_trade_pct']:+.2f}%, against {b2['average_trade_pct']:+.2f}% for all "
                       f"{n}. They flipped a coin, so the early lead could only be luck."}


def drawn(key, C):
    """What the reel's chart draws for an indicator beside the candles (src/reel.html drawChart): {"lines": [...]} on the price
    scale and/or {"panel": {...}} in a strip under them. One value a candle, None until the indicator has its candles."""
    c = [k[3] for k in C]; n = len(C)
    L = lambda name, v, col=None: dict({"name": name, "values": [None if x is None else round(x, 4 if abs(x) < 10 else 2) for x in v]}, **({"color": col} if col else {}))
    PAIR = "#c084fc"                                         # (a pair of edges shares one colour, apart from the orange and blue averages)
    gauge = lambda name, v, levels: {"panel": {"name": name, "lo": 0, "hi": 100, "levels": levels, "lines": [L(name.split()[0], v)]}}
    band = lambda k: [None if m is None else m + k * statistics.pstdev(c[i - 19:i + 1]) for i, m in enumerate(smas(c, 20))]
    edge = lambda f, col: [None] * 20 + [f(k[col] for k in C[i - 20:i]) for i in range(20, n)]
    return {"rsi": lambda: gauge("RSI 14", rsis(c), [30, 70]), "rsi2": lambda: gauge("RSI 2", rsis(c, 2), [10]),
            "stochastic": lambda: gauge("Stochastic 14", stochs(C), [20, 80]),
            "macd": lambda: {"panel": {"name": "MACD", "levels": [0], "lines": [L("MACD", macds(c)[0]), L("signal", macds(c)[1])]}},
            "atr": lambda: {"panel": {"name": "ATR 14", "lines": [L("ATR", atrs(C))]}},
            "ema": lambda: {"lines": [L("EMA 9", emas(c, 9)), L("EMA 21", emas(c, 21))]},
            "bollinger": lambda: {"lines": [L("upper", band(2), PAIR), L("lower", band(-2), PAIR)]},
            "range": lambda: {"lines": [L("20 high", edge(max, 1), PAIR), L("20 low", edge(min, 2), PAIR)]}}.get(key, dict)()


DRAW = {"rsi_dip": "rsi", "rsi_trend": "rsi", "rsi2": "rsi2", "stoch_dip": "stochastic", "macd_cross": "macd", "ema_cross": "ema",
        "bollinger": "bollinger", "breakout": "range", "breakout_2r": "range"}   # what a rule's example chart draws
DEMOS = {"overfit": overfit, "luck": luck}                   # demonstrations: two halves side by side, no single rule's result
COUNTED = ("A signal is read on a candle's close and the trade opens at the next candle's open. Buying only, no shorting. Every "
           "trade pays the game's fee, 0.1% a side. A stop or a target fills inside the candle that touches it, the stop first.")
LIMITS = ("A small sample from a game market with fictional stocks, a few days of candles: it shows how to test a rule and what "
          f"this one did here. It is no forecast for a real market. It is one of {len(TESTS)} tests we run, and by chance alone "
          "about one test in twenty lands outside its noise band.")


def test(key, get, tickers, cache=CACHE):
    """One rule on every chart -> (the facts the reel may say, [an example chart with real trades on it])."""
    name, claim, how, vs = TESTS[key]
    U = [dict(ch, tf=tf) for tf in TFS for ch in universe(get, tickers, tf, cache)]
    if len(U) < 20: raise SystemExit("too few charts to test a rule on")
    sample = lambda n: {"stocks": len({ch["ticker"] for ch in U}), "timeframes": list(TFS.values()), "charts": len(U),
                        "candles_per_chart": 120, "of_which_warm_up_for_the_indicators": WARM, "trades": n}
    if key in DEMOS:
        d = DEMOS[key](U)
        return dict({"strategy": name, "the_claim_people_repeat": claim, "the_exact_rules": how, "how_a_trade_is_counted": COUNTED,
                     "sample": sample(d["result_after_fees"]["trades"]), "terms": TERMS, "limits": LIMITS}, **d), []
    sig = [rules(ch["candles"]) for ch in U]
    run = lambda k: [(ch, trades(ch["candles"], **g[k])) for ch, g in zip(U, sig)]
    S = run(key); m = summary(S)
    comp = lambda ts: math.prod(1 + net(t) for t in ts) - 1
    hold = lambda C: C[-1][3] * (1 - FEE) / (C[WARM + 1][0] * (1 + FEE)) - 1
    rose = lambda C: C[-1][3] > C[WARM][3]
    eff = lambda C: abs(C[-1][3] - C[WARM][3]) / (sum(abs(C[i][3] - C[i - 1][3]) for i in range(WARM + 1, len(C))) or 1)
    beat = sum(comp(ts) > hold(ch["candles"]) for ch, ts in S)
    order = sorted(S, key=lambda s: eff(s[0]["candles"])); third = len(order) // 3
    facts = {
        "strategy": name, "the_claim_people_repeat": claim, "the_exact_rules": how,
        "how_a_trade_is_counted": COUNTED, "sample": sample(m["trades"]),
        "result_after_fees": m, "verdict": verdict(m, beat, len(U)),
        "against_buying_and_holding": {
            "note": "Per chart, over its traded candles: the rule's trades compounded, against buying at the first of them and "
                    "holding to the last. Fees paid in both.",
            "rule_average_pct_per_chart": pct(statistics.mean(comp(ts) for _, ts in S)),
            "holding_average_pct_per_chart": pct(statistics.mean(hold(ch["candles"]) for ch in U)),
            "charts_where_the_rule_beat_holding": beat, "charts": len(U),
            "share_of_the_time_in_a_trade_pct": round(100 * sum(t[1] - t[0] for _, ts in S for t in ts) / sum(len(ch["candles"]) - WARM - 1 for ch in U), 1)},
        "why": {"note": "Where the result came from. Use the two or three lines that explain it best.",
                "on_charts_that_ended_higher": summary([s for s in S if rose(s[0]["candles"])], True),
                "on_charts_that_ended_lower": summary([s for s in S if not rose(s[0]["candles"])], True),
                "on_the_choppiest_third_of_charts": summary(order[:third], True),
                "on_the_steadiest_trending_third": summary(order[-third:], True)},
        "on_each_timeframe": {TFS[tf]: summary([s for s in S if s[0]["tf"] == tf], True) for tf in TFS},
        "terms": TERMS, "limits": LIMITS,
    }
    if vs: facts["compared_with"] = {"rule": OTHER[vs], "result_after_fees": summary(run(vs))}
    p2 = lambda p: round(p, 4 if p < 1 else 2)
    both = lambda ts: any(net(t) > 0 for t in ts) and any(net(t) <= 0 for t in ts)
    ex = max((s for s in S if s[0]["tf"] == "1h" and s[1]), key=lambda s: (both(s[1]), len(s[1])), default=None)
    if ex is None: return facts, []
    ch, ts = ex; C = ch["candles"]
    facts["example_trades_on_chart_0"] = {
        "note": "Real trades of this rule on chart 0, at their candles. Show a win and a loss when both are here.",
        "trades": [{"buy_candle": t[0], "buy_price": p2(t[2]), "sell_candle": t[1], "sell_price": p2(t[3]), "result_pct": pct(net(t))} for t in ts[:6]]}
    return facts, [dict({"candles": C, "label": f"{ch['name']} ({ch['ticker']}) · 1-hour", "upto": len(C) - 1, "end": len(C) - 1,
                         "win": [WARM - 21, len(C) - 1], "overlay": OVERLAY.get(key, [])}, **drawn(DRAW.get(key), C))]


def demo():
    import tempfile
    C = [[10, 10.5, 9.5, 10, 1]] * 60 + [[10, 11, 10, 11, 1], [11, 12, 11, 12, 1], [12, 12.2, 9, 9.5, 1], [9.5, 10, 9, 10, 1], [10, 10, 10, 10, 1]]
    one = lambda i: i == 59
    assert trades(C, one, hold=2) == [(60, 62, 10, 12)]                                        # (in at the next open, out at an open)
    assert trades(C, one, stop=lambda i: 9.8, target=lambda i: 99) == [(60, 62, 10, 9.8)]      # (the stop fills inside candle 62)
    assert trades(C, one, stop=lambda i: 9.8, target=lambda i: 11.5) == [(60, 61, 10, 11.5)]   # (the target came first)
    assert trades(C, one, stop=lambda i: 12.5, target=lambda i: 99) == [(60, 60, 10, 10)]      # (a gap through the stop: the open)
    assert trades(C, one, leave=lambda i: False) == [(60, 64, 10, 10)]                         # (still open at the end: the last close)
    assert abs(net((0, 0, 100, 110)) - (110 * .999 / 100.1 - 1)) < 1e-12
    assert rsis([float(k) for k in range(1, 40)])[-1] == 100 and smas([1, 2, 3, 4], 2) == [None, 1.5, 2.5, 3.5]
    assert emas([1, 2, 3, 4, 5], 3) == [None, None, 2, 3, 4] and stochs([[1, 2, 0, 1, 1]] * 13 + [[1, 4, 1, 3, 1]])[-1] == 75 and len(PAIRS) == 23
    ln, sg = macds([float(k) for k in range(60)]); assert ln[24] is None and sg[32] is None and abs(ln[-1] - 7) < 1e-9 and abs(sg[-1] - 7) < 1e-9   # (a straight line: the EMAs trail it by 5.5 and 12.5)
    assert trades(C, one, leave=lambda i: False, b=62) == [(60, 61, 10, 12)] and trades(C, one, hold=2, a=60) == []   # (half a chart: closed at its last close; a signal before it is not seen)
    d = drawn("rsi", C)["panel"]; assert d["levels"] == [30, 70] and len(d["lines"][0]["values"]) == len(C) and d["lines"][0]["values"][13] is None
    assert [len(x["values"]) for x in drawn("bollinger", C)["lines"]] == [len(C)] * 2 and drawn(None, C) == {} and all(drawn(k, C) for k in set(DRAW.values()) | {"atr"})
    assert drawn("range", C)["lines"][0]["values"][62] == 12 and drawn("ema", C)["lines"][0]["name"] == "EMA 9"   # (the high of the 20 candles before candle 62)
    m = summary([({}, [(0, 1, 100, 110), (2, 3, 100, 95), (4, 5, 100, 95)])])
    assert m["trades"] == 3 and m["win_rate_pct"] == 33.3 and m["average_trade_before_fees_pct"] == 0.0 and m["average_trade_pct"] < 0
    assert verdict({"trades": 5}, 0, 9).startswith("Too few") and "No edge" in verdict({"trades": 99, "average_trade_pct": -.1, "noise_band_pct": .3}, 0, 9)
    assert "lost money" in verdict({"trades": 99, "average_trade_pct": -.5, "noise_band_pct": .3}, 0, 9)
    assert verdict({"trades": 99, "average_trade_pct": .5, "noise_band_pct": .3}, 2, 9).endswith("on most charts.")
    rng = random.Random(7)

    def fake(path):                                         # a made-up game: 12 random walks and one stock that is not listed
        tk = path.split("/")[4].split("?")[0]
        if tk == "GONE": raise urllib.error.HTTPError(path, 404, "x", None, None)
        p, cs = 50.0, []
        for _ in range(120):
            o = p; p = max(1, p * (1 + rng.gauss(0, 0.012))); cs.append([o, max(o, p) * 1.003, min(o, p) * 0.997, p, 100])
        return {"ticker": tk, "name": tk + " Corp", "candles": cs}
    with tempfile.TemporaryDirectory() as d:
        for key in TESTS:
            f, ch = test(key, fake, [f"T{k}" for k in range(12)] + ["GONE"], os.path.join(d, "c.json"))
            json.dumps(f); m = f["result_after_fees"]
            assert f["sample"]["stocks"] == 12 and f["sample"]["charts"] == 36 and f["sample"]["trades"] == m["trades"] and f["verdict"], f
            assert (TESTS[key][3] is None) == ("compared_with" not in f) and len(ch) <= 1 and set(OTHER) | set(TESTS) - set(DEMOS) == set(rules(C)), key
            if key == "overfit":                            # (the pick is the best of its half, and has a place in the other)
                a, b = f["first_half"], f["second_half"]
                assert a["settings_tried"] == 23 and a["its_result"]["average_trade_pct"] >= a["average_trade_of_all_settings_pct"] and 1 <= b["its_rank_among_the_settings"] <= b["of"], f
            if key == "luck":                               # (the best tenth led after ten trades; every trader was dealt twenty)
                a, b = f["first_ten_trades"], f["next_ten_trades"]
                assert a["the_best_tenth"]["average_trade_pct"] >= a["all_traders"]["average_trade_pct"] and a["all_traders"]["trades"] == b["all_traders"]["trades"] == 10 * a["all_traders"]["traders"], f
            assert all(60 > t["sell_candle"] - t["buy_candle"] >= 0 and t["buy_candle"] > WARM for t in f.get("example_trades_on_chart_0", {}).get("trades", []))
    print("ok")


if __name__ == "__main__":
    if "demo" in sys.argv[1:]: demo()
    else:
        import make_spec
        tk = [c["ticker"] for c in json.load(open(make_spec.PACK, encoding="utf-8"))["companies"]]
        for key in sys.argv[1:] or TESTS:
            f, _ = test(key, make_spec.get, tk); m = f["result_after_fees"]
            print(f"{key:12} {m['trades']:4} trades  win {m.get('win_rate_pct')}%  avg {m.get('average_trade_pct')}%  | {f['verdict']}")
