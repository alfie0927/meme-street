"""Voice an auto reel (spec.json from make_spec.py) and time everything on screen to the words.

Every scene's line is spoken with the Meme Street voice; the scenes follow each other with a short breath (GAP), never
a silent wait. A question scene keeps THINK seconds for the viewer, filled by a ticking countdown on screen and in the
sound. Each cue ("say": a phrase of the line) gets the time that phrase is spoken, and every word keeps its time for
the burned-in captions.
Output: work/<slot>/timeline.json (+ vo/*.wav, sfx/*.wav).   Usage: python3 src/narrate.py work/<slot>
"""
import json, os, re, sys
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

        def at(phrase):
            """When `phrase` starts being spoken (seconds into the clip); the scene start if it is not in the line."""
            ch = sc["vo"].lower().find(phrase.lower().strip())
            if ch < 0: return 0.0
            k = len(norm_words(sc["vo"][:ch]))
            if W:
                return W[min(k, len(W) - 1)][1]
            return d * k / max(1, len(spoken))

        sc["t0"] = round(t, 3); vs = t + 0.05
        sc["vs"] = round(vs, 3); sc["ve"] = round(vs + d, 3)
        vo.append([clip, round(vs, 3)])
        sc["words"] = [[w[0], round(vs + w[1], 3), round(vs + w[2], 3)] for w in W] or \
            [[w, round(vs + d * k / len(spoken), 3), round(vs + d * (k + 1) / len(spoken), 3)] for k, w in enumerate(spoken)]
        sc["text_words"] = sc["vo"].split()                    # (the captions show the written words, timed by W)
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
