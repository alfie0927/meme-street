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

CATEGORY = "Blocky story"
STORIES, STATE = os.path.join(HERE, "stories.json"), os.path.join(ROOT, "state", "story.json")
WHAT = ("A STORY REEL IN PARTS (the owner, 2026-11-14), made like the viral blocky-game story reels ('In this town, you only get "
        "1,000,000 steps': the owner's exemplar). Told in the first person by the narrator, an average trader. THE PREMISE, said in the "
        "first line over the first shot: in this town, everyone's money is printed on their chest, and it is set by their trades. THE "
        "LOOK, as the exemplar: the whole 1080x1920 frame is the scene, a film shot in a blocky game world, no panels, no HUD, no "
        "diagrams, no cards. A NEW SHOT ON ALMOST EVERY LINE (about every 2 seconds): a close shot of one character (head and chest "
        "filling most of the frame) or a wide shot of a street, a house, a shop, a park, a bank, an airport; the camera pushes in slowly "
        "on every shot. Everyday places drawn as flat, shaded blocks: sky, grass, a road with a yellow line, houses with windows and "
        "doors, trees as green blocks on brown trunks, cars as boxes. EVERY PERSON is a blocky avatar drawn in svg with a little depth "
        "(each block has a lit face and a darker side face): a cube head, a simple painted face (dot or oval eyes, a mouth that shows "
        "the mood: smile, grin, frown, open shock, tears), hair as a block cap, a box torso with a shirt colour, block arms and legs "
        "that swing stiffly when they walk. ON EVERY CHEST a white rounded label with the person's money in bold black numbers "
        "('1,000,000', '2,450', '0'): it is the device, it counts up or crashes on screen when their trades win or lose, and the "
        "narrator's own number is ordinary. People act out every line: Timmy holding out his hands to strangers, the rich waving from "
        "a plane and a sports car, the narrator shrugging on a park bench. Never write the name of any real game, never draw its logo. "
        "THE CAPTIONS are the renderer's: one big word at a time on the ground in front of the actors, from y 1310 to y 1440 (it sets "
        "them; never draw your own text below y 1150; in a wide shot stand every character with the feet at or above y 1290, and in "
        "a close shot keep the face and the chest label above y 1250, so a word only ever lands on the ground or on legs; give every free scene its 2 to 5 word \"text\" as usual, but never call api.punch: "
        "the renderer hides punch lines and the top hook in this format). The only words you draw are the chest numbers "
        "and the odd sign on a building. "
        "THE STORY: facts.story.story is this part's story: tell every beat of it, in that order, in the narrator's voice "
        "('I'm just an average trader'), tightened to fit the word limit, every line acted out by the avatars, funny and fast. "
        "A SERIAL: facts.story.earlier_parts is what the viewers have already seen (never retell it beyond the story's own first "
        "sentence, never contradict it), and facts.story.cast gives every returning character's colours and numbers: draw them exactly "
        "so, in the same town, palette and chest labels in every part (the device is the series' own: the same on purpose). "
        "facts.story.lesson is the one trading idea this part teaches: the story says it once, in plain words. The link to Meme "
        "Street is one line, where the story places it (only what facts.meme_street says: made-up companies, news that moves prices, "
        "1,000 memebucks of practice money with no cash value, the lessons and the Daily Chart); 'better' means a plan and practice, "
        "never a promise of money or of beating the market. Then facts.story.cliffhanger, as the last story line before the sign-off: "
        "a MAJOR cliffhanger, something shocking happens on screen (a number crashes, a door bursts open, the sky turns dark red) and "
        "the line breaks off unresolved. The sign-off scene names the next part: 'Part 3 drops soon. Join free at memestreet.net.' "
        "(part N+1). If facts.story.last is true this is the final part: facts.story.cliffhanger is the closing line, said whole, "
        "nothing left open, and the sign-off is 'Follow for the next story. Join free at memestreet.net.' "
        "Shape: scene 0 is the hook: a close shot of a character whose chest number races, crashes or flips inside the first second "
        "(in part 1 it races to 1,000,000), and the first spoken sentence carries the premise (your money is printed on your chest) "
        "and, in a later part, where the last one stopped, so a new viewer follows: the story's own first sentence. Every scene of "
        "kind \"free\" but the outro; short scenes, one or two lines each. \"type\" is \"Blocky story\". A clean picture: nothing "
        "runs off an edge, no drawn text below y 1150. The post caption: line 1 is the hook with a question for the viewer (under "
        "125 characters); 'Part N' (add 'of M' only if facts.story.of is given); the story in two or three short lines that give "
        "away nothing of the ending; a line on Meme Street with 'practice money with no cash value'; 'Follow for part N+1.' unless "
        "it is the final part; 'Practise at memestreet.net'; "
        "'Fictional market. Not investment advice.' (word for word: the checker wants it); 3 to 5 hashtags. The voice tells it like "
        "the exemplar's narrator, in flowing sentences of 10 to 20 words joined with and, so, but, because (the checker refuses "
        "an average under 10), while the pictures still cut every 2 seconds.")
M.CATEGORIES.setdefault(CATEGORY, WHAT)
M.LENGTH.setdefault(CATEGORY, (90, 140, True))        # (spoken words: the part's beats, the link and the cliffhanger; 60 s at most)


def brief(st, slot):
    hist = json.load(open(M.HISTORY)) if os.path.exists(M.HISTORY) else {}
    notes = os.path.join(ROOT, "exemplar", "NOTES.md")
    # (recent_devices stays empty: a serial keeps its own device, and the checker refuses one that is close to a recent reel's)
    facts = {"story": st, "meme_street": M.SITE_FACTS, "recent_devices": [], "video": {"available": False}, "hook_shots_used_lately": []}
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


def main(st, post=False, resume=None):
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
        spec = M.write(B, msgs, work=work); spec["one_word"] = True        # (reel.html: one word at a time, no header, as the exemplar)
        M.save(spec, B, work)
        json.dump(st, open(os.path.join(work, "story.json"), "w", encoding="utf-8"), indent=1)
        r = subprocess.run([sys.executable, os.path.join(HERE, "critic.py"), "loop", work, out], cwd=ROOT)
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
