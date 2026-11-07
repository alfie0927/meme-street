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


def main():
    os.makedirs(ASSETS, exist_ok=True)
    sf.write(os.path.join(ASSETS, "music.wav"), music(), SR)
    sf.write(os.path.join(ASSETS, "sfx_whoosh.wav"), whoosh(), SR)
    sf.write(os.path.join(ASSETS, "sfx_pop.wav"), pop(), SR)
    sf.write(os.path.join(ASSETS, "sfx_boom.wav"), boom(), SR)
    sf.write(os.path.join(ASSETS, "sfx_thud.wav"), thud(), SR)
    sf.write(os.path.join(ASSETS, "sfx_tick.wav"), (tone(1800, 0.05, 0.01) * 0.25).astype(np.float32), SR)
    sf.write(os.path.join(ASSETS, "sfx_chime.wav"), ((tone(880, 0.6, 0.15) + tone(1320, 0.6, 0.15)) * 0.2).astype(np.float32), SR)
    print("wrote", ", ".join(sorted(f for f in os.listdir(ASSETS) if f.endswith(".wav"))))


if __name__ == "__main__":
    main()
