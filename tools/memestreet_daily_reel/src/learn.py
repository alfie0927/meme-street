"""Why our best reels did well and our worst did badly, from Instagram's own numbers, turned into rules the writer reads
before every reel (the owner, 2026-11-13: "figure out why, and how they did better, and why some reels did so badly.
then collate that knowledge into better reels").

  python3 src/learn.py          read Instagram, update the ledger, and when due ask Claude why   (auto_reel.sh, once a day)
  python3 src/learn.py show     the rules the writer is following now, and the splits behind them
  python3 src/learn.py demo     the self-check, no network, no Claude

1. The ledger, state/reel_ledger.json: one row per posted reel, kept for good (work/ folders are cleaned, the ledger is not).
   What the reel WAS (format, opening line and on-screen words, its device, length, scenes, first scene's kind, whether it
   opens or captions with a question, the critic's scores, the hour) beside what Instagram measured (hold = 100 minus the skip
   rate, views, reach, shares, saves, likes, comments, seconds and percent watched). A reel is read from 24 hours old, read
   again for a week, then frozen; one shown fewer than 20 times is left out (the scoreboard's rules, src/format_scores.py).
2. The splits, in code: each feature's groups with their median hold, watched and sends. A group under 4 reels is only a
   hint: one reel's skip rate is good to about 5 points at our size, so a reason must hold across several reels.
3. Claude (one call, at most once a day, when 3 or more reels were scored since the last time or a week has passed) gets
   the ledger, the splits, the rules it wrote last time and the owner's rulebook headings, and answers: why each of the five
   best and five worst did as it did, and the rules for the next reels (each with its evidence, at most 15). The rules go to
   state/learned.md (make_spec.py learned() hands them to the writer), the reasons onto the ledger rows (own_reels.py shows
   them beside the best and worst openings), and what changed to state/learn_history.md for the owner.
It never touches the RULEBOOK (the owner's) or which formats are made (src/format_scores.py does that).
"""
import datetime, json, os, re, statistics, sys, time
from own_reels import insights, folders, age, load
from post_instagram import http, token, ig_id, HOST, V, ROOT

STATE = os.path.join(ROOT, "state")
LEDGER, LEARNED, HISTORY = (os.path.join(STATE, f) for f in ("reel_ledger.json", "learned.md", "learn_history.md"))
M = ["views", "reach", "shares", "saved", "likes", "comments", "total_interactions", "ig_reels_avg_watch_time", "reels_skip_rate"]
DAY, SHOWN, HINT, MAX_RULES, EACH, NEW, MIN_ROWS = 86400, 20, 4, 15, 5, 3, 6
PATTERNS = ("What the virality research found on other accounts (a lead to test on ours, not a fact about ours): winners move on "
            "frame 0, show something the viewer recognises at once, make one big element do something extraordinary before 3 "
            "seconds, land the claim word by word at about 1.2 to 1.6 s, speak the subject within 0.5 s, work on mute and are "
            "about the viewer, not about us. Losers open on a still card, an empty or abstract frame, small pale text, or a topic "
            "about the maker. Comments come when the reel asks one plain question the viewer can answer in a word.")
first = lambda s: re.split(r"(?<=[.?!])\s+", (s or "").strip())[0][:160]
med = lambda xs: round(statistics.median(xs), 1) if xs else None


def features(tl, caption, approved):
    """What a reel was, from its timeline (narrate.py or lab/silent.py), its caption and the critic's approval."""
    sc = tl.get("scenes") or [{}]; s0 = sc[0]; dev = tl.get("device") or {}
    cap = (caption or tl.get("caption") or "").strip()
    return {"title": tl.get("title"), "opening": first(s0.get("vo")), "on_screen": s0.get("text"), "opening_q": "?" in first(s0.get("vo")),
            "first_kind": s0.get("kind"), "device": {k: dev[k] for k in ("metaphor", "opening", "palette") if dev.get(k)} or None,
            "T": round(tl["T"], 1) if tl.get("T") else None, "scenes": len(sc), "caption_first": cap.split("\n")[0][:160],
            "caption_q": cap.split("\n")[0].rstrip().endswith("?"), "critic": (approved or {}).get("scores")}


def numbers(i, T):
    """Instagram's insights -> the ledger's measured fields."""
    r = {"skip": round(i["reels_skip_rate"], 1), "hold": round(100 - i["reels_skip_rate"], 1), "views": i.get("views") or 0,
         "reach": i.get("reach"), "shares": i.get("shares") or 0, "saved": i.get("saved") or 0, "likes": i.get("likes") or 0,
         "comments": i.get("comments") or 0, "watch_s": round((i.get("ig_reels_avg_watch_time") or 0) / 1000, 1)}
    if T: r["watched_pct"] = min(100, round(r["watch_s"] * 100 / T))
    if r["reach"]: r["sends_per_100"] = round(100 * r["shares"] / r["reach"], 1)
    return r


def bucket_len(T): return None if not T else "under 40 s" if T < 40 else "40 to 60 s" if T <= 60 else "over 60 s"


FEATURES = {"format": lambda r: r.get("format"), "length": lambda r: bucket_len(r.get("T")),
            "scenes": lambda r: None if not r.get("scenes") else "1 to 5" if r["scenes"] <= 5 else "6 to 8" if r["scenes"] <= 8 else "9 or more",
            "opens with a question": lambda r: r.get("opening_q"), "caption opens with a question": lambda r: r.get("caption_q"),
            "first scene kind": lambda r: r.get("first_kind"),
            "critic's content score": lambda r: None if not (r.get("critic") or {}).get("content") else "9 or 10" if r["critic"]["content"] >= 9 else "8 or less",
            "hour posted (UTC)": lambda r: (r.get("posted") or "")[11:13] or None,
            "weekday": lambda r: datetime.date.fromisoformat(r["posted"][:10]).strftime("%a") if r.get("posted") else None}


def splits(rows):
    """feature -> group -> {n, hold, watched, sends, hint?}: the median of each measure per group, groups with best hold first."""
    rows = [r for r in rows if r.get("hold") is not None]; out = {}
    for name, f in FEATURES.items():
        G = {}
        for r in rows:
            k = f(r)
            if k is not None: G.setdefault(str(k), []).append(r)
        if len(G) < 2: continue                                   # (one group says nothing)
        out[name] = {k: {"n": len(rs), "hold": med([r["hold"] for r in rs]), "watched": med([r["watched_pct"] for r in rs if r.get("watched_pct") is not None]),
                         "sends": med([r["sends_per_100"] for r in rs if r.get("sends_per_100") is not None]), **({"hint": True} if len(rs) < HINT else {})}
                     for k, rs in sorted(G.items(), key=lambda kv: -statistics.median(r["hold"] for r in kv[1]))}
    return out


def ranked(rows):
    """Scored rows, best first: hold, then the share of the reel watched."""
    return sorted((r for r in rows if r.get("hold") is not None), key=lambda r: (-r["hold"], -(r.get("watched_pct") or 0)))


def prompt(L, rulebook):
    """Everything the analyst gets, in one message."""
    rows = sorted(L["rows"].items(), key=lambda kv: kv[1].get("posted") or "")[-60:]
    keep = ("format", "posted", "title", "opening", "on_screen", "opening_q", "first_kind", "device", "T", "scenes", "caption_first",
            "caption_q", "critic", "hold", "watched_pct", "watch_s", "views", "sends_per_100", "saved", "likes", "comments")
    R = [{"id": m, **{k: r[k] for k in keep if r.get(k) is not None}} for m, r in rows if r.get("hold") is not None]
    rk = ranked([dict(r, id=m) for m, r in rows]); k = min(EACH, len(rk) // 2)
    heads = [h for h in re.findall(r"^#{2,3} (.+)$", rulebook, re.M)]
    return ("You study the Instagram Reels of Meme Street (memestreet.net), a free stock market game with fictional companies, "
            "to find out why some reels kept their viewers and others lost them, and to turn that into rules for the writer of "
            "the next reels. Measures: hold = percent still watching after 3 seconds (100 minus Instagram's skip rate: the main "
            "one), watched_pct = average share of the reel's length watched, sends_per_100 = shares per 100 people reached. "
            "At our size one reel's hold is good to about 5 points, so a reason must hold across several reels: compare the best "
            "with the worst, and use the splits (groups under 4 reels are marked hint). Look at what the viewer saw and heard in "
            "the first seconds (opening, on_screen, first_kind, device), the length, the subject, the caption.\n\n"
            f"Median hold {med([r['hold'] for r in R])}, median watched {med([r['watched_pct'] for r in R if r.get('watched_pct') is not None])}% over {len(R)} reels.\n\n"
            f"THE REELS, oldest first:\n{json.dumps(R, ensure_ascii=False)}\n\n"
            f"THE {k} BEST: {[r['id'] for r in rk[:k]]}\nTHE {k} WORST: {[r['id'] for r in rk[::-1][:k]]}\n\n"
            f"THE SPLITS:\n{json.dumps(splits([r for _, r in rows]), ensure_ascii=False)}\n\n" + PATTERNS + "\n\n"
            "THE RULES YOU WROTE LAST TIME (keep those the numbers still back, change or retire the rest):\n" +
            (L.get("rules_text") or "(none yet)") + "\n\n"
            "The owner's rulebook has these sections, and its rules always win: never write a rule against them, never change "
            "the format choice (a scoreboard does that) or the posting schedule: " + "; ".join(heads) + "\n\n"
            "Reply with JSON only:\n{\"best\": [{\"id\": \"...\", \"why\": \"one sentence: what in this reel kept people\"}], "
            "\"worst\": [{\"id\": \"...\", \"why\": \"one sentence: what lost them\"}], "
            f"\"rules\": [{{\"rule\": \"one sentence the writer can act on in the next script\", \"evidence\": \"n reels, hold X against Y\", "
            "\"strength\": \"strong or weak\"}], \"retired\": [\"a rule from last time the numbers no longer back\"], "
            "\"note\": \"three sentences for the owner: what wins, what loses, what the next reels change\"}\n"
            f"At most {MAX_RULES} rules. strong = 4 or more reels on each side and 5 points or more apart; weak = fewer reels but "
            "still 5 points or more apart, and it starts with 'Try'. A gap under 5 points is noise: write no rule from it. The "
            "caption is read after the first seconds, so judge a caption choice on comments and sends, never on hold. Rules "
            "about craft (what is on screen, what is said, when, how long), never about facts.")


def apply(ans, L, today):
    """Claude's answer -> the new learned.md text and a history entry; the reasons go onto the ledger rows. Raises on a bad answer."""
    rules = [r for r in ans["rules"] if isinstance(r, dict) and str(r.get("rule", "")).strip()]
    if not rules: raise ValueError("no rules in the answer")
    rules = sorted(rules, key=lambda r: r.get("strength") != "strong")[:MAX_RULES]
    for x in (ans.get("best") or []) + (ans.get("worst") or []):
        if isinstance(x, dict) and str(x.get("id")) in L["rows"] and x.get("why"): L["rows"][str(x["id"])]["why"] = str(x["why"])[:300]
    n = sum(r.get("hold") is not None for r in L["rows"].values())
    body = "\n".join(f"- {r['rule'].strip()} ({r.get('evidence', '').strip() or 'no evidence given'})" for r in rules)
    md = f"# What Instagram's numbers taught us ({today}, {n} reels)\n{body}\n"
    hist = (f"\n## {today} ({n} reels)\n{ans.get('note', '').strip()}\n\nRules now:\n{body}\n" +
            ("Retired:\n" + "\n".join(f"- {x}" for x in ans.get("retired") or []) + "\n" if ans.get("retired") else ""))
    return md, hist


def due(L, now):
    n = sum(r.get("hold") is not None for r in L["rows"].values())
    return n >= MIN_ROWS and (n - L.get("analysed_n", 0) >= NEW or now - L.get("analysed_at", 0) >= 7 * DAY)


def save(L):
    os.makedirs(STATE, exist_ok=True)
    json.dump(L, open(LEDGER + ".tmp", "w", encoding="utf-8"), indent=1, ensure_ascii=False); os.replace(LEDGER + ".tmp", LEDGER)


def pull(L, now):
    """Instagram's last 60 posts into the ledger: new reels with what they were, numbers re-read for a week."""
    tok = token(); uid = ig_id(tok); where = folders(); got = 0
    posts = http("GET", f"{HOST}/{V}/{uid}/media", {"fields": "id,caption,media_product_type,timestamp", "limit": 60, "access_token": tok}).get("data", [])
    for p in posts:
        mid = str(p["id"]); a = age(p, now); r = L["rows"].get(mid)
        if p.get("media_product_type") != "REELS" or a < DAY or (r and r.get("hold") is not None and a > 7 * DAY): continue
        if not r or not r.get("opening"):                         # (what the reel was: once, while its work folder is here)
            d, w = where.get(mid, (None, None)); tl, cat, ok = {}, None, None
            try: tl = load(os.path.join(w, "timeline.json"))
            except (OSError, ValueError, TypeError): pass
            try: cat = load(os.path.join(w, "brief.json")).get("category")
            except (OSError, ValueError, TypeError): pass
            try: ok = load(os.path.join(d, "approved.json"))
            except (OSError, ValueError, TypeError): pass
            r = {**(r or {}), "slot": os.path.basename(d) if d else None, "format": cat or tl.get("type"), "posted": p["timestamp"][:16],
                 **features(tl, p.get("caption"), ok)}
            if not r.get("opening"): r["opening"] = first((p.get("caption") or "").split("\n")[0])
        i = insights(mid, tok, M); time.sleep(0.3)
        if i.get("reels_skip_rate") is None or (i.get("views") or 0) < SHOWN: L["rows"][mid] = r; continue
        L["rows"][mid] = {**r, **numbers(i, r.get("T")), "pulled": time.strftime("%F %T", time.gmtime())}; got += 1
    return got


def main():
    now = time.time(); L = load(LEDGER) if os.path.exists(LEDGER) else {"rows": {}}
    got = pull(L, now); save(L)
    n = sum(r.get("hold") is not None for r in L["rows"].values())
    print(time.strftime("%F %T UTC", time.gmtime()), f"{got} reels read, {n} scored in the ledger")
    if not due(L, now): return print("no analysis today (it needs", NEW, "new scored reels or a week)")
    from make_spec import claude_cli
    rb = os.path.join(ROOT, "RULEBOOK.md"); rulebook = open(rb, encoding="utf-8").read() if os.path.exists(rb) else ""
    try:
        raw = claude_cli([{"role": "user", "content": prompt(L, rulebook)}], "You answer with JSON only.",
                         os.environ.get("REEL_LEARN_MODEL", "sonnet"), wait=False)
        md, hist = apply(json.loads(re.search(r"\{.*\}", raw, re.S).group(0)), L, time.strftime("%F"))
    except (SystemExit, ValueError, AttributeError, KeyError, TypeError) as e:
        return print("analysis skipped today, learned.md unchanged:", str(e)[:300])   # (a plan limit or a bad answer: tomorrow again)
    open(LEARNED + ".tmp", "w", encoding="utf-8").write(md); os.replace(LEARNED + ".tmp", LEARNED)
    with open(HISTORY, "a", encoding="utf-8") as f: f.write(hist)
    L.update(rules_text=md, analysed_at=now, analysed_n=n); save(L)
    print(md)


def show():
    L = load(LEDGER) if os.path.exists(LEDGER) else {"rows": {}}
    print(open(LEARNED, encoding="utf-8").read() if os.path.exists(LEARNED) else "(no rules yet)")
    rk = ranked(L["rows"].values())
    for title, rs in (("best", rk[:EACH]), ("worst", rk[::-1][:EACH])):
        print(f"\nThe {title}:")
        for r in rs: print(f"  hold {r['hold']:>5}  watched {r.get('watched_pct', '-'):>4}%  {(r.get('format') or '?')[:18]:18}  {r.get('opening', '')[:60]}" + (f"\n      why: {r['why']}" if r.get("why") else ""))
    for name, G in splits(L["rows"].values()).items():
        print(f"\n{name}:")
        for k, x in G.items(): print(f"  {k[:24]:24} n {x['n']:>3}  hold {x['hold']:>5}  watched {x['watched'] if x['watched'] is not None else '-':>5}  sends {x['sends'] if x['sends'] is not None else '-':>4}" + ("  (hint)" if x.get("hint") else ""))


def demo():
    tl = load(os.path.join(ROOT, "src", "scenes", "fixtures", "boat", "timeline.json"))
    f = features(tl, "Ever drilled a hole in your own boat?\nmore", {"scores": {"content": 9}})
    assert f["title"] == "Your Boat Has Holes" and f["T"] == 31.3 and f["scenes"] == len(tl["scenes"]) and f["caption_q"] and f["device"]["metaphor"].startswith("a rowing boat"), f
    i = {"reels_skip_rate": 40, "views": 200, "reach": 100, "shares": 2, "ig_reels_avg_watch_time": 15650}
    assert numbers(i, 31.3) == {"skip": 40, "hold": 60, "views": 200, "reach": 100, "shares": 2, "saved": 0, "likes": 0, "comments": 0,
                                "watch_s": 15.7, "watched_pct": 50, "sends_per_100": 2.0}
    row = lambda fmt, hold, q, T=30: {"format": fmt, "hold": hold, "opening_q": q, "T": T, "posted": "2026-11-12T09:00", "opening": fmt + str(hold)}
    rows = {str(k): r for k, r in enumerate([row("A", 70, True), row("A", 66, True), row("A", 64, True), row("A", 68, True),
                                              row("B", 40, False, 80), row("B", 42, False, 80), row("B", 38, False, 80), row("C", 50, False)])}
    S = splits(rows.values())
    assert list(S["format"]) == ["A", "C", "B"] and S["format"]["A"] == {"n": 4, "hold": 67, "watched": None, "sends": None}, S["format"]
    assert S["format"]["B"].get("hint") and S["opens with a question"]["True"]["n"] == 4 and "weekday" not in S   # (one weekday: no split)
    L = {"rows": rows}; p = prompt(L, "# Rules\n## Style\nx\n### Chart quiz\ny")
    assert "Style; Chart quiz" in p and "is noise" in p and "THE 4 BEST: ['0', '3', '1', '2']" in p and "(none yet)" in p, p[-900:]
    assert due(L, 0) and not due(dict(L, analysed_n=8, analysed_at=0), 6 * DAY) and due(dict(L, analysed_n=8, analysed_at=0), 7 * DAY)
    ans = {"best": [{"id": "0", "why": "a question on frame 0"}], "worst": [{"id": "9", "why": "not ours"}],
           "rules": [{"rule": "Try a shorter cut", "evidence": "3 reels", "strength": "weak"}, {"rule": "Open with a question", "evidence": "4 v 4, hold 67 v 40", "strength": "strong"}] +
                    [{"rule": f"r{k}", "strength": "weak"} for k in range(20)], "retired": ["Open on the logo"], "note": "Questions win."}
    md, hist = apply(ans, L, "2026-11-13")
    lines = md.splitlines()
    assert lines[0] == "# What Instagram's numbers taught us (2026-11-13, 8 reels)" and lines[1] == "- Open with a question (4 v 4, hold 67 v 40)" and len(lines) == 1 + MAX_RULES, md
    assert rows["0"]["why"] == "a question on frame 0" and "9" not in rows and "Retired:\n- Open on the logo" in hist and "Questions win." in hist
    for bad in ({"rules": []}, {"rules": [{"rule": " "}]}, {}):
        try: apply(bad, L, "x"); raise AssertionError(bad)
        except (ValueError, KeyError): pass
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    demo() if a == ["demo"] else show() if a == ["show"] else main()
