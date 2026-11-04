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

GAP, LEAD, TAIL, SENT_GAP, THINK = 0.22, 0.15, 0.9, 0.12, 1.6
SR = 24000

def tone(path, freqs, length, vol=0.25):
    """A short synthesised sound: a tick, or a two-note chime for a reveal."""
    t = np.arange(int(length * SR)) / SR
    a = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs) * np.exp(-t * (40 if length < .1 else 7)) * vol
    sf.write(path, a.astype(np.float32), SR)

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

def main(work):
    S = json.load(open(os.path.join(work, "spec.json")))
    K = Kokoro(os.path.join(MODEL, "kokoro-v1.0.onnx"), os.path.join(MODEL, "voices-v1.0.bin"))
    for d in ("vo", "sfx"):
        os.makedirs(os.path.join(work, d), exist_ok=True)
    tick, chime = os.path.join(work, "sfx", "tick.wav"), os.path.join(work, "sfx", "chime.wav")
    tone(tick, [1800], 0.05, 0.18); tone(chime, [880, 1320], 0.6, 0.22)
    t, vo = LEAD, []
    for i, sc in enumerate(S["scenes"]):
        sents = [x for x in re.split(r"(?<=[.!?])\s+", sc["vo"].strip()) if x]
        parts, cur = [], 0.0
        for j, s in enumerate(sents):
            a, _ = K.create(s, voice="af_heart", speed=float(os.environ.get("VOICE_SPEED", "1.05")), lang="en-us")
            a = trim(a, SR)
            if j: parts.append(np.zeros(int(SENT_GAP * SR), np.float32))
            parts.append(a)
        clip = os.path.join(work, "vo", f"s{i}.wav"); sf.write(clip, np.concatenate(parts), SR)
        d = dur(clip); W = words(clip)
        spoken = norm_words(sc["vo"])

        tw = sc["vo"].split()
        wt = align(tw, W, d)                                   # each written word's own (start, end) in the clip

        def at(phrase):
            """When `phrase` starts being spoken (seconds into the clip); the scene start if it is not in the line."""
            ch = sc["vo"].lower().find(phrase.lower().strip())
            if ch < 0: return 0.0
            return wt[min(len(sc["vo"][:ch].split()), len(wt) - 1)][0]

        sc["t0"] = round(t, 3); vs = t + 0.05
        sc["vs"] = round(vs, 3); sc["ve"] = round(vs + d, 3)
        vo.append([clip, round(vs, 3)])
        sc["text_words"] = tw                                  # the captions: the written words, each at its spoken time
        sc["wt"] = [[round(vs + a, 3), round(vs + b, 3)] for a, b in wt]
        for c in sc.get("cues", []):
            c["t"] = round(vs + at(c.get("say", "")), 3)
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
    json.dump(S, open(os.path.join(work, "timeline.json"), "w"))
    print(f"narration: {len(S['scenes'])} scenes, {S['T']:.1f}s")

if __name__ == "__main__":
    main(sys.argv[1])
