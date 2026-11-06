"""Voice an auto reel (spec.json from make_spec.py) and time everything on screen to the words.

Every scene's line is spoken with the Meme Street voice; the scenes follow each other with a short breath (GAP), never
a silent wait. A question scene keeps THINK seconds for the viewer, filled by a ticking countdown on screen and in the
sound. Each cue ("say": a phrase of the line) gets the time that phrase is spoken, and every word keeps its time for
the burned-in captions.
Output: work/<slot>/timeline.json (+ vo/*.wav, sfx/*.wav).   Usage: python3 src/narrate.py work/<slot>
"""
import difflib, glob, hashlib, json, os, re, shutil, sys
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
from voice import MODEL, NUM, trim, dur, words, norm_words
from pronounce import say_as, digits

GAP, LEAD, TAIL, THINK = 0.24, 0.1, 0.6, 1.6        # (seconds: between scenes = heard as a sentence pause, before the first, after the last, quiz thinking time)
SR = 24000

def tone(path, freqs, length, vol=0.25):
    """A short synthesised sound: a tick, or a two-note chime for a reveal."""
    t = np.arange(int(length * SR)) / SR
    a = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs) * np.exp(-t * (40 if length < .1 else 7)) * vol
    sf.write(path, a.astype(np.float32), SR)

# How real narrators pace a Short (measured 2026-11-06 on 16 top Shorts from TradingLab, JeaFx, Casual Finance, Qxir,
# Sticky Academy, Stickman Invests, Brad Goh and Tom Crown, with the same word timing as below): about 3.9 words a second
# while talking, a pause of about 0.28 s after a comma and 0.36 s after a sentence, and no pause inside a phrase.
WPS, HUMAN = 3.9, {"comma": 0.28, "sentence": 0.36}
# The silence put in to get there: the voice trails off before it is silent, so a pause is heard about 0.2 s longer
# than the silence inserted (calibrated 2026-11-06 with the same measure: 0.08 s at a full stop is heard as 0.25 s,
# 0.16 s as 0.41 s; a comma is never heard under about 0.33 s).
PAUSE = {",": 0.2, ";": 0.2, ":": 0.2, ".": 0.32, "!": 0.32, "?": 0.32}      # (a full stop under a comma's pause was heard as a comma: HUMAN)
INSIDE = 0.08                                            # (longest pause kept between words with no punctuation)

def talk_rate(W):
    """Words a second while talking (pauses over 0.25 s left out), as measured on the human Shorts."""
    if len(W) < 3: return None
    t = sum(e - s for _, s, e in W) + sum(g for g in (b[1] - a[2] for a, b in zip(W, W[1:])) if 0 < g < 0.25)
    return len(W) / t if t > 0 else None

def pace(a, tw, sr=SR):
    """Put human pauses into a line. The voice already stops at its punctuation, so the line's N longest silences are its
    N commas and full stops (in order): each becomes the pause its mark asks for (PAUSE), and every other silence is cut
    to INSIDE. Word timings are not used: Whisper writes 'sixty-nine' as '69,' and shifts them, which put a comma pause
    one word early ('near | sixty-nine') and left the real one in (a double pause)."""
    f = int(0.01 * sr); n = len(a) // f
    rms = np.sqrt(np.mean(a[:n * f].reshape(n, f) ** 2, axis=1)); quiet = rms < max(rms.max() * 0.03, 1e-4)
    runs, s = [], None                                   # interior silences, in 10 ms frames
    for j in range(n + 1):
        if j < n and quiet[j]:
            s = j if s is None else s
        elif s is not None:
            if s > 0 and j < n: runs.append((s, j))
            s = None
    marks = [PAUSE[m] for w in tw[:-1] if (m := w.rstrip("\"')")[-1:]) in PAUSE]
    stops = sorted(sorted((r for r in runs if r[1] - r[0] >= 3), key=lambda r: r[0] - r[1])[:len(marks)])   # (30 ms+: the voice dips at a mark even when it barely stops)
    want = dict(zip(stops, marks if len(stops) == len(marks) else [PAUSE[","]] * len(stops)))
    out, pos = [], 0
    for r in runs:
        z = want.get(r, min((r[1] - r[0]) * 0.01, INSIDE))
        out += [a[pos:r[0] * f], np.zeros(int(z * sr), a.dtype)]; pos = r[1] * f
    out.append(a[pos:])
    return np.concatenate(out)

def demo():
    t = np.arange(int(0.3 * SR)) / SR; v = (0.5 * np.sin(2 * np.pi * 200 * t)).astype(np.float32); z = lambda d: np.zeros(int(d * SR), np.float32)
    a = np.concatenate([v, z(0.2), v, z(0.5), v, z(0.15), v])         # "one | two, three four": the 0.5 s silence is the comma
    o = pace(a, ["one", "two,", "three", "four"])   # (the 0.15 s silence is cut to INSIDE)
    assert abs(len(o) - (4 * len(v) + int((INSIDE * 2 + PAUSE[","]) * SR))) < SR * 0.03, len(o) / SR
    w = align(["warning,", "or", "trouble"], [("warning", 0.0, 0.5), ("trouble", 1.4, 1.8)], 2.0)
    assert abs(w[1][0] - 1.1) < 1e-6, w                                   # 'or' is said just before 'trouble', after the pause

def heard_ok(line, W):
    """Did the voice say the line? The recognised words must cover most of the written ones (a garbled or skipped
    passage fails the reel instead of posting)."""
    sp = lambda x: re.sub(r"\d", lambda m: NUM[m.group()], "".join(norm_words(x)))   # (letters only, digits spelt: Whisper writes "A, one to one" as "a1 to 1")
    want, got = sp(say_as(line)), sp(" ".join(w[0] for w in W))
    if not want: return True
    if not got: return False                               # (no recognised words: the captions could not be timed)
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
        if lo is not None and tw[lo].rstrip("\"')")[-1:] in PAUSE:          # (after a comma the pause comes first: the missed words
            t0 = max(t0, t1 - 0.3 * (b - a - 1))                           #  are said at the end of the gap, not the start)
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

FILM_FPS = 30


def film(sc, work):
    """The scene's shot as frames (work/footage/<clip>/f00001.jpg...) at FILM_FPS, slowed to fill the scene (never below
    0.6x; past that the last frame holds). No clip (no key, over the cap, refused): a film scene becomes big text."""
    import footage, subprocess
    d = sc["t1"] - sc["t0"]
    clip = footage.shot(sc["shot"], d, os.path.join(work, "footage"))
    if not clip:
        sc.pop("shot", None)
        if sc["kind"] == "film": sc.update(kind="big", text=sc.get("head") or "")
        return
    n = int(d * FILM_FPS) + 2
    out = clip[:-4]
    if len(glob.glob(os.path.join(out, "f*.jpg"))) < n:
        cd = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", clip],
                                  capture_output=True, text=True).stdout or 5)
        slow = min(1 / 0.6, max(1.0, d / cd))
        os.makedirs(out, exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clip, "-vf", f"setpts={slow:.4f}*PTS,fps={FILM_FPS},eq=brightness=-0.03:contrast=1.06:saturation=0.9,"   # (graded to the house look)
                        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920", "-q:v", "3",
                        "-frames:v", str(n), os.path.join(out, "f%05d.jpg")], check=True)
    sc["film"] = {"dir": os.path.abspath(out), "n": len(glob.glob(os.path.join(out, "f*.jpg"))), "fps": FILM_FPS}


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
        clip = os.path.join(work, "vo", f"s{i}.wav"); tw = sc["vo"].split()
        speed = float(os.environ.get("VOICE_SPEED", "1.0"))
        h = os.path.join(work, "vo", "cache", hashlib.sha1(json.dumps([sc["vo"], speed, PAUSE, INSIDE, WPS]).encode()).hexdigest()[:16])
        if os.path.exists(h + ".json"):                        # (a line the last cut already voiced: a remake redoes only what changed)
            shutil.copy(h + ".wav", clip); W = [tuple(w) for w in json.load(open(h + ".json"))]
        else:
            for _ in range(3):                                 # one take per line (natural flow), at the human talking speed
                a = trim(K.create(say_as(sc["vo"].strip()), voice="af_heart", speed=speed, lang="en-us")[0], SR)
                sf.write(clip, pace(a, tw), SR)   # the pauses a person makes, at the commas and full stops
                W = words(clip); r = talk_rate(W)              # (measured as heard, pauses in: what the critic and a viewer hear)
                if not r or abs(r / WPS - 1) < 0.05: break
                speed = min(1.35, max(0.8, speed * WPS / r))
            os.makedirs(os.path.dirname(h), exist_ok=True); shutil.copy(clip, h + ".wav"); json.dump(W, open(h + ".json", "w"))
        d = dur(clip)
        if not heard_ok(sc["vo"], W):
            raise SystemExit(f"scene {i}: the voice does not match the line (garbled or skipped): {sc['vo'][:80]}")
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
        cap = digits(tw)                                       # the captions: the written words, numbers in digits ('two oh three' 203),
        sc["text_words"] = [c for c, _, _ in cap]              # each from when it starts being said
        sc["wt"] = [[round(vs + wt[a][0], 3), round(vs + wt[b][1], 3)] for _, a, b in cap]
        if sc.get("text") and (sc["kind"] == "big" or sc.get("chart") is None):   # big words appear as they are said
            sc["text_t"] = [round(vs + x, 3) for x in follow(sc["text"].split(), tw, wt, d)]
        if sc.get("options"):                                  # each option appears as it is read out
            sc["opt_t"] = [round(vs + x, 3) for x in follow([o.split()[0] for o in sc["options"]], tw, wt, d)]
        for p in sc.get("props", []):                         # a 3D scene's props pop in on their words
            p["t"] = round(vs + at(p["say"]) if p.get("say") else vs + 0.2, 3); vo.append([pop, p["t"]])
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
    for sc in S["scenes"]:                                     # realistic video shots (footage.py), fitted to their scenes
        if sc.get("shot"):
            film(sc, work)
    S["T"] = round(t, 2); S["vo"] = vo; S["num"] = None
    S["daily"] = live_daily()
    json.dump(S, open(os.path.join(work, "timeline.json"), "w"))
    print(f"narration: {len(S['scenes'])} scenes, {S['T']:.1f}s")

if __name__ == "__main__":
    main(sys.argv[1])
