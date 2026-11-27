"""Step 7 of the studio: check every single frame (the step "everybody skips": one bad frame and the whole part is ruined).

  python check.py <reel.mp4> [out dir]      -> <out>/check.json, <out>/sheet_NN.jpg (every 3rd frame), <out>/first3.jpg; exit 1 on a fault
  python check.py demo                      self-check on two clips it makes itself

It reads EVERY frame with ffmpeg (no other dependency) and reports:
  faults   blank frame (black, white or one flat colour); a one-frame glitch (a frame unlike both its neighbours, which agree);
           nothing moving for FREEZE seconds (a still card: the eye leaves); frame 0 empty or still; wrong size, rate or length;
           no sound, sound too quiet or loud, a hole in the sound.
  warns    a long stretch without a change of picture; the loudness a little off.
Then it lays every 3rd frame out on contact sheets, and the first three seconds frame by frame, for the eye: numbers find a
dead frame, only looking finds an extra arm. A reel is done when check.json says ok AND the sheets have been looked at.
"""
import json, math, os, re, subprocess, sys
FF = os.environ.get("FFMPEG", "ffmpeg")
FREEZE = float(os.environ.get("CHECK_FREEZE", "0.8"))       # seconds with no motion that count as a still card
STILL = float(os.environ.get("CHECK_STILL", "0.035"))       # mean luma change per frame (0-255, at 160 px wide) under which nothing moved
LUFS = (-16.5, -12.5)                                       # (the reels are mixed at about -14.5)


def run(args, cwd=None):
    return subprocess.run([FF, "-hide_banner", "-nostats"] + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="ignore")


def probe(mp4):
    e = run(["-i", mp4]).stderr; d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", e); v = re.search(r"Video: .*?(\d{3,5})x(\d{3,5})[^\n]*?([\d.]+) fps", e)
    return {"secs": (int(d[1]) * 3600 + int(d[2]) * 60 + float(d[3])) if d else 0.0, "w": int(v[1]) if v else 0, "h": int(v[2]) if v else 0,
            "fps": float(v[3]) if v else 0.0, "audio": bool(re.search(r"Audio: ", e))}


def frames(mp4, work):
    """-> [{t, avg, lo, hi, move, move2}] for every frame: its brightness, its range, how far it is from the frame before (move)
    and from the frame two before (move2: small while move is large means the frame between them was the odd one out)."""
    os.makedirs(work, exist_ok=True)
    for f in ("a.txt", "b.txt", "c.txt", "d.txt"):
        if os.path.exists(os.path.join(work, f)): os.remove(os.path.join(work, f))
    d = "tblend=all_mode=difference,signalstats,metadata=mode=print:key=lavfi.signalstats.YAVG:file="
    g = ("[0:v]scale=160:-2,split=4[p][q][e][o];[p]signalstats,metadata=mode=print:file=a.txt[x];[q]" + d + "b.txt[y];"
         r"[e]select=not(mod(n\,2))," + d + r"c.txt[z];[o]select=mod(n\,2)," + d + "d.txt[w]")          # (the even frames and the odd frames apart: each against the frame two before)
    r = run(["-i", os.path.abspath(mp4), "-filter_complex", g] + [x for k in "xyzw" for x in ("-map", f"[{k}]", "-f", "null", "-")], cwd=work)
    if r.returncode: raise SystemExit("ffmpeg could not read the frames: " + r.stderr[-300:])
    F, cur = [], None
    for line in open(os.path.join(work, "a.txt"), encoding="utf-8", errors="ignore"):
        m = re.match(r"frame:(\d+)\s+pts:\S+\s+pts_time:([\d.]+)", line)
        if m: cur = {"t": float(m[2])}; F.append(cur); continue
        m = re.match(r"lavfi\.signalstats\.(YAVG|YLOW|YHIGH)=([\d.]+)", line)
        if m and cur is not None: cur[{"YAVG": "avg", "YLOW": "lo", "YHIGH": "hi"}[m[1]]] = float(m[2])
    def diffs(*names):
        mv, t, first = {}, None, set()
        for name in names:
            k = 0
            for line in open(os.path.join(work, name), encoding="utf-8", errors="ignore"):
                m = re.match(r"frame:(\d+)\s+pts:\S+\s+pts_time:([\d.]+)", line)
                if m:
                    t = round(float(m[2]), 3); k += 1
                    if k == 1: first.add(t)                  # (tblend's first frame has no frame before it)
                    continue
                m = re.match(r"lavfi\.signalstats\.YAVG=([\d.]+)", line)
                if m and t is not None: mv[t] = float(m[1])
        return {t: (0.0 if t in first else v) for t, v in mv.items()}
    m1, m2 = diffs("b.txt"), diffs("c.txt", "d.txt")
    for f in F: f["move"] = m1.get(round(f["t"], 3), 0.0); f["move2"] = m2.get(round(f["t"], 3), 0.0)
    return F


def judge(F, info, lo=8.0, hi=95.0):
    """The faults and warnings of a list of frame measurements. Pure: demo() tests it on made-up lists."""
    faults, warns = [], []; n = len(F); fps = info.get("fps") or 30.0
    if not n: return ["no frames"], [], {}
    for f in F:                                                      # blank: black, white, or one flat colour
        if f.get("avg", 99) < 6 or f.get("avg", 99) > 249 or f.get("hi", 255) - f.get("lo", 0) < 6: faults.append(f"{f['t']:.2f}s: a blank frame"); break
    M = sorted(f["move"] for f in F[1:]) or [0.0]; med = M[len(M) // 2]; big = max(6.0, med * 8)
    for i in range(1, n - 1):                                         # a glitch: this frame is far from the one before, the next is far from it, yet the frames on its two sides are alike (a fast move or a double cut is not: its sides differ too)
        a, b = F[i]["move"], F[i + 1]["move"]
        if a > big and b > big and F[i + 1].get("move2", a) < .3 * min(a, b): faults.append(f"{F[i]['t']:.2f}s: a one-frame glitch (unlike the frames on both sides, which are alike)")
    run0 = None; stills = []
    for i in range(1, n):
        if F[i]["move"] < STILL: run0 = i - 1 if run0 is None else run0
        else:
            if run0 is not None: stills.append((F[run0]["t"], F[i - 1]["t"]))
            run0 = None
    if run0 is not None: stills.append((F[run0]["t"], F[-1]["t"]))
    for a, b in stills:
        if b - a >= FREEZE: (warns if a >= F[-1]["t"] - 1.6 else faults).append(f"{a:.1f}s to {b:.1f}s: nothing moves for {b - a:.1f}s")       # (the closing card may hold its last second and a half)
    first = [f["move"] for f in F[1:int(fps * .5) + 1]]
    if first and max(first) < STILL * 2: faults.append("frame 0 is a still: nothing moves in the first half second")
    if F[0].get("hi", 255) - F[0].get("lo", 0) < 30: faults.append("frame 0 is empty (a flat picture)")
    cuts = [F[i]["t"] for i in range(1, n) if F[i]["move"] > big]; gaps = [b - a for a, b in zip([0.0] + cuts, cuts + [F[-1]["t"]])]
    if gaps and max(gaps) > 6.5: warns.append(f"{max(gaps):.1f}s without a cut or a big change of picture")
    if info.get("w") and (info["w"], info["h"]) != (1080, 1920): faults.append(f"the picture is {info['w']}x{info['h']}, not 1080x1920")
    if info.get("fps") and abs(info["fps"] - 30) > .5: faults.append(f"{info['fps']} frames a second, not 30")
    if info.get("secs") and not lo <= info["secs"] <= hi: faults.append(f"{info['secs']:.1f}s long: a reel is {lo:g} to {hi:g} seconds")
    return faults, warns, {"frames": n, "cuts": len(cuts), "median_move": round(med, 3), "longest_hold": round(max(gaps), 2) if gaps else 0, "stills": [(round(a, 2), round(b, 2)) for a, b in stills if b - a >= .4]}


def sound(mp4):
    """-> (faults, warns, {lufs, peak}) for the sound track."""
    r = run(["-i", mp4, "-map", "0:a:0", "-af", "ebur128=peak=true,silencedetect=noise=-45dB:d=1.5", "-f", "null", "-"]).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r); p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r); sil = re.findall(r"silence_start: ([\d.]+)", r)
    if not i: return ["no sound track could be measured"], [], {}
    lufs, peak = float(i[-1]), float(p[-1]) if p else 0.0; faults, warns = [], []
    if not LUFS[0] - 3 <= lufs <= LUFS[1] + 2: faults.append(f"the sound is at {lufs} LUFS (it should be about -14.5)")
    elif not LUFS[0] <= lufs <= LUFS[1]: warns.append(f"the sound is at {lufs} LUFS (about -14.5 is the mark)")
    if peak > -0.3: faults.append(f"the sound clips (peak {peak} dB)")
    for s in sil[:3]: faults.append(f"{float(s):.1f}s: a hole in the sound (silence for 1.5s or more)")
    return faults, warns, {"lufs": lufs, "peak": peak}


def sheets(mp4, out, secs, step=3, cols=16, rows=6):
    """Every `step`th frame on contact sheets (cols x rows, 135 px wide), and the first three seconds frame by frame."""
    n = max(1, math.ceil(secs * 30 / step / (cols * rows)))
    run(["-y", "-v", "error", "-i", mp4, "-vf", f"select=not(mod(n\\,{step})),scale=135:-2,tile={cols}x{rows}", "-fps_mode", "vfr", "-frames:v", str(n), "-q:v", "4", os.path.join(out, "sheet_%02d.jpg")])
    run(["-y", "-v", "error", "-i", mp4, "-vf", "select=lt(n\\,90)*not(mod(n\\,5)),scale=216:-2,tile=9x2", "-fps_mode", "vfr", "-frames:v", "1", "-q:v", "3", os.path.join(out, "first3.jpg")])
    return sorted(f for f in os.listdir(out) if f.startswith("sheet_"))


def check(mp4, out=None, lo=8.0, hi=95.0):
    out = out or os.path.join(os.path.dirname(os.path.abspath(mp4)), "check"); os.makedirs(out, exist_ok=True)
    info = probe(mp4); F = frames(mp4, out); faults, warns, stats = judge(F, info, lo, hi)
    if info["audio"]:
        f2, w2, s2 = sound(mp4); faults += f2; warns += w2; stats.update(s2)
    else: faults.append("the reel has no sound track")
    res = {"ok": not faults, "faults": faults, "warns": warns, "info": info, "stats": stats, "sheets": sheets(mp4, out, info["secs"]) + ["first3.jpg"]}
    json.dump(res, open(os.path.join(out, "check.json"), "w"), indent=1); return res


def demo():
    f = lambda t, avg=120, lo=20, hi=230, move=2.0: {"t": t, "avg": avg, "lo": lo, "hi": hi, "move": move}
    ok = [f(i / 30) for i in range(300)]; info = {"w": 1080, "h": 1920, "fps": 30.0, "secs": 10.0}
    assert judge(ok, info)[0] == [], judge(ok, info)[0]
    black = [dict(x) for x in ok]; black[100].update(avg=2, lo=0, hi=3); assert any("blank" in e for e in judge(black, info)[0])
    still = [dict(x) for x in ok]
    for i in range(60, 100): still[i]["move"] = 0.0
    assert any("nothing moves" in e for e in judge(still, info)[0])
    glitch = [dict(x, move2=2.0) for x in ok]; glitch[150]["move"] = glitch[151]["move"] = 60.0; assert any("glitch" in e for e in judge(glitch, info)[0])
    whip = [dict(x, move2=2.0) for x in ok]; whip[150]["move"] = whip[151]["move"] = 60.0; whip[151]["move2"] = 70.0; assert not any("glitch" in e for e in judge(whip, info)[0])      # (a two-frame whip of the camera)
    cut = [dict(x) for x in ok]; cut[150]["move"] = 60.0; assert not any("glitch" in e for e in judge(cut, info)[0])          # (one spike is a cut)
    dead0 = [dict(x) for x in ok]
    for i in range(0, 20): dead0[i]["move"] = 0.0
    assert any("frame 0" in e for e in judge(dead0, info)[0])
    assert any("1080x1920" in e for e in judge(ok, dict(info, w=720, h=1280))[0]) and any("long" in e for e in judge(ok, dict(info, secs=3.0))[0])
    end = [dict(x) for x in ok]
    for i in range(265, 300): end[i]["move"] = 0.0
    assert not any("nothing moves" in e for e in judge(end, info)[0]) and any("nothing moves" in e for e in judge(end, info)[1])      # (the closing card: a warning)
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "demo": demo()
    else:
        r = check(a[0], a[1] if len(a) > 1 else None)
        print(json.dumps({k: r[k] for k in ("ok", "faults", "warns", "stats")}, indent=1)); sys.exit(0 if r["ok"] else 1)
