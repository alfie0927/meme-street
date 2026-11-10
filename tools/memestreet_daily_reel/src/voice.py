"""Narrate each beat (Kokoro 'af_heart', the Meme Street voice) and time every visual to the words.

For each beat it produces:
  t0 .. t1  : the scene on screen        vs : when the voice starts (may be a moment after t0)
  kf        : reveal keyframes [[time, candle]]: candles flow during the sentence that mentions them,
              never faster than MAX_CPS candles/second, and reach the candle as its phrase is spoken
  mk_t      : time each trade marker pops (start of "Short..." / "Buy..." / "Close trade...")
  cap_t     : time each caption appears (start of its phrase)
Word times come from speech recognition of the generated audio (faster-whisper); if that isn't
available they are estimated from sentence timing.
Usage: python3 src/voice.py work/<date>
"""
import json, os, re, subprocess, sys
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
MODEL = os.environ.get("KOKORO_DIR", os.path.join(ROOT, "models"))
GAP, TAIL, LEAD, SENT_GAP = 0.55, 1.2, 0.4, 0.16
MAX_CPS = float(os.environ.get("MAX_CANDLES_PER_SEC", "7"))      # reveal speed limit (peak candles/second)
MAX_PREROLL = 0.8                                                 # voice starts almost at once: candles draw while it speaks                                                 # most a scene may start before its voice

def trim(a, sr, db=-45):
    thr = 10 ** (db / 20); idx = np.where(np.abs(a) > thr)[0]
    return a if not len(idx) else a[max(0, idx[0] - int(.02 * sr)): idx[-1] + int(.06 * sr)]

def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)

_ASR = None
def words(path):
    global _ASR
    try:
        if _ASR is None:
            from faster_whisper import WhisperModel
            m = os.environ.get("ASR_MODEL", "base.en")      # (the copy on disk: loading it online hung for 1h45 on 2026-11-08)
            try: _ASR = WhisperModel(m, device="cpu", compute_type="int8", local_files_only=True)
            except Exception: _ASR = WhisperModel(m, device="cpu", compute_type="int8")   # (not downloaded yet: once, online)
        a = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                                         capture_output=True).stdout, np.float32)
        segs, _ = _ASR.transcribe(a, word_timestamps=True, language="en", beam_size=5)
        return [(re.sub(r"[^a-z0-9']", "", w.word.lower()), w.start, w.end) for s in segs for w in s.words]
    except Exception as e:
        print("word alignment unavailable, using estimates:", str(e)[:120]); return []

NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}
def norm_words(text):
    ws = [re.sub(r"[^a-z0-9']", "", x.lower()) for x in text.split()]
    return [NUM.get(x, x) for x in ws if x]

def speak(K, sent):
    """One sentence in the house voice: ElevenLabs (Sarah, as the other reels) at an easy recap pace, Kokoro if it fails."""
    if os.environ.get("ELEVEN_API_KEY", "").strip() and os.environ.get("REEL_VOICE") != "kokoro":
        try:
            import narrate
            from pronounce import say_as
            return narrate.el_line(say_as(sent), float(os.environ.get("RECAP_SPEED", "1.0"))), narrate.SR
        except Exception as e:
            print(f"ElevenLabs failed ({str(e)[:120]}); Kokoro reads it", flush=True)
    return K.create(sent, voice="af_heart", speed=1.0, lang="en-us")


def main(work):
    S = json.load(open(os.path.join(work, "script.json")))
    K = Kokoro(os.path.join(MODEL, "kokoro-v1.0.onnx"), os.path.join(MODEL, "voices-v1.0.bin"))
    os.makedirs(os.path.join(work, "vo"), exist_ok=True)
    clips, spans_all = [], []
    for i, b in enumerate(S["beats"]):                       # one sentence at a time -> exact sentence timing
        sents = [x for x in re.split(r"(?<=[.!?])\s+", b["vo"].strip()) if x]
        audio, spans, pos, cur, sr = [], [], 0, 0.0, 24000
        for j, sent in enumerate(sents):
            c0 = b["vo"].index(sent, pos); pos = c0 + len(sent)
            a, sr = speak(K, sent); a = trim(a, sr)
            if j: audio.append(np.zeros(int(SENT_GAP * sr), np.float32)); cur += SENT_GAP
            spans.append([c0, c0 + len(sent), cur, cur + len(a) / sr]); audio.append(a); cur += len(a) / sr
        out = os.path.join(work, "vo", f"b{i}.wav"); sf.write(out, np.concatenate(audio), sr)
        clips.append(out); spans_all.append(spans)
    # keep the reel under MAX_SECONDS with a gentle, pitch-preserving tempo (max 1.08x)
    MAX_T = float(os.environ.get("MAX_SECONDS", "120"))     # (the recap is slow on purpose: no speeding up to fit)
    talk = sum(dur(c) for c in clips); fixed = LEAD + GAP * (len(clips) - 1) + TAIL; f = 1.0
    if talk + fixed > MAX_T:
        f = min(1.08, talk / max(1.0, MAX_T - fixed))
        for c in clips:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", c, "-af", f"atempo={f:.3f}", c + ".tmp.wav"], check=True)
            os.replace(c + ".tmp.wav", c)
    for sp in spans_all:
        for x in sp: x[2] /= f; x[3] /= f

    t = LEAD; vo = []
    for i, (b, c, spans) in enumerate(zip(S["beats"], clips, spans_all)):
        d = dur(c)
        needs = b.get("cues") or b.get("capcues") or any(len(m) > 4 for m in b.get("mk", []))
        W = words(c) if needs else []
        text = b["vo"]

        def sentence_of(ch):
            for s_ in spans:
                if s_[0] <= ch <= s_[1] + 1: return s_
            return spans[-1]

        def phrase_time(ph, after_char=0):
            """(start, end) seconds within the clip at which `ph` is spoken."""
            ch = text.find(ph, after_char)
            if ch < 0: ch = text.find(ph)
            if ch < 0: return None
            # words before the phrase -> index in the recognised words (robust to small recognition differences)
            if W:
                target = norm_words(text[:ch]); want = norm_words(ph)
                k = min(len(W) - 1, len(target))
                best = None
                for j in range(max(0, k - 4), min(len(W), k + 5)):
                    sc = sum(1 for q, x in enumerate(want[:3]) if j + q < len(W) and (W[j + q][0][:4] == x[:4]))
                    if best is None or sc > best[0] or (sc == best[0] and abs(j - k) < abs(best[1] - k)): best = (sc, j)
                if best and best[0] >= 1:
                    j = best[1]; e = min(len(W) - 1, j + len(want) - 1)
                    return W[j][1], W[e][2]
            s_ = sentence_of(ch); fr0 = (ch - s_[0]) / max(1, s_[1] - s_[0]); fr1 = (ch + len(ph) - s_[0]) / max(1, s_[1] - s_[0])
            return s_[2] + fr0 * (s_[3] - s_[2]), s_[2] + fr1 * (s_[3] - s_[2])

        # ---- reveal keyframes (relative to voice start), candles flow during the sentence that mentions them
        kf, pre = None, 0.0
        if b.get("cues"):
            pts, have, after = [], b["reveal"][0], 0
            for cue in b["cues"]:
                ph, target = cue[0], cue[1]; zone = cue[2] if len(cue) > 2 else None
                ch = text.find(ph, after); after = max(after, ch + 1)
                tt = phrase_time(ph, max(0, ch))
                if tt is None or target <= have: continue
                s_ = sentence_of(max(0, ch))
                if zone is not None and have < zone < target:
                    # reach the zone as the phrase starts, then draw the zone's candles WHILE it is spoken
                    pts.append([s_[2], tt[0], have, zone]); pts.append([tt[0], max(tt[1], tt[0] + 0.3), zone, target])
                else:
                    pts.append([s_[2], tt[0] + 0.55 * (tt[1] - tt[0]), have, target])
                have = target
            if have < b["reveal"][1]:
                pts.append([spans[-1][2], d - 0.2, have, b["reveal"][1]])
            kf = [[0.0, b["reveal"][0]]]; prev_end = -MAX_PREROLL
            for s_start, arrive, v0, v1 in pts:
                need = (v1 - v0) / MAX_CPS                     # candles draw at a steady pace
                span = max(need, min((v1 - v0) * 0.45, arrive - (s_start - 0.1)))   # flow with the sentence; small moves just before the word
                start = max(prev_end, -MAX_PREROLL, min(arrive - span, arrive - 0.25))   # faster rather than a long silent pause
                kf.append([start, v0]); kf.append([max(start + 0.25, arrive), v1]); prev_end = kf[-1][0]
            kf[0][0] = min(kf[0][0], kf[1][0] if len(kf) > 1 else 0)
            pre = max(0.0, -min(k_[0] for k_ in kf))
        b["t0"] = round(t, 3); b["vs"] = round(t + pre, 3); b["vo_end"] = round(t + pre + d, 3)
        vo.append([c, round(t + pre, 3)])
        if kf: b["kf"] = [[round(b["vs"] + k_[0], 3), k_[1]] for k_ in kf]
        # ---- markers and captions pop at the start of their phrase
        for m in b.get("mk", []):
            if len(m) > 4 and m[4]:
                tt = phrase_time(m[4]); m.append(round(b["vs"] + (tt[0] if tt else 0.3), 3))
        if b.get("lv"):
            b["lv_t"] = []
            for L in b["lv"]:
                say = str(round(float(L[1:])))
                tt = phrase_time(say) if say in text else None
                b["lv_t"].append(round(b["vs"] + (tt[0] if tt else 0.1), 3))
        if b.get("capcues"):
            b["cap_t"] = []
            for cap, ph in b["capcues"]:
                tt = phrase_time(ph); b["cap_t"].append([cap, round(b["vs"] + (tt[0] if tt else 0.3), 3)])
        t += pre + d + (GAP if i < len(S["beats"]) - 1 else TAIL); b["t1"] = round(t, 3)
    S["T"] = round(t, 2); S["vo"] = vo; S["num"] = S.get("number")
    json.dump(S, open(os.path.join(work, "timeline.json"), "w"))
    print(f"narration: {len(vo)} beats, {S['T']:.1f}s (tempo x{f:.2f})")

if __name__ == "__main__":
    main(sys.argv[1])
