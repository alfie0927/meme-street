"""Turn one day's Daily Chart data into a beat-by-beat reel script.

Input : data/<date>.json  (the /api/daily response after the game is done)
Output: work/<date>/script.json  (beats with narration, captions and chart directions)

Rules baked in (house style):
  * no mention of fees
  * no stop-loss placement; say "watch in case it turns into a fake breakout" instead
  * only trades someone could have taken live: enter/exit at a candle close, after the signal
"""
import json, sys, os
import numpy as np

MIN_TRADE = 0.004      # ignore trades smaller than 0.4%
MAX_TRADES = 6         # before merging same-direction trades; keeps the story short
MERGE_GAP = 4          # events this close together share one beat

def pct(x, sign=True):
    return ("+" if x >= 0 and sign else "") + f"{x*100:.2f}%"

def say_pct(x):
    v = f"{abs(x)*100:.1f}".rstrip("0").rstrip(".")
    return v.replace(".", " point ")                  # "2.9" -> "2 point 9" so the voice says "two point nine"

def say_price(p):
    return f"{round(p)}"

def analyse(d, own_name=""):
    g = d["game"]; C = g["candles"]; H = g.get("history", 60); n = len(C)
    o = np.array([c[0] for c in C])
    cl = np.array([c[3] for c in C]); vol = np.array([c[4] for c in C], float)
    green = cl >= o
    hold = g.get("hold", cl[-1] / cl[H] - 1)

    def vol_ratio(i):
        a = max(0, i - 22); base = vol[a:max(a + 1, i - 1)].mean()
        return float(vol[max(0, i - 1):i + 1].mean() / base) if base > 0 else 1.0

    # ---------------------------------------------------------------- events in the live part
    events = []
    for L in g.get("levels", []):
        p = L["price"]
        for idx, outcome in L["tests"]:
            if idx < H - 1:
                continue
            ref = cl[max(0, idx - 3)]
            frm = "above" if ref > p else "below"
            ev = dict(idx=int(idx), price=p, kind=L["kind"], outcome=outcome, frm=frm, vr=vol_ratio(idx))
            # direction this event points to, and the candle that confirms it
            if outcome == "broke":
                ev["dir"] = "short" if frm == "above" else "long"
                cond = (lambda k: cl[k] < p) if ev["dir"] == "short" else (lambda k: cl[k] > p)
            elif outcome == "held":
                ev["dir"] = "long" if frm == "above" else "short"
                cond = (lambda k: green[k]) if ev["dir"] == "long" else (lambda k: not green[k])
            else:  # fake break: price pokes through, then snaps back
                ev["dir"] = "long" if frm == "above" else "short"
                cond = (lambda k: cl[k] > p) if ev["dir"] == "long" else (lambda k: cl[k] < p)
            ev["entry"] = next((k for k in range(max(H, idx - 1), min(n, idx + 5)) if cond(k)), None)
            if outcome == "broke" and ev["entry"] is not None:   # judge a break by the volume on the candle that confirms it
                ev["vr"] = vol_ratio(ev["entry"])
            events.append(ev)
    events = [e for e in events if e["entry"] is not None]          # only narrate what a candle close confirmed
    events.sort(key=lambda e: e["idx"])

    # ---------------------------------------------------------------- candidate trades + best combination
    sig = [(e["entry"], e["dir"], e) for e in events if e["entry"] is not None]
    sig_idx = set(s[0] for s in sig)
    trail = {"long": set(), "short": set()}
    for k in range(H + 3, n):           # first opposite candle after a run of 3+ in the trade's favour
        if not green[k] and green[k - 1] and green[k - 2] and green[k - 3]: trail["long"].add(k)
        if green[k] and not green[k - 1] and not green[k - 2] and not green[k - 3]: trail["short"].add(k)
    cands = []
    for e_idx, d_, ev in sig:
        for x in sorted(sig_idx | trail[d_] | {n - 1}):
            if x <= e_idx:
                continue
            r = (cl[x] - cl[e_idx]) / cl[e_idx] * (1 if d_ == "long" else -1)
            if r >= MIN_TRADE:
                why = "end" if x == n - 1 else ("signal" if x in sig_idx else "trail")
                cands.append(dict(entry=e_idx, exit=x, dir=d_, r=float(r), ev=ev, why=why))
    # dynamic programme: best compounded return with non-overlapping trades (entry >= previous exit)
    cands.sort(key=lambda c: c["exit"])
    best = {H - 1: (1.0, [])}
    def best_upto(i):
        b = (1.0, [])
        for k, v in best.items():
            if k <= i and v[0] > b[0]:
                b = v
        return b
    for c in cands:
        base = best_upto(c["entry"])
        if len(base[1]) >= MAX_TRADES:
            continue
        val = (base[0] * (1 + c["r"]), base[1] + [c])
        if c["exit"] not in best or val[0] > best[c["exit"]][0]:
            best[c["exit"]] = val
    total_mult, trades = max(best.values(), key=lambda v: v[0])
    merged = []
    for t in trades:
        if merged and merged[-1]["dir"] == t["dir"] and merged[-1]["exit"] == t["entry"]:
            m = merged[-1]; m["exit"] = t["exit"]; m["why"] = t["why"]
            m["r"] = float((cl[m["exit"]] - cl[m["entry"]]) / cl[m["entry"]] * (1 if m["dir"] == "long" else -1))
        else:
            merged.append(dict(t))
    trades = merged
    if len(trades) > 3:                              # keep the story tight: narrate the 3 biggest trades
        keep = sorted(sorted(trades, key=lambda t: -t["r"])[:3], key=lambda t: t["entry"])
        trades = keep
    total = float(np.prod([1 + t["r"] for t in trades]) - 1) if trades else 0.0

    board = [b for b in d.get("board", []) if b.get("name") != own_name]
    best_player = max([b["ret"] for b in board], default=None)
    return dict(C=C, H=H, n=n, hold=float(hold), events=events, trades=trades, total=float(total),
                best_player=best_player, players=len(board), number=d.get("number"), levels=g.get("levels", []))

# ==================================================================== narration
def event_cues(e, n):
    """Cues for an event: [phrase, candle, zone_start]. The zone's candles draw while the phrase is spoken.
    Also returns the word each caption should appear on (captions appear as their word is said)."""
    k, en = e["idx"], (e["entry"] if e["entry"] is not None else e["idx"])
    nx = lambda j: min(n - 1, j)
    if e["outcome"] == "broke":
        return [["broke", en, max(0, en - 1)]], ["broke", "volume"]
    if e["outcome"] == "held":
        if e["frm"] == "above":
            if e["kind"] == "resistance":
                return [["acted as support", k, k], ["buyers stepped in", en, en]], ["acted as support"]
            return [["and it held", k, k], ["Buyers stepped in", en, en]], ["held"]
        if e["kind"] == "support":
            return [["back up to old support", max(0, k - 1), max(0, k - 2)], ["pushed it back", nx(max(en, k + 1)), k]], ["acted as resistance"]
        return [["and it held", k, k], ["pushed it back", nx(max(en, k + 1)), k]], ["held"]
    if e["frm"] == "below":
        return [["poked above", k, max(0, k - 1)], ["couldn't hold", nx(k + 2), k + 1]], ["fake break"]
    return [["dipped below", k, max(0, k - 1)], ["snapped straight back", nx(k + 2), k + 1]], ["fake break"]

def describe(e):
    p, P = e["price"], say_price(e["price"])
    vr = e["vr"]
    volp = (f", on about {round(vr)} times normal volume. That's a real break." if vr >= 2 else
            ", but on light volume." if vr < 1.2 else ".")
    if e["outcome"] == "broke":
        if e["frm"] == "above":
            return ("Support breaks", f"Then support near {P} broke{volp}", [f"support {p:.2f} broke"] + ([f"volume {vr:.1f}x average"] if vr >= 2 else []), "red")
        return ("Resistance breaks", f"Then price broke above resistance near {P}{volp}", [f"resistance {p:.2f} broke"] + ([f"volume {vr:.1f}x average"] if vr >= 2 else []), "green")
    if e["outcome"] == "held":
        if e["frm"] == "above":
            if e["kind"] == "resistance":
                return ("Old resistance holds", f"Old resistance near {P} now acted as support, and buyers stepped in.", [f"{p:.2f} held as support"], "green")
            return ("Support holds", f"Price dropped to support near {P}, and it held. Buyers stepped in.", [f"support {p:.2f} held"], "green")
        if e["kind"] == "support":
            return ("Rejected", f"Then price ran back up to old support near {P}. It now acted as resistance, and sellers pushed it back.", ["old support = new resistance"], "red")
        return ("Resistance holds", f"Price pushed up to resistance near {P}, and it held. Sellers pushed it back.", [f"resistance {p:.2f} held"], "red")
    if e["frm"] == "below":
        return ("Fake breakout", f"Price poked above {P}, but it couldn't hold. A fake breakout.", [f"fake break of {p:.2f}"], "amber")
    return ("Fake breakdown", f"Price dipped below {P}, then snapped straight back. A fake breakdown.", [f"fake break of {p:.2f}"], "amber")

def build_script(A):
    C, H, n = A["C"], A["H"], A["n"]
    cl = [c[3] for c in C]
    trades, events = A["trades"], A["events"]
    beats = []
    hold, total, num = A["hold"], A["total"], A["number"]
    up_down = "rose" if hold >= 0 else "fell"
    if trades and total < hold:
        hook = f"Daily Chart number {num}. The stock {up_down} {say_pct(hold)} percent. Today the stock did better than us: just buying at the open and holding beat these trades. We trade proper setups, not hope."
    elif trades:
        hook = f"Daily Chart number {num}. The stock {up_down} {say_pct(hold)} percent. Here's how you could have finished up {say_pct(total)} percent."
    else:
        hook = f"Daily Chart number {num}. The stock {up_down} {say_pct(hold)} percent. And today, patience was the winning trade."
    beats.append(dict(title=f"Daily Chart #{num}", vo=hook, win=[0, n - 1], reveal=[0, n - 1], caps=[f"the stock: {pct(hold)}"],
                      capcues=[[f"the stock: {pct(hold)}", "The stock"]]))

    # setup: nearest levels around the price when the clock starts
    p0 = cl[H - 1]
    first_live = events[0]["price"] if events else None
    pre = [L for L in A["levels"] if any(H - 40 <= t[0] < H for t in L["tests"]) or L["price"] == first_live] or A["levels"]
    sup = max([L["price"] for L in pre if L["price"] < p0], default=None)       # nearest level below price acts as support
    res = min([L["price"] for L in pre if L["price"] > p0], default=None)       # nearest level above acts as resistance
    lv, caps = [], []
    if sup and res:
        vo = f"Before the clock started, price sat between support near {say_price(sup)}, and resistance near {say_price(res)}."
    elif sup:
        vo = f"Before the clock started, price sat above support near {say_price(sup)}."
    elif res:
        vo = f"Before the clock started, price sat just under resistance near {say_price(res)}."
    else:
        vo = "Before the clock started, price was drifting with no clear levels."
    if res: lv.append(f"R{res:.2f}"); caps.append(f"resistance {res:.2f}")
    if sup: lv.append(f"S{sup:.2f}"); caps.append(f"support {sup:.2f}")
    capc0 = ([[f"resistance {res:.2f}", "resistance near"]] if res else []) + ([[f"support {sup:.2f}", "support near"]] if sup else [])
    beats.append(dict(title="The setup", vo=vo, win=[0, min(n - 1, H + 4)], reveal=[H - 1, H - 1], lv=lv, caps=caps, capcues=capc0))

    # moments: events that matter (anything tied to a trade, every break / fake, and holds)
    tidx = {}
    for k, t in enumerate(trades, 1):
        tidx.setdefault(t["entry"], []).append(("in", k, t)); tidx.setdefault(t["exit"], []).append(("out", k, t))
    near_trade = lambda e: any(abs(e["idx"] - i) <= 2 or abs((e["entry"] or -99) - i) <= 1 for i in tidx)
    keep = [e for e in events if near_trade(e) or (e["outcome"] == "broke" and e["vr"] >= 1.2) or e["outcome"] == "fake break"]
    if len(keep) > 6:
        keep = [e for e in keep if any(abs(e["idx"] - i) <= 3 for i in tidx) or e["outcome"] != "held"][:6]
    moments = [("ev", e["idx"], e) for e in keep]
    for i, lst in tidx.items():
        for x in lst:
            moments.append(("tr", i, x))
    order = lambda m: 0 if m[0] == "ev" else (1 if m[2][0] == "out" else 2)
    moments.sort(key=lambda m: (m[1], order(m)))
    groups = []
    for m in moments:
        if groups and m[1] - groups[-1][-1][1] <= MERGE_GAP:
            groups[-1].append(m)
        else:
            groups.append([m])

    pre_sup, pre_res = sup, res
    def gap_beat(s0, e0):
        seg_cl = cl[s0:e0 + 1]; hi_ = max(c[1] for c in C[s0:e0 + 1]); lo_ = min(c[2] for c in C[s0:e0 + 1])
        ch = seg_cl[-1] / seg_cl[0] - 1
        dur_s = max(5, int(round((e0 - s0) / 5.0)) * 5)        # 1 candle = 1 second of the game
        vols = [c[4] for c in C]; thin = np.mean(vols[s0:e0 + 1]) < 0.8 * np.mean(vols[H:])
        if pre_res and hi_ > pre_res and seg_cl[-1] < pre_res and s0 <= H + 2:
            t_, v_, c_ = "A weak push", "From the open, price climbed and poked above resistance" + (", but volume was thin" if thin else "") + ", and it couldn't hold. Straight back into the range.", ["above resistance, no follow-through"]
        elif pre_sup and lo_ < pre_sup and seg_cl[-1] > pre_sup and s0 <= H + 2:
            t_, v_, c_ = "A shakeout", "From the open, price slipped and dipped below support, then snapped straight back.", ["below support, snapped back"]
        elif ch < -0.006:
            t_, v_, c_ = "Sellers take over", f"Then sellers took over, and price drifted lower for about {dur_s} seconds" + (", on thin volume." if thin else "."), [f"drift lower {ch*100:.1f}%"]
        elif ch > 0.006:
            t_, v_, c_ = "Buyers step in", f"Then buyers stepped in, and price drifted higher for about {dur_s} seconds" + (", on thin volume." if thin else "."), [f"drift higher +{ch*100:.1f}%"]
        else:
            t_, v_, c_ = "Chop zone", f"Then it chopped sideways for about {dur_s} seconds. No clean setup, so no trade.", ["no setup = no trade"]
        lvg = ([f"R{pre_res:.2f}"] if pre_res else []) + ([f"S{pre_sup:.2f}"] if pre_sup else []) if s0 <= H + 2 else []
        hl_ = []
        if t_ == "A weak push":   # box the candles that poked above resistance
            ks = [k for k in range(s0, e0 + 1) if C[k][1] > pre_res]; hl_ = [[ks[0], ks[-1], "amber"]] if ks else []
        if t_ == "A shakeout":
            ks = [k for k in range(s0, e0 + 1) if C[k][2] < pre_sup]; hl_ = [[ks[0], ks[-1], "amber"]] if ks else []
        if t_ == "A weak push" and hl_:
            cues = [["above resistance", hl_[0][1], hl_[0][0]], ["back into the range", e0]]; capc = [[c_[0], "couldn't hold"]]
        elif t_ == "A shakeout" and hl_:
            cues = [["below support", hl_[0][1], hl_[0][0]], ["snapped straight back", e0]]; capc = [[c_[0], "snapped straight back"]]
        elif t_ == "Chop zone":
            cues = [["so no trade", e0]]; capc = [[c_[0], "No clean setup"]]     # sideways candles flow through the whole scene
        else:
            cues = [["seconds", e0]]; capc = [[c_[0], "lower" if t_ == "Sellers take over" else "higher"]]
        return dict(title=t_, vo=v_, win=[max(0, s0 - 20), e0 + 8], reveal=[s0, e0], lv=lvg[:2], hl=hl_, caps=c_, cues=cues, capcues=capc)
    open_tr = {}
    reveal_from = H
    for grp in groups:
        grp.sort(key=order)
        a = min(m[1] for m in grp); b = max(m[1] for m in grp)
        if a - reveal_from >= 18:                     # long stretch before the next event: narrate it first
            beats.append(gap_beat(reveal_from, a - 3)); reveal_from = a - 3
        title, parts, caps, lv, hl, mk, span = None, [], [], [], [], [], []
        cues, capc = [], []
        if grp[0][0] == "tr" and grp[0][2][0] == "out" and a - reveal_from >= 6:
            up = cl[a] > cl[reveal_from]
            parts.append(f"Price {'climbed' if up else 'fell'} for the next {a - reveal_from} seconds.")
            cues.append(["seconds", a])
        for kind, i, x in grp:
            if kind == "ev":
                t_, v_, c_, col = describe(x)
                title = title or t_; parts.append(v_); caps += c_
                ec, kw = event_cues(x, n); cues += [list(c) for c in ec]
                for j, cap_ in enumerate(c_): capc.append([cap_, kw[min(j, len(kw) - 1)]])
                lv.append(("S" if x["frm"] == "above" else "R") + f"{x['price']:.2f}")
                c0 = x["entry"] if (x["outcome"] == "broke" and x["entry"] is not None) else x["idx"]   # (2) box the candle that confirms it
                if x["outcome"] != "held": hl.append([max(0, c0 - 1), min(n - 1, c0), col])
            else:
                io, k, t = x
                if io == "in":
                    side = "Short" if t["dir"] == "short" else "Buy"
                    where = {"broke": "below the break" if t["dir"] == "short" else "above the break",
                             "held": "on the bounce" if t["dir"] == "long" else "on the rejection",
                             "fake break": "as it snaps back"}[t["ev"]["outcome"]]
                    parts.append(f"Trade {k}. {side} the first close {where}, and watch in case it turns into a fake breakout." if k == 1
                                 else f"Trade {k}. {side} {where}, and watch for a fake breakout.")
                    caps.append(f"{side.lower()} {cl[t['entry']]:.2f}")
                    side_ph = " ".join(parts[-1].split(". ", 1)[1].split()[:3])
                    cues.append([f"Trade {k}.", t["entry"]]); capc.append([caps[-1], side_ph])
                    span.append([t["entry"], t["exit"], "red" if t["dir"] == "short" else "green"])
                    said = parts[-1].split(". ", 1)[1].split()[:3]           # e.g. "Short the first" / "Buy on the"
                    mk.append([t["entry"], cl[t["entry"]], "SHORT" if t["dir"] == "short" else "BUY", "red" if t["dir"] == "short" else "green", " ".join(said)])
                    title = f"Trade {k}: {'short' if t['dir'] == 'short' else 'long'}" if title is None else title
                else:
                    word = "Plus" if t["r"] >= 0 else "Minus"
                    how = {"end": f"Hold trade {k} into the close.",
                           "trail": f"Close trade {k} on the first {'green' if t['dir'] == 'short' else 'red'} candle.",
                           "signal": f"Close trade {k}."}[t["why"]]
                    parts.append(f"{how} {word} {say_pct(t['r'])} percent.")
                    caps.append(f"trade {k}: {pct(t['r'])}")
                    ph = how.split(" into")[0].split(" on the")[0].rstrip(".")
                    cues.append([ph, t["exit"]]); capc.append([caps[-1], f"{word} {say_pct(t['r'])}"])
                    if not any(m_[0] == t["entry"] for m_ in mk):
                        mk.append([t["entry"], cl[t["entry"]], "SHORT" if t["dir"] == "short" else "BUY", "red" if t["dir"] == "short" else "green"])
                    mk.append([t["exit"], cl[t["exit"]], "COVER" if t["dir"] == "short" else "SELL", "green" if t["dir"] == "short" else "red", " ".join(how.split()[:3]).rstrip(".")])
                    span.append([t["entry"], t["exit"], "red" if t["dir"] == "short" else "green"])
                    title = title or f"Trade {k} closes"
        win0 = max(0, a - 24); win1 = max(b + 12, win0 + 36)
        for k, t in list(open_tr.items()):             # trades still open: keep their entry marker + shading
            if not any(m_[2] == "SHORT" or m_[2] == "BUY" for m_ in mk if m_[0] == t["entry"]):
                mk.insert(0, [t["entry"], cl[t["entry"]], "SHORT" if t["dir"] == "short" else "BUY", "red" if t["dir"] == "short" else "green"])
            if not any(sp[0] == t["entry"] for sp in span): span.append([t["entry"], min(t["exit"], b), "red" if t["dir"] == "short" else "green"])
            win0 = min(win0, max(0, t["entry"] - 6))
        for kind, i, x in grp:
            if kind == "tr":
                io, k, t = x
                if io == "in": open_tr[k] = t
                else: open_tr.pop(k, None)
        beats.append(dict(title=title, vo=" ".join(parts), win=[win0, win1], reveal=[reveal_from, b],
                          lv=list(dict.fromkeys(lv))[:2], hl=hl, mk=mk, span=span, caps=caps[:2],
                          cues=cues, capcues=[c for c in capc if c[0] in caps[:2]]))
        reveal_from = b

    if len(beats) > 11:                              # busy day: drop optional chop beats first
        beats = [b for b in beats if b["title"] != "Chop zone"] if sum(b["title"] == "Chop zone" for b in beats) else beats
    if (n - 1) - reveal_from >= 12:                    # the story always runs to the final candle
        beats.append(gap_beat(reveal_from, n - 1))
    # keep the reveal moving forward only: a scene ends at its furthest cue, the next one starts there
    last_end = H
    for bb in beats:
        if not bb.get("cues"): continue
        bb["reveal"][0] = max(bb["reveal"][0], last_end)
        for c in bb["cues"]: c[1] = max(c[1], bb["reveal"][0])
        bb["reveal"][1] = max([bb["reveal"][1]] + [c[1] for c in bb["cues"]])
        last_end = bb["reveal"][1]
    sc_trades = [dict(k=f"trade {k} · {'short' if t['dir'] == 'short' else 'long'}", v=pct(t["r"])) for k, t in enumerate(trades, 1)]
    bp = A["best_player"]
    if trades:
        sc_vo = (f"{len(trades)} trade{'s' if len(trades) > 1 else ''}. Plus {say_pct(total)} percent. "
                 f"The stock {'gained' if hold >= 0 else 'lost'} {say_pct(hold)}"
                 + (f", and today's best player made {say_pct(bp)}." if bp is not None and bp >= 0 else "."))
    else:
        sc_vo = "No clean setups today, so the best trade was no trade."
    beats.append(dict(title="The scorecard", vo=sc_vo, win=[H, n - 1], reveal=[n - 1, n - 1],
                      span=[[t["entry"], t["exit"], "red" if t["dir"] == "short" else "green"] for t in trades],
                      score=dict(tr=sc_trades, tot=pct(total), hold=pct(hold), best=pct(bp) if bp is not None else "—"), caps=[]))
    beats.append(dict(title="New chart daily", vo="A new chart drops every day. Play the Daily Chart at Meem Street dot net, slash daily.",
                      win=[0, n - 1], reveal=[n - 1, n - 1], caps=["memestreet.net/daily"], outro=True))
    return beats

def day_notes(A):
    """What only this day's chart had: its range, its biggest candle, its key moment, and how many played."""
    C, H = A["C"], A["H"]
    live = C[H:]
    big = max(range(len(live)), key=lambda k: abs(live[k][3] / live[k][0] - 1))
    out = ["", f"Range: {min(c[2] for c in live):.2f} to {max(c[1] for c in live):.2f}. "
               f"Biggest candle: {pct(live[big][3] / live[big][0] - 1)} at second {big + 1}."]
    if A["events"]:
        k = describe(max(A["events"], key=lambda e: e["vr"]))[1].removeprefix("Then ")
        out.append("Key moment: " + k[0].upper() + k[1:])
    if A["players"]:
        out.append(f"{A['players']} {'player' if A['players'] == 1 else 'players'} took on this chart.")
    return out

def caption(A):
    hold, total, num = A["hold"], A["total"], A["number"]
    lines = [f"Daily Chart #{num} recap", ""]
    if A["trades"]:
        lines.append(f"The stock {'gained' if hold >= 0 else 'lost'} {pct(hold, False).lstrip('+-')}. The best realistic play made {pct(total)}.")
        for k, t in enumerate(A["trades"], 1):
            lines.append(f"Trade {k}: {t['dir']} {pct(t['r'])}")
    else:
        lines.append("No clean setups today. Sometimes the best trade is no trade.")
    if A["best_player"] is not None:
        lines.append(f"Today's best player: {pct(A['best_player'])}")
    lines += day_notes(A)
    lines += ["", "New mystery chart every day. Two minutes. Can you beat it?", "memestreet.net/daily (link in bio)", "",
              "Fictional market · practice money, no cash value · not investment advice", "",
              "#memestreet #dailychart #chartreading #tradingeducation #learntotrade"]
    return "\n".join(lines)

if __name__ == "__main__":
    src, out_dir = sys.argv[1], sys.argv[2]
    own = os.environ.get("MS_USER", "")
    d = json.load(open(src))
    A = analyse(d, own)
    beats = build_script(A)
    os.makedirs(out_dir, exist_ok=True)
    json.dump(dict(number=A["number"], history=A["H"], candles=A["C"], levels=A["levels"], beats=beats), open(os.path.join(out_dir, "script.json"), "w"))
    open(os.path.join(out_dir, "caption.txt"), "w").write(caption(A))
    print(f"Daily #{A['number']}: hold {pct(A['hold'])}, best plan {pct(A['total'])} with {len(A['trades'])} trades, best player {pct(A['best_player']) if A['best_player'] is not None else 'n/a'}")
    for k, t in enumerate(A["trades"], 1):
        print(f"  trade {k}: {t['dir']:5s} {t['entry']}->{t['exit']} ({t['why']}) {pct(t['r'])}  from {t['ev']['outcome']} {t['ev']['price']}")
    for b in beats:
        print(f"  [{b['title']}] {b['vo']}")
