"""Ears for a maker who cannot hear: measure a sound effect, say whether it is the sound it is meant to be, and why.

WHY. "Claude can't hear, so its sound effects were terrible": the maker of these reels picks a file named pop.wav and has no
way to know that it is a three-second synthesiser beep with a click at the end. This file is the check that stands in for
listening. It measures a WAV and JUDGES it against what its kind should be (a pop is a short single hit, a whoosh is a swell
of noise with no pitch, a ding rings at a pitch, rain is steady noise), and it flags the faults and the fakes a number can
show: a bare oscillator where a real object is expected, hard clipping, a tail cut off, a silent lead-in that makes the hit
land late, hiss under a sound that should end clean.

  python ears.py <file.wav> [kind]     one file -> JSON: fits (true / false), reasons, notes, score, sounds_like, sync_s, measures
  python ears.py lib <manifest.json>   every file of a library against its own kind; the manifest is rewritten with the results
  python ears.py demo                  self-check, needs no files: a click, a sine beep, noise and a clipped tone, made here
  python ears.py kinds                 what each kind is expected to be

  from ears import listen, hear        listen(path, kind) for a file; hear(samples, rate, kind) for an array
Without a kind only the faults are judged. It always exits 0 when it could judge: read "fits". numpy and the standard library
only; WAV is read with the wave module (a float WAV falls back to soundfile where that is installed).

WHAT COMES BACK. fits; reasons (why not, in words); notes (worth knowing, not a refusal: "99 % of its energy is under 250 Hz:
a phone's speaker will hardly play it"); score (1-100 among files that fit: how far inside the kind's limits it sits, the best
file of a kind first); sounds_like (one line: "0.23 s, one fast hit, mid-coloured (660 Hz), noise"); sync_s (the second of the
file that belongs on the picture's frame: the onset of a hit, the peak of a swell); measures.

WHAT IS MEASURED. length; peak, RMS and crest factor; DC offset; noise floor (the quietest tenth of its 20 ms pieces); the silent
lead-in, the onset, where the peak is, the silent tail, a dead gap inside; attack (onset to 90 % of the peak) and decay (peak to
the last moment within 20 dB of it); how long the loud part is and how many separate hits there are; how steady the level is;
the level of the last 10 ms (a cut tail); clipping (flat tops) and the crest of each short piece (a square wave or a squashed
one is flat, a bare sine sits at 3 dB); spectral centroid, 85 % roll-off, how high the content reaches, the energy under 250 Hz
and over 4 kHz (dark / bright); spectral flatness (noise against tone); how much of the energy sits in a few pure lines, the
dominant pitch, how steady it is, which way it moves and whether it goes one way; how empty the spectrum is between the lines;
zero crossings a second.

WHERE THE IDEAS COME FROM. earshot (github.com/Leonxlnx/earshot, MIT), the tool the reel calls "ears". Its real listening is a
1.1 GB sound-and-text model (CLAP) and is NOT used here. What is taken from it is its model-free half: the measurements "a
synthesizer leaves behind" of earshot/realness.py (energy in a few pure spectral lines, no noise between them, a dead-steady
pitch) with its pure-tone rule, the audit earshot runs on its own renders (clicks, cut tails, clipping, DC), and the reading
rules of its real-sound skill (noise floor = the quiet tenth of the 20 ms pieces, the attack, the centroid). Nothing of
earshot is imported or copied; the kind table and its limits are this file's own.

THE LIMITS, plainly. Numbers say what a sound is SHAPED like, not what it IS. A door slam and a book dropped on a desk measure
the same; so do a real click and a burst of random numbers (the demo's click passes, and it is made of random numbers). earshot
itself found its measurements added nothing to its model's judgement. So "fits" means "nothing measurable says no": it catches
the wrong length, the wrong shape, the wrong colour, the broken file and the bare oscillator, and it cannot catch a cheesy,
ugly or simply wrong recording. The kind limits are deliberately loose and were set against about 180 public-domain recordings,
by a maker who has not heard any of them. Pitch under about 90 Hz is not seen (a hum and a rumble look alike in 46 ms), so a
synthesised sine boom passes. The bare-oscillator rule rests on one thing, the emptiness between the lines: it caught three of
three known synthesiser coins, and it also refused one hand bell recorded on a phone (a noise gate leaves the same emptiness).
Sounds that are electronic by nature (buzz, wrong, correct, rise, drop, riser) are let through with a note.
Clipping that a lossy codec has smeared is seen only when it left the wave flat. A person's ear outranks every line here.
"""
import json, math, os, sys, wave
import numpy as np

db = lambda v: round(20 * math.log10(max(float(v), 1e-10)), 1)


def read(path):
    """A WAV as mono floats in -1..1 and its sample rate."""
    try:
        with wave.open(path, "rb") as f: ch, wd, sr, raw = f.getnchannels(), f.getsampwidth(), f.getframerate(), f.readframes(f.getnframes())
    except (wave.Error, EOFError):                                   # float or odd WAV: the wave module reads plain PCM only
        try: import soundfile as sf
        except ImportError: raise SystemExit(f"{path}: not a PCM WAV, and soundfile is not installed to read it")
        x, sr = sf.read(path, dtype="float64", always_2d=True); return x.mean(1), sr
    if wd == 1: x = (np.frombuffer(raw, np.uint8).astype(np.float64) - 128) / 128
    elif wd == 2: x = np.frombuffer(raw, "<i2") / 32768
    elif wd == 4: x = np.frombuffer(raw, "<i4") / 2147483648
    else: b = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.int32); v = b[:, 0] | b[:, 1] << 8 | b[:, 2] << 16; x = np.where(v >= 1 << 23, v - (1 << 24), v) / 8388608
    return x.reshape(-1, ch).mean(1), sr


def measure(x, sr):
    """Every number the judgement rests on. Times in seconds, levels in dB, shares in percent."""
    x = np.asarray(x, np.float64); n = len(x); a = np.abs(x); peak = float(a.max()) if n else 0.0
    m = dict(seconds=round(n / sr, 3), sample_rate=int(sr))
    if n < .01 * sr or peak < 1e-4: return dict(m, silent=True)
    T = lambda i: round(float(i) / sr, 4); rms = float(np.sqrt((x * x).mean()))
    m.update(peak_db=db(peak), rms_db=db(rms), crest_db=round(db(peak) - db(rms), 1), dc_pct=round(100 * abs(float(x.mean())) / peak, 2))
    # the shape in time, to the sample: 1 % of the peak = the sound has begun, 10 % = the onset, 90 % = the attack is done
    i1, i10, i90, ipk = (int(np.argmax(a > .01 * peak)), int(np.argmax(a > .1 * peak)), int(np.argmax(a >= .9 * peak)), int(np.argmax(a)))
    j10, j0 = n - 1 - int(np.argmax(a[::-1] > .1 * peak)), n - 1 - int(np.argmax(a[::-1] > .003 * peak))
    m.update(lead_silence_s=T(i1), onset_s=T(i10), peak_at_s=T(ipk), peak_at_pct=round(100 * ipk / n), attack_s=T(i90 - i10), decay_s=T(j10 - ipk),
             body_s=T(j10 - i10), trail_silence_s=T(n - 1 - j0))
    # in 1 ms steps: the largest sample and the energy of each; from them 5 ms, 10 ms, 20 ms and 100 ms pieces
    h = max(1, int(round(sr / 1000))); nb = n // h; blk = a[: nb * h].reshape(nb, h); bm, be = blk.max(1), (blk * blk).mean(1)
    pieces = lambda v, k, f: f(v[: len(v) // k * k].reshape(-1, k), 1) if len(v) >= k else f(v[None, :], 1)
    hold = np.max([bm[i: nb - 4 + i] for i in range(5)], 0) > .1 * peak                       # within 20 dB of the peak, held 5 ms
    on = np.flatnonzero(hold); m["events"] = int(1 + (np.diff(on) > 50).sum())                # a gap of 50 ms makes it another hit
    e10 = np.sqrt(np.convolve(be, np.ones(10) / 10, "valid")) if nb >= 10 else np.sqrt(be); m["end_db"] = round(db(e10[-1]) - db(e10.max()), 1)
    e20 = np.sqrt(pieces(be, 20, np.mean)); m["noise_floor_db"] = db(np.percentile(e20, 10)); m["floor_rel_db"] = round(m["noise_floor_db"] - db(e20.max()), 1)
    q = np.flatnonzero(np.diff(np.r_[0, (bm[i1 // h: j0 // h + 1] < .003 * peak).astype(np.int8), 0])); m["gap_s"] = round(float((q[1::2] - q[::2]).max()) * h / sr, 3) if len(q) else 0.0
    lv = np.sqrt(pieces(be[i1 // h: j0 // h + 1], 100, np.mean)); lv = lv[1:-1] if len(lv) > 6 else lv
    m["level_std_db"] = round(float(np.std(20 * np.log10(lv + 1e-9))), 1) if len(lv) >= 4 else None
    m["zcr_hz"] = int(np.count_nonzero(np.diff(np.signbit(x[i1: j0 + 1]))) / max((j0 - i1) / sr, 1e-3))
    pc = int(min(100, max(20, math.ceil(3000 / max(m["zcr_hz"] / 2, 20))))); ep = np.sqrt(pieces(be, pc, np.mean))       # a piece: 20 ms, or three periods of a low wave
    m["piece_crest_db"] = round(float(np.median((20 * np.log10((pieces(bm, pc, np.max) + 1e-12) / (ep + 1e-12)))[ep > ep.max() * .25])), 1)
    # the spectrum: 46 ms pieces, a quarter apart, 40 Hz to 15 kHz (a lossy codec's own cut-off stays out of it)
    N = 2 ** int(round(math.log2(sr * .046))); hop = N // 4; nf = 1 + max(0, int(math.ceil((n - N) / hop)))
    xp = np.r_[x, np.zeros(max(0, (nf - 1) * hop + N - n))]; S = np.abs(np.fft.rfft(xp[np.arange(N)[None, :] + hop * np.arange(nf)[:, None]] * np.hanning(N), axis=1)) ** 2
    fq = np.fft.rfftfreq(N, 1 / sr); k0, k1 = int(np.searchsorted(fq, 40)), int(np.searchsorted(fq, min(15000, .45 * sr))); B = S[:, k0:k1]; fb = fq[k0:k1]
    E = B.sum(1); act = E > E.max() * 1e-3; loud = E > E.max() * 1e-2; P = B[act].mean(0); tot = P.sum(); cum = np.cumsum(P)
    flat = lambda R: np.exp(np.log(R + 1e-12 * R.max(1, keepdims=True) + 1e-300).mean(1)) / (R.mean(1) + 1e-300)
    # flatness and emptiness are read only up to where the sound itself reaches (99.9 % of its energy, 2 kHz at least): a recording
    # that a codec or an old recorder cut off at 4 kHz must not look "empty" for the band it never had
    kt = min(len(fb), max(int(np.searchsorted(cum, .999 * tot)) + 1, int(np.searchsorted(fb, 2000)))); Bt = B[:, :kt]
    m.update(centroid_hz=int((fb * P).sum() / tot), rolloff_hz=int(fb[min(len(fb) - 1, int(np.searchsorted(cum, .85 * tot)))]), top_hz=int(fb[kt - 1]),
             low_pct=round(100 * P[fb < 250].sum() / tot), high_pct=round(100 * P[fb >= 4000].sum() / tot), flatness=round(float(np.median(flat(Bt[act]))), 4))
    quiet = (E > E.max() * 1e-9) & (E <= np.percentile(E, 25)); m["quiet_flatness"] = round(float(np.median(flat(Bt[quiet]))), 4) if quiet.any() else None
    m["between_lines_db"] = round(float(np.median(10 * np.log10(np.percentile(Bt[loud], 10, axis=1) / Bt[loud].max(1) + 1e-20))), 1)
    # pure lines: a peak that stands 15 dB over the spectrum 4 bins to each side; up to five a piece, the strongest is the pitch
    share, f0 = [], []
    for row, e in zip(S[act], E[act]):
        used, s = [], 0.0
        for k in np.argsort(row[k0:k1])[::-1][:16] + k0:
            if len(used) == 5: break
            if k < 4 or k > len(row) - 5 or any(abs(k - u) <= 4 for u in used) or row[k] < row[k - 1] or row[k] < row[k + 1]: continue
            if row[k] < 30 * row[k - 4] or row[k] < 30 * row[k + 4]: continue
            used.append(k); s += row[k - 2: k + 3].sum()
        share.append(min(1.0, s / e))
        if used and s / e >= .3:
            k = used[0]; l0, l1, l2 = np.log(row[k - 1: k + 2] + 1e-300); f0.append((k + .5 * (l0 - l2) / (l0 - 2 * l1 + l2 - 1e-12)) * sr / N)
        else: f0.append(np.nan)
    f0 = np.array(f0); ok = f0[np.isfinite(f0)]; m["tonal_pct"] = round(100 * float(np.median(share)))
    m.update(pitch_hz=None, pitch_drift_cents=None, pitch_move_st=None, pitch_bend_st=None, pitched_pct=round(100 * len(ok) / len(f0)))
    if len(ok) >= 3:
        mid = float(np.median(ok)); m["pitch_hz"] = round(mid, 1); m["pitch_drift_cents"] = round(float(np.median(np.abs(1200 * np.log2(ok / mid)))), 1)
        if len(ok) >= 6:                                                 # thirds: where the pitch starts, passes and ends, in semitones
            t = len(ok) // 3; p0, p1, p2 = (12 * math.log2(np.median(v)) for v in (ok[:t], ok[t: len(ok) - t], ok[-t:]))
            m["pitch_move_st"] = round(p2 - p0, 1); m["pitch_bend_st"] = round(max(0.0, min(p0, p2) - p1, p1 - max(p0, p2)), 1)
    # flat tops: three samples or more at the very peak, and more of them than a pure wave of this pitch would rest there
    f_low = min(m["pitch_hz"] or 1e9, max(m["zcr_hz"] / 2, 20)); need = max(3, int(math.ceil(3 * .0064 * sr / f_low)))
    top = np.flatnonzero(np.diff(np.r_[0, (a >= peak * (1 - 2e-4)).astype(np.int8), 0])); m["clipped_runs"] = int(((top[1::2] - top[::2]) >= need).sum())
    return m


# ------------------------------------------------------------------------------------------------ what each kind should be
# want: (measure, at least, at most). anchor: the moment the mixer puts on the picture's frame: the "onset" of a hit (a late one
# is a fault), the "peak" of a swell, the "start" of a bed or a texture. clean: a hit that ends in silence (hiss under it is a
# fault; its anchor is the onset). synth: electronic by nature, so a bare tone is a note and not a fault.
# cut: it may stop dead (a buzzer does, a riser ends on its peak).
K = lambda say, want, anchor=None, clean=False, synth=False, cut=False: dict(say=say, want=want, anchor=anchor or ("onset" if clean else "start"), clean=clean, synth=synth, cut=cut)
KINDS = {
    "pop": K("one short hit: fast attack, the loud part under a quarter second, no long tail",
             [("body_s", None, .25), ("seconds", None, .8), ("attack_s", None, .033), ("events", None, 2)], clean=True),
    "click": K("one very short hit: its peak within a frame of its onset, over in a tenth of a second",
               [("body_s", None, .12), ("seconds", None, .5), ("attack_s", None, .033), ("events", None, 2)], clean=True),
    "tick": K("one very short hit, like a clock's: its peak within a frame of its onset, over in a tenth of a second",
              [("body_s", None, .12), ("seconds", None, .5), ("attack_s", None, .033), ("events", None, 2)], clean=True),
    "snap": K("one short bright hit: instant attack, energy well above 1 kHz",
              [("body_s", None, .3), ("seconds", None, .9), ("attack_s", None, .033), ("centroid_hz", 1000, None), ("events", None, 2)], clean=True),
    "thud": K("one dull hit: fast attack, its energy low, short",
              [("body_s", None, .6), ("seconds", None, 2.0), ("attack_s", None, .05), ("centroid_hz", None, 900), ("events", None, 2)], clean=True),
    "boom": K("a low hit with weight: fast attack, most energy in the bass, a tail",
              [("seconds", .3, 4.1), ("attack_s", None, .1), ("centroid_hz", None, 700), ("low_pct", 30, None)], clean=True),
    "ding": K("a struck note: fast attack, a clear pitch, it rings on",
              [("seconds", .25, 4.1), ("attack_s", None, .033), ("tonal_pct", 45, None), ("pitch_hz", 250, 6000), ("decay_s", .1, None)], clean=True),
    "bell": K("a struck bell: fast attack, pitched partials, a long ring",
              [("seconds", .5, 4.1), ("attack_s", None, .06), ("tonal_pct", 35, None), ("pitch_hz", 150, 6000), ("decay_s", .25, None)], clean=True),
    "coin": K("small bright metal: a hit or a few bounces, its energy high up", [("seconds", .08, 3.1), ("attack_s", None, .2), ("centroid_hz", 2500, None)], clean=True),
    "sparkle": K("bright ringing, like chimes: energy high up, pitched", [("seconds", .3, 4.1), ("centroid_hz", 2000, None), ("tonal_pct", 20, None)]),
    "whoosh": K("a swell of air noise: it rises to its peak and falls away, no hit in it, no clear pitch, not all bass",
                [("seconds", .2, 2.6), ("attack_s", .008, None), ("peak_at_pct", 8, 92), ("tonal_pct", None, 40), ("low_pct", None, 80), ("events", None, 2)], anchor="peak"),
    "swish": K("a short quick swell of air noise: no hit in it, no clear pitch, not all bass",
               [("seconds", .1, 1.0), ("attack_s", .008, None), ("peak_at_pct", 8, 92), ("tonal_pct", None, 40), ("low_pct", None, 80), ("events", None, 2)], anchor="peak"),
    "rise": K("a pitch that slides up", [("seconds", .3, 3.1), ("tonal_pct", 35, None), ("pitch_move_st", 4, None), ("pitch_bend_st", None, 1.5)], anchor="onset", synth=True),
    "drop": K("a pitch that slides down", [("seconds", .3, 3.1), ("tonal_pct", 35, None), ("pitch_move_st", None, -4), ("pitch_bend_st", None, 1.5)], anchor="onset", synth=True),
    "riser": K("a build: it grows to its loudest moment near the end", [("seconds", .5, 4.1), ("peak_at_pct", 55, None), ("attack_s", .2, None)], anchor="peak", synth=True, cut=True),
    "crumble": K("many small hits of rubble: noise, rough, no pitch", [("seconds", .4, 4.1), ("tonal_pct", None, 35), ("crest_db", 12, None)]),
    "buzz": K("a harsh held sound, like a buzzer: it lasts, low and mid, not bright", [("seconds", .15, 2.1), ("body_s", .12, None), ("centroid_hz", None, 3000)], anchor="onset", synth=True, cut=True),
    "wrong": K("a wrong-answer buzzer: a harsh held sound, low and mid", [("seconds", .15, 2.6), ("body_s", .12, None), ("centroid_hz", None, 3000)], anchor="onset", synth=True, cut=True),
    "correct": K("a right-answer chime: clear pitched notes", [("seconds", .15, 2.6), ("tonal_pct", 35, None), ("pitch_hz", 350, 6000)], anchor="onset", synth=True),
    "crowd_cheer": K("a crowd cheering: noise that lasts, no single pitch, no single hit",
                     [("seconds", 2.0, 8.1), ("tonal_pct", None, 35), ("level_std_db", None, 7), ("crest_db", None, 24)]),
    "crowd_gasp": K("many people breathing in at once: a soft swell of noise", [("seconds", .4, 4.1), ("tonal_pct", None, 40), ("attack_s", .02, None)], anchor="peak"),
    "cash_register": K("a till: bright mechanical hits and a ring", [("seconds", .3, 4.1), ("centroid_hz", 1500, None), ("attack_s", None, .3)], anchor="onset"),
    "paper": K("paper moving: bright rustling noise, no pitch", [("seconds", .15, 4.1), ("centroid_hz", 1500, None), ("tonal_pct", None, 35)]),
    "engine_start": K("an engine turning over and catching: it lasts, its energy low and mid", [("seconds", 1.5, 8.1), ("centroid_hz", None, 3000), ("body_s", .8, None)]),
    "car_pass": K("a car going by: noise that swells and falls away", [("seconds", 1.5, 4.6), ("peak_at_pct", 15, 85), ("tonal_pct", None, 45)], anchor="peak"),
    "thunder": K("thunder: a low rumble that rolls on", [("seconds", 1.5, 4.6), ("centroid_hz", None, 900), ("low_pct", 25, None), ("body_s", .5, None)]),
    "rain": K("rain: steady noise, no pitch, no single hit", [("seconds", 3.0, 8.1), ("tonal_pct", None, 25), ("level_std_db", None, 3.5), ("crest_db", None, 20), ("flatness", .01, None)]),
    "rope_creak": K("a rope straining: a drawn-out creak, not a hit", [("seconds", .3, 4.1), ("body_s", .15, None)], anchor="peak"),
    "slide": K("something sliding: a drawn-out scrape of noise, not a hit", [("seconds", .2, 3.1), ("body_s", .12, None), ("tonal_pct", None, 45)], anchor="peak"),
    "typing": K("typing: a run of small bright clicks", [("seconds", 1.0, 4.1), ("events", 4, None), ("centroid_hz", 800, None), ("tonal_pct", None, 40)]),
    "camera_shutter": K("a shutter: one or two short bright mechanical clicks",
                        [("seconds", None, 1.6), ("body_s", None, .6), ("attack_s", None, .3), ("centroid_hz", 1500, None), ("events", None, 4)], clean=True),
    "glass": K("glass: a bright sharp hit, energy high up", [("seconds", .15, 4.1), ("attack_s", None, .08), ("centroid_hz", 1500, None)], anchor="onset"),
    "door": K("a door shutting: a hit with body, not bright", [("seconds", .15, 3.1), ("centroid_hz", None, 3000), ("attack_s", None, .6)], anchor="onset"),
}
WORDS = dict(seconds=("its length", "{:.2f} s"), body_s=("its loud part (within 20 dB of the peak)", "{:.2f} s"), attack_s=("its attack (onset to peak)", "{:.3f} s"),
             decay_s=("its ring (peak to 20 dB down)", "{:.2f} s"), centroid_hz=("its brightness (spectral centroid)", "{:.0f} Hz"), low_pct=("its energy under 250 Hz", "{:.0f} %"),
             tonal_pct=("its energy in pure pitched lines", "{:.0f} %"), pitch_hz=("its pitch", "{:.0f} Hz"), pitch_move_st=("the slide of its pitch", "{:+.1f} semitones"),
             pitch_bend_st=("the detour of its pitch (how far its middle leaves the way from start to end)", "{:.1f} semitones"),
             peak_at_pct=("where its loudest moment sits", "{:.0f} % of the way in"), events=("its number of separate hits", "{:.0f}"), level_std_db=("the wobble of its level", "{:.1f} dB"),
             crest_db=("its crest factor (peak over average)", "{:.1f} dB"), flatness=("its spectral flatness (1 = pure noise)", "{:.3f}"))


def room(v, lo, hi):
    """How far inside its limits a value sits: below 0 = outside, 1 = half the limit to spare."""
    r = [(v - lo) / (abs(lo) * .5 + 1e-9)] if lo is not None else []
    return max(-1.0, min([1.0] + r + ([(hi - v) / (abs(hi) * .5 + 1e-9)] if hi is not None else [])))


def judge(m, kind=None):
    """(fits, reasons, notes, score): the faults any sound may have, then what this kind should be."""
    if m.get("silent"): return False, ["it is silent or shorter than 10 ms"], [], 0
    k = KINDS[kind] if kind else None; bad, note, rooms = [], [], []
    hit = bool(k and k["anchor"] == "onset"); synth = bool(k and k["synth"]); fps = 30
    # ---- faults
    if m["clipped_runs"] >= 2: bad.append(f"hard clipping: the wave sits flat at its peak {m['clipped_runs']} times")
    if m["piece_crest_db"] <= 2.0 and not synth: bad.append(f"its wave is flat-topped (peak only {m['piece_crest_db']} dB over its average): a square wave or a clipped one, not a recorded thing")
    elif m["piece_crest_db"] <= 2.0: note.append("a square wave (electronic, as this kind may be)")
    empty = m["between_lines_db"] <= -85; fake = None                                        # no room, no microphone noise, no object around the tone
    if empty and m["pitch_hz"] and m["tonal_pct"] >= 85 and m["pitched_pct"] >= 80 and m["pitch_drift_cents"] <= 3:
        fake = (f"a bare oscillator: {m['tonal_pct']} % of the energy in a few pure lines at {m['pitch_hz']:.0f} Hz, pitch steady to {m['pitch_drift_cents']} cents, "
                f"nothing between the lines down to {m['between_lines_db']} dB (no room, no microphone, no object)")
    elif empty and 2.0 < m["piece_crest_db"] <= 3.6:
        fake = (f"a bare sine wave: its peak stays {m['piece_crest_db']} dB over its level, as a pure sine's does (3.0), and the spectrum around it is empty "
                f"down to {m['between_lines_db']} dB (no room, no microphone, no object)")
    if fake and not synth: bad.append(fake)
    elif fake: note.append("a bare electronic tone (as this kind may be)")
    if m["dc_pct"] > 5: bad.append(f"DC offset: the wave sits {m['dc_pct']} % of its peak off centre (a thump where it starts and stops)")
    if m["gap_s"] >= .4: bad.append(f"a dead gap of {m['gap_s']:.2f} s inside it: more than one take in the file")
    if m["end_db"] > -20 and m["seconds"] > .05 and not (k and k["cut"]): bad.append(f"its tail is cut off: the last 10 ms are still only {-m['end_db']:.0f} dB under its loudest moment")
    late = m["onset_s"] if hit else 0.0 if k and k["anchor"] == "peak" else m["lead_silence_s"]     # (a swell is placed by its peak)
    if late > (.05 if hit else .3): bad.append(f"a silent lead-in of {late:.2f} s: placed on a frame it would sound {late * fps:.0f} frames late")
    elif hit and late > .02: note.append(f"its onset is {late * 1000:.0f} ms in (put sync_s, not the file's start, on the frame)")
    if m["trail_silence_s"] > .5: note.append(f"{m['trail_silence_s']:.1f} s of silence at the end")
    if k and k["clean"] and m["seconds"] >= .4 and m["floor_rel_db"] > -32 and (m["quiet_flatness"] or 0) > .1:      # (only a hit must end in silence)
        bad.append(f"hiss: its quiet parts are only {-m['floor_rel_db']:.0f} dB under its loud ones and are flat noise (flatness {m['quiet_flatness']})")
    if m["low_pct"] >= 90: note.append(f"{m['low_pct']} % of its energy is under 250 Hz: a phone's speaker will hardly play it")
    if m["peak_db"] < -30: note.append(f"very quiet (peak {m['peak_db']} dBFS): raising it raises its noise")
    # ---- the kind
    for key, lo, hi in (k["want"] if k else []):
        v = m.get(key); name, fmt = WORDS[key]
        if v is None:
            if key == "pitch_move_st": bad.append(f"no pitch that can be followed, and a {kind} is {k['say']}")
            elif key == "pitch_hz": bad.append(f"no clear pitch, and a {kind} is {k['say']}")
            continue
        r = room(v, lo, hi); rooms += [max(0.0, r)] * (key != "seconds")              # (the length is a limit, not a taste: a full-length bed is no worse)
        if r < 0: bad.append(f"{name} is {fmt.format(v)}; a {kind} needs {'at least ' + fmt.format(lo) if lo is not None and v < lo else 'at most ' + fmt.format(hi)}")
    score = 0 if bad else max(1, round(100 * (sum(rooms) / len(rooms) if rooms else 1.0)) - 8 * len(note))
    return not bad, bad, note, score


def sounds_like(m):
    """One plain line: what the numbers describe."""
    if m.get("silent"): return "silence"
    tex = (f"a tone near {m['pitch_hz']:.0f} Hz" + ("" if abs(m["pitch_move_st"] or 0) < 2 else " sliding up" if m["pitch_move_st"] > 0 else " sliding down")
           if m["tonal_pct"] >= 60 and m["pitch_hz"] else "a low rumble" if m["low_pct"] >= 60 else "noise" if m["tonal_pct"] < 25 else "noise with some ring in it")
    col = "dark" if m["centroid_hz"] < 500 else "bright" if m["centroid_hz"] > 2500 else "mid-coloured"
    shape = ("a steady bed" if m["seconds"] >= 2 and (m["level_std_db"] or 9) <= 3.5 else f"{m['events']} hits" if m["events"] > 1 else
             "one fast hit" if m["attack_s"] <= .033 and m["body_s"] <= .6 else "a fast hit with a tail" if m["attack_s"] <= .033 else f"its peak {m['attack_s']:.2f} s after its onset")
    return f"{m['seconds']:.2f} s, {shape}, {col} ({m['centroid_hz']} Hz), {tex}"


def hear(x, sr, kind=None):
    if kind and kind not in KINDS: raise SystemExit(f"no such kind: {kind}. Kinds: {', '.join(KINDS)}")
    m = measure(x, sr); fits, bad, note, score = judge(m, kind)
    anchor = KINDS[kind]["anchor"] if kind else "onset"                                       # the second of the file that belongs on the picture's frame
    sync = None if m.get("silent") else m[dict(onset="onset_s", peak="peak_at_s", start="lead_silence_s")[anchor]]
    return dict(kind=kind, fits=fits, score=score, reasons=bad, notes=note, sounds_like=sounds_like(m), sync_s=sync, measures=m)


def listen(path, kind=None):
    return dict(file=path, **hear(*read(path), kind=kind))


def lib(manifest):
    """Every file of a library against its kind; the results go into the manifest, which is rewritten."""
    d = json.load(open(manifest, encoding="utf-8")); files = d["files"] if isinstance(d, dict) else d; base = os.path.dirname(os.path.abspath(manifest)); no = 0
    for e in files:
        p = os.path.join(base, e["file"])
        r = listen(p, e.get("kind")) if os.path.exists(p) else dict(fits=False, score=0, reasons=["the file is missing"], notes=[], sounds_like=None, sync_s=None, measures={})
        e.update(seconds=r["measures"].get("seconds", e.get("seconds")), fits=r["fits"], score=r["score"], reasons=r["reasons"], notes=r["notes"], sounds_like=r["sounds_like"],
                 sync_s=r["sync_s"], ears=r["measures"]); no += not r["fits"]
        print(f"{'ok  ' if r['fits'] else 'NO  '}{r['score']:3d}  {e.get('kind') or '-':15s} {e['file']:28s} {'; '.join(r['reasons'])[:150] or r['sounds_like']}")
    json.dump(d, open(manifest, "w", encoding="utf-8"), indent=1); print(f"{len(files) - no} fit, {no} do not ({manifest} rewritten)")
    return d


def demo():
    """Self-check with sounds made here: what must pass passes, what must fail fails, and for the stated reason."""
    sr = 44100; rng = np.random.default_rng(7); t = lambda s: np.arange(int(s * sr)) / sr; bits = lambda x: np.round(x * 32767) / 32768       # as a 16 bit file holds it
    edge = lambda x, s=.005: bits(x * np.minimum(1, np.minimum(np.arange(len(x)), np.arange(len(x))[::-1]) / (s * sr)))
    click = bits(rng.standard_normal(int(.04 * sr)) * np.exp(-150 * t(.04)) * .25)
    beep = bits(np.sin(2 * np.pi * 880 * t(.5)) * np.exp(-12 * t(.5)) * .7)                      # the "ding" a script makes: a sine that dies away
    noise = edge(rng.standard_normal(int(4 * sr)), .3) * .2
    clipped = edge(np.clip(4 * np.sin(2 * np.pi * 220 * t(.5)), -1, 1)) * .9
    square = edge(np.sign(np.sin(2 * np.pi * 110 * t(.3)))) * .6
    says = lambda r, word: any(word in s for s in r["reasons"])
    r = hear(click, sr, "click"); assert r["fits"] and r["measures"]["attack_s"] < .005 and r["measures"]["seconds"] < .05, r
    r = hear(beep, sr, "ding"); assert not r["fits"] and says(r, "bare oscillator") and abs(r["measures"]["pitch_hz"] - 880) < 2, r
    r = hear(beep, sr, "correct"); assert r["fits"], r                                          # electronic by nature: a note, not a fault
    r = hear(noise, sr, "rain"); assert r["fits"] and r["measures"]["flatness"] > .3 and r["measures"]["tonal_pct"] < 20, r
    r = hear(noise, sr, "ding"); assert not r["fits"] and says(r, "pitch"), r
    r = hear(noise, sr, "pop"); assert not r["fits"] and says(r, "its loud part"), r
    r = hear(clipped, sr); assert not r["fits"] and says(r, "clipping") and says(r, "flat-topped"), r
    r = hear(square, sr, "thud"); assert not r["fits"] and says(r, "flat-topped"), r
    r = hear(np.r_[np.zeros(int(.3 * sr)), click], sr, "click"); assert not r["fits"] and says(r, "lead-in"), r
    r = hear(noise[: 2 * sr], sr); assert not r["fits"] and says(r, "cut off"), r
    r = hear(click + .08, sr); assert not r["fits"] and says(r, "DC offset"), r
    r = hear(np.zeros(sr), sr, "pop"); assert not r["fits"], r
    r = hear(bits(beep + .02 * rng.standard_normal(len(beep))), sr, "ding"); assert not r["fits"] and says(r, "hiss") and not says(r, "bare"), r
    sweep = edge(np.sin(2 * np.pi * np.cumsum(300 * 2 ** (t(1.0) * 1.5)) / sr) + .002 * rng.standard_normal(sr), .1) * .5
    assert hear(sweep, sr, "rise")["fits"] and not hear(sweep[::-1], sr, "rise")["fits"] and hear(sweep[::-1], sr, "drop")["fits"]
    print("ears demo: 15 checks passed (a click, steady noise as rain and a pitch slide fit; a sine beep, a clipped tone, a square wave, "
          "a late start, a cut tail, DC and hiss are refused, each for its own reason)")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: raise SystemExit(__doc__)
    if a[0] == "demo": demo()
    elif a[0] == "kinds": print("\n".join(f"{k:15s} {v['say']}" for k, v in KINDS.items()))
    elif a[0] == "lib": lib(a[1])
    else: print(json.dumps(listen(a[0], a[1] if len(a) > 1 else None), indent=1))
