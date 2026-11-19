"""A story reel in parts, made on the owner's word (2026-11-14: "one of those roblox story reels ... a 2-3 part story ... a MAJOR
cliff hanger at the end", then "create the story yourself part 2, 3, 4, etc... post them one a day"): blocky game characters
tell a short first-person story about trading, link it to Meme Street, and end on a cliffhanger that the next part picks up.

  python3 src/story_reel.py next                   the day's part of the serial in src/stories.json, made and queued if one is due
                                                   (auto_reel.sh runs it every time; it does nothing unless a part is due)
  python3 src/story_reel.py <story.json>           write, voice, render and review one part into out/story-<time>; nothing posts
  python3 src/story_reel.py <story.json> --post    the same, then queue it (the queue timer posts it within five minutes)
  ... --resume <work>/attempt-N.txt                 start from a failed draft: the writer fixes it instead of starting over

story.json: {"part": 2, "story": "the beats", "cliffhanger": "how this part ends", "lesson": "its one trading idea",
             "earlier_parts": ["..."], "cast": {...}, "last": false}
src/stories.json, the serial: {"cast": {...}, "parts": [{"part", "story", "cliffhanger", "lesson", "last"?, "posted"?}, ...]}.
One part a day from STORY_HOUR (10) UTC, two tries a day at most; state/story.json keeps what went out. When the parts run out,
nothing is made. The work folder is story-<time> and the reel is queued under the same time, so the ledger finds its script
(own_reels.folders); the rotation never picks the format.
"""
import datetime, glob, json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import make_spec as M
import world as W

CATEGORY = "Blocky story"
STORIES, STATE = os.path.join(HERE, "stories.json"), os.path.join(ROOT, "state", "story.json")
S0 = json.load(open(STORIES, encoding="utf-8"))
WHAT = ("A STORY REEL IN PARTS (the owner, 2026-11-14), made like the viral blocky-game story reels ('In this town, you only get "
        "1,000,000 steps': the owner's exemplar). Told in the first person by the narrator, an average trader. THE PREMISE, said in the "
        "first line over the first shot: in this town, everyone's money is printed on their chest, and it is set by their trades. THE "
        "LOOK (the owner, 2026-11-14: 'a proper 3D world, where the people are walking around'): a film shot in a real 3D toy-block "
        "town. The renderer builds the town and its people and films what your SHOTS say: for this format you write NO scene function "
        "and no svg, so send NO ```js block (ignore DIRECTOR REELS' scene function, HUD, punch and geometry rules; still send "
        "\"device\", the same in every part: the chest labels). Every scene but the outro carries \"shots\": 1 to 3 shots, a new one "
        "about every 2 seconds; the first runs from the scene's first word, each later one cuts in on its \"say\" (two or three "
        "words of the line, exactly as written; number words are fine: \"hit zero\"). facts.example is part 1 as it was filmed: copy its form. "
        "A SHOT: {\"say\"?, \"place\", \"cam\", \"move\"?, \"sky\"?, \"sky_say\"?, \"actors\": [...], \"crowd\"?, \"screen\"?, \"car\"?, "
        "\"plane\"?, \"door\"?, \"fx\"?}. "
        "PLACES: street (the pavement of the main street: houses, traffic and passers-by behind), home (the narrator's front garden, "
        "his door behind), doorway (from inside the narrator's hall, looking out through his front door: the visitor stands at "
        "[0, -1.7]; \"door\": \"burst\" throws it open on \"door_say\"), shop, bank, park (a bench at [0, -1]: someone there with "
        "do sit sits on it), square (the town square: a stage at [0, -7], the town's big screen above it), airport (the gold plane "
        "stands at [0, -8]), room (the narrator's room: the screen on its wall is his Meme Street screen; he stands at [2.2, -2.2] "
        "with do present; in a \"screen\" shot there everyone stands at x 1.9 or more, or a head covers the screen's words). "
        "POSITIONS are [x, z] in metres from the place's centre: x runs left (-) to right (+) as the camera sees it, z back (-) to "
        "front (+). A portrait frame is narrow: keep a shot's people within x -3 to 3, a metre or more apart. "
        "CAMERAS: \"close:Name\" (the face and the chest label fill the frame: the shot for a number that changes), \"mid:Name\" (the "
        "whole person, the crowd behind), \"low:Name\" (from the ground, looking up: the powerful, or someone watching the sky), "
        "\"two:A,B\", \"over:A>B\" (over A's shoulder at B), \"wide\" (everyone in the shot and the place round them), \"high\" (from "
        "above), \"screen\" (the room's or the square's screen across the frame, the people small under it), \"wide:plane\", "
        "\"wide:car\". \"move\": in (the default, a slow push), out, orbit, rise, still. "
        "SKY: day, gold (morning), sunset, night, red (the cliffhanger's dark red sky); it stays until a later shot changes it, and "
        "with \"sky_say\" it turns on those words. "
        "AN ACTOR: {\"who\", \"at\": [x, z], \"to\"?: [x, z] (walks there; \"do\": \"run\" runs), \"do\"?: a pose, \"face\"?: a mood, "
        "\"chest\"?: the number on the chest label (a number; [from, to] counts up or crashes as the shot opens; or a short word "
        "like \"#1\"), \"look\"?: a name, \"screen\" or [x, z], \"hold\"?: an item, \"emote\"?: a bubble by the head, and \"say\" with "
        "\"then\": on those words the actor changes to what \"then\" gives (do, face, chest, to, hold, emote, hide). A number that "
        "crashes on its word: {\"chest\": 12480, \"say\": \"crashed\", \"then\": {\"chest\": 0, \"do\": \"shock\"}}. \"who\" is a cast "
        "name, drawn exactly as facts.story.cast says (narrator, Timmy, Mr Gold, Maya, old neighbour, sheriff), or any other name "
        "for a townsperson with a look of their own. POSES: %(poses)s (shake is a handshake, not a shaken head; show holds the item up). FACES: %(faces)s. ITEMS for \"hold\": %(items)s. EMOTES: "
        "%(emotes)s. "
        "A CROWD: {\"n\": 2 to 14, \"form\": row | line (a queue) | cluster (round \"at\", behind it) | scatter, \"at\", \"do\", "
        "\"face\", \"chest\": rand (each their own number) | zero | x2 | x10 | half | neg (below zero, in red) | a number, \"say\", "
        "\"then\"}: with \"then\": {\"chest\": \"zero\"} their numbers crash one after another. "
        "THE SCREEN (in the room and the square; anywhere else as a chart in a hand, \"hold\": \"chart\"): \"screen\": {\"title\", "
        "\"chart\": %(charts)s, \"pct\"?: \"+900%%\", \"news\"?: a headline strip}, or {\"title\", \"lines\": up to 3 short lines} (a "
        "checklist that ticks itself), or {\"text\": \"LINE ONE|LINE TWO\", \"tone\": gold | red | green}. Only made-up company names. "
        "\"car\": {\"color\": %(cars)s, \"from\", \"to\", \"who\"?: its driver, an actor of the shot}. \"plane\": {\"mode\": parked | "
        "takeoff | land | fly | away (a dot high in the sky: film it with cam low on someone watching), \"at\"?}. \"fx\": [{\"do\": "
        "%(fx)s, \"say\"?}]. \"look\": \"photo\" turns a shot into an old photograph (a flashback). "
        "Passers-by, traffic and clouds are added by the renderer in every outdoor shot: you place only the people of the story. "
        "DIRECTING: every line is acted out where it happens, by the people it names, doing what it says, and a number changes on "
        "the very word that says so (with redflash and shake for a crash, coins or confetti for a win). Never two shots running "
        "with the same camera on the same person: a close shot when a number or a face matters, a wide or mid one when people "
        "move. Every named actor carries \"chest\" in every shot (the device), the same number as in the shot before unless the "
        "line changes it. People act: Timmy holding out his hands, the rich waving from a sports car, the narrator shrugging on a "
        "park bench. Never write the name of any real game. THE CAPTIONS are the renderer's: one big word at a time, low in the "
        "frame; give every free scene its 2 to 5 word \"text\" as usual (the renderer hides punch lines and the top hook in this "
        "format). The only words on screen are the chest numbers and what a screen shows. "
        "THE STORY: facts.story.story is this part's story: tell every beat of it, in that order, in the narrator's voice "
        "('I'm just an average trader'), tightened to fit the word limit, every line acted out by the avatars, funny and fast. "
        "A SERIAL: facts.story.earlier_parts is what the viewers have already seen (never retell it beyond the story's own first "
        "sentence, never contradict it), and facts.story.cast gives every returning character's colours and numbers: draw them exactly "
        "so, in the same town, palette and chest labels in every part (the device is the series' own: the same on purpose). "
        "facts.story.lesson is the one trading idea this part teaches: the story says it once, in plain words. The link to Meme "
        "Street is one line, where the story places it (only what facts.meme_street says: since 2026-11-18 Meme Street is a free daily "
        "game, one real stock chart a day, two minutes to trade it with practice money, the stock named at the end; no memebucks, "
        "no lessons any more); 'better' means a plan and practice, "
        "never a promise of money or of beating the market. Then facts.story.cliffhanger, as the last story line before the sign-off: "
        "a MAJOR cliffhanger, something shocking happens on screen (a number crashes, the door bursts open, the sky turns red: \"sky\": \"red\" with \"sky_say\") and "
        "the line breaks off unresolved. The sign-off scene names the next part: 'Part 3 drops soon. Join free at memestreet.net.' "
        "(part N+1). If facts.story.last is true this is the final part: facts.story.cliffhanger is the closing line, said whole, "
        "nothing left open, and the sign-off is 'Follow for the next story. Join free at memestreet.net.' "
        "Shape: scene 0 is the hook: a close shot of a character whose chest number races, crashes or flips inside the first second "
        "(in part 1 it races to 1,000,000), and the first spoken sentence carries the premise (your money is printed on your chest) "
        "and, in a later part, where the last one stopped, so a new viewer follows: the story's own first sentence. Every scene of "
        "kind \"free\" but the outro; short scenes, one or two lines each. \"type\" is \"Blocky story\". The post caption: line 1 is the hook with a question for the viewer (under "
        "125 characters); 'Part N' (add 'of M' only if facts.story.of is given); the story in two or three short lines that give "
        "away nothing of the ending; a line on Meme Street with 'practice money with no cash value'; 'Follow for part N+1.' unless "
        "it is the final part; 'Practise at memestreet.net'; "
        "'Practice money only. Not investment advice.' (word for word); 3 to 5 hashtags. The voice tells it like "
        "the exemplar's narrator, in flowing sentences of 10 to 20 words joined with and, so, but, because (the checker refuses "
        "an average under 10), while the pictures still cut every 2 seconds.") % {k: ", ".join(v) for k, v in W.VOC.items()}
M.CATEGORIES.setdefault(CATEGORY, WHAT)
# (the serial's own sound and look, the same in every part; the owner, 2026-11-14: "music like the roblox videos ... change the voice so it
#  matches too". Measured on the owner's exemplar 10-42-35: the narrator speaks 4.4 words a second with no pause over 0.3 s, at about
#  225 Hz; the house voice is 3.4 to 3.9 words a second at 205 Hz. So: Kokoro's bright af_bella, read quicker and played 9% higher,
#  its pauses cut to under half (measured on the server: 4.2 words a second at 225 to 230 Hz, every line still understood by the
#  speech check), over the bouncy tune of sounds.story_music; one word of caption at a time)
STYLE = {"one_word": True, "voice": "af_bella", "voice_speed": 1.3, "voice_pitch": 1.09, "voice_pauses": 0.45, "music": "story"}
M.LENGTH.setdefault(CATEGORY, (90, 140, True))        # (spoken words: the part's beats, the link and the cliffhanger; 60 s at most)


def brief(st, slot):
    hist = json.load(open(M.HISTORY)) if os.path.exists(M.HISTORY) else {}
    notes = os.path.join(ROOT, "exemplar", "NOTES.md")
    # (recent_devices stays empty: a serial keeps its own device, and the checker refuses one that is close to a recent reel's)
    facts = {"story": st, "meme_street": M.GAME_FACTS, "recent_devices": [], "video": {"available": False}, "hook_shots_used_lately": [],
             "example": W.example()}                       # (part 1 as it was filmed: every later part is shot the same way)
    ask = {"category": CATEGORY, "what_this_reel_is": WHAT, "facts": facts, "recent_titles_to_avoid": hist.get("titles", [])[-20:],
           "exemplar_notes": open(notes, encoding="utf-8").read() if os.path.exists(notes) else ""}
    return {"slot": slot, "category": CATEGORY, "system": M.system_prompt(CATEGORY), "ask": ask, "charts": []}


def due(S, st, now):
    """The part to make now, as main() takes it, or None: the first part not out yet, one a day, from STORY_HOUR UTC, two tries a day."""
    today = now.strftime("%Y-%m-%d")
    done = {**{str(p["part"]): p["posted"] for p in S["parts"] if p.get("posted")}, **st.get("done", {})}
    left = [p for p in S["parts"] if str(p["part"]) not in done]
    if not left or now.hour < int(os.environ.get("STORY_HOUR", "10")) or today in [d[:10] for d in done.values()] \
       or st.get("tries", {}).get(today, 0) >= 2: return None
    k = S["parts"].index(left[0])
    return {**left[0], "cast": S["cast"], "earlier_parts": [f"Part {p['part']}: {p['story']} {p['cliffhanger']}" for p in S["parts"][:k]]}


def last_draft(today):
    """Today's failed draft, if the last try never got past the writer: the second try fixes it instead of starting over."""
    ws = sorted(glob.glob(os.path.join(ROOT, "work", f"story-{today}T*")))
    if not ws or os.path.exists(os.path.join(ws[-1], "spec.json")): return None
    at = sorted(glob.glob(os.path.join(ws[-1], "attempt-*.txt")), key=lambda f: int(re.search(r"(\d+)\.txt$", f).group(1)))
    return at[-1] if at else None


def main(st, post=False, resume=None, ready=None):
    """One part: written (or, with `ready`, a script made by hand), voiced, rendered, reviewed, and queued with `post`."""
    slot = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H%M")
    B = brief(st, slot)
    work, out = os.path.join(ROOT, "work", "story-" + slot), os.path.join(ROOT, "out", "story-" + slot)
    import fcntl                                          # (Linux: the server)
    with open(os.path.join(ROOT, "queue", ".auto.lock"), "a") as lk:   # (one reel at a time: auto_reel.sh takes the same lock)
        fcntl.flock(lk, fcntl.LOCK_EX)
        msgs = None
        if resume:                                         # (the draft and what was wrong with it: the writer fixes it)
            raw = open(resume, encoding="utf-8").read(); errs = M.parse(raw, B)[1]
            msgs = [{"role": "user", "content": json.dumps(B["ask"], indent=1)}, {"role": "assistant", "content": raw},
                    {"role": "user", "content": "Fix these and reply with the whole JSON again: " + "; ".join(errs)}]
        spec = dict(ready) if ready else M.write(B, msgs, work=work)
        if ready and W.check(spec): raise SystemExit("the ready-made script: " + "; ".join(W.check(spec)))
        spec.update(STYLE, scene_js=W.JS, part=st.get("part"), series=S0.get("title", ""))   # (reel.html: the 3D town, one word at a time; the cover says PART N)
        M.save(spec, B, work)
        json.dump(st, open(os.path.join(work, "story.json"), "w", encoding="utf-8"), indent=1)
        r = subprocess.run([sys.executable, os.path.join(HERE, "critic.py"), "loop", work, out], cwd=ROOT,
                           env=dict(os.environ, STEP_TIMEOUT=os.environ.get("STORY_STEP_TIMEOUT", "2700")))   # (a 3D render takes 10 to 20 minutes on the server, over the usual 15-minute limit for a step)
    if r.returncode or not os.path.exists(os.path.join(out, "approved.json")):
        print("HELD: the critic did not approve it; the cut is in", out); return 1
    if not post:
        print("approved, not posted:", out); return 0
    stage, dest = os.path.join(ROOT, "queue", ".staging", slot), os.path.join(ROOT, "queue", slot)   # (a past time: it posts at the next queue run)
    os.makedirs(stage, exist_ok=True)
    for f in ("reel.mp4", "caption.txt", "cover.jpg", "approved.json"): subprocess.run(["cp", os.path.join(out, f), stage], check=True)
    os.rename(stage, dest); print("queued", slot); return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["demo"]:                                  # (no Claude, no voice: the brief carries the story, and the serial's turns)
        B = brief({"part": 1, "of": 3, "story": "Timmy lost it all.", "cliffhanger": "Then my rank hit zero."}, "2026-01-01T0000")
        assert B["category"] in M.CATEGORIES and "Timmy" in B["ask"]["facts"]["story"]["story"] and M.LENGTH[CATEGORY][2] and "Blocky story" in B["system"]
        assert "%(" not in WHAT and "cheer" in WHAT and "doorway" in WHAT and B["ask"]["facts"]["example"][0]["shots"] and CATEGORY == W.CATEGORY   # (the 3D town: its words are in the brief)
        raw = json.dumps({"title": "T", "type": CATEGORY, "device": {"metaphor": "labels"}, "caption": "c", "scenes": W.example()})
        assert M.parse(raw, B)[0]["scene_js"] == W.JS and any("shots" in e for e in M.parse(raw.replace('"shots"', '"shot_list"'), B)[1])   # (the town's scene function is put in; shots are checked)
        S = json.load(open(STORIES, encoding="utf-8")); P = S["parts"]; D = lambda *x: datetime.datetime(*x)
        assert [p["part"] for p in P] == list(range(1, len(P) + 1)) and P[0].get("posted") and P[-1].get("last") and not any(p.get("last") for p in P[:-1])
        for p in P:                                        # (short enough to tell in 140 words with the sign-off)
            assert p["lesson"] and len(p["story"].split()) <= 125 and len(p["cliffhanger"].split()) <= 40, p["part"]
        assert due(S, {}, D(2026, 11, 14, 12)) is None and due(S, {}, D(2026, 11, 15, 9)) is None         # (part 1's day; before the hour)
        p = due(S, {}, D(2026, 11, 15, 10)); assert p["part"] == 2 and len(p["earlier_parts"]) == 1 and "Timmy" in p["cast"] and p["earlier_parts"][0].startswith("Part 1: ")
        assert due(S, {"tries": {"2026-11-15": 2}}, D(2026, 11, 15, 12)) is None                           # (two tries a day)
        assert due(S, {"done": {"2": "2026-11-15"}}, D(2026, 11, 15, 23)) is None and due(S, {"done": {"2": "2026-11-15"}}, D(2026, 11, 16, 10))["part"] == 3
        assert due(S, {"done": {str(q["part"]): "2026-11-15" for q in P}}, D(2026, 12, 1, 10)) is None      # (the parts ran out)
        print("ok")
    elif a[:1] == ["ready"]:                               # (a part made by hand: python3 src/story_reel.py ready src/story_part1.json [--post])
        spec = json.load(open(a[1], encoding="utf-8")); p = next(q for q in S0["parts"] if q["part"] == spec.get("part", 1))
        sys.exit(main({**p, "cast": S0["cast"], "earlier_parts": []}, "--post" in a, ready=spec))
    elif a[:1] == ["next"]:
        S = json.load(open(STORIES, encoding="utf-8")); st = json.load(open(STATE)) if os.path.exists(STATE) else {}
        now = datetime.datetime.now(datetime.UTC); today = now.strftime("%Y-%m-%d"); p = due(S, st, now)
        if not p: sys.exit(0)
        keep = lambda: json.dump(st, open(STATE, "w"), indent=1)
        st["tries"] = {today: st.get("tries", {}).get(today, 0) + 1}; keep()        # (counted before the run: a crash is a try too)
        print(f"=== story part {p['part']}, {now:%F %T} UTC", flush=True)
        rc = main(p, True, last_draft(today))
        if rc == 0: st.setdefault("done", {})[str(p["part"])] = today; keep()
        sys.exit(rc)
    else:
        sys.exit(main(json.load(open(a[0], encoding="utf-8")), "--post" in a, a[a.index("--resume") + 1] if "--resume" in a else None))
