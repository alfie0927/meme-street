"""Chart patterns found the way a trader finds them (ROADMAP TA-A9), from candles alone: no peeking at the price model.

`find(candles, swing)` returns every pattern in a list of candles ([open, high, low, close, ...], oldest first), each
as a dict:

    kind      double_top, double_bottom, head_shoulders, inverse_head_shoulders, ascending_triangle,
              descending_triangle, symmetric_triangle, bull_flag, bear_flag, rising_wedge, falling_wedge,
              up_channel, down_channel, cup_handle
    dir       +1 if it points up (a breakout above `trigger` completes it), -1 if down
    at        the candle on which the pattern is known: its last swing point has just been confirmed
    start     the candle of its first swing point
    trigger   the price whose break (on a close) completes it: the neckline, the flag's top, the triangle's side
    invalid   the price beyond which (on a close) it has failed: the other side of the pattern
    target    the measured move: the pattern's height added to the trigger

`outcome(candles, pattern, wait, hold)` follows it forward like a trade: does a close break the trigger within `wait`
candles (it *completes*), and then does the price reach the target before a close beyond `invalid` (it *works*)?

Swing points come from a zigzag: a high is a swing high once the price has fallen `swing` (in log price) below it, and
the other way round, so each one is known only when it is confirmed, never earlier. A pattern is a template on the
last few swing points; the tolerances are the usual textbook ones (Bulkowski): two tops within a third of the pattern's
height of each other, a head clearly above its shoulders, a flag that gives back at most half of its pole.
"""
import math


def zigzag(candles, swing):
    """Swing points as (index, log price, +1 high / -1 low, index where confirmed), alternating."""
    out = []
    if not candles:
        return out
    hi, lo = math.log(candles[0][1]), math.log(candles[0][2])
    hi_i = lo_i = 0
    trend = 0                                     # +1: in an up-swing, following its high; -1: a down-swing's low
    for i, c in enumerate(candles):
        h, l = math.log(c[1]), math.log(c[2])
        if trend == 0:                            # (the start: wait until the first swing of the full size)
            if h > hi:
                hi, hi_i = h, i
            if l < lo:
                lo, lo_i = l, i
            if hi - lo >= swing:
                if hi_i > lo_i:
                    out.append((lo_i, lo, -1, i))
                    trend = 1
                else:
                    out.append((hi_i, hi, 1, i))
                    trend = -1
        elif trend == 1:
            if h > hi:
                hi, hi_i = h, i
            elif hi - l >= swing:
                out.append((hi_i, hi, 1, i))
                trend, lo, lo_i = -1, l, i
        else:
            if l < lo:
                lo, lo_i = l, i
            elif h - lo >= swing:
                out.append((lo_i, lo, -1, i))
                trend, hi, hi_i = 1, h, i
    return out


def _near(a, b, tol):
    return abs(a - b) <= tol


def _templates(pv, k, swing, n_candles):
    """The patterns whose last swing point is pv[k]."""
    out = []
    if k < 2:
        return out
    E = lambda j: pv[k - j]                      # E(0) is the newest swing point
    p0 = E(0)

    def add(kind, d, first, trigger, invalid, height):
        out.append({"kind": kind, "dir": d, "start": first[0], "at": p0[3], "trigger": math.exp(trigger),
                    "invalid": math.exp(invalid), "target": math.exp(trigger + d * height)})

    # double top / bottom: two swing points of the same kind at about the same price, with a clear dip between
    a, m, b = E(2), E(1), E(0)
    if a[2] == b[2]:
        s = a[2]
        height = (a[1] - m[1]) * s
        if height >= 1.5 * swing and _near(a[1], b[1], height / 3) and b[0] - a[0] >= 4:
            before = pv[k - 3] if k >= 3 else None
            if before is None or (m[1] - before[1]) * s > 0:          # it came after a move up (a top) or down
                add("double_top" if s == 1 else "double_bottom", -s, a, m[1], max(a[1], b[1]) if s == 1 else min(a[1], b[1]), height)
    # head and shoulders: shoulder, neck, head, neck, shoulder
    if k >= 4:
        ls, n1, hd, n2, rs = E(4), E(3), E(2), E(1), E(0)
        if ls[2] == hd[2] == rs[2]:
            s = hd[2]
            neck = (n1[1] + n2[1]) / 2
            height = (hd[1] - neck) * s
            if (height >= 1.5 * swing and (hd[1] - ls[1]) * s >= 0.25 * height and (hd[1] - rs[1]) * s >= 0.25 * height
                    and _near(ls[1], rs[1], 0.4 * height) and _near(n1[1], n2[1], 0.35 * height)):
                trig = min(n1[1], n2[1]) if s == 1 else max(n1[1], n2[1])
                add("head_shoulders" if s == 1 else "inverse_head_shoulders", -s, ls, trig, hd[1], height)
    if k >= 4:
        q = [E(4), E(3), E(2), E(1), E(0)]
        highs = [x for x in q if x[2] == 1]
        lows = [x for x in q if x[2] == -1]
        if len(highs) >= 2 and len(lows) >= 2:
            amps = [abs(q[i][1] - q[i - 1][1]) for i in range(1, 5)]
            first_amp = amps[0]
            hs = highs[-1][1] - highs[0][1]                  # how the tops moved
            ls_ = lows[-1][1] - lows[0][1]                   # how the bottoms moved
            flat = 0.25 * first_amp
            converging = amps[-1] < 0.75 * amps[0] and amps[-2] < amps[0]
            top, bot = max(x[1] for x in highs[-2:]), min(x[1] for x in lows[-2:])
            last_hi, last_lo = highs[-1][1], lows[-1][1]
            if first_amp >= 1.5 * swing and converging:
                if abs(hs) <= flat and ls_ > flat:
                    add("ascending_triangle", 1, q[0], top, last_lo, first_amp)
                elif abs(ls_) <= flat and hs < -flat:
                    add("descending_triangle", -1, q[0], bot, last_hi, first_amp)
                elif hs < -flat and ls_ > flat:
                    trend = 1 if (k >= 5 and pv[k - 5][2] == -1) else -1          # (it breaks out the way the move into it went)
                    add("symmetric_triangle", trend, q[0], last_hi if trend == 1 else last_lo,
                        last_lo if trend == 1 else last_hi, first_amp)
                elif hs > flat and ls_ > 1.3 * hs:
                    add("rising_wedge", -1, q[0], last_lo, last_hi, first_amp)
                elif ls_ < -flat and hs < 1.3 * ls_:
                    add("falling_wedge", 1, q[0], last_hi, last_lo, first_amp)
            # a channel: both sides moving the same way, by about the same amount, with steady swings (the pullbacks of a
            # trending channel are often half the size of its pushes)
            if (first_amp >= 1.5 * swing and min(amps) >= 0.35 * max(amps) and hs * ls_ > 0
                    and min(abs(hs), abs(ls_)) >= 0.5 * max(abs(hs), abs(ls_)) and abs(hs) >= 0.5 * first_amp):
                d = 1 if hs > 0 else -1
                add("up_channel" if d == 1 else "down_channel", d, q[0], last_hi if d == 1 else last_lo,
                    last_lo if d == 1 else last_hi, first_amp)
    # a flag: a fast, big move (the pole), then a pullback that gives back at most half of it
    pole0, pole1, flag = E(2), E(1), E(0)
    if pole1[2] == -flag[2]:
        s = pole1[2]
        pole = (pole1[1] - pole0[1]) * s
        give = (pole1[1] - flag[1]) * s
        if pole >= 3 * swing and pole1[0] - pole0[0] <= 8 and give <= 0.5 * pole and flag[3] - pole1[0] <= 10:
            add("bull_flag" if s == 1 else "bear_flag", s, pole0, pole1[1], flag[1], pole)
    # cup and handle: a rim, a rounded dip, a second rim at about the same height, and a small handle
    if k >= 3:
        r0, bottom, r1, handle = E(3), E(2), E(1), E(0)
        if r0[2] == r1[2] == 1 and bottom[2] == handle[2] == -1:
            depth = r0[1] - bottom[1]
            if (depth >= 2 * swing and _near(r0[1], r1[1], 0.15 * depth) and r1[1] - handle[1] <= 0.45 * depth
                    and bottom[0] - r0[0] >= 5 and r1[0] - bottom[0] >= 5 and handle[3] - r1[0] <= 0.6 * (r1[0] - r0[0])):
                add("cup_handle", 1, r0, max(r0[1], r1[1]), handle[1], depth)
    return out


KINDS = ("double_top", "double_bottom", "head_shoulders", "inverse_head_shoulders", "ascending_triangle",
         "descending_triangle", "symmetric_triangle", "bull_flag", "bear_flag", "rising_wedge", "falling_wedge",
         "up_channel", "down_channel", "cup_handle")


def find(candles, swing):
    """Every pattern in the candles, in the order they became known. `swing` is the zigzag's threshold in log price
    (about two daily sigmas on game-day candles). Where two patterns end on the same swing point, the more specific one
    is kept (a head and shoulders over the double top inside it)."""
    order = {k: i for i, k in enumerate(KINDS)}
    rank = {"head_shoulders": 0, "inverse_head_shoulders": 0, "cup_handle": 1, "double_top": 2, "double_bottom": 2}
    out = []
    pv = zigzag(candles, swing)
    for k in range(len(pv)):
        found = [p for p in _templates(pv, k, swing, len(candles)) if "flag" not in p["kind"]]
        if found:
            found.sort(key=lambda p: (rank.get(p["kind"], 4), order[p["kind"]]))
            out.append(found[0])
    # flags are shallow (they give back at most half of a fast move), so they are read off a finer zigzag
    fine = zigzag(candles, swing / 2)
    for k in range(len(fine)):
        out += [p for p in _templates(fine, k, swing / 2, len(candles)) if "flag" in p["kind"]]
    out.sort(key=lambda p: p["at"])
    return out


def find_all(candles, swings):
    """`find` at several swing sizes (small patterns show on a fine zigzag, big ones on a coarse one), without the same
    pattern twice: one of the same kind known within three candles of another is left out."""
    out = []
    for swing in swings:
        for p in find(candles, swing):
            if not any(q["kind"] == p["kind"] and abs(q["at"] - p["at"]) <= 3 for q in out):
                out.append(p)
    out.sort(key=lambda p: p["at"])
    return out


def outcome(candles, p, wait=10, hold=20):
    """Follow a pattern forward from the candle it became known on. Returns a dict: completed (a close beyond the
    trigger within `wait` candles, the way it points), broke_other_way (a close beyond `invalid` first), and for a
    completed one: the entry (that close), worked (the target was reached before a close beyond `invalid`, within
    `hold` candles), the exit price and the candles it took. Invalid (None) if the data runs out first."""
    d, i0, n = p["dir"], p["at"], len(candles)
    for j in range(i0 + 1, min(n, i0 + 1 + wait)):
        c = candles[j][3]
        if (c - p["trigger"]) * d > 0:
            entry = c
            for m in range(j + 1, min(n, j + 1 + hold)):
                hi, lo, cl = candles[m][1], candles[m][2], candles[m][3]
                if (hi if d == 1 else lo) * d >= p["target"] * d:
                    return {"completed": True, "worked": True, "entry": entry, "exit": p["target"], "bars": m - j}
                if (cl - p["invalid"]) * d < 0:
                    return {"completed": True, "worked": False, "entry": entry, "exit": cl, "bars": m - j}
            if j + hold >= n:
                return None
            return {"completed": True, "worked": False, "entry": entry, "exit": candles[j + hold][3], "bars": hold}
        if (c - p["invalid"]) * d < 0:
            return {"completed": False, "broke_other_way": True}
    if i0 + wait >= n:
        return None
    return {"completed": False, "broke_other_way": False}
