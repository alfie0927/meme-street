"""'What if': one hypothetical about money, explored in the 3D town, built like the reel the owner chose as the model.

The owner, 2026-11-22: "i want to make reels gather hundreds of thousands of views following how other reels did e.g. reels like
this" (Yastor's "What if your reaction time was 10x faster?", 231,000 likes, 678 comments). What it does, measured: the premise as
a question in the first words and on screen at the top; at once one concrete consequence with a number; the real-world baseline;
four to six vignettes of everyday life with the power, small to absurd; "But there's a catch."; the downside in vignettes with
numbers; the good news that flips it; a verdict question and a last line that lands on the first picture, so the reel loops.
241 words in 96 s, a new shot every 3.2 s, a badge with the power at the top the whole time. Second person throughout.

  python3 src/whatif.py slot <YYYY-MM-DDTHHMM>    write, voice, render, review and queue (exit 1 when not made)
  python3 src/whatif.py demo                      the self-check: no Claude, no voice
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import make_spec as M, story_reel as S, world as W, town_story as TS

TYPE = "What if"
FORM = "what-if"
WORDS = (200, 260)
STATE = os.path.join(ROOT, "state", "whatif.json")
IDEAS = TS.IDEAS
SEEDS = ["What if you could see one second into the future?", "What if every price tag showed tomorrow's price?",
         "What if your savings were printed on your forehead?", "What if you felt every coin you lost as a pinch?",
         "What if you could undo one purchase a day?", "What if you could only check your money once a year?",
         "What if money doubled every year you didn't touch it?", "What if every shop changed its prices every second?",
         "What if your phone buzzed every time someone else got richer?", "What if everyone could hear what you think when you shop?",
         "What if your money got heavier the more scared you were?", "What if you could copy the richest person's every move?"]
M.LENGTH.setdefault(FORM, (WORDS[0] - 30, WORDS[1] + 30, False))   # (make_spec.check reads a form's own length)


def what():
    w = S.WHAT
    grammar = w[w.index("THE LOOK"):w.index("THE STORY:")]
    return ("WHAT IF: ONE HYPOTHETICAL ABOUT YOU AND MONEY, explored in the blocky town (the owner's model reel: 'What if your reaction "
            "time was 10x faster?', 231,000 likes, 678 comments). " + f"{WORDS[0]} to {WORDS[1]}" + " spoken words, about 90 seconds, "
            "in SHORT sentences (6 to 7 words on average), in the second person ('you'), unhurried, curious, funny. "
            "THE PREMISE: a power or a change of the world about money, prices, luck, buying and selling, or the feelings round them, "
            "made physical or superhuman, about the VIEWER ('What if you could see one second into the future?'). facts.premise_seeds "
            "are examples of the kind; invent your own, never one in facts.premises_used. "
            "THE BEATS, in this order (the model reel's own): "
            "1. THE PREMISE, the very first words, as a question: 'What if <you ...>?' (6 to 12 words). Then AT ONCE the first concrete, "
            "visible consequence with an exact number ('Your phone would fall 3 millimeters.'). "
            "2. THE BASELINE: how it is now, in one or two sentences with a number ('Right now, your brain needs a quarter of a second "
            "to react.'). "
            "3. THE GOOD: four to six quick vignettes of everyday life with the power, each one picture and one or two short sentences, "
            "from small to absurd; one plain silly; one a question that is its own joke ('Blaming the lag? For the first time ever, it "
            "really is the lag.'). "
            "4. 'But there's a catch.' Then the cost the premise brings, by its own logic, in one or two sentences. "
            "5. THE BAD: three or four vignettes of the downside, each with a number ('A one-minute microwave? 10 minutes.'). "
            "6. THE GOOD NEWS: one line that flips the downside ('The good news? Your weekend lasts almost three weeks.'). "
            "7. THE VERDICT AND THE LOOP: a question to the viewer ('So, super power?'), then a last line that lands back on the first "
            "picture, so the reel loops into itself ('You'd never drop your phone again.'). No sign-off, no address, no outro scene. "
            "facts.idea is THE CATCH or THE GOOD NEWS: said as a truth about people and money, in plain words. Plain words only: price, "
            "buy, sell, money, coins, a chart; no jargon ('stop-loss', 'portfolio', 'leverage', 'volatility'). NUMBERS: inside the "
            "hypothetical, or real ones everybody knows (60 seconds, 24 hours, 365 days) and plain arithmetic; never a statistic about "
            "people, markets or companies, never a real company. "
            + grammar +
            "FOR THIS FORMAT: 18 to 28 scenes, each one or two short sentences (4 to 22 words) with 1 to 3 shots, so the picture cuts about "
            "every 3 seconds; every vignette is acted out by the narrator (the viewer's stand-in: 'you') and the townspeople it names, "
            "where it happens. Scene 0 shows the power working inside its first second, on the words that say so. Scenes 0 and 1 are "
            "wide or mid shots (the premise stands at the top of the frame over the first 4 seconds: the sky above the heads is free). "
            "Sound words get an fx on their word. \"type\" is \"Blocky story\"; every scene is of kind \"free\". The title is the premise "
            "in 3 to 7 words. Beside the title: \"premise\": the opening question, word for word as said; \"badge\": the power in 2 to 4 "
            "words in capitals ('1 SECOND AHEAD', 'PRICES x10'), shown in a pill at the top for the whole reel; \"ask\": the question the "
            "reel leaves on screen over its last seconds, 4 to 8 words ending in '?' ('Would YOU want it?'); the renderer adds COMMENT "
            "BELOW and stands it at the top over the last four seconds, so the last shots are wide or mid. "
            "THE CAPTION: line 1 is the premise and a question that invites an answer, under 125 characters; then 'A made-up what if.'; "
            "then one line on Meme Street, only what facts.meme_street says, with 'Play today's stock at memestreet.net'; then '"
            + M.DISCLAIMER + "'; then these hashtags: #whatif #animation #3danimation #money #MemeStreet.")


def brief(slot):
    st = TS.state(STATE); i = TS.idea(st)
    facts = {"idea": i[1], "premise_seeds": SEEDS, "premises_used": [u.get("rule") for u in st.get("used", []) if u.get("rule")][-40:],
             "story": {"cast": {"the narrator (you)": TS.CAST["the narrator (I)"], "the townspeople": TS.CAST["the neighbours"]}},
             "meme_street": M.GAME_FACTS, "example": W.example(), "recent_devices": [], "video": {"available": False}, "hook_shots_used_lately": []}
    ask = {"category": S.CATEGORY, "what_this_reel_is": what(), "facts": facts, "recent_titles_to_avoid": [u.get("title") for u in st.get("used", [])][-20:]}
    return {"slot": slot, "category": S.CATEGORY, "form": FORM, "system": M.system_prompt(S.CATEGORY), "ask": ask, "charts": []}, i


def errors(spec):
    """The form's own faults, in words the writer can fix (the rest is make_spec.check and world.check)."""
    sc = spec.get("scenes") or []; text = " ".join(str(s.get("vo", "")) for s in sc); n = len(text.split()); errs = []
    first = re.split(r"(?<=[?.!])\s", text.strip(), 1)[0]
    if not (text.strip().lower().startswith("what if") and first.endswith("?")): errs.append("the first words are the premise as a question: 'What if <you ...>?'")
    if "a catch" not in text.lower(): errs.append("the turn is said: 'But there's a catch.'")
    if not WORDS[0] - 30 <= n <= WORDS[1] + 30: errs.append(f"the script is {n} words; it must be {WORDS[0]} to {WORDS[1]}")
    if any(s.get("kind") == "outro" for s in sc): errs.append("no outro scene and no sign-off: the last line lands back on the first picture")
    if "memestreet.net" in text.lower() or "meme street" in text.lower(): errs.append("the script never names Meme Street: the caption does")
    if not 14 <= len(sc) <= 32: errs.append(f"{len(sc)} scenes: 18 to 28, each one or two short sentences")
    short = [k for k, x in enumerate(sc) if len(str(x.get("vo", "")).split()) < 4]
    if short: errs.append(f"scene {short[0]}'s line is under 4 words: a two-word beat rides inside a longer line (the voice is checked line by line)")
    if str(spec.get("premise") or "").strip().lower() != first.lower(): errs.append('"premise": the opening question, word for word as the first sentence says it')
    if not (1 <= len(str(spec.get("badge") or "").split()) <= 4 and len(str(spec.get("badge") or "")) <= 22): errs.append('"badge": the power in 2 to 4 words, at most 22 letters')
    ask = str(spec.get("ask") or "").strip()
    if not (3 <= len(ask.split()) <= 9 and ask.endswith("?")): errs.append('"ask": the closing question to the viewer, 4 to 8 words ending in a question mark')
    return errs


def demo():
    t = what()
    assert "THE PREMISE" in t and "THE LOOK" in t and "%(" not in t and M.DISCLAIMER in t and "But there's a catch" in t
    B, i = brief("2026-01-01T1800")
    assert B["form"] == FORM and B["ask"]["facts"]["idea"] == i[1] and M.LENGTH[FORM][2] is False
    sc = lambda vo, **k: dict({"kind": "free", "text": " ".join(vo.split()[:3]), "vo": vo, "shots": [{"place": "street", "cam": "mid:narrator", "actors": [{"who": "narrator", "at": [0, 0]}]}]}, **k)
    body = [sc("What if you could see one second ahead? Your coin would never drop.")] + [sc("You catch the falling coin before it even leaves the table.") for _ in range(17)] + [sc("But there's a catch. Everyone else sees you coming.")]
    good = {"title": "One Second Ahead", "premise": "What if you could see one second ahead?", "badge": "1 SECOND AHEAD", "ask": "Would YOU want it?",
            "type": S.CATEGORY, "device": {"metaphor": "a second ahead"}, "caption": "c memestreet.net", "scenes": body}
    assert errors(good) == [], errors(good)
    assert any("premise as a question" in e for e in errors(dict(good, scenes=body[1:])))
    assert any('"premise"' in e for e in errors(dict(good, premise="What if?"))) and any('"badge"' in e for e in errors(dict(good, badge="")))
    assert any("catch" in e for e in errors(dict(good, scenes=body[:-1])))
    spec, errs = M.parse(json.dumps(good), B)
    assert spec.get("remake_of") == FORM and not any("outro" in e or "headline" in e or "sentences average" in e for e in errs), errs
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:] or ["demo"]
    if a[0] == "demo": demo()
    elif a[0] == "slot": sys.exit(0 if TS.make(a[1], F=sys.modules[__name__]) else 1)
