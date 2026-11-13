"""A reel on a REALLY big real headline, made and posted at once (the owner, 2026-11-12: "scan news constantly and when
something REALLY big comes out, run the reel", linked to Meme Street). news_watch.sh runs `watch` every 20 minutes.

  python3 src/news_reel.py watch          one pass: read the feeds (free); only when one story is in several outlets is
                                          Claude asked whether it is really big; if so it is researched, written, fact-checked,
                                          sent through the film critic and queued to post now
  python3 src/news_reel.py feeds          today's stories that are in several outlets, as `watch` sees them (free, no Claude)
  python3 src/news_reel.py make "<story>" skip the scan: research this story and make its reel (the same checks);
                                          NEWS_DRY=1 stops before the queue (the approved reel stays in out/news-<time>)
  python3 src/news_reel.py demo           the self-check, no network

What keeps a reel about real people honest (the first one, 2026-11-12, was made by hand to these rules):
- the story must be in NEWS_MIN_OUTLETS outlets' feeds before anything is asked, and a researcher must then find it in three
  major outlets; every claim keeps its status (confirmed, admitted, reported by whom) and its outlet, and what is only
  alleged is left out of the reel altogether;
- never a death, a disaster, violence, war, a crime against a person, health, a child or an election; nobody named but
  the public figures at the centre; no ticker symbol, no advice on the real share, no prediction;
- a separate fact check reads the script against the fact pack before the voice is made and again after the critic's
  rewrite; one failed check after a fix holds the reel (nothing posts);
- at most NEWS_MAX_PER_DAY a day (1), never the same story twice in 10 days; `touch state/news_off` stops it.
"""
import datetime, email.utils, html, json, os, re, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
STATE = os.path.join(ROOT, "state", "news_reels.json")
MIN_OUTLETS = int(os.environ.get("NEWS_MIN_OUTLETS", "4")); MAX_PER_DAY = int(os.environ.get("NEWS_MAX_PER_DAY", "1"))
FRESH, ASK_AGAIN, COVERED, JUDGES_A_DAY = 20 * 3600, 6 * 3600, 10 * 86400, 12
TRIES = int(os.environ.get("NEWS_TRIES", "2"))            # (drafts a held story gets: each is a whole reel of the plan's usage)
CATEGORY = "Market news"
FEEDS = {   # (free, no key; each answered from the reel server on 2026-11-12)
    "google": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "google-business": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
    "bbc": "https://feeds.bbci.co.uk/news/rss.xml", "bbc-business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "guardian": "https://www.theguardian.com/business/rss", "wsj": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "ft": "https://www.ft.com/rss/home", "cnbc": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "bloomberg": "https://feeds.bloomberg.com/markets/news.rss", "nyt": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "abc": "https://abcnews.go.com/abcnews/moneyheadlines", "marketwatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "npr": "https://feeds.npr.org/1006/rss.xml", "techcrunch": "https://techcrunch.com/feed/", "fortune": "https://fortune.com/feed/"}
STOP = set("""a an the and or but of to in on at for from by with as is are was were be been it its this that these those his her their our your
after before over under into out up down off amid amidst than then when while who what why how where which will would could should may might can
says said say report reports reported new news live update updates latest today week year years day days first last more most less least big
stock stocks share shares market markets price prices fall falls fell rise rises rose jump jumps surge surges drop drops slide slides plunge plunges
gain gains loss losses record high low deal deals plan plans talks billion million trillion percent company companies firm firms chief executive
ceo boss business economy economic bank banks investors investor trading trade wall street world global here about just now still back away
could gets get makes make made take takes took sees see seen set sets hits hit near amid against between during since until what's here's
watch video opinion analysis explainer explained things know need means mean inside biggest best worst top
monday tuesday wednesday thursday friday saturday sunday january february march april june july august september october november december""".split())
EXCLUDE = ("Never: a death, a disaster, an attack, war, a crime against a person, someone's health, anything about a child, an election or "
           "party politics (a market crash or spike that one of them caused may be told, as the market's story), a rumour no major outlet stands behind.")
TOK = re.compile(r"[A-Za-z][A-Za-z'’&-]*|\d[\d.,]*%?")
now = lambda: time.time()
stamp = lambda: datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M UTC")
say = lambda *a: print(stamp(), *a, flush=True)


# ---------------------------------------------------------------------------------------------------- the feeds (free)
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"})
    return urllib.request.urlopen(req, timeout=12).read(2_000_000).decode("utf-8", "ignore")


def items(feed, xml, t=None, n=20):
    """A feed's first `n` headlines of the last 20 hours: [{feed, outlet, title, link}]. Read with patterns, not an XML
    parser (a feed is someone else's file). Google's titles end in " - Outlet": that outlet is the one that counts."""
    t = t or now(); out = []
    for it in re.findall(r"<item\b.*?</item>", xml, re.S)[:n]:
        g = lambda tag: html.unescape(re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", (re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", it, re.S) or [None, ""])[1], flags=re.S)).strip()
        title, link, when = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", g("title"))), g("link"), g("pubDate")
        try:
            if when and t - email.utils.parsedate_to_datetime(when).timestamp() > FRESH: continue
        except (TypeError, ValueError): pass
        outlet = feed.split("-")[0]
        if feed.startswith("google") and " - " in title: title, outlet = title.rsplit(" - ", 1); outlet = re.sub(r"[^a-z0-9]", "", outlet.lower())[:20] or "google"
        if len(title) > 12: out.append({"feed": feed, "outlet": outlet, "title": title, "link": link})
    return out


def terms(title):
    """(names, words): the capitalised words that are not everyday news words, and every word that carries meaning."""
    ws = [w.strip("'’-&") for w in TOK.findall(title)]
    low = lambda w: re.sub(r"['’]s$", "", w.lower())
    return ({low(w) for w in ws if w[:1].isupper() and len(w) > 2 and low(w) not in STOP},
            {low(w) for w in ws if len(w) > 3 and low(w) not in STOP})


def clusters(its):
    """Headlines about the same story, grouped: two belong together when they share two names, or one name and three
    words. -> [{outlets, names (most shared first), titles, links}] with the story in the most outlets first.
    ponytail: every pair is compared (a few hundred headlines); a name index if the feed list grows tenfold."""
    T = [terms(x["title"]) for x in its]; par = list(range(len(its)))
    def find(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for a in range(len(its)):
        for b in range(a + 1, len(its)):
            nm = len(T[a][0] & T[b][0])
            if nm >= 2 or (nm >= 1 and len(T[a][1] & T[b][1]) >= 3): par[find(a)] = find(b)
    G = {}
    for k in range(len(its)): G.setdefault(find(k), []).append(k)
    out = []
    for ks in G.values():
        cnt = {}
        for k in ks:
            for w in T[k][0]: cnt[w] = cnt.get(w, 0) + 1
        names = [w for w, c in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0])) if c >= 2][:6]
        seen, titles, links = set(), [], []
        for k in ks:                                       # (one headline an outlet: the pack stays short)
            if its[k]["outlet"] not in seen: seen.add(its[k]["outlet"]); titles.append(f'{its[k]["title"]} ({its[k]["outlet"]})'); links.append(its[k]["link"])
        out.append({"outlets": len(seen), "names": names, "titles": titles[:10], "links": [l for l in links if l][:8]})
    return sorted(out, key=lambda c: -c["outlets"])


def headlines():
    its, down = [], []
    for feed, url in FEEDS.items():
        try: its += items(feed, fetch(url))
        except Exception as e: down.append(f"{feed} ({str(e)[:40]})")   # (a feed that is down is one outlet fewer, never the end of the pass)
    return its, down


# ------------------------------------------------------------------------------------------------------------ state
def load():
    try: return json.load(open(STATE, encoding="utf-8"))
    except (OSError, ValueError): return {"judged": [], "made": []}


def keep(st):
    st["judged"] = [j for j in st.get("judged", []) if now() - j["at"] < 3 * 86400]; st["made"] = st.get("made", [])[-60:]
    os.makedirs(os.path.dirname(STATE), exist_ok=True); json.dump(st, open(STATE, "w", encoding="utf-8"), indent=1)


def same_story(a, b): return len(set(a) & set(b)) >= 2


def skip(c, st, t=None):
    """Why this story is not asked about now, or None: made in the last 10 days, or judged in the last 6 hours."""
    t = t or now()
    if any(m.get("posted") and t - m["at"] < COVERED and same_story(c["names"], m.get("names", [])) for m in st.get("made", [])): return "covered"
    if any(t - j["at"] < ASK_AGAIN and same_story(c["names"], j.get("names", [])) for j in st.get("judged", [])): return "judged"
    return None


# ----------------------------------------------------------------------------------------------------------- Claude
def claude(prompt, model, tools=None, timeout=900):
    """Claude Code on this server, on the owner's plan (as make_spec.claude_cli). `tools`: the web tools for the researcher."""
    cmd = ["claude", "-p", "--output-format", "text", "--model", model]
    if tools: cmd += ["--allowedTools", ",".join(tools), "--disallowedTools", "Bash,Edit,Write,Read,Glob,Grep,Task,NotebookEdit"]
    else: cmd += ["--disallowedTools", "Bash,Edit,Write,Read,WebFetch,WebSearch,Glob,Grep,Task,NotebookEdit"]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout, cwd="/tmp",
                       env={k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"})
    if r.returncode: raise SystemExit("claude -p failed: " + (r.stderr or r.stdout)[-300:])
    return r.stdout


def obj(raw):
    """The first JSON object in a reply, or {}."""
    i = raw.find("{")
    while i >= 0:
        try: return json.JSONDecoder().raw_decode(raw, i)[0]
        except ValueError: i = raw.find("{", i + 1)
    return {}


def judge(cands, st):
    covered = [m.get("headline") for m in st.get("made", []) if m.get("posted") and now() - m["at"] < COVERED]
    p = ("You pick stories for Meme Street, a free stock market game with made-up companies (memestreet.net) that posts short reels. "
         "Its owner wants a reel ONLY when a story is REALLY big: it leads the front pages, people who never read business news will hear "
         "about it today, and it is about a famous company, its boss, a market, a coin or a fortune (a chief executive out, a scandal at a "
         "household name, a crash or a record, a giant deal or a collapse, a money moment the whole internet is talking about). Expect one a "
         "week or fewer. An ordinary busy day has none: then pick nothing. A story that is merely the top business story of the day is not enough.\n"
         + EXCLUDE + "\nNever a story already covered: " + json.dumps(covered) + "\n\n"
         "Stories that are in several outlets right now:\n" +
         "\n".join(f"{k}. in {c['outlets']} outlets: " + " | ".join(c["titles"][:6]) for k, c in enumerate(cands)) +
         '\n\nReply with JSON only: {"pick": <a number above, or null>, "story": "the story in one sentence", "why": "one sentence"}')
    v = obj(claude(p, os.environ.get("NEWS_JUDGE_MODEL", "sonnet"), timeout=300))
    return v if isinstance(v.get("pick"), int) and 0 <= v["pick"] < len(cands) else dict(v, pick=None)


STATUS = ("confirmed", "admitted", "reported", "alleged")


def research(story, titles=(), links=()):
    p = (f"Research this news story for a short video. Now: {stamp()}.\nStory: {story}\n"
         + ("Headlines seen: " + " | ".join(titles) + "\n" if titles else "") + ("Links: " + " ".join(links) + "\n" if links else "") +
         "Use WebSearch and WebFetch. Read at least three reports from different major outlets (wire services, national papers, the big "
         "business channels) and the company's own statement or filing if there is one. Then reply with JSON only:\n"
         '{"ok": true, "headline": "what happened, one plain sentence", "day": "the date it happened",\n'
         ' "people": [{"name": "...", "role": "..."}],\n "company": "... or null",\n'
         ' "facts": [{"claim": "one plain sentence", "status": "confirmed|admitted|reported|alleged", "by": ["Outlet"], "url": "..."}],\n'
         ' "numbers": [{"what": "...", "value": "...", "by": ["Outlet"]}],\n'
         ' "market": "what the share price, coin or market did, with the figure and the outlet, or null",\n'
         ' "not_known": ["what is still open or disputed"],\n "viewer_question": "the trader\'s dilemma this poses, one sentence",\n'
         ' "sources": ["every outlet you read"]}\n'
         "Rules. facts: 6 to 12, in the order they happened. people: only the public figures at the centre, three at most. Status: "
         "\"confirmed\" = the company, a filing or the person said it, or two or more major outlets state it as fact; \"admitted\" = the person "
         "said it about themselves; \"reported\" = one outlet's own reporting, and the claim names that outlet; \"alleged\" = a disputed or "
         "unproven claim, and the claim says who makes it. Never raise a status. Every number names its outlet. Name no private person "
         "(a partner, a relative, a junior employee, an accuser): say \"an executive\", \"a woman\". " + EXCLUDE + " If the story is one of "
         "those, or fewer than three major outlets report it, reply {\"ok\": false, \"why\": \"...\"}.")
    return obj(claude(p, os.environ.get("NEWS_RESEARCH_MODEL", "opus"), tools=("WebSearch", "WebFetch"), timeout=1500))


def sound(pack):
    """What is wrong with a fact pack, [] when it can carry a reel."""
    if not pack.get("ok"): return ["the researcher said no: " + str(pack.get("why", "no reason given"))[:200]]
    F = pack.get("facts") or []; errs = []
    if not 5 <= len(F) <= 14: errs.append(f"{len(F)} facts (5 to 14 are needed)")
    if sum(1 for f in F if isinstance(f, dict) and f.get("status") in STATUS[:3]) < 5: errs.append("fewer than five facts that are more than an allegation")
    for k, f in enumerate(F):
        if not isinstance(f, dict) or f.get("status") not in STATUS or not f.get("claim") or not f.get("by"): errs.append(f"fact {k} has no claim, status or outlet")
    outs = {re.sub(r"[^a-z]", "", str(o).lower()) for f in F if isinstance(f, dict) for o in (f.get("by") or [])} | {re.sub(r"[^a-z]", "", str(o).lower()) for o in pack.get("sources") or []}
    if len(outs - {""}) < 3: errs.append("fewer than three outlets")
    if len(pack.get("people") or []) > 3: errs.append("more than three people named")
    if not pack.get("headline"): errs.append("no headline")
    return errs


# -------------------------------------------------------------------------------------------------------- the reel
WHAT = ("VIRAL, REAL NEWS (the owner, 2026-11-12): one REALLY big real headline told as a short film and linked to Meme Street. "
        "ONLY what is in facts.news may be said, shown or put in the caption: every claim, number, date and name comes from it, and each "
        "claim keeps its status: 'admitted' only for a fact marked admitted; a fact marked reported is said with its outlet ('the Times "
        "reported'), never state one as fact; what is only alleged is not in the pack and is not told at all (not a spy claim, not a "
        "rumour, not 'sources say'). Name only the people in facts.news.people "
        "and nobody else. No ticker symbol, no advice on the real share, no prediction, no view on guilt, no joke about a person's body, "
        "family or private life beyond the reported fact. The public figure is a simple cartoon you draw in svg with one or two trademark "
        "features (a jacket, the hair, glasses), never a realistic face, and nothing cruel happens to the figure beyond the story's own "
        "event (stepping down, being voted out, a fall from the top of the device). "
        "Shape: scene 0 is the hook, and the story's extraordinary event is acted out inside the FIRST SECOND, with the number or the "
        "name as the first spoken word ('4 days. That's all it took to end ...'); then what happened, in order, one beat a line, every "
        "line shown; the market's move as the device itself changing size, with its figure; a question to the viewer near the middle "
        "(facts.news.viewer_question: sell or hold?), drawn as two big buttons; then the link: on Meme Street the companies are made up "
        "and have bosses too, news moves their prices the same way, and you practise with 1,000 memebucks of practice money with no cash "
        "value (only what facts.meme_street says); then the sign-off scene. 35 to 60 seconds, 100 to 145 spoken words, every scene of "
        "kind \"free\" but the outro. \"type\" is \"Market news\". "
        "A clean picture (the critic held the first of these for it): every tag and name has its own lane and never sits on a figure, a "
        "prop or another tag; nothing tilts, flies in over the device or covers it; nothing is drawn in the right 230 px below y 960 or "
        "runs off an edge; a punch text is 2 to 5 words of its own line, in order, spelt as the caption spells them. "
        "The caption: line 1 is the hook with the question (under 125 characters); then the facts as short lines with their status "
        "words; one line 'Send this to the friend who ...'; a line on Meme Street with 'practice money with no cash value'; 'Practise at "
        "memestreet.net'; a line 'Sources: <the outlets>, <the date>. Not investment advice.'; then 3 to 5 hashtags.")


def script_text(spec):
    """Everything a viewer would read or hear: the lines, the punches, the strings the scene code draws, the caption."""
    js = spec.get("scene_js") or ""
    found = re.findall(r"'([^'\n]{2,60})'", js) + re.findall(r'"([^"\n]{2,60})"', js) + re.findall(r">([^<>{}$`]{2,60})</text>", js)
    label = lambda m: bool(re.fullmatch(r"[A-Za-z0-9 %$+~.,'&:?!-]+", m)) and (
        bool(re.search(r"[A-Za-z]{3}", m)) and (m.upper() == m or " " in m) or bool(re.fullmatch(r"[-+~]?\$?\d[\d.,]*[%BMK+]+", m)))
    drawn = sorted({m.strip() for m in found if label(m.strip())})   # (the tags, HUD words and figures: words in capitals, phrases, numbers with a unit)
    return {"spoken": [s.get("vo", "") for s in spec.get("scenes", [])], "punches": [s.get("text", "") for s in spec.get("scenes", [])],
            "drawn_by_the_scene_code": drawn, "title": spec.get("title"), "caption": spec.get("caption")}


def fact_check(pack, site, spec):
    p = ("A short video about a real news story may say nothing its fact pack does not support. Check the script against the pack.\n"
         "FACT PACK:\n" + json.dumps(pack, indent=1) + "\nWHAT MAY BE SAID ABOUT MEME STREET:\n" + json.dumps(site, indent=1) +
         "\nSCRIPT (spoken lines, on-screen punches, the labels its scene code draws, the caption):\n" + json.dumps(script_text(spec), indent=1) +
         "\nList every claim, number, date or name the pack does not support; every claim said more strongly than its status (a reported or "
         "alleged claim said as plain fact, or without who reported or alleges it); every person named who is not in \"people\"; anything from \"left_out_as_unproven\" told in any form; any ticker "
         "symbol, advice on the real share or prediction. Honest rounding is fine ('over 400 billion' for 440). Labels are short by nature: a "
         "label is fine when the spoken line beside it carries the status. Counting and arithmetic from the pack's dates and numbers is fine.\n"
         'Reply with JSON only: {"ok": true|false, "problems": ["scene 2: ...", "caption: ..."]}')
    v = obj(claude(p, os.environ.get("NEWS_CHECK_MODEL", "sonnet"), timeout=600))
    return [] if v.get("ok") is True else [str(x) for x in v.get("problems") or ["the fact check gave no verdict"]]


def lock():
    """The pipeline's one-reel-at-a-time lock (auto_reel.sh takes the same one): the news reel waits for the reel being made."""
    import fcntl
    f = open(os.path.join(ROOT, "queue", ".auto.lock"), "a"); fcntl.flock(f, fcntl.LOCK_EX); return f


def make(pack, names=()):
    """Write, check, voice, render, review and queue the reel for a sound fact pack. -> the queue slot, or None (held)."""
    sys.path.insert(0, HERE)
    import make_spec as M
    M.CATEGORIES.setdefault(CATEGORY, WHAT)
    hist = json.load(open(M.HISTORY)) if os.path.exists(M.HISTORY) else {}
    notes = os.path.join(ROOT, "exemplar", "NOTES.md")
    facts = {"news": pack, "meme_street": M.SITE_FACTS, "recent_devices": [d for d in hist.get("devices", []) if isinstance(d, dict)][-30:],
             "video": {"available": False}, "hook_shots_used_lately": []}
    ask = {"category": CATEGORY, "what_this_reel_is": WHAT, "facts": facts, "recent_titles_to_avoid": hist.get("titles", [])[-20:],
           "exemplar_notes": open(notes, encoding="utf-8").read() if os.path.exists(notes) else "",
           "what_works_now": {"note": "Openings that beat their account's usual views. Use the SHAPE, never the words.", "examples": M.VIRAL_EVIDENCE}}
    slot = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H%M")
    B = {"slot": slot, "category": CATEGORY, "system": M.system_prompt(CATEGORY), "ask": ask, "charts": []}
    work, out = os.path.join(ROOT, "work", "news-" + slot), os.path.join(ROOT, "out", "news-" + slot)
    say("waiting for the reel being made, then writing:", pack.get("headline"))
    held = lambda why: (say("HELD, nothing posts:", why), None)[1]
    with lock():
        spec = M.write(B, work=work)
        bad = fact_check(pack, M.SITE_FACTS, spec)
        if bad:                                            # (one fix; a second failed check holds the reel)
            say("fact check sent the script back:", "; ".join(bad)[:600])
            draft = json.dumps({k: v for k, v in spec.items() if k != "scene_js"}, indent=1) + "\n```js\n" + (spec.get("scene_js") or "") + "\n```"
            spec = M.write(B, msgs=[{"role": "user", "content": json.dumps(ask, indent=1)}, {"role": "assistant", "content": draft},
                                    {"role": "user", "content": "A fact check found these in your script. Fix every one, change nothing else, and reply "
                                                                "with the whole JSON and the js block again: " + "; ".join(bad)}], work=work)
            bad = fact_check(pack, M.SITE_FACTS, spec)
            if bad: return held("the fact check failed twice: " + "; ".join(bad)[:400])
        words = sum(len(s.get("vo", "").split()) for s in spec["scenes"])
        if words > 160: return held(f"{words} spoken words (a news reel has 145 at most)")
        M.save(spec, B, work)
        json.dump(pack, open(os.path.join(work, "facts.json"), "w", encoding="utf-8"), indent=1)
        r = subprocess.run([sys.executable, os.path.join(HERE, "critic.py"), "loop", work, out], cwd=ROOT)
        if r.returncode or not os.path.exists(os.path.join(out, "approved.json")): return held("the critic did not approve it")
        bad = fact_check(pack, M.SITE_FACTS, json.load(open(os.path.join(work, "spec.json"), encoding="utf-8")))   # (the critic's rewrite is checked too)
        if bad: return held("the fact check failed after the critic's rewrite: " + "; ".join(bad)[:400])
    if os.environ.get("NEWS_DRY") == "1": return held("a dry run (NEWS_DRY=1): approved and left in " + out)
    slot = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H%M")             # (it posts now: the queue takes any folder whose time has come)
    stage, dest = os.path.join(ROOT, "queue", ".staging", slot), os.path.join(ROOT, "queue", slot)
    os.makedirs(stage, exist_ok=True)
    for f in ("reel.mp4", "caption.txt", "cover.jpg", "approved.json"): subprocess.run(["cp", os.path.join(out, f), stage], check=True)
    open(os.path.join(stage, ".news"), "w").write(pack.get("headline", ""))
    os.rename(stage, dest); say("queued", slot, "-", pack.get("headline"))
    return slot


def run(story, c=None, st=None):
    st = st or load(); c = c or {"names": sorted(terms(story)[0])[:6], "titles": [], "links": []}
    pack = research(story, c["titles"], c["links"]); errs = sound(pack)
    rec = {"at": now(), "names": c["names"], "headline": pack.get("headline") or story, "posted": False}
    if errs:
        say("not made:", "; ".join(errs)); st.setdefault("made", []).append(dict(rec, why="; ".join(errs)[:300])); keep(st); return None
    left = [f["claim"] for f in pack["facts"] if f["status"] == "alleged"]      # (an unproven allegation is never told by an unattended reel)
    pack = dict(pack, facts=[f for f in pack["facts"] if f["status"] != "alleged"], left_out_as_unproven=left)
    slot = None
    for k in range(TRIES):                                 # (the critic held the first dry run for its layout: a really big story gets a second, fresh draft)
        slot = make(pack, c["names"])
        if slot or os.environ.get("NEWS_DRY") == "1": break
    st = load(); st.setdefault("made", []).append(dict(rec, posted=bool(slot), slot=slot, day=stamp()[:10])); keep(st)
    return slot


def watch():
    if os.path.exists(os.path.join(ROOT, "state", "news_off")): return
    st = load(); day = stamp()[:10]
    if sum(1 for m in st.get("made", []) if m.get("posted") and m.get("day") == day) >= MAX_PER_DAY: return
    its, down = headlines(); cl = [c for c in clusters(its) if c["outlets"] >= MIN_OUTLETS and len(c["names"]) >= 2]
    cands = [c for c in cl if not skip(c, st)][:4]
    if down and len(down) > len(FEEDS) // 2: say("most feeds are down:", ", ".join(down)[:300])
    if not cands: return
    if sum(1 for j in st.get("judged", []) if now() - j["at"] < 86400 and j.get("asked")) >= JUDGES_A_DAY: return   # (the plan's usage: a busy news day asks 12 times at most)
    v = judge(cands, st)
    for k, c in enumerate(cands): st.setdefault("judged", []).append({"at": now(), "names": c["names"], "asked": k == 0, "big": v.get("pick") == k})
    keep(st)
    say(f"{len(its)} headlines, {len(cands)} stories in {MIN_OUTLETS}+ outlets ({'; '.join(' '.join(c['names'][:3]) for c in cands)}):",
        "BIG: " + str(v.get("story")) if v.get("pick") is not None else "none is really big (" + str(v.get("why", ""))[:160] + ")")
    if v.get("pick") is not None: run(v.get("story") or cands[v["pick"]]["titles"][0], cands[v["pick"]], st)


def demo():
    t = 1_800_000_000; d = email.utils.formatdate(t - 3600); old = email.utils.formatdate(t - 30 * 3600)
    rss = lambda *rows: "<rss><channel>" + "".join(f"<item><title><![CDATA[{a}]]></title><link>http://x/{k}</link><pubDate>{w}</pubDate></item>" for k, (a, w) in enumerate(rows)) + "</channel></rss>"
    its = (items("google", rss(("Nvidia CEO Jensen Huang resigns after board probe - CNBC", d), ("Senate passes the budget bill - Reuters", d)), t)
           + items("bbc-business", rss(("Jensen Huang steps down as Nvidia chief", d), ("Old story about Huang and Nvidia", old)), t)
           + items("guardian", rss(("Nvidia shares slide as Huang quits", d), ("Bank of England holds rates", d)), t)
           + items("wsj", rss(("Huang Out at Nvidia After Scandal", d), ("Oil Prices Slide", d)), t))
    assert len(its) == 7 and its[0]["outlet"] == "cnbc" and its[0]["title"].endswith("probe") and its[2]["outlet"] == "bbc", its
    cl = clusters(its); assert cl[0]["outlets"] == 4 and cl[0]["names"][:2] == ["huang", "nvidia"] and cl[1]["outlets"] == 1, cl
    st = {"made": [{"at": t - 86400, "names": ["nvidia", "huang", "jensen"], "posted": True}], "judged": []}
    assert skip(cl[0], st, t) == "covered" and skip(cl[0], {"made": [], "judged": [{"at": t - 60, "names": ["huang", "nvidia"]}]}, t) == "judged"
    assert skip(cl[0], {"made": [dict(st["made"][0], posted=False)], "judged": []}, t) is None and skip(cl[0], st, t + 11 * 86400) is None
    assert obj('Sure:\n{"pick": null, "why": "a {quiet} day"} thanks') == {"pick": None, "why": "a {quiet} day"} and obj("no") == {}
    f = lambda s="confirmed", by=("CNBC",): {"claim": "He stepped down.", "status": s, "by": list(by), "url": "u"}
    ok = {"ok": True, "headline": "h", "facts": [f(), f("admitted", ("NPR",)), f("reported", ("NYT",)), f(), f()], "people": [{"name": "A"}], "sources": ["CNBC", "NPR", "NYT"]}
    assert sound(ok) == [] and sound({"ok": False, "why": "an election"}) and sound(dict(ok, facts=ok["facts"][:3])) and sound(dict(ok, sources=["CNBC"], facts=[f()] * 5))
    assert sound(dict(ok, facts=[f("proven")] * 5)) and sound(dict(ok, people=[{}] * 4))
    assert sound(dict(ok, facts=ok["facts"][:3] + [f("alleged"), f("alleged")])) and sound(dict(ok, facts=ok["facts"] + [f("alleged")])) == []   # (allegations do not count towards the five, and never reach the writer: run())
    tx = script_text({"scenes": [{"vo": "4 days.", "text": "4 days"}], "caption": "c", "title": "T",
                      "scene_js": "({t}) => { const RD = '#ff4d5a'; return tag(1, 2, 'OFF THE BOARD') + `<text>-13%</text>` + tag(3, 4, \"HALF BACK\") + 'M0,0 L1,1'; }"})
    assert tx["drawn_by_the_scene_code"] == ["-13%", "HALF BACK", "OFF THE BOARD"] and tx["spoken"] == ["4 days."], tx
    assert "never state one as fact" in WHAT and "practice money with no cash value" in WHAT
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:] or ["demo"]
    if a[0] == "demo": demo()
    elif a[0] == "feeds":
        its, down = headlines()
        print(f"{len(its)} headlines from {len(FEEDS) - len(down)} feeds" + (f"; down: {', '.join(down)}" if down else ""))
        for c in clusters(its)[:12]:
            if c["outlets"] >= 2: print(f"{c['outlets']:>2} outlets  [{' '.join(c['names'][:4])}]  " + " | ".join(c["titles"][:3])[:230])
    elif a[0] == "watch": watch()
    elif a[0] == "make" and len(a) > 1: print(run(" ".join(a[1:])) or "held or not made: see the lines above")
    else: raise SystemExit(__doc__)
