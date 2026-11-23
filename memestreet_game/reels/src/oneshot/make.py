"""Meme Street's one reel a day: the story behind the day's Daily stock, told as a one-shot 3D money story.

The owner, 2026-11-22: "completely remake everything from the ground up ... copy their styles, there should be NO differences
(except mine is one unique style for all reels)"; then, on the first cut: "the animation could be more creative, like the person
should sit at their laptop and start typing, then the camera transitions to the computer screen and starts typing in the trade ...
only post ONCE a day (at 23:30) and the story should be about the stock that was picked for the daily on that day. talk about why
it moved like it did, what happened, etc, introduce characters, and everything. make sure it's in the same style and make it
DYNAMIC and creative."
  the story   the day's Daily stock over its window (data/<date>.json: the real ticker, the dates, the real prices), researched
              with sources (news_reel.research: every claim with its status), told in How Money Works' rhythm (COPY.md):
              hook / setup / terms / move / payoff / sting, figures said and shown, no question, no moral, no call to action;
              up to three characters by role (THE CEO, A DAY TRADER), each tagged when the story first turns to them.
  the picture one trading office, faceless low-poly people, one unbroken camera move that never rests and never cuts, depth
              of field, amber captions; each sentence its own shot: walk, type (they sit at the laptop, type the trade, the camera
              dives into the screen), wall (the big display: breaking news, the real price line, a counter), meet, react, crowd.
  the sound   a man's voice from frame 0 at ~3.6 words a second, a tonal bed with no beat, a soft hit in most pauses, -14.5 LUFS.
It is queued for <date>T2330 only when at least PASS of the 13 simulated viewers (lab/audience.py) watch to the end.

  python3 src/oneshot/make.py daily [YYYY-MM-DD]        the day's reel: fetch, research, write, voice, direct, render, check, queue
  python3 src/oneshot/make.py dailytry <date> <dir>     the same into <dir>, not queued
  python3 src/oneshot/make.py spec <spec.json> <dir>    voice, direct and render a written script (PANEL=1: with the panel)
  python3 src/oneshot/make.py preview <spec.json> <dir> voice and direct, then the panel's two images only
  python3 src/oneshot/make.py demo                      self-check: no Claude, no voice, no render
"""
import asyncio, difflib, json, math, os, re, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.dirname(HERE); ROOT = os.path.dirname(SRC)
sys.path.insert(0, SRC)
STATE = os.path.join(ROOT, "state", "oneshot.json")
VOICE = os.environ.get("ONESHOT_VOICE", "am_michael")
TALK = 3.6                                   # words a second while talking (the exemplars: 3.30 to 3.45)
GAP = {"comma": .12, "stop": .45, "hook": .75, "sting": .65, "payoff": .6}   # (How Money Works reads nearly unbroken: ~3.1 words a second overall)   # (pauses: production.md A variant; true_stories.md 5.1)
FPS = int(os.environ.get("ONESHOT_FPS", "30"))
BEATS = ["hook", "setup", "terms", "move", "payoff", "sting"]
SHOTS = ["walk", "type", "wall", "meet", "react", "crowd"]
LOOKS = ["man_tie", "man_sleeves", "man", "woman"]   # (dressed, and they can sit: the only models with a Sitting clip)
SET = {   # the trading office (oneshot.js SETS.office): the spots people use [x, z, facing], what stands where (for the camera)
    "W": 9, "D": 16,
    "seat": (-2.6, 1.08, math.pi), "seat_via": (-1.3, 1.25), "lap": (-2.6, 1.0, .76),
    "wall": (.32, -5.5, math.pi), "display": (0, 1.8, -7.97), "dw": 2.6,
    "homes": [(.4, .9, math.pi), (.7, -2.4, -2.4), (-.5, -1.4, 2.4)],
    "walks": [(.3, -3.6), (-.2, 2.6), (.5, -.6)],
    "meet": [(.55, -1.6), (-.35, -2.4)],
    "boxes": [(-3.5, -6.1, -1.7, -4.3), (-3.5, -3.1, -1.7, -1.3), (-3.5, -.1, -1.7, 1.75), (1.7, -6.1, 3.5, -4.3), (1.7, -3.1, 3.5, -1.3),
              (1.7, -.1, 3.5, 1.7), (3.7, -4.6, 4.5, 4.0), (-4.5, -3.6, -3.7, 4.0)],
    "extras": [["man_sleeves", -2.6, -4.8, math.pi, "Sitting"], ["woman", 2.6, -1.8, math.pi, "Sitting"], ["man_tie", 2.6, -4.8, math.pi, "Sitting"]],
}
DISCLAIMER = "Practice money only. Not investment advice."
say = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- the writer
def system():
    return ("You write one short vertical money-story video for Meme Street (memestreet.net, a free daily stock-chart game): the true "
            "story behind the stock in today's Daily, over the exact stretch of time the game showed. You copy a proven format: How Money "
            "Works' winning Shorts. The spec and its winners, word for word, follow. Copy their sentence lengths, their rhythm, their "
            "hook pattern, their beat order and their endings. Only the story differs: it is the true story you are given.\n\n"
            + open(os.path.join(HERE, "COPY.md"), encoding="utf-8").read())


def story_text(story):
    """Everything the writer may say, as one block (the facts check reads the same block)."""
    return json.dumps({k: story[k] for k in ("stock", "window", "prices", "research") if k in story}, indent=1)


def ask(story, fix=None, recent=(), critique=None):
    return ("THE TRUE STORY. Every figure, date, name and claim you write must be in here, nothing else:\n" + story_text(story) +
            "\n\nWRITE the reel as JSON only:\n"
            '{"title": the title in the winners\' pattern (9 to 15 words, one loaded word, the stock named),\n'
            ' "ticker": the screens\' header, at most 14 letters (the ticker),\n'
            ' "cast": 1 to 3 characters of the story, by role, never a private person: [{"id": a short id, "tag": who they are on screen, '
            'at most 18 letters ("THE CEO", "A DAY TRADER", "SHORT SELLERS", "WALL STREET"), "look": one of ' + json.dumps(LOOKS) + '}],\n'
            ' "sentences": [6 to 9 of {"beat": one of ' + json.dumps(BEATS) + ', "say": the sentence, "who": the cast id the camera is on,\n'
            '   "shot": one of ' + json.dumps(SHOTS) + ',\n'
            '   "screen": what the screen shows (needed for type and wall, else null): {"lines": 1 to 3 lines of at most 20 letters, typed out '
            '(for type: the trade itself, "BUY 500 GPRO", "AT $4.80"), "news": 1 or 2 headline lines of at most 20 letters (wall only), '
            '"chart": null or how far through the window the real price line has got by this sentence, 0 to 1 (0 = the first day, 1 = the last), '
            '"count": null or {"to": a number, "prefix": "$", "suffix": "%"} (a counter rolling up to it)},\n'
            '   "card": null or {"top": a figure, "bot": the figure it is set against} (each at most 10 letters, both said in this sentence)}],\n'
            ' "caption": the post caption: the title as its first line, then the whole script as one paragraph}\n\n'
            "THE SHOTS (one unbroken take; each sentence its own shot, so the film keeps moving): walk = the character crosses the "
            "office, the camera tracking beside them; type = they sit at the laptop and type the trade, the camera dives into the screen "
            "until the screen IS the frame; wall = they step up to the big wall display (breaking news, the real price line climbing or "
            "crashing, a counter); meet = two characters face each other, the camera circling them (who is one of them, the other is the "
            "next cast member); react = the camera pushes in on them as the news lands; crowd = everyone in the room, the camera rising "
            "high and wide. Use at least 4 different shots, at least one type and at least one wall, never the same shot twice in a row.\n"
            "THE CHARACTERS: introduce each one the first time the camera is on them (the tag appears then); every cast member is the "
            "'who' of at least one sentence. Name a person only if the research names them as a public figure; otherwise the role.\n"
            "RULES: 160 to 210 words in all. The hook is ONE statement of 15 to 25 words holding the stock and its biggest figure and "
            "why it is surprising; no question, no 'you', no 'did you know', no 'imagine'. Beats in the order hook, setup, terms, move, "
            "payoff, sting (a beat may span two sentences). Tell WHY it moved: the events, in order, each from the research. A fact "
            "marked 'reported' is said with its outlet ('Reuters reported'). The sting is ONE sentence of 16 to 37 words, a further "
            "true fact opening with a turning word ('The best part is', 'Despite', 'Tragically', 'Even'); no moral, no lesson, no "
            "question, no call to follow, like or comment, never 'Meme Street'. Long, clause-chained sentences (mostly 17 to 34 words). "
            "AT MOST 9 NUMBERS IN THE WHOLE SCRIPT (dates count): the ones the story needs. Say prices the simple way ('$4.80', "
            "'about $8'). The chart points rise from sentence to sentence (the line only moves forward in time). At most one card."
            + (("\n\nRecent titles, not to repeat: " + json.dumps(list(recent)[-12:])) if recent else "")
            + (("\n\nTHE LAST CUT WAS SHOWN TO A PANEL OF VIEWERS AND SOME SWIPED AWAY. Your last script:\n" + json.dumps(critique["spec"]["sentences"]) +
                "\nWho left, when and why:\n" + critique["why"] + "\nKeep the format; change what made them leave (a stronger first "
                "sentence, a figure sooner, a sharper turn, livelier shots), then reply with the whole JSON again.") if critique else ""))


def parse(txt):
    m = re.search(r"\{.*\}", txt, re.S)
    if not m: raise ValueError("no JSON in the reply")
    return json.loads(m.group(0))


NUMW = re.compile(r"\$?\d[\d,.]*%?")
SCALE = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
def nums(text):
    """The figures in a text, as plain digit strings ('$60,000' -> '60000'; '4.5%' -> '4.5'); years included. A figure with a
    scale word counts in both forms ('$200 million' -> '200' and '200000000'), so a screen's counter can roll to it."""
    out = {re.sub(r"[^\d.]", "", x).rstrip(".") for x in NUMW.findall(text or "") if re.sub(r"[^\d]", "", x)}
    for n, w in re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*(thousand|million|billion|trillion)", text or "", re.I):
        v = float(n.replace(",", "")) * SCALE[w.lower()]; out.add(str(int(v)) if v == int(v) else str(v))
    for x in list(out):                                  # ('8.04' allows 'about $8'; '4.80' allows '$4.8')
        if "." in x: out |= {x.rstrip("0").rstrip("."), str(round(float(x)))}
    return out


def errors(spec, story):
    """Everything the format can check in code, in words the writer can act on."""
    E = []; S = spec.get("sentences") or []; C = spec.get("cast") or []; ids = [c.get("id") for c in C]
    if not 6 <= len(S) <= 9: E.append(f"{len(S)} sentences: write 6 to 9")
    words = sum(len(str(s.get("say", "")).split()) for s in S)
    if not 160 <= words <= 210: E.append(f"{words} words: write 160 to 210")
    order = [BEATS.index(s.get("beat")) if s.get("beat") in BEATS else -1 for s in S]
    if -1 in order: E.append("every sentence's beat is one of " + ", ".join(BEATS))
    elif order != sorted(order) or order[0] != 0 or order[-1] != 5 or 4 not in order: E.append("beats in order: hook first, a payoff, the sting last")
    if S:
        h = str(S[0].get("say", "")); hw = len(h.split())
        if not 15 <= hw <= 25: E.append(f"the hook is {hw} words: one statement of 15 to 25")
        if "?" in h or re.search(r"\b(you|your|imagine|did you know)\b", h, re.I): E.append("the hook is a statement: no question, no 'you', no 'imagine'")
        if not nums(h): E.append("the hook holds the story's biggest figure")
        st = str(S[-1].get("say", "")); sw = len(st.split())
        if not 14 <= sw <= 40: E.append(f"the sting is {sw} words: one sentence of 16 to 37")
        if "?" in st or re.search(r"\b(follow|subscribe|comment|like and|meme ?street|lesson|moral)\b", st, re.I): E.append("the sting is a further fact: no question, no moral, no call to follow, like or comment")
    txt = " ".join(str(s.get("say", "")) for s in S); facts = story_text(story)
    shown = " ".join(" ".join(str(l) for l in ((s.get("screen") or {}).get("lines") or []) + ((s.get("screen") or {}).get("news") or []))
                     + " " + str(((s.get("screen") or {}).get("count") or {}).get("to", "")) + " " + " ".join(str(v) for v in (s.get("card") or {}).values()) for s in S)
    extra = sorted(nums(txt + " " + shown) - nums(facts) - {"0", "1", "2", "3"})
    if extra: E.append("these figures are not in the true story: " + ", ".join(extra) + " (use only its own figures)")
    OPEN = {"in", "by", "at", "then", "when", "the", "this", "these", "despite", "after", "on", "as", "for", "but", "and", "so", "even",
            "a", "an", "within", "over", "until", "while", "that", "its", "his", "her", "their", "tragically"}   # (a sentence's first word, not a name)
    names = {m for m in re.findall(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b", txt) if m.split()[0].lower() not in OPEN and m.lower() not in facts.lower()}
    if names: E.append("these names are not in the research: " + ", ".join(sorted(names)) + " (name only its public figures; otherwise the role)")
    nn = len(NUMW.findall(txt))
    if nn > 9: E.append(f"{nn} numbers in the script: at most 9; keep only the ones the story needs")
    if not 1 <= len(C) <= 3: E.append("1 to 3 cast members")
    if len(set(ids)) != len(ids) or not all(ids): E.append("every cast member has its own id")
    for c in C:
        if c.get("look") not in LOOKS: E.append("a cast member's look is one of " + ", ".join(LOOKS))
        if not 2 <= len(str(c.get("tag", ""))) <= 18: E.append("a tag is at most 18 letters")
        if not any(s.get("who") == c.get("id") for s in S): E.append(f"cast member '{c.get('id')}' is never the one the camera is on")
    shots = [s.get("shot") for s in S]
    if any(x not in SHOTS for x in shots): E.append("every shot is one of " + ", ".join(SHOTS))
    if "type" not in shots or "wall" not in shots: E.append("at least one type shot and one wall shot")
    if len(set(shots)) < 4: E.append("at least 4 different shots")
    if any(a == b for a, b in zip(shots, shots[1:])): E.append("never the same shot twice in a row")
    if "meet" in shots and len(C) < 2: E.append("a meet needs two cast members")
    last = -1.0; cards = 0
    for s in S:
        if s.get("who") not in ids: E.append("every sentence's 'who' is a cast id")
        q = s.get("screen") or {}
        if s.get("shot") == "type" and not q.get("lines"): E.append("a type shot types the trade: its screen has lines")
        if s.get("shot") == "wall" and not (q.get("news") or q.get("chart") is not None or q.get("count")): E.append("a wall shot shows news, the chart or a count")
        if any(len(str(l)) > 20 for l in (q.get("lines") or []) + (q.get("news") or [])) or len(q.get("lines") or []) > 3 or len(q.get("news") or []) > 2: E.append("screen lines: at most 3 (news 2), each at most 20 letters")
        if q.get("chart") is not None:
            try: k = float(q["chart"]); assert 0 <= k <= 1 and k >= last; last = k
            except Exception: E.append("chart points run from 0 to 1 and only move forward")
        if q.get("count") and not isinstance(q["count"].get("to"), (int, float)): E.append("a screen count's 'to' is a number")
        if s.get("card"):
            cards += 1; c = s["card"]
            if any(len(str(c.get(k, ""))) > 10 or str(c.get(k, "")) not in str(s.get("say", "")) for k in ("top", "bot")): E.append("a card's two figures are at most 10 letters each and both said in its sentence")
    if cards > 1: E.append("at most one card")
    if len(str(spec.get("ticker", ""))) > 14: E.append("the ticker is at most 14 letters")
    if not 9 <= len(str(spec.get("title", "")).split()) <= 15: E.append("the title is 9 to 15 words")
    return E


def write(story, recent=(), critique=None):
    import make_spec as M
    sysp, fix, spec = system(), None, None
    msgs = [{"role": "user", "content": ask(story, None, recent, critique)}]
    for k in range(5):                                   # (a fix sees its own last script: fresh rewrites kept making new faults)
        reply = M.claude_cli(msgs, sysp, model=os.environ.get("ONESHOT_MODEL", "opus"))
        try: spec = parse(reply); fix = errors(spec, story)
        except ValueError as e: spec, fix = None, [f"the reply was not valid JSON ({str(e)[:80]})"]
        if not fix: return spec
        say("the format sent it back:", "; ".join(fix))
        msgs += [{"role": "assistant", "content": reply},
                 {"role": "user", "content": "Sent back. Change only what these name, keep the rest, and reply with the whole JSON again: " + "; ".join(fix)}]
    raise SystemExit("not made: the script failed the format five times: " + "; ".join(fix))


# ---------------------------------------------------------------- the voice
def phrases(spec):
    """The script as spoken phrases: each sentence split at its commas; the pause after each (the exemplars' own)."""
    S = spec["sentences"]; out = []
    big = max(range(len(S)), key=lambda i: S[i].get("beat") == "payoff")
    for i, s in enumerate(S):
        parts = [p.strip() for p in re.split(r"(?<=,)\s+", str(s["say"]).strip()) if p.strip()]
        for j, p in enumerate(parts):
            last = j == len(parts) - 1
            gap = GAP["comma"] if not last else GAP["hook"] if i == 0 else GAP["sting"] if i == len(S) - 2 else GAP["payoff"] if i == big else GAP["stop"]
            out.append({"i": i, "text": p, "gap": 0 if (last and i == len(S) - 1) else gap})
    return out


def spoken(text):
    """What the voice reads (the captions keep the text): '$60,000' -> '60,000 dollars', '$17 million' -> '17 million dollars',
    '4%' -> '4 percent' (Kokoro read "$60,000" as "dollars sixty thousand")."""
    text = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)(\s+(?:thousand|million|billion|trillion))?", lambda m: f"{m.group(1)}{m.group(2) or ''} dollars", text)
    return re.sub(r"(\d)%", r"\1 percent", text)


def voice(spec, work):
    """Each phrase in the voice at the copied pace: spoken once, measured, spoken again at the speed that gives ~3.4 words a
    second. -> (wav path, [(i, start, end, text)] phrase times, T)."""
    import numpy as np, soundfile as sf
    from kokoro_onnx import Kokoro
    from voice import MODEL, trim
    K = Kokoro(os.path.join(MODEL, "kokoro-v1.0.onnx"), os.path.join(MODEL, "voices-v1.0.bin"))
    P = phrases(spec); SR = 24000; clips = []
    def make(text, sp):
        a, sr = K.create(spoken(text), voice=VOICE, speed=sp, lang="en-us"); return trim(np.asarray(a, np.float32), sr)
    for p in P:
        a = make(p["text"], 1.0); n = len(p["text"].split())
        sp = min(1.25, max(.8, TALK / max(.5, n / (len(a) / SR)))) if n >= 3 else 1.0     # (rate of this phrase at 1.0 -> the speed for 3.4)
        if abs(sp - 1) > .04: a = make(p["text"], sp)
        clips.append(a)
    t, segs, parts = 0.0, [], []
    for p, a in zip(P, clips):
        segs.append((p["i"], t, t + len(a) / SR, p["text"])); parts += [a, np.zeros(int(p["gap"] * SR), np.float32)]; t += len(a) / SR + p["gap"]
    wav = os.path.join(work, "voice.wav"); sf.write(wav, np.concatenate(parts), SR)
    return wav, segs, t + .9                    # (the last word ends ~0.9 s before the file: the exemplars)


def word_times(wav, segs):
    """Every written word with its spoken time: the transcriber's words aligned to the script's; a word it missed gets its
    place inside its own phrase by its length."""
    from voice import words as asr
    W = asr(wav); out = []
    for i, a, b, text in segs:
        toks = text.split(); L = [len(re.sub(r"\W", "", x)) + 2 for x in toks]; c = a
        for tk, l in zip(toks, L): out.append([tk, c, c + (b - a) * l / sum(L), i]); c += (b - a) * l / sum(L)
    if W:
        norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
        A = [norm(w[0]) for w in out]; B = [norm(w[0]) for w in W]
        for blk in difflib.SequenceMatcher(None, A, B, autojunk=False).get_matching_blocks():
            for k in range(blk.size):
                out[blk.a + k][1], out[blk.a + k][2] = W[blk.b + k][1], W[blk.b + k][2]
    return out


def captions(wt):
    """One line of 1 to 3 words (at most 15 letters), capitals, punctuation kept, swapped whole on its first word."""
    caps, cur = [], []
    unit = re.compile(r"^(million|billion|thousand|trillion|yen|dollars?|percent|shares?|%)[.,]?$", re.I)
    for w in wt:
        glued = cur and unit.match(w[0]) and re.search(r"\d", cur[-1][0])          # (a figure keeps its unit)
        if cur and not glued and (len(cur) == 3 or len(" ".join(x[0] for x in cur + [w])) > 15 or cur[-1][3] != w[3]):
            caps.append(cur); cur = []
        cur.append(w)
        if re.search(r"[.,;:!?]$", w[0]): caps.append(cur); cur = []
    if cur: caps.append(cur)
    out = []
    for k, c in enumerate(caps):
        t1 = caps[k + 1][0][1] if k + 1 < len(caps) else c[-1][2] + .5
        out.append({"t0": round(c[0][1], 3), "t1": round(min(t1, c[-1][2] + .6), 3), "text": " ".join(x[0] for x in c).upper()})
    return out


# ---------------------------------------------------------------- the director: one place, one take, a shot a sentence
def spans_of(segs):
    sp = {}
    for i, a, b, _ in segs: sp[i] = (min(sp.get(i, (a, b))[0], a), max(sp.get(i, (a, b))[1], b))
    return sp


def direct(spec, segs, T):
    """People, the one camera move and what each screen shows, for oneshot.js. Each cast member waits at a home spot and walks
    (never through furniture: every path goes by its waypoints) to the place their sentence's shot needs; whoever holds that
    place goes home first. The camera keys of each shot avoid furniture and people and keep the subject in clear view."""
    S, C, st = spec["sentences"], spec["cast"], SET
    sp = spans_of(segs); idx = {c["id"]: k for k, c in enumerate(C)}
    pos = [list(st["homes"][k][:2]) for k in range(len(C))]; face = [st["homes"][k][2] for k in range(len(C))]
    paths = [[[0.0, *pos[k]]] for k in range(len(C))]; acts = [[[0.0, "Idle"]] for _ in C]; faceAt = [[[0.0, face[k]]] for k in range(len(C))]
    seated = None
    first = {}
    for s_ in S: first.setdefault(s_["who"], s_["shot"])
    for c_ in C:                                         # (a character whose story starts at the laptop is already sitting there)
        k_ = idx[c_["id"]]
        if first.get(c_["id"]) == "type" and seated is None:
            seated = k_; pos[k_] = list(st["seat"][:2]); face[k_] = st["seat"][2]; paths[k_] = [[0.0, *pos[k_]]]; acts[k_] = [[0.0, "Type"]]; faceAt[k_] = [[0.0, face[k_]]]
    def go(k, t, route, end_face, then, speed=1.3):     # (walk k along route from t; -> arrival time)
        nonlocal seated
        if seated == k: acts[k].append([round(t, 3), "Idle"]); seated = None; t += .3
        if paths[k][-1][0] < t: paths[k].append([round(t, 3), *pos[k]])
        acts[k].append([round(t, 3), "Walk"])
        for x, z in route:
            t += max(.5, math.hypot(x - pos[k][0], z - pos[k][1]) / speed); paths[k].append([round(t, 3), x, z]); pos[k] = [x, z]
        acts[k].append([round(t, 3), then]); faceAt[k].append([round(t, 3), end_face]); return t
    def home_route(k):
        h = st["homes"][k]; return ([st["seat_via"]] if seated == k else []) + [h[:2]]
    look, screen, lap, term, tags, cards, cam = [], [], [], [], [], [], []
    face_of = lambda k: faceAt[k][-1][1]
    seen = set()
    for i, s in enumerate(S):
        a, b = sp[i]; k = idx[s["who"]]; shot = s["shot"]; q = s.get("screen") or {}; ready = a
        if shot == "type":
            if seated is not None and seated != k: go(seated, a, home_route(seated), st["homes"][seated][2], "Idle")
            if seated != k: ready = go(k, a, [st["seat_via"], st["seat"][:2]], st["seat"][2], "Type"); seated = k
            else: acts[k].append([round(a, 3), "Type"])
            lap.append(dict(q, t0=round(ready, 3), t1=round(b, 3)))
            dive0 = min(b - 1.4, ready + 2.2)                  # (first a look at them typing over the shoulder, then the dive)
            if dive0 > ready + .9: term.append({"t0": round(dive0, 3), "t1": round(b - .15, 3)})
        elif shot == "wall":
            if math.hypot(pos[k][0] - st["wall"][0], pos[k][1] - st["wall"][1]) > .3: ready = go(k, a, ([st["seat_via"]] if seated == k else []) + [st["wall"][:2]], st["wall"][2], "Idle")
            screen.append(dict(q, t0=round(a, 3), t1=round(b, 3)))
        elif shot == "walk":
            tgt = st["walks"][i % len(st["walks"])]
            go(k, a, ([st["seat_via"]] if seated == k else []) + [tgt], face[k], "Idle", speed=.9)
        elif shot == "meet":
            o = (k + 1) % len(C); (ax, az), (bx, bz) = st["meet"]
            ta = go(k, a, ([st["seat_via"]] if seated == k else []) + [(ax, az)], math.atan2(bx - ax, bz - az), "Idle_Neutral")
            go(o, a, ([st["seat_via"]] if seated == o else []) + [(bx, bz)], math.atan2(ax - bx, az - bz), "Idle_Neutral"); ready = ta
        elif shot == "react":
            if seated != k: acts[k].append([round(a + .2, 3), "Jump" if s.get("beat") == "payoff" else "Clapping" if s.get("beat") == "move" else "Idle"])
        elif shot == "crowd":
            for j in range(len(C)):
                if j != k and seated != j: acts[j].append([round(a + .3, 3), "Clapping" if s.get("beat") in ("payoff", "move") else "Idle"])
        if s["who"] not in seen:
            t0 = (ready + .4) if shot != "type" else a + .2
            t1 = (term[-1]["t0"] - .3) if shot == "type" and term and term[-1]["t0"] > a else min(b, t0 + 3.2)
            if shot != "wall" and t1 - t0 >= 1.2: seen.add(s["who"]); tags.append({"who": k, "text": C[k]["tag"].upper(), "t0": round(t0, 3), "t1": round(t1, 3)})
        if s.get("card"):
            c = s["card"]; tw = word_at(segs, i, c["top"]); cards.append({"t0": round(tw, 3), "t1": round(min(b, tw + 1.3), 3), "top": c["top"], "bot": c["bot"]})
        look.append([round(a, 3), round(b, 3), "wall" if shot == "wall" else "lap" if shot == "type" and seated == k else k])
        others = [tuple(pos[j]) for j in range(len(C)) if j != k] + [(e[1], e[2]) for e in st["extras"]]
        cam += keys(shot, s, i, a, b, ready, k, pos, seated, term[-1] if shot == "type" and term else None, face_of(k), others)
    last = cam[-1]; cam.append([round(T, 3), last[1], last[2] + .2, last[3], last[4], last[5], last[6], last[7]])
    actors = [{"who": c["look"], "path": paths[k], "acts": acts[k], "face": st["homes"][k][2], "faceAt": faceAt[k],
               "skin": ["#8d5a3b", "#c58c64", "#6b4430"][k % 3]} for k, c in enumerate(C)]
    for k, (who, ex, ez, ef, cl_) in enumerate(st["extras"]):
        actors.append({"who": who, "path": [[0, ex, ez]], "face": ef, "acts": [[0, cl_]], "skin": ["#e0b08a", "#b7774f", "#c58c64"][k % 3]})
    return {"actors": actors, "cam": cam, "look": look, "screen": screen, "lap": lap, "term": term, "tags": tags, "cards": cards}


def word_at(segs, i, text):
    """When the first word of `text` is said in sentence i (the phrase's start, else the sentence's)."""
    w0 = re.sub(r"[^a-z0-9]", "", str(text).split()[0].lower()) if str(text).split() else ""
    for j, a, b, t in segs:
        if j == i and w0 and w0 in re.sub(r"[^a-z0-9 ]", "", t.lower()).split(): return a + (b - a) * t.lower().split().index(next(x for x in t.lower().split() if re.sub(r"[^a-z0-9]", "", x) == w0)) / max(1, len(t.split()))
    return next(a for j, a, b, t in segs if j == i)


def keys(shot, s, i, a, b, ready, k, pos, seated, dv, fc=math.pi, others=()):
    """The camera keys [t, x, y, z, lx, ly, lz, fov] of one shot. The renderer turns the lens onto its subject every frame
    (R.look), so these place the camera; each candidate place is checked against the furniture and the people."""
    st = SET; hx, hz = pos[k]; W2, D2 = st["W"] / 2 - .45, st["D"] / 2 - .45
    def free(cx, cz, tx=None, tz=None):                  # (room for the lens, and nobody between it and its subject)
        if not (abs(cx) <= W2 and abs(cz) <= D2) or any(x0 - .3 <= cx <= x1 + .3 and z0 - .3 <= cz <= z1 + .3 for x0, z0, x1, z1 in st["boxes"]): return False
        if any(math.hypot(cx - ox, cz - oz) < 1.0 for ox, oz in others): return False
        if tx is not None:
            for u in (.2, .4, .6, .8):
                px, pz = cx + (tx - cx) * u, cz + (tz - cz) * u
                if any(math.hypot(px - ox, pz - oz) < .4 for ox, oz in others if math.hypot(tx - ox, tz - oz) > .5): return False
        return True
    def around(x, z, d, ang, y, fov=42):                 # (the first free place on a circle round x, z, starting at ang)
        for da in (0, .4, -.4, .8, -.8, 1.2, -1.2, 1.7, -1.7, 2.3, -2.3, math.pi):
            cx, cz = x + d * math.sin(ang + da), z + d * math.cos(ang + da)
            if free(cx, cz, x, z): return [round(cx, 3), y, round(cz, 3), round(x, 3), 1.35, round(z, 3), fov]
        return [round(x, 3), y, round(min(D2, z + d), 3), round(x, 3), 1.35, round(z, 3), fov]
    if shot == "type":
        lx, ly, lz = st["lap"]; sh = [-1.9, 2.05, 2.15, lx, ly, lz]   # (high over the right shoulder, off the walk to and from the seat)
        K = [[round(a, 3)] + around(hx, hz, 2.6, fc + 2.4, 1.75), [round(ready + .2, 3)] + sh + [40]]
        if dv: K += [[round(dv["t0"] + .1, 3)] + sh + [13], [round(b, 3)] + sh + [13]]
        else: K += [[round(b, 3)] + [-1.6, 1.85, 2.5, lx, ly, lz, 30]]
        return K
    if shot == "wall":
        dx, dy, dz = st["display"]; fit = st["dw"] / 2 / math.tan(math.radians(12)) * 1.06
        return [[round(a + .3, 3), dx - .3, 1.66, round(dz + fit * 1.12, 3), dx, dy, dz, 42], [round(b, 3), dx - .1, 1.66, round(dz + fit * .97, 3), dx, dy, dz, 42]]
    if shot == "walk":
        return [[round(a, 3)] + around(hx, hz, 2.4, fc + 1.1, 1.55), [round(b, 3)] + around(*pos[k], 2.1, fc + .9, 1.5)]
    if shot == "meet":
        (ax, az), (bx, bz) = st["meet"]; mx, mz = (ax + bx) / 2, (az + bz) / 2
        return [[round(a + .4, 3)] + around(mx, mz, 3.2, .9, 1.7), [round(ready, 3)] + around(mx, mz, 2.6, .9, 1.6), [round((ready + b) / 2, 3)] + around(mx, mz, 2.4, 2.0, 1.65), [round(b, 3)] + around(mx, mz, 2.3, 3.0, 1.6)]
    if shot == "react":
        return [[round(a, 3)] + around(hx, hz, 2.6, fc + .5, 1.6), [round(b, 3)] + around(hx, hz, 1.4, fc + .35, 1.55, 36)]
    return [[round(a, 3)] + around(0, -1.5, 3.2, .3, 1.8), [round(b, 3)] + around(0, -1.5, 4.6, .5, 3.0, 50)]   # crowd: up and out


# ---------------------------------------------------------------- render and sound
async def frames(R, fdir, cover):
    from playwright.async_api import async_playwright
    os.makedirs(fdir, exist_ok=True); n = int(round(R["T"] * FPS))
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--allow-file-access-from-files", "--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={"width": 1080, "height": 1920}); pg.set_default_timeout(300000)
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.add_init_script(f"window.__R={json.dumps(R)};")
        await pg.goto(f"file://{HERE}/oneshot.html"); await pg.evaluate("window.ready")
        for i in range(n):
            await pg.evaluate("t=>render(t)", i / FPS)
            await pg.screenshot(path=f"{fdir}/f{i:05d}.jpg", type="jpeg", quality=90)
            if i % 300 == 0: say(f"frame {i}/{n}")
        await pg.evaluate("t=>render(t)", min(1.2, R["T"] / 2)); await pg.screenshot(path=cover, type="jpeg", quality=90)
        await b.close()
        if errs: raise SystemExit("render errors: " + "; ".join(errs[:3]))
    return n


def sound(R, wav, work):
    """The voice over the bed, a soft hit in most pauses and on every card, mixed to -14.5 LUFS."""
    import numpy as np, soundfile as sf, sounds as SD
    T = R["T"]; bed = SD.bed(T, R.get("title", "")); sf.write(os.path.join(work, "bed.wav"), bed, SD.SR)
    hits = np.zeros((int(T * SD.SR) + SD.SR, 2), np.float32)
    def put(x, t, g):
        a = int(t * SD.SR); x = np.asarray(x, np.float32)[: len(hits) - a]; hits[a:a + len(x)] += (g * x)[:, None]
    for c in R.get("cards", []): put(SD.whoosh(.4), max(0, c["t0"] - .2), .9)
    for f in R.get("figs", []): put(SD.pop(), f["t0"], .7)
    for k, (i, a, b, _) in enumerate(R["segs"][:-1]):
        nxt = R["segs"][k + 1][1]
        if nxt - b >= .6 and k % 3 != 2: put(SD.whoosh(.32), b + .1, .35)        # (two of three pauses carry a soft hit)
    sf.write(os.path.join(work, "hits.wav"), hits[: int(T * SD.SR)], SD.SR)
    out = os.path.join(work, "mix.m4a")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-i", os.path.join(work, "bed.wav"), "-i", os.path.join(work, "hits.wav"), "-filter_complex",
                    f"[0:a]aformat=channel_layouts=stereo,apad=whole_dur={T},asplit=2[v][sc];[1:a]volume=0.15[b];[b][sc]sidechaincompress=threshold=0.03:ratio=2.5:attack=20:release=400[bd];"
                    f"[2:a]volume=0.8[h];[v][bd][h]amix=inputs=3:normalize=0,atrim=0:{T},loudnorm=I=-14.5:TP=-1.5:LRA=7[o]",
                    "-map", "[o]", "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "192k", out], check=True)
    return out


def render(R, wav, work, out):
    fdir = os.path.join(work, "frames"); shutil.rmtree(fdir, ignore_errors=True); os.makedirs(out, exist_ok=True)
    tl = os.path.join(work, "timeline.json")                       # (drawn in a fresh process: the voice and transcriber models held
    subprocess.run([sys.executable, __file__, "frames", tl, fdir, os.path.join(out, "cover.jpg")], check=True)   #  in this one starve Chromium: 15 s a frame, not 1.5)
    n = len(os.listdir(fdir)); a = sound(R, wav, work)
    mp4 = os.path.join(out, "reel.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{fdir}/f%05d.jpg", "-i", a, "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "copy",
                    "-movflags", "+faststart", "-t", str(R["T"]), mp4], check=True)
    shutil.rmtree(fdir, ignore_errors=True); say(f"rendered {mp4} ({n} frames, {R['T']:.1f}s)")
    return mp4


def caption_text(spec, story):
    script = " ".join(str(s["say"]) for s in spec["sentences"]); st = story.get("stock", {})
    src = sorted({o for f in story.get("research", {}).get("facts", []) for o in (f.get("by") or [])})[:5]
    return (f"{spec['title']}\n\n{script}\n\nToday's Daily was {st.get('name')} ({st.get('ticker')}), {st.get('start')} to {st.get('end')}. "
            f"Tomorrow's chart is live at midnight UTC: memestreet.net\n" + ("Sources: " + ", ".join(src) + "\n" if src else "") +
            f"{DISCLAIMER}\n#stocks #investing #stockmarket #{re.sub(r'[^A-Za-z0-9]', '', str(st.get('ticker', '')))} #MemeStreet")


# ---------------------------------------------------------------- the whole reel
def cut(spec, work, story):
    """Voice and direct a script -> the timeline for oneshot.js."""
    wav, segs, T = voice(spec, work); wt = word_times(wav, segs); D = direct(spec, segs, T)
    R = dict(D, T=round(T, 3), set="office", cw=720, title=spec["title"], ticker=spec.get("ticker", ""), caps=captions(wt), segs=segs, words=wt,
             prices=story.get("chart"), dates=[story.get("stock", {}).get("start"), story.get("stock", {}).get("end")], seat={"y": 0})
    json.dump(R, open(os.path.join(work, "timeline.json"), "w", encoding="utf-8"))
    return R, wav


ROUNDS = int(os.environ.get("ONESHOT_ROUNDS", "5"))
# The bar (the owner, 2026-11-22, after the panel was calibrated on the copied hits: MagnatesMedia's 2M-view reel kept 9 of 13 to the
# end, How Money Works' 5.4M-view one 6, Zack D. Films' 17M-view one 5; "all 13" is a bar no hit passes): match the best hit.
PASS = int(os.environ.get("ONESHOT_PASS", "9"))
def build(story, work, out, recent=(), spec=None, panel=True):
    """Write, voice, direct; show the panel a preview and rewrite until PASS of 13 simulated viewers stay to the end (at most
    ROUNDS; the best round is filmed); render; show the panel the real cut. -> (spec, R, mp4, the last verdict)."""
    shutil.rmtree(work, ignore_errors=True); os.makedirs(work, exist_ok=True); verdict, crit, best = None, None, None
    for k in range(ROUNDS if panel else 1):
        if k or not spec: spec = write(story, recent, crit)
        json.dump(spec, open(os.path.join(work, "spec.json"), "w", encoding="utf-8"), indent=1)
        R, wav = cut(spec, work, story)
        if not panel: break
        verdict = gate(R, spec, work, os.path.join(work, f"panel{k}"))
        say(f"panel round {k + 1}: {verdict['stayed']} of {verdict['of']} stayed to the end" + ("" if verdict["ok"] else ": " + verdict["why"][:300]))
        if not best or verdict["stayed"] > best[1]["stayed"]: best = (json.loads(json.dumps(spec)), verdict)
        if verdict["ok"]: break
        crit = {"spec": spec, "why": verdict["why"]}
    if panel and best and best[1]["stayed"] > verdict["stayed"]:   # (the panel is noisy: film the best round, not the last)
        spec, verdict = best; json.dump(spec, open(os.path.join(work, "spec.json"), "w", encoding="utf-8"), indent=1); R, wav = cut(spec, work, story)
        say(f"filming the best round: {verdict['stayed']} of {verdict['of']}")
    mp4 = render(R, wav, work, out)
    open(os.path.join(out, "caption.txt"), "w", encoding="utf-8").write(caption_text(spec, story))
    if panel and verdict and verdict["ok"]:
        verdict = gate(R, spec, work, os.path.join(work, "panel_final"), mp4)
        say(f"panel on the real cut: {verdict['stayed']} of {verdict['of']} stayed to the end")
    return spec, R, mp4, verdict


def state():
    return json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"used": []}


def month_table(P, start, end):
    """The real price at each month of the window (trading days spread evenly over the dates): what the writer may say about
    where the price stood when, and the chart point (0..1) for it."""
    import datetime
    a, b = datetime.date.fromisoformat(start), datetime.date.fromisoformat(end); n = len(P) - 1; out, seen = [], set()
    for i, p in enumerate(P):
        d = a + (b - a) * (i / n); key = d.strftime("%b %Y")
        if key not in seen: seen.add(key); out.append({"month": key, "chart_point": round(i / n, 2), "price": f"${p:.2f}"})
    return out


def day_story(date, data):
    """The day's Daily -> what the writer may use: the stock and its window, the real prices, the researched story."""
    import news_reel as N
    d = json.load(open(data, encoding="utf-8")); g = d["game"]; rv = g.get("real")
    if not rv: raise SystemExit(f"not made: the Daily of {date} was a model chart, not a real stock")
    H = g.get("history", 60); P = [round(c[3] * rv["k"], 2) for c in g["candles"][H - 1:]]
    hi, lo = max(range(len(P)), key=P.__getitem__), min(range(len(P)), key=P.__getitem__)
    cache = data.replace(".json", ".research.json")
    if os.path.exists(cache): pack = json.load(open(cache, encoding="utf-8"))
    else:
        pack = N.research(f"{rv['name']} ({rv['ticker']}) shares between {rv['start']} and {rv['end']}: what the company does and where its "
                          f"shares stood at the start; every event in that window that moved the price, with its date; why it moved, each "
                          f"cause with its source; the key players (executives, big investors, short sellers, retail traders); how the "
                          f"window ended. The share price went from about ${P[0]:.2f} to ${P[-1]:.2f}.")
        errs = N.sound(pack)
        if errs: raise SystemExit("not made: the research is not sound: " + "; ".join(errs))
        json.dump(pack, open(cache, "w", encoding="utf-8"), indent=1)
    pack = dict(pack, facts=[f for f in pack.get("facts", []) if f.get("status") != "alleged"])
    T = month_table(P, rv["start"], rv["end"])
    def when(i):
        import datetime
        a, b = datetime.date.fromisoformat(rv["start"]), datetime.date.fromisoformat(rv["end"]); return (a + (b - a) * (i / (len(P) - 1))).strftime("%b %Y")
    return {"stock": {"ticker": rv["ticker"], "name": rv["name"], "start": rv["start"], "end": rv["end"], "events_in_window": rv.get("events", [])},
            "window": {"first_price": f"${P[0]:.2f}", "last_price": f"${P[-1]:.2f}", "change_pct": f"{(P[-1] / P[0] - 1) * 100:.0f}%",
                       "high": {"price": f"${P[hi]:.2f}", "when": when(hi), "chart_point": round(hi / (len(P) - 1), 2)},
                       "low": {"price": f"${P[lo]:.2f}", "when": when(lo), "chart_point": round(lo / (len(P) - 1), 2)},
                       "note": "prices are the real daily closes the Daily showed; the chart point says where in the window a moment falls"},
            "prices": T, "research": {k: pack.get(k) for k in ("headline", "people", "company", "facts", "numbers", "market", "not_known")},
            "chart": P, "sources": pack.get("sources", [])}


def daily(date, where=None):
    """The day's reel: queued for <date>T2330 (or, with `where`, made there and not queued). -> the slot or the folder, or None."""
    import news_reel as N
    sl = f"{date}T2330"; q = os.path.join(ROOT, "queue", sl)
    if not where and (os.path.exists(os.path.join(q, ".auto")) or os.path.exists(os.path.join(q, "posted.json"))): say(sl, "already has its reel"); return sl
    tries = os.path.join(ROOT, "state", f"oneshot-{date}.tries"); n = int(open(tries).read()) if os.path.exists(tries) else 0
    if not where and n >= 3: say(f"{date}: tried three times, not made"); return None
    os.makedirs(os.path.dirname(tries), exist_ok=True); open(tries, "w").write(str(n + 1))
    data = os.path.join(ROOT, "data", f"{date}.json")
    if not os.path.exists(data): subprocess.run([sys.executable, os.path.join(SRC, "fetch.py"), data], cwd=ROOT, check=True)
    story = day_story(date, data); st = state()
    base = where or ROOT; work, out = os.path.join(base, "work", "daily-" + date), os.path.join(base, "out", "daily-" + date)
    shutil.rmtree(out, ignore_errors=True)
    spec, R, mp4, g = build(story, work, out, [u.get("title") for u in st["used"]])
    if where: return out
    if not (g and g["ok"]): say("not queued: too few simulated viewers stayed to the end:", (g or {}).get("why", "")); return None
    json.dump({"by": "oneshot", "audience": g}, open(os.path.join(out, "approved.json"), "w"))
    st["used"].append({"date": date, "ticker": story["stock"]["ticker"], "title": spec["title"]}); json.dump(st, open(STATE, "w", encoding="utf-8"), indent=1)
    return N.queue_out(out, sl, spec["title"])


def gate(R, spec, work, d, mp4=None):
    """The owner, 2026-11-22: "pass this through any skills that mimic human behaviour and see if they would watch through
    to the end or not". The 13-persona panel (lab/audience.py) sees what the feed serves: the first 3 seconds frame by frame and
    the whole reel every 1.5 s (drawn from the timeline, or cut from the finished video), with what is said and shown when."""
    import importlib.util
    lab = os.path.join(ROOT, "lab", "audience.py")
    if not os.path.exists(lab): return {"ok": False, "why": "lab/audience.py is missing", "stayed": 0, "of": 0}
    sp = importlib.util.spec_from_file_location("audience", lab); A = importlib.util.module_from_spec(sp); sp.loader.exec_module(A)
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d, exist_ok=True); T = R["T"]
    if mp4: A.frames(mp4, d, T)
    else: subprocess.run([sys.executable, __file__, "stills", os.path.join(work, "timeline.json"), d, json.dumps(A.HOOK_T)], check=True)
    S = spec["sentences"]; spans = spans_of(R["segs"]); tag = {c["id"]: c["tag"] for c in spec["cast"]}
    feed = {"length_secs": round(T, 1), "format": "a true stock story told by a calm male narrator over one unbroken 3D take in a trading office, a new shot each sentence",
            "title": spec["title"], "post_caption_first_line": spec["title"],
            "audio": "a calm male documentary voice-over from the first frame, a soft tonal music bed with no beat, a soft whoosh in most pauses",
            "words_in_first_3s": [(w[0], round(w[1], 2)) for w in R["words"] if w[1] < 3],
            "timeline": [{"from": round(spans[i][0], 1), "to": round(spans[i][1], 1), "said": s["say"],
                          "on_screen": {"shot": s["shot"], "character": tag.get(s["who"]), "captions": "the words as said, 1 to 3 at a time, amber capitals in a black box",
                                        **({"screen": s["screen"]} if s.get("screen") else {}), **({"card": s["card"]} if s.get("card") else {})}} for i, s in enumerate(S)],
            "images": A.IMAGES}
    json.dump(feed, open(os.path.join(d, "feed.json"), "w"), indent=1)
    res = None; err = ""
    for k in range(2):                                   # (the panel's reply is a model's JSON: once in a while it does not parse)
        try: res = A.watch(d); break
        except (SystemExit, Exception) as e: err = str(e)[:300]; say("the panel failed, trying again:", err)
    if res is None: return {"ok": False, "why": "the panel failed twice: " + err, "stayed": 0, "of": 0}
    P = res.get("personas") or []
    left = [p for p in P if p.get("leaves_at") not in (None, "null") and float(p["leaves_at"]) < T - 1.5]
    return {"ok": bool(P) and len(P) - len(left) >= PASS, "stayed": len(P) - len(left), "of": len(P), "predicted": res.get("predicted"),
            "why": "; ".join(f"{p.get('id')} leaves at {p.get('leaves_at')}s: {str(p.get('why') or p.get('reason') or '')[:160]}" for p in left)[:1500]}


async def stills(R, d, hook_t):
    """The panel's two images drawn straight from the timeline (no full render): first_3s.jpg and whole_reel.jpg."""
    from playwright.async_api import async_playwright
    tmp = os.path.join(d, "_s"); os.makedirs(tmp, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--allow-file-access-from-files", "--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={"width": 1080, "height": 1920}); pg.set_default_timeout(300000)
        await pg.add_init_script(f"window.__R={json.dumps(R)};"); await pg.goto(f"file://{HERE}/oneshot.html"); await pg.evaluate("window.ready")
        ts = [("h", k, t) for k, t in enumerate(hook_t)] + [("w", k, k * 1.5) for k in range(int(R["T"] / 1.5) + 1)]
        for kind, k, t in ts:
            await pg.evaluate("t=>render(t)", min(t, R["T"] - .05)); await pg.screenshot(path=os.path.join(tmp, f"{kind}{k:03d}.jpg"), type="jpeg", quality=85)
        await b.close()
    ff = lambda *a: subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)
    hs = sorted(f for f in os.listdir(tmp) if f.startswith("h"))
    ff(*sum([["-i", os.path.join(tmp, f)] for f in hs], []), "-filter_complex",
       "".join(f"[{i}]scale=360:-1[s{i}];" for i in range(len(hs))) + "".join(f"[s{i}]" for i in range(len(hs))) + f"hstack={len(hs)}", os.path.join(d, "first_3s.jpg"))
    n = int(R["T"] / 1.5) + 1
    ff("-framerate", "1", "-i", os.path.join(tmp, "w%03d.jpg"), "-vf", f"scale=180:-1,tile=8x{math.ceil(n / 8)}", "-frames:v", "1", os.path.join(d, "whole_reel.jpg"))
    shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- self-check
DEMO_STORY = {"stock": {"ticker": "GPRO", "name": "GoPro", "start": "2020-08-24", "end": "2021-02-12", "events_in_window": []},
              "window": {"first_price": "$4.80", "last_price": "$8.04", "change_pct": "67%", "high": {"price": "$13.89", "when": "Jan 2021", "chart_point": .93}},
              "prices": [{"month": "Nov 2020", "chart_point": .42, "price": "$6.20"}],
              "research": {"people": [{"name": "Nick Woodman", "role": "founder and CEO"}], "facts": [
                  {"claim": "GoPro shares jumped in January 2021 as Reddit traders piled into heavily shorted stocks", "status": "confirmed", "by": ["Reuters"]},
                  {"claim": "In November 2020 the first vaccine results lifted beaten-down stocks", "status": "confirmed", "by": ["AP"]}]},
              "chart": [4.8, 5.2, 6.2, 9.0, 13.89, 8.04]}
DEMO_SPEC = {"title": "How A Camera Company Nobody Wanted Became A Meme Stock In Five Months", "ticker": "GPRO",
             "cast": [{"id": "ceo", "tag": "THE CEO", "look": "man_tie"}, {"id": "trader", "tag": "A REDDIT TRADER", "look": "man"}],
             "sentences": [
    {"beat": "hook", "who": "ceo", "shot": "wall", "say": "This camera company went from a $4.80 stock nobody wanted to a meme stock that touched $13.89 in five wild months.", "screen": {"chart": 0.1, "count": {"to": 13.89, "prefix": "$"}}},
    {"beat": "setup", "who": "ceo", "shot": "walk", "say": "In August 2020 GoPro was a fading gadget maker, its founder Nick Woodman still pushing subscriptions while the rest of the market looked the other way and the shares drifted lower week after week."},
    {"beat": "terms", "who": "trader", "shot": "type", "say": "Then in November 2020, when the first vaccine results lifted beaten-down stocks, a trader at home typed in a buy at around $6.20 a share.", "screen": {"lines": ["BUY GPRO", "AT $6.20"], "chart": 0.42}},
    {"beat": "move", "who": "trader", "shot": "meet", "say": "By January 2021 Reddit traders were piling into heavily shorted stocks, Reuters reported, and GoPro was swept up with them, climbing day after day."},
    {"beat": "payoff", "who": "trader", "shot": "react", "say": "At the peak the stock touched $13.89, more than double the $6.20 the trader had paid, before it sank back to $8.04 by the middle of February.", "card": {"top": "$6.20", "bot": "$13.89"}},
    {"beat": "sting", "who": "ceo", "shot": "crowd", "say": "Despite all the noise, nothing about the cameras had changed, and the company was still the same struggling gadget maker it had been back in the quiet days of August."}],
             "caption": "x"}


def demo():
    E = errors(DEMO_SPEC, DEMO_STORY); assert not E, E
    bad = json.loads(json.dumps(DEMO_SPEC)); bad["sentences"][0]["say"] = "Did you know this camera company went from $4.80 to a meme stock that touched $13.89 in five wild months?"
    assert any("hook" in e for e in errors(bad, DEMO_STORY))
    bad = json.loads(json.dumps(DEMO_SPEC)); bad["sentences"][4]["say"] = bad["sentences"][4]["say"].replace("$13.89", "$19.50")
    assert any("not in the true story" in e for e in errors(bad, DEMO_STORY))
    bad = json.loads(json.dumps(DEMO_SPEC)); bad["sentences"][1]["say"] += " Jane Porter agreed."
    assert any("not in the research" in e for e in errors(bad, DEMO_STORY))
    bad = json.loads(json.dumps(DEMO_SPEC)); bad["sentences"][3]["shot"] = "type"
    assert any("twice in a row" in e for e in errors(bad, DEMO_STORY))
    bad = json.loads(json.dumps(DEMO_SPEC)); bad["sentences"][2]["screen"]["chart"] = .05
    assert any("forward" in e for e in errors(bad, DEMO_STORY))
    P = phrases(DEMO_SPEC); assert P[-1]["gap"] == 0
    segs, t = [], 0.0
    for p in P:
        d = len(p["text"].split()) / TALK; segs.append((p["i"], t, t + d, p["text"])); t += d + p["gap"]
    D = direct(DEMO_SPEC, segs, t + .9); cam = D["cam"]
    assert cam[0][0] >= 0 and all(b[0] >= a[0] for a, b in zip(cam, cam[1:])) and all(len(k) == 8 for k in cam)
    assert all(abs(k[1]) <= SET["W"] / 2 and abs(k[3]) <= SET["D"] / 2 for k in cam)
    assert [g["text"] for g in D["tags"]] == ["THE CEO", "A REDDIT TRADER"] and len(D["lap"]) == 1 and len(D["term"]) == 1 and len(D["screen"]) == 1
    tr = D["actors"][1]; assert any(a[1] == "Type" for a in tr["acts"]) and any(abs(p[1] - SET["seat"][0]) < 1e-6 for p in tr["path"])
    for a in D["actors"][:2]:                           # (every walk goes round the furniture: no path point inside a box)
        assert not any(x0 < p[1] < x1 and z0 < p[2] < z1 for p in a["path"] for x0, z0, x1, z1 in SET["boxes"][:2] + SET["boxes"][3:]), a["path"]
    assert len(D["cards"]) == 1 and D["cards"][0]["bot"] == "$13.89"
    T = month_table([1, 2, 3, 4], "2020-01-01", "2020-04-01"); assert T[0]["month"] == "Jan 2020" and T[-1]["chart_point"] == 1.0
    assert spoken("He got $60,000 and $17 million, 4% of it.") == "He got 60,000 dollars and 17 million dollars, 4 percent of it."
    c = caption_text(DEMO_SPEC, DEMO_STORY); assert "memestreet.net" in c and DISCLAIMER in c and "#GPRO" in c
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:] or ["demo"]
    if a[0] == "demo": demo()
    elif a[0] == "daily": sys.exit(0 if daily(a[1] if len(a) > 1 else time.strftime("%Y-%m-%d", time.gmtime())) else 1)
    elif a[0] == "dailytry": print(daily(a[1], a[2]))
    elif a[0] == "frames": asyncio.run(frames(json.load(open(a[1], encoding="utf-8")), a[2], a[3]))
    elif a[0] == "stills": asyncio.run(stills(json.load(open(a[1], encoding="utf-8")), a[2], json.loads(a[3])))
    elif a[0] in ("preview", "spec"):                   # (a written script; its story from DAILY_DATA or the demo story)
        sp = json.load(open(a[1], encoding="utf-8")); st = day_story("x", os.environ["DAILY_DATA"]) if os.environ.get("DAILY_DATA") else DEMO_STORY
        w = os.path.join(a[2], "work"); os.makedirs(w, exist_ok=True)
        if a[0] == "preview":
            R, _ = cut(sp, w, st); subprocess.run([sys.executable, __file__, "stills", os.path.join(w, "timeline.json"), a[2], json.dumps([0, .5, 1, 1.5, 2, 3])], check=True)
        else: build(st, w, os.path.join(a[2], "out"), spec=sp, panel=os.environ.get("PANEL") == "1")
