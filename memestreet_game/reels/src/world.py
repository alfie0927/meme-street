"""The story serial's 3D town (src/world3d.js draws it; the owner, 2026-11-14: "a proper 3D world, where the people are
walking around"). A story script carries "shots" in every scene instead of a scene function of its own: this file holds
the fixed scene function, the words a shot may use (read from world3d.js, which refuses to load if they differ from what
it draws), and the check that tells the writer what is wrong with a shot.

  python3 src/world.py demo     the self-check (the hand-made part 1 passes; broken shots are refused)
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
CATEGORY = "Blocky story"
JS = "({t, api}) => api.world(t)"                          # (the scene function of every 3D story reel: reel.html draws the shots)
VOC = json.loads(re.search(r"^const VOC=(\{.*\});$", open(os.path.join(HERE, "world3d.js"), encoding="utf-8").read(), re.M).group(1))
THINGS = ("screen", "plane", "car", "door")
CROWD_CHEST = ("rand", "zero", "x2", "x10", "half", "neg")
ALIAS = {"i": "narrator", "me": "narrator", "market sheriff": "sheriff"}
nk = lambda w: re.sub(r"[^a-z0-9%$.]", "", str(w).lower())


def norm(name):
    """A name as world3d.js reads it: 'the narrator (I)' is 'narrator'."""
    s = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", re.sub(r"^the\s+", "", re.sub(r"\(.*?\)", "", str(name or "").lower()).strip()))).strip()
    return ALIAS.get(s, s)


def said(vo, phrase):
    """Is the phrase in the line, as world3d.js finds it (atSay): its words in order, each the start of a written word.
    Number words count: the shots are timed on the line as written, not on the captions' digits."""
    P, W = [p for p in map(nk, str(phrase).split()) if p], [nk(w) for w in str(vo).split()]
    return bool(P) and any(all(W[k + j].startswith(p) for j, p in enumerate(P)) for k in range(len(W) - len(P) + 1))


def check(spec, charts=None):
    """What is wrong with the shots, in words the writer can fix. `charts`: the reel's real charts, for a screen's "real"."""
    errs = []; charts = charts if charts is not None else (spec.get("charts") or [])
    for k, sc in enumerate(spec.get("scenes") or []):
        sh, vo = sc.get("shots"), sc.get("vo", "")
        if sc.get("kind") == "outro":
            if sh: errs.append(f"scene {k}: the outro has no shots (the end card covers the town)")
            continue
        if not isinstance(sh, list) or not 1 <= len(sh) <= 3 or not all(isinstance(q, dict) for q in sh):
            errs.append(f"scene {k}: give it \"shots\", a list of 1 to 3 shot objects (a new shot about every 3 seconds)"); continue
        for j, q in enumerate(sh):
            w = f"scene {k} shot {j}"; bad = lambda m: errs.append(f"{w}: {m}")
            if q.get("place") not in VOC["places"]: bad(f"place must be one of {', '.join(VOC['places'])}")
            if j and not q.get("say"): bad('a later shot needs "say", the words of the line it cuts in on')
            for f in ("say", "sky_say", "door_say"):
                if q.get(f) and not said(vo, q[f]): bad(f'{f} {q[f]!r} is not in the scene\'s line, word for word (two or three of its words, exactly as written)')
            people = [a for a in q.get("actors") or [] if isinstance(a, dict)]
            crowds = [c for c in (q["crowd"] if isinstance(q.get("crowd"), list) else [q.get("crowd")]) if isinstance(c, dict)]
            names = {norm(a.get("who")) for a in people}
            if len(people) + sum(int(c.get("n") or 6) for c in crowds) > 18: bad("at most 18 people in a shot")
            if not people and not crowds and not any(q.get(x) for x in ("plane", "car", "screen")): bad("nobody and nothing is in it: give it actors")
            cam = str(q.get("cam") or "wide").split(":"); kind = cam[0].strip(); tg = [x.strip() for x in re.split(r"[,>]", cam[1]) if x.strip()] if len(cam) > 1 else []
            if kind in THINGS: tg, kind = [kind], "wide"
            if kind not in VOC["cams"]: bad(f"cam is one of {', '.join(VOC['cams'])} (with its target, 'close:Timmy'), or screen, wide:plane, wide:car")
            need = {"close": 1, "mid": 1, "low": 1, "two": 2, "over": 2}.get(kind, 0)
            if len(tg) < need: bad(f"cam {kind} names {need} of the shot's actors ('{kind}:{'A,B' if need == 2 else 'Timmy'}')")
            for t in tg:
                if t == "screen":
                    if q.get("place") not in ("room", "square") or not q.get("screen"): bad('the camera is on the screen: only the room and the square have one, and the shot gives it "screen"')
                elif t in THINGS:
                    if t != "door" and not q.get(t): bad(f'the camera is on the {t}, but the shot has no "{t}"')
                elif norm(t) not in names: bad(f"the camera names {t!r}, who is not among this shot's actors")
            if "screen" in tg and q.get("place") == "room":   # (part 2's review: a head covered the words on the screen)
                for a in people:
                    if any(isinstance(v, list) and v and isinstance(v[0], (int, float)) and v[0] < 1.9 for v in (a.get("at"), a.get("to"), (a.get("then") or {}).get("to"))):
                        bad(f"{a.get('who')} stands in front of the room's screen and covers its words: in a screen shot there everyone is at x 1.9 or more (the presenter at [2.2, -2.2], a second person at [3.1, -1.4])")
            if q.get("move") and q["move"] not in VOC["moves"]: bad(f"move is one of {', '.join(VOC['moves'])}")
            if q.get("sky") and q["sky"] not in VOC["skies"]: bad(f"sky is one of {', '.join(VOC['skies'])}")
            if q.get("door") and (q["door"] not in ("open", "closed", "burst") or q.get("place") not in ("home", "doorway")): bad('door is open, closed or burst, at home or in the doorway')
            if q.get("look") not in (None, "photo"): bad('a shot\'s "look" can only be "photo"')
            for f in q.get("fx") or []:
                f = {"do": f} if isinstance(f, str) else f
                if f.get("do") not in VOC["fx"]: bad(f"fx is one of {', '.join(VOC['fx'])}")
                if f.get("say") and not said(vo, f["say"]): bad(f"fx say {f['say']!r} is not in the line")
            s = q.get("screen")
            if s is not None:
                if not isinstance(s, dict) or not (s.get("chart") or s.get("lines") or s.get("text") or s.get("title") or s.get("real") is not None): bad('screen is {"title", "chart"}, {"title", "lines"} or {"text"}')
                elif s.get("real") is not None:            # (the reel's real chart on the screen)
                    n = len((charts[s["real"]] or {}).get("candles") or []) if isinstance(s["real"], int) and not isinstance(s["real"], bool) and 0 <= s["real"] < len(charts) else 0
                    whole = lambda v: isinstance(v, int) and not isinstance(v, bool)
                    if not n: bad('"real" on a screen is the number of one of the charts of this reel (facts.charts), and this reel has ' + (f"{len(charts)}" if charts else "none"))
                    elif not (whole(s.get("to")) and 0 <= s["to"] < n and (s.get("from") is None or (whole(s["from"]) and 0 <= s["from"] <= s["to"]))): bad(f'a real chart draws its candles "from" to "to": whole candle numbers, 0 to {n - 1}, from no later than to')
                    elif any(s.get(k) is not None and not (whole(s[k]) and 0 <= s[k] <= s["to"]) for k in ("buy", "sell")): bad('"buy" and "sell" are candle numbers no later than "to"')
                    elif s.get("level") is not None and not isinstance(s["level"], (int, float)): bad('"level" is a real price')
                    elif s.get("chart"): bad('a screen shows "real" or a made-up "chart", not both')
                    if q.get("place") not in ("room", "square"): bad("a real chart is shown on the screen of the square or of the room")
                elif s.get("chart") and s["chart"] not in VOC["charts"]: bad(f"a screen's chart is one of {', '.join(VOC['charts'])}")
                elif s.get("lines") and not (isinstance(s["lines"], list) and len(s["lines"]) <= 3 and all(len(str(x)) <= 22 for x in s["lines"])): bad("a screen's lines: at most 3, each 22 characters or fewer")
                elif q.get("place") not in ("room", "square") and not any(a.get("hold") == "chart" or (a.get("then") or {}).get("hold") == "chart" for a in people): bad('only the room and the square have a screen; elsewhere someone holds it ("hold": "chart")')
            p = q.get("plane")
            if p is not None and (p if isinstance(p, str) else (p or {}).get("mode", "parked")) not in VOC["planes"]: bad(f"a plane's mode is one of {', '.join(VOC['planes'])}")
            c = q.get("car")
            if c is not None:
                if not isinstance(c, dict) or c.get("color", "gold") not in VOC["cars"]: bad(f"car is {{color, from, to, who}}, its color one of {', '.join(VOC['cars'])}")
                elif c.get("who") and norm(c["who"]) not in names: bad(f"the car's driver {c['who']!r} is not among the shot's actors")
            for a in people + crowds:
                who = a.get("who") or "the crowd"; mob = a in crowds
                if not mob and not a.get("who"): bad('every actor has "who"')
                if mob and (not isinstance(a.get("n", 6), int) or not 2 <= a.get("n", 6) <= 14 or a.get("form", "cluster") not in VOC["forms"]): bad(f"a crowd is {{n: 2 to 14, form: {' | '.join(VOC['forms'])}, at}}")
                for st, what in ((a, who), (a.get("then") or {}, who + "'s then")):
                    if not isinstance(st, dict): bad(f"{what}: an object"); continue
                    if st.get("do") and st["do"] not in VOC["poses"]: bad(f"{what}: do {st['do']!r} is not a pose ({', '.join(VOC['poses'])})")
                    if st.get("face") and st["face"] not in VOC["faces"]: bad(f"{what}: face is one of {', '.join(VOC['faces'])}")
                    if st.get("hold") and st["hold"] not in VOC["items"]: bad(f"{what}: hold is one of {', '.join(VOC['items'])}")
                    if st.get("emote") and st["emote"] not in VOC["emotes"]: bad(f"{what}: emote is one of {' '.join(VOC['emotes'])}")
                    for f in ("at", "to"):
                        v = st.get(f)
                        if v is not None and not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v) and abs(v[0]) <= 14 and abs(v[1]) <= 12): bad(f"{what}: {f} is [x, z] in metres, x -14 to 14 and z -12 to 12")
                    ch = st.get("chest")
                    ok = ch is None or isinstance(ch, (int, float)) or (isinstance(ch, str) and (ch in CROWD_CHEST if mob else 0 < len(ch) <= 6)) or (isinstance(ch, list) and len(ch) == 2 and all(isinstance(x, (int, float)) for x in ch))
                    if not ok: bad(f"{what}: chest is a number, [from, to], " + ("or one of " + ", ".join(CROWD_CHEST) if mob else 'or a short word like "#1"'))
                    lk = st.get("look")
                    if isinstance(lk, str) and lk != "screen" and norm(lk) not in names: bad(f"{what}: look names {lk!r}, who is not among this shot's actors")
                if a.get("then") and a.get("say") and not said(vo, a["say"]): bad(f"{who}: say {a['say']!r} is not in the line, word for word")
                if a.get("say") and not a.get("then"): bad(f'{who}: "say" does nothing without "then" (what changes on those words)')
    return errs[:10]


def example():
    """The hand-made part 1 (story_part1.json), cut down to what a writer copies: each line with its shots."""
    S = json.load(open(os.path.join(HERE, "story_part1.json"), encoding="utf-8"))
    return [{k: s[k] for k in ("kind", "text", "vo", "shots") if k in s} for s in S["scenes"]]


if __name__ == "__main__" and sys.argv[1:] == ["demo"]:
    P1 = json.load(open(os.path.join(HERE, "story_part1.json"), encoding="utf-8"))
    assert check(P1) == [], check(P1)
    assert P1["scene_js"] == JS and all(s.get("shots") for s in P1["scenes"][:-1]) and len(example()) == len(P1["scenes"])
    assert said("It rose nine hundred percent.", "nine hundred") and said("They all hit zero.", "hit zero")
    assert norm("the narrator (I)") == "narrator" and norm("Mr Gold") == "mr gold" and said("It crashed to zero.", "crashed to") and not said("It crashed.", "zero")
    line = "Then every number in town crashed to zero."
    sc = lambda **q: {"scenes": [{"kind": "free", "vo": line, "shots": [dict({"place": "street", "cam": "close:Timmy", "actors": [{"who": "Timmy", "chest": 5}]}, **q)]}]}
    assert check(sc()) == []
    rs = lambda **k: {"scenes": [{"kind": "free", "vo": "The price fell to the moon.", "shots": [{"place": "square", "cam": "screen", "screen": dict({"title": "T", "real": 0, "from": 2, "to": 5}, **k)}]}]}
    C = [{"candles": [[1, 2, 1, 2, 0]] * 8}]
    assert check(rs(), C) == [] and check(rs(buy=3, sell=5, level=1.5), C) == [] and check(rs()) and check(rs(to=8), C) and check(rs(buy=7), C) and check(rs(chart="up"), C)
    for q, word in (({"place": "moon"}, "place"), ({"cam": "close:Maya"}, "not among"), ({"cam": "screen"}, "screen"), ({"sky": "green"}, "sky"), ({"fx": ["bang"]}, "fx"),
                    ({"actors": [{"who": "Timmy", "do": "fly"}]}, "pose"), ({"actors": [{"who": "Timmy", "at": [40, 0]}]}, "metres"), ({"actors": [{"who": "Timmy", "say": "moon", "then": {"chest": 0}}]}, "not in the line"),
                    ({"actors": [{"who": "Timmy", "hold": "sword"}]}, "hold"), ({"place": "room", "cam": "screen", "screen": {"text": "A|B"}, "actors": [{"who": "Timmy", "at": [-1.4, -1.2]}]}, "covers its words"), ({"crowd": {"n": 40}}, "crowd"), ({"plane": "rocket"}, "plane"), ({"sky_say": "banana"}, "sky_say")):
        e = check(sc(**q)); assert e and any(word in x for x in e), (q, e)
    assert any("shots" in x for x in check({"scenes": [{"kind": "free", "vo": line}]})) and check({"scenes": [{"kind": "outro", "vo": "Part 2 drops soon."}]}) == []
    print("ok")
