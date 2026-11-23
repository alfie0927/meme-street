"""Meme Street's one reel a day: the story behind the day's Daily stock, as a low-poly 3D story explainer (story3d.js).

The owner, 2026-11-22: "the goal is to have something that shows off the story, shows every part of the story, e.g., shows the
GO PRO as it's being made etc similar to this reel [a 2D AMD vs Intel explainer] ... it shouldn't just be people walking around
an office, there should be different scenes for each new stock based on what they do and the story told"; then "it should be 3d
like the previous reel was, except it goes through all the events and story like this current reel"; 2026-11-23, on the first 3D
cut (small props in dark empty sets, a list of headlines; 29 views, 59% gone in 3 s): "i still don't like it... make the reel
better. also it's pronounced GO PRO (two words)".
  the story   the day's Daily stock over its window (data/<date>.json), researched with sources (news_reel.research), told as ONE
              story with a turn and a payoff: short sentences, each a step, plain words, few figures.
  the picture every sentence is a SHOT: its own 3D set, one or two subjects at real size, the camera fitted so they fill the frame
              (the product, its factory making it, the store, people, the real price line...), one line of big words when it
              earns it, a headline that stays, the date. Nothing overlaps (a check measures every box).
  the sound   a man's voice (Kokoro; say.json holds the owner's pronunciations: 'GoPro' -> two stressed words), a light tune that
              follows the story and sits well under the voice, a few soft effects.
The owner, 2026-11-23, on the remake ("better. but i think it can still be better"): "the caption timings can be better, i want the
music to be better (and not as loud), also at the beginning explain that this is today's mystery chart". So the reel opens on the
mystery chart itself ("Today's mystery chart on Meme Street..."), reveals the company in its second shot and closes on tomorrow's;
every caption word takes its time from its own letters as heard; the music is sounds.tune(), set 21 dB under the voice.
The owner, 2026-11-23, on that cut ("this is way better"): "make sure the audio is smoother though. it should flow like normal human
speech". The voice was spoken clause by clause, each clause at its own speed, glued with fixed gaps. It is now spoken in even
breaths of three or four sentences at one speed, its pauses a person's (voice(), flow()), and the mix has one gain all through.
It is queued for <date>T2330 only when at least PASS of the 13 simulated viewers (lab/audience.py) watch to the end.

  python3 src/explainer/make.py daily [YYYY-MM-DD]        fetch, research, write, voice, check, render, panel, queue
  python3 src/explainer/make.py dailytry <date> <dir>     the same into <dir>, not queued (PANEL=0: no panel)
  python3 src/explainer/make.py spec <spec.json> <dir>    voice and render a written script (DAILY_DATA=<data json> for its story)
  python3 src/explainer/make.py preview <spec.json> <dir> one still a shot from a script, no voice (the look, the overlap check)
  python3 src/explainer/make.py cut <spec.json> <dir>     voice and timeline only; then the frames can be drawn on a faster machine:
  python3 src/explainer/make.py film <timeline> <dir>       frames -> <dir>/silent.mp4 (EXPLAINER_GL, EXPLAINER_Q, EXPLAINER_WORKERS)
  python3 src/explainer/make.py mux <dir> <silent.mp4>      the sound and the picture -> <dir>/out/reel.mp4
  python3 src/explainer/make.py phonemes <spec.json>      what the voice will say, sound by sound (to check a pronunciation)
  python3 src/explainer/make.py demo                      self-check: no Claude, no voice, no render
"""
import asyncio, difflib, json, math, os, re, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.dirname(HERE); ROOT = os.path.dirname(SRC)
sys.path.insert(0, SRC)
STATE = os.path.join(ROOT, "state", "explainer.json")
VOICE = os.environ.get("EXPLAINER_VOICE", "am_michael")
TALK = 3.2                                   # words a second while talking (the reference: 226 words in 85 s with its pauses)
GAP = {"comma": .12, "stop": .32, "hook": .5}
FPS = int(os.environ.get("EXPLAINER_FPS", "30"))
DISCLAIMER = "Practice money only. Not investment advice."
CLOSE = "A new mystery chart goes live at midnight."        # every reel's last line: back to where it began
SPEED = float(os.environ.get("EXPLAINER_SPEED", "1.15"))     # ONE pace for the whole reel: about 5 syllables a second while talking, as the owner's three model narrators (5.1 to 5.7); the voice's own 1.0 is a slow reader's 4.1
BREATH = 300                                  # phonemes the voice speaks in one go at most (its window is 510; even breaths sound alike)
# How long a pause the voice made is kept: its own length x k, never under `least`, never over `most` (seconds). By itself the voice
# stops for half a second at a full stop and 0.3 to 0.45 s at EVERY comma; a narrator people watch: 0.28 s, rarely over 0.5.
PAUSES = {"stop": (.7, .28, .42), "comma": (.45, .08, .18), None: (1, 0, .1)}
BETWEEN = .4                                  # the pause between two breaths
# The voice (the owner, 2026-11-23: "use all the skills you have to make sure the voiceovers are as realistic as possible"):
# ElevenLabs, the most human voice we have (the Starter plan the account already pays for: about 1,300 characters a reel),
# a young American narrator like the owner's third model reel; Kokoro reads if ElevenLabs fails or EXPLAINER_TTS=kokoro.
TTS = os.environ.get("EXPLAINER_TTS", "eleven")
EL_VOICE = os.environ.get("EXPLAINER_EL_VOICE", "TX3LPaxmHKxFdv7VOQHJ")     # (Liam: "Energetic, Social Media Creator")
EL_MODEL = os.environ.get("EXPLAINER_EL_MODEL", "eleven_multilingual_v2")
EL_SET = {"stability": .45, "similarity_boost": .8, "style": .3, "use_speaker_boost": True, "speed": float(os.environ.get("EXPLAINER_EL_SPEED", "1.0"))}
# The music. The owner, 2026-11-23: "make the music more exciting, and creative (it's too AI generated and boring rn)", then, on
# Kevin MacLeod's tracks (heard in thousands of videos): "change the music up so it's more unique". So: tracks by independent
# artists on Jamendo, free to use with a credit (CC BY), found through Openverse (lab/music_search.py) and kept in
# assets/music_cc/jamendo/ on the server with tracks.json (file, title, artist, licence, source); never in the repo. A reel takes
# its own track (EXPLAINER_TRACK names one) and its caption credits it; synthesised music (sounds.tune) only if none is there.
MUSIC_DIR = os.path.join(ROOT, "assets", "music_cc", "genre")
# Then, 2026-11-23 night: "i don't like this music... use the music that is typically used in these types of reels". A research
# agent read the music labels on Segment Zero's and Zack D. Films' Shorts: paid Epidemic Sound tracks, mostly sneaky pizzicato
# orchestral comedy, mystery pulses and cinematic builds. The free match: Steven O'Brien's cues (CC BY, not registered with
# Content ID) and John Bartmann's "Jazzy Detective", in assets/music_cc/genre/ with tracks.json (each with its own "credit").
CAP_LEAD = .06                                # a caption word shows this long before it is heard (a late word reads as lag)
CAP_WORDS = 2                                 # words a caption at most (the owner's second model reel: one to three, big, changing often)
CAP_MIN = .36                                  # seconds a caption stays at least (a shorter one joins its neighbour)
MUSIC_DB = -18.0                              # the music's level against the voice (the model reel: 20 dB under; the first cuts: 14)
FX_DB = {"whoosh": -13, "pop": -14, "thud": -12, "boom": -13, "ding": -14, "rise": -18}      # (the fourth model reel: effects you hear on every cut and every action)      # each effect's peak against the voice's
GOLD = "#ffc83d"
PAGE = "story3d.html"
# How the browser draws: the reel server has no graphics card (software GL, 2 cores: two browsers, each half the frames, at 2/3
# size). A PC with one: EXPLAINER_GL="--use-gl=angle --ignore-gpu-blocklist" EXPLAINER_Q=1 (full size, ~0.25 s a frame).
GL = ["--allow-file-access-from-files"] + os.environ.get("EXPLAINER_GL", "--use-gl=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist").split()
Q = float(os.environ.get("EXPLAINER_Q", "0.667"))
WORKERS = int(os.environ.get("EXPLAINER_WORKERS", "2"))
INIT = lambda R: f"window.__R={json.dumps(R)};window.__Q={Q};"
say = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)

# ---------------------------------------------------------------- what a shot can show (story3d.js builds the same lists)
BGS = {"office": "a bright office: tall windows, shelves, plants", "home": "a living room: a sofa, a rug, pictures (customers at home)",
       "store": "inside a shop: walls of colourful shelves", "factory": "a factory hall: pipes, machines, crates",
       "city": "a sunny street of buildings", "night": "the city at dusk, windows lit", "outdoors": "mountains, pines, sky",
       "sea": "the open sea: waves, an island, the sun (surfing, ships)", "stage": "a keynote stage: curtains, a big screen, spotlights",
       "trading": "a trading floor: a wall of price screens", "court": "a courthouse: columns, marble",
       "studio": "a clean studio in the company's colour (for the product, the chart, a figure)"}
PRODUCTS = ["camera", "chip", "phone", "laptop", "car", "bottle", "pill", "shoe", "shirt", "game", "food", "box"]
LOOKS = ["suit", "casual", "hoodie", "worker", "woman"]
POSES = ["stand", "cheer", "point", "shock", "sad", "hold", "walk"]
# a subject of a shot: a 3D thing at real size the camera frames. kind: (what it shows, its fields)
KINDS = {
    "person": ("a cast member, as tall as the frame when alone", '{"who": cast id, "pose": ' + "|".join(POSES) + '}'),
    "crowd": ("five people (buyers, fans, staff, traders)", '{"pose"}'),
    "product": ("THE PRODUCT, huge, turning on a lit stand", '{"brand", "product": ' + "|".join(PRODUCTS) + ', "text": at most 8 letters on it}'),
    "factory": ("THE PRODUCT BEING MADE: a belt, robot arms fitting its parts, sparks", '{"brand", "product", "text": the sign over the line, at most 12 letters}'),
    "store": ("a shop front with the product in its window", '{"brand", "product", "text": shop name, "sign": at most 10 letters ("SOLD OUT")}'),
    "building": ("the company's tower with its name on it", '{"brand", "text": the name}'),
    "action": ("someone surfing, skiing or biking with a camera on their head", '{"sport": "surf"|"ski"|"bike"}'),
    "phone": ("a giant phone: an app, a subscription, an order", '{"brand", "title": at most 10 letters, "lines": 1-3 of at most 12 letters, "tap": true}'),
    "chart": ("THE REAL PRICE LINE on a big screen, drawn from one point of the window to a later one, its price at the tip", '{"from": 0-1, "to": 0-1}'),
    "bars": ("2 or 3 bars compared, growing", '{"bars": [{"label": at most 8 letters, "value": number, "text": the figure shown}]}'),
    "news": ("a TV: BREAKING and a headline", '{"lines": 1-3 of at most 14 letters}'),
    "doc": ("a paper: results, a deal, a filing", '{"title": at most 12 letters, "text": a figure}'),
    "arrow": ("a big arrow up (green) or down (red) with a figure", '{"dir": "up"|"down", "text": "+25%"}'),
    "money": ("a money bag, coins raining", '{"text": at most 8 letters, "rain": true}'),
    "calendar": ("a calendar page", '{"month": "FEB", "day": "5"}'),
    "podium": ("a 1-2-3 podium with cast members on it", '{"first": cast id, "second": cast id or null, "third": null}'),
    "monitor": ("an old computer typing lines", '{"lines": 1-3 lines of at most 14 letters}'),
    "trophy": ("a gold cup, confetti", "{}"),
    "bulb": ("a lightbulb: an idea", '{"text": at most 10 letters}'),
    "rocket": ("a rocket taking off", "{}"),
    "boxes": ("a stack of shipping boxes", '{"text": at most 6 letters}'),
    "question": ("a box with a question mark (the unknown, the doubt)", "{}"),
    "badge": ("the company's logo tile", '{"brand", "text"}'),
    "gavel": ("a judge's gavel", "{}"),
}
# the words slammed on a shot, in the band above the subjects: at most one a shot
FLAT = {
    "title": ("the hook's promise in huge letters, two lines, the second in gold (the first shot has one)", '{"text": at most 28 letters}'),
    "counter": ("a big number rolling up", '{"to": number, "prefix": "$", "suffix": "%", "text": what it is, at most 18 letters, "color": "#hex"}'),
    "stamp": ("a red stamp", '{"text": at most 12 letters}'),
}


# ---------------------------------------------------------------- the writer
def system():
    return ("You write one short vertical video for Meme Street (memestreet.net, a free daily stock-chart game): the true story "
            "behind the stock in today's Daily, over the exact stretch of time the game showed, as a 3D story explainer. A stranger "
            "scrolling past must stop in the first second and stay to the last line, so it is ONE story, never a list of headlines: "
            "someone is in trouble or makes a bet, it turns, it pays off or bites back, and the last line lands.\n\n"
            "A reel whose rhythm to copy (never its words): " + open(os.path.join(HERE, "REFERENCE.md"), encoding="utf-8").read())


def story_text(story):
    return json.dumps({k: story[k] for k in ("stock", "window", "prices", "research") if k in story}, indent=1)


def opening(story):
    """The words every reel begins with: whose chart this is ('Today's mystery chart on Meme Street')."""
    return f"{story.get('day') or 'Today' + chr(39) + 's'} mystery chart on Meme Street"


def ask(story, recent=(), critique=None):
    kinds = "\n".join(f"  {k}: {v[0]}. Fields {v[1]}." for k, v in KINDS.items())
    flats = "\n".join(f"  {k}: {v[0]}. Fields {v[1]}." for k, v in FLAT.items())
    return ("THE TRUE STORY. Every figure, date, name and claim you write must be in here, nothing else:\n" + story_text(story) +
            "\n\nWRITE the reel as JSON only:\n"
            '{"title": the post title (8 to 14 words, the company named, one loaded word),\n'
            ' "brands": [{"name": the company as it is said ("GoPro"), "color": its brand colour "#rrggbb", a bright one}] '
            '(a second brand only for a real rival or opponent in the story),\n'
            ' "cast": 1 to 4 people of the story, by role, never a private person: [{"id", "tag": their on-screen tag, at most 22 letters '
            '("NICK WOODMAN, CEO", "A GOPRO FAN", "SHORT SELLERS"), "look": one of ' + json.dumps(LOOKS) + ', "color": "#rrggbb"}],\n'
            ' "sentences": [17 to 24 of {"say": the sentence,\n'
            '   "scene": {"bg": the set, "label": null or the date of this moment, at most 14 letters ("OCT 2020", "BLACK FRIDAY"),\n'
            '             "items": [1 or 2 subjects, the bigger one first, then at most one line of words: {"kind", "on": the word of the '
            'sentence at which it appears, ...its fields}]}}],\n'
            ' "caption": the post caption: the title as its first line, then the whole script as one paragraph}\n\n'
            "EVERY SENTENCE IS ONE SHOT. The camera frames its subjects so that they fill the screen, so one subject is huge and two "
            "share the frame: choose the ONE thing the sentence is about (never decoration), and a second subject only when the "
            "sentence is about two things (the founder AND his idea, the results AND the money). The first subject is on screen as "
            "the shot opens; the second comes in a moment later and the words on their word (\"on\").\n"
            "THE SETS (\"bg\"):\n" + "\n".join(f"  {k}: {v}." for k, v in BGS.items()) + "\n"
            "THE SUBJECTS:\n" + kinds + "\n"
            "THE WORDS (at most one a shot, only when a figure or a verdict deserves to be read big):\n" + flats + "\n\n"
            "SHOW THE STORY, literally: what the company makes (the product), the product being made (the factory), sold (the "
            "store) and used (action, phone); each event with its own subject, set and date; the people (the founder, buyers, "
            "traders) acting the moment with their pose; the price on the real chart at least twice more as the story moves "
            "(from/to are points of the window, 0 = its first day, 1 = its last; each of these ends later than the one before). "
            "Use at least 9 different kinds and at least 6 different sets; never the same set three sentences running.\n"
            "THE OPENING IS FIXED IN FORM, because the reel is the answer to a game: Meme Street shows a mystery chart every day and "
            "this is the story behind it.\n"
            f"  Sentence 1 begins \"{opening(story)}\" and never names the company: it says the most surprising true thing the "
            "chart did, with a figure, in at most 16 words (\"" + opening(story) + " doubled from $4.80 in a pandemic.\"). Its shot is "
            "the mystery itself: a chart with \"title\": \"???\" from 0 to its most dramatic point, a question box beside it, and a "
            "title of at most 28 letters in two short lines that holds the surprise (\"DOUBLED IN A PANDEMIC\").\n"
            "  Sentence 2 is the reveal: it names the company and what it makes (\"It was GoPro, the maker of action cameras.\"). Its "
            "shot is the product, or someone using it, with the title \"IT WAS <NAME>\".\n"
            "THE STORY, from sentence 3: 160 to 220 words in all, sentences of 5 to 16 words, most under 11. The trouble, the bet, "
            "the proof (a figure, the stock), the blow, where it ended against where it began, then a line that is a further true "
            "fact with a sting (a doubt, a catch, what came next); no moral, no question, no call to follow, like or comment. Link "
            "the steps with 'then', 'but', 'so': each sentence makes the next one wanted. Say what happened as a fact; never name a "
            "news outlet (the sources go in the caption). Name the company the way it is said (GoPro), never its ticker. Say prices "
            "simply ('$4.80', 'near $8'). AT MOST 16 NUMBERS in the whole script (dates count): give a figure only where it is the "
            "point. Name a person only if the research names them as a public figure.\n"
            f"THE LAST SENTENCE is always, word for word: \"{CLOSE}\" Its shot: a phone ({{\"kind\": \"phone\", \"title\": \"MEME STREET\", "
            "\"lines\": [\"NEW CHART\", \"AT MIDNIGHT\"], \"tap\": true}) and a question box."
            + (("\n\nRecent titles, not to repeat: " + json.dumps(list(recent)[-12:])) if recent else "")
            + (("\n\nTHE LAST CUT WAS SHOWN TO A PANEL OF VIEWERS AND SOME SWIPED AWAY. Who left, when and why:\n" + critique["why"] +
                "\nKeep the format; change what made them leave, then reply with the whole JSON again.") if critique else ""))


def parse(txt):
    m = re.search(r"\{.*\}", txt, re.S)
    if not m: raise ValueError("no JSON in the reply")
    return json.loads(m.group(0))


NUMW = re.compile(r"\$?\d[\d,.]*%?")
SCALE = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
def nums(text):
    """The figures in a text as plain digit strings ('$60,000' -> '60000'); a scale word counts both ways; '8.04' allows '8'."""
    out = {re.sub(r"[^\d.]", "", x).rstrip(".") for x in NUMW.findall(text or "") if re.sub(r"[^\d]", "", x)}
    for n, w in re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*(thousand|million|billion|trillion)", text or "", re.I):
        v = float(n.replace(",", "")) * SCALE[w.lower()]; out.add(str(int(v)) if v == int(v) else str(v))
    for n, w in re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*([KMB])\b", text or ""):
        v = float(n.replace(",", "")) * {"K": 1e3, "M": 1e6, "B": 1e9}[w]; out.add(str(int(v)) if v == int(v) else str(v))
    for x in list(out):
        if "." in x: out |= {x.rstrip("0").rstrip("."), str(round(float(x)))}
    return out


HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
def shown(it):
    """The words and figures a prop puts on screen."""
    v = [it.get(k) for k in ("text", "title", "sign", "month", "day")] + list(it.get("lines") or []) + [b.get("text") for b in it.get("bars") or []]
    if it.get("kind") == "counter": v.append(str(it.get("to", "")))
    return " ".join(str(x) for x in v if x not in (None, ""))


def errors(spec, story):
    """Everything the format can check in code, in words the writer can act on."""
    E = []; S = spec.get("sentences") or []; C = spec.get("cast") or []; ids = [c.get("id") for c in C]; B = spec.get("brands") or []
    if not 17 <= len(S) <= 24: E.append(f"{len(S)} sentences: write 17 to 24")
    words = sum(len(str(s.get("say", "")).split()) for s in S)
    if not 160 <= words <= 220: E.append(f"{words} words: write 160 to 220")
    for k, s in enumerate(S):
        n = len(str(s.get("say", "")).split())
        if not 5 <= n <= 16: E.append(f"sentence {k + 1} is {n} words: 5 to 16 (a shot needs two seconds)")
    name = str((B[0] if B else {}).get("name") or story.get("stock", {}).get("name", ""))
    if S:
        h = str(S[0].get("say", "")); first = (S[0].get("scene") or {}).get("items") or []
        if not h.lower().startswith(opening(story).lower()): E.append(f"the first sentence begins \"{opening(story)}\" (the reel is the story behind the game's chart)")
        if len(h.split()) > 16: E.append("the first sentence is at most 16 words")
        if "?" in h or re.search(r"\b(you|your|imagine|did you know)\b", h, re.I): E.append("the first sentence is a statement: no question, no 'you', no 'imagine'")
        if not re.search(r"\d", h): E.append("the first sentence holds a figure (a price, a percentage, a count)")
        if name and re.search(rf"\b{re.escape(name)}\b", h, re.I): E.append("the first sentence never names the company: the chart is a mystery until sentence 2")
        if not any(it.get("kind") == "chart" and str(it.get("title")) == "???" for it in first): E.append("the first shot shows the mystery chart with \"title\": \"???\"")
        if not any(it.get("kind") == "title" for it in first): E.append("the first shot carries a title: the surprise in at most 28 letters")
        if len(S) > 1 and name and not re.search(rf"\b{re.escape(name)}\b", str(S[1].get("say", "")), re.I): E.append("the second sentence is the reveal: it names the company")
        if str(S[-1].get("say", "")).strip() != CLOSE: E.append(f"the last sentence is, word for word: \"{CLOSE}\"")
        st = str(S[-2].get("say", "")) if len(S) > 1 else ""
        if "?" in st or re.search(r"\b(follow|subscribe to|comment|like and|lesson|moral)\b", st, re.I): E.append("the line before the last is a further fact with a sting: no question, no moral, no call to follow")
    txt = " ".join(str(s.get("say", "")) for s in S); facts = story_text(story)
    tk = str(story.get("stock", {}).get("ticker", "")); nm = str(story.get("stock", {}).get("name", ""))
    if tk and tk.lower() != nm.lower() and re.search(rf"\b{re.escape(tk)}\b", txt): E.append(f"never say the ticker {tk}: say the company's name")
    if re.search(r"\breported\b", txt, re.I): E.append("say what happened as a fact: no 'X reported' (the sources go in the caption)")
    items = [it for s in S for it in ((s.get("scene") or {}).get("items") or [])]
    screen = " ".join(shown(it) for it in items) + " " + " ".join(str((s.get("scene") or {}).get("label") or "") for s in S)
    extra = sorted(nums(txt + " " + screen) - nums(facts) - {"0", "1", "2", "3"})
    if extra: E.append("these figures are not in the true story: " + ", ".join(extra) + " (use only its own figures)")
    OPEN = {"in", "by", "at", "then", "when", "the", "this", "these", "despite", "after", "on", "as", "for", "but", "and", "so", "even",
            "a", "an", "within", "over", "until", "while", "that", "its", "his", "her", "their", "today", "now", "black", "wall", "meme", "street"}
    def unknown(run):              # (a run of capitalised words is a name the research lacks only if none of its pairs is in it)
        w = [x for x in run.split() if x.lower() not in OPEN]
        return len(w) >= 2 and not any(f"{a} {b}".lower() in facts.lower() for a, b in zip(w, w[1:]))
    names = {r for r in re.findall(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)+\b", txt) if unknown(r)}
    if names: E.append("these names are not in the research: " + ", ".join(sorted(names)) + " (name only its public figures; otherwise the role)")
    nn = len(NUMW.findall(txt))
    if nn > 16: E.append(f"{nn} numbers in the script: at most 16")
    if not 1 <= len(B) <= 2 or not all(HEX.match(str(b.get("color", ""))) and b.get("name") for b in B): E.append("1 or 2 brands, each with a name and a #rrggbb colour")
    if not 1 <= len(C) <= 4: E.append("1 to 4 cast members")
    if len(set(ids)) != len(ids) or not all(ids): E.append("every cast member has its own id")
    for c in C:
        if c.get("look") not in LOOKS: E.append("a cast member's look is one of " + ", ".join(LOOKS))
        if not HEX.match(str(c.get("color", ""))): E.append("a cast member's colour is #rrggbb")
        if not 2 <= len(str(c.get("tag", ""))) <= 22: E.append("a tag is at most 22 letters")
        if not any(it.get("who") == c.get("id") or c.get("id") in (it.get("first"), it.get("second"), it.get("third")) for it in items):
            E.append(f"cast member '{c.get('id')}' never appears in a scene")
    bgs = []; last = -1.0; kinds = set()
    for k, s in enumerate(S):
        sc = s.get("scene") or {}; IT = sc.get("items") or []; where = f"sentence {k + 1}"
        bgs.append(sc.get("bg"))
        if sc.get("bg") not in BGS: E.append(f"{where}: bg is one of " + ", ".join(BGS))
        if sc.get("label") and len(str(sc["label"])) > 14: E.append(f"{where}: the date is at most 14 letters")
        subs = [it for it in IT if it.get("kind") in KINDS]; fl = [it for it in IT if it.get("kind") in FLAT]
        for it in IT:
            if it.get("kind") not in KINDS and it.get("kind") not in FLAT: E.append(f"{where}: '{it.get('kind')}' is not a subject (" + ", ".join(KINDS) + ") nor words (" + ", ".join(FLAT) + ")")
        if not 1 <= len(subs) <= 2: E.append(f"{where}: {len(subs)} subjects: a shot has 1 or 2")
        if len(fl) > 1: E.append(f"{where}: at most one line of words a shot")
        if k > 1 and any(it.get("kind") == "title" for it in fl): E.append(f"{where}: only the first two shots carry a title (the mystery, the reveal)")
        for it in IT:
            kd = it.get("kind"); kinds.add(kd)
            if kd == "person" and it.get("who") not in ids: E.append(f"{where}: a person's 'who' is a cast id")
            if kd in ("person", "crowd") and it.get("pose", "stand") not in POSES: E.append(f"{where}: pose is one of {POSES}")
            if kd == "podium" and it.get("first") not in ids: E.append(f"{where}: a podium's 'first' is a cast id")
            if kd in ("product", "factory", "store") and it.get("product", "box") not in PRODUCTS: E.append(f"{where}: product is one of " + ", ".join(PRODUCTS))
            if kd == "chart":
                try: a, b = float(it["from"]), float(it["to"]); assert 0 <= a < b <= 1 and (not k or b >= last); last = b if k else last      # (the mystery chart shows the whole run; the story's charts move forward)
                except Exception: E.append(f"{where}: a chart's from < to, both 0 to 1, each chart ending later than the last")
            if kd == "counter" and not isinstance(it.get("to"), (int, float)): E.append(f"{where}: a counter's 'to' is a number")
            if kd == "bars" and not (2 <= len(it.get("bars") or []) <= 3 and all(isinstance(b.get("value"), (int, float)) for b in it["bars"])): E.append(f"{where}: bars has 2 or 3 bars with number values")
            if any(len(str(l)) > 14 for l in it.get("lines") or []) or len(it.get("lines") or []) > 3: E.append(f"{where}: lines are at most 14 letters, at most 3")
            for f, n in (("text", 28 if kd == "title" else 18 if kd == "counter" else 12), ("sign", 10), ("title", 12)):
                if it.get(f) and len(str(it[f])) > n: E.append(f"{where}: a {kd}'s {f} is at most {n} letters")
            if kd in ("stamp", "title") and not it.get("text"): E.append(f"{where}: a {kd} has text")
    if sum(1 for it in items if it.get("kind") == "chart") < 3: E.append("show the real chart at least twice more as the story moves")
    if len(kinds & set(KINDS)) < 9: E.append(f"{len(kinds & set(KINDS))} different subjects: use at least 9")
    if len(set(bgs)) < 6: E.append(f"{len(set(bgs))} sets: use at least 6")
    if any(a == b == c for a, b, c in zip(bgs, bgs[1:], bgs[2:])): E.append("never the same set three sentences running")
    if not 8 <= len(str(spec.get("title", "")).split()) <= 15: E.append("the title is 8 to 14 words")
    return E


def write(story, recent=(), critique=None):
    import make_spec as M
    sysp, fix, spec = system(), None, None
    msgs = [{"role": "user", "content": ask(story, recent, critique)}]
    for k in range(6):                                   # (a fix sees its own last script: fresh rewrites kept making new faults)
        reply = M.claude_cli(msgs, sysp, model=os.environ.get("EXPLAINER_MODEL", "opus"))
        try: spec = parse(reply); fix = errors(spec, story)
        except ValueError as e: spec, fix = None, [f"the reply was not valid JSON ({str(e)[:80]})"]
        if not fix: return spec
        say("the format sent it back:", "; ".join(fix)[:600])
        msgs += [{"role": "assistant", "content": reply},
                 {"role": "user", "content": "Sent back. Change only what these name, keep the rest, and reply with the whole JSON again: " + "; ".join(fix)}]
    raise SystemExit("not made: the script failed the format six times: " + "; ".join(fix))


# ---------------------------------------------------------------- the voice
LEX = json.load(open(os.path.join(HERE, "say.json"), encoding="utf-8"))
def spoken(text, story=None):
    """What the voice reads (the captions keep the text). A ticker as the company's name, then the house words (say.json: the
    owner's corrections, respelt until the voice's phonemes are right: 'GoPro' -> 'Goh Proh' is two stressed words, where
    'Go Pro' came out as one, 'go-PRO'), a domain's '.com' as 'dot com', glued capitals and digits apart ('HERO9' -> 'Hero 9'),
    CamelCase apart, '$60,000' -> '60,000 dollars', '$4.80' -> '4 dollars 80', '4%' -> '4 percent'."""
    st = (story or {}).get("stock", {})
    if st.get("ticker") and st.get("name"): text = re.sub(rf"\b{re.escape(st['ticker'])}\b", st["name"], text)
    for a, b in LEX.items(): text = re.sub(rf"(?<![A-Za-z]){re.escape(a)}(?![A-Za-z])", b, text)
    text = re.sub(r"\.(com|net|org|io)\b", r" dot \1", text)
    text = re.sub(r"\b([A-Z]{3,})(\d+)\b", lambda m: m.group(1).capitalize() + " " + m.group(2), text)
    text = re.sub(r"\b(?!Mc|Mac)([A-Z][a-z]+)([A-Z][a-z]+)\b", r"\1 \2", text)
    text = re.sub(r"\$(\d[\d,]*)\.(\d\d)(?!\d|\s+(?:thousand|million|billion|trillion))", r"\1 dollars \2", text)       # ('$4.80': money, not a decimal)
    text = re.sub(r"\$(\d(?:[\d,]*\d)?(?:\.\d+)?)(\s+(?:thousand|million|billion|trillion))?", lambda m: f"{m.group(1)}{m.group(2) or ''} dollars", text)
    return re.sub(r"(\d)%", r"\1 percent", text)


def phrases(spec):
    S = spec["sentences"]; out = []
    for i, s in enumerate(S):
        parts = [p.strip() for p in re.split(r"(?<=,)\s+", str(s["say"]).strip()) if p.strip()]
        for j, p in enumerate(parts):
            last = j == len(parts) - 1
            gap = GAP["comma"] if not last else GAP["hook"] if i == 0 else GAP["stop"]
            out.append({"i": i, "text": p, "gap": 0 if (last and i == len(S) - 1) else gap})
    return out


TURN = re.compile(r"(But|Then|So|Yet|Still|Instead|Weeks|Days|Months|By|In \d|On \w+ \d|A new mystery)\b")
def rest(before, nxt, n, last=False, comma=False):
    """How long a person pauses here (the owner, 2026-11-23: "make the audio sound more human, especially the timing between
    words/sentences"; the third model reel's narrator: 13 pauses in 100 words, median 0.34 s, the longest 0.66 s).
    before = the words just said, nxt = the next word(s), n = how many words the stretch just said had.
    After a sentence: a beat before a turn ("But", "Then", a new date), longer after a long sentence or a figure that lands,
    quick between two lines that run on; the closing line comes after the longest. At a comma: short, a little longer after a
    long clause. A small, fixed variation so no two are alike. -> seconds"""
    import zlib
    j = (zlib.crc32((before + "|" + nxt).encode()) % 1000) / 1000 - .5          # (-0.5 to 0.5, the same each time for the same words)
    if comma: return round(min(.22, max(.08, .1 + .012 * n + .04 * j)), 3)
    t = .2 + .009 * min(n, 12) + .05 * j
    if re.search(r"\d", before.split()[-1] if before.split() else ""): t += .04            # (a figure that lands gets a moment)
    if TURN.match(nxt): t += .12
    if last: t = max(t, .55)
    return round(min(.55, max(.16, t)), 3)


def breaths(size, soft, most=BREATH):
    """The sentences shared out into breaths: stretches the voice speaks in one go, as even as they come (a short one is
    spoken at another pace and loudness than its neighbours). size = each sentence's phonemes, soft = whether it leans on the
    sentence before it ('And...': never the first of a breath). -> [[sentence, ...], ...]"""
    n = max(1, math.ceil(sum(size) / most)); goal = sum(size) / n; out, cur, done = [], [], 0
    for i, p in enumerate(size):
        have = sum(size[j] for j in cur)
        if cur and (have + p > 480 or (len(out) < n - 1 and done + have + p / 2 > goal * (len(out) + 1) and not soft[i])): out.append(cur); done += have; cur = []
        cur.append(i)
    return out + [cur]


def loud(x, sr):
    """How loud a sound is while it sounds: the level of its louder half (50 ms blocks)."""
    import numpy as np
    n = int(.05 * sr); r = np.sqrt((np.asarray(x, np.float64)[: len(x) // n * n].reshape(-1, n) ** 2).mean(1)); return float(np.sqrt((np.sort(r)[len(r) // 2:] ** 2).mean()))


def quiet(a, sr, least=.12, floor=-40):
    """The pauses in a clip: stretches of at least `least` seconds that stay `floor` dB under its loudest 10 ms.
    -> [[start, length], ...] in seconds"""
    import numpy as np
    n = int(.01 * sr); r = np.sqrt((np.asarray(a, np.float64)[: len(a) // n * n].reshape(-1, n) ** 2).mean(1)); q = r <= r.max() * 10 ** (floor / 20)
    e = np.flatnonzero(np.diff(np.concatenate([[0], q.astype(np.int8), [0]])))          # each run's first frame, and the frame after its last
    return [[round(a0 * .01, 2), round((a1 - a0) * .01, 2)] for a0, a1 in zip(e[::2].tolist(), e[1::2].tolist()) if (a1 - a0) * .01 >= least]


def flow(a, sr, wt, own):
    """A breath paced as a person would pace it. Every pause stays where the voice put it and gets a person's length (PAUSES):
    the one between two sentences, the one after a comma, and a stop in mid-phrase (before a figure, say), which a person
    hardly makes. Only silence is taken out or put in, in the middle of the pause: no sound is cut.
    a = the breath, wt = its written words with first-guess times [[word, start, end], ...], own = each word's sentence.
    -> (the audio, {sentence: (start, end)}, the pauses as they now are [[start, length], ...], f: a time in the old audio -> the new)"""
    import numpy as np
    d = len(a) / sr; Q = quiet(a, sr); tail = Q.pop() if Q and Q[-1][0] + Q[-1][1] >= d - .02 else None
    G = []                                     # the gaps between words: (from, to, what the text asks for there, the word before)
    for k in range(len(wt) - 1):
        lo, hi = sorted((wt[k][2], wt[k + 1][1])); w = wt[k][0].rstrip("\"')")
        G.append((lo, hi, "stop" if own[k] != own[k + 1] else "comma" if w[-1:] in ",;:.!?" else None, k))
    far = lambda q, g: max(g[0] - (q[0] + q[1] / 2), (q[0] + q[1] / 2) - g[1], 0); kind = [None] * len(Q); ends = {}; which = {}
    for want, reach in (("stop", .5), ("comma", .45)):          # (the transcriber stretches a word over the pause beside it, so a pause is looked for around its gap)
        for g in G:
            c = [j for j in range(len(Q)) if kind[j] is None and far(Q[j], g) <= reach] if g[2] == want else []
            if c:
                j = max(c, key=lambda j: Q[j][1]) if want == "stop" else min(c, key=lambda j: far(Q[j], g)); kind[j] = want; which[j] = g[3]
                if want == "stop": ends[g[3]] = j
    def want(j):                               # a person's pause for this one (rest()), or, mid-phrase, as short as the voice allows
        if kind[j] is None: return min(Q[j][1], PAUSES[None][2])
        k = which[j]; said = [w[0] for i, w in enumerate(wt[:k + 1]) if own[i] == own[k]]
        if kind[j] == "comma": said = " ".join(said).split(",")[-1].split()
        return rest(" ".join(said), " ".join(w[0] for w in wt[k + 1:k + 4]), len(said), last=k + 1 < len(wt) and wt[k + 1][0] == CLOSE.split()[0] and " ".join(w[0] for w in wt[k + 1:k + 4]) == " ".join(CLOSE.split()[:3]), comma=kind[j] == "comma")
    new = [want(j) for j in range(len(Q))]
    parts, edits, pos = [], [], 0              # edits: (from, to) of the old audio taken out; silence put in is (at, at - its length)
    for q, n in zip(Q, new):
        c, x = q[0] + q[1] / 2, (q[1] - n) / 2
        if x > 0: parts.append(a[pos:int((c - x) * sr)]); pos = int((c + x) * sr); edits.append((c - x, c + x))
        elif x < 0: parts += [a[pos:int(c * sr)], np.zeros(int(-2 * x * sr), a.dtype)]; pos = int(c * sr); edits.append((c, c + 2 * x))
    b = np.concatenate(parts + [a[pos:]])
    f = lambda t: t - sum(min(max(t - x0, 0), x1 - x0) if x1 > x0 else (x1 - x0 if t >= x0 else 0) for x0, x1 in edits)
    spans, start = {}, 0.0
    for k in range(len(wt) - 1):               # each sentence: from the end of the pause before it to the start of the pause after
        if own[k] == own[k + 1]: continue
        e = f(Q[ends[k]][0]) if k in ends else f((wt[k][2] + wt[k + 1][1]) / 2)        # (no pause there: the voice ran on, and so does the cut)
        spans[own[k]] = (round(start, 3), round(e, 3)); start = e + (new[ends[k]] if k in ends else 0)
    spans[own[-1]] = (round(start, 3), round(f(tail[0]) if tail else len(b) / sr, 3))
    return b, spans, [[round(f(q[0]), 3), round(n, 3)] for q, n in zip(Q, new) if n >= .06], f


def el_say(text, before="", after=""):
    """One breath read by ElevenLabs, with the breaths around it as context so it is read as part of one telling. -> float32 at 24 kHz"""
    import numpy as np, urllib.request
    body = {"text": text, "model_id": EL_MODEL, "voice_settings": EL_SET, **({"previous_text": before[-600:]} if before else {}), **({"next_text": after[:600]} if after else {})}
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{EL_VOICE}?output_format=pcm_24000", data=json.dumps(body).encode(),
                                 headers={"xi-api-key": os.environ["ELEVEN_API_KEY"].strip(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r: return np.frombuffer(r.read(), np.int16).astype(np.float32) / 32768


def el_text(text, story=None):
    """What ElevenLabs reads: as spoken() but without the respellings made for the other voice (it says "GoPro" right)."""
    st = (story or {}).get("stock", {})
    if st.get("ticker") and st.get("name"): text = re.sub(rf"\b{re.escape(st['ticker'])}\b", st["name"], text)
    text = re.sub(r"\.(com|net|org|io)\b", r" dot \1", text)
    return re.sub(r"\b([A-Z]{3,})(\d+)\b", lambda m: m.group(1).capitalize() + " " + m.group(2), text)


def voice(spec, work, story=None):
    """The script in the voice, paced as a person reads aloud. The owner, 2026-11-23: "make sure the audio is smoother ... it
    should flow like normal human speech". Before, every clause was spoken on its own, each at its own speed (0.98x to 1.25x,
    to force 3.2 words a second), and glued with fixed gaps: a new tempo and a stop at every comma, the pauses all alike
    (median 0.62 s as heard; in the reel the owner sent as a model 0.28 s). Now the sentences are shared out into even breaths
    that the voice speaks in one go, so its melody runs through the commas and from sentence to sentence; all at ONE speed;
    its pauses are kept where it put them and made a person's (flow()); the breaths are set to one loudness.
    -> (wav path, [(sentence, start, end, text)], the words as heard [(word, start, end)], T)."""
    import numpy as np, soundfile as sf
    from kokoro_onnx import Kokoro
    from voice import MODEL, trim, words as asr
    K = Kokoro(os.path.join(MODEL, "kokoro-v1.0.onnx"), os.path.join(MODEL, "voices-v1.0.bin")); SR = 24000
    S = [str(x["say"]).strip() for x in spec["sentences"]]; out = [spoken(x, story) for x in S]; made = []
    B = breaths([len(K.tokenizer.phonemize(x, "en-us")) for x in out], [bool(re.match(r"(And|So|Or|Plus|Because)\b", x)) for x in S]); el = TTS == "eleven" and os.environ.get("ELEVEN_API_KEY", "").strip()
    for bi, idx in enumerate(B):
        a = None
        if el:
            try:
                txt = lambda b: " ".join(el_text(S[i], story) for i in b)
                a = el_say(txt(idx), txt(B[bi - 1]) if bi else "", txt(B[bi + 1]) if bi + 1 < len(B) else ""); sr = 24000
            except Exception as e: say("ElevenLabs failed, the other voice reads this reel:", str(e)[:120]); el = False; made = []; break
        if a is None: a, sr = K.create(" ".join(out[i] for i in idx), voice=VOICE, speed=SPEED, lang="en-us")
        a = trim(np.asarray(a, np.float32), sr)
        tmp = os.path.join(work, "breath.wav"); sf.write(tmp, a, sr); heard = asr(tmp); os.remove(tmp)
        if not heard: raise SystemExit("not made: the voice could not be timed (the transcriber gave no words)")
        wt = align(estimate([(0, 0.0, len(a) / sr, " ".join(S[i] for i in idx))]), heard)
        b, spans, rests, f = flow(a, sr, wt, [i for i in idx for _ in S[i].split()]); H = []
        for w, t0, t1 in heard:                # (the transcriber stretches a word over the pause beside it: the word is where the sound is)
            t0, t1 = f(t0), f(t1)
            for r0, rl in rests:
                if min(t1, r0 + rl) - max(t0, r0) > .03:
                    if r0 + rl / 2 < (t0 + t1) / 2: t0 = min(r0 + rl, t1 - .05)
                    else: t1 = max(r0, t0 + .05)
            H.append((w, t0, t1))
        made.append((b, spans, H))
    if not made:                               # (ElevenLabs failed part-way: one voice for the whole reel, never two)
        os.environ["EXPLAINER_TTS"] = "kokoro"; globals()["TTS"] = "kokoro"; return voice(spec, work, story)
    level = sorted(loud(b, SR) for b, _, _ in made)[len(made) // 2]; t, parts, segs, W = 0.0, [], [], []
    for k, (b, spans, H) in enumerate(made):
        b = b * (level / loud(b, SR)); n = int(.006 * SR); b[:n] *= np.linspace(0, 1, n); b[-4 * n:] *= np.linspace(1, 0, 4 * n)      # (one loudness, soft edges)
        segs += [(i, round(t + a0, 3), round(t + a1, 3), S[i]) for i, (a0, a1) in sorted(spans.items())]; W += [(w, t + t0, t + t1) for w, t0, t1 in H]
        nxt = made[k + 1][2][0][0] if k + 1 < len(made) and made[k + 1][2] else ""; last_s = max(spans)
        gap = 0 if k == len(made) - 1 else max(.05, rest(S[last_s], " ".join(S[min(last_s + 1, len(S) - 1)].split()[:3]), len(S[last_s].split()), last=S[min(last_s + 1, len(S) - 1)] == CLOSE) - .17)      # (trim leaves 0.15 s after a breath and 0.02 s before the next)
        parts += [b.astype(np.float32), np.zeros(int(gap * SR), np.float32)]; t += len(b) / SR + gap
    wav = os.path.join(work, "voice.wav"); sf.write(wav, np.concatenate(parts), SR)
    say(f"voice: {'ElevenLabs ' + EL_VOICE if el else 'Kokoro at ' + str(SPEED)}, {len(made)} breaths, {t:.1f}s, {sum(len(x.split()) for x in S) / t:.2f} words a second")
    return wav, segs, W, t + 1.0


def estimate(segs):
    """Every written word with a first guess at its time: its share of its phrase, by letters. -> [[word, start, end, sentence, phrase start, phrase end]]"""
    out = []
    for i, a, b, text in segs:
        toks = text.split(); L = [len(re.sub(r"\W", "", x)) + 2 for x in toks]; c = a
        for tk, l in zip(toks, L): out.append([tk, c, c + (b - a) * l / sum(L), i, a, b]); c += (b - a) * l / sum(L)
    return out


def align(est, W):
    """The times of the words as heard (W = the transcriber's [(word, start, end)]) given to the written ones. They are matched
    LETTER BY LETTER: the transcriber writes '$4.80' as '4' '80', '500,000' as '500' '000' and 'GoPro.com' as 'gopro' 'com', so
    matching word by word lost exactly the figures and the name, which then popped in on a guess (the owner, 2026-11-23: "the
    caption timings can be better"). A word it did not hear sits between its neighbours; a phrase's first word starts with its
    phrase, which is known exactly. -> [[word, start, end, sentence]]"""
    norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
    out = [list(w) for w in est]; W = [(norm(w[0]), w[1], w[2]) for w in W]; W = [w for w in W if w[0]]; heard = {}
    if W:
        A = [(k, c) for k, w in enumerate(out) for c in norm(w[0])]
        Bt = [(w[1] + (w[2] - w[1]) * j / len(w[0]), w[1] + (w[2] - w[1]) * (j + 1) / len(w[0]), c) for w in W for j, c in enumerate(w[0])]
        for blk in difflib.SequenceMatcher(None, [c for _, c in A], [c for *_, c in Bt], autojunk=False).get_matching_blocks():
            for q in range(blk.size):
                k = A[blk.a + q][0]; a, b, _ = Bt[blk.b + q]; g = heard.setdefault(k, [a, b, 0]); g[0] = min(g[0], a); g[1] = max(g[1], b); g[2] += 1
        heard = {k: g for k, g in heard.items() if 2 * g[2] >= len(norm(out[k][0])) and out[k][4] - .2 <= g[0] <= out[k][5] + .2}      # (most of its letters, and inside its own phrase)
    for k, w in enumerate(out):
        if k in heard: w[1], w[2] = max(w[4], heard[k][0]), min(w[5], max(heard[k][1], heard[k][0] + .05))
    k = 0
    while k < len(out):                      # each phrase: its first word starts with it, the unheard are shared out between their neighbours
        j = k
        while j < len(out) and out[j][4] == out[k][4]: j += 1
        a, b = out[k][4], out[k][5]; out[k][1] = a + .02; idx = list(range(k, j)); q = 0
        while q < len(idx):
            if idx[q] in heard or q == 0: q += 1; continue
            r = q
            while r < len(idx) and idx[r] not in heard: r += 1
            t0 = out[idx[q - 1]][2] if (idx[q - 1] in heard) else out[idx[q - 1]][1] + .12; t1 = out[idx[r]][1] if r < len(idx) else b - .1
            if q == 1 and idx[0] not in heard: t0 = a + .02; q = 0                       # (the phrase's first words unheard too: share from its start)
            L = [len(norm(out[x][0])) + 2 for x in idx[q:r]]; c = t0
            for x, l in zip(idx[q:r], L): out[x][1], out[x][2] = c, c + max(.0, t1 - t0) * l / sum(L); c = out[x][2]
            q = r
        for x in idx[1:]: out[x][1] = max(out[x][1], out[x - 1][1] + .04)            # (in order, never two at once)
        for x in idx: out[x][2] = max(out[x][2], out[x][1] + .05)
        k = j
    return [[w[0], round(w[1], 3), round(w[2], 3), w[3]] for w in out]


def captions(wt, spec, sp=None):
    """The captions: a clause at a time, in equal parts of at most CAP_WORDS words (never one word left over on its own), each
    part on screen whole, CAP_LEAD before its first word is heard, until the next; the brands in their colours, figures in gold.
    A sentence's last caption ends at its shot's cut."""
    col = {re.sub(r"\W", "", b["name"].lower()): b["color"] for b in spec.get("brands") or []}
    def color(w):
        k = re.sub(r"('s|s')$", "", re.sub(r"[^\w']", "", w.lower()))
        return col.get(re.sub(r"\W", "", k)) or (GOLD if re.search(r"\d", w) else None)
    clauses, cur = [], []
    for w in wt:
        if cur and cur[-1][3] != w[3]: clauses.append(cur); cur = []
        cur.append(w)
        if re.search(r"[,;:]$", w[0]) and len(cur) >= 2: clauses.append(cur); cur = []
    if cur: clauses.append(cur)
    for k in range(len(clauses) - 1, 0, -1):          # (a clause of one word joins the one before it in its sentence)
        if len(clauses[k]) == 1 and clauses[k - 1][-1][3] == clauses[k][0][3]: clauses[k - 1] += clauses.pop(k)
    groups = []
    for c in clauses:
        n = math.ceil(len(c) / CAP_WORDS); j = 0
        for k in range(n): size = len(c) // n + (k < len(c) % n); groups.append(c[j:j + size]); j += size          # (seven words: 3, 2, 2, never 3, 3, 1)
    k = 0
    while k < len(groups):                   # (a caption there for under half a second cannot be read: it joins its shorter neighbour in the sentence)
        g = groups[k]; nxt = groups[k + 1] if k + 1 < len(groups) and groups[k + 1][0][3] == g[0][3] else None; prv = groups[k - 1] if k and groups[k - 1][0][3] == g[0][3] else None
        end = nxt[0][1] if nxt else g[-1][2] + .3
        if end - g[0][1] < CAP_MIN and (nxt or prv):
            if nxt and (not prv or len(nxt) <= len(prv)) and len(g) + len(nxt) <= CAP_WORDS + 2: groups[k:k + 2] = [g + nxt]; continue
            if prv and len(g) + len(prv) <= CAP_WORDS + 2: groups[k - 1:k + 1] = [prv + g]; k -= 1; continue
        k += 1
    out = []; t0 = lambda w: round(max(0, w[1] - CAP_LEAD), 3)
    for k, g in enumerate(groups):
        t1 = t0(groups[k + 1][0]) if k + 1 < len(groups) else g[-1][2] + .8
        if sp and k + 1 < len(groups) and groups[k + 1][0][3] != g[-1][3]: t1 = min(t1, shot_at(sp, groups[k + 1][0][3]))      # (a sentence's last words leave with its shot, not over the next one)
        out.append({"t0": t0(g[0]), "t1": round(t1, 3), "words": [{"text": w[0], "t0": t0(w), "color": color(w[0]), "hot": bool(re.search(r"\d", w[0]) or color(w[0]) not in (None, GOLD) or (re.search(r"[.!?]$", w[0]) and len(re.sub(r"\W", "", w[0])) > 3))} for w in g]})
    return out


# ---------------------------------------------------------------- the director: a scene a sentence, each prop on its word
def shot_at(sp, i):
    """When sentence i's shot begins: a quarter second before it is said, but never before the sentence before has ended."""
    return round(max(sp[i][0] - .25, sp[i - 1][1] + .03), 3) if i else 0


def spans_of(segs):
    sp = {}
    for i, a, b, _ in segs: sp[i] = (min(sp.get(i, (a, b))[0], a), max(sp.get(i, (a, b))[1], b))
    return sp


def direct(spec, segs, wt, T):
    """A shot a sentence. Its first subject stands there as the camera arrives; the second and the words come on their word."""
    S = spec["sentences"]; sp = spans_of(segs); norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    scenes = []
    for i, s in enumerate(S):
        t0 = shot_at(sp, i); t1 = shot_at(sp, i + 1) if i + 1 < len(S) else T
        mine = [w for w in wt if w[3] == i]; items = []; first = True
        for k, it in enumerate((s.get("scene") or {}).get("items") or []):
            on = [w[1] for w in mine if it.get("on") and norm(w[0]) == norm(it["on"])]
            sub = it.get("kind") in KINDS          # (a second subject is in within 0.7 s: half the frame is not left empty; words land on their word, with time left to be read)
            at = min(on[0] - .1 if on else 9e9, sp[i][0] + (.7 if sub else 9e9 if on else .6), t1 - 1.5)
            t = round(max(t0 + .3, at), 3)
            if it.get("kind") in KINDS and first: t, first = round(t0 - 1, 3), False
            if it.get("kind") == "title" and not i: t = -1.0          # (the promise is on the very first frame)
            items.append(dict(it, t=t, seed=i * 7 + k))
        scenes.append({"t0": t0, "t1": t1, "bg": s["scene"]["bg"], "label": s["scene"].get("label"), "items": items, "mood": mood({"items": items})})
    return scenes


def fake_times(spec):
    """Timings without a voice (the preview): TALK words a second and the pauses. -> (segs, word times, T)."""
    t, segs, wt = 0.0, [], []
    for p in phrases(spec):
        w = p["text"].split(); d = len(w) / TALK; segs.append((p["i"], t, t + d, p["text"]))
        wt += [[x, t + d * k / len(w), t + d * (k + 1) / len(w), p["i"]] for k, x in enumerate(w)]; t += d + p["gap"]
    return segs, wt, t + 1.0


def timeline(spec, story, segs, wt, T):
    """What story3d.js draws from. The header reads whose chart this is ("TODAY'S MYSTERY CHART") and, from the moment the
    company is first said, its name."""
    cast = {c["id"]: {k: c.get(k) for k in ("look", "color", "tag")} for c in spec["cast"]}; name = spec["brands"][0]["name"]
    day = str(story.get("day") or "Today's").upper(); norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    said = [w[1] for w in wt if norm(name) and norm(w[0]).startswith(norm(name))]
    st = story.get("stock", {}); lo = min(story.get("chart") or [0]); P = story.get("chart") or [0]
    choice = spec.get("choice") or {"a": f"Buy it at ${lo:.2f}", "b": "Stay away"}      # (the fifth model's ending: a choice to answer in the comments)
    return {"T": round(T, 3), "title": spec["title"], "tag": f"{day} MYSTERY CHART", "ticker": st.get("ticker"), "choice": choice,
            "where": f"Meme Street \u00B7 Daily #{story.get('number')}" if story.get("number") else "Meme Street", "when": f"{day} mystery chart", "tag2": f"{day} CHART: {name.upper()}", "reveal": round(said[0] - CAP_LEAD, 3) if said else 0,
            "brands": spec["brands"], "cast": cast, "scenes": direct(spec, segs, wt, T),
            "caps": captions(wt, spec, spans_of(segs)), "segs": segs, "words": wt, "prices": story.get("chart"),
            "dates": [story.get("stock", {}).get("start"), story.get("stock", {}).get("end")],
            "hud": spec.get("hud", True), "cover": spec.get("cover") or {"badge": f"Daily #{story.get('number')}" if story.get("number") else "The Daily", "lines": [spec["title"]]},
            **({"reveal": round(T + 99, 3)} if spec.get("mystery") else {}), **{k: spec[k] for k in ("where", "when") if spec.get(k)}}     # (a promo: the company stays a mystery, its own tag)


# ---------------------------------------------------------------- render and sound
async def page(p, R):
    b = await p.chromium.launch(args=GL); pg = await b.new_page(viewport={"width": 1080, "height": 1920}); pg.set_default_timeout(300000)
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    await pg.add_init_script(INIT(R)); await pg.goto("file:///" + os.path.join(HERE, PAGE).replace("\\", "/").lstrip("/")); await pg.evaluate("window.ready")
    return b, pg, errs


async def preview(R, d, times=None):
    """One still a shot (settled), or one a time asked for, a contact sheet, and what overlaps. For looking before a full run."""
    from playwright.async_api import async_playwright
    os.makedirs(d, exist_ok=True); json.dump(R, open(os.path.join(d, "timeline.json"), "w", encoding="utf-8")); bad = []
    async with async_playwright() as p:
        b, pg, errs = await page(p, R); names = []
        for k, t in enumerate(times or [s["t1"] - .3 for s in R["scenes"]]):
            ov = await pg.evaluate("t=>overlaps(t)", t); bad += [f"{t:.1f}s (still {k}): {o}" for o in ov]
            if times: await pg.evaluate("t=>render(t)", t)
            names.append(f"s{k:02d}.jpg"); await pg.screenshot(path=os.path.join(d, names[-1]), type="jpeg", quality=85)
        say("cameras (distance, x, y):", await pg.evaluate("window.__cams()"))
        sh = await b.new_page(viewport={"width": 7 * 274, "height": 490})
        open(os.path.join(d, "sheet.html"), "w").write("<body style='margin:0;background:#000;display:grid;grid-template-columns:repeat(7,270px);gap:4px'>" + "".join(f"<img src='{n}' width=270 height=480>" for n in names) + "</body>")
        await sh.goto("file:///" + os.path.abspath(os.path.join(d, "sheet.html")).replace(os.sep, "/").lstrip("/")); await sh.wait_for_timeout(500); await sh.screenshot(path=os.path.join(d, "sheet.jpg"), full_page=True, type="jpeg", quality=82); await b.close()
    for o in bad + ["render error: " + e for e in errs[:5]]: say(o)
    say(f"{len(names)} stills and sheet.jpg in {d}; {len(bad)} overlaps, {len(errs)} render errors")


async def frames(R, fdir, cover, part=0, parts=1):
    from playwright.async_api import async_playwright
    os.makedirs(fdir, exist_ok=True); n = int(round(R["T"] * FPS))
    async with async_playwright() as p:
        b, pg, errs = await page(p, R)
        for i in range(n * part // parts, n * (part + 1) // parts):
            await pg.evaluate("t=>render(t)", i / FPS)
            await pg.screenshot(path=f"{fdir}/f{i:05d}.jpg", type="jpeg", quality=92)
            if i % 300 == 0: say(f"frame {i}/{n}")
        if part == 0:        # the cover: the hook's own frame, settled (the product and the promise)
            await pg.evaluate("t=>{window.__coverOn=1;render(t);window.__coverOn=0}", (R.get("cover") or {}).get("t") or min(R["scenes"][0]["t1"] - .2, 2.5)); await pg.screenshot(path=cover, type="jpeg", quality=92)
        await b.close()
        if errs: raise SystemExit("render errors: " + "; ".join(errs[:3]))
    return n


async def overlaps(R):
    """Every shot, settled (all its subjects in), and every caption: any two drawn boxes that touch. -> ["t: a x b"]."""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b, pg, errs = await page(p, R)
        ts = sorted({round(s["t1"] - .3, 2) for s in R["scenes"]} | {round(c["t1"] - .05, 2) for c in R["caps"]})
        out = []
        for t in ts:
            for o in await pg.evaluate("t=>overlaps(t)", t): out.append(f"{t}s: {o}")
        await b.close()
    return out + ["render error: " + e for e in errs[:3]]


def track(title):
    """The reel's music: a track of the library by the reel's title (EXPLAINER_TRACK picks one by its title), or None.
    -> {"file", "title", "artist", "license", "source"}"""
    import zlib
    try: have = [t for t in json.load(open(os.path.join(MUSIC_DIR, "tracks.json"), encoding="utf-8")) if os.path.exists(os.path.join(MUSIC_DIR, t["file"]))]
    except (OSError, ValueError): return None
    pick = [t for t in have if t["title"] == os.environ.get("EXPLAINER_TRACK")]
    return pick[0] if pick else have[zlib.crc32(title.encode()) % len(have)] if have else None


def mood(sc):
    """A shot's mood for the music: -1 a blow (a fall, a red stamp, bad news, a sad or shocked figure), +1 a win, else 0."""
    K = sc["items"]
    if any((it["kind"] == "arrow" and it.get("dir") == "down") or it["kind"] in ("stamp", "news") or it.get("pose") in ("sad", "shock") for it in K): return -1
    if any(it["kind"] in ("rocket", "trophy", "money", "counter") or (it["kind"] == "arrow" and it.get("dir") != "down") or it.get("pose") == "cheer" for it in K): return 1
    return 0


def sound(R, wav, work):
    """The voice over the reel's own tune and a few soft effects, at -14.5 LUFS. The music's level is SET, not guessed:
    sounds.tune() follows the shots' moods and is scaled until it sits MUSIC_DB under the voice (its loud half against the
    voice's), then ducked a little more while the voice speaks; each effect's peak sits FX_DB under the voice's. The loudness
    is reached with ONE gain for the whole reel (measured first), and a limiter only for stray peaks: a one-pass normaliser
    rides the level up and down under speech, which is heard as pumping."""
    import numpy as np, soundfile as sf, sounds as SD
    T = R["T"]; v, vsr = sf.read(wav); v = v if v.ndim == 1 else v.mean(1)
    lv, pk = loud(v, vsr), float(np.percentile(np.abs(v), 99.9))
    tr = track(R.get("title", "")); f = os.path.join(MUSIC_DIR, tr["file"]) if tr else None
    if f and os.path.exists(f):                # a composed track: from where it is in full swing (its quiet intro skipped), looped if short, faded out at the end
        raw = np.frombuffer(subprocess.run([FFMPEG, "-v", "error", "-i", f, "-ac", "2", "-ar", str(SD.SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32).reshape(-1, 2)
        b = int(SD.SR); lv_ = np.sqrt((raw[: len(raw) // b * b].mean(1).reshape(-1, b) ** 2).mean(1)); go = int(np.argmax(lv_ >= .8 * np.median(lv_))); raw = raw[go * b:]
        n = int(T * SD.SR); m = np.concatenate([raw] * (n // len(raw) + 1))[:n].copy(); k = int(1.6 * SD.SR); m[-k:] *= np.linspace(1, 0, k)[:, None]; m[: int(.3 * SD.SR)] *= np.linspace(0, 1, int(.3 * SD.SR))[:, None]
    else: m = SD.tune(T, [(s["t0"], s["t1"], s.get("mood", 0)) for s in R["scenes"]], R.get("title", ""))
    m = m * (lv * 10 ** (MUSIC_DB / 20) / loud(m.mean(1), SD.SR))
    sf.write(os.path.join(work, "bed.wav"), m.astype(np.float32), SD.SR)
    hits = np.zeros((int(T * SD.SR) + SD.SR, 2), np.float32)
    def put(kind, t, x=None):
        x = np.asarray(getattr(SD, kind)() if x is None else x, np.float32); a = int(max(0, t) * SD.SR); x = x[: len(hits) - a]
        hits[a:a + len(x)] += (x * (pk * 10 ** (FX_DB[kind] / 20) / (np.abs(x).max() + 1e-9)))[:, None]
    for s in R["scenes"][1:]: put("whoosh", s["t0"] - .05, SD.whoosh(.3))
    for s in R["scenes"]:
        for k, it in enumerate(s["items"]):
            t = it["t"]; kd = it["kind"]
            if t < s["t0"]: continue                                   # (what stands there as the shot opens makes no sound)
            if kd in ("stamp", "title"): put("thud", t + .12)
            elif kd == "counter": put("rise", t); put("ding", t + min(1.1, max(.3, (s["t1"] - t) * .45)))
            elif kd == "arrow" and it.get("dir") == "down": put("boom", t + .05)
            elif kd in ("rocket", "trophy", "money") or kd == "arrow": put("ding", t + .1)
            else: put("pop", t)
    sf.write(os.path.join(work, "hits.wav"), hits[: int(T * SD.SR)], SD.SR)
    pre, out = os.path.join(work, "premix.wav"), os.path.join(work, "mix.m4a")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", wav, "-i", os.path.join(work, "bed.wav"), "-i", os.path.join(work, "hits.wav"), "-filter_complex",
                    f"[0:a]aformat=channel_layouts=stereo,apad=whole_dur={T},asplit=2[v][sc];[1:a][sc]sidechaincompress=threshold=0.02:ratio=2:attack=15:release=350[bd];"
                    f"[v][bd][2:a]amix=inputs=3:normalize=0,atrim=0:{T}[o]", "-map", "[o]", "-ar", "48000", "-ac", "2", pre], check=True)
    heard = re.findall(r"I:\s+(-?[\d.]+) LUFS", subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", pre, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr)
    gain = -14.5 - float(heard[-1]) if heard else 0.0
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", pre, "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false:attack=3:release=60",
                    "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "192k", out], check=True)
    os.remove(pre)
    return out


FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
def film(tl, work, mp4, cover):
    """A timeline's frames (WORKERS browsers, each its share) -> a silent mp4. -> the number of frames."""
    fdir = os.path.join(work, "frames"); shutil.rmtree(fdir, ignore_errors=True)
    procs = [subprocess.Popen([sys.executable, __file__, "frames", tl, fdir, cover, str(k), str(WORKERS)]) for k in range(WORKERS)]
    if any(q.wait() for q in procs): raise SystemExit("not made: a frame worker failed")
    n = len(os.listdir(fdir))
    subprocess.run([FFMPEG, "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{fdir}/f%05d.jpg", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart", mp4], check=True)
    shutil.rmtree(fdir, ignore_errors=True); return n


def mux(R, wav, work, silent, out):
    os.makedirs(out, exist_ok=True); a = sound(R, wav, work); mp4 = os.path.join(out, "reel.mp4")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", silent, "-i", a, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy",
                    "-movflags", "+faststart", "-t", str(R["T"]), mp4], check=True)
    return mp4


def render(R, wav, work, out):
    os.makedirs(out, exist_ok=True); silent = os.path.join(work, "silent.mp4")
    n = film(os.path.join(work, "timeline.json"), work, silent, os.path.join(out, "cover.jpg")); mp4 = mux(R, wav, work, silent, out)
    say(f"rendered {mp4} ({n} frames, {R['T']:.1f}s)")
    return mp4


def caption_text(spec, story):
    script = " ".join(str(s["say"]) for s in spec["sentences"]); st = story.get("stock", {})
    if spec.get("caption"):         # (a promo writes its own: it never names the day's stock before the answer reel)
        t = track(spec["title"]); return (f"{spec['caption']}\n\n" + ((t.get("credit") or "") + "\n" if t else "") + f"{DISCLAIMER}\n" + spec.get("tags", "#stocks #trading #stockmarket #daytrading #MemeStreet"))
    src = sorted({o for f in story.get("research", {}).get("facts", []) for o in (f.get("by") or [])})[:5]
    return (f"{spec['title']}\n\n{script}\n\n{story.get('day') or 'Today' + chr(39) + 's'} mystery chart was {st.get('name')} ({st.get('ticker')}), {st.get('start')} to {st.get('end')}. "
            f"A new one goes live every midnight UTC: memestreet.net\n" + ("Sources: " + ", ".join(src) + "\n" if src else "") +
            ((track(spec["title"]).get("credit") or "Music: \"{title}\" by {artist} ({source}), {license}".format(**track(spec["title"]))) + "\n" if track(spec["title"]) else "") +
            f"{DISCLAIMER}\n#stocks #investing #stockmarket #{re.sub(r'[^A-Za-z0-9]', '', str(st.get('ticker', '')))} #MemeStreet")


# ---------------------------------------------------------------- the whole reel
def cut(spec, work, story):
    """Voice and direct a script -> the timeline for story3d.js; fails on any overlap."""
    wav, segs, W, T = voice(spec, work, story); R = timeline(spec, story, segs, align(estimate(segs), W), T)
    json.dump(R, open(os.path.join(work, "timeline.json"), "w", encoding="utf-8"))
    ov = json.loads(subprocess.run([sys.executable, __file__, "overlaps", os.path.join(work, "timeline.json")], check=True, capture_output=True, text=True).stdout)
    if ov: raise SystemExit("not made: things overlap: " + "; ".join(ov[:8]))
    return R, wav


ROUNDS = int(os.environ.get("EXPLAINER_ROUNDS", "4"))
PASS = int(os.environ.get("EXPLAINER_PASS", "9"))     # (the owner's bar, 2026-11-22: 9 of the 13 simulated viewers stay to the end)
def build(story, work, out, recent=(), spec=None, panel=True):
    """Write, voice, direct; the panel sees each round's preview, the writer rewrites until PASS of 13 stay (at most ROUNDS;
    the best round is filmed); render; the panel sees the real cut. -> (spec, R, mp4, the last verdict)."""
    shutil.rmtree(work, ignore_errors=True); os.makedirs(work, exist_ok=True); verdict, crit, best = None, None, None
    final = TTS; globals()["TTS"] = "kokoro"       # (drafts are read by the free voice; ElevenLabs reads only the cut that is filmed: its characters are counted)
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
    if panel and best and best[1]["stayed"] > verdict["stayed"]:
        spec, verdict = best; json.dump(spec, open(os.path.join(work, "spec.json"), "w", encoding="utf-8"), indent=1)
        say(f"filming the best round: {verdict['stayed']} of {verdict['of']}")
    globals()["TTS"] = final
    if final != "kokoro": R, wav = cut(spec, work, story)        # (the filmed cut in the real voice; its own timings)
    mp4 = render(R, wav, work, out)
    open(os.path.join(out, "caption.txt"), "w", encoding="utf-8").write(caption_text(spec, story))
    if panel and verdict and verdict["ok"]:
        verdict = gate(R, spec, work, os.path.join(work, "panel_final"), mp4)
        say(f"panel on the real cut: {verdict['stayed']} of {verdict['of']} stayed to the end")
    return spec, R, mp4, verdict


def state():
    return json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"used": []}


def month_table(P, start, end):
    """The real price at each month of the window and its chart point (0..1)."""
    import datetime
    a, b = datetime.date.fromisoformat(start), datetime.date.fromisoformat(end); n = len(P) - 1; out, seen = [], set()
    for i, p in enumerate(P):
        d = a + (b - a) * (i / n); key = d.strftime("%b %Y")
        if key not in seen: seen.add(key); out.append({"month": key, "chart_point": round(i / n, 2), "price": f"${p:.2f}"})
    return out


def day_word(date):
    """How a reel names the day of its chart: "Today's" on the day itself (the 23:30 reel), "Yesterday's" the day after, then
    the weekday ("Sunday's"): a reel made or posted late never calls an old chart today's."""
    import datetime
    try: d = datetime.date.fromisoformat(str(date)[:10])
    except ValueError: return "Today's"
    n = (datetime.datetime.now(datetime.timezone.utc).date() - d).days
    return "Today's" if n <= 0 else "Yesterday's" if n == 1 else d.strftime("%A") + "'s"


def day_story(date, data):
    """The day's Daily -> what the writer may use: the stock and its window, the real prices, the researched story."""
    import news_reel as N, datetime
    d = json.load(open(data, encoding="utf-8")); g = d["game"]; rv = g.get("real")
    if not rv: raise SystemExit(f"not made: the Daily of {date} was a model chart, not a real stock")
    H = g.get("history", 60); P = [round(c[3] * rv["k"], 2) for c in g["candles"][H - 1:]]
    hi, lo = max(range(len(P)), key=P.__getitem__), min(range(len(P)), key=P.__getitem__)
    cache = data.replace(".json", ".research.json")
    if os.path.exists(cache): pack = json.load(open(cache, encoding="utf-8"))
    else:
        pack = N.research(f"{rv['name']} ({rv['ticker']}) shares between {rv['start']} and {rv['end']}: what the company does and makes and how "
                          f"it makes it; where its shares stood at the start; every event in that window that moved the price, with its date; why "
                          f"it moved, each cause with its source; the key players (executives, rivals, big investors, short sellers, retail "
                          f"traders); how the window ended. The share price went from about ${P[0]:.2f} to ${P[-1]:.2f}.")
        errs = N.sound(pack)
        if errs: raise SystemExit("not made: the research is not sound: " + "; ".join(errs))
        json.dump(pack, open(cache, "w", encoding="utf-8"), indent=1)
    pack = dict(pack, facts=[f for f in pack.get("facts", []) if f.get("status") != "alleged"])
    a, b = datetime.date.fromisoformat(rv["start"]), datetime.date.fromisoformat(rv["end"])
    when = lambda i: (a + (b - a) * (i / (len(P) - 1))).strftime("%b %Y")
    return {"number": d.get("number"), "day": os.environ.get("EXPLAINER_DAY") or day_word(date if re.match(r"\d{4}-\d\d-\d\d", str(date)) else os.path.basename(data)),
            "stock": {"ticker": rv["ticker"], "name": rv["name"], "start": rv["start"], "end": rv["end"], "events_in_window": rv.get("events", [])},
            "window": {"first_price": f"${P[0]:.2f}", "last_price": f"${P[-1]:.2f}", "change_pct": f"{(P[-1] / P[0] - 1) * 100:.0f}%",
                       "high": {"price": f"${P[hi]:.2f}", "when": when(hi), "chart_point": round(hi / (len(P) - 1), 2)},
                       "low": {"price": f"${P[lo]:.2f}", "when": when(lo), "chart_point": round(lo / (len(P) - 1), 2)},
                       "note": "prices are the real daily closes the Daily showed; the chart point says where in the window a moment falls"},
            "prices": month_table(P, rv["start"], rv["end"]), "research": {k: pack.get(k) for k in ("headline", "people", "company", "facts", "numbers", "market", "not_known")},
            "chart": P, "sources": pack.get("sources", [])}


def daily(date, where=None):
    """The day's reel: queued for <date>T2330 (or, with `where`, made there and not queued). -> the slot or the folder, or None."""
    import news_reel as N
    sl = f"{date}T2330"; q = os.path.join(ROOT, "queue", sl)
    if not where and (os.path.exists(os.path.join(q, ".auto")) or os.path.exists(os.path.join(q, "posted.json"))): say(sl, "already has its reel"); return sl
    tries = os.path.join(ROOT, "state", f"explainer-{date}.tries"); n = int(open(tries).read()) if os.path.exists(tries) else 0
    if not where and n >= 3: say(f"{date}: tried three times, not made"); return None
    os.makedirs(os.path.dirname(tries), exist_ok=True); open(tries, "w").write(str(n + 1))
    data = os.path.join(ROOT, "data", f"{date}.json")
    if not os.path.exists(data): subprocess.run([sys.executable, os.path.join(SRC, "fetch.py"), data], cwd=ROOT, check=True)
    story = day_story(date, data); st = state()
    base = where or ROOT; work, out = os.path.join(base, "work", "daily-" + date), os.path.join(base, "out", "daily-" + date)
    shutil.rmtree(out, ignore_errors=True)
    spec, R, mp4, g = build(story, work, out, [u.get("title") for u in st["used"]], panel=os.environ.get("PANEL", "1") == "1")
    if where: return out
    if not (g and g["ok"]): say("not queued: too few simulated viewers stayed to the end:", (g or {}).get("why", "")); return None
    json.dump({"by": "explainer", "audience": g}, open(os.path.join(out, "approved.json"), "w"))
    st["used"].append({"date": date, "ticker": story["stock"]["ticker"], "title": spec["title"]}); json.dump(st, open(STATE, "w", encoding="utf-8"), indent=1)
    return N.queue_out(out, sl, spec["title"])


def gate(R, spec, work, d, mp4=None):
    """The 13-persona panel (lab/audience.py) sees what the feed serves: the first 3 seconds frame by frame and the whole reel
    every 1.5 s, with what is said and shown when."""
    import importlib.util
    lab = os.path.join(ROOT, "lab", "audience.py")
    if not os.path.exists(lab): return {"ok": False, "why": "lab/audience.py is missing", "stayed": 0, "of": 0}
    sp = importlib.util.spec_from_file_location("audience", lab); A = importlib.util.module_from_spec(sp); sp.loader.exec_module(A)
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d, exist_ok=True); T = R["T"]
    if mp4: A.frames(mp4, d, T)
    else: subprocess.run([sys.executable, __file__, "stills", os.path.join(work, "timeline.json"), d, json.dumps(A.HOOK_T)], check=True)
    S = spec["sentences"]; spans = spans_of(R["segs"])
    feed = {"length_secs": round(T, 1), "format": "a true stock story told by a male narrator over low-poly 3D animation: every sentence a new shot in its own 3D set (the factory making the product, the store, a beach, a trading floor...), its one or two subjects filling the frame, the camera pushing in and flying from set to set, a headline that stays, the date, big words on a figure, the real price chart",
            "title": spec["title"], "pill_on_screen_all_reel": R.get("tag"), "post_caption_first_line": spec["title"],
            "audio": "a male voice-over from the first frame over a light, quiet tune (piano, mallets, a soft pulse) that drops out on bad news, a soft whoosh on each scene change",
            "words_in_first_3s": [(w[0], round(w[1], 2)) for w in R["words"] if w[1] < 3],
            "timeline": [{"from": round(spans[i][0], 1), "to": round(spans[i][1], 1), "said": s["say"],
                          "on_screen": {"set": s["scene"]["bg"], "date": s["scene"].get("label"), "subjects_and_words": [{k: v for k, v in it.items() if k != "on"} for it in s["scene"]["items"]],
                                        "captions": "the words as said, a clause at a time, big white outlined letters, the company in its colour, figures in gold"}} for i, s in enumerate(S)],
            "images": A.IMAGES}
    json.dump(feed, open(os.path.join(d, "feed.json"), "w"), indent=1)
    res = None; err = ""
    for k in range(2):
        try: res = A.watch(d); break
        except (SystemExit, Exception) as e: err = str(e)[:300]; say("the panel failed, trying again:", err)
    if res is None: return {"ok": False, "why": "the panel failed twice: " + err, "stayed": 0, "of": 0}
    P = res.get("personas") or []
    left = [p for p in P if p.get("leaves_at") not in (None, "null") and float(p["leaves_at"]) < T - 1.5]
    return {"ok": bool(P) and len(P) - len(left) >= PASS, "stayed": len(P) - len(left), "of": len(P), "predicted": res.get("predicted"),
            "why": "; ".join(f"{p.get('id')} leaves at {p.get('leaves_at')}s: {str(p.get('why') or p.get('reason') or '')[:160]}" for p in left)[:1500]}


async def stills(R, d, hook_t):
    """The panel's two images drawn straight from the timeline: first_3s.jpg and whole_reel.jpg."""
    from playwright.async_api import async_playwright
    tmp = os.path.join(d, "_s"); os.makedirs(tmp, exist_ok=True)
    async with async_playwright() as p:
        b, pg, errs = await page(p, R)
        ts = [("h", k, t) for k, t in enumerate(hook_t)] + [("w", k, k * 1.5) for k in range(int(R["T"] / 1.5) + 1)]
        for kind, k, t in ts:
            await pg.evaluate("t=>render(t)", min(t, R["T"] - .05)); await pg.screenshot(path=os.path.join(tmp, f"{kind}{k:03d}.jpg"), type="jpeg", quality=85)
        await b.close()
    ff = lambda *a: subprocess.run([FFMPEG, "-v", "error", "-y", *a], check=True)
    hs = sorted(f for f in os.listdir(tmp) if f.startswith("h"))
    ff(*sum([["-i", os.path.join(tmp, f)] for f in hs], []), "-filter_complex",
       "".join(f"[{i}]scale=360:-1[s{i}];" for i in range(len(hs))) + "".join(f"[s{i}]" for i in range(len(hs))) + f"hstack={len(hs)}", os.path.join(d, "first_3s.jpg"))
    n = int(R["T"] / 1.5) + 1
    ff("-framerate", "1", "-i", os.path.join(tmp, "w%03d.jpg"), "-vf", f"scale=180:-1,tile=8x{math.ceil(n / 8)}", "-frames:v", "1", os.path.join(d, "whole_reel.jpg"))
    shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- self-check
DEMO_STORY = {"day": "Today's", "stock": {"ticker": "GPRO", "name": "GoPro", "start": "2020-08-24", "end": "2021-02-12"},
              "window": {"first_price": "$4.80", "last_price": "$8.04", "high": {"price": "$13.89"}},
              "research": {"people": [{"name": "Nick Woodman", "role": "founder and CEO"}], "facts": [{"claim": "HERO9 launched in September 2020; GoPro.com sales grew", "status": "confirmed", "by": ["GoPro"]}]}}


def demo():
    global CAP_WORDS, CAP_MIN; keep = (CAP_WORDS, CAP_MIN); CAP_WORDS, CAP_MIN = 3, .5      # (the caption checks below were written for these)
    js = open(os.path.join(HERE, "story3d.js"), encoding="utf-8").read(); flat = open(os.path.join(HERE, "story.js"), encoding="utf-8").read()
    for k in KINDS: assert re.search(rf"\n  (async )?{k}\(it\) ", js), k                # (the writer's lists and the renderer's agree)
    for k in BGS: assert re.search(rf"\n  (async )?{k}\(g\) ", js), k
    for k in FLAT: assert re.search(rf"\n  {k}: \[", flat), k
    assert spoken("GoPro sold 2 HERO9 cameras on GoPro.com for $60,000, 4% more.", DEMO_STORY) == "Goh Proh sold 2 Hero 9 cameras on Goh Proh dot com for 60,000 dollars, 4 percent more."
    assert spoken("It sat at $4.80, then $10 and $1.5 billion.") == "It sat at 4 dollars 80, then 10 dollars and 1.5 billion dollars.", spoken("It sat at $4.80, then $10 and $1.5 billion.")
    assert spoken("GPRO fell. McDonald stayed at 70%.", DEMO_STORY) == "Goh Proh fell. McDonald stayed at 70 percent.", spoken("GPRO fell. McDonald stayed at 70%.", DEMO_STORY)
    S = [{"say": "For five months GoPro fought to stay alive.", "scene": {"bg": "night", "label": "AUG 2020", "items": [
            {"kind": "building", "brand": "GoPro", "text": "GoPro"}, {"kind": "person", "who": "ceo", "pose": "sad"}, {"kind": "chart", "from": 0, "to": .3}]}}]
    spec = {"title": "x", "brands": [{"name": "GoPro", "color": "#1aa3e8"}], "cast": [{"id": "ceo", "tag": "NICK WOODMAN, CEO", "look": "suit", "color": "#1aa3e8"}], "sentences": S}
    E = errors(spec, DEMO_STORY)
    assert any("3 subjects" in e for e in E) and any("sentences" in e for e in E) and any("first sentence begins" in e for e in E) and any("mystery chart with" in e for e in E) and any("word for word" in e for e in E), E
    S[0]["scene"]["items"] = [{"kind": "chart", "from": 0, "to": .9, "title": "???"}, {"kind": "title", "text": "DOUBLED IN A PANDEMIC"}, {"kind": "stamp", "text": "X"}]
    S[0]["say"] = "Today's mystery chart on Meme Street, GPRO, went from $4.80 to $99, The Fool reported."; E = errors(spec, DEMO_STORY)
    assert any("ticker" in e for e in E) and any("99" in e for e in E) and any("one line of words" in e for e in E) and any("no 'X reported'" in e for e in E), E
    assert not any("a shot has" in e or "first sentence begins" in e or "mystery chart with" in e or "carries a title" in e or "names are not" in e for e in E), E
    assert any("never names the company" in e for e in errors(dict(spec, sentences=[dict(S[0], say="Today's mystery chart on Meme Street was GoPro at $4.80.")]), DEMO_STORY))
    assert day_word("2000-01-03") == "Monday's" and day_word("x") == "Today's" and opening({"day": "Yesterday's"}) == "Yesterday's mystery chart on Meme Street"
    segs = [(0, 0.0, 2.0, "For five months GoPro"), (0, 2.1, 3.0, "fought on."), (1, 3.4, 5.0, "Then it rose.")]
    wt = [["For", 0, .3, 0], ["five", .3, .6, 0], ["months", .6, 1, 0], ["GoPro", 1, 2, 0], ["fought", 2.1, 2.5, 0], ["on.", 2.5, 3, 0], ["Then", 3.4, 3.8, 1], ["$4.80", 3.8, 4.4, 1], ["rose.", 4.4, 5, 1]]
    sp2 = {"brands": [{"name": "GoPro", "color": "#1aa3e8"}], "sentences": [{"say": "", "scene": {"bg": "night", "items": [{"kind": "badge"}, {"kind": "bulb", "on": "GoPro"}, {"kind": "title", "text": "A"}]}},
                                                                          {"say": "", "scene": {"bg": "city", "items": [{"kind": "arrow"}, {"kind": "counter", "to": 4.8, "on": "$4.80"}]}}]}
    D = direct(sp2, segs, wt, 6.0); assert D[0]["t0"] == 0 and D[0]["t1"] == D[1]["t0"] == 3.15 and D[1]["t1"] == 6.0, D
    assert [it["t"] for it in D[0]["items"]] == [-1, .7, -1] and [it["t"] for it in D[1]["items"]] == [2.15, 3.7], D      # (the first subject is there as the shot opens)
    assert captions(wt, sp2, spans_of(segs))[1]["t1"] == 3.15 and captions(wt, sp2)[1]["t1"] == 3.34          # (the last caption of a sentence ends at the cut)
    C = captions(wt, sp2); assert [len(c["words"]) for c in C] == [3, 3, 3] and C[1]["words"][0]["color"] == "#1aa3e8" and C[-1]["words"][1]["color"] == GOLD and C[1]["t0"] == .94, C     # (six words: three and three, never five and one; each shown 0.06 s early)
    heard = [("for", .05, .3), ("five", .3, .6), ("months", .6, 1), ("gopro", 1.1, 1.7), ("fought", 2.15, 2.5), ("on", 2.5, 2.8), ("then", 3.45, 3.7), ("4", 3.9, 4.1), ("80", 4.1, 4.4), ("rose", 4.5, 4.9)]
    AL = align(estimate([(0, 0.0, 2.0, "For five months GoPro"), (0, 2.1, 3.0, "fought on."), (1, 3.4, 5.0, "Then $4.80 rose.")]), heard)
    assert AL[3][1] == 1.1 and AL[7][:3] == ["$4.80", 3.9, 4.4] and AL[4][1] == 2.12 and all(a[1] < b[1] for a, b in zip(AL, AL[1:])), AL      # ('$4.80' heard as '4' '80' still gets its own time)
    assert .8 < align(estimate([(0, 0.0, 2.0, "One two three four")]), [])[2][1] < 1 and mood({"items": [{"kind": "arrow", "dir": "down"}]}) == -1 and mood({"items": [{"kind": "counter"}]}) == 1 and mood({"items": [{"kind": "product"}]}) == 0
    import numpy as np
    assert breaths([100] * 6, [False] * 6) == [[0, 1, 2], [3, 4, 5]] and breaths([100] * 6, [0, 0, 0, 1, 0, 0]) == [[0, 1, 2, 3], [4, 5]] and breaths([90, 90], [0, 0]) == [[0, 1]]
    sr = 8000; tone = lambda d: (np.sin(np.arange(int(d * sr)) * .9) * .5).astype(np.float32); hush = lambda d: np.zeros(int(d * sr), np.float32)
    a = np.concatenate([tone(1), hush(.5), tone(1), hush(.4), tone(1), hush(.15)])          # "One." 0.5 s "two," 0.4 s "three." and the clip's tail
    b, spans, rests, f = flow(a, sr, [["One.", 0, 1.0], ["two,", 1.5, 2.5], ["three.", 2.9, 3.9]], [0, 1, 1])
    assert quiet(a, sr) == [[1.0, .5], [2.5, .4], [3.9, .15]] and abs(len(b) / sr - (3.0 + rests[0][1] + rests[1][1] + .15)) < .02 and spans[0] == (0.0, 1.0) and .16 <= rests[0][1] <= .3 and .08 <= rests[1][1] <= .2, (quiet(a, sr), len(b) / sr, spans, rests, f(3.0))
    assert abs(loud(tone(1), sr) - .354) < .01 and shot_at({0: (0, 3.0), 1: (3.1, 5)}, 1) == 3.03 and shot_at({0: (0, 3.0), 1: (3.4, 5)}, 1) == 3.15
    seven = [[f"w{k}", k * .3, k * .3 + .25, 0] for k in range(7)]; assert [len(c["words"]) for c in captions(seven, sp2)] == [3, 2, 2]
    quick = [["a", 0, .1, 0], ["b", .12, .2, 0], ["c", .22, .3, 0], ["d", .35, .9, 0], ["e", 1, 1.5, 0]]; assert [len(c["words"]) for c in captions(quick, sp2)] == [5]     # (three words in 0.35 s join the next two)
    sg, w2, T2 = fake_times({"sentences": [{"say": "One two three, four."}, {"say": "Five six."}]}); assert len(w2) == 6 and sg[1][1] > sg[0][2] and T2 > w2[-1][2], (sg, T2)
    assert not any("names" in e for e in errors(dict(spec, sentences=[{"say": "Founder Nick Woodman smiled.", "scene": {}}]), DEMO_STORY))
    assert any("Jane Porter" in e for e in errors(dict(spec, sentences=[{"say": "Then Jane Porter smiled.", "scene": {}}]), DEMO_STORY))
    CAP_WORDS, CAP_MIN = keep
    assert .3 <= rest("The stock sank.", "But", 6) <= .5 and rest("It rose.", "It", 4) < .32 and rest("x.", "A", 4, True) >= .55 and .08 <= rest("one, two", "and", 3, comma=True) <= .22
    c = caption_text({"title": "T", "sentences": [{"say": "a"}]}, DEMO_STORY); assert "memestreet.net" in c and DISCLAIMER in c and "#GPRO" in c
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:] or ["demo"]
    if a[0] == "demo": demo()
    elif a[0] == "daily": sys.exit(0 if daily(a[1] if len(a) > 1 else time.strftime("%Y-%m-%d", time.gmtime())) else 1)
    elif a[0] == "dailytry": print(daily(a[1], a[2]))
    elif a[0] == "frames": asyncio.run(frames(json.load(open(a[1], encoding="utf-8")), a[2], a[3], *(int(x) for x in a[4:6])))
    elif a[0] == "overlaps": print(json.dumps(asyncio.run(overlaps(json.load(open(a[1], encoding="utf-8"))))))
    elif a[0] == "stills": asyncio.run(stills(json.load(open(a[1], encoding="utf-8")), a[2], json.loads(a[3])))
    elif a[0] in ("spec", "preview", "cut"):
        sp = json.load(open(a[1], encoding="utf-8")); st = day_story("x", os.environ["DAILY_DATA"]) if os.environ.get("DAILY_DATA") else DEMO_STORY
        E = errors(sp, st)
        if E: say("the format's faults:", "; ".join(E))
        if a[0] == "preview": asyncio.run(preview(timeline(sp, st, *fake_times(sp)), a[2], json.loads(a[3]) if len(a) > 3 else None))
        elif a[0] == "cut":
            work, out = os.path.join(a[2], "work"), os.path.join(a[2], "out"); os.makedirs(work, exist_ok=True); os.makedirs(out, exist_ok=True)
            json.dump(sp, open(os.path.join(work, "spec.json"), "w", encoding="utf-8"), indent=1); cut(sp, work, st)
            open(os.path.join(out, "caption.txt"), "w", encoding="utf-8").write(caption_text(sp, st)); print(os.path.join(work, "timeline.json"))
        else: build(st, os.path.join(a[2], "work"), os.path.join(a[2], "out"), spec=sp, panel=os.environ.get("PANEL") == "1")
    elif a[0] == "phonemes":          # each phrase of a script as the voice's phonemes
        from kokoro_onnx import Kokoro
        from voice import MODEL
        K = Kokoro(os.path.join(MODEL, "kokoro-v1.0.onnx"), os.path.join(MODEL, "voices-v1.0.bin")); st = day_story("x", os.environ["DAILY_DATA"]) if os.environ.get("DAILY_DATA") else DEMO_STORY
        for ph in phrases(json.load(open(a[1], encoding="utf-8"))): print(spoken(ph["text"], st), "->", K.tokenizer.phonemize(spoken(ph["text"], st), "en-us"))
    elif a[0] == "film": os.makedirs(a[2], exist_ok=True); print(film(a[1], a[2], os.path.join(a[2], "silent.mp4"), os.path.join(a[2], "cover.jpg")), "frames")
    elif a[0] == "mux":
        work = os.path.join(a[1], "work"); print(mux(json.load(open(os.path.join(work, "timeline.json"), encoding="utf-8")), os.path.join(work, "voice.wav"), work, a[2], os.path.join(a[1], "out")))
