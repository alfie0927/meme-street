"""The "In this town" blocky story reel (huss3d.html), the owner's model reel's style (2026-11-25: "make the reel about HUSS HUSS but
about trading ... EXACTLY the same animation style"): a deadpan narrator in short lines, one shot a line, one yellow word at a time.

  python3 huss.py cut <script.json> <dir>        voice (ElevenLabs, pitched to the model's narrator), word times, timeline -> <dir>/work
  python3 huss.py film <timeline.json> <dir>     frames (EXPLAINER_GL / _Q / _WORKERS) -> <dir>/silent.mp4 + cover.jpg
  python3 huss.py mux <dir> <silent.mp4>         sound -> <dir>/out/reel.mp4 + caption.txt
A script: {"title", "caption", "track", "voice", "pitch", "speed", "lines": [{"say", "shot": {set, cast, crowd, cam, ...}}]}.
"""
import json, os, re, subprocess, sys
os.environ.setdefault("EXPLAINER_PAGE", "huss3d.html")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)


def setup(sp):
    os.environ["EXPLAINER_EL_VOICE"] = sp.get("voice", "SOYHLrjzK2X1ezoPC6cr")      # (Harry: the closest the account has to the model's narrator, pitched up)
    os.environ["EXPLAINER_EL_SPEED"] = str(sp.get("speed", 1.08)); os.environ["EXPLAINER_TRACK"] = sp.get("track", "Well This is Awkward")
    import make as M
    M.EL_SET.update({"stability": .32, "style": .5}); M.MUSIC_DB = sp.get("music_db", -5.2); return M      # (the model reel's music sits 17 dB under its voice, measured: louder than our story reels)


def word(w):
    s = re.sub(r"[,;:]$", "", w)
    return "HUSS!" if re.match(r"(?i)huss", s) else s


def cut(sp, d):
    M = setup(sp); work = os.path.join(d, "work"); os.makedirs(work, exist_ok=True)
    spec = {"sentences": [{"say": l["say"], "scene": {"items": []}} for l in sp["lines"]]}
    wav, segs, W, T = M.voice(spec, work, {})
    if sp.get("pitch", 1.17) != 1:            # (the model's narrator speaks higher than any voice the account has: shifted, same timing)
        tmp = os.path.join(work, "voice_p.wav")
        subprocess.run([M.FFMPEG, "-v", "error", "-y", "-i", wav, "-af", f"rubberband=pitch={sp.get('pitch', 1.17)}:formant=preserved", tmp], check=True); os.replace(tmp, wav)
    wt = M.align(M.estimate(segs), W); spans = M.spans_of(segs); n = len(sp["lines"])
    starts = [0.0] + [round(spans[i][0] - .12, 3) for i in range(1, n)]
    shots = [dict(l.get("shot") or {}, t0=starts[i], t1=(starts[i + 1] if i + 1 < n else round(T + (sp.get("tail", 0)), 3))) for i, l in enumerate(sp["lines"])]
    caps = []
    for i, (w, t0, t1, *_) in enumerate(wt):
        nx = wt[i + 1][1] if i + 1 < len(wt) else t1 + .4
        caps.append({"t0": round(t0 - .04, 3), "t1": round(min(nx - .04, t1 + .6), 3), "text": word(w)})
    R = {"T": shots[-1]["t1"], "title": sp["title"], "shots": shots, "caps": caps, "prices": sp.get("prices") or [], "cover": sp.get("cover"),
         "scenes": [{"t0": 0, "t1": shots[0]["t1"], "items": []}] + [{"t0": s["t0"], "t1": s["t1"], "items": [{"kind": k, "t": s["t0"] + .1, **({"dir": "down"} if k == "arrow" else {})} for k in (s.get("sfx") or [])]}
                    for s in shots[1:] if s.get("sfx") or s.get("whoosh")]}      # (a whoosh only on the cuts that ask for one: the model cuts hard and quiet)
    json.dump(R, open(os.path.join(work, "timeline.json"), "w", encoding="utf-8")); json.dump(sp, open(os.path.join(work, "spec.json"), "w", encoding="utf-8"), indent=1)
    print(os.path.join(work, "timeline.json"), f"{R['T']:.1f}s")


def mux(d, silent):
    sp = json.load(open(os.path.join(d, "work", "spec.json"), encoding="utf-8")); M = setup(sp); work = os.path.join(d, "work")
    R = json.load(open(os.path.join(work, "timeline.json"), encoding="utf-8")); out = os.path.join(d, "out")
    print(M.mux(R, os.path.join(work, "voice.wav"), work, silent, out))
    tr = M.track(sp["title"]); open(os.path.join(out, "caption.txt"), "w", encoding="utf-8").write(sp["caption"] + "\n\n" + (tr["credit"] + "\n" if tr and tr.get("credit") else "") + M.DISCLAIMER + "\n" + sp.get("tags", ""))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "cut": cut(json.load(open(a[1], encoding="utf-8")), a[2])
    elif a[0] == "film":
        import make as M; os.makedirs(a[2], exist_ok=True); print(M.film(a[1], a[2], os.path.join(a[2], "silent.mp4"), os.path.join(a[2], "cover.jpg")), "frames")
    elif a[0] == "mux": mux(a[1], a[2])
