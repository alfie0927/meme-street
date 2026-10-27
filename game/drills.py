"""Chart tests for the Learn page (ROADMAP TA-C2, TA-C3): a real game chart stopped at a moment worth asking about, a
question with a few answers, and then the candles that came next.

`make(kind, candles, rng)` looks through `candles` (oldest first, each [open, high, low, close, volume]) for one
moment of that kind and returns a test, or None when there is none. Everything is read from the candles alone, as a
trader would read them, and the right answer is what the candles did next (or, for a question about what the chart
shows, what it shows): never what the price model meant to do.

A test is a dict:
    kind, q (the question), options, answer (an index into options)
    upto       the last candle shown with the question (the candles after it are the answer)
    show       how many candles after `upto` the answer reveals
    lines      [{"price", "label", "tone", "from", "after"}]: levels, stops and targets drawn on the chart; tone is
               level, stop, target, entry or trigger; "after" lines are drawn only with the answer
    marks      [{"i", "price", "label", "after"}]: labelled points (swing highs and lows, a candle to look at)
    overlay    moving averages to draw, e.g. ["sma20", "sma50"]; panel: "rsi" for an RSI panel
    result     what happened, in words (shown with the answer); explain: the idea behind the question
Tests come out roughly half and half where there are two outcomes, so always answering the same way scores 50%.
"""
import math
import statistics

import patterns

KINDS = ("level", "trend", "pattern", "breakout", "candle", "rsi", "ma", "fib", "rr", "stop", "next")
TITLES = {"level": "Bounce or break?", "trend": "Read the trend", "pattern": "Name the pattern",
          "breakout": "Real or fake breakout?", "candle": "Name the candle", "rsi": "Read the RSI",
          "ma": "Moving-average cross", "fib": "Fibonacci pullback", "rr": "Reward to risk",
          "stop": "Where does the stop go?", "next": "Up or down next?"}
ABOUT = {"level": "The price is back at support or resistance: does it hold?",
         "trend": "Up, down or sideways, from the swing highs and lows.",
         "pattern": "Double tops, head and shoulders, flags, triangles, wedges...",
         "breakout": "A close beyond the recent range: does it run or fail?",
         "candle": "Doji, hammer, shooting star, engulfing, marubozu.",
         "rsi": "Overbought, oversold or neither, and what came next.",
         "ma": "Golden cross, death cross, or nothing.",
         "fib": "How much of a swing a pullback gave back.",
         "rr": "Read the stop and the target: what is the trade's reward to risk?",
         "stop": "Where a stop-loss belongs, and what each choice would have done.",
         "next": "Call the next ten candles, and see why nobody can."}
PATTERN_NAMES = {"double_top": "Double top", "double_bottom": "Double bottom", "head_shoulders": "Head and shoulders",
                 "inverse_head_shoulders": "Inverse head and shoulders", "ascending_triangle": "Ascending triangle",
                 "descending_triangle": "Descending triangle", "symmetric_triangle": "Symmetric triangle",
                 "bull_flag": "Bull flag", "bear_flag": "Bear flag", "rising_wedge": "Rising wedge",
                 "falling_wedge": "Falling wedge", "up_channel": "Rising channel", "down_channel": "Falling channel",
                 "cup_handle": "Cup and handle"}
MIRROR = {"double_top": "double_bottom", "head_shoulders": "inverse_head_shoulders",
          "ascending_triangle": "descending_triangle", "bull_flag": "bear_flag", "rising_wedge": "falling_wedge",
          "up_channel": "down_channel"}
MIRROR.update({v: k for k, v in list(MIRROR.items())})
LOOK = 60          # candles shown before the moment, at least
AFTER = 25         # candles the answer reveals


# ---------------------------------------------------------------------------------------------------- measures
def true_ranges(c):
    return [c[0][1] - c[0][2]] + [max(c[i][1], c[i - 1][3]) - min(c[i][2], c[i - 1][3]) for i in range(1, len(c))]


def atr_series(c, n=14):
    tr, out, s = true_ranges(c), [], 0.0
    for i, x in enumerate(tr):
        s += x - (tr[i - n] if i >= n else 0.0)
        out.append(s / min(i + 1, n))
    return out


def sma(v, n):
    out, s = [None] * len(v), 0.0
    for i, x in enumerate(v):
        s += x - (v[i - n] if i >= n else 0.0)
        if i >= n - 1:
            out[i] = s / n
    return out


def rsi(v, n=14):
    """Wilder's RSI, as the chart draws it (chart.js rsiOf)."""
    out, g, l_ = [None] * len(v), 0.0, 0.0
    for i in range(1, len(v)):
        d = v[i] - v[i - 1]
        up, dn = max(d, 0.0), max(-d, 0.0)
        if i <= n:
            g, l_ = g + up / n, l_ + dn / n
            if i == n:
                out[i] = 100 - 100 / (1 + g / l_) if l_ else 100.0
        else:
            g, l_ = (g * (n - 1) + up) / n, (l_ * (n - 1) + dn) / n
            out[i] = 100 - 100 / (1 + g / l_) if l_ else 100.0
    return out


def unit(c):
    """A typical candle's range as a share of the price: the yardstick every test sizes things by."""
    return statistics.median((x[1] - x[2]) / x[3] for x in c if x[3] > 0) or 0.001


def pct(x):
    return f"{x * 100:+.1f}%"


def _test(kind, q, options, answer, upto, **kw):
    t = {"kind": kind, "title": TITLES[kind], "q": q, "options": options, "answer": answer, "upto": upto,
         "show": AFTER, "lines": [], "marks": [], "overlay": [], "panel": None, "result": "", "explain": ""}
    t.update(kw)
    return t


def _shuffled(rng, right, wrong):
    """The options in a random order, and where the right one ended up."""
    opts = [right] + list(wrong)
    rng.shuffle(opts)
    return opts, opts.index(right)


def _pick(rng, found_by_outcome):
    """Half and half: choose the outcome first, then a moment that had it (the other one if there is none)."""
    keys = sorted(k for k, v in found_by_outcome.items() if v)
    if not keys:
        return None, None
    k = rng.choice(keys)
    return k, rng.choice(found_by_outcome[k])


# ---------------------------------------------------------------------------------------------------- the kinds
def _level(c, rng, only=None):
    """A price comes back to a swing high or low: does the level hold or break? Read from the closes that follow:
    held = the price moves one ATR away on its own side first; broke = it closes one ATR through and does not come
    back within the candles shown. A break that came back (a fake break) is left out: the question would be unfair."""
    n, u = len(c), unit(c)
    atr = atr_series(c)
    piv = patterns.zigzag(c, 3 * u)
    found = {"held": [], "broke": []}
    for i in range(LOOK, n - AFTER):
        cl, prev = c[i][3], c[i - 1][3]
        for idx, lp, kind, conf in piv:
            if conf > i - 3 or idx < i - 150 or idx < 5:
                continue
            lv, side = math.exp(lp), -kind                          # a swing low is support (+1), a high resistance
            if only and side != only:
                continue
            band, th = 0.35 * atr[i], 1.0 * atr[i]
            if not ((prev - lv) * side > band and abs(cl - lv) <= band):
                continue
            if any((x[3] - lv) * side < -band for x in c[idx + 1:i]):
                continue                                             # it was already broken once: not a clean level
            out = None
            for j in range(i + 1, min(n, i + AFTER)):
                d = (c[j][3] - lv) * side
                if d > th:
                    out = "held"
                    break
                if d < -th:
                    back = any((x[3] - lv) * side > 0 for x in c[j + 1:i + AFTER])
                    out = None if back else "broke"
                    break
            if out:
                found[out].append((i, lv, side, idx))
    out, hit = _pick(rng, found)
    if not hit:
        return None
    i, lv, side, idx = hit
    name = "support" if side > 0 else "resistance"
    opts = [f"It holds: the price turns {'up' if side > 0 else 'down'} from the {name}",
            f"It breaks: the price closes through the {name} and keeps going"]
    move = c[min(n - 1, i + AFTER - 1)][3] / c[i][3] - 1
    res = (f"It held: the price turned away from the {name}." if out == "held" else
           f"It broke: the price closed through the {name} and stayed through it.") + f" {AFTER} candles later it was {pct(move)} from here."
    return _test("level", f"The price is back at a {name} level. Does the level hold or break?", opts,
                 0 if out == "held" else 1, i,
                 lines=[{"price": lv, "label": name.capitalize(), "tone": "level", "from": idx, "after": False}],
                 marks=[{"i": idx, "price": lv, "label": "Swing " + ("low" if side > 0 else "high"), "after": False}],
                 result=res,
                 explain="Levels hold often enough to trade and break often enough that every trade needs a stop. "
                         "Before the test, a trader looks at how many times the level has turned the price, which way the "
                         "trend runs, and whether volume grows into the level (a break is likelier) or dries up.")


def _trend(c, rng):
    """Up, down or sideways, from the last swing points: higher highs and higher lows, lower highs and lower lows,
    or highs and lows that stay level."""
    n, u = len(c), unit(c)
    piv = patterns.zigzag(c, 3 * u)
    found = {"up": [], "down": [], "side": []}
    for i in range(LOOK + 20, n - 10, 3):
        pts = [p for p in piv if p[3] <= i and p[0] >= i - 120]
        if len(pts) < 4:
            continue
        hs = [p for p in pts if p[2] == 1][-2:]
        ls = [p for p in pts if p[2] == -1][-2:]
        if len(hs) < 2 or len(ls) < 2:
            continue
        dh, dl = hs[1][1] - hs[0][1], ls[1][1] - ls[0][1]
        ok_up, ok_dn = c[i][3] > math.exp(ls[1][1]), c[i][3] < math.exp(hs[1][1])
        if dh > 1.5 * u and dl > 1.5 * u and ok_up:
            found["up"].append((i, pts[-4:]))
        elif dh < -1.5 * u and dl < -1.5 * u and ok_dn:
            found["down"].append((i, pts[-4:]))
        elif abs(dh) < 0.6 * u and abs(dl) < 0.6 * u and ok_up and ok_dn:
            found["side"].append((i, pts[-4:]))
    out, hit = _pick(rng, found)
    if not hit:
        return None
    i, pts = hit
    labels = {"up": "An uptrend", "down": "A downtrend", "side": "Sideways: a range"}
    marks = []
    hs = [p for p in pts if p[2] == 1]
    ls = [p for p in pts if p[2] == -1]
    for group, hi in ((hs, True), (ls, False)):
        for k, p in enumerate(group):
            if k == 0:
                word = "High" if hi else "Low"
            else:
                d = p[1] - group[k - 1][1]
                word = ("Higher high" if d > 0 else "Lower high") if hi else ("Higher low" if d > 0 else "Lower low")
            marks.append({"i": p[0], "price": math.exp(p[1]), "label": word, "after": True})
    move = c[min(n - 1, i + AFTER - 1)][3] / c[i][3] - 1
    return _test("trend", "Look at the swing highs and lows. What is this chart doing?", list(labels.values()),
                 list(labels).index(out), i, marks=marks,
                 result=f"{labels[out]}: the labels show the swing points it is read from. Over the next {AFTER} candles "
                        f"the price went {pct(move)}.",
                 explain="An uptrend makes higher highs and higher lows; a downtrend lower highs and lower lows; a range "
                         "makes highs and lows at about the same prices. A trend is only a trend until it stops: the "
                         "first lower low in an uptrend is the first warning.")


def _pattern(c, rng):
    n, u = len(c), unit(c)
    pool = []
    for swing in (3 * u, 5 * u):
        for p in patterns.find(c, swing):
            if LOOK <= p["at"] < n - AFTER and p["at"] - p["start"] <= 120:
                o = patterns.outcome(c, p, wait=10, hold=AFTER - 10)
                if o is not None:
                    pool.append((p, o, swing))
    if not pool:
        return None
    by = {}
    for x in pool:
        by.setdefault(x[0]["kind"], []).append(x)
    p, o, swing = rng.choice(by[rng.choice(sorted(by))])          # every kind as likely, however common
    right = PATTERN_NAMES[p["kind"]]
    others = [k for k in PATTERN_NAMES if k != p["kind"]]
    wrong = [PATTERN_NAMES[MIRROR[p["kind"]]]] if p["kind"] in MIRROR else []
    rng.shuffle(others)
    wrong += [PATTERN_NAMES[k] for k in others if PATTERN_NAMES[k] not in wrong][:3 - len(wrong)]
    opts, ans = _shuffled(rng, right, wrong)
    pts = [q for q in patterns.zigzag(c, swing) if p["start"] <= q[0] <= p["at"]]
    d = "up" if p["dir"] > 0 else "down"
    if o.get("completed"):
        res = (f"It completed (a close {'above' if p['dir'] > 0 else 'below'} the trigger) and "
               + ("reached its measured move." if o["worked"] else "then failed before its measured move."))
    else:
        res = ("It never broke out: the price closed past the other side first." if o.get("broke_other_way")
               else "It never broke out within 10 candles: it was only a pause.")
    return _test("pattern", "Which pattern has the chart just finished drawing?", opts, ans, p["at"],
                 marks=[{"i": q[0], "price": math.exp(q[1]), "label": "", "after": True} for q in pts],
                 lines=[{"price": p["trigger"], "label": "Trigger", "tone": "trigger", "from": p["start"], "after": True},
                        {"price": p["invalid"], "label": "Wrong if closed past", "tone": "stop", "from": p["start"], "after": True},
                        {"price": p["target"], "label": "Measured move", "tone": "target", "from": p["at"], "after": True}],
                 result=f"{'An' if right[0] in 'AEIOU' else 'A'} {right.lower()}, which points {d}. {res}",
                 explain="A pattern is only complete when a close breaks its trigger (the neckline, the flag's edge, the "
                         "triangle's side). Until then it can still fail; the measured move (the pattern's height added "
                         "to the trigger) is a common first target, and the other side of the pattern is where the idea "
                         "is wrong.")


def _breakout(c, rng):
    """The first close above the last 20 candles' high (or below their low): does it keep going, or fall back?"""
    n = len(c)
    atr = atr_series(c)
    vol_avg = sma([x[4] for x in c], 20)
    found = {"real": [], "fake": []}
    for i in range(LOOK, n - AFTER):
        hh, ll = max(x[1] for x in c[i - 20:i]), min(x[2] for x in c[i - 20:i])
        for d, lv in ((1, hh), (-1, ll)):
            if not ((c[i][3] - lv) * d > 0 and (c[i - 1][3] - lv) * d <= 0):
                continue
            nxt = c[i + 1:i + 1 + 8]
            back = any((x[3] - lv) * d < 0 for x in nxt[:6])
            ran = max((x[3] - c[i][3]) * d for x in nxt) > 1.0 * atr[i]
            if back and not ran:
                found["fake"].append((i, d, lv))
            elif ran and not back:
                found["real"].append((i, d, lv))
    out, hit = _pick(rng, found)
    if not hit:
        return None
    i, d, lv = hit
    va = vol_avg[i - 1] or 1.0
    vr = c[i][4] / va if va else 1.0
    word = "high" if d > 0 else "low"
    vol = f"The breakout candle's volume was {vr:.1f} times the 20-candle average"
    vol += (": strong volume, and a real breakout." if out == "real" and vr >= 1.3 else
            ": strong volume did not save it." if vr >= 1.3 else
            ": weak volume, and it failed." if out == "fake" else ": weak volume, and it worked anyway.")
    return _test("breakout", f"The price has just closed beyond the last 20 candles' {word}. Real breakout or fake?",
                 ["Real: it keeps going", "Fake: it falls back inside the range"], 0 if out == "real" else 1, i,
                 lines=[{"price": lv, "label": f"20-candle {word}", "tone": "trigger", "from": i - 20, "after": False}],
                 result=("It was real: the price ran on and never closed back inside." if out == "real" else
                         "It was fake: the price closed back inside the range within six candles.") + " " + vol,
                 explain="Breakouts fail often. Traders look for volume that grows on the break, a close (not just a "
                         "wick) beyond the level, and a retest that holds; a stop just inside the old range limits the "
                         "damage of a fake one.")


CANDLES = {"doji": "Doji", "hammer": "Hammer", "shooting_star": "Shooting star", "bull_engulf": "Bullish engulfing",
           "bear_engulf": "Bearish engulfing", "marubozu": "Marubozu"}
CANDLE_WHY = {"doji": "a doji: open and close almost the same, so buyers and sellers ended even",
              "hammer": "a hammer: a long lower wick, at least twice the body, after a fall: sellers pushed it down and "
                        "buyers pushed it back",
              "shooting_star": "a shooting star: a long upper wick after a rise: buyers pushed it up and sellers "
                               "pushed it back",
              "bull_engulf": "a bullish engulfing candle: a green body that covers the whole red body before it",
              "bear_engulf": "a bearish engulfing candle: a red body that covers the whole green body before it",
              "marubozu": "a marubozu: a big body with almost no wicks, one side in control from open to close"}


def candle_kind(c, i, atr):
    """What shape candle i is, or None. Checked in order, so a candle has one name."""
    o, h, l_, cl = c[i][:4]
    rng_, body = h - l_, abs(cl - o)
    if rng_ <= 0 or rng_ < 0.6 * atr[i]:
        return None
    up_w, lo_w = h - max(o, cl), min(o, cl) - l_
    po, pc = c[i - 1][0], c[i - 1][3]
    trend = c[i - 1][3] - c[i - 6][3]
    if body >= 0.9 * rng_ and rng_ >= 1.3 * atr[i]:
        return "marubozu"
    if body <= 0.08 * rng_:
        return "doji"
    if lo_w >= 2 * body and up_w <= 0.4 * body and trend < -atr[i]:
        return "hammer"
    if up_w >= 2 * body and lo_w <= 0.4 * body and trend > atr[i]:
        return "shooting_star"
    if abs(pc - po) >= 0.4 * atr[i] and body >= 0.6 * rng_:
        if pc < po and cl > o and cl >= po and o <= pc:
            return "bull_engulf"
        if pc > po and cl < o and cl <= po and o >= pc:
            return "bear_engulf"
    return None


def _candle(c, rng):
    n = len(c)
    atr = atr_series(c)
    by = {}
    for i in range(LOOK, n - AFTER):
        k = candle_kind(c, i, atr)
        if k:
            by.setdefault(k, []).append(i)
    if not by:
        return None
    k = rng.choice(sorted(by))
    i = rng.choice(by[k])
    others = [CANDLES[x] for x in CANDLES if x != k]
    rng.shuffle(others)
    opts, ans = _shuffled(rng, CANDLES[k], others[:3])
    move = c[min(n - 1, i + 10)][3] / c[i][3] - 1
    return _test("candle", "What is the candle under the arrow called?", opts, ans, i, show=12,
                 marks=[{"i": i, "price": c[i][1], "label": "This one", "after": False}],
                 result=f"It is {CANDLE_WHY[k]}. Ten candles later the price was {pct(move)} from its close.",
                 explain="A single candle says who won one stretch of time. It means most at a level that matters and "
                         "with volume; on its own, in the middle of nowhere, it predicts little.")


def _rsi(c, rng):
    n = len(c)
    r = rsi([x[3] for x in c])
    found = {"over": [], "under": [], "mid": []}
    for i in range(LOOK, n - AFTER):
        if r[i] is None:
            continue
        if r[i] >= 72:
            found["over"].append(i)
        elif r[i] <= 28:
            found["under"].append(i)
        elif 45 <= r[i] <= 55:
            found["mid"].append(i)
    if not any(found.values()):
        return None
    k = rng.choice(sorted(x for x in found if found[x]))
    i = rng.choice(found[k])
    labels = {"over": "Overbought: above 70", "under": "Oversold: below 30", "mid": "Neutral: between 30 and 70"}
    move = c[i + 15][3] / c[i][3] - 1
    follow = ("kept rising" if move > 0 else "fell back") if k == "over" else \
             ("kept falling" if move < 0 else "bounced") if k == "under" else ("rose" if move > 0 else "fell")
    return _test("rsi", "Read the RSI (14) in the panel under the chart. Where is it at the last candle?",
                 list(labels.values()), list(labels).index(k), i, panel="rsi",
                 result=f"The RSI was {r[i]:.0f}. Over the next 15 candles the price {follow} ({pct(move)}).",
                 explain="Above 70 the price has risen fast and below 30 it has fallen fast. That is a description, "
                         "not a signal: in a strong trend the RSI can stay overbought or oversold for a long time. "
                         "Traders use it with levels and with divergences (a new high in price on a lower RSI).")


def _ma(c, rng):
    n = len(c)
    cl = [x[3] for x in c]
    f_, s_ = sma(cl, 20), sma(cl, 50)
    found = {"golden": [], "death": [], "none": []}
    for i in range(max(LOOK, 66), n - AFTER):
        a, b = f_[i - 1] - s_[i - 1], f_[i] - s_[i]
        if a <= 0 < b:
            found["golden"].append(i)
        elif a >= 0 > b:
            found["death"].append(i)
        elif all((f_[j] - s_[j]) * b > 0 for j in range(i - 15, i + 1)):
            found["none"].append(i)
    if not any(found.values()):
        return None
    k = rng.choice(sorted(x for x in found if found[x]))
    i = rng.choice(found[k])
    labels = {"golden": "A golden cross: the 20 crossed above the 50", "death": "A death cross: the 20 crossed below the 50",
              "none": "No cross: the averages have not crossed lately"}
    move = c[i + AFTER - 1][3] / c[i][3] - 1
    return _test("ma", "The orange line is the 20-candle average, the blue one the 50. What just happened at the last candle?",
                 list(labels.values()), list(labels).index(k), i, overlay=["sma20", "sma50"],
                 result=f"{labels[k].split(':')[0]}. Over the next {AFTER} candles the price went {pct(move)}.",
                 explain="A cross says the recent average price has moved past the older one: the trend has already "
                         "turned by the time it happens, so crosses are late, and in a range they flip back and forth "
                         "(whipsaws). They are a filter for direction, not a timing tool.")


FIBS = (0.236, 0.382, 0.5, 0.618, 0.786)


def _fib(c, rng):
    """A swing and its pullback: which Fibonacci retracement did the pullback reach?"""
    n, u = len(c), unit(c)
    piv = patterns.zigzag(c, 3 * u)
    found = []
    for k in range(2, len(piv)):
        a, b, p = piv[k - 2], piv[k - 1], piv[k]
        if not (LOOK <= p[3] < n - AFTER) or a[2] == b[2]:
            continue
        lo, hi = (math.exp(a[1]), math.exp(b[1])) if b[2] == 1 else (math.exp(b[1]), math.exp(a[1]))
        r = abs(math.exp(b[1]) - math.exp(p[1])) / (hi - lo) if hi > lo else 0
        near = min(FIBS, key=lambda f: abs(f - r))
        if abs(near - r) <= 0.04 and (b[1] - a[1]) * b[2] > 5 * u:
            found.append((a, b, p, near))
    if not found:
        return None
    f = rng.choice(sorted({x[3] for x in found}))                 # every level as likely, however common
    a, b, p, f = rng.choice([x for x in found if x[3] == f])
    up = b[2] == 1
    names = [f"{x * 100:.1f}%" for x in FIBS]
    opts = names[:]
    ans = FIBS.index(f)
    lo, hi = math.exp(min(a[1], b[1])), math.exp(max(a[1], b[1]))
    lines = [{"price": (hi - x * (hi - lo)) if up else (lo + x * (hi - lo)), "label": f"{x * 100:.1f}%",
              "tone": "level", "from": a[0], "after": True} for x in FIBS]
    return _test("fib", f"The price swung {'up' if up else 'down'} from the first point to the second, then pulled back. "
                        f"About how much of the swing did the pullback give back?", opts, ans, p[3],
                 marks=[{"i": a[0], "price": math.exp(a[1]), "label": "Swing start", "after": False},
                        {"i": b[0], "price": math.exp(b[1]), "label": "Swing end", "after": False},
                        {"i": p[0], "price": math.exp(p[1]), "label": "Pullback", "after": True}],
                 lines=lines, result=f"It gave back about {f * 100:.1f}% of the swing.",
                 explain="Fibonacci retracements divide a swing at 23.6%, 38.2%, 50%, 61.8% and 78.6%. Pullbacks in a "
                         "trend often stop somewhere between 38.2% and 61.8%, which is why traders watch those levels "
                         "for an entry with a stop beyond the next one. No level is special on its own: they work best "
                         "where they line up with support or resistance.")


def _rr(c, rng):
    n = len(c)
    atr = atr_series(c)
    i = rng.randrange(LOOK, n - AFTER)
    ratio = rng.choice((1.0, 1.5, 2.0, 3.0))
    d = rng.choice((1, -1))
    risk = 1.2 * atr[i]
    entry = c[i][3]
    stop, target = entry - d * risk, entry + d * risk * ratio
    hit = None
    for j in range(i + 1, n):
        hi, lo = c[j][1], c[j][2]
        st = lo <= stop if d > 0 else hi >= stop
        tg = hi >= target if d > 0 else lo <= target
        if st or tg:
            hit = ("stop" if st else "target", j - i)
            break
    names = ["1 to 1", "1.5 to 1", "2 to 1", "3 to 1"]
    side = "long (a buy)" if d > 0 else "short"
    res = (f"The reward is {ratio:g} times the risk. "
           + (f"The {'stop-loss' if hit[0] == 'stop' else 'take-profit'} was hit {hit[1]} candles later: "
              f"{'-1R' if hit[0] == 'stop' else f'+{ratio:g}R'}." if hit else "Neither was hit in the candles there are."))
    return _test("rr", f"A {side} at the teal line, with the stop-loss and take-profit shown. What is the reward-to-risk ratio?",
                 names, [1.0, 1.5, 2.0, 3.0].index(ratio), i, show=min(AFTER, (hit[1] + 3) if hit else AFTER),
                 lines=[{"price": entry, "label": "Entry", "tone": "entry", "from": i, "after": False},
                        {"price": stop, "label": "Stop-loss", "tone": "stop", "from": i, "after": False},
                        {"price": target, "label": "Take-profit", "tone": "target", "from": i, "after": False}],
                 result=res,
                 explain="Reward to risk is the distance to the target divided by the distance to the stop. At 2 to 1 "
                         "you can be wrong twice for every win and still break even (before fees). It only means "
                         "something if the target is a place the price can really reach.")


def _stop(c, rng):
    """A bounce off support with a long entry: which stop makes sense? The answer is about where the idea is wrong,
    and the candles then show what each stop would have done."""
    t = _level(c, rng, only=1)
    if not t:
        return None
    i, lv = t["upto"], t["lines"][0]["price"]
    atr = atr_series(c)[i]
    entry = c[i][3]
    stops = {"good": lv - 0.6 * atr, "tight": entry - 0.15 * atr, "wide": entry - 6 * atr}
    labels = {"good": "Just below the support, outside the usual noise",
              "tight": "A hair below the entry, to lose as little as possible",
              "wide": "Far below, so it is never hit"}
    opts, ans = _shuffled(rng, labels["good"], [labels["tight"], labels["wide"]])
    hits = []
    for key in ("good", "tight", "wide"):
        j = next((j for j in range(i + 1, min(len(c), i + AFTER)) if c[j][2] <= stops[key]), None)
        hits.append(f"{labels[key].split(',')[0].lower()}: {'hit after ' + str(j - i) + ' candles' if j else 'not hit'}")
    return _test("stop", "You buy here, as the price bounces off support. Where does the stop-loss belong?", opts, ans, i,
                 lines=[t["lines"][0], {"price": entry, "label": "Entry", "tone": "entry", "from": i, "after": False}]
                 + [{"price": stops[k], "label": {"good": "Below support", "tight": "Tight", "wide": "Wide"}[k],
                     "tone": "stop", "from": i, "after": True} for k in stops],
                 result="What each stop did in the next candles: " + "; ".join(hits) + ".",
                 explain="A stop goes where the trade idea is proved wrong: here, a close well below the support. A stop "
                         "inside the normal noise gets hit by chance; a stop far away makes each loss so big the "
                         "position has to be tiny. Size the position from the stop, not the other way round.")


def _next(c, rng):
    n = len(c)
    for _ in range(50):
        i = rng.randrange(LOOK, n - 12)
        move = c[i + 10][3] / c[i][3] - 1
        if abs(move) > 1e-9:
            break
    else:
        return None
    return _test("next", "Will the price be higher or lower 10 candles from now?", ["Higher", "Lower"],
                 0 if move > 0 else 1, i, show=12,
                 result=f"Ten candles later it was {pct(move)}.",
                 explain="Over many tries, nobody calls the next few candles much better than a coin. Your score here "
                         "will drift towards 50%: that is the point. Trading works on many trades with small losses and "
                         "bigger wins, not on calling every move.")


MAKERS = {"level": _level, "trend": _trend, "pattern": _pattern, "breakout": _breakout, "candle": _candle, "rsi": _rsi,
          "ma": _ma, "fib": _fib, "rr": _rr, "stop": _stop, "next": _next}


def make(kind, candles, rng):
    """One test of `kind` from these candles ([o, h, l, c, v], oldest first), or None."""
    if kind not in MAKERS or len(candles) < LOOK + AFTER + 20:
        return None
    if any(x[2] <= 0 or x[1] < x[2] for x in candles):
        return None
    return MAKERS[kind](candles, rng)
