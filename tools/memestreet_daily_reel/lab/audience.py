"""Lab (on the side: the reel pipeline never runs this yet): a simulated Instagram audience.

A panel of personas (lab/personas.json) watches a finished reel the way the feed serves it - the first frame and the
first three seconds decide, then the rest - and each says how likely they are to keep watching, how far they'd get,
and whether they'd like, comment, send, save or follow. The weighted panel gives the reel's predicted hold at 3 s,
average watch, and engagement per reach (Instagram's top signals: watch time, sends per reach, likes per reach).
`calibrate` checks predictions against the reels' real insights; until they agree, the panel only ranks cuts.

  python3 lab/audience.py pack <work> <out> <dir>   the feed pack (ffmpeg; run where the reel is)
  python3 lab/audience.py packvideo <mp4> <dir>     the same from a posted video alone (posts.json gives its caption)
  python3 lab/audience.py packtl <timeline> <dir>   feed.json for frames made by lab/frames.py --sheet (template tests)
  python3 lab/audience.py watch <dir>...            the panel's prediction (claude CLI) -> <dir>/audience.json
  python3 lab/audience.py pair <dirA> <dirB>        which of two cuts the panel would rather watch
  python3 lab/audience.py calibrate                 predictions against real insights (lab/data/insights.json)
  python3 lab/audience.py textpairs <tsv> <subs>    blind best-vs-worst pairs from public Shorts: the panel's accuracy
  python3 lab/audience.py demo                      self-check
The judge is the 13-persona panel; AUDIENCE_PANEL=generic swaps in one plain viewer, the baseline. 2026-11-07: on 40
blind pairs of public Shorts scripts the plain viewer was right 65%, the panel 52%; on our own 17 reels (with frames)
the panel's score tracked real likes at Spearman 0.55, the plain viewer's at 0.09. Real skip rates will decide.
"""
import glob, json, math, os, random, re, subprocess, sys, time

LAB = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(LAB, "data")
PERSONAS = json.load(open(os.path.join(LAB, "personas.json"), encoding="utf-8"))["personas"]
if os.environ.get("AUDIENCE_PANEL") == "generic":   # (one plain viewer: the baseline; 65% on 40 blind Shorts scripts against the panel's 52%,
                                                   #  but 0.09 against the panel's 0.55 on our own 17 reels' likes: real skip rates decide)
    PERSONAS = [{"id": "viewer", "w": 1.0, "who": "A typical Instagram user scrolling their Reels feed: Instagram shows this "
                 "reel to people whose recent viewing looks like its topic, plus some it is testing it on."}]
HOOK_T = [0, 0.5, 1, 1.5, 2, 3]

PANEL = """You simulate Instagram users scrolling Reels on their phones. Each persona below sees the reel in their feed:
it autoplays from the first frame with sound on (most people keep sound on for Reels, some scroll muted and read the
captions). In the first second or two they decide to keep watching or swipe; if they stay, they keep deciding, and
leave the moment it stops paying off. Judge as each person, from their own interests and patience, not as a critic.

Be calibrated, not kind. Typical numbers for a reel from a small, unknown account: about half of viewers swipe within
the first 3 seconds; those who stay watch on average 40-60% of a 30-45 s reel; likes are about 1-4% of viewers, sends
(sharing in a DM) 0.1-1%, saves 0.2-1%, comments under 0.5%, follows 0.1-0.5%. A great reel beats these; a weak one
falls well below. Most reels are swiped by most people.

You see the reel through feed.json (what is said and shown when, the post caption, the audio) and images: the first
3 seconds frame by frame (exactly what the feed shows first) and the whole reel at one frame every 1.5 s. Read them all.
On a phone Instagram lays the account name, the post caption and the buttons over the bottom fifth of the frame and
the right edge, so a dark band there is normal and is not seen as empty.

PERSONAS:
{personas}

Reply with JSON only:
{"personas": [{"id": "...", "p_stop3": 0.0-1.0 (chance they are still watching at 3 s), "leaves_at": seconds or null
   (when they would most likely swipe if they stayed past 3 s; null = to the end), "watch_frac": 0.0-1.0 (expected share
   of the reel watched if they stayed past 3 s), "p_rewatch": 0-1, "p_like": 0-1, "p_comment": 0-1, "p_send": 0-1,
   "p_save": 0-1, "p_follow": 0-1, "why": "one sentence in their voice: what made them stay or go, naming the frame or line"}],
 "first_frame": "what a scroller sees in frame 1 and whether it stops the thumb",
 "biggest_drop": {"at": seconds, "why": "..."},
 "fixes": ["the 3 changes that would keep the most people watching, most important first"]}"""


FFMPEG = os.environ.get("FFMPEG", "ffmpeg")


def ff(*a):
    subprocess.run([FFMPEG, "-v", "error", "-y", *a], check=True)


def secs(mp4):
    e = subprocess.run([FFMPEG, "-i", mp4], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", e).groups(); return int(h) * 3600 + int(m) * 60 + float(s)


def frames(mp4, d, T):
    os.makedirs(d, exist_ok=True); parts = []
    for k, t in enumerate(HOOK_T):
        p = os.path.join(d, f"_h{k}.jpg"); ff("-ss", f"{t:.2f}", "-i", mp4, "-frames:v", "1", "-vf", "scale=360:-1", p); parts.append(p)
    ff(*sum([["-i", p] for p in parts], []), "-filter_complex", f"hstack={len(parts)}", os.path.join(d, "first_3s.jpg"))
    for p in parts: os.remove(p)
    ff("-i", mp4, "-vf", f"fps=1/1.5,scale=180:-1,tile=8x{math.ceil(T / 1.5 / 8)}", "-frames:v", "1", os.path.join(d, "whole_reel.jpg"))


IMAGES = {"first_3s.jpg": f"frames at {HOOK_T} s, left to right (360 px wide each; the phone shows them full screen)",
          "whole_reel.jpg": "one frame every 1.5 s, left to right, top to bottom"}
AUDIO = "a synthetic female voice-over (ElevenLabs or Kokoro), a quiet music bed under it, small sound effects on reveals"


def pack(work, out, d):
    """What the feed serves: the first 3 seconds frame by frame, the whole reel, what is said and shown when."""
    R = json.load(open(os.path.join(work, "timeline.json")))
    frames(os.path.join(out, "reel.mp4"), d, R["T"])
    return feed(R, os.path.join(work, "caption.txt"), d)


def feed(R, cap, d):
    """feed.json: what is said and shown when (the images are made by frames(), or lab/frames.py --sheet for a template test)."""
    T = R["T"]
    words = [(w, round(a, 2)) for s in R["scenes"] for w, (a, _) in zip(s.get("text_words") or [], s.get("wt") or []) if a < 3]
    feed = {"length_secs": round(T, 1), "format": R.get("type"), "title": R.get("title"),
            "post_caption_first_line": open(cap, encoding="utf-8").read().split("\n")[0] if os.path.exists(cap) else "",
            "audio": AUDIO,
            "words_in_first_3s": words,
            "timeline": [{"from": round(s["t0"], 1), "to": round(s["t1"], 1), "kind": s["kind"], "said": s["vo"],
                          "on_screen": {k: s[k] for k in ("head", "text", "options", "layout") if s.get(k)}} for s in R["scenes"]],
            "images": IMAGES}
    json.dump(feed, open(os.path.join(d, "feed.json"), "w"), indent=1)
    return feed


def packvideo(mp4, d):
    """A posted reel with no timeline: the frames carry the burned-in captions (what is said)."""
    T = secs(mp4); frames(mp4, d, T); mid = os.path.basename(mp4).split(".")[0]
    post = next((p for p in json.load(open(os.path.join(DATA, "posts.json"))) if p["id"] == mid), {})
    feed = {"length_secs": round(T, 1), "post_caption_first_line": (post.get("caption") or "").split("\n")[0], "audio": AUDIO,
            "said": "read the burned-in captions in the frames", "images": IMAGES}
    json.dump(feed, open(os.path.join(d, "feed.json"), "w"), indent=1)
    return feed


def claude(req, system, cwd, model=None):
    r = subprocess.run(["claude", "-p", "--output-format", "text", "--model", model or os.environ.get("AUDIENCE_MODEL", "sonnet"),
                        "--append-system-prompt", system, "--allowedTools", "Read",
                        "--disallowedTools", "Bash,Edit,Write,WebFetch,WebSearch,Task,NotebookEdit"],
                       input=req, capture_output=True, text=True, timeout=900, cwd=cwd, encoding="utf-8",
                       env={k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"})   # (an API key would be billed instead)
    if r.returncode: raise SystemExit("claude failed: " + (r.stderr or r.stdout)[-400:])
    m = re.search(r"\{.*\}", r.stdout, re.S)
    return json.loads(m.group(0))


def panel_text():
    return "\n".join(f"- {p['id']} (weight {p['w']}): {p['who']}" for p in PERSONAS)


def aggregate(rows, T):
    """The panel's weighted prediction per reach (per person shown the reel)."""
    w = {p["id"]: p["w"] for p in PERSONAS}; rows = [r for r in rows if r.get("id") in w]
    W = sum(w[r["id"]] for r in rows) or 1
    avg = lambda f: sum(w[r["id"]] * f(r) for r in rows) / W
    hold = avg(lambda r: float(r["p_stop3"]))
    watch = avg(lambda r: float(r["p_stop3"]) * float(r["watch_frac"]) + (1 - float(r["p_stop3"])) * min(1, 1.5 / T))
    per = {k: round(avg(lambda r: float(r.get("p_" + k, 0))), 4) for k in ("like", "comment", "send", "save", "follow", "rewatch")}
    # ponytail: uncalibrated weights (watch first, then sends and likes, as Instagram ranks); `calibrate` replaces them once insights exist
    score = 100 * (0.5 * hold + 0.3 * watch + 0.1 * min(1, per["send"] / 0.01) + 0.1 * min(1, per["like"] / 0.04))
    return {"hold_3s": round(hold, 3), "skip_rate": round(1 - hold, 3), "avg_watch_frac": round(watch, 3),
            "avg_watch_secs": round(watch * T, 1), **{k + "_per_reach": v for k, v in per.items()}, "score": round(score, 1)}


def watch(d, model=None):
    feed = json.load(open(os.path.join(d, "feed.json")))
    res = claude("Read feed.json in this folder, then Read every image it lists, then reply with the JSON.",
                 PANEL.replace("{personas}", panel_text()), d, model)
    res["predicted"] = aggregate(res.get("personas", []), feed["length_secs"])
    res["when"] = time.strftime("%F %T UTC", time.gmtime()); res["model"] = model or os.environ.get("AUDIENCE_MODEL", "sonnet")
    json.dump(res, open(os.path.join(d, "audience.json"), "w"), indent=1)
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "predictions.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"pack": os.path.basename(os.path.normpath(d)), "when": res["when"], "model": res["model"], **res["predicted"]}) + "\n")
    return res


PAIR = """You simulate Instagram users scrolling Reels. Two cuts, A and B, are in the folders A/ and B/ (each has
feed.json and the images it lists: the first 3 seconds frame by frame and the whole reel). Each persona below meets
one of them in their feed, cold. For each persona say which cut they would watch longer, and which they would be more
likely to like, send or follow from. Judge as each person, not as a critic; ties are allowed only when truly equal.

PERSONAS:
{personas}

Reply with JSON only:
{"personas": [{"id": "...", "watch_longer": "A|B|tie", "engage_more": "A|B|tie", "why": "one sentence"}],
 "verdict": "which cut wins and the one reason that decides it"}"""


def pair(a, b, model=None, flip=None):
    """Which of two cuts the panel prefers (the order is shuffled so neither gets a position advantage; `both` asks
    twice, once each way round, and averages)."""
    flip = random.random() < 0.5 if flip is None else flip; first, second = (b, a) if flip else (a, b)
    tmp = os.path.join(DATA, "pair"); os.makedirs(tmp, exist_ok=True)
    for name, src in (("A", first), ("B", second)):
        dst = os.path.join(tmp, name); os.makedirs(dst, exist_ok=True)
        for f in glob.glob(os.path.join(src, "*")):
            if f.endswith((".json", ".jpg")) and not f.endswith("audience.json"):
                open(os.path.join(dst, os.path.basename(f)), "wb").write(open(f, "rb").read())
    res = claude("Read A/feed.json and B/feed.json, then every image they list, then reply with the JSON.", PAIR.replace("{personas}", panel_text()), tmp, model)
    w = {p["id"]: p["w"] for p in PERSONAS}; unflip = lambda x: {"A": "B", "B": "A"}.get(x, x) if flip else x
    share = {k: round(sum(w.get(r["id"], 0) for r in res["personas"] if unflip(r.get(k)) == "A"), 3) for k in ("watch_longer", "engage_more")}
    print(json.dumps({"A": a, "B": b, "share_preferring_A": share, "panel_saw_as_A": first, "verdict": res.get("verdict", "")}, indent=1))
    return share


TEXTPAIRS = """You simulate Instagram/YouTube Shorts viewers. Below are pairs of short finance videos; in each pair both came
from the SAME channel (same audience, same follower count). You get what was said with times, the length and the title.
For each pair, judge which one beat that channel's usual views by more: which hook stops more people in the first
seconds and which video keeps them watching and sharing. Think as the personas below would, then decide.

PERSONAS:
{personas}

Reply with JSON only: {"pairs": [{"pair": n, "winner": "A|B", "confidence": 0.5-1.0, "why": "one sentence"}]}"""


def words_json3(f):
    """YouTube auto-captions (json3) -> [(word, start seconds)]."""
    ws = []
    for e in json.load(open(f, encoding="utf-8")).get("events", []):
        for g in e.get("segs") or []:
            w = (g.get("utf8") or "").strip()
            if w: ws.append((w, round((e.get("tStartMs", 0) + g.get("tOffsetMs", 0)) / 1000, 2)))
    return ws


def textpairs(tsv, subs, model=None, per_call=10):
    """The panel against reality: for each channel, its best and worst short (by multiple over the channel median) as a
    blind pair; the share it calls right is its pairwise accuracy on scripts and hooks (50% = no better than a coin)."""
    import csv
    rows = [r for r in csv.DictReader(open(tsv, encoding="utf-8"), delimiter="\t")]
    have = lambda r: glob.glob(os.path.join(subs, r["url"].rstrip("/").split("/")[-1].split("=")[-1] + "*.json3"))
    by = {}
    for r in rows:
        if have(r): by.setdefault(r["account"], []).append(r)
    pairs = []
    for acc, rs in by.items():                          # (each channel's two best against its two worst, where clearly apart)
        rs.sort(key=lambda r: float(r["multiple"])); k = min(2, len(rs) // 2)
        pairs += [(hi, lo) for hi in rs[-k:] for lo in rs[:k] if float(hi["multiple"]) >= 1.5 * float(lo["multiple"])]
    random.seed(7); right = n = 0; out = []
    show = lambda r: {"title": r.get("title", ""), "length_secs": r.get("duration_s"),
                      "said": " ".join(f"{w}@{t}" if t < 3 else w for w, t in words_json3(have(r)[0]))[:2500]}
    for k in range(0, len(pairs), per_call):
        chunk = pairs[k:k + per_call]; flips = [random.random() < 0.5 for _ in chunk]
        body = "\n\n".join(f"PAIR {j}:\nA: {json.dumps(show(lo if f else hi))}\nB: {json.dumps(show(hi if f else lo))}"
                           for j, ((hi, lo), f) in enumerate(zip(chunk, flips)))
        res = claude(body + "\n\nReply with the JSON.", TEXTPAIRS.replace("{personas}", panel_text()), DATA, model)
        for x in res.get("pairs", []):
            j = int(x["pair"]); hi_is = "B" if flips[j] else "A"; ok = x.get("winner") == hi_is
            right += ok; n += 1; out.append({"account": chunk[j][0]["account"], "right": ok, "conf": x.get("confidence"), "why": x.get("why")})
    json.dump(out, open(os.path.join(DATA, f"textpairs-{os.environ.get('AUDIENCE_PANEL', 'personas')}.json"), "w"), indent=1)
    print(f"pairwise accuracy {right}/{n} = {right / max(1, n):.0%} (50% is a coin toss)")


def both(a, b, model=None):
    """The pair asked both ways round; the share of the panel (by weight) preferring a."""
    s1, s2 = pair(a, b, model, False), pair(a, b, model, True)
    avg = {k: round((s1[k] + s2[k]) / 2, 3) for k in s1}
    print(f"BOTH ORDERS: share preferring {a}: {avg}")
    return avg


def spearman(x, y):
    rk = lambda v: [sorted(v).index(e) + (v.count(e) - 1) / 2 for e in v]
    a, b = rk(list(x)), rk(list(y)); n = len(a); ma, mb = sum(a) / n, sum(b) / n
    cov = sum((p - ma) * (q - mb) for p, q in zip(a, b)); va = sum((p - ma) ** 2 for p in a); vb = sum((q - mb) ** 2 for q in b)
    return cov / math.sqrt(va * vb) if va and vb else 0.0


def calibrate():
    """Predictions against what really happened: rank agreement per metric (Spearman), over every reel with both."""
    ins = json.load(open(os.path.join(DATA, "insights.json")))["posts"]
    pred = {}
    for line in open(os.path.join(DATA, "predictions.jsonl"), encoding="utf-8"): r = json.loads(line); pred[r["pack"]] = r
    media = {}
    for f in glob.glob(os.path.join(os.path.dirname(LAB), "queue", "*", "posted.json")) + glob.glob(os.path.join(os.path.dirname(LAB), "out", "*", "posted.json")):
        media[json.load(open(f))["media_id"]] = os.path.basename(os.path.dirname(f))
    rows = []
    for p in ins:
        k = media.get(p["id"]); r = pred.get(p["id"]) or pred.get(k) or pred.get("auto-" + str(k))   # (packs are named by media id or slot)
        if r and "views" in p.get("insights", {}): rows.append((r, p["insights"]))
    if len(rows) < 6: return print(f"{len(rows)} reels have both a prediction and real insights; need 6+")
    per = lambda k: lambda i: (i.get(k) or 0) / max(1, i.get("reach") or 0)
    for a, name, real in (("skip_rate", "reels_skip_rate", lambda i: i.get("reels_skip_rate") or 0),
                          ("avg_watch_secs", "ig_reels_avg_watch_time", lambda i: i.get("ig_reels_avg_watch_time") or 0),
                          ("send_per_reach", "shares per reach", per("shares")), ("like_per_reach", "likes per reach", per("likes")),
                          ("score", "views", lambda i: i.get("views") or 0)):
        print(f"{a:>16} vs {name:<24} rho {spearman([r[a] for r, _ in rows], [real(i) for _, i in rows]):+.2f}  (n={len(rows)})")


def demo():
    rows = [{"id": p["id"], "p_stop3": 0.5, "watch_frac": 0.5, "p_like": 0.02, "p_send": 0.005} for p in PERSONAS]
    a = aggregate(rows, 30)
    assert a["hold_3s"] == 0.5 and abs(a["avg_watch_frac"] - (0.25 + 0.5 * 0.05)) < 1e-3 and a["like_per_reach"] == 0.02, a
    assert abs(sum(p["w"] for p in PERSONAS) - 1) < 1e-6, "persona weights must sum to 1"
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0 and spearman([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "demo": demo()
    elif a[0] == "pack": pack(a[1], a[2], a[3])
    elif a[0] == "packvideo": packvideo(a[1], a[2])
    elif a[0] == "packtl": feed(json.load(open(a[1], encoding="utf-8")), a[3] if len(a) > 3 else "", a[2])   # (after lab/frames.py <timeline> <page> <dir>/ --sheet; [caption.txt])
    elif a[0] == "watch":
        for d in a[1:]: r = watch(d); print(os.path.basename(os.path.normpath(d)), json.dumps(r["predicted"]), "|", r.get("biggest_drop"))
    elif a[0] == "pair": pair(a[1], a[2])
    elif a[0] == "both": both(a[1], a[2])
    elif a[0] == "calibrate": calibrate()
    elif a[0] == "textpairs": textpairs(a[1], a[2])
