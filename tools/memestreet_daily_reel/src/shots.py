"""The scene library (the owner, 2026-11-08: "sometimes it still just looks ugly"): every acted scene is one of these shots,
composed once and polished, never a free arrangement. The writer picks a shot, casts its roles with props and words, and
ties its moments to phrases of the line:
  {"layout": "stage", "act": "clash", "cast": {"a": {"p": "truck", "label": "Delivery"}, "b": {"p": "dragon"}},
   "on": {"hit": "shut a motorway"}}
expand() turns that into the storyboard reel.html draws (actors on fixed slots and sizes, beats on the words), so the
positions, sizes, timing and effects are always the polished ones.   python3 src/shots.py   (self-check)
"""
UPRIGHT = ("candle", "chart", "question")                 # (never fly, fall or crash: the owner, 2026-11-08)

# name: what it acts out, roles (slot, size, moves?), moments (beats: verb, role, extras; "after" = seconds after the word)
SHOTS = {   # (the owner's ratings, 2026-11-08: no spray, crashes dramatic, a winner knocks the loser away, literal pictures)
    "rally_drop": {"for": "a price that rises and then drops, shown as a row of candles marching across the screen, climbing on one phrase and tumbling on the next (it rises, then it drops)",
                   "roles": {}, "layout": "updown",
                   "on": {"up": [], "down": []}},   # (the owner, round 5: many candles, not one)
    "rise_fall": {"for": "something shoots up, then crashes back down (a hyped price, a launch that flops)",
                  "roles": {"hero": ("mid", "m", True)},
                  "on": {"up": [("launch", "hero", {"to": "sky-mid"})], "down": [("fall", "hero", {"crash": True})]}},   # (a flier turns over or dives as it crashes; a landing stays upright)
    "clash": {"for": "one thing drives into another and knocks it back (a rival ship ramming a freighter, a runaway truck hitting a depot)",
              "roles": {"a": ("left", "m", True), "b": ("right", "m", False)},
              "on": {"hit": [("hit", "a", {"with": "b"})]}},
    "crash_landing": {"for": "something drops out of the sky just as another thing drives into it (an escaped dragon landing on a motorway as a truck arrives)",
                      "roles": {"a": ("left", "m", True), "b": ("sky-right", "m", True)},
                      "on": {"land": [("fall", "b", {}), ("hit", "a", {"with": "b", "after": .25})]}},
    "pour": {"for": "money, rain or fire streams from one thing into another, which grows (rentals paying the company, rain filling a reservoir)",
             "roles": {"source": ("left", "m", False), "pile": ("right", "s", False)},
             "on": {"pour": [("emit", "source", {"what": "$what", "with": "pile"}), ("grow", "pile", {"to": "m", "after": .6})]},
             "opts": {"what": ("coins", "coins|fire|hearts")}},
    "fill": {"for": "rain falls from a cloud straight down into what it fills (rain on demand filling a reservoir)",
             "roles": {"cloud": ("sky-mid", "m", False), "pile": ("mid", "m", False)},
             "on": {"rain": [("emit", "cloud", {"what": "rain", "with": "pile"})]}},
    "shield": {"for": "a threat strikes something that holds, and is thrown back (support holding against sellers, a stop-loss saving you)",
               "roles": {"guard": ("mid", "m", False), "threat": ("sky-right", "s", True)},
               "on": {"strike": [("hit", "threat", {"with": "guard"}), ("fling", "threat", {"to": "off-right", "after": .55})]}},
    "three_up": {"for": "three things, then the question (a quiz: three charts, three questions; three reasons)",
                 "roles": {"item1": ("left", "s", False), "item2": ("mid", "s", False), "item3": ("right", "s", False),
                           "topper": ("sky-mid", "s", False)},
                 "on": {"items": [("enter", "item1", {}), ("enter", "item2", {"after": .3}), ("enter", "item3", {"after": .6})],
                        "topper": [("grow", "topper", {"to": "m"})]}},
    "versus": {"for": "two things face off and the winner knocks the loser away, then takes the middle (patience vs rushing, buyers vs sellers)",
               "roles": {"left": ("left", "m", True), "right": ("right", "m", True)},
               "on": {"win": [("hit", "$winner", {"with": "$loser"}), ("fling", "$loser", {"to": "$off", "after": .55}),
                              ("move", "$winner", {"to": "mid", "after": 1.2})]},
               "opts": {"winner": ("left", "left|right")}},
    "count": {"for": "the thing a number is about swells big as the voice says the number (support held 24 times, 3 ways to earn)",
              "roles": {"hero": ("mid", "m", False)},
              "on": {"count": [("grow", "hero", {"to": "l"})]}},   # (the owner, round 2: no number tag, the voice says it)
    "arrive": {"for": "something lands and the people there react (a new drone landing and buyers loving it, money rolling in to a rocket)",
               "roles": {"hero": ("sky-mid", "m", True), "left": ("left", "s", False), "right": ("right", "s", False)},
               "on": {"arrive": [("fall", "hero", {})],
                      "cheer": [("emit", "left", {"what": "$what", "with": "hero", "after": .5}), ("emit", "right", {"what": "$what", "with": "hero", "after": .5})]},   # (both at once, after the landing)
               "opts": {"what": ("hearts", "hearts (love) or coins (money)")}},
    "reveal": {"for": "something hatches or breaks out (an egg hatching a baby dragon, a dragon breaking out of its cage, a crate opening)",
               "roles": {"inside": ("mid", "s", False), "shell": ("mid", "m", False)},   # (inside first: the shell's rim covers it, so it peeks out)
               "on": {"open": [("crack", "shell", {}), ("enter", "inside", {"after": .1}), ("grow", "inside", {"to": "m", "after": .35})]}},
}


def schema():
    """The shot list as the writer reads it."""
    out = []
    for n, S in SHOTS.items():
        opts = "".join(f', "{k}": {d[1]!r}' for k, d in S.get("opts", {}).items())
        out.append(f'  {n}: {S["for"]}. cast {", ".join(S["roles"])}; on {", ".join(S["on"])}{opts}')
    return "\n".join(out)


def expand(k, s, props):
    """Scene `s` with a "act": its actors and beats written in (layout stage). Returns what is wrong, [] when fine."""
    S = SHOTS.get(s.get("act"))
    if not S: return [f"scene {k}: shot must be one of {', '.join(SHOTS)}"]
    cast, on, errs = s.get("cast") or {}, s.get("on") or {}, []
    for r, (_, _, moves) in S["roles"].items():
        p = (cast.get(r) or {}).get("p")
        if p not in props: errs.append(f"scene {k}: shot {s['act']} needs cast.{r}.p, one of the props")
        elif moves and p in UPRIGHT: errs.append(f"scene {k}: a {p} never flies, falls or crashes; cast it in a role that stays put")
    for m in S["on"]:
        if not on.get(m): errs.append(f"scene {k}: shot {s['act']} needs on.{m}: the phrase of the line it happens on")
    opt = {o: s.get(o) if s.get(o) is not None else d[0] for o, d in S.get("opts", {}).items()}
    if "number" in opt and not any(c.isdigit() for c in str(opt["number"] or "")): errs.append(f"scene {k}: shot count needs \"number\" with the number in it")
    if "winner" in opt: opt["loser"] = "right" if opt["winner"] == "left" else "left"; opt["off"] = "off-" + opt["loser"]
    if errs: return errs
    sub = lambda v: opt.get(v[1:]) if isinstance(v, str) and v.startswith("$") else v
    if S.get("layout"):                                    # (a shot drawn by its own layout: its moments time the layout's props)
        s["layout"] = S["layout"]; s["props"] = [{"p": "candle", "color": "green", "label": "", "say": on[m]} for m in S["on"]]
        s.pop("actors", None); s.pop("beats", None); return []
    s["layout"] = "stage"; s["props"] = []
    drop = {"inside"} if s["act"] == "reveal" and cast.get("shell", {}).get("p") == "cage" else set()   # (seen through the bars)
    egg = s["act"] == "reveal" and cast.get("shell", {}).get("p") == "egg"   # (a hatchling only peeks its head out: the owner, round 3)
    s["actors"] = [{"id": r, "p": cast[r]["p"], "color": cast[r].get("color", "teal"), "at": at, "size": z,
                    "label": cast[r].get("label", "")} for r, (at, z, _) in S["roles"].items()]
    s["beats"] = [dict({"say": on[m], "do": v, "who": sub(who)}, **{x: sub(y) for x, y in ex.items()})
                  for m, bs in S["on"].items() for v, who, ex in bs if not (v == "enter" and sub(who) in drop) and not (egg and v == "grow")]
    return []


def expand_all(spec, props):
    """Every acted scene comes from the library: a scene with a shot is expanded; a free storyboard is refused."""
    errs = []
    for k, s in enumerate(spec.get("scenes") or []):
        if not s.get("act") and s.get("shot") in SHOTS: s["act"] = s.pop("shot")   # ("shot" is the video field: a library name there is moved)
        if s.get("act"): errs += expand(k, s, props)
        elif s.get("actors") or s.get("beats") or s.get("layout") == "stage":
            errs.append(f"scene {k}: acted scenes come from the shot library (\"act\", \"cast\", \"on\"), never free actors or beats")
    return errs


def demo():
    P = ["truck", "dragon", "coin", "chart", "question", "candle", "shield", "cloud", "person", "rocket", "cage", "egg"]
    s = {"act": "clash", "cast": {"a": {"p": "truck"}, "b": {"p": "dragon", "label": "Escaped"}}, "on": {"hit": "shut a motorway"}}
    assert expand(0, s, P) == [] and s["layout"] == "stage" and s["actors"][1]["label"] == "Escaped"
    assert s["beats"] == [{"say": "shut a motorway", "do": "hit", "who": "a", "with": "b"}]
    v = {"act": "versus", "winner": "right", "cast": {"left": {"p": "coin"}, "right": {"p": "rocket"}}, "on": {"win": "won"}}
    assert expand(0, v, P) == [] and v["beats"][0]["with"] == "left" and v["beats"][1] == {"say": "won", "do": "fling", "who": "left", "to": "off-left", "after": .55}
    r = {"act": "reveal", "cast": {"shell": {"p": "dragon"}, "inside": {"p": "rocket"}}, "on": {"open": "hatched"}}
    assert expand(0, r, P) == [] and [b["do"] for b in r["beats"]] == ["crack", "enter", "grow"]
    c = {"act": "reveal", "cast": {"shell": {"p": "cage"}, "inside": {"p": "dragon"}}, "on": {"open": "broke out"}}
    assert expand(0, c, P) == [] and [b["do"] for b in c["beats"]] == ["crack", "grow"]
    assert any("never flies" in e for e in expand(0, {"act": "rise_fall", "cast": {"hero": {"p": "candle"}}, "on": {"up": "a", "down": "b"}}, P))
    assert any("needs on.down" in e for e in expand(0, {"act": "rise_fall", "cast": {"hero": {"p": "rocket"}}, "on": {"up": "a"}}, P))
    assert expand(0, {"act": "count", "cast": {"hero": {"p": "coin"}}, "on": {"count": "x"}}, P) == []
    assert expand_all({"scenes": [{"layout": "stage", "actors": [{}]}]}, P)
    assert expand_all({"scenes": [{"layout": "pens", "props": [{}]}]}, P) == []
    m = {"scenes": [{"shot": "count", "cast": {"hero": {"p": "coin"}}, "on": {"count": "x"}}]}
    assert expand_all(m, P) == [] and m["scenes"][0]["act"] == "count" and "shot" not in m["scenes"][0]
    u = {"act": "rally_drop", "on": {"up": "rises", "down": "drops"}}
    assert expand(0, u, P) == [] and u["layout"] == "updown" and [p["say"] for p in u["props"]] == ["rises", "drops"]
    assert "three_up" in schema()
    print("ok")


if __name__ == "__main__":
    demo()
