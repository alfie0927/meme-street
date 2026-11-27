"""Meme Street's reel studio: the SECOND reel generator. The first (src/explainer, the 3D story reel) is not touched by it.

The owner, 2026-11-27, sent five reels and said: "build the workflow these reels explain in a new reel generator (keeping the
old one intact) ... more imaginative animation ... use all the motion graphic tools ... implement the hook method".
What the reels teach, and where it lives here:

  the nine steps of a series (one reel = one part)                     this file, in order
    1 the bible      who and where the series is, the rules nobody breaks      BIBLE.md, bible.json
    2 the script     a hook in the first second, a choice in the last          reel.json, lint()
    3 the voice      every word timed to the frame                             voice() (the explainer's voice and aligner, reused)
    4 the cast       every character drawn in code                             engines/*/ (SVG, canvas and 3D figures; no image files)
    5 the shots      camera, layers, captions                                  render(): four engines
    6 the sound      every hit, and the music under the voice                  sound.py
    7 the check      every single frame                                        check.py
    8 the post       the cover, the caption, the vote                          pack()
    9 the votes      the comments decide what comes next                       votes()
  the Triple Hook (context, lean, contrarian snapback)                 lint(): a script without the three is sent back
  a different art style a reel, reusable style packs                   styles/*.json (the look as data: colours, type, motion)
  the motion graphic tools                                             engines/: hf (HyperFrames compositions: HTML + GSAP),
                                                                       remotion (React), manim (maths and chart drawing),
                                                                       page (our own three.js pages); craft rules: CRAFT.md

A reel is a folder holding reel.json:
  {"name", "slot": "0400|0900|1600|2330", "engine": "page|hf|remotion|manim", "style", "entry": the page, composition or scene,
   "title", "hook": {"context", "lean", "snapback", "text": the words on frame 0, "visual": what moves on frame 0},
   "say": [sentence, ...] ([] for a reel with no narrator), "choice": {"q", "a", "b"[, "c"]}, "props": {...the engine's data...},
   "events": [[t, sound], ...], "music": a track of the library, "caption", "tags", "cover": {"t": seconds}}

  python studio.py steps                  the nine steps
  python studio.py lint <dir>             step 2: the script's faults (hook, choice, length)
  python studio.py voice <dir>            step 3: voice.wav and the word times into work/timeline.json (the server: it has the voices)
  python studio.py fake <dir>             the same timeline with estimated word times and no voice (to look before voicing)
  python studio.py stills <dir> "[t, ...]"  one picture at each second given, and a sheet: LOOK at a reel while making it
  python studio.py render <dir>           step 5: work/silent.mp4 and out/cover.jpg (a PC with a graphics card)
  python sound.py <dir>                   step 6: out/reel.mp4 (the server: it has the music)
  python studio.py check <dir>            step 7: every frame, the sound, the contact sheets
  python studio.py pack <dir>             step 8: out/caption.txt and out/vote.txt
  python studio.py votes <comments.json> [dir]   step 9: the count
  python studio.py demo                   self-check: no network, no voice, no render
"""
import json, os, re, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.dirname(HERE); EXPL = os.path.join(SRC, "explainer"); ENG = os.path.join(HERE, "engines")
BIBLE = json.load(open(os.path.join(HERE, "bible.json"), encoding="utf-8"))
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
STEPS = ["the bible: who and where, the rules nobody breaks (BIBLE.md)", "the script: a hook in the first second, a choice in the last (lint)",
         "the voice: every word timed to the frame (voice)", "the cast: every character drawn in code (engines)", "the shots: camera, layers, captions (render)",
         "the sound: every hit, and the music under the voice (sound.py)", "the check: every single frame (check.py)", "the post: the cover, the caption, the vote (pack)",
         "the votes: the comments decide what comes next (votes)"]
SLOTS = BIBLE["slots"]          # {"0400": {"secs": [lo, hi], ...}, ...}
say = lambda *a: print(*a, flush=True)
words = lambda s: re.findall(r"[A-Za-z0-9$%'.,-]+", str(s))
norm = lambda s: re.sub(r"[^a-z0-9$%]", "", str(s).lower())


def load(d):
    r = json.load(open(os.path.join(d, "reel.json"), encoding="utf-8")); r["_dir"] = os.path.abspath(d); return r


# ---------------------------------------------------------------- step 2: the script, and the Triple Hook
def lint(r):
    """-> (faults, warnings). The Triple Hook (the owner's fifth reel): 1 CONTEXT, what this is about, in the very first words, said
    AND shown AND written; 2 the LEAN, a number, a proof, a pain or something unexpected that makes the viewer want the next line;
    3 the contrarian SNAPBACK, a line that pulls the other way. Then the nine steps' own rule: a choice in the last second."""
    F, W = [], []; h = r.get("hook") or {}; S = [str(s) for s in r.get("say") or []]; slot = SLOTS.get(str(r.get("slot")))
    if r.get("engine") not in ("page", "hf", "remotion", "manim"): F.append("engine is one of page, hf, remotion, manim")
    if not slot: F.append("slot is one of " + ", ".join(SLOTS))
    for k in ("context", "lean", "snapback", "text", "visual"):
        if not str(h.get(k) or "").strip(): F.append(f"the hook has no {k}" + {"text": " (the words on frame 0)", "visual": " (what is already moving on frame 0)"}.get(k, ""))
    ctx = [norm(w) for w in BIBLE["context_words"]]; has = lambda text, n=99: any(any(c in norm(w) for c in ctx) for w in words(text)[:n])
    if h.get("context"):
        if len(words(h["context"])) > 12: F.append("the hook's context is over 12 words: it must be understood in one breath")
        if not has(h["context"], 6): F.append("the context is not in the first six words: name the subject at once (" + ", ".join(BIBLE["context_words"][:6]) + "...)")
    if h.get("text") and (len(words(h["text"])) > 6 or len(str(h["text"])) > 30): F.append("the words on frame 0 are at most six words and thirty letters")
    if h.get("lean") and not (re.search(r"\d", h["lean"]) or any(norm(w) in norm(h["lean"]) for w in BIBLE["lean_words"])):
        F.append("the lean gives the viewer nothing to lean on: a number, a proof, a pain or something unexpected")
    if h.get("snapback") and not any(re.search(r"\b" + re.escape(w) + r"\b", h["snapback"].lower()) for w in BIBLE["turn_words"]):
        F.append("the snapback does not turn: it pulls against the lean (" + ", ".join(BIBLE["turn_words"][:8]) + "...)")
    hook_words = sum(len(words(h.get(k) or "")) for k in ("context", "lean", "snapback"))
    if hook_words > 34: F.append(f"the three hook lines are {hook_words} words: at most 34 (about ten seconds)")
    if S:                                             # a narrated reel says its hook, in order, at the start
        head = norm(" ".join(S[:4]))
        for k in ("context", "lean", "snapback"):
            if h.get(k) and norm(h[k]) not in head: F.append(f"the narrator does not say the hook's {k} in the first four sentences, word for word")
        if h.get("context") and not norm(S[0]).startswith(norm(h["context"])): F.append("the first sentence does not open with the context")
    c = r.get("choice") or {}
    if not (c.get("q") and c.get("a") and c.get("b")): F.append("no choice in the last second: choice {q, a, b}, answered in the comments")
    elif max(len(str(c[k])) for k in c if k != "q") > 26: F.append("a choice's answer is at most 26 letters")
    n = sum(len(words(s)) for s in S)
    if slot and S:
        lo, hi = slot["secs"]; est = n / BIBLE["words_a_second"] + 1.5
        if not lo - 2 <= est <= hi + 2: F.append(f"{n} words is about {est:.0f}s: this slot's reel is {lo} to {hi} seconds")
    for i, s in enumerate(S):
        if len(words(s)) > 16: W.append(f"sentence {i + 1} is {len(words(s))} words: a shot holds about 14")
    if not r.get("music"): W.append("no music named")
    if not r.get("caption"): W.append("no caption")
    return F, W


# ---------------------------------------------------------------- step 3: the voice (the explainer's, reused: one narrator, each word timed from its own sound)
def voice(d, fake=False):
    """fake: the same timeline from estimated word times, with no voice (to look at a reel before it is voiced)."""
    r = load(d); work = os.path.join(d, "work"); os.makedirs(work, exist_ok=True); sys.path.insert(0, EXPL); sys.path.insert(0, SRC)
    import make as M, words
    _el = M.el_text; M.el_text = lambda text, story=None: words.say(_el(text, story)); M.spoken = (lambda f: lambda text, story=None: f(words.say(text), story))(M.spoken)      # (numbers said as words: 'one thousand and fifty-two dollars'; the captions keep the digits)
    spec = {"title": r["title"], "brands": r.get("brands") or [], "cast": [], "sentences": [{"say": s, "scene": {"bg": "studio", "items": []}} for s in r["say"]]}
    story = M.day_story("x", os.environ["DAILY_DATA"]) if os.environ.get("DAILY_DATA") else None
    if fake: segs, wt, T = M.fake_times(spec)
    else: wav, segs, W, T = M.voice(spec, work, story); wt = M.align(M.estimate(segs), W)
    sp = M.spans_of(segs)
    R = dict(r.get("props") or {}, T=round(T + float(r.get("tail", 0)), 3), words=wt, caps=M.captions(wt, spec, sp), spans=[[round(sp[i][0], 3), round(sp[i][1], 3)] for i in sorted(sp)],
             cuts=[round(M.shot_at(sp, i), 3) for i in range(len(r["say"]))], title=r["title"], choice=r.get("choice"), hook=r.get("hook"), cover=r.get("cover") or {"t": 1.6})
    json.dump(R, open(os.path.join(work, "timeline.json"), "w", encoding="utf-8")); say(os.path.join(work, "timeline.json"), f"{R['T']}s"); return R


def silent_timeline(d):
    """A reel with no narrator: its engine's data as it stands (props carries T)."""
    r = load(d); work = os.path.join(d, "work"); os.makedirs(work, exist_ok=True)
    R = dict(r.get("props") or {}, title=r["title"], choice=r.get("choice"), hook=r.get("hook"), cover=r.get("cover") or {"t": 1.6})
    if "T" not in R: raise SystemExit("a reel with no narrator gives its length: props.T")
    json.dump(R, open(os.path.join(work, "timeline.json"), "w", encoding="utf-8")); return R


# ---------------------------------------------------------------- step 5: the shots, by engine
def render(d):
    r = load(d); work, out = os.path.join(d, "work"), os.path.join(d, "out"); os.makedirs(out, exist_ok=True); tl = os.path.join(work, "timeline.json")
    if not os.path.exists(tl): silent_timeline(d)
    R = json.load(open(tl, encoding="utf-8")); mp4, cover = os.path.join(work, "silent.mp4"), os.path.join(out, "cover.jpg"); eng = r["engine"]; entry = r["entry"]
    if eng in ("page", "hf"):               # a page whose render(t) is a pure function of time, grabbed frame by frame (an hf composition gets it from hfplay.js)
        page = os.path.join(ENG, eng if eng == "hf" else "", entry)
        if eng == "hf": prepare_hf(os.path.dirname(page))
        env = dict(os.environ, EXPLAINER_PAGE=os.path.relpath(page, EXPL).replace(os.sep, "/"))
        subprocess.run([sys.executable, os.path.join(EXPL, "make.py"), "film", tl, work], check=True, env=env); shutil.copy(os.path.join(work, "cover.jpg"), cover)
        stills(d, [R["cover"]["t"]])                 # (and the page's own list of what is heard, work/events.json)
    elif eng == "remotion":                 # entry: the composition's id in engines/remotion/src/Root.jsx; its props are the timeline
        cli = [os.environ.get("NODE", "node"), os.path.join("node_modules", "@remotion", "cli", "remotion-cli.js")]; br = ["--browser-executable=" + os.environ["STUDIO_CHROME"]] if os.environ.get("STUDIO_CHROME") else []
        common = ["--props=" + os.path.abspath(tl), "--log=error"] + br; cwd = os.path.join(ENG, "remotion")
        subprocess.run(cli + ["render", "src/index.jsx", entry, os.path.abspath(mp4), "--codec=h264", "--crf=16", "--muted", "--concurrency=" + os.environ.get("EXPLAINER_WORKERS", "3")] + common, check=True, cwd=cwd)
        subprocess.run(cli + ["still", "src/index.jsx", entry, os.path.abspath(cover), "--frame=" + str(int(round(R["cover"]["t"] * 30))), "--image-format=jpeg", "--jpeg-quality=92"] + common, check=True, cwd=cwd)
    elif eng == "manim":                    # entry: "file.py::Scene" in engines/manim; the scene reads its data from STUDIO_PROPS
        f, scene = entry.split("::"); media = os.path.join(work, "manim"); py = os.environ.get("STUDIO_MANIM_PY", sys.executable)
        subprocess.run([py, "-m", "manim", "render", "-qh", "--disable_caching", "--media_dir", media, "-r", "1080,1920", "--fps", "30", "-o", "silent.mp4", f, scene], check=True, cwd=os.path.join(ENG, "manim"), env=dict(os.environ, STUDIO_PROPS=os.path.abspath(tl)))
        made = [os.path.join(p, n) for p, _, fs in os.walk(media) for n in fs if n == "silent.mp4"]; shutil.copy(made[0], mp4)
        subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", str(R["cover"]["t"]), "-i", mp4, "-frames:v", "1", "-q:v", "2", cover], check=True)
    say(mp4); return mp4


def prepare_hf(proj):
    """An hf composition keeps its libraries inside its own folder (HyperFrames' rule): GSAP from the installed package, and hfplay.js,
    which lets our frame grabber drive the composition's timelines exactly as HyperFrames' own renderer does."""
    v = os.path.join(proj, "vendor"); os.makedirs(v, exist_ok=True)
    g = os.path.join(ENG, "hf", "node_modules", "gsap", "dist", "gsap.min.js")
    if not os.path.exists(g): g = os.path.join(ENG, "hf", "lib", "gsap.min.js")          # (the committed copy: the server has no node_modules)
    if os.path.exists(g): shutil.copy(g, os.path.join(v, "gsap.min.js"))
    elif not os.path.exists(os.path.join(v, "gsap.min.js")): raise SystemExit("GSAP is not installed: npm install in engines/hf")
    shutil.copy(os.path.join(ENG, "hf", "hfplay.js"), os.path.join(v, "hfplay.js"))
    for src in (os.path.join(SRC, "oneshot", "vendor", "three.min.js"), os.path.join(EXPL, "models3d.js")):      # (a composition may draw the realistic 3D models too)
        shutil.copy(src, os.path.join(v, os.path.basename(src)))


def hf_tools(d):
    """HyperFrames' own lint and layout check (overlap, contrast, the 9:16 safe zone) on an hf composition. Its tracking and update
    checks are off; it is never signed in and its `usage`, `share`, `publish` and `cloud` commands are never run (they send data out)."""
    r = load(d); proj = os.path.dirname(os.path.join(ENG, "hf", r["entry"])); prepare_hf(proj); res = {}
    env = dict(os.environ, HYPERFRAMES_NO_TELEMETRY="1", DO_NOT_TRACK="1", HYPERFRAMES_NO_UPDATE_CHECK="1", HYPERFRAMES_SKIP_SKILLS="1")
    if os.environ.get("STUDIO_CHROME"): env["HYPERFRAMES_BROWSER_PATH"] = os.environ["STUDIO_CHROME"]
    for cmd in ("lint", "check"):
        p = subprocess.run([os.environ.get("NODE", "node"), os.path.join("node_modules", "hyperframes", "bin", "hyperframes.mjs"), cmd, proj], cwd=os.path.join(ENG, "hf"), env=env, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        res[cmd] = [l.strip() for l in (p.stdout + p.stderr).split("\n") if re.search(r"✗|error\(s\)|warning\(s\)", l)]
    return res


def stills(d, times):
    """One picture at each time (seconds) into <dir>/stills, and sheet.jpg: how a reel is LOOKED AT while it is being made."""
    r = load(d); work = os.path.join(d, "work"); tl = os.path.join(work, "timeline.json"); out = os.path.join(d, "stills"); os.makedirs(out, exist_ok=True)
    if not os.path.exists(tl): silent_timeline(d)
    R = json.load(open(tl, encoding="utf-8")); eng = r["engine"]; names = [f"s{k:02d}.jpg" for k in range(len(times))]
    if eng in ("page", "hf"):
        page = os.path.join(ENG, eng if eng == "hf" else "", r["entry"])
        if eng == "hf": prepare_hf(os.path.dirname(page))
        os.environ["EXPLAINER_PAGE"] = os.path.relpath(page, EXPL).replace(os.sep, "/"); sys.path.insert(0, EXPL); sys.path.insert(0, SRC)
        import asyncio, make as M
        M.PAGE = os.environ["EXPLAINER_PAGE"]          # (make may have been imported earlier with another page: daily.py loads it for the day's story)
        async def go():
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                b, pg, errs = await M.page(p, R)
                for n, t in zip(names, times): await pg.evaluate("t=>render(t)", t); await pg.screenshot(path=os.path.join(out, n), type="jpeg", quality=88)
                ev = await pg.evaluate("window.__events ? window.__events() : null"); await b.close()
                if ev is not None: json.dump(ev, open(os.path.join(work, "events.json"), "w"))
                for e in errs[:5]: say("page error:", e)
        asyncio.run(go())
    elif eng == "remotion":
        cli = [os.environ.get("NODE", "node"), os.path.join("node_modules", "@remotion", "cli", "remotion-cli.js")]; br = ["--browser-executable=" + os.environ["STUDIO_CHROME"]] if os.environ.get("STUDIO_CHROME") else []
        for n, t in zip(names, times): subprocess.run(cli + ["still", "src/index.jsx", r["entry"], os.path.abspath(os.path.join(out, n)), "--frame=" + str(int(round(t * 30))), "--image-format=jpeg", "--props=" + os.path.abspath(tl), "--log=error"] + br, check=True, cwd=os.path.join(ENG, "remotion"))
    elif eng == "manim":                    # a quick low-quality run of the whole scene, then its frames
        f, scene = r["entry"].split("::"); media = os.path.join(work, "manim_ql"); py = os.environ.get("STUDIO_MANIM_PY", sys.executable)
        subprocess.run([py, "-m", "manim", "render", "-ql", "--disable_caching", "--media_dir", media, "-r", "540,960", "--fps", "15", "-o", "ql.mp4", f, scene], check=True, cwd=os.path.join(ENG, "manim"), env=dict(os.environ, STUDIO_PROPS=os.path.abspath(tl)))
        made = [os.path.join(p, n) for p, _, fs in os.walk(media) for n in fs if n == "ql.mp4"]
        for n, t in zip(names, times): subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", str(t), "-i", made[0], "-frames:v", "1", "-q:v", "3", os.path.join(out, n)], check=True)
    cols = min(7, len(names)); rows = -(-len(names) // cols)
    subprocess.run([FFMPEG, "-v", "error", "-y", "-pattern_type", "sequence", "-start_number", "0", "-i", os.path.join(out, "s%02d.jpg"), "-vf", f"scale=270:480,tile={cols}x{rows}", "-frames:v", "1", "-q:v", "3", os.path.join(out, "sheet.jpg")], check=True)
    say(len(names), "stills and sheet.jpg in", out)


# ---------------------------------------------------------------- step 7: the check
def check(d):
    sys.path.insert(0, HERE); import check as C
    r = load(d); lo, hi = SLOTS[str(r["slot"])]["secs"]; res = C.check(os.path.join(d, "out", "reel.mp4"), os.path.join(d, "check"), lo - 2, hi + 4)
    F, W = lint(r); res["script"] = {"faults": F, "warns": W}; res["ok"] = res["ok"] and not F
    if r["engine"] == "hf" and shutil.which(os.environ.get("NODE", "node")) and os.path.isdir(os.path.join(ENG, "hf", "node_modules")): res["hyperframes"] = hf_tools(d)      # (an extra: the reel server has no Node)
    json.dump(res, open(os.path.join(d, "check", "check.json"), "w"), indent=1); return res


# ---------------------------------------------------------------- step 8: the post
def pack(d):
    """The caption (the hook's first line, the choice as a question, the link) and the vote: the first comment to pin under the reel."""
    r = load(d); out = os.path.join(d, "out"); os.makedirs(out, exist_ok=True); c = r.get("choice") or {}
    opts = [f"{k.upper()}: {c[k]}" for k in ("a", "b", "c") if c.get(k)]
    vote = (f"{c['q']} " + " or ".join(k.upper() for k in ("a", "b", "c") if c.get(k)) + "? " + "  ".join(opts) + "\nComment your letter. The count is in tonight's reel.") if c.get("q") else ""
    cap = "\n".join(x for x in [r.get("caption") or r["title"], "", (c.get("q") + " " + " / ".join(opts)) if c.get("q") else "", BIBLE["link_line"], BIBLE["disclaimer"], r.get("tags") or BIBLE["tags"]] if x is not None)
    open(os.path.join(out, "caption.txt"), "w", encoding="utf-8").write(cap.strip() + "\n"); open(os.path.join(out, "vote.txt"), "w", encoding="utf-8").write(vote + "\n")
    return cap, vote


# ---------------------------------------------------------------- step 9: the votes
def votes(comments, choice):
    """Count the letters in a reel's comments: the first A, B or C that stands alone in a comment (or an answer's own first word),
    one vote a person. -> {"a": n, "b": n, "c": n, "n": voters, "top": letter or None, "line": a sentence for tonight's script}."""
    keys = [k for k in ("a", "b", "c") if (choice or {}).get(k)]; first = {k: norm(words(choice[k])[0]) for k in keys}; seen, n = {}, {k: 0 for k in keys}
    for c in comments:
        who = c.get("username") or c.get("id"); t = str(c.get("text") or "").lower()
        if who in seen: continue
        m = re.search(r"(?<![a-z0-9])([abc])(?![a-z0-9])", t); k = m.group(1) if m and m.group(1) in keys else next((k for k in keys if first[k] and re.search(r"(?<![a-z0-9])" + re.escape(first[k]) + r"(?![a-z0-9])", norm_keep(t))), None)
        if k: seen[who] = k; n[k] += 1
    tot = sum(n.values()); top = max(keys, key=lambda k: n[k]) if tot and sorted(n.values())[-1] != (sorted(n.values())[-2] if len(keys) > 1 else -1) else None
    line = "" if not tot else (f"{n[top]} of {tot} of you said {choice[top]}." if top else "You were split on this one.")
    return dict(n, n=tot, top=top, line=line)
norm_keep = lambda s: re.sub(r"[^a-z0-9 ]", " ", str(s).lower())


def demo():
    ok = {"slot": "0900", "engine": "hf", "title": "t", "music": "m", "caption": "c",
          "hook": {"context": "This stock had just landed UPS.", "lean": "An order for up to 1,000 electric vans.", "snapback": "It still lost 78% that year.", "text": "LANDED UPS", "visual": "a van bursts out of a crate"},
          "say": ["This stock had just landed UPS.", "An order for up to 1,000 electric vans.", "It still lost 78% that year.", "Would you have held it or sold it that day, knowing only the chart?"],
          "choice": {"q": "The day of the deal:", "a": "Buy the news", "b": "Stay away"}}
    assert lint(ok) == ([], []), lint(ok)
    bad = lambda **k: lint(dict(ok, **k))[0]
    assert any("context is not in the first six" in e for e in bad(hook=dict(ok["hook"], context="Back in the winter of 2017 a small firm from Ohio got a call about a stock.")) + bad(hook=dict(ok["hook"], context="Here is a thing that happened once.")))
    assert any("nothing to lean on" in e for e in bad(hook=dict(ok["hook"], lean="It was a company.")))
    assert any("does not turn" in e for e in bad(hook=dict(ok["hook"], snapback="It went up a lot.")))
    assert any("no choice" in e for e in bad(choice={})) and any("frame 0" in e for e in bad(hook=dict(ok["hook"], text="")))
    assert any("does not say the hook's lean" in e for e in bad(say=[ok["say"][0], "Something else.", ok["say"][2], ok["say"][3]]))
    assert any("seconds" in e for e in bad(say=ok["say"] + ["More words here to make it long."] * 30))
    v = votes([{"username": "x", "text": "A for sure"}, {"username": "y", "text": "b"}, {"username": "x", "text": "B"}, {"username": "z", "text": "buy!!"}, {"username": "q", "text": "nice reel"}], ok["choice"])
    assert (v["a"], v["b"], v["n"], v["top"]) == (2, 1, 3, "a"), v
    assert votes([], ok["choice"])["line"] == "" and votes([{"username": "x", "text": "a"}, {"username": "y", "text": "B"}], ok["choice"])["top"] is None
    assert len(STEPS) == 9 and all(os.path.isdir(os.path.join(ENG, e)) for e in ("hf", "remotion", "manim", "ride"))
    import tempfile
    d = tempfile.mkdtemp(); json.dump(ok, open(os.path.join(d, "reel.json"), "w")); cap, vote = pack(d); assert "A: Buy the news" in vote and "memestreet.net" in cap; shutil.rmtree(d)
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "demo": demo()
    elif a[0] == "steps": [say(f"{i + 1}. {s}") for i, s in enumerate(STEPS)]
    elif a[0] == "lint": F, W = lint(load(a[1])); [say("FAULT", f) for f in F]; [say("warn ", w) for w in W]; say("ok" if not F else f"{len(F)} faults"); sys.exit(1 if F else 0)
    elif a[0] == "voice": voice(a[1])
    elif a[0] == "fake": voice(a[1], fake=True) if load(a[1]).get("say") else silent_timeline(a[1])
    elif a[0] == "stills": stills(a[1], json.loads(a[2]))
    elif a[0] == "render": render(a[1])
    elif a[0] == "check": res = check(a[1]); say(json.dumps({k: res[k] for k in ("ok", "faults", "warns", "script") if k in res}, indent=1)); [say("hyperframes", k, v) for k, v in (res.get("hyperframes") or {}).items()]; sys.exit(0 if res["ok"] else 1)
    elif a[0] == "pack": cap, vote = pack(a[1]); say(cap); say("--- the vote (first comment):"); say(vote)
    elif a[0] == "votes": say(json.dumps(votes(json.load(open(a[1], encoding="utf-8")), load(a[2])["choice"] if len(a) > 2 else {"a": "A", "b": "B"})))
    else: raise SystemExit(__doc__)
