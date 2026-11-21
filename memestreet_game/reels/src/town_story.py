"""'In this town': one complete story a day in the 3D town, built the way the genre's most-watched stories are built.

The owner, 2026-11-21: "watch through thousands of reels from my niche ... remake the entire structure of my reels and how they
flow". The study (research/niche3d_2026-11-21.md) found the genre of the owner's own exemplar (craftee_films' "In This Town, You
Get 1,000,000 Steps", 749K likes): the "In This Town" Roblox story. 114 of its scripts were read, 60 of them published by one
studio in order of views. What its top third does is the form below: one physical rule, "You see,", gags with named neighbours,
the narrator's odd place in the rule, one loved person, a crisis the rule causes, the rule used as the tool, a twist that proves
"what everyone says" wrong, and a callback. About 100 seconds, short sentences, no sign-off (the caption carries the address).

  python3 src/town_story.py slot <YYYY-MM-DDTHHMM> [script.json]   write (or take a script already written), voice, render, review
                                                                   and queue the day's story (exit 1 when not made)
  python3 src/town_story.py demo                     the self-check: no Claude, no voice
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import make_spec as M, story_reel as S, world as W

TYPE = "In this town"                                      # (the saved type: the ledger tells these from the serial's parts)
FORM = "in-this-town"                                      # (make_spec.check reads a brief's form as a remake's: up to 460 words, no outro, short sentences)
WORDS = (330, 420)
STATE = os.path.join(ROOT, "state", "town_stories.json")
FPS = "24"                                                 # (a 3D frame takes about 2 s on the server: 24 a second instead of 30 is a fifth less to draw)
IDEAS = [  # (the trading idea each twist carries, as a truth about people; the least lately used is next)
    ["panic", "Selling in a panic is what makes the loss real: the ones who held through the scare got it back."],
    ["exit first", "Decide where you get out before you get in: a way out chosen calm beats one chosen scared."],
    ["one basket", "Never put everything on one thing: spread out, one loss cannot take it all."],
    ["chasing", "Chasing what has already flown is how you buy at the very top."],
    ["patience", "What is left alone grows: the hands that keep touching it are what stop it."],
    ["borrowing", "Borrowed money makes every fall twice as deep."],
    ["checking", "Watching the price every minute makes you sell at the worst one."],
    ["the crowd", "A crowd shouting about a thing is not what the thing is worth."],
    ["sunk cost", "What you paid for it does not matter: only what it is worth now."],
    ["practice", "Mistakes made in practice cost nothing: the same ones made for real cost everything."],
    ["winning it back", "Trying to win it all back at once is how a small loss becomes a big one."],
    ["small first", "Start small enough that being wrong is cheap."]]
SEEDS = ["In this town, your money is a plant: it only grows when nobody is looking at it.",
         "In this town, every price drops the moment you check it.",
         "In this town, piggy banks are alive, and a scared one spits everything out.",
         "In this town, whatever you buy, you must carry on your back.",
         "In this town, borrowed coins are twice as heavy.",
         "In this town, you only get ten trades in your whole life.",
         "In this town, your savings are a balloon tied to your wrist, and everyone can see how big it is.",
         "In this town, the louder you brag about a thing, the less it is worth.",
         "In this town, luck is a coin you are born with, and you can only flip it once.",
         "In this town, every shop has one price in the morning and another at night, and nobody knows which is higher.",
         "In this town, coins melt if you squeeze them.",
         "In this town, when one person runs to the bank, everybody's feet run too.",
         "In this town, the scared ones sink into the ground, an inch for every worry.",
         "In this town, wanting more makes your pockets heavier.",
         "In this town, regret follows you around as a little grey cloud."]
CAST = {"the narrator (I)": "a kid of the town, about ten: grey-blue shirt #8a96ab, dark blue trousers #2e3a52, brown hair #6b4426, skin #f1c27d",
        "the one they love": "a little brother or sister, a dad or a grandpa: one person, named, with one trademark thing (a red mitten, a helmet, a cap)",
        "the neighbours": "two to four named townspeople for the gags (Mr. and Mrs. somebody, the mailman, a dog), each with one look of their own"}


def state():
    try: return json.load(open(STATE, encoding="utf-8"))
    except (OSError, ValueError): return {"used": []}


def idea(st):
    """The idea out longest ago (never used first, in the list's order)."""
    last = {u.get("idea"): k for k, u in enumerate(st.get("used", []))}
    return min(IDEAS, key=lambda i: last.get(i[0], -1))


def what():
    w = S.WHAT
    grammar = w[w.index("THE LOOK"):w.index("THE STORY:")]
    return ("IN THIS TOWN: ONE COMPLETE STORY in the blocky town (the genre of the owner's exemplar; built the way that genre's most-watched "
            "stories are built: 114 scripts were studied). " + f"{WORDS[0]} to {WORDS[1]}" + " spoken words, about 95 seconds, in SHORT "
            "sentences (7 words on average, many of 3 to 5), told in the first person by a kid of the town, warm and funny, fast. Never a "
            "lesson, never a lecture, no trading words at all (no 'stock', 'trade', 'invest', 'stop-loss', 'portfolio'): money, coins, "
            "prices, shops and luck are the whole vocabulary. "
            "THE TEN BEATS, in this order: "
            "1. THE RULE, the very first words: 'In this town, <one physical rule in 4 to 8 words>.' ('In this town, running turns you "
            "gold.' 'In this town, hugs run out.') Yours makes PHYSICAL one thing every trader knows in the gut, money, prices, luck, "
            "risk, or the feelings round them (fear, greed, patience, envy, regret): something a body or a thing visibly does (a number on "
            "a chest, coins that melt, a piggy bank that spits, the scared sinking into the ground). The genre's most-watched rules are "
            "about family, the body and feelings, so lean there. One rule only. facts.premise_seeds are examples of the "
            "kind; invent your own, never one in facts.premises_used. "
            "2. 'You see, ...': how it works, in two or three sentences, with one exact number and one sound word (Clink. Ding. Boing. "
            "Whoosh.), and ONE thing 'everyone says' about the rule, said plainly here, that the ending will prove wrong. "
            "3. 'So, everybody here ...': three or four quick gags of how the town lives with the rule, each a picture of its own, with "
            "named neighbours (Mr. Pruitt, Mrs. Tibbs, the mailman, a dog called Meatball); one of them plain silly; in one of them "
            "somebody tries the obvious way round the rule and it fails. "
            "4. 'Me? ...': the narrator's own odd place in the rule (the only one who..., the one who never..., saving theirs for "
            "something big), with a number. "
            "5. THE ONE THEY LOVE: a little brother or sister, a dad or a grandpa, and a small daily ritual between the two with a number "
            "in it ('my record was 9 seconds'); and one line somebody says that will come back at the end. "
            "6. THE SLIP: the rule bites the narrator or the loved one once, small, 'the first time ever'. "
            "7. THE CRISIS: the loved one in real trouble because of the rule, the town watching and unable to help BECAUSE of the rule, "
            "and a clock running in numbers ('ten minutes', 'half the sun was gone'). "
            "8. THE MOVE: the narrator does what nobody dares, using the rule itself as the tool; it nearly fails: the rule seems to strike. "
            "9. THE TWIST: what 'everyone says' was wrong, in one or two short sentences that make the viewer re-read the whole story "
            "('Running never turned anyone gold. Running away did.'). The twist IS facts.idea, said as a truth about people. "
            "10. THE CALLBACK: the ritual of beat 5 comes back turned round and the planted line is answered; the last sentence is a "
            "picture, never a moral. NO sign-off, no 'join', no address: the story's last line is the reel's last line, and no scene is "
            "of kind \"outro\". "
            "WHAT THE GENRE'S MOST-WATCHED THIRD DOES AND ITS LEAST-WATCHED THIRD DOES NOT: opens 'In this town' (not 'In this world'); "
            "'You see,' in the second sentence; sound words; named neighbours; family. Nothing 'deadly', no monster, nothing that "
            "'takes you'; nobody dies; the ending is happy and earned. Leave ONE loophole unanswered that a clever viewer will shout at "
            "the screen: under these stories the biggest comments are loopholes ('Bro just leave the town', 171,000 likes). "
            + grammar +
            "FOR THIS FORMAT: 20 to 30 scenes, each one or two short sentences (4 to 26 words: a sound word never stands as a scene's whole "
            "line) with 1 to 3 shots, so the picture cuts "
            "about every 1.5 to 2 seconds and every sentence is acted out by the people it names, where it happens. The rule is SEEN "
            "working in scene 0 (a close shot: the number, the coin, the thing changing inside the first second, on the words that say "
            "so). The number on a chest, when the rule has one, is on every named actor in every shot. Sound words get an fx on their "
            "word. \"type\" is \"Blocky story\"; every scene is of kind \"free\". The title is the rule in 3 to 6 words. \"ask\" (a field beside "
            "the title): the question the reel leaves on screen over its last seconds, 4 to 8 words ending in '?', put to the viewer and "
            "answerable in a word or with a loophole ('What would YOU do with your last one?'); the renderer adds COMMENT BELOW and stands it at the top of the frame over the last four seconds, so the story's last shots are wide or mid, never close: the sky above the heads is free. "
            "THE CAPTION: line 1 is the rule and a question that invites a loophole ('In this town, hugs run out. What would you do with "
            "your last one?'), under 125 characters; then 'A made-up town and a made-up story.'; then one line on Meme Street, only what "
            "facts.meme_street says, with 'Play today's stock at memestreet.net'; then '" + M.DISCLAIMER + "'; then these hashtags: #inthistown "
            "#storytime #animation #3danimation #MemeStreet.")


def brief(slot):
    st = state(); i = idea(st)
    facts = {"idea": i[1], "premise_seeds": SEEDS, "premises_used": [u.get("rule") for u in st.get("used", []) if u.get("rule")][-40:],
             "story": {"cast": CAST}, "meme_street": M.GAME_FACTS, "example": W.example(), "recent_devices": [], "video": {"available": False},
             "hook_shots_used_lately": []}
    ask = {"category": S.CATEGORY, "what_this_reel_is": what(), "facts": facts, "recent_titles_to_avoid": [u.get("title") for u in st.get("used", [])][-20:]}
    return {"slot": slot, "category": S.CATEGORY, "form": FORM, "system": M.system_prompt(S.CATEGORY), "ask": ask, "charts": []}, i


def errors(spec):
    """The form's own faults, in words the writer can fix (the rest is make_spec.check and world.check)."""
    sc = spec.get("scenes") or []; text = " ".join(str(s.get("vo", "")) for s in sc); n = len(text.split()); errs = []
    if not text.strip().lower().startswith("in this town"): errs.append("the first words are 'In this town, <the rule>.'")
    if "you see" not in " ".join(text.split()[:45]).lower(): errs.append("'You see,' opens the second or third sentence: how the rule works")
    if not WORDS[0] - 30 <= n <= WORDS[1] + 30: errs.append(f"the story is {n} words; it must be {WORDS[0]} to {WORDS[1]}")
    if any(s.get("kind") == "outro" for s in sc): errs.append("no outro scene and no sign-off: the story's last line is the reel's last line")
    if "memestreet.net" in text.lower() or "meme street" in text.lower(): errs.append("the story never names Meme Street: the caption does")
    if not 16 <= len(sc) <= 34: errs.append(f"{len(sc)} scenes: 20 to 30, each one or two short sentences")
    short = [k for k, x in enumerate(sc) if len(str(x.get("vo", "")).split()) < 4]
    if short: errs.append(f"scene {short[0]}'s line is under 4 words: a sound word or a two-word beat rides inside a longer line (the voice is checked line by line)")
    ask = str(spec.get("ask") or "").strip()
    if not (3 <= len(ask.split()) <= 9 and ask.endswith("?")): errs.append('"ask": the closing question to the viewer, 4 to 8 words ending in a question mark')
    return errs


def make(slot, ready=None):
    """The day's story: written (its form checked, one fix) or, with `ready`, a script already written and read; voiced, rendered at
    24 frames, reviewed, queued in its slot. -> the slot, or None."""
    import news_reel as N
    B, i = brief(slot)
    work, out = os.path.join(ROOT, "work", "auto-" + slot), os.path.join(ROOT, "out", "auto-" + slot)
    subprocess.run(["rm", "-rf", work, out], check=True)
    spec = json.load(open(ready, encoding="utf-8")) if ready else M.write(B, work=work)
    bad = errors(spec) + (W.check(spec) if ready else [])
    if bad and ready: print("the ready-made script:", "; ".join(bad), flush=True); return None
    if bad:
        print("the form sent it back:", "; ".join(bad), flush=True)
        spec = M.write(B, msgs=[{"role": "user", "content": json.dumps(B["ask"], indent=1)}, {"role": "assistant", "content": json.dumps(spec)},
                                {"role": "user", "content": "Fix these and reply with the whole JSON again: " + "; ".join(bad)}], work=work)
        if errors(spec): print("not made: the form failed twice:", "; ".join(errors(spec)), flush=True); return None
    spec.update(S.STYLE, voice_speed=1.5, scene_js=W.JS, part=None, series="", remake_of=FORM)   # (the serial's voice, faster: the genre tells its stories at 4.4 words a second; at 1.5 ours runs 4.25 and every test line was heard right, 2026-11-21)
    M.save(spec, B, work)
    r = subprocess.run([sys.executable, os.path.join(HERE, "critic.py"), "loop", work, out], cwd=ROOT,
                       env=dict(os.environ, STEP_TIMEOUT=os.environ.get("TOWN_STEP_TIMEOUT", "9000"), REVIEW_FPS=FPS, AUTO_FPS=FPS))   # (about 2,300 frames at 2 s each)
    if r.returncode or not os.path.exists(os.path.join(out, "approved.json")):
        print("not made: the cut was not finished", flush=True); return None
    p = os.path.join(work, "spec.json"); final = json.load(open(p, encoding="utf-8")); final["type"] = TYPE
    json.dump(final, open(p, "w", encoding="utf-8"))
    st = state(); st.setdefault("used", []).append({"slot": slot, "idea": i[0], "title": final.get("title"), "rule": str((final.get("scenes") or [{}])[0].get("vo", ""))[:120]})
    os.makedirs(os.path.dirname(STATE), exist_ok=True); json.dump(st, open(STATE, "w", encoding="utf-8"), indent=1)
    return N.queue_out(out, slot, final.get("title", ""))


def demo():
    t = what()
    assert "THE TEN BEATS" in t and "THE LOOK" in t and "%(" not in t and M.DISCLAIMER in t and "In this town" in t
    assert idea({"used": []})[0] == IDEAS[0][0] and idea({"used": [{"idea": IDEAS[0][0]}]})[0] == IDEAS[1][0]
    assert idea({"used": [{"idea": k[0]} for k in IDEAS]})[0] == IDEAS[0][0]                       # (all used: the one out longest)
    B, i = brief("2026-01-01T1300")
    assert B["form"] == FORM and B["category"] == S.CATEGORY and B["ask"]["facts"]["idea"] == i[1] and B["ask"]["facts"]["example"]
    sc = lambda vo, **k: dict({"kind": "free", "text": " ".join(vo.split()[:3]), "vo": vo, "shots": [{"place": "street", "cam": "close:narrator", "actors": [{"who": "narrator", "at": [0, 0], "chest": 5}]}]}, **k)
    body = [sc("In this town, coins melt if you squeeze them."), sc("You see, the tighter you hold one, the faster it drips. Drip.")] + [sc("So everybody here carries their coins on open hands, even Mr. Pruitt the baker.") for _ in range(24)]
    good = {"title": "Coins Melt", "ask": "What would YOU do with yours?", "type": S.CATEGORY, "device": {"metaphor": "melting coins"}, "caption": "c memestreet.net", "scenes": body}
    assert errors(good) == [], errors(good)
    assert any("first words" in e for e in errors(dict(good, scenes=body[1:] + body[:1]))) and any("outro" in e for e in errors(dict(good, scenes=body + [{"kind": "outro", "vo": "x"}])))
    assert any("words" in e for e in errors(dict(good, scenes=body[:17]))) and any('"ask"' in e for e in errors(dict(good, ask="Comment below")))
    spec, errs = M.parse(json.dumps(good), B)                # (the brief's form reaches the checks: no outro, no headline, the length of a remake)
    assert spec.get("remake_of") == FORM and not any("outro" in e or "headline" in e or "narration is" in e or "sentences average" in e for e in errs), errs
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:] or ["demo"]
    if a[0] == "demo": demo()
    elif a[0] == "slot" and len(a) > 1: sys.exit(0 if make(a[1], a[2] if len(a) > 2 else None) else 1)
    else: raise SystemExit(__doc__)
