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
3. Claude (one call a day, when a reel was scored since the last time: the owner, 2026-11-14, "check the instagram analytics
   every day and see what has done well, what has stalled, and why") gets
   the ledger, the splits, the rules it wrote last time and the owner's rulebook headings, and answers: why each of the five
   best and five worst did as it did, and the rules for the next reels (each with its evidence, at most 15). The rules go to
   state/learned.md (make_spec.py learned() hands them to the writer), the reasons onto the ledger rows (own_reels.py shows
   them beside the best and worst openings), and what changed to state/learn_history.md for the owner.
4. Every day, too: the best reels of the last week and the STALLED ones (a reel under the median that gained under 3% views
   in a day: Instagram stopped showing it), each with Claude's why, in state/daily_report.md (`learn.py show` prints it).
   Each row keeps its views at every daily read (`trail`, [hours old, views]) for this.
It never touches the RULEBOOK (the owner's) or which formats are made (src/format_scores.py does that).
"""
import datetime, json, os, re, statistics, sys, time
from own_reels import insights, folders, age, load
from post_instagram import http, token, ig_id, HOST, V, ROOT

STATE = os.path.join(ROOT, "state")
LEDGER, LEARNED, HISTORY, REPORT = (os.path.join(STATE, f) for f in ("reel_ledger.json", "learned.md", "learn_history.md", "daily_report.md"))
M = ["views", "reach", "shares", "saved", "likes", "comments", "total_interactions", "ig_reels_avg_watch_time", "reels_skip_rate"]
DAY, SHOWN, HINT, MAX_RULES, EACH, NEW, MIN_ROWS = 86400, 20, 4, 15, 5, 1, 6
PATTERNS = ("What the virality research found on other accounts (a lead to test on ours, not a fact about ours): winners move on "
            "frame 0, show something the viewer recognises at once, make one big element do something extraordinary before 3 "
            "seconds, land the claim word by word at about 1.2 to 1.6 s, speak the subject within 0.5 s, work on mute and are "
            "about the viewer, not about us. Losers open on a still card, an empty or abstract frame, small pale text, or a topic "
            "about the maker. Comments come when the reel asks one plain question the viewer can answer in a word. The niche study of "
            "2026-11-17 (research/niche_2026-11-17.md: 4,500 videos ranked against their own accounts, 101 watched) found the winners "
            "share: one subject filling the frame with labels landing as spoken, the claim kept on screen the whole reel, big two-to-"
            "four-word captions, a first sentence naming one concrete thing, something resolving at the end, content exact enough to "
            "argue with; pace, cuts, length and title wording did not separate winners from flops there.")
first = lambda s: re.split(r"(?<=[.?!])\s+", (s or "").strip())[0][:160]
med = lambda xs: round(statistics.median(xs), 1) if xs else None


def features(tl, caption, approved, brief=None):
    """What a reel was, from its timeline (narrate.py or lab/silent.py), its caption, the critic's approval and its brief: the
    opening, and (the owner, 2026-11-17: "what kept people watching?") the beats, one line per scene, so the analyst can say
    where the body held or lost them, and the hook formula the writer was handed (make_spec.brief(): facts.hook_shape)."""
    sc = tl.get("scenes") or [{}]; s0 = sc[0]; dev = tl.get("device") or {}
    cap = (caption or tl.get("caption") or "").strip()
    hs = (((brief or {}).get("ask") or {}).get("facts") or {}).get("hook_shape") or {}
    return {"title": tl.get("title"), "opening": first(s0.get("vo")), "on_screen": s0.get("text"), "opening_q": "?" in first(s0.get("vo")),
            "beats": [f"{round(s.get('t0', 0))}s {first(s.get('vo'))[:70]}" for s in sc if s.get("vo")][:24], "hook_formula": hs.get("name"),
            "first_kind": s0.get("kind"), "device": {k: dev[k] for k in ("metaphor", "opening", "palette") if dev.get(k)} or None,
            "T": round(tl["T"], 1) if tl.get("T") else None, "scenes": len(sc), "caption_first": cap.split("\n")[0][:160],
            "caption_q": cap.split("\n")[0].rstrip().endswith("?"), "critic": (approved or {}).get("scores")}


def numbers(i, T):
    """Instagram's insights -> the ledger's measured fields."""
    r = {"skip": round(i["reels_skip_rate"], 1), "hold": round(100 - i["reels_skip_rate"], 1), "views": i.get("views") or 0,
         "reach": i.get("reach"), "shares": i.get("shares") or 0, "saved": i.get("saved") or 0, "likes": i.get("likes") or 0,
         "comments": i.get("comments") or 0, "watch_s": round((i.get("ig_reels_avg_watch_time") or 0) / 1000, 1)}
    if T: r["watched_pct"] = min(100, round(r["watch_s"] * 100 / T))
    if r["reach"]: r["sends_per_100"] = round(100 * r["shares"] / r["reach"], 1); r["likes_per_100"] = round(100 * r["likes"] / r["reach"], 1)
    return r


def account(L, tok, uid, now):
    """The account's own day, kept as a trail of 60: followers, and who the reels reached in the last day and the last 29 days
    (followers against strangers). On 2026-11-17 the 29-day reach was 12,214 people, 8 of them followers: every view is a
    stranger's first look, so a reel leaves the 100-200 view plateau only on what strangers do in it (the owner's question)."""
    row = {"date": time.strftime("%F", time.gmtime(now))}
    try: row["followers"] = http("GET", f"{HOST}/{V}/{uid}", {"fields": "followers_count", "access_token": tok}).get("followers_count")
    except SystemExit: pass
    for days, key in ((1, "day"), (29, "month")):
        try:
            r = http("GET", f"{HOST}/{V}/{uid}/insights", {"metric": "reach", "period": "day", "metric_type": "total_value", "breakdown": "follow_type",
                                                           "since": int(now - days * DAY), "until": int(now), "access_token": tok})
            tv = r["data"][0]["total_value"]; bd = {x["dimension_values"][0]: x["value"] for b in tv.get("breakdowns", []) for x in b.get("results", [])}
            row[key] = {"reach": tv.get("value"), "followers": bd.get("FOLLOWER", 0), "strangers": bd.get("NON_FOLLOWER", 0)}
        except (SystemExit, KeyError, IndexError, TypeError): pass
    L["account"] = ([a for a in L.get("account") or [] if a.get("date") != row["date"]] + [row])[-60:]


def account_line(L):
    """What the analyst is told about the account, from its latest row ("" before the first)."""
    a = (L.get("account") or [{}])[-1]; m = a.get("month") or {}
    if not a.get("followers") and not m: return ""
    who = (f" In the last 29 days the reels reached {m.get('reach')} people: {m.get('followers')} followers and {m.get('strangers')} strangers"
           " (the followers see next to nothing, so every view is a stranger's first look, and a reel wins a wider audience only on what "
           "strangers do in it: hold, watch time, likes per 100 reached, sends per 100 reached)." if m else "")
    return f"THE ACCOUNT ({a.get('date')}): {a.get('followers')} followers.{who}\n\n"


def breakouts(rows):
    """The reels that left the plateau: over twice the median views (ids, best first), and the median."""
    v = sorted(r["views"] for r in rows if r.get("views") is not None); m = v[len(v) // 2] if v else 0
    return sorted((r for r in rows if m and r.get("views", 0) > 2 * m), key=lambda r: -r["views"]), m


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


def stalled(rows):
    """Reels that stopped gaining views (under 3%, or 5 views, between two daily reads) while under the median views."""
    mv = med([r["views"] for r in rows if r.get("views")]) or 0
    return [r for r in rows if len(r.get("trail") or []) >= 2 and r["trail"][-1][0] - r["trail"][-2][0] >= 20
            and r["trail"][-1][1] - r["trail"][-2][1] <= max(5, .03 * r["trail"][-2][1]) and r["trail"][-1][1] < mv]


def recent(rows, now, days=7):
    """The scored reels posted in the last `days`, best first."""
    cut = time.strftime("%Y-%m-%dT%H:%M", time.gmtime(now - days * DAY))
    return ranked(r for r in rows if (r.get("posted") or "") >= cut)


def ranked(rows):
    """Scored rows, best first: hold, then the share of the reel watched."""
    return sorted((r for r in rows if r.get("hold") is not None), key=lambda r: (-r["hold"], -(r.get("watched_pct") or 0)))


def prompt(L, rulebook, now=None):
    """Everything the analyst gets, in one message."""
    rows = sorted(L["rows"].items(), key=lambda kv: kv[1].get("posted") or "")[-60:]
    keep = ("format", "posted", "title", "opening", "on_screen", "opening_q", "first_kind", "device", "hook_formula", "beats", "T", "scenes",
            "caption_first", "caption_q", "critic", "hold", "watched_pct", "watch_s", "views", "sends_per_100", "likes_per_100", "saved", "likes", "comments")
    R = [{"id": m, **{k: r[k] for k in keep if r.get(k) is not None}} for m, r in rows if r.get("hold") is not None]
    rk = ranked([dict(r, id=m) for m, r in rows]); k = min(EACH, len(rk) // 2)
    idr = [dict(r, id=m) for m, r in L["rows"].items()]
    wk = [r["id"] for r in recent(idr, now or time.time())][:EACH]; st = [r["id"] for r in stalled(idr)]
    # (the views trail: [hours old, views] at each daily read)
    R = [dict(x, trail=L["rows"][x["id"]]["trail"]) if L["rows"][x["id"]].get("trail") else x for x in R]
    heads = [h for h in re.findall(r"^#{2,3} (.+)$", rulebook, re.M)]
    bo, mv = breakouts(R)
    return (account_line(L) + "You study the Instagram Reels of Meme Street (memestreet.net), a free stock market game with fictional companies, "
            "to find out why some reels kept their viewers and others lost them, and to turn that into rules for the writer of "
            "the next reels. Measures: hold = percent still watching after 3 seconds (100 minus Instagram's skip rate: the main "
            "one), watched_pct = average share of the reel's length watched, sends_per_100 = shares per 100 people reached. "
            "At our size one reel's hold is good to about 5 points, so a reason must hold across several reels: compare the best "
            "with the worst, and use the splits (groups under 4 reels are marked hint). Two questions, kept apart (the owner): THE HOOK: "
            "what the viewer saw and heard in the first seconds (opening, on_screen, first_kind, device, hook_formula) and what in it "
            "held them or lost them (hold). THE BODY: what kept them watching after the hook, or where they left (watched_pct and "
            "watch_s against the beats, one line per scene with its start second: the stake raised, a turn, a payoff held back, a "
            "running counter; or background, a list, a lesson that starts early). Then the length, the subject, the caption.\n\n"
            f"Median hold {med([r['hold'] for r in R])}, median watched {med([r['watched_pct'] for r in R if r.get('watched_pct') is not None])}% over {len(R)} reels.\n\n"
            f"THE REELS, oldest first:\n{json.dumps(R, ensure_ascii=False)}\n\n"
            f"THE {k} BEST: {[r['id'] for r in rk[:k]]}\nTHE {k} WORST: {[r['id'] for r in rk[::-1][:k]]}\n"
            f"THE BREAKOUTS (over twice the median of {mv} views; a reel's views stop growing after its first day, so these are the ones "
            f"Instagram carried past its first batch of strangers): {[(r['id'], r['views'], r.get('hold'), r.get('watched_pct')) for r in bo] or 'none yet'}\n"
            f"THE BEST OF THE LAST 7 DAYS: {wk}\nSTALLED (under the median views and gained under 3% in the last day: Instagram "
            f"stopped showing them; trail = [hours old, views]): {st or 'none'}\n\n"
            f"THE SPLITS:\n{json.dumps(splits([r for _, r in rows]), ensure_ascii=False)}\n\n" + PATTERNS + "\n\n"
            "THE RULES YOU WROTE LAST TIME (keep those the numbers still back, change or retire the rest):\n" +
            (L.get("rules_text") or "(none yet)") + "\n\n"
            "The owner's rulebook has these sections, and its rules always win: never write a rule against them, never change "
            "the format choice (a scoreboard does that) or the posting schedule: " + "; ".join(heads) + "\n\n"
            "Reply with JSON only:\n{\"best\": [{\"id\": \"...\", \"hook\": \"one sentence: what about its hook was so interesting\", "
            "\"kept\": \"one sentence: what kept people watching after it\"}], "
            "\"worst\": [{\"id\": \"...\", \"hook\": \"one sentence: what in the hook lost them\", \"kept\": \"one sentence: where the body lost the rest\"}], "
            "\"week\": [{\"id\": \"one of the best of the last 7 days\", \"why\": \"one sentence: why it did well\"}], "
            "\"stalled\": [{\"id\": \"one of the stalled\", \"why\": \"one sentence: why viewers stopped and Instagram stopped showing it\"}], "
            "\"breakouts\": \"two or three sentences for the writer: what the breakouts shared, in the hook and in the body, that the plateau reels lacked; the numbers that marked the line (hold, watched)\", "
            f"\"rules\": [{{\"rule\": \"one sentence the writer can act on in the next script\", \"evidence\": \"n reels, hold X against Y\", "
            "\"strength\": \"strong or weak\", \"part\": \"hook (the first seconds) or body (what keeps them watching after it)\"}], "
            "\"retired\": [\"a rule from last time the numbers no longer back\"], "
            "\"note\": \"three sentences for the owner: what did well this week, what stalled, what the next reels change\"}\n"
            f"At most {MAX_RULES} rules. strong = 4 or more reels on each side and 5 points or more apart; weak = fewer reels but "
            "still 5 points or more apart, and it starts with 'Try'. A gap under 5 points is noise: write no rule from it. The "
            "caption is read after the first seconds, so judge a caption choice on comments and sends, never on hold. Rules "
            "about craft (what is on screen, what is said, when, how long), never about facts. Write body rules as well as hook "
            "rules: a hook that holds and a body that empties is half a reel.")


def apply(ans, L, today):
    """Claude's answer -> the new learned.md text and a history entry; the reasons go onto the ledger rows. Raises on a bad answer."""
    rules = [r for r in ans["rules"] if isinstance(r, dict) and str(r.get("rule", "")).strip()]
    if not rules: raise ValueError("no rules in the answer")
    rules = sorted(rules, key=lambda r: r.get("strength") != "strong")[:MAX_RULES]
    for x in (ans.get("best") or []) + (ans.get("worst") or []) + (ans.get("week") or []) + (ans.get("stalled") or []):
        if not isinstance(x, dict) or str(x.get("id")) not in L["rows"]: continue
        why = str(x.get("why") or "").strip() or " ".join(str(x[k]).strip() for k in ("hook", "kept") if x.get(k))   # (hook and kept, as one reason for own_reels.py and the report)
        if why: L["rows"][str(x["id"])]["why"] = x["why"] = why[:400]
    n = sum(r.get("hold") is not None for r in L["rows"].values())
    line = lambda r: f"- {r['rule'].strip()} ({r.get('evidence', '').strip() or 'no evidence given'})"
    part = lambda r: "body" if str(r.get("part", "")).lower().startswith("body") else "hook"
    body = ((f"## Leaving the 100-200 view plateau\n{str(ans['breakouts']).strip()}\n" if str(ans.get("breakouts") or "").strip() else "") +
            "## The hook: what held them past 3 seconds\n" + ("\n".join(line(r) for r in rules if part(r) == "hook") or "- (no hook rule yet)") +
            "\n## The body: what kept them watching\n" + ("\n".join(line(r) for r in rules if part(r) == "body") or "- (no body rule yet)"))
    md = f"# What Instagram's numbers taught us ({today}, {n} reels)\n{body}\n"
    def lines(xs):
        out = []
        for x in xs or []:
            r = L["rows"].get(str(x.get("id"))) if isinstance(x, dict) else None
            if r: out.append(f"- {r.get('title') or r.get('opening', '')[:50]} ({r.get('format') or '?'}, {(r.get('posted') or '')[:10]}): "
                             f"hold {r.get('hold')}, {r.get('views')} views. {x.get('why', '')}")
        return "\n".join(out) or "- none"
    report = (f"# Instagram, {today}\n{ans.get('note', '').strip()}\n\n## Did well this week\n{lines(ans.get('week'))}\n\n"
              f"## Stalled\n{lines(ans.get('stalled'))}\n")
    hist = (f"\n## {today} ({n} reels)\n{ans.get('note', '').strip()}\n\nDid well this week:\n{lines(ans.get('week'))}\n"
            f"Stalled:\n{lines(ans.get('stalled'))}\n\nRules now:\n{body}\n" +
            ("Retired:\n" + "\n".join(f"- {x}" for x in ans.get("retired") or []) + "\n" if ans.get("retired") else ""))
    return md, hist, report


def due(L, now):
    n = sum(r.get("hold") is not None for r in L["rows"].values())
    return n >= MIN_ROWS and (n - L.get("analysed_n", 0) >= NEW or now - L.get("analysed_at", 0) >= 7 * DAY)


def save(L):
    os.makedirs(STATE, exist_ok=True)
    json.dump(L, open(LEDGER + ".tmp", "w", encoding="utf-8"), indent=1, ensure_ascii=False); os.replace(LEDGER + ".tmp", LEDGER)


def pull(L, now):
    """Instagram's last 60 posts into the ledger: new reels with what they were, numbers re-read for a week."""
    tok = token(); uid = ig_id(tok); where = folders(); got = 0
    account(L, tok, uid, now)
    posts = http("GET", f"{HOST}/{V}/{uid}/media", {"fields": "id,caption,media_product_type,timestamp", "limit": 60, "access_token": tok}).get("data", [])
    for p in posts:
        mid = str(p["id"]); a = age(p, now); r = L["rows"].get(mid)
        if p.get("media_product_type") != "REELS" or a < DAY or (r and r.get("hold") is not None and a > 7 * DAY): continue
        d, w = where.get(mid, (None, None))
        if not r or not r.get("opening") or (not r.get("beats") and w and os.path.isdir(w)):   # (what the reel was: once, while its work folder is here; a row made before the beats existed gets them while it still can)
            tl, br, ok = {}, {}, None
            try: tl = load(os.path.join(w, "timeline.json"))
            except (OSError, ValueError, TypeError): pass
            try: br = load(os.path.join(w, "brief.json"))
            except (OSError, ValueError, TypeError): pass
            try: ok = load(os.path.join(d, "approved.json"))
            except (OSError, ValueError, TypeError): pass
            r = {**(r or {}), "slot": os.path.basename(d) if d else None, "format": br.get("category") or tl.get("type") or (r or {}).get("format"),
                 "posted": p["timestamp"][:16], **features(tl, p.get("caption"), ok, br)}
            if not r.get("opening"): r["opening"] = first((p.get("caption") or "").split("\n")[0])
        i = insights(mid, tok, M); time.sleep(0.3)
        if i.get("reels_skip_rate") is None or (i.get("views") or 0) < SHOWN: L["rows"][mid] = r; continue
        nr = numbers(i, r.get("T"))
        L["rows"][mid] = {**r, **nr, "pulled": time.strftime("%F %T", time.gmtime()), "trail": ((r.get("trail") or []) + [[round(a / 3600), nr["views"]]])[-10:]}; got += 1
    return got


def main():
    now = time.time(); L = load(LEDGER) if os.path.exists(LEDGER) else {"rows": {}}
    got = pull(L, now); save(L)
    n = sum(r.get("hold") is not None for r in L["rows"].values())
    print(time.strftime("%F %T UTC", time.gmtime()), f"{got} reels read, {n} scored in the ledger")
    if not due(L, now): return print("no analysis today (no reel was scored since the last one)")
    from make_spec import claude_cli
    rb = os.path.join(ROOT, "RULEBOOK.md"); rulebook = open(rb, encoding="utf-8").read() if os.path.exists(rb) else ""
    try:
        raw = claude_cli([{"role": "user", "content": prompt(L, rulebook, now)}], "You answer with JSON only.",
                         os.environ.get("REEL_LEARN_MODEL", "sonnet"), wait=False)
        md, hist, report = apply(json.loads(re.search(r"\{.*\}", raw, re.S).group(0)), L, time.strftime("%F"))
    except (SystemExit, ValueError, AttributeError, KeyError, TypeError) as e:
        return print("analysis skipped today, learned.md unchanged:", str(e)[:300])   # (a plan limit or a bad answer: tomorrow again)
    open(LEARNED + ".tmp", "w", encoding="utf-8").write(md); os.replace(LEARNED + ".tmp", LEARNED)
    with open(HISTORY, "a", encoding="utf-8") as f: f.write(hist)
    open(REPORT + ".tmp", "w", encoding="utf-8").write(report); os.replace(REPORT + ".tmp", REPORT)
    L.update(rules_text=md, analysed_at=now, analysed_n=n); save(L)
    print(md)


def show():
    L = load(LEDGER) if os.path.exists(LEDGER) else {"rows": {}}
    print(open(REPORT, encoding="utf-8").read() if os.path.exists(REPORT) else "(no daily report yet)")
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
    assert len(f["beats"]) == sum(1 for s in tl["scenes"] if s.get("vo")) and f["beats"][0].startswith("0s ") and f["hook_formula"] is None, f["beats"][:2]
    assert features(tl, "", None, {"ask": {"facts": {"hook_shape": {"name": "The Statistic"}}}})["hook_formula"] == "The Statistic"
    i = {"reels_skip_rate": 40, "views": 200, "reach": 100, "shares": 2, "ig_reels_avg_watch_time": 15650}
    assert numbers(i, 31.3) == {"skip": 40, "hold": 60, "views": 200, "reach": 100, "shares": 2, "saved": 0, "likes": 0, "comments": 0,
                                "watch_s": 15.7, "watched_pct": 50, "sends_per_100": 2.0, "likes_per_100": 0.0}
    assert account_line({}) == "" and "419 followers" in account_line({"account": [{"date": "2026-11-17", "followers": 419}]})
    al = account_line({"account": [{"date": "2026-11-17", "followers": 419, "month": {"reach": 12214, "followers": 8, "strangers": 12192}}]})
    assert "12214 people: 8 followers and 12192 strangers" in al and "stranger's first look" in al, al
    row = lambda fmt, hold, q, T=30: {"format": fmt, "hold": hold, "opening_q": q, "T": T, "posted": "2026-11-12T09:00", "opening": fmt + str(hold)}
    rows = {str(k): r for k, r in enumerate([row("A", 70, True), row("A", 66, True), row("A", 64, True), row("A", 68, True),
                                              row("B", 40, False, 80), row("B", 42, False, 80), row("B", 38, False, 80), row("C", 50, False)])}
    S = splits(rows.values())
    assert list(S["format"]) == ["A", "C", "B"] and S["format"]["A"] == {"n": 4, "hold": 67, "watched": None, "sends": None}, S["format"]
    assert S["format"]["B"].get("hint") and S["opens with a question"]["True"]["n"] == 4 and "weekday" not in S   # (one weekday: no split)
    L = {"rows": rows}; p = prompt(L, "# Rules\n## Style\nx\n### Chart quiz\ny")
    assert "Style; Chart quiz" in p and "is noise" in p and "THE 4 BEST: ['0', '3', '1', '2']" in p and "(none yet)" in p, p[-900:]
    assert due(L, 0) and not due(dict(L, analysed_n=8, analysed_at=0), 6 * DAY) and due(dict(L, analysed_n=7, analysed_at=0), DAY)
    st = [{"views": 100, "trail": [[30, 90], [54, 92]]}, {"views": 400, "trail": [[30, 300], [54, 400]]}, {"views": 50, "trail": [[30, 50]]},
          {"views": 300, "trail": [[30, 299], [54, 300]]}]
    assert stalled(st) == [st[0]], stalled(st)                # (gained 2 under the median; growing; one read; stalled above the median)
    assert [r["opening"] for r in recent(rows.values(), time.mktime((2026, 11, 14, 0, 0, 0, 0, 0, 0)))][:2] == ["A70", "A68"]
    assert "STALLED" in p and "BEST OF THE LAST 7 DAYS" in p and "THE BREAKOUTS" in p and "breakouts" in p
    bo, mv = breakouts([{"id": "a", "views": 100}, {"id": "b", "views": 1200}, {"id": "c", "views": 90}, {"id": "d", "views": 201}, {"id": "e", "views": 500}])
    assert mv == 201 and [r["id"] for r in bo] == ["b", "e"] and breakouts([]) == ([], 0), (bo, mv)
    ans = {"best": [{"id": "0", "hook": "a question on frame 0", "kept": "the answer held to the end"}], "worst": [{"id": "9", "why": "not ours"}],
           "week": [{"id": "3", "why": "it moved on frame 0"}], "stalled": [{"id": "5", "why": "a still chart"}], "breakouts": "They held 64 or more.",
           "rules": [{"rule": "Try a shorter cut", "evidence": "3 reels", "strength": "weak", "part": "body"}, {"rule": "Open with a question", "evidence": "4 v 4, hold 67 v 40", "strength": "strong"}] +
                    [{"rule": f"r{k}", "strength": "weak"} for k in range(20)], "retired": ["Open on the logo"], "note": "Questions win."}
    md, hist, report = apply(ans, L, "2026-11-13")
    assert "## Did well this week\n- A68 (A, 2026-11-12): hold 68, None views. it moved on frame 0" in report and "a still chart" in report, report
    assert rows["5"]["why"] == "a still chart" and "Stalled:\n- B42" in hist, hist
    lines = md.splitlines()
    assert lines[0] == "# What Instagram's numbers taught us (2026-11-13, 8 reels)" and lines[1:3] == ["## Leaving the 100-200 view plateau", "They held 64 or more."], md
    assert lines[3:5] == ["## The hook: what held them past 3 seconds", "- Open with a question (4 v 4, hold 67 v 40)"] and len(lines) == 5 + MAX_RULES, md
    assert "## Leaving" not in apply(dict(ans, breakouts=""), L, "x")[0]
    assert "## The body: what kept them watching\n- Try a shorter cut (3 reels)" in md, md
    assert rows["0"]["why"] == "a question on frame 0 the answer held to the end" and "9" not in rows and "Retired:\n- Open on the logo" in hist and "Questions win." in hist
    for bad in ({"rules": []}, {"rules": [{"rule": " "}]}, {}):
        try: apply(bad, L, "x"); raise AssertionError(bad)
        except (ValueError, KeyError): pass
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    demo() if a == ["demo"] else show() if a == ["show"] else main()
