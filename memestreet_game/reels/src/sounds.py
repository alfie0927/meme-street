"""The house sounds of every reel, all synthesised here (no samples, no licences): a soft music loop that sits under
the voice, and a small fixed set of effects (whoosh on a scene change, pop when something appears, tick for a quiz
countdown, chime on a reveal, boom for a crash or a burst, thud for a fall). Usage: python3 src/sounds.py  (writes assets/music.wav and assets/sfx_*.wav once)
"""
import os
import numpy as np
import soundfile as sf

SR = 44100
ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def env(n, a=0.01, r=0.3):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / r)


def tone(f, length, r=0.3, shape="sine"):
    t = np.arange(int(length * SR)) / SR
    w = np.sin(2 * np.pi * f * t) if shape == "sine" else (2 * ((f * t) % 1) - 1) * 0.4
    return w * env(len(t), 0.01, r)


def music(seconds=64, bpm=92):
    """A calm loop: four chords (Am F C G) as a soft filtered pad, a low pulse on each beat, a light hat on the off-beat."""
    beat = 60 / bpm; n = int(seconds * SR); out = np.zeros(n)
    chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [130.81, 196.0, 261.63], [196.0, 246.94, 293.66]]
    bar = 4 * beat
    for b in range(int(seconds / bar) + 1):
        ch = chords[b % 4]; s = int(b * bar * SR); L = int(bar * SR)
        t = np.arange(L) / SR
        pad = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t) for f in ch) / 6
        pad *= np.minimum(1, t / 0.6) * np.minimum(1, (bar - t) / 0.6)
        e = min(n, s + L); out[s:e] += 0.22 * pad[:e - s]
        for k in range(4):                                   # pulse and hat
            p = int(s + k * beat * SR)
            if p >= n: break
            kick = np.sin(2 * np.pi * 55 * np.arange(int(0.25 * SR)) / SR) * env(int(0.25 * SR), 0.003, 0.08)
            out[p:p + len(kick)] += 0.35 * kick[:max(0, n - p)]
            h = int(p + beat / 2 * SR); hat = np.random.default_rng(k).standard_normal(int(0.04 * SR)) * env(int(0.04 * SR), 0.001, 0.012)
            if h < n: out[h:h + len(hat)] += 0.05 * hat[:max(0, n - h)]
    k = int(0.02 * SR); smooth = np.convolve(out, np.ones(8) / 8, mode="same")        # soften the top end
    return (smooth / np.abs(smooth).max() * 0.6).astype(np.float32)


def whoosh(length=0.35):
    n = int(length * SR); noise = np.random.default_rng(1).standard_normal(n)
    sweep = np.convolve(noise, np.ones(24) / 24, mode="same") * np.sin(np.pi * np.arange(n) / n) ** 2
    return (sweep / np.abs(sweep).max() * 0.35).astype(np.float32)


def pop():
    n = int(0.09 * SR); t = np.arange(n) / SR
    f = 500 + 900 * t / t[-1]
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.03) * 0.4).astype(np.float32)


def boom(length=0.5):
    """A crash: a low noise burst with a thump that sinks from 110 to 45 Hz."""
    n = int(length * SR); t = np.arange(n) / SR; noise = np.convolve(np.random.default_rng(2).standard_normal(n), np.ones(24) / 24, mode="same")
    f = 110 - 65 * t / t[-1]; thump = np.sin(2 * np.pi * np.cumsum(f) / SR)
    w = (noise * 0.8 + thump) * env(n, 0.003, 0.18)
    return (w / np.abs(w).max() * 0.5).astype(np.float32)


def thud(length=0.22):
    """A landing: a short sine drop from 90 to 40 Hz with a touch of noise."""
    n = int(length * SR); t = np.arange(n) / SR; f = 90 - 50 * t / t[-1]
    w = (np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.15 * np.random.default_rng(3).standard_normal(n)) * env(n, 0.002, 0.07)
    return (w / np.abs(w).max() * 0.4).astype(np.float32)


NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
hz = lambda n: 440 * 2 ** ((NOTE[n[0]] + 12 * (int(n[1:]) - 4) - 9) / 12)   # 'E5' -> its pitch


def pluck(f, length=0.32, bright=1.0):
    """A mallet note, like a marimba: the pitch and two quick overtones."""
    t = np.arange(int(length * SR)) / SR
    return (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.11) + 0.45 * bright * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.05)
            + 0.2 * bright * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.025)) * np.minimum(1, t / 0.004)


def story_music(bpm=126):
    """The story serial's own tune (the owner, 2026-11-14: music like the blocky-game story videos): a bouncy original in C,
    sixteen bars that loop: an oom-pah bass, off-beat mallet chords, a skipping mallet melody, kick, clap and hats.
    Written here note by note: no sample and no existing song is used."""
    beat = 60 / bpm; e = beat / 2; bars = 16; n = int(bars * 4 * beat * SR); out = np.zeros(n + SR); rng = np.random.default_rng(7)

    def put(w, at, vol):
        s = int(at * SR); out[s:s + len(w)] += vol * w
    chords = {"C": ("C3", "G3", ["C4", "E4", "G4"]), "Am": ("A2", "E3", ["A3", "C4", "E4"]), "F": ("F2", "C3", ["F3", "A3", "C4"]), "G": ("G2", "D3", ["G3", "B3", "D4"])}
    tune = ["E5 G5 C6 G5 E5 G5 A5 G5", "E5 A5 C6 A5 E5 A5 G5 E5", "F5 A5 C6 A5 F5 A5 G5 F5", "D5 G5 B5 G5 D5 G5 A5 B5",
            "C6 - G5 E5 G5 - C6 -", "A5 - E5 C5 E5 - A5 -", "A5 - F5 C5 F5 A5 C6 A5", "B5 - G5 D5 G5 B5 D6 -"]
    k16 = int(.16 * SR); kick = np.sin(2 * np.pi * np.cumsum(120 - 70 * np.arange(k16) / k16) / SR) * env(k16, .002, .06)
    for b in range(bars):
        t0 = b * 4 * beat; root, fifth, tri = chords[["C", "Am", "F", "G"][b % 4]]
        for k in range(4):
            put(pluck(hz(root if k % 2 == 0 else fifth), 0.3, 0.5), t0 + k * beat, 0.55)             # oom-pah
            for nn in tri: put(pluck(hz(nn), 0.16), t0 + k * beat + e, 0.16)                          # the chord on the off-beat
            if k % 2 == 0: put(kick, t0 + k * beat, 0.6)
            else: put(np.convolve(rng.standard_normal(int(.09 * SR)), np.ones(6) / 6, "same") * env(int(.09 * SR), .001, .03), t0 + k * beat, 0.3)   # clap
            for j in range(2): put(rng.standard_normal(int(.03 * SR)) * env(int(.03 * SR), .001, .008), t0 + k * beat + j * e, 0.045 if j else 0.03)   # hats
        for k, nn in enumerate(tune[b % 8].split()):
            if nn != "-": put(pluck(hz(nn), 0.3), t0 + k * e, 0.34)
    out[:SR] += out[n:n + SR]; out = out[:n]              # (the last bar rings into the first: a clean loop)
    return (out / np.abs(out).max() * 0.7).astype(np.float32)


QUAL = {"maj7": [0, 4, 7, 11], "m7": [0, 3, 7, 10], "add9": [0, 4, 7, 14], "maj": [0, 4, 7], "sus": [0, 5, 7, 10], "6": [0, 4, 7, 9], "9": [0, 4, 10, 14]}
PROGS = [[(0, "maj7"), (9, "m7"), (5, "maj7"), (7, "sus")], [(0, "add9"), (7, "maj"), (9, "m7"), (5, "maj7")],
         [(9, "m7"), (5, "maj7"), (0, "add9"), (7, "maj")], [(5, "maj7"), (7, "6"), (4, "m7"), (9, "m7")],
         [(2, "m7"), (7, "9"), (0, "maj7"), (9, "m7")], [(0, "6"), (4, "m7"), (5, "maj7"), (7, "sus")]]
mhz = lambda m: 440 * 2 ** ((m - 69) / 12)


def score(T, holds=(), title="", seed=None):
    """A reel's own music (the owner, 2026-11-22: "the music is more unique and rounded"; the reel he chose sits at about 68 bpm with
    warm mids and a little stereo width, ours was a 126 bpm oom-pah in mono). Written for THIS reel's timeline: its own key, tempo,
    chords and motif (seeded by its title, so no two reels share a tune); a soft FM electric piano, a slow pad, a round bass and
    half-time brushed drums; the drums, bass and motif drop out under each suspense hold (narrate.py "hold") while the pad swells,
    and the last bars resolve on the home chord. -> stereo float32 (n, 2). Synthesised here, note by note."""
    import hashlib
    rng = np.random.default_rng(seed if seed is not None else int(hashlib.sha1(title.encode()).hexdigest()[:8], 16))
    key = 45 + int(rng.integers(0, 12)); prog = PROGS[int(rng.integers(0, len(PROGS)))]
    bpm = int(rng.integers(80, 97)); beat = 60 / bpm; bar = 4 * beat; n = int((T + 1) * SR)
    L = {k: np.zeros((n, 2)) for k in ("pad", "keys", "bass", "drums", "motif")}

    def put(stem, w, at, pan=0.0, vol=1.0):
        s = int(at * SR)
        if s >= n: return
        w = w[:n - s]; L[stem][s:s + len(w), 0] += vol * w * (1 - max(0, pan)); L[stem][s:s + len(w), 1] += vol * w * (1 + min(0, pan))

    def ep(f, d):                                        # a Rhodes-like tine: FM, its brightness fading fast, the body slow
        t = np.arange(int(d * SR)) / SR; idx = 1.6 * np.exp(-t / 0.25) + 0.25
        return np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t)) * np.minimum(1, t / 0.004) * np.exp(-t / 1.1) * np.minimum(1, (d - t) / 0.08)

    def pad(fs, d, cents):                               # soft saws, few overtones, a slow swell in and out
        t = np.arange(int(d * SR)) / SR; w = np.zeros(len(t))
        for f in fs:
            f = f * 2 ** (cents / 1200)
            for h in range(1, 7): w += np.sin(2 * np.pi * f * h * t + h) / h ** 1.7
        return w / len(fs) * np.minimum(1, t / 0.7) * np.minimum(1, (d - t) / 0.7)

    def bass(f, d):
        t = np.arange(int(d * SR)) / SR
        return (np.sin(2 * np.pi * f * t) + .22 * np.sin(4 * np.pi * f * t)) * np.minimum(1, t / 0.012) * np.exp(-t / 1.4) * np.minimum(1, (d - t) / 0.05)

    k16 = int(.2 * SR); kick = np.sin(2 * np.pi * np.cumsum(62 - 22 * np.arange(k16) / k16) / SR) * env(k16, .003, .09)
    brush = lambda d, r: np.convolve(rng.standard_normal(int(d * SR)), np.ones(5) / 5, "same") * env(int(d * SR), .002, r)
    motif = [(float(rng.choice([0, .5, 1, 1.5])), int(rng.integers(0, 4))) for _ in range(4)]   # (beat, chord tone): one motif, the reel's hook
    motif = sorted({m[0]: m for m in motif}.values()) + [(2.5 + .5 * int(rng.integers(0, 2)), int(rng.integers(0, 4)))]
    bars = int(T / bar) + 2
    for b in range(bars):
        t0 = b * bar; root, q = prog[b % 4]; last = t0 + bar >= T - bar   # (the closing bars: home chord, no drums)
        if last: root, q = 0, "add9"
        notes = [key + root + i for i in QUAL[q]]
        put("pad", pad([mhz(m + 12) for m in notes], bar + .7, -5), t0, -.35, .5); put("pad", pad([mhz(m + 12) for m in notes], bar + .7, 5), t0, .35, .5)
        for k, at in enumerate((0, 1.5, 2.5) if b % 2 else (0, 2)):   # (the chord on the piano, a lazy rhythm)
            for j, m in enumerate(notes): put("keys", ep(mhz(m + 12), 1.6), t0 + at * beat + .012 * j, -.15, .21 if k else .26)
        put("bass", bass(mhz(key + root - 12 if root < 7 else key + root - 24), 2 * beat), t0, 0, .3)
        put("bass", bass(mhz(key + root - 12 if root < 7 else key + root - 24), 2 * beat), t0 + 2 * beat, 0, .22)
        if not last:
            put("drums", kick, t0, 0, .3); put("drums", brush(.14, .05), t0 + 2 * beat, .1, .12)
            for e8 in range(8): put("drums", brush(.03, .008), t0 + e8 * beat / 2, .3, .035 if e8 % 2 else .02)
            if b % 4 in (1, 3):
                for at, i in motif: put("motif", ep(mhz(notes[i % len(notes)] + 24), .9), t0 + at * beat, .25, .16)
    # the arrangement: a soft start (pad and piano), the band from the second bar, everything but the pad out under a hold
    tt = np.arange(n) / SR; band = np.clip((tt - bar) / beat, 0, 1)
    swell = np.ones(n)
    for a, b in holds:
        k = np.clip(np.minimum((tt - a + .15) / .12, (b + .25 - tt) / .2), 0, 1); band *= 1 - k; swell += .45 * k * np.clip((tt - a) / max(.1, b - a), 0, 1)
    sm = lambda g: np.convolve(g, np.ones(int(.04 * SR)) / int(.04 * SR), "same")[:, None]
    band, swell = sm(band), sm(swell)
    out = L["pad"] * swell + L["keys"] + (L["bass"] + L["drums"] + L["motif"]) * band
    out = out[:int(T * SR) + SR]
    return (out / np.abs(out).max() * 0.7).astype(np.float32)


def extra(name):
    """A reel's own music, made the first time it is asked for (render.py: timeline "music")."""
    os.makedirs(ASSETS, exist_ok=True); sf.write(os.path.join(ASSETS, f"music_{name}.wav"), {"story": story_music}[name](), SR)


def main():
    os.makedirs(ASSETS, exist_ok=True)
    sf.write(os.path.join(ASSETS, "music.wav"), music(), SR)
    extra("story")
    sf.write(os.path.join(ASSETS, "sfx_whoosh.wav"), whoosh(), SR)
    sf.write(os.path.join(ASSETS, "sfx_pop.wav"), pop(), SR)
    sf.write(os.path.join(ASSETS, "sfx_boom.wav"), boom(), SR)
    sf.write(os.path.join(ASSETS, "sfx_thud.wav"), thud(), SR)
    sf.write(os.path.join(ASSETS, "sfx_tick.wav"), (tone(1800, 0.05, 0.01) * 0.25).astype(np.float32), SR)
    sf.write(os.path.join(ASSETS, "sfx_chime.wav"), ((tone(880, 0.6, 0.15) + tone(1320, 0.6, 0.15)) * 0.2).astype(np.float32), SR)
    print("wrote", ", ".join(sorted(f for f in os.listdir(ASSETS) if f.endswith(".wav"))))


def demo():
    a, b = score(20, [(10, 11.4)], "Coins Melt"), score(20, [], "The Panic That Never Came")
    assert a.shape[1] == 2 and 20 * SR <= len(a) <= 21 * SR and np.abs(a).max() <= .71
    assert not np.allclose(a[:len(b)], b[:len(a)])                    # (another title, another tune)
    def low(x, s, e):                                    # (energy under 150 Hz: the bass and the kick)
        m = x[int(s * SR):int(e * SR)].mean(1); F = np.abs(np.fft.rfft(m)) ** 2; f = np.fft.rfftfreq(len(m), 1 / SR)
        return float(F[f < 150].sum())
    assert low(a, 10.3, 11.2) < 0.5 * low(score(20, [], "Coins Melt"), 10.3, 11.2)   # (under a beat the band drops out, the pad stays)
    print("ok")


if __name__ == "__main__":
    import sys
    demo() if sys.argv[1:] == ["demo"] else main()
