"""Add the impact sounds to a voiced timeline and point its sound files at this computer: python sounds.py <reel root> <work>
The times are worked out the way scene.js works them out (api.at: when a phrase of the scene's line is said)."""
import json, os, re, sys
root, work = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
p = os.path.join(work, "timeline.json"); R = json.load(open(p, encoding="utf-8")); S = R["scenes"]
nk = lambda w: re.sub(r"[^a-z0-9%$.]", "", str(w).lower())
def at(k, phrase, default=None):
    s = S[k]; P = [x for x in map(nk, phrase.split()) if x]; W = [nk(x) for x in s.get("text_words", [])]
    for j in range(len(W) - len(P) + 1):
        if all(W[j + m] == w or W[j + m].startswith(w) for m, w in enumerate(P)):
            return s["wt"][j][0]
    assert default is not None, (k, phrase); return default
sfx = lambda n: os.path.join(root, "assets", f"sfx_{n}.wav")
vs = lambda k: S[k]["vs"]
t_out = vs(0) - .05; t4 = t_out + .9; t33 = max(at(0, "33"), t4 + 1)
t_adm, t_wed, t_rep = at(1, "admitted"), at(1, "Wednesday"), at(1, "reported a second")
t_thu, t_step = at(2, "Thursday"), at(2, "stepped down")
t_fell, t_400, t_back = at(3, "fell"), at(3, "400"), at(3, "won back")
t_sell, t_hold = at(4, "sell"), at(4, "hold")
t_ms, t_hit, t_pr, t_1k = at(5, "Meme Street"), at(5, "news hits"), at(6, "Practise", vs(6)), at(6, "1,000")
add = [("pop", t_out + .3), ("pop", t_out + .6), ("boom", t4), ("thud", t4 + .5),          # the calendar flips, the throw, the jacket lands
       ("tick", t33), ("tick", t33 + .15), ("tick", t33 + .3), ("chime", t33 + .6),        # YEARS races and locks
       ("thud", t_adm), ("pop", t_wed), ("thud", t_rep), ("pop", t_thu)]
add += [("tick", t_step + k * 1.9 / 6 + .28) for k in range(6)]                           # six steps down
add += [("boom", t_fell), ("tick", t_400), ("tick", t_400 + .2), ("tick", t_400 + .4), ("tick", t_400 + .6), ("chime", t_back + .3),
        ("pop", t_sell), ("pop", t_hold), ("whoosh", t_ms - .1), ("boom", t_hit), ("boom", t_pr + .25), ("chime", t_1k + .7)]
vo = [[os.path.join(work, "vo", os.path.basename(f)), a] for f, a in R["vo"] if "/vo/" in f.replace("\\", "/")]
assert len(vo) == len(S), (len(vo), len(S))
R["vo"] = sorted(vo + [[sfx(n), round(t, 3)] for n, t in add], key=lambda x: x[1])
for f, _ in R["vo"]: assert os.path.exists(f), f
json.dump(R, open(p, "w", encoding="utf-8"), ensure_ascii=False)
print(len(add), "sounds added;", "throw at", round(t4, 2), "| 33 at", round(t33, 2), "| fell at", round(t_fell, 2), "| hit at", round(t_hit, 2))
