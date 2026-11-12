"""Lab: a silent narration. Times a spec.json the way narrate.py would (a human pace of 3.9 words a second, the house
pauses after commas and full stops, the quiz countdown) without voicing it, so a script can be drawn (lab/frames.py)
and judged by the simulated audience (lab/audience.py) with no voice credits and no work on the reel server.

  python3 lab/silent.py <work>     <work>/spec.json -> <work>/timeline.json
"""
import json, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from pronounce import digits

GAP, LEAD, TAIL, THINK = 0.24, 0.1, 1.6, 1.6            # (as narrate.py)
BEAT = {"enter": (0, "pop"), "move": (0, None), "hit": (.6, "boom"), "fall": (.5, "thud"), "launch": (0, "whoosh"), "emit": (0, None),
        "grow": (0, "pop"), "burst": (0, "boom"), "tint": (0, None), "count": (0, None), "fling": (0, "whoosh"), "crack": (0, "pop")}   # (a storyboard verb: seconds to its impact, its sound; as reel.html BEAT)
EVENTS = ("hit", "fall", "launch", "burst", "emit", "grow", "fling", "crack")


def beats(sc, vs, at, vo, sfx):
    """Time a scene's storyboard beats on their words (t), note each impact (ti), and add the verb's sound: a hit or a
    fall sounds at the impact, the rest as they start; coins chime; a count ticks. Returns the impact times."""
    out = []
    for b in sc.get("beats", []):
        b["t"] = round((vs + at(b["say"]) if b.get("say") else vs + 0.3) + float(b.get("after", 0)), 3)   # (a shot staggers its moves: "after")
        d, s = BEAT.get(b.get("do"), (0, None)); b["ti"] = round(b["t"] + d, 3)
        if b.get("do") == "emit": s = "chime" if b.get("what") == "coins" else "pop"
        if b.get("do") == "count":
            for k in range(min(6, int((re.findall(r"\d+", str(b.get("text", ""))) or ["0"])[0]) or 1)): vo.append(["tick", round(b["t"] + .15 * k, 3)])
        elif s: vo.append([s, b["ti"] if b["do"] in ("hit", "fall") else b["t"]])
        if b.get("do") in EVENTS: out.append(b["ti"])
    P = sc.get("props") or []                             # (a layout's own events are impacts too: the storm's strikes, the candles' burst)
    if sc.get("layout") == "storm": out += [p["t"] for p in P[1:] if p.get("t") is not None]
    return out

WPS, COMMA, STOP = 3.9, 0.28, 0.36
key = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())


def times(tw):
    """Each word's (start, end) in its line at the human pace, with the pauses a person makes; and the line's length."""
    t, out = 0.0, []
    for w in tw:
        d = 1 / WPS * (0.6 + 0.4 * min(2.0, len(w) / 5))    # (long words take a little longer)
        out.append((round(t, 3), round(t + d, 3))); t += d
        t += STOP if w[-1:] in ".?!" else COMMA if w[-1:] in ",;:" else 0
    return out, round(t, 3)


def follow(words, tw, wt, d):
    """When each on-screen word is said: matched in order to the line (unmatched ones spread between)."""
    keys, out, kw = [key(w) for w in tw], [], [key(w) for w in words]
    j = next((q for q in range(len(keys) - len(kw) + 1) if keys[q:q + len(kw)] == kw), 0)   # (said as one phrase, the words land there: "can hit the stock" is the line's last "can", not its first; the critic, 2026-11-12)
    for w in words:
        k = next((q for q in range(j, len(keys)) if keys[q] == key(w) and key(w)), None)
        out.append(wt[k][0] if k is not None else None)
        if k is not None: j = k + 1
    return [x if x is not None else d * 0.8 * i / max(1, len(out)) for i, x in enumerate(out)]


def at(vo, wt, phrase):
    ch = vo.lower().find((phrase or "").lower().strip())
    return 0.0 if ch < 0 or not phrase else wt[min(len(vo[:ch].split()), len(wt) - 1)][0]


def main(work):
    S = json.load(open(os.path.join(work, "spec.json"), encoding="utf-8")); t = LEAD; impacts = []
    for i, sc in enumerate(S["scenes"]):
        tw = sc["vo"].split(); wt, d = times(tw)
        sc["t0"] = round(t, 3); vs = t + 0.05; sc["vs"] = round(vs, 3); sc["ve"] = round(vs + d, 3)
        cap = digits(tw)
        sc["text_words"] = [c for c, _, _ in cap]
        sc["wt"] = [[round(vs + wt[a][0], 3), round(vs + wt[b][1], 3)] for _, a, b in cap]
        if sc.get("text") and (sc["kind"] in ("big", "free") or sc.get("chart") is None):
            sc["text_t"] = [round(vs + x, 3) for x in follow(sc["text"].split(), tw, wt, d)]
        if sc.get("options"):
            sc["opt_t"] = [round(vs + x, 3) for x in follow([o.split()[0] for o in sc["options"]], tw, wt, d)]
        for p in sc.get("props", []): p["t"] = round(vs + (at(sc["vo"], wt, p["say"]) if p.get("say") else 0.2), 3)
        for c in sc.get("cues", []): c["t"] = round(vs + at(sc["vo"], wt, c.get("say", "")), 3)
        impacts += beats(sc, vs, lambda ph: at(sc["vo"], wt, ph), [], None)
        t = vs + d
        if sc["kind"] == "question":
            think = float(sc.get("think", THINK)); sc["think_t"] = [round(t + 0.15, 3), round(t + 0.15 + think, 3)]; t += 0.15 + think
        t += GAP if i < len(S["scenes"]) - 1 or sc["kind"] != "outro" else TAIL   # (the hold is the sign-off's: a reel with no outro, a loop, replays at once)
        sc["t1"] = round(t, 3)
        if sc.get("layout") == "candles": impacts.append(round(sc["t1"] - .55, 3))   # (the candles' burst is an impact too)
    S["T"] = round(t, 2); S["vo"] = []; S["num"] = None; S.setdefault("daily", None); S["impacts"] = sorted(impacts)
    json.dump(S, open(os.path.join(work, "timeline.json"), "w", encoding="utf-8"))
    print(f"silent timeline: {len(S['scenes'])} scenes, {S['T']:.1f}s")


def demo():
    wt, d = times("Buy or sell? You have five seconds.".split())
    assert len(wt) == 7 and wt[3][0] > wt[2][1] + 0.3 and abs(d - (wt[-1][1] + STOP)) < 1e-6, (wt, d)
    assert follow(["Buy", "sell"], "Buy or sell?".split(), wt[:3], 1.0) == [wt[0][0], wt[2][0]]
    assert follow(["sell", "You"], "Buy or sell? You have five seconds.".split(), wt, d) == [wt[2][0], wt[3][0]]
    w2, d2 = times("It can stop and it can hit you.".split()); assert follow(["can", "hit"], "It can stop and it can hit you.".split(), w2, d2) == [w2[5][0], w2[6][0]]
    print("ok")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["demo"] else main(sys.argv[1])
