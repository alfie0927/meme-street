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
}
OTHER = {"three_green": "The opposite rule: buy after three green candles in a row. Sell three candles later.",
         "wide_stop": "The wide stop: 2 ATR under the close, target 4 ATR above.",
         "big_red": "The opposite rule: buy after a red candle whose body is over 2 ATR. Sell three candles later.",
         "rsi_dip": "The same rule without the filter: " + TESTS["rsi_dip"][2]}
OVERLAY = {"ma_cross": ["sma20", "sma50"], "bollinger": ["sma20"], "rsi_trend": ["sma50"]}
TERMS = {"RSI": "a 0 to 100 gauge of how one-sided the last 14 candles were; under 30 is called oversold",
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


def rules(C):
    """Every rule's signals on one chart: key -> the arguments of trades()."""
    c = [k[3] for k in C]; s20, s50, r, a = smas(c, 20), smas(c, 50), rsis(c), atrs(C)
    hh = lambda i, n: max(k[1] for k in C[i - n:i]); ll = lambda i, n: min(k[2] for k in C[i - n:i])
    red = lambda i: C[i][3] < C[i][0]; green = lambda i: C[i][3] > C[i][0]; body = lambda i: abs(C[i][3] - C[i][0])
    brk = lambda i: c[i] > hh(i, 20); dip = lambda i: r[i] < 30; back = lambda i: r[i] > 50
    return {
        "rsi_dip": dict(enter=dip, leave=back),
        "rsi_trend": dict(enter=lambda i: dip(i) and c[i] > s50[i], leave=back),
        "ma_cross": dict(enter=lambda i: s20[i] > s50[i] and s20[i - 1] <= s50[i - 1], leave=lambda i: s20[i] < s50[i]),
        "breakout": dict(enter=brk, leave=lambda i: c[i] < ll(i, 10)),
        "breakout_2r": dict(enter=brk, stop=lambda i: c[i] - a[i], target=lambda i: c[i] + 2 * a[i]),
        "tight_stop": dict(enter=brk, stop=lambda i: c[i] - 0.5 * a[i], target=lambda i: c[i] + a[i]),
        "wide_stop": dict(enter=brk, stop=lambda i: c[i] - 2 * a[i], target=lambda i: c[i] + 4 * a[i]),
        "three_red": dict(enter=lambda i: red(i) and red(i - 1) and red(i - 2), hold=3),
        "three_green": dict(enter=lambda i: green(i) and green(i - 1) and green(i - 2), hold=3),
        "bollinger": dict(enter=lambda i: c[i] < s20[i] - 2 * statistics.pstdev(c[i - 19:i + 1]), leave=lambda i: c[i] >= s20[i]),
        "chase_green": dict(enter=lambda i: green(i) and body(i) > 2 * a[i - 1], hold=3),
        "big_red": dict(enter=lambda i: red(i) and body(i) > 2 * a[i - 1], hold=3),
        "coin_flip": dict(enter=lambda i: random.Random(f"{i}:{C[i][3]}").random() < 0.125, hold=5),
    }


def trades(C, enter, leave=None, hold=None, stop=None, target=None):
    """-> [(entry candle, exit candle, entry price, exit price)] of one rule on one chart (the counting at the top of the file)."""
    out, i, n = [], WARM, len(C)
    while i < n - 1:
        if not enter(i): i += 1; continue
        e = i + 1; px = C[e][0]; sl = stop(i) if stop else None; tp = target(i) if target else None; x = xp = None
        for j in range(e, n):
            if sl is not None and C[j][2] <= sl: x, xp = j, min(sl, C[j][0]); break
            if tp is not None and C[j][1] >= tp: x, xp = j, max(tp, C[j][0]); break
            if j < n - 1 and ((hold and j - e + 1 >= hold) or (leave and leave(j))): x, xp = j + 1, C[j + 1][0]; break
        if x is None: x, xp = n - 1, C[-1][3]
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


def test(key, get, tickers, cache=CACHE):
    """One rule on every chart -> (the facts the reel may say, [an example chart with real trades on it])."""
    name, claim, how, vs = TESTS[key]
    U = [dict(ch, tf=tf) for tf in TFS for ch in universe(get, tickers, tf, cache)]
    if len(U) < 20: raise SystemExit("too few charts to test a rule on")
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
        "how_a_trade_is_counted": "A signal is read on a candle's close and the trade opens at the next candle's open. Buying only, "
                                  "no shorting. Every trade pays the game's fee, 0.1% a side. A stop or a target fills inside the "
                                  "candle that touches it, the stop first.",
        "sample": {"stocks": len({ch["ticker"] for ch in U}), "timeframes": list(TFS.values()), "charts": len(U),
                   "candles_per_chart": 120, "of_which_warm_up_for_the_indicators": WARM, "trades": m["trades"]},
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
        "terms": TERMS,
        "limits": "A small sample from a game market with fictional stocks, a few days of candles: it shows how to test a rule and "
                  "what this one did here. It is no forecast for a real market.",
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
    return facts, [{"candles": C, "label": f"{ch['name']} ({ch['ticker']}) · 1-hour", "upto": len(C) - 1, "end": len(C) - 1,
                    "win": [WARM - 21, len(C) - 1], "overlay": OVERLAY.get(key, [])}]


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
            assert (TESTS[key][3] is None) == ("compared_with" not in f) and len(ch) <= 1 and set(OTHER) | set(TESTS) == set(rules(C)), key
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
