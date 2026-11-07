"""Lab: a silent narration. Times a spec.json the way narrate.py would (a human pace of 3.9 words a second, the house
pauses after commas and full stops, the quiz countdown) without voicing it, so a script can be drawn (lab/frames.py)
and judged by the simulated audience (lab/audience.py) with no voice credits and no work on the reel server.

  python3 lab/silent.py <work>     <work>/spec.json -> <work>/timeline.json
"""
import json, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from pronounce import digits

GAP, LEAD, TAIL, THINK = 0.24, 0.1, 1.6, 1.6            # (as narrate.py)
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
    keys, out, j = [key(w) for w in tw], [], 0
    for w in words:
        k = next((q for q in range(j, len(keys)) if keys[q] == key(w) and key(w)), None)
        out.append(wt[k][0] if k is not None else None)
        if k is not None: j = k + 1
    return [x if x is not None else d * 0.8 * i / max(1, len(out)) for i, x in enumerate(out)]


def at(vo, wt, phrase):
    ch = vo.lower().find((phrase or "").lower().strip())
    return 0.0 if ch < 0 or not phrase else wt[min(len(vo[:ch].split()), len(wt) - 1)][0]


def main(work):
    S = json.load(open(os.path.join(work, "spec.json"), encoding="utf-8")); t = LEAD
    for i, sc in enumerate(S["scenes"]):
        tw = sc["vo"].split(); wt, d = times(tw)
        sc["t0"] = round(t, 3); vs = t + 0.05; sc["vs"] = round(vs, 3); sc["ve"] = round(vs + d, 3)
        cap = digits(tw)
        sc["text_words"] = [c for c, _, _ in cap]
        sc["wt"] = [[round(vs + wt[a][0], 3), round(vs + wt[b][1], 3)] for _, a, b in cap]
        if sc.get("text") and (sc["kind"] == "big" or sc.get("chart") is None):
            sc["text_t"] = [round(vs + x, 3) for x in follow(sc["text"].split(), tw, wt, d)]
        if sc.get("options"):
            sc["opt_t"] = [round(vs + x, 3) for x in follow([o.split()[0] for o in sc["options"]], tw, wt, d)]
        for p in sc.get("props", []): p["t"] = round(vs + (at(sc["vo"], wt, p["say"]) if p.get("say") else 0.2), 3)
        for c in sc.get("cues", []): c["t"] = round(vs + at(sc["vo"], wt, c.get("say", "")), 3)
        t = vs + d
        if sc["kind"] == "question":
            think = float(sc.get("think", THINK)); sc["think_t"] = [round(t + 0.15, 3), round(t + 0.15 + think, 3)]; t += 0.15 + think
        t += GAP if i < len(S["scenes"]) - 1 else TAIL
        sc["t1"] = round(t, 3)
    S["T"] = round(t, 2); S["vo"] = []; S["num"] = None; S.setdefault("daily", None)
    json.dump(S, open(os.path.join(work, "timeline.json"), "w", encoding="utf-8"))
    print(f"silent timeline: {len(S['scenes'])} scenes, {S['T']:.1f}s")


def demo():
    wt, d = times("Buy or sell? You have five seconds.".split())
    assert len(wt) == 7 and wt[3][0] > wt[2][1] + 0.3 and abs(d - (wt[-1][1] + STOP)) < 1e-6, (wt, d)
    assert follow(["Buy", "sell"], "Buy or sell?".split(), wt[:3], 1.0) == [wt[0][0], wt[2][0]]
    print("ok")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["demo"] else main(sys.argv[1])
