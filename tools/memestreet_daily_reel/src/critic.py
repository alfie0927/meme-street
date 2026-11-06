"""The film critic: every finished reel is watched by a harsh film maker (Claude, on the owner's plan) before it may be
posted. He gets a review pack made from the real render: frames of every scene, a contact sheet, what the voice is
heard saying (Whisper on the final mix) against the script, the pacing against real narrators, and how far every
caption sits from its word. He approves, or sends it back with notes. Every note must carry evidence from this cut (a
frame of the pack, a quote of the report) or it is dropped (verify); earlier notes come back only as a checklist he
must prove still wrong. The writer rewrites only the scenes the checked script notes name (make_spec.py revise), only
changed lines are voiced again, and the reel is reviewed again, as many rounds as it takes. Template ("renderer") notes
never block: they go to state/renderer_todo.json to be fixed in code. Every checked script note becomes a lesson the
writer reads before every later reel (state/lessons.json).

  python3 src/critic.py loop <work> <out>     voice, render, review, rewrite... -> <out>/approved.json at 60 fps
  python3 src/critic.py review <work> <out>   review one rendered reel -> <work>/review-<n>.json
  python3 src/critic.py demo                  self-check of the evidence check
"""
import datetime, difflib, glob, itertools, json, math, os, re, subprocess, sys, tempfile, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from pronounce import say_as
from narrate import WPS, HUMAN, talk_rate

LESSONS = os.path.join(ROOT, "state", "lessons.json")
TODO = os.path.join(ROOT, "state", "renderer_todo.json")
_ASR = None


def heard(mp4):
    """Every word the final mix is heard saying, with its time (a bigger model than the timing one: this is the ear)."""
    global _ASR
    if _ASR is None:
        from faster_whisper import WhisperModel
        _ASR = WhisperModel(os.environ.get("CRITIC_ASR", "small.en"), device="cpu", compute_type="int8")
    a = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                                     capture_output=True).stdout, np.float32)
    segs, _ = _ASR.transcribe(a, word_timestamps=True, language="en", beam_size=5)
    return [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]


def silences(vo, T, sr=16000):
    """The silent stretches (>= 0.15 s) of the voice alone, from the waveform: Whisper's word edges stretch a pause
    (it ends a word like 'forty-six' early), so they are not a measure of how long the voice is quiet."""
    a = np.zeros(int(T * sr) + sr, np.float32)
    for f, o in vo:
        if "/vo/" not in f: continue                         # (sound effects are not the voice)
        c = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(ROOT, f), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                                         capture_output=True).stdout, np.float32)
        i = int(o * sr); c = c[:len(a) - i]; a[i:i + len(c)] += c
    n = len(a) // 160; loud = np.sqrt(np.mean(a[:n * 160].reshape(n, 160) ** 2, axis=1)) >= 0.01   # 10 ms frames, -40 dB
    on = np.flatnonzero(loud)
    if not len(on): return []
    runs, s = [], None
    for j in range(on[0], on[-1] + 1):
        if not loud[j]: s = j if s is None else s
        elif s is not None:
            if j - s >= 15: runs.append((s / 100, j / 100))
            s = None
    return runs


key = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())


def pack(work, out, rd, only=None):
    """The review pack: images to look at and a report of what is heard and when (frames of the scenes in `only`, or
    of every scene, plus a contact sheet of the whole reel)."""
    R = json.load(open(os.path.join(work, "timeline.json")))
    mp4 = os.path.join(out, "reel.mp4"); os.makedirs(rd, exist_ok=True)
    for f in glob.glob(os.path.join(rd, "*.jpg")): os.remove(f)
    T = R["T"]; ff = lambda *a: subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)
    ff("-i", mp4, "-vf", f"fps=1,scale=180:-1,tile=8x{math.ceil(T / 8)}", "-frames:v", "1", os.path.join(rd, "contact_sheet_1fps.jpg"))
    imgs = ["contact_sheet_1fps.jpg"]
    for i, s in enumerate(R["scenes"]):                      # each scene: as it lands, mid-line, and its last moment
        if only is not None and i not in only: continue
        ts =[s["t0"] + 0.35, (s.get("vs", s["t0"]) + s.get("ve", s["t1"])) / 2, s["t1"] - 0.08]
        parts = []
        for k, t in enumerate(ts):
            p = os.path.join(rd, f"_s{i}_{k}.jpg"); ff("-ss", f"{max(0, t):.2f}", "-i", mp4, "-frames:v", "1", "-vf", "scale=360:-1", p); parts.append(p)
        name = f"scene{i:02d}_{s['kind']}_{ts[0]:.1f}s-{ts[2]:.1f}s.jpg"
        ff(*sum([["-i", p] for p in parts], []), "-filter_complex", "hstack=3", os.path.join(rd, name)); imgs.append(name)
        for p in parts: os.remove(p)
    H = heard(mp4)
    said = [(w, i) for i, s in enumerate(R["scenes"]) for w in say_as(s["vo"]).split()]
    sm = difflib.SequenceMatcher(None, [key(w) for w, _ in said], [key(w) for w, _, _ in H], autojunk=False)
    misheard = []
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op != "equal":
            misheard.append({"scene": said[a0][1] if a0 < len(said) else None, "script": " ".join(w for w, _ in said[a0:a1]),
                             "heard": " ".join(w for w, _, _ in H[b0:b1]), "at": round(H[b0][1], 2) if b0 < len(H) else None})
    scenes, Q = [], silences(R["vo"], T)
    SC = R["scenes"]   # each heard word belongs to the scene whose voice it is nearest (the first and last are open-ended)
    cut = [-1e9] + [(a.get("ve", a["t1"]) + b.get("vs", b["t0"])) / 2 for a, b in zip(SC, SC[1:])] + [1e9]
    for i, s in enumerate(SC):
        hw = [h for h in H if cut[i] <= h[1] < cut[i + 1]]
        clip = next(((f, o) for f, o in R["vo"] if f.endswith(f"/s{i}.wav")), None)
        if clip:   # what each scene says, its pace and caption sync, from its own voice track: in the mix, music and effects blur
                   # word edges and Whisper moves a scene's first word into the scene before (mix problems show in script_vs_heard_differences)
            hw = [(w, a + clip[1], b + clip[1]) for w, a, b in heard(clip[0])]
        r = talk_rate([(key(w), a, b) for w, a, b in hw])
        pauses = [{"after": next((w for w, _, b in reversed(hw) if b <= q0 + 0.15), ""), "secs": round(q1 - q0, 2), "at": round(q0, 2)}
                  for q0, q1 in Q if cut[i] <= q0 < cut[i + 1]]
        sync = []                                           # caption word time vs when it is heard
        tw = s.get("text_words") or []
        m = difflib.SequenceMatcher(None, [key(w) for w in tw], [key(w) for w, _, _ in hw], autojunk=False)
        for a0, b0, n in m.get_matching_blocks():
            for q in range(n):
                sync.append(round(s["wt"][a0 + q][0] - hw[b0 + q][1], 2))
        on_screen = {k: s[k] for k in ("head", "text", "badge", "options") if s.get(k)}
        for c in s.get("cues", []):
            if c.get("text") or c.get("label"): on_screen.setdefault("cue_texts", []).append(f"{c['do']}: {c.get('text') or c.get('label')} @ {c.get('t')}s")
        if s.get("items"): on_screen["cards"] = [x.get("text") for x in s["items"]]
        if s.get("figures"): on_screen["figures"] = [f"{f.get('label', '')} ({f.get('color', 'white')}, {f.get('pose', 'stand')})" for f in s["figures"]]
        scenes.append({"scene": i, "kind": s["kind"], "from_s": s["t0"], "to_s": s["t1"], "has_chart": s.get("chart") is not None,
                       "script": s["vo"], "heard": " ".join(w for w, _, _ in hw), "words_per_sec_talking": round(r, 2) if r else None,
                       "pauses_heard": pauses, "caption_minus_voice_secs": {"max_abs": max(map(abs, sync), default=None),
                       "mean": round(sum(sync) / len(sync), 2) if sync else None}, "on_screen": on_screen,
                       "cues": [f"{c.get('do')} on '{c.get('say', '')}' @ {c.get('t')}s" for c in s.get("cues", [])]})
    gaps = [q1 - q0 for q0, q1 in Q]
    wr = [(len(x["script"].split()), x["words_per_sec_talking"]) for x in scenes if x["words_per_sec_talking"]]
    report = {"title": R.get("title"), "format": R.get("type"), "length_secs": T,
              "caption_post_text": open(os.path.join(work, "caption.txt"), encoding="utf-8").read() if os.path.exists(os.path.join(work, "caption.txt")) else "",
              "human_narrator_reference": {"words_per_sec_talking": WPS, "pause_after_comma": HUMAN["comma"], "pause_after_sentence": HUMAN["sentence"],
                                           "source": "measured on 16 top finance Shorts narrated by people"},
              "whole_reel": {"words_per_sec_talking": round(sum(n for n, _ in wr) / max(1e-9, sum(n / r for n, r in wr)), 2),
                             "longest_silence_secs": round(max(gaps, default=0), 2), "silences_over_0.6s": sum(g > 0.6 for g in gaps)},
              "script_vs_heard_differences": misheard,
              "transcript_notes": "The script is shown as the voice is told to say it. Whisper writes 'Meem Street dot net' as "
                                  "MemeStreet.net or Meme Street, numbers as digits ('93' for 'ninety-three', '15%' for "
                                  "'fifteen percent') and may split or join words: those are not mispronunciations. A "
                                  "different word ('rice' for 'price', 'week' for 'weak' where the sense needs 'weak') may be.",
              "scenes": scenes, "images": imgs}
    json.dump(report, open(os.path.join(rd, "report.json"), "w"), indent=1, default=float)
    return report


SYSTEM = """You are a film maker with twenty years in short-form video, hired to approve or reject every Instagram Reel
before it goes out on Meme Street (a free stock market game with fictional companies, memestreet.net). You are harsh
and exact. You have watched thousands of finance Shorts and you know what holds a thumb and what loses it in a second.
Nothing reaches the audience until it is something you would put your own name on.

You judge, and score out of 10:
1. SYNC - every on-screen word, caption, marker and move lands exactly when the voice says it; nothing early, nothing late,
   nothing on screen that the voice does not explain, nothing said that the screen does not show.
2. VISUALS - appealing, clean, balanced, readable at a glance on a phone; every scene pops and gives the eye something new;
   no clutter, no ugly or cramped labels, no empty dead stage, no text touching other text, nothing cut off. Every piece
   of text is properly written: each title, head, card, bubble, label, caption sentence and the post caption starts with
   a capital letter, names are capitalised ('Ember Dragon Ranches', 'I'), no lowercase fragments ('level cost you 11%').
   A capitals fault is a script note (major on the hook or the end card).
3. AUDIO - smooth, human pacing: steady speed (real narrators: about 3.9 words a second while talking), natural pauses after
   commas (about 0.3 s) and sentences (about 0.35 s), never rushed, never dragging, no dead air; every word pronounced
   correctly (the transcript of the final mix against the script shows what a listener hears: a word heard differently
   is a mispronunciation unless it is clearly a homophone or a number written differently).
4. CONTENT - the story: a hook that earns the next second, a clear arc with a payoff that delivers the hook's promise,
   one idea, true and useful to a beginner trader, a reason to play the game, and an ending that makes people want the
   next reel. Language that sounds like a person, not an advert. In a stock story (format "Stock story"), the company's
   business is SHOWN, not just said: an animated scene whose sprites act out what the voice says (a dragon-rental
   company: dragons flying over a ranch; a foundry: metal pouring from a furnace), and its news acted out where it can
   be. A stock story with no animated scene, or with sprites that do not match the words or barely move, is a script
   major; an animation that looks broken (sprites cut off, piled on each other, floating where they should stand) is a
   renderer note.

You cannot hear the audio directly: you hear it through the report (what Whisper hears in the final mix, with times,
the talking speed and the pauses). You see the reel through the images (Read them all: a contact sheet at one frame a
second, and three frames per scene: as it lands, mid-line and its last moment, named with their times).
The frame below about 1440 px and the right edge are left empty on purpose: Instagram's caption, buttons and audio strip
cover them, so nothing may go there; do not mark that space down as dead.

Approve only if nothing would embarrass you. Be accurate before you are harsh: a note is only for something that is
wrong in THIS cut and that you can point at in this round's images or report.json. Judge only what is in front of you,
never what you remember of an earlier cut; do not invent problems to look tough, do not guess at what you cannot see,
and do not move the goalposts. Numbers (pauses, speeds, drift) come only from report.json, never from estimates.

Every note carries evidence, or it is thrown away unread: the image file(s) where it shows, named exactly as in
report.json "images", and/or a "report" quote copied character for character from report.json that proves it (for
example "secs": 0.62). A note also says exactly where (scene, time), what is wrong, the concrete fix, and a one-line
lesson: the general rule the writer must follow in EVERY future reel. Scenes count from 0, as in report.json.

Say who can fix it. The writer controls only the script: each scene's kind and order, its spoken line, head and
on-screen text, and its cues: which phrase each cue lands on, which candles are revealed, marked, shaded or zoomed,
each line's price, label and tone, cards, figures, poses, bubbles and sprites. That is "script", and its fix names the
change in those terms (e.g. "scene 1: a line cue at 119.42 labelled 'Entry', said on 'entry'"). Everything about how
the house template draws (where a tag sits, tags stacking, sizes, fonts, colours, the voice's pauses and pronunciation
of a word that is written right, the end card's layout) is "renderer": the writer cannot change it, so never give the
writer a renderer fix.

From round 2 you get a numbered checklist of your earlier notes that are still open, and the scenes that changed since
the last cut. For each checklist note, look at this cut: "fixed", or "still_wrong" with evidence from this cut. Never
repeat a checklist note as a new issue, and never write "not fixed from round N" in a new issue. Scenes that did not
change passed last round: judge the changed scenes and the scenes a checklist note names; raise a new note on an
unchanged scene only for a blocker.

Reply with JSON only:
{"approved": true|false, "scores": {"sync": n, "visuals": n, "audio": n, "content": n},
 "verdict": "two or three blunt sentences",
 "previous": [{"n": 1, "status": "fixed|still_wrong", "evidence": [{"image": "..."}, {"report": "..."}]}],
 "issues": [{"severity": "blocker|major|minor", "where": "scene 3, 12.4s", "what": "...", "fix": "...",
             "owner": "script|renderer", "lesson": "a rule for every future reel",
             "evidence": [{"image": "scene03_chart_12.1s-15.0s.jpg"}, {"report": "\\"secs\\": 0.62"}]}]}"""


def ask_critic(rd, rnd, prev, changed=None):
    """His review of this cut. `prev`: his checked notes still open from the last cut (a checklist); `changed`: the
    scenes rewritten since then (None: the first cut, judge everything)."""
    req = ("Review this reel. Read report.json in this folder, then Read every image it lists, then reply with the JSON.\n"
           f"This is round {rnd}.")
    if changed is not None:
        req += f"\nScenes changed since the last cut: {changed or 'none'} (only their frames, and those of the scenes the checklist names, are in this pack)."
    if prev:
        req += ("\nChecklist, your open notes on the last cut (they describe that cut, not this one; check each against this "
                "cut and answer in \"previous\"):\n" +
                "\n".join(f"{n}. [{x.get('severity')}] {x.get('where')}: {x.get('what')}" for n, x in enumerate(prev, 1)))
    r = subprocess.run(["claude", "-p", "--output-format", "text", "--model", os.environ.get("REEL_CRITIC_MODEL", "opus"),
                        "--append-system-prompt", SYSTEM, "--allowedTools", "Read",
                        "--disallowedTools", "Bash,Edit,Write,WebFetch,WebSearch,Task,NotebookEdit"],
                       input=req, capture_output=True, text=True, timeout=900, cwd=rd,
                       env={k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"})
    if r.returncode:
        raise SystemExit("critic failed: " + (r.stderr or r.stdout)[-400:])
    m = re.search(r"\{.*\}", r.stdout, re.S)
    rev = json.loads(m.group(0)) if m else {}
    if "approved" not in rev:
        raise SystemExit("critic gave no verdict: " + r.stdout[-300:])
    return rev


def verify(rev, rd, prev):
    """Keep only what this cut shows. A note stays if it has evidence and every piece checks out: each image is in this
    round's pack, each report quote is in report.json. A new note that repeats a checklist note is dropped (the checklist
    answers it); a checklist note stays open only as "still_wrong" with checked evidence. Approved = no checked script
    blocker or major left (template notes go to the to-do list and never block; scores are his opinion and are logged)."""
    imgs = set(os.listdir(rd))
    norm = lambda x: re.sub(r'[\s"\\]', "", str(x))
    rep = norm(open(os.path.join(rd, "report.json"), encoding="utf-8").read())
    def proved(ev):
        ev = [e for e in ev if isinstance(e, dict)] if isinstance(ev, list) else []
        return bool(ev) and all(e["image"] in imgs if e.get("image") else len(norm(e.get("report", ""))) >= 4 and norm(e.get("report", "")) in rep
                                for e in ev)
    same = lambda a, b: difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() > 0.72
    keep, drop = [], []
    for x in rev.get("issues", []):
        why = ("no evidence from this cut" if not proved(x.get("evidence")) else
               "repeats a checklist note" if any(same(x.get("what", ""), p.get("what", "")) for p in prev) else None)
        (drop if why else keep).append(dict(x, dropped=why) if why else x)
    for p in rev.get("previous", []):
        n = p.get("n")
        if isinstance(n, int) and 1 <= n <= len(prev) and p.get("status") == "still_wrong":
            (keep if proved(p.get("evidence")) else drop).append(dict(prev[n - 1], evidence=p.get("evidence"), still_open=True,
                                                                      **({} if proved(p.get("evidence")) else {"dropped": "still_wrong without evidence from this cut"})))
    rev.update(issues=keep, dropped=drop, critic_said_approved=rev.get("approved"))
    rev["approved"] = not any(x.get("severity") in ("blocker", "major") and x.get("owner", "script") != "renderer" for x in keep)
    return rev


def remember(path, items, slot, field):
    """Each item's `field` (a lesson, a template fault) becomes a new entry or strengthens a similar one."""
    L = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M")
    for x in items:
        txt = (x.get(field) or "").strip()
        if not txt: continue
        best = max(L, key=lambda y: difflib.SequenceMatcher(None, y[field].lower(), txt.lower()).ratio(), default=None)
        if best and difflib.SequenceMatcher(None, best[field].lower(), txt.lower()).ratio() > 0.72:
            best["count"] = best.get("count", 1) + 1; best["last"] = now
        else:
            L.append({field: txt, "owner": x.get("owner", "script"), "count": 1, "first": now, "last": now, "slot": slot,
                      **({"fix": x.get("fix", ""), "where": x.get("where", ""), "evidence": x.get("evidence")} if field == "what" else {})})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(L, open(path, "w", encoding="utf-8"), indent=1)


def learn(rev, slot):
    """Checked script notes become lessons the writer reads before every later reel; checked template notes go to the
    renderer to-do list (fixed in reel.html / narrate.py, not by the writer)."""
    iss = rev.get("issues", [])
    remember(LESSONS, [x for x in iss if x.get("owner", "script") != "renderer" and x.get("severity") != "minor" and not x.get("still_open")], slot, "lesson")
    remember(TODO, [x for x in iss if x.get("owner") == "renderer" and not x.get("still_open")], slot, "what")


def unstick(rev, slot):
    """Count how many rounds each script note has stayed open. One the writer has failed to change for three rounds is
    almost always the pipeline (a template line, a renamed level): it stops blocking and goes to the to-do list."""
    keep, stuck = [], []
    for x in rev.get("issues", []):
        x["rounds_open"] = x.get("rounds_open", 0) + 1 if x.get("still_open") else 1
        (stuck if x["rounds_open"] >= 3 and x.get("owner", "script") != "renderer" else keep).append(x)
    if stuck:
        remember(TODO, [dict(x, what="STUCK (the writer could not change it in 3 rounds): " + x.get("what", "")) for x in stuck], slot, "what")
        rev.update(issues=keep, stuck=stuck)
        rev["approved"] = not any(x.get("severity") in ("blocker", "major") and x.get("owner", "script") != "renderer" for x in keep)
    return rev


def run(cmd, **env):
    """Run a step; its output is shown, and on failure its last lines are the reason (SystemExit with them)."""
    r = subprocess.run(cmd, cwd=ROOT, env=dict(os.environ, **{k: str(v) for k, v in env.items()}),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(r.stdout, end="", flush=True)
    if r.returncode:
        raise SystemExit([l for l in r.stdout.strip().splitlines() if l.strip() and not l.startswith((" ", "Traceback"))][-1:] or [" ".join(cmd) + " failed"])


def loop(work, out):
    """Voice, render, review, rewrite... as many rounds as it takes, until he approves. Each rewrite touches only the
    scenes his checked notes name; only their lines are voiced again and only their frames go in the next pack."""
    slot = os.path.basename(os.path.normpath(work)); prev, old = [], None
    rd = os.path.join(work, "review")
    for rnd in itertools.count(1):
        scenes = json.load(open(os.path.join(work, "spec.json")))["scenes"]
        changed = None if old is None else [i for i, s in enumerate(scenes) if i >= len(old) or s != old[i]]
        old = scenes
        try:
            run(["python3", "src/narrate.py", work])
            run(["python3", "src/render.py", work, out], PAGE="reel.html", FPS=os.environ.get("REVIEW_FPS", "30"))
        except SystemExit as e:   # a QA gate stopped it (garbled voice, text on text): that is a send-back, not the end
            why = e.code[0] if isinstance(e.code, list) else str(e.code)
            rev = {"approved": False, "scores": None, "verdict": "The automatic checks stopped this cut before review: " + why,
                   "issues": [{"severity": "blocker", "where": "automatic check", "what": why, "owner": "script",
                               "fix": "Rewrite the part named so the check passes: plainer words the voice can say, shorter on-screen text.",
                               "lesson": ""}]}
        else:
            named = {int(n) for x in prev for n in re.findall(r"scene (\d+)", x.get("where", ""))}
            pack(work, out, rd, None if changed is None else sorted(set(changed) | named))
            while True:
                try:
                    rev = verify(ask_critic(rd, rnd, prev, changed), rd, prev); break
                except (SystemExit, subprocess.TimeoutExpired, ValueError) as e:   # (the critic call failed: wait, ask again)
                    print(f"critic round {rnd}: no review ({str(e)[:200]}); asking again in 5 minutes", flush=True); time.sleep(300)
        rev = unstick(rev, slot)
        json.dump(rev, open(os.path.join(work, f"review-{rnd}.json"), "w"), indent=1)
        print(f"critic round {rnd}: {'APPROVED' if rev['approved'] else 'sent back'} {rev.get('scores')} - {rev.get('verdict', '')}", flush=True)
        for x in rev.get("issues", []):
            print(f"   [{x.get('severity')}/{x.get('owner')}{'/still open' if x.get('still_open') else ''}] {x.get('where')}: {x.get('what')}", flush=True)
        for x in rev.get("dropped", []):
            print(f"   dropped ({x.get('dropped')}): {x.get('where')}: {str(x.get('what'))[:160]}", flush=True)
        for x in rev.get("stuck", []):
            print(f"   stuck 3 rounds, to the to-do list: {x.get('where')}: {str(x.get('what'))[:160]}", flush=True)
        learn(rev, slot)
        if rev["approved"]:
            run(["python3", "src/render.py", work, out], PAGE="reel.html", FPS=os.environ.get("AUTO_FPS", "60"))   # (the same frames, smoother)
            json.dump({"round": rnd, "scores": rev.get("scores"), "verdict": rev.get("verdict"),
                       "at": datetime.datetime.now(datetime.UTC).isoformat()}, open(os.path.join(out, "approved.json"), "w"))
            return rnd
        prev = [x for x in rev["issues"] if x.get("owner", "script") != "renderer" and x.get("where") != "automatic check"]
        while True:
            try:
                run(["python3", "src/make_spec.py", "revise", work, os.path.join(work, f"review-{rnd}.json")]); break
            except SystemExit as e:   # (the rewrite did not pass its checks in five tries: it tries again)
                print(f"rewrite after round {rnd} did not pass its checks ({e.code}); trying again", flush=True)


def demo():
    """The evidence check: made-up frames, made-up quotes, repeats and unproved 'still wrong' answers are dropped."""
    rd = tempfile.mkdtemp()
    json.dump({"scenes": [{"pauses_heard": [{"after": "high,", "secs": 0.33}]}]}, open(os.path.join(rd, "report.json"), "w"), indent=1)
    open(os.path.join(rd, "scene02_chart_5.0s-9.0s.jpg"), "w").close()
    prev = [{"severity": "major", "owner": "script", "where": "scene 1, 4s", "what": "The Stop tag touches the price tag."}]
    rev = {"approved": False, "issues": [
        {"severity": "major", "owner": "script", "what": "real, seen", "evidence": [{"image": "scene02_chart_5.0s-9.0s.jpg"}]},
        {"severity": "major", "owner": "script", "what": "a frame that is not in the pack", "evidence": [{"image": "scene09_x.jpg"}]},
        {"severity": "major", "owner": "script", "what": "a 0.72 s pause", "evidence": [{"report": '"secs": 0.72'}]},
        {"severity": "minor", "owner": "script", "what": "a 0.33 s pause after high", "evidence": [{"report": '"secs": 0.33'}]},
        {"severity": "major", "owner": "script", "what": "no evidence at all"},
        {"severity": "major", "owner": "script", "what": "The Stop tag touches the price tag!", "evidence": [{"image": "scene02_chart_5.0s-9.0s.jpg"}]},
        {"severity": "blocker", "owner": "renderer", "what": "template", "evidence": [{"image": "scene02_chart_5.0s-9.0s.jpg"}]}],
        "previous": [{"n": 1, "status": "still_wrong"}]}
    v = verify(rev, rd, prev)
    assert [x["what"] for x in v["issues"]] == ["real, seen", "a 0.33 s pause after high", "template"], v["issues"]
    assert len(v["dropped"]) == 5 and not v["approved"]
    v = verify({"issues": [{"severity": "blocker", "owner": "renderer", "what": "t", "evidence": [{"image": "scene02_chart_5.0s-9.0s.jpg"}]}],
                "previous": [{"n": 1, "status": "still_wrong", "evidence": [{"report": '"after": "high,"'}]}]}, rd, prev)
    assert [x.get("still_open") for x in v["issues"]] == [None, True] and not v["approved"]
    assert verify({"issues": [], "previous": [{"n": 1, "status": "fixed"}]}, rd, prev)["approved"]
    global TODO
    TODO, old = os.path.join(rd, "todo.json"), TODO
    note = {"severity": "blocker", "owner": "script", "what": "stuck", "evidence": [{"image": "scene02_chart_5.0s-9.0s.jpg"}]}
    v = unstick(verify({"issues": [note], "previous": []}, rd, []), "t")
    assert v["issues"][0]["rounds_open"] == 1 and not v["approved"]
    for r in (2, 3):                                     # the same note, still wrong in the next two cuts
        v = unstick(verify({"issues": [], "previous": [{"n": 1, "status": "still_wrong", "evidence": note["evidence"]}]}, rd, v["issues"] or v["stuck"]), "t")
    assert v["approved"] and v["stuck"][0]["rounds_open"] == 3 and "STUCK" in json.load(open(TODO))[0]["what"]
    TODO = old
    print("verify ok")


if __name__ == "__main__":
    if sys.argv[1] == "demo":
        demo()
    elif sys.argv[1] == "loop":
        loop(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "review":
        w, o = sys.argv[2], sys.argv[3]; n = len(glob.glob(os.path.join(w, "review-*.json"))) + 1
        pack(w, o, os.path.join(w, "review")); rev = verify(ask_critic(os.path.join(w, "review"), n, []), os.path.join(w, "review"), [])
        json.dump(rev, open(os.path.join(w, f"review-{n}.json"), "w"), indent=1); print(json.dumps(rev, indent=1))
