"""Step 6 of the studio: the sound. "Every footstep, every door, and the music under the voice."

  python3 sound.py <reel dir>          work/silent.mp4 (+ work/voice.wav when the reel has a narrator) -> out/reel.mp4

It runs where the music library and the voices are (the reel server). From reel.json it takes "music" (a track of the no-credit
library), "events" [[t, kind(, gain)], ...] (what is HEARD when something is SEEN) and "music_db".
  the music   starts where the track gets going, loops to the reel's length, fades out; with a narrator it sits MUSIC_UNDER dB
              under the voice and DUCKS a further DUCK dB while he speaks (it comes back up in the gaps); alone it is the bed.
  the hits    each lands ONE FRAME after its picture (a sound that leads its picture reads as a mistake), its peak HIT_OVER dB
              over the music where it lands, never over the voice.
  the level   one gain for the whole reel to -14.5 LUFS (measured, not guessed), a limiter for stray peaks only.
Nothing here can be judged by ear by the maker: check.py measures the result (loudness, peak, holes).
"""
import json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.dirname(HERE); sys.path.insert(0, os.path.join(SRC, "explainer")); sys.path.insert(0, SRC)
import numpy as np, soundfile as sf, sounds as SD
SR = SD.SR; MUSIC_UNDER, DUCK, HIT_OVER, LUFS = 13.0, 7.0, 5.0, -14.5
rms = lambda x: float(np.sqrt((np.asarray(x, np.float64) ** 2).mean()) + 1e-9)


SFX = os.environ.get("STUDIO_SFX") or os.path.join(os.path.dirname(SRC), "assets", "sfx")      # (real CC0 recordings, judged by ears.py: manifest.json + wav/)
_LIB = None
def library():
    """kind -> [(wav samples, sync seconds)], best first: the recordings ears.py passed. {} when the library is not there."""
    global _LIB
    if _LIB is None:
        _LIB = {}; mf = os.path.join(SFX, "manifest.json")
        if os.path.exists(mf):
            for f in sorted(json.load(open(mf, encoding="utf-8"))["files"], key=lambda f: -float(f.get("score") or 0)):
                if f.get("fits") is False or str(f.get("licence")).lower() not in ("cc0", "pdm"): continue          # (never a sound that needs a credit)
                x, sr = sf.read(os.path.join(SFX, f["file"]), dtype="float32"); x = x if x.ndim == 1 else x.mean(1)
                if sr != SR: x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x).astype(np.float32)
                _LIB.setdefault(f["kind"], []).append((x, float(f.get("sync_s") or 0)))
    return _LIB
ALIAS = {"rise": ["rise", "riser"], "riser": ["riser", "rise"], "tick": ["tick", "click"], "swish": ["swish", "whoosh"], "sparkle": ["sparkle", "bell"], "ding": ["ding", "bell"], "snap": ["snap", "click"], "drop": ["drop", "thud"]}


def real(kind, n):
    """The n-th use of a kind in a reel takes the next good recording of it (a repeat never sounds the same twice in a row). -> (samples, sync) or None."""
    L = library()
    for k in ALIAS.get(kind, [kind]):
        if L.get(k): return L[k][n % len(L[k])]
    return None


def synth(kind):
    """A hit by name: the library's (pop, whoosh, thud, ding, rise, boom) and a few made here."""
    t = lambda n: np.arange(int(n * SR)) / SR; env = lambda x, k: x * np.exp(-k * t(len(x) / SR)); rng = np.random.default_rng(7)
    if kind == "tick": return np.asarray(SD.pop(), np.float32) * .5
    if kind == "whoosh": return np.asarray(SD.whoosh(.3), np.float32)
    if kind == "swish": return np.asarray(SD.whoosh(.18), np.float32) * .7
    if kind in ("pop", "thud", "ding", "rise", "boom"): return np.asarray(getattr(SD, kind)(), np.float32)
    if kind == "coin": x = t(.35); return (env(np.sin(2 * np.pi * 1318 * x), 9) + .7 * np.roll(env(np.sin(2 * np.pi * 1975 * x), 11), int(.07 * SR))).astype(np.float32)
    if kind == "click": return env(rng.standard_normal(int(.03 * SR)), 160).astype(np.float32)
    if kind == "snap": x = t(.09); return (env(rng.standard_normal(len(x)), 60) + env(np.sin(2 * np.pi * 220 * x), 40)).astype(np.float32)
    if kind == "drop": x = t(.6); return env(np.sin(2 * np.pi * np.cumsum(180 * np.exp(-3.2 * x)) / SR), 3.5).astype(np.float32)               # a falling tone
    if kind == "riser": x = t(.9); n = rng.standard_normal(len(x)); k = np.cumsum(n) ; k = n - np.convolve(n, np.ones(40) / 40, "same"); return (k * (x / .9) ** 2 * .8).astype(np.float32)      # hiss that swells
    if kind == "crumble": x = t(.7); return (env(np.convolve(rng.standard_normal(len(x)), np.ones(24) / 24, "same") * (rng.random(len(x)) > .55), 4) * 4).astype(np.float32)
    if kind == "sparkle": x = t(.5); return sum(np.roll(env(np.sin(2 * np.pi * f * x), 14), int(k * .06 * SR)) for k, f in enumerate((2093, 2637, 3136, 3951))).astype(np.float32) * .5
    if kind == "buzz": x = t(.32); return (env(np.sign(np.sin(2 * np.pi * 110 * x)), 5) * .6).astype(np.float32)                                # a wrong-answer buzzer
    raise SystemExit("no such sound: " + kind)


def mix(d):
    import make as M
    r = json.load(open(os.path.join(d, "reel.json"), encoding="utf-8")); work, out = os.path.join(d, "work"), os.path.join(d, "out"); os.makedirs(out, exist_ok=True)
    silent = os.path.join(work, "silent.mp4"); R = json.load(open(os.path.join(work, "timeline.json"), encoding="utf-8")); T = float(R["T"]); n = int(T * SR)
    os.environ["EXPLAINER_TRACK"] = r.get("music") or ""; tr = M.track(r.get("title", "")); f = os.path.join(M.MUSIC_DIR, tr["file"])
    if tr.get("credit"): raise SystemExit("this track needs a credit line: the studio uses only the no-credit library")
    raw = np.frombuffer(subprocess.run([M.FFMPEG, "-v", "error", "-i", f, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32).reshape(-1, 2)
    b = SR; lv = np.sqrt((raw[: len(raw) // b * b].mean(1).reshape(-1, b) ** 2).mean(1)); go = int(np.argmax(lv >= .8 * np.median(lv))); raw = raw[go * b:]       # (from where it gets going)
    m = np.concatenate([raw] * (n // len(raw) + 1))[:n].copy(); k = int(1.2 * SR); m[-k:] *= np.linspace(1, 0, k)[:, None]
    vf = os.path.join(work, "voice.wav"); v = None
    if r.get("say") and os.path.exists(vf):
        x = np.frombuffer(subprocess.run([M.FFMPEG, "-v", "error", "-i", vf, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32)
        v = np.zeros(n, np.float32); v[: min(n, len(x))] = x[:n]
        talk = np.abs(v) > 10 ** (-38 / 20); ref = rms(v[talk]) if talk.any() else rms(v)                    # the voice's level while he speaks
        m *= ref * 10 ** (-MUSIC_UNDER / 20) / rms(m)
        w = int(.02 * SR); e = np.sqrt(np.convolve(v.astype(np.float64) ** 2, np.ones(w) / w, "same")); on = (e > ref * 10 ** (-24 / 20)).astype(np.float64)
        up, dn = np.exp(-1 / (.06 * SR)), np.exp(-1 / (.4 * SR)); g = np.empty(n); a = 0.0          # (down fast as he starts, back up slowly after)
        for i in range(n): a = on[i] + (a - on[i]) * (up if on[i] > a else dn); g[i] = a
        m *= (10 ** (-DUCK * g / 20))[:, None]
    else: m *= .25 * 10 ** (float(r.get("music_db", -6.0)) / 20) / rms(m)
    hits = np.zeros((n + SR, 2), np.float32); bed = rms(m) * 2.2; used = {}          # (about the music's peaks)
    evf = os.path.join(work, "events.json")             # (a page engine writes what is heard itself: ride.js's window.__events)
    for ev in r.get("events") or (json.load(open(evf)) if os.path.exists(evf) else []):
        t, kind = float(ev[0]) + 1 / 30, ev[1]; used[kind] = used.get(kind, -1) + 1; rx = real(kind, used[kind])
        x, sync = rx if rx else (synth(kind), 0.0); a = int((t - sync) * SR)                    # (a recording lands with its own hit point on the frame, not its first sample)
        if a < 0: x, a = x[-a:], 0
        if a >= n: continue
        x = x[: len(hits) - a]; peak = bed * 10 ** (HIT_OVER / 20) * (float(ev[2]) if len(ev) > 2 else 1.0)
        if v is not None: peak = min(peak, float(np.percentile(np.abs(v), 99.5)) * .7)
        hits[a:a + len(x)] += (x * (peak / (np.abs(x).max() + 1e-9)))[:, None]
    y = m + hits[:n] + (v[:, None] if v is not None else 0); pre = os.path.join(work, "mix.wav"); sf.write(pre, y, SR)
    heard = re.findall(r"I:\s+(-?[\d.]+) LUFS", subprocess.run([M.FFMPEG, "-hide_banner", "-nostats", "-i", pre, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr)
    gain = LUFS - float(heard[-1]) if heard else 0; mp4 = os.path.join(out, "reel.mp4")
    subprocess.run([M.FFMPEG, "-v", "error", "-y", "-i", silent, "-i", pre, "-map", "0:v", "-map", "1:a", "-map_metadata", "-1", "-c:v", "copy", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{T:.3f}", mp4], check=True)
    os.remove(pre); print(mp4, tr["title"], f"gain {gain:+.1f} dB", "voice" if v is not None else "no voice", len(r.get("events") or (json.load(open(evf)) if os.path.exists(evf) else [])), "hits"); return mp4


if __name__ == "__main__":
    if len(sys.argv) < 2: raise SystemExit(__doc__)
    mix(sys.argv[1])
