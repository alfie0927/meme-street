"""The film critic: every finished reel is watched by a harsh film maker (Claude, on the owner's plan) before it may be
posted. He gets a review pack made from the real render: frames of every scene, a contact sheet, what the voice is
heard saying (Whisper on the final mix) against the script, the pacing against real narrators, and how far every
caption sits from its word. He approves, or sends it back with notes; the writer rewrites from the notes
(make_spec.py revise) and the reel is voiced, rendered and reviewed again, until he approves (at most MAX_ROUNDS).
Every reason for a send-back becomes a lesson the writer reads before every later reel (state/lessons.json).

  python3 src/critic.py loop <work> <out>     voice, render, review, rewrite... -> <out>/approved.json at 60 fps
  python3 src/critic.py review <work> <out>   review one rendered reel -> <work>/review-<n>.json
"""
import datetime, difflib, glob, json, math, os, re, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from pronounce import say_as
from narrate import WPS, HUMAN, talk_rate

MAX_ROUNDS = int(os.environ.get("MAX_ROUNDS", "4"))
LESSONS = os.path.join(ROOT, "state", "lessons.json")
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


key = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())


def pack(work, out, rd):
    """The review pack: images to look at and a report of what is heard and when."""
    R = json.load(open(os.path.join(work, "timeline.json")))
    mp4 = os.path.join(out, "reel.mp4"); os.makedirs(rd, exist_ok=True)
    for f in glob.glob(os.path.join(rd, "*.jpg")): os.remove(f)
    T = R["T"]; ff = lambda *a: subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)
    ff("-i", mp4, "-vf", f"fps=1,scale=180:-1,tile=8x{math.ceil(T / 8)}", "-frames:v", "1", os.path.join(rd, "contact_sheet_1fps.jpg"))
    imgs = ["contact_sheet_1fps.jpg"]
    for i, s in enumerate(R["scenes"]):                      # each scene: as it lands, mid-line, and its last moment
        ts = [s["t0"] + 0.35, (s.get("vs", s["t0"]) + s.get("ve", s["t1"])) / 2, s["t1"] - 0.08]
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
    scenes = []
    SC = R["scenes"]   # each heard word belongs to the scene whose voice it is nearest (the first and last are open-ended)
    cut = [-1e9] + [(a.get("ve", a["t1"]) + b.get("vs", b["t0"])) / 2 for a, b in zip(SC, SC[1:])] + [1e9]
    for i, s in enumerate(SC):
        hw = [h for h in H if cut[i] <= h[1] < cut[i + 1]]
        r = talk_rate([(key(w), a, b) for w, a, b in hw])
        pauses = [{"after": a[0], "secs": round(b[1] - a[2], 2), "at": round(a[2], 2)} for a, b in zip(hw, hw[1:]) if b[1] - a[2] >= 0.15]
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
    gaps = [b[1] - a[2] for a, b in zip(H, H[1:])]
    report = {"title": R.get("title"), "format": R.get("type"), "series": R.get("series"), "length_secs": T,
              "caption_post_text": open(os.path.join(work, "caption.txt"), encoding="utf-8").read() if os.path.exists(os.path.join(work, "caption.txt")) else "",
              "human_narrator_reference": {"words_per_sec_talking": WPS, "pause_after_comma": HUMAN["comma"], "pause_after_sentence": HUMAN["sentence"],
                                           "source": "measured on 16 top finance Shorts narrated by people"},
              "whole_reel": {"words_per_sec_talking": round(talk_rate([(key(w), a, b) for w, a, b in H]) or 0, 2),
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
   no clutter, no ugly or cramped labels, no empty dead stage, no text touching other text, nothing cut off.
3. AUDIO - smooth, human pacing: steady speed (real narrators: about 3.9 words a second while talking), natural pauses after
   commas (about 0.3 s) and sentences (about 0.35 s), never rushed, never dragging, no dead air; every word pronounced
   correctly (the transcript of the final mix against the script shows what a listener hears: a word heard differently
   is a mispronunciation unless it is clearly a homophone or a number written differently).
4. CONTENT - the story: a hook that earns the next second, a clear arc with a payoff that delivers the hook's promise,
   one idea, true and useful to a beginner trader, a reason to play the game, and an ending that makes people want the
   next reel. Language that sounds like a person, not an advert.

You cannot hear the audio directly: you hear it through the report (what Whisper hears in the final mix, with times,
the talking speed and the pauses). You see the reel through the images (Read them all: a contact sheet at one frame a
second, and three frames per scene: as it lands, mid-line and its last moment, named with their times).
The frame below about 1440 px and the right edge are left empty on purpose: Instagram's caption, buttons and audio strip
cover them, so nothing may go there; do not mark that space down as dead.

Approve only if every score is 8 or more and nothing would embarrass you. Do not invent problems to look tough, and
do not move the goalposts: judge what is in front of you. When you send it back, every note says exactly where (scene,
time), what is wrong and the concrete fix, and a one-line lesson: the general rule the writer must follow in EVERY
future reel so you never see this again. Say whether the fix belongs to the "script" (words, scenes, cues, on-screen
text, which the writer controls) or the "renderer" (how the house template draws things, which the writer cannot change).

Reply with JSON only:
{"approved": true|false, "scores": {"sync": n, "visuals": n, "audio": n, "content": n},
 "verdict": "two or three blunt sentences",
 "issues": [{"severity": "blocker|major|minor", "where": "scene 3, 12.4s", "what": "...", "fix": "...",
             "owner": "script|renderer", "lesson": "a rule for every future reel"}]}"""


def ask_critic(rd, rnd, prev):
    req = ("Review this reel. Read report.json in this folder, then Read every image it lists, then reply with the JSON.\n"
           f"This is round {rnd}.")
    if prev:
        req += ("\nYour notes on the previous cut were:\n" + json.dumps(prev.get("issues", []), indent=1) +
                "\nCheck each one was fixed; judge the rest fresh.")
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
    sc = rev.get("scores") or {}
    rev["approved"] = bool(rev["approved"]) and all(isinstance(v, (int, float)) and v >= 8 for v in sc.values()) \
        and not any(x.get("severity") == "blocker" for x in rev.get("issues", []))
    return rev


def learn(rev, slot):
    """Each reason for a send-back becomes (or strengthens) a lesson for every later reel."""
    L = json.load(open(LESSONS, encoding="utf-8")) if os.path.exists(LESSONS) else []
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M")
    for x in rev.get("issues", []):
        les = (x.get("lesson") or "").strip()
        if not les or x.get("severity") == "minor": continue
        best = max(L, key=lambda y: difflib.SequenceMatcher(None, y["lesson"].lower(), les.lower()).ratio(), default=None)
        if best and difflib.SequenceMatcher(None, best["lesson"].lower(), les.lower()).ratio() > 0.72:
            best["count"] = best.get("count", 1) + 1; best["last"] = now
        else:
            L.append({"lesson": les, "owner": x.get("owner", "script"), "count": 1, "first": now, "last": now, "slot": slot})
    os.makedirs(os.path.dirname(LESSONS), exist_ok=True)
    json.dump(L, open(LESSONS, "w", encoding="utf-8"), indent=1)


def run(cmd, **env):
    """Run a step; its output is shown, and on failure its last lines are the reason (SystemExit with them)."""
    r = subprocess.run(cmd, cwd=ROOT, env=dict(os.environ, **{k: str(v) for k, v in env.items()}),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(r.stdout, end="", flush=True)
    if r.returncode:
        raise SystemExit([l for l in r.stdout.strip().splitlines() if l.strip() and not l.startswith((" ", "Traceback"))][-1:] or [" ".join(cmd) + " failed"])


def loop(work, out):
    slot = os.path.basename(os.path.normpath(work)); prev = None
    for rnd in range(1, MAX_ROUNDS + 1):
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
            pack(work, out, os.path.join(work, "review"))
            rev = ask_critic(os.path.join(work, "review"), rnd, prev)
        json.dump(rev, open(os.path.join(work, f"review-{rnd}.json"), "w"), indent=1)
        print(f"critic round {rnd}: {'APPROVED' if rev['approved'] else 'sent back'} {rev.get('scores')} - {rev.get('verdict', '')}", flush=True)
        for x in rev.get("issues", []):
            print(f"   [{x.get('severity')}/{x.get('owner')}] {x.get('where')}: {x.get('what')}", flush=True)
        if rev["approved"]:
            run(["python3", "src/render.py", work, out], PAGE="reel.html", FPS=os.environ.get("AUTO_FPS", "60"))   # (the same frames, smoother)
            json.dump({"round": rnd, "scores": rev.get("scores"), "verdict": rev.get("verdict"),
                       "at": datetime.datetime.now(datetime.UTC).isoformat()}, open(os.path.join(out, "approved.json"), "w"))
            return rnd
        learn(rev, slot)
        if rnd < MAX_ROUNDS:
            run(["python3", "src/make_spec.py", "revise", work, os.path.join(work, f"review-{rnd}.json")])
        prev = rev
    raise SystemExit(f"the critic did not approve the reel in {MAX_ROUNDS} rounds: nothing is posted")


if __name__ == "__main__":
    if sys.argv[1] == "loop":
        loop(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "review":
        w, o = sys.argv[2], sys.argv[3]; n = len(glob.glob(os.path.join(w, "review-*.json"))) + 1
        pack(w, o, os.path.join(w, "review")); rev = ask_critic(os.path.join(w, "review"), n, None)
        json.dump(rev, open(os.path.join(w, f"review-{n}.json"), "w"), indent=1); print(json.dumps(rev, indent=1))
