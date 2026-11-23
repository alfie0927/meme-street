"""What a reel's sound is made of, measured (no listening): voice level against the music in the gaps, whether there is a beat and
at what tempo, how much low end and top end the music has, its key. python3 audio_probe.py <file> [<file> ...]
With --speech first: how the voice paces itself (words a second, how many pauses and how long). That one needs the transcriber."""
import sys, subprocess, numpy as np
SR = 22050
def load(p):
    return np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout, np.float32).astype(np.float64)
def db(x): return 20 * np.log10(max(x, 1e-9))
def probe(p):
    a = load(p); n = 1024; hop = 512; fr = np.lib.stride_tricks.sliding_window_view(a, n)[::hop] * np.hanning(n); S = np.abs(np.fft.rfft(fr, axis=1)); f = np.fft.rfftfreq(n, 1 / SR)
    rms = np.sqrt((fr ** 2).mean(1)) + 1e-9; order = np.argsort(rms); lo = order[int(.03 * len(order)):int(.12 * len(order))]; hi = order[int(.6 * len(order)):]
    quiet = S[lo].mean(0); loud = S[hi].mean(0)
    band = lambda X, a_, b_: float((X[(f >= a_) & (f < b_)] ** 2).sum() / (X ** 2).sum())
    # beat: spectral flux, autocorrelation between 60 and 180 bpm
    flux = np.maximum(0, np.diff(np.log1p(30 * S), axis=0)).sum(1); flux -= flux.mean(); ac = np.correlate(flux, flux, "full")[len(flux) - 1:]; ac /= ac[0]
    lag = lambda bpm: 60 / bpm * SR / hop; ks = np.arange(int(lag(180)), int(lag(60)) + 1); k = ks[np.argmax(ac[ks])]
    # key: chroma of the quiet frames (the music alone)
    ch = np.zeros(12)
    for i, fq in enumerate(f):
        if 80 < fq < 2000: ch[int(round(12 * np.log2(fq / 261.63))) % 12] += quiet[i] ** 2
    maj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]); mnr = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    best = max(((np.corrcoef(np.roll(pr, r), ch)[0, 1], "C C# D D# E F F# G G# A A# B".split()[r] + (" major" if pr is maj else " minor")) for r in range(12) for pr in (maj, mnr)))
    print(f"{p}\n  length {len(a) / SR:.1f}s | loud frames (voice+music) {db(rms[hi].mean()):.1f} dB, quiet frames (music in the gaps) {db(rms[lo].mean()):.1f} dB -> music sits {db(rms[hi].mean()) - db(rms[lo].mean()):.1f} dB under the voice"
          f"\n  beat: {60 / (k * hop / SR):.0f} bpm, strength {ac[k]:.2f} (0 = none, >0.25 = a clear pulse) | gaps: under 120 Hz {100 * band(quiet, 0, 120):.0f}%, 120-500 Hz {100 * band(quiet, 120, 500):.0f}%, 500-2k {100 * band(quiet, 500, 2000):.0f}%, over 2 kHz {100 * band(quiet, 2000, 11025):.0f}% | centroid {float((f * quiet ** 2).sum() / (quiet ** 2).sum()):.0f} Hz | key guess {best[1]} ({best[0]:.2f})")
def speech(p):
    """How the voice in a video paces itself (needs the transcriber: run it on the reel server). A narrator people watch
    (the owner's model reel, 2026-11-23): 3.7 words a second, a pause every 5 or 6 words, median 0.28 s, few over 0.3 s.
    Ours before that day: 2.6 words a second, every pause over 0.3 s, median 0.62 s."""
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")); from voice import words
    W = words(p); g = sorted(b[1] - a[2] for a, b in zip(W, W[1:]) if b[1] - a[2] >= .12); n = len(W)
    print(f"{p}\n  {n} words in {W[-1][2] - W[0][1]:.1f}s = {n / (W[-1][2] - W[0][1]):.2f} words a second | pauses of 0.12 s or more: {len(g)} ({100 * len(g) / n:.0f} per 100 words), "
          f"median {g[len(g) // 2] if g else 0:.2f} s, longest {g[-1] if g else 0:.2f} s | of 0.3 s or more: {sum(x >= .3 for x in g)} ({100 * sum(x >= .3 for x in g) / n:.0f} per 100 words)")
if sys.argv[1:2] == ["--speech"]: [speech(p) for p in sys.argv[2:]]
else: [probe(p) for p in sys.argv[1:]]
