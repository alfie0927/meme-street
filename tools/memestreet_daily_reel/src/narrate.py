"""Voice an auto reel (spec.json from make_spec.py) and time everything on screen to the words.

Every scene's line is spoken with the Meme Street voice; the scenes follow each other with a short breath (GAP), never
a silent wait. A question scene keeps THINK seconds for the viewer, filled by a ticking countdown on screen and in the
sound. Each cue ("say": a phrase of the line) gets the time that phrase is spoken, and every word keeps its time for
the burned-in captions.
Output: work/<slot>/timeline.json (+ vo/*.wav, sfx/*.wav).   Usage: python3 src/narrate.py work/<slot>
"""
import difflib, json, os, re, sys
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
from voice import MODEL, trim, dur, words, norm_words
from pronounce import say_as

GAP, LEAD, TAIL, THINK = 0.12, 0.1, 0.6, 1.6        # (seconds: between scenes, before the first, after the last, quiz thinking time)
SR = 24000

def tone(path, freqs, length, vol=0.25):
    """A short synthesised sound: a tick, or a two-note chime for a reveal."""
    t = np.arange(int(length * SR)) / SR
    a = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs) * np.exp(-t * (40 if length < .1 else 7)) * vol
    sf.write(path, a.astype(np.float32), SR)

def tighten(a, sr=SR, keep=0.16, longest=0.22):
    """The voice without dead air: any pause inside a line longer than `longest` seconds is cut down to `keep`
    (the breath stays, the wait goes), and the ends are trimmed."""
    a = trim(a, sr)
    f = int(0.01 * sr); n = len(a) // f
    if n < 3: return a
    rms = np.sqrt(np.mean(a[:n * f].reshape(n, f) ** 2, axis=1)); quiet = rms < max(rms.max() * 0.03, 1e-4)
    out, k = [], 0
    while k < n:
        if quiet[k]:
            e = k
            while e < n and quiet[e]: e += 1
            run = a[k * f:e * f]
            out.append(run if (e - k) * 0.01 <= longest else np.concatenate([run[:int(keep / 2 * sr)], run[-int(keep / 2 * sr):]]))
            k = e
        else:
            out.append(a[k * f:(k + 1) * f]); k += 1
    out.append(a[n * f:])
    return np.concatenate(out)

def heard_ok(line, W):
    """Did the voice say the line? The recognised words must cover most of the written ones (a garbled or skipped
    passage fails the reel instead of posting)."""
    want = [key(w) for w in say_as(line).split() if key(w)]
    got = [w[0] for w in W]
    if not want or not got: return True
    m = sum(b.size for b in difflib.SequenceMatcher(None, want, got, autojunk=False).get_matching_blocks())
    return m / len(want) >= 0.6

def key(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())

def follow(words, tw, wt, d):
    """The time each of `words` (on-screen text) is said: matched in order to the spoken line, the rest spread between."""
    keys, out, j = [key(w) for w in tw], [], 0
    for w in words:
        k = next((q for q in range(j, len(keys)) if keys[q] == key(w) and key(w)), None)
        out.append(wt[k][0] if k is not None else None)
        if k is not None: j = k + 1
    known = [i for i, x in enumerate(out) if x is not None]
    for i in range(len(out)):
        if out[i] is None:
            lo = max([q for q in known if q < i], default=None); hi = min([q for q in known if q > i], default=None)
            a = out[lo] if lo is not None else 0.0; b = out[hi] if hi is not None else d * 0.8
            n0 = lo if lo is not None else -1; n1 = hi if hi is not None else len(out)
            out[i] = a + (b - a) * (i - n0) / (n1 - n0)
    return out

def align(tw, W, d):
    """Match the written words to the recognised ones (difflib), so every written word gets the time it is really
    said; a word the recogniser heard differently ("230" for "two thirty") takes its place between its neighbours."""
    key = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())
    out = [None] * len(tw)
    if W:
        sm = difflib.SequenceMatcher(None, [key(w) for w in tw], [w[0] for w in W], autojunk=False)
        for a, b, n in sm.get_matching_blocks():
            for q in range(n):
                out[a + q] = (W[b + q][1], W[b + q][2])
    known = [k for k, x in enumerate(out) if x]
    if not known:
        return [(d * k / len(tw), d * (k + 1) / len(tw)) for k in range(len(tw))]
    for k in range(len(tw)):
        if out[k]: continue
        lo = max([j for j in known if j < k], default=None); hi = min([j for j in known if j > k], default=None)
        t0 = out[lo][1] if lo is not None else 0.0; t1 = out[hi][0] if hi is not None else d
        a = lo if lo is not None else -1; b = hi if hi is not None else len(tw)
        f0, f1 = (k - a - 1) / (b - a - 1), (k - a) / (b - a - 1)
        out[k] = (t0 + (t1 - t0) * f0, t0 + (t1 - t0) * f1)
    return out

def live_daily():
    """Today's Daily Chart for the end card: its number and the best return so far (the game's own numbers)."""
    import urllib.request
    try:
        req = urllib.request.Request(os.environ.get("MS_BASE_LOCAL", "http://127.0.0.1:8000") + "/api/daily",
                                     headers={"X-Visitor": "reelendcard0000000001"})
        d = json.loads(urllib.request.urlopen(req, timeout=10).read())
        board = d.get("board") or []
        return {"number": d.get("number"), "best": max((b.get("ret") for b in board if b.get("ret") is not None), default=None)}
    except Exception:
        return None

def series_no(work, kind):
    """The reel's episode number in its series (Chart quiz #7), fixed per slot so a re-render keeps it."""
    f = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "series.json")
    S = json.load(open(f)) if os.path.exists(f) else {}
    slot = os.path.basename(os.path.normpath(work))
    if slot not in S.setdefault("slots", {}):
        c = S.setdefault("count", {}); c[kind] = c.get(kind, 0) + 1
        S["slots"][slot] = c[kind]
        os.makedirs(os.path.dirname(f), exist_ok=True); json.dump(S, open(f, "w"))
    return S["slots"][slot]

def main(work):
    S = json.load(open(os.path.join(work, "spec.json")))
    K = Kokoro(os.path.join(MODEL, "kokoro-v1.0.onnx"), os.path.join(MODEL, "voices-v1.0.bin"))
    for d in ("vo", "sfx"):
        os.makedirs(os.path.join(work, d), exist_ok=True)
    A = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    if not os.path.exists(os.path.join(A, "sfx_pop.wav")):
        import sounds; sounds.main()                           # (the house sounds, made once: sounds.py)
    tick, chime, pop, whoosh = (os.path.join(A, f"sfx_{x}.wav") for x in ("tick", "chime", "pop", "whoosh"))
    t, vo = LEAD, []
    for i, sc in enumerate(S["scenes"]):
        speed = float(os.environ.get("VOICE_SPEED", "1.08")) * (1.04 if sc["kind"] == "hook" else 1.0)
        a, _ = K.create(say_as(sc["vo"].strip()), voice="af_heart", speed=speed, lang="en-us")   # one take: natural flow
        clip = os.path.join(work, "vo", f"s{i}.wav"); sf.write(clip, tighten(a), SR)
        d = dur(clip); W = words(clip)
        if not heard_ok(sc["vo"], W):
            raise SystemExit(f"scene {i}: the voice does not match the line (garbled or skipped): {sc['vo'][:80]}")

        tw = sc["vo"].split()
        wt = align(tw, W, d)                                   # each written word's own (start, end) in the clip

        def at(phrase):
            """When `phrase` starts being spoken (seconds into the clip); the scene start if it is not in the line."""
            ch = sc["vo"].lower().find(phrase.lower().strip())
            if ch < 0: return 0.0
            return wt[min(len(sc["vo"][:ch].split()), len(wt) - 1)][0]

        sc["t0"] = round(t, 3); vs = t + 0.05
        if i: vo.append([whoosh, round(max(0, t - 0.12), 3)])                 # every scene change sounds the same
        sc["vs"] = round(vs, 3); sc["ve"] = round(vs + d, 3)
        vo.append([clip, round(vs, 3)])
        sc["text_words"] = tw                                  # the captions: the written words, each at its spoken time
        sc["wt"] = [[round(vs + a, 3), round(vs + b, 3)] for a, b in wt]
        if sc.get("text") and (sc["kind"] == "big" or sc.get("chart") is None):   # big words appear as they are said
            sc["text_t"] = [round(vs + x, 3) for x in follow(sc["text"].split(), tw, wt, d)]
        if sc.get("options"):                                  # each option appears as it is read out
            sc["opt_t"] = [round(vs + x, 3) for x in follow([o.split()[0] for o in sc["options"]], tw, wt, d)]
        for c in sc.get("cues", []):
            c["t"] = round(vs + at(c.get("say", "")), 3)
            if c.get("do") in ("mark", "bubble", "item", "line"): vo.append([pop, c["t"]])
        for x in sc.get("opt_t", []): vo.append([pop, x])
        t = vs + d
        if sc["kind"] == "question":                          # the viewer's moment: a ticking countdown, not silence
            think = float(sc.get("think", THINK)); sc["think_t"] = [round(t + 0.15, 3), round(t + 0.15 + think, 3)]
            for k in range(int(think / 0.4) + 1):
                vo.append([tick, round(t + 0.15 + k * 0.4, 3)])
            t += 0.15 + think
            vo.append([chime, round(t, 3)])
        t += GAP if i < len(S["scenes"]) - 1 else TAIL
        sc["t1"] = round(t, 3)
    S["T"] = round(t, 2); S["vo"] = vo; S["num"] = None
    S["daily"] = live_daily(); S["series"] = series_no(work, S.get("type", ""))
    json.dump(S, open(os.path.join(work, "timeline.json"), "w"))
    print(f"narration: {len(S['scenes'])} scenes, {S['T']:.1f}s")

if __name__ == "__main__":
    main(sys.argv[1])
