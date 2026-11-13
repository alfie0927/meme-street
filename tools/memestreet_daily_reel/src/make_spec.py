"""Write one auto reel's script: the facts come from the game, the words from Claude, and both are checked.

  python3 src/make_spec.py <slot YYYY-MM-DDTHHMM> <work dir> [--category NAME] [--remake <november folder entry json>]

Facts are never invented: a quiz uses real game charts with the answer the chart actually gave (/api/learn/test), a
stock story uses a real game company and its real chart (/api/reel/stock), a lesson uses a real chart that shows the
idea. Claude writes the narration, the on-screen words, the hook and the caption around those facts, in the voice in
voice.md, and the result is checked (hook score, length, words per line, no emoji, the disclaimer) and sent back to
Claude to fix at most twice. Output: <work>/spec.json and <work>/caption.txt.
"""
import difflib, glob, json, os, random, re, shutil, subprocess, sys, time, urllib.error, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "ig"))
import detect, hookscore
import caption as igcap
import shots
from pronounce import LEX

SITE = os.environ.get("MS_BASE_LOCAL", "http://127.0.0.1:8000")
MODEL = os.environ.get("REEL_MODEL", "claude-sonnet-5-5")
DISCLAIMER = "Fictional market. Not investment advice."
HISTORY = os.path.join(ROOT, "state", "auto_history.json")
PACK = os.environ.get("CONTENT_PACK", "/opt/memestreet/content/pack_fiction.json")

CATEGORIES = {
    "Chart quiz": "Three questions on three real game charts. Each: a question scene (options shown, a short countdown), "
                  "then an answer scene (the rest of the chart plays out, the right option lights up, one or two lines on why).",
    "Stock story": "Just the company, never its chart (the owner, 2026-11-07; the four November stock stories that did best "
                   "had no chart). Seven beats, in this order: (1) the hook, one odd and specific fact about what it does "
                   "('This company sells rain.'), over a story scene; (2) what it is: its name and what it does, a story "
                   "scene (pens when it has a home: a ranch, farm, clinic, depot); (3) how it makes money: a story scene, layout earns (its 3 jobs, each paying out); (4) why it matters: a story scene "
                   "(line when people want it, compare for the old way against its way, or flow); a scene on what moves the "
                   "stock may be candles (they fall, then burst into the next scene); (5) what's unique: a story scene that grows (grow or "
                   "network); (6) risks and what moves its stock: a story scene, layout storm (2 or 3 risks strike), from "
                   "the bad news in the facts; (7) the outro, inviting viewers to trade it. No chart scene, no "
                   "candles, no price moves.",
    "Chart breakdown": "One game company's real recent chart, read like an analyst, in its own structure: (1) the hook, the "
                       "chart's biggest move said as a stake ('This stock fell 12% in a day. The chart warned you.'), with the "
                       "chart already drawn; (2) the company in one line, over the chart; (3) three numbered reads, each a "
                       "scene titled '1. ...', '2. ...', '3. ...' on the same chart with marks, lines, shades and zooms (the "
                       "trend, the level, the tell); (4) the one lesson to take away; (5) the outro. One chart the whole way, "
                       "no story scenes.",
    "Technical lesson": "Teach one chart idea (an indicator, a level, a pattern) on a real chart that shows it working: what it "
                        "is, how to spot it (point at it), what the price did next, why it worked, then one short line that it "
                        "does not work every time, and the one rule to remember.",
    "Trading mistake": "One common beginner mistake, shown on a real chart: what people do, what it costs, what to do instead.",
    "Guess the move": "A viral, interactive reel: a real chart stops at a big moment, the viewer guesses what came next "
                      "(a short countdown), then the reveal and why. One or two charts.",
    "Myth or fact": "A viral reel: three common trading beliefs, each called myth or fact with one line of why, ending on "
                    "the most surprising one. Cards and big text, one real chart to prove the last point.",
    "Daily recap": "Tonight's Daily Chart recap, the same chart every player had today: what the stock did, the realistic "
                   "trades a careful reader could have taken (only those in the facts, at their candles), today's best "
                   "player's return, and the invitation to play tomorrow's chart. Open on the decision the viewer would have faced at the day's hardest candle (would you have held here?), never on how many people played or on the chart's number. Its own device like every director reel "
                   "(the day's chart may be the star): the day revealed in order, the trades marked at their candles, a HUD "
                   "scoring the plan against holding. The outro ends: \"Tomorrow's "
                   "Daily Chart drops at midnight. Beat it at memestreet.net.\" When the facts say plan_beat_holding is false, "
                   "own it in the first or second scene, in the owner's voice: the stock did better than us today, just buying at the "
                   "open and holding beat these trades, but we trade proper setups, not hope (say 'holding' and 'setups').",
    # the viral formats from the research of 2026-11-04 (swipe.md: 169 shorts and TikToks, 11 accounts, ranked by how far
    # each beat its own account's median). The formula is copied, never a script.
    "Chart twist": "VIRAL (top format, 37x its account's median): a real chart that looks one way ('it still looked bearish'), "
                   "then the candles tell a different story. Hook names what it looked like; the middle builds the case "
                   "for it; the turn ('but then...') reveals what the chart really did and the clue that showed it early.",
    "One trick": "VIRAL (43x): one concrete, actionable rule shown on a real chart, said as an instruction in the first "
                 "line ('Don't buy the breakout. Put an order at the retest.'). Then the chart proves it, then the one-line rule again.",
    "Big players": "VIRAL (11x): how a move traps beginners: the push past a level that grabs everyone's stops, then the "
                   "reversal. Calm, not conspiratorial: 'this is where the stops sat, this is what price did to them'.",
    # stick figures (research 2026-11-05: 632 videos from 19 stick-figure and animated finance accounts)
    "Trader levels": "VIRAL STICK FIGURES (538x its account's median): 'Your life at every level of a trader'. Four or five "
                     "levels, each a stick scene (head 'Level 1'...) with Rookie or Pro acting it out with a pose and a short "
                     "bubble, from the gambler who buys whatever went up to the one who sets the stop first. Every level "
                     "that mentions candles or price stands beside the real chart and acts out what that chart did. Funny, true, kind.",
    "Explained like you're 5": "VIRAL STICK FIGURES (548x and 165x): one market idea explained like you're five by stick "
                               "figures acting it out (a shop, a queue, a seesaw), then the same idea on the real chart. "
                               "Big simple words; the stick figure is the teacher.",
    "Stick skit": "VIRAL STICK FIGURES (75x on TikTok): a 20 to 30 second skit with two stick figures and one punchline, "
                  "about a real beginner habit (buying the top, selling the bottom, ignoring the stop), played out on the "
                  "real chart. The last beat lands the lesson in one line.",
    # from accounts like the owner's examples (research 2026-11-05: 479 videos, 16 trading short-form accounts)
    "Truth list": "VIRAL LOOP (261x its account's median): a 6 to 10 second reel made to be replayed while the caption is "
                  "read. Scenes: a hook (on-screen text, max 6 words, like 'Trading truths nobody tells you') over a real "
                  "chart moving, then one big scene, no outro. The spoken line is the hook and 'read the caption'. The "
                  "caption carries the value: 7 to 12 numbered, original, plain trading truths (risk, stops, patience, "
                  "overtrading, revenge trading), one line each, then the usual ending.",
    "Hard truth": "VIRAL (6 to 10x): one hard truth about trading psychology in 10 to 20 seconds, shown on the real chart "
                  "moment that proves it (for example one loss, then the urge to win it back). One stick figure may act it "
                  "out. Short lines, a pause-free build, the truth said plainly in the last scene before a short outro.",
    "Meme Street explained": "What Meme Street is and why someone learning to trade should join, told through your own device "
                             "(never a feature list read out): a fictional market that never closes, 1,000 MB of practice money, "
                             "real charts, lessons, the Daily Chart, fair prices. Only the facts in 'site'; pick the two or three "
                             "that make the strongest story and dramatise them. A new angle every time: read 'previous_explainers' "
                             "and take none of their angles, devices or titles.",
    "Daily Chart explained": "How the Daily Chart works and how it runs, told through your own device: the same mystery chart for "
                             "everyone, the lead-in, two minutes of live candles, the buttons, the score against holding, the board, "
                             "streaks, a new chart at midnight UTC. Only the facts in 'daily'; a real past Daily Chart is chart 0 "
                             "(its lead-in is shaded by the renderer). A new angle every time: read 'previous_explainers' and take "
                             "none of their angles, devices or titles. The outro ends: \"Today's Daily Chart is live. Play it at memestreet.net.\"",
    "Speed cheat sheet": "VIRAL (14x): rapid fire, three candles or patterns in under 30 seconds, each named, shown on a "
                         "real chart, and given one line on what it means. The hook promises the speed.",
}
# (the owner, 2026-11-11: the five formats rated Ugly left the mix: Technical lesson, Explained like you're 5, Speed cheat sheet,
#  One trick, Myth or fact. Their turns went to Stock story, Trader levels, Hard truth and Stick skit. REEL_CATEGORY can still ask for one.)
ROTATION = {"0600": ["Stock story", "Trading mistake"], "1200": ["Chart quiz"], "1800": ["Stock story", "Chart breakdown"],
            "2100": ["Chart twist", "Hard truth", "Big players", "Stock story", "Guess the move"],
            "0300": ["Chart twist", "Hard truth", "Big players", "Stock story"]}
ROTATION["0900"] = ["Hard truth"]
EXPLAINERS = ("Daily Chart explained", "Meme Street explained")   # (each every 6 days, one every 3: the owner, 2026-11-10)


def explainer(slot):
    """The explainer this slot carries, or None: the 18:00 slot of every third day from 2026-11-10, alternating."""
    import datetime as dt
    k = (dt.date.fromisoformat(slot[:10]) - dt.date(2026, 11, 10)).days
    return EXPLAINERS[(k // 3) % 2] if slot[-4:] == "1800" and k > 0 and k % 3 == 0 else None
ROTATION["1300"] = ["Stick skit", "Chart twist"]   # (was Truth list: a 7 s "read the caption" reel can never meet the bar of the owner's references)
ROTATION["2100"] += ["Trader levels", "Stick skit"]
ROTATION["0300"] += ["Trader levels", "Stick skit"]
# (no "pattern" questions: triangles, wedges, channels and flags need slanted trendlines the renderer cannot draw yet;
#  a quiz on one looped 55 critic rounds on 2026-11-07)
KINDS = {"Chart quiz": ["candle", "breakout", "level", "trend", "stop", "rr", "fib"],
         "Technical lesson": ["rsi", "ma", "fib", "level", "breakout", "candle", "trend"],
         "Trading mistake": ["stop", "rr", "breakout", "level", "next"],
         "Guess the move": ["breakout", "level", "next"], "Myth or fact": ["next", "breakout", "level"],
         "Chart twist": ["breakout", "level", "next"], "One trick": ["breakout", "stop", "level", "rr"],
         "Big players": ["breakout", "level"], "Speed cheat sheet": ["candle", "trend"],
         "Trader levels": ["breakout", "level", "stop"], "Explained like you're 5": ["trend", "level", "candle", "rr"],
         "Stick skit": ["breakout", "level", "next"], "Truth list": ["trend", "breakout", "level"],
         "Hard truth": ["stop", "next", "breakout", "level"]}
LENGTH = {"Truth list": (8, 30, False), "Hard truth": (25, 60, True)}     # spoken words min, max, and whether it ends on the outro
# New formats on trial since 2026-11-12 (the owner: "create more types of reels... creative... a really good hook"). src/format_scores.py
# judges every format on Instagram's skip rate, and brief() drops the worst and makes the best every day.
NEW_HOOK = (" THE HOOK: frame 0 already shows a character or an odd object with the stake in view (never a bare chart, a title card or "
            "a list of 'three things'), and the first spoken sentence is 12 words at most and carries the stake: a number or a loss "
            "from the facts, or a dare the viewer can answer.")
CATEGORIES.update({
    "Two traders": "NEW, STICK FIGURES, head to head: Rookie and Pro take the SAME trade on the same real chart at the same candle and "
                   "differ in ONE choice (where the stop goes, chasing the break or waiting, cutting or hoping). Their two account bars "
                   "start level in the HUD; the chart plays on and the bars split; the last beat names the one choice. Hook formula: "
                   "Head To Head with the loss in it ('Same chart. Same candle. One of them is about to lose.'). What each choice did "
                   "comes from the facts only (what_happened, after_the_question)." + NEW_HOOK,
    "Rewind": "NEW, the ending first: open ON the aftermath of the chart's real move (the drop or the jump already there, a character or "
              "an object wearing the damage), in the Mid-Sentence Start formula ('...and that is how 9% went in six candles'). Then "
              "REWIND: a reveal cue with a lower index runs the candles backwards like a tape, to the one clue that showed it early; then "
              "it plays forward again with the clue lit. Do not name the clue before the rewind stops: the viewer waits for it. One "
              "chart, one clue." + NEW_HOOK,
    "Trade diary": "NEW, STICK FIGURES, the feelings of one trade: one real trade told as a diary, an entry every few candles ('Candle 3: "
                   "I am a genius.' 'Candle 9: I hate this.' 'Candle 14: please, just get back to my entry.'), each entry acted by the "
                   "figure beside the real price at that candle (closes_after gives the path). A mood meter in the HUD swings with the "
                   "price. The last entry is the lesson: the plan was made before candle 1 and the feelings changed nothing. Hook "
                   "formula: The Receipt ('I held this trade for 25 candles. Here is every feeling I had.'). Funny, true, kind." + NEW_HOOK,
    "Candles talk": "NEW, the candles are the characters: two or three candles of the real chart get faces and speak in short bubbles, "
                    "saying what the buyers and sellers did inside them (a long wick: 'They pushed me up there and left me.'; a doji: 'We "
                    "tied. Nobody won.'). The viewer learns to read a candle by hearing it complain; then the next candles show who was "
                    "right. Hook formula: Cold Open Demo, a candle already mid-rant on frame 0 ('If this candle could talk, it would be "
                    "screaming at you.'). The voice tells the story; the bubbles are the candles' own few words." + NEW_HOOK,
    "Instant replay": "NEW, sports commentary: one real move on the chart called like a goal by a commentator at a desk ('He is through "
                      "the level! Oh, he has given it straight back!'), then the replay: the same candles again, slowed, with the one "
                      "moment that decided it frozen and circled (the close, not the wick). A scoreboard in the HUD: Buyers against "
                      "Sellers. It ends on the referee's ruling, the rule in one line. Hook formula: Cold Open Demo, mid-action from the "
                      "first word. Excited but exact: every call is something the facts show." + NEW_HOOK,
    "Expectation vs reality": "NEW, two lanes: on top what a beginner pictures a trade to be (your own drawing: a clean line straight "
                              "up), underneath the real candles after the entry: the dips it took before it got anywhere, or the loss "
                              "it turned into. A figure rides each lane: one relaxed, one sweating. The point: the real one needs a "
                              "stop and patience to get through the middle. Hook formula: Before And After, On Screen ('What you think a "
                              "trade looks like. What it looks like.'). The top lane is labelled a drawing, never passed off as a chart." + NEW_HOOK,
    "Breaking news": "NEW, the game's own world: a newsroom for one fictional company. A headline from the facts breaks "
                     "(good_news_examples or bad_news_examples), the viewer gets a beat to call it, up or down, then the ticker answers; a "
                     "second headline goes the other way; then the twist when the facts give one: the same news moves other sectors too "
                     "(news_also_moves). Say only the direction, never a percentage the facts do not give. The lesson: on Meme Street the "
                     "news moves prices, so read the wire before you trade. Hook formula: The Reveal with a dare ('This headline just "
                     "hit. Up or down?'). The company, its product and the headline are the comedy: play them straight." + NEW_HOOK,
})
KINDS.update({"Two traders": ["stop", "breakout", "level"], "Rewind": ["breakout", "level", "next"],
              "Trade diary": ["next", "breakout", "level", "stop"], "Candles talk": ["candle", "trend"],
              "Instant replay": ["breakout", "level"], "Expectation vs reality": ["next", "breakout", "level"]})
ROTATION["0600"] += ["Expectation vs reality", "Trade diary"]; ROTATION["1300"] += ["Two traders", "Candles talk"]   # (each new format in two turns)
ROTATION["1800"] += ["Breaking news", "Instant replay"]; ROTATION["2100"] += ["Rewind", "Two traders", "Trade diary", "Instant replay"]
ROTATION["0300"] += ["Rewind", "Candles talk", "Expectation vs reality", "Breaking news"]
# In depth (the owner, 2026-11-12: "there needs to be more depth in the actual content", "what happened to all the technical lessons?",
# "we tested [X] strategy, here's why it worked/didn't work"). Technical lesson is back as one lesson of the site's own curriculum per
# reel (69 lessons in 11 technical tracks, the one out longest ago, the tracks in turn); Strategy test is new: src/backtest.py runs the
# rule on every listed stock and the reel says only its numbers. Both may run long.
DEEP = ("Technical lesson", "Strategy test")
DEEP_LENGTH = (" LENGTH AND DEPTH: this format goes deep. It may run 60 to 100 seconds (150 to 260 spoken words) whatever the general "
               "length line says, and it uses the proper terms, each one said once in plain words and then used. Depth is ONE idea "
               "followed all the way down: the mechanism, the number, the case where it fails. Never three ideas skimmed.")
CATEGORIES.update({
    "Technical lesson": "NEW, IN DEPTH: one lesson from Meme Street's own curriculum (facts.lesson: its title, its track, its level and "
                        "its whole text). Teach ONE idea of it properly, at the level of its track (an expert track gets the real "
                        "maths: the formula said in words, then worked once with the lesson's own numbers on screen). The device IS "
                        "the mechanism (an order book is a queue you can see, Kelly is a bet-size dial with a cliff, a walk-forward "
                        "test is a window sliding along a tape); the HUD carries the number as it changes. What the idea is, how it "
                        "works step by step, the case where it breaks, then the one rule. Use only what the lesson text says, in your "
                        "own words: no number, formula or claim that is not in it. When the facts hold a chart, it is a real one "
                        "that shows the idea: point at its candles. The last line before the sign-off names the lesson: it is free "
                        "on memestreet.net." + NEW_HOOK + DEEP_LENGTH,
    "Strategy test": "NEW, IN DEPTH, 'we tested it': one trading rule, run by our own code on every listed Meme Street stock (facts: "
                     "the claim people repeat, the exact rules, the sample, the result after fees, buying and holding the same "
                     "candles, where it worked and where it failed, each timeframe, the verdict). Open on the claim as a dare with "
                     "the count in it ('Buy when the RSI drops under 30. Everyone says it. We ran it 83 times.'). The device is a "
                     "test rig that runs the trades: a counter racing through them, wins and losses dropping into two piles or an "
                     "account line drawn trade by trade, the holding line beside it. Then the verdict as facts.verdict words it, "
                     "then WHY from the facts (the win rate against the break-even win rate, the size of wins against losses, "
                     "charts that rose against charts that fell, choppy against trending, the fee, the noise band: say what a "
                     "noise band is in one plain sentence). With facts.compared_with, it is a duel: both rules on the rig, one "
                     "result each. One honest line on the sample, from facts.limits. When the facts hold example trades, show one "
                     "win and one loss on chart 0 at their candles. Every number comes from the facts and is said as it is "
                     "written; a rule that lost is said to have lost, and nothing here promises the next trade. The viewer leaves "
                     "knowing HOW to test a rule, more than what this one did." + NEW_HOOK + DEEP_LENGTH,
})
ROTATION["1200"] += ["Technical lesson"]; ROTATION["0900"] += ["Strategy test"]      # (each in two turns, like every new format)
ROTATION["2100"] += ["Technical lesson"]; ROTATION["1800"] += ["Strategy test"]
# More than levels and breakouts (the owner, 2026-11-12: "they always talk about resistance/support so much"): until today nearly every
# format drew its chart test from "breakout" and "level". Each format now has every kind that suits it, and gather() takes the kind
# that went out longest ago (lru()).
for _c, _more in {"Chart quiz": ["rsi", "ma", "pattern"], "Trading mistake": ["rsi", "ma", "trend"], "Guess the move": ["rsi", "ma", "pattern", "candle", "fib"],
                  "Chart twist": ["rsi", "ma", "pattern", "fib"], "Trader levels": ["rr", "rsi", "ma", "trend"], "Stick skit": ["stop", "rr", "rsi"],
                  "Hard truth": ["rr", "rsi", "ma", "trend"], "Two traders": ["rr", "next", "rsi", "ma"], "Rewind": ["rsi", "ma", "pattern", "stop"],
                  "Trade diary": ["rr", "rsi", "ma"], "Candles talk": ["pattern"], "Expectation vs reality": ["rsi", "ma", "pattern", "fib"]}.items():
    KINDS[_c] = KINDS[_c] + [k for k in _more if k not in KINDS[_c]]
SUBJECT = {"level": "support and resistance levels", "breakout": "breakouts, real or fake", "candle": "candle shapes", "trend": "trends",
           "pattern": "chart patterns", "rsi": "the RSI", "ma": "moving averages", "fib": "Fibonacci levels", "rr": "reward against risk",
           "stop": "where the stop goes", "next": "what the next candles did"}
LESSON_TRACKS = ("charts", "indicators", "orders", "risk", "shorting", "derivatives", "strategies", "testing", "microstructure",
                 "vol-trading", "sizing-uncertainty")
LESSON_KIND = {"candlesticks": "candle", "trends": "trend", "support-resistance": "level", "ranges-breakouts": "breakout",   # a real chart of
               "reversal-patterns": "pattern", "continuation-patterns": "pattern", "moving-averages": "ma", "momentum": "rsi",   # the kind, for
               "fibonacci": "fib", "r-multiples": "rr", "stop-placement": "stop", "breakout-trading": "breakout",                 # the lessons
               "trend-following": "ma", "mean-reversion": "rsi"}                                                                # that have one
# The first 3 seconds, for every format (the owner, 2026-11-12: "use these for reel ideas/hooks/animations/generation"): the hook
# checklist of github.com/ootto-ai/claude-virality-skill (commit 542ed54, MIT; its study of 262 reels, winners against flops frame by
# frame), put in our terms, with our own numbers. Its "comment a keyword for a DM" rule is left out: nothing here sends DMs.
FIRST3 = """
THE FIRST 3 SECONDS (the owner, 2026-11-12). Most viewers decide in the first 3 seconds; ours give a reel about 7. Our reels that open on a
character or an odd object keep 52 to 76% of viewers past 3 seconds; the ones that open on a chart or a list keep 25 to 30%. Scene 0 passes
every line below, or you rewrite it before writing anything else:
1. Frame 0 is already moving: the device is on screen and mid-action at t = 0. No fade-in, no empty stage, no title card that holds.
2. Frame 0 shows something a stranger recognises at a glance (a person in trouble, a phone, money, a shop, a familiar object), never
   abstract shapes and never a bare chart.
3. The biggest thing on screen fills most of the world band and moves from the first frame.
4. Something extraordinary happens before 3 seconds: it breaks, falls, bursts, snaps shut, builds itself, or a number races and locks.
5. The punch lands between 1 and 2 seconds, word by word as the voice says it, and carries the stake.
6. The first spoken word is the subject or "you", never a warm-up ("so", "today", "let's", "here's", "in this video").
7. The first sentence is about the viewer wherever the format allows: "you" or "your" in it, or a dare they can answer.
8. With the sound off, the first 3 seconds still say what is at stake.
After the hook, every spoken line has its own change on screen: every line is shown, never only said.
Rotate the angle from reel to reel: the result first; a contrarian claim; the pain first; something breaks on screen; a dare.
"recent_devices" in the request shows the last openings: take a different angle from the last two.
"""
# (docs/ROADMAP.md A4, the owner 2026-11-11: viewers give a reel about 7 seconds, so one format fits inside them and
#  replays. A test: half of the 13:00 reels, about ten in three weeks. 12:00 gets a Hard truth turn: more reels at that length.)
CATEGORIES["Loop"] = ("SHORT LOOP (a test, the owner 2026-11-11): 7 to 12 seconds made to be watched twice. ONE full animated scene of "
                      "your device, moving from the first frame to the last, that SHOWS one trading truth: the picture carries the whole "
                      "idea (this is not a 'read the caption' reel). Two or three free scenes, 16 to 30 spoken words in all, and NO outro "
                      "scene: the last line breaks off so that the first line finishes it when the reel replays ('...and that is exactly "
                      "why' runs into the hook), and your device ends in the pose it began in. The address is never spoken: the caption "
                      "carries memestreet.net. A chart is optional.")
KINDS["Loop"] = KINDS["Hard truth"]; LENGTH["Loop"] = (16, 30, False); ROTATION["1300"] += ["Loop", "Loop"]; ROTATION["1200"] += ["Hard truth"]
SECONDS = {"Loop": (6, 12.5)}   # a format's length in seconds at the voice's pace, checked by the dry run (every other format: at most 60, the owner 2026-11-11)
SECONDS.update({c: (0, 105) for c in DEEP})   # (the in-depth formats may run to 100 seconds: the owner, 2026-11-12)
VIRAL_EVIDENCE = [
    ["37x", "It still looked bearish... but the candles told a different story."],
    ["6x", "It looked bullish, until the second test changed everything."],
    ["43x", "Don't buy it, but put an order in."],
    ["7x", "This one candle can predict where price is going."],
    ["11x", "The big players can move price, but they leave a footprint."],
    ["14x", "Candlestick patterns explained in less than a minute."],
    ["0.2x (what flops)", "Here are my top three chart settings."], ["0.2x (what flops)", "Markets went crazy today, here's why."]]
STICK_EVIDENCE = [
    ["538x", "Your life at every level of a day trader."], ["548x", "Stocks explained for those who want to be rich."],
    ["165x", "Stock market terms explained, for beginners."], ["152x", "How to actually quit it, explained by a stick figure."],
    ["75x", "Bro forgot his job. (a 15-second stick-figure skit)"], ["80x", "Every scam tactic explained in eight minutes."]]
SHORT_EVIDENCE = [
    ["261x", "15 trading truths you need to hear. (6-second loop, the list in the caption)"],
    ["68x", "'More trades = more money' and other beliefs that cost traders. (6-second loop)"],
    ["10x", "The harsh reality of trading."], ["2x on a small account", "One loss. That's all it takes for emotion to grab the wheel."]]
CHART_COUNT = {"Chart quiz": 3, "Guess the move": 2, "Speed cheat sheet": 3}
V2 = os.environ.get("REEL_V2") == "1"   # (the version-2 test track, posted as Trial Reels against the current reels: the owner's go, 2026-11-07)
V2_FORMAT = {
    "Chart quiz": "One question on one real game chart: a question scene (the game's options, each with a short label of at most 4 "
                  "words in \"labels\", a 5-second countdown), then an answer scene (the rest of the chart plays out, the right "
                  "option lights up, one line on why). Ask viewers to comment their answer before the reveal."}
V2_SAY = [("the reel's title, 2 to 5 words: its theme (e.g. 'Spot The Doji'), not the line",
           "the on-screen hook, 2 to 7 words: the reel's question, dare or stake, put in other words than the voice "
           "(e.g. 'Where Is Your Stop?', 'Only 1 In 5 Get This', 'One Dragon Cost 12%'), never an abstract theme"),
          ("the hook's title is the reel's theme", "the hook's on-screen text is the reel's question, dare or stake in other words than the voice"),
          ("A hook over a chart puts the reel's theme in its text, as a title;",
           "A hook over a chart puts the reel's question, dare or stake in its text (other words than the voice);")]


CHAMPION = os.path.join(ROOT, "CHAMPION.md")   # (a version 2 that won its Trial Reels round, promoted by lab/evolve.py: every regular reel follows it)
END_RULES = "\n\n(end of the rules above)\n\n"


def rules_file(category=None):
    """The rules this reel is made under: version 2's on the test track, else the promoted winner's (never the Daily recap's)."""
    if V2: return os.path.join(ROOT, "RULES_V2.md")
    if os.path.exists(CHAMPION) and category != "Daily recap": return CHAMPION


def v2_system(system, path=None):
    """Version 2's instructions (or the promoted winner's): its rules first, and the title rules that clash with them restated."""
    path = path or os.path.join(ROOT, "RULES_V2.md")
    head = ("RULES UNDER TEST (version 2)" if path.endswith("RULES_V2.md") else "RULES THAT WON THE TRIAL REELS TEST") + \
           ". Where they differ from anything below, the owner's rulebook included, these win:\n"
    if END_RULES in system: system = system.split(END_RULES, 1)[1]   # (one set of rules at a time: v2's replace the winner's)
    elif system.startswith("RULES UNDER TEST"): return system      # (a brief saved before 2026-11-08)
    for a, b in V2_SAY: system = system.replace(a, b)
    return head + open(path, encoding="utf-8").read() + END_RULES + system


def v2_brief(B, path=None):
    """The same facts in version 2's shape (a quiz keeps only its first chart) and with its instructions."""
    import copy
    B = copy.deepcopy(B)
    if B["category"] in V2_FORMAT:
        B["ask"]["what_this_reel_is"] = V2_FORMAT[B["category"]]
        if B["category"] == "Chart quiz":
            B["ask"]["facts"]["charts"] = B["ask"]["facts"]["charts"][:1]; B["charts"] = B["charts"][:1]
    B["system"] = v2_system(B["system"], path); B["v2"] = True
    return B


def pair(slot, w1, w2, category=None):
    """One brief, two reels: the current rules (w1) and version 2 (w2), on the same facts and chart (the Trial Reels test)."""
    B = brief(slot, category)
    B1 = v2_brief(B, CHAMPION) if rules_file(B["category"]) else B   # (v1 is the promoted winner, once there is one)
    save(write(B1, work=w1), B1, w1)
    B2 = v2_brief(B)
    save(write(B2, work=w2), B2, w2)


def get(path, body=None):
    for attempt in range(5):
        time.sleep(0.5 + attempt)                         # (the game's per-address limit on these)
        try:
            req = urllib.request.Request(SITE + path, data=json.dumps(body).encode() if body else None,
                                         headers={"content-type": "application/json"}, method="POST" if body else "GET")
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4: raise


def drill(kind):
    """A fresh chart test of `kind` with its answer: the question, then the game's marking of it (the candles that came
    next, the right answer and why). A new real chart every time, unlike a lesson's example."""
    q = get(f"/api/learn/test?kind={kind}")
    if "candles" not in q:
        raise RuntimeError(f"no chart test for {kind}: {q}")
    a = get("/api/learn/test", {"id": q["id"], "choice": 0})
    return dict(q, upto=len(q["candles"]) - 1, candles=q["candles"] + a["candles"], lines=a["lines"], marks=a["marks"],
                answer=a["answer"], result=a["result"], explain=a["explain"], where=a["where"])


def swings(C, a, b, k=4):
    """The clearest highs and lows between candles a and b (index, price), for Claude to point at."""
    out = []
    for i in range(max(a, k), min(b, len(C) - k)):
        if C[i][1] == max(c[1] for c in C[i - k:i + k + 1]): out.append(["high", i, round(C[i][1], 2)])
        if C[i][2] == min(c[2] for c in C[i - k:i + k + 1]): out.append(["low", i, round(C[i][2], 2)])
    return out[-10:]


def chart_from_drill(d):
    up, C = d["upto"], d["candles"]
    end = min(len(C) - 1, up + 25)
    if re.search(r"fake|back inside|fail", d["result"], re.I) and d["lines"]:
        # a fake or failed move: the reveal stops just after the close back across the level, so the payoff shows the
        # failure (25 candles on, the price can be anywhere, e.g. +40% after a "fake" breakout)
        lv = d["lines"][0]["price"]; side = C[up][3] > lv
        back = next((k for k in range(up + 1, end + 1) if (C[k][3] > lv) != side), None)
        if back is not None: end = min(end, max(up + 6, back + 3))
    return {"candles": C, "label": f"{d['where']['name']} · {d['where']['tf']}", "upto": up, "end": end,
            "win": [max(0, up - 70), end], "drill": d, "overlay": d.get("overlay") or []}


# formats that teach a signal show it working (the owner, round 7: "show the signal playing out in favour of the trader...
# then say it doesn't happen every time"): their example is one where the price did what the signal says
TEACH = ("Technical lesson", "Speed cheat sheet", "Explained like you're 5", "One trick")
UP = r"golden|bullish|hammer|morning star|uptrend|oversold|piercing|three white"
DOWN = r"death|bearish|shooting star|hanging man|downtrend|overbought|evening star|dark cloud|three black"


def played_out(d, need=2.0, strict=False):
    """True when the price after the question moved the way the right answer says (by `need` % or more), or when the
    answer says no direction (a doji, a Fibonacci level). A breakout or level: the side of the line it closed on, turned
    round for a fake or a break."""
    C, up = d["candles"], d["upto"]
    pct = (C[min(len(C) - 1, up + 25)][3] / C[up][3] - 1) * 100
    a = d["options"][d["answer"]].lower()
    if d.get("kind") in ("breakout", "level") and d.get("lines"):
        s = 1 if C[up][3] > d["lines"][0]["price"] else -1
        if re.search(r"fake|breaks?\b|fail", a): s = -s
    elif re.search(UP, a): s = 1
    elif re.search(DOWN, a): s = -1
    else: return not strict                           # (strict: a lesson's example needs a signal with a direction, never "no cross")
    return s * pct >= need


def teach_drill(kind, tries=8):
    """A drill whose signal played out (TEACH), or the last one tried."""
    for _ in range(tries):
        d = drill(kind)
        if played_out(d, strict=kind not in ("candle", "fib")): return d
    return d


def chart_summary(i, ch):
    d, C = ch.get("drill"), ch["candles"]
    s = {"chart": i, "candles": len(C), "label": ch["label"], "first_shown": ch["win"][0], "last": ch["end"],
         **({"overlay": ch["overlay"]} if ch.get("overlay") else {}),
         "swings": swings(C, ch["win"][0], ch["end"] + 1), "close_first": round(C[ch["win"][0]][3], 2),
         "close_last": round(C[ch["end"]][3], 2)}
    if d:
        s.update(question=d["q"], options=d["options"], right_answer=d["options"][d["answer"]], stops_at=d["upto"],
                 what_happened=d["result"], why=d["explain"], drawn_with_answer=[x["label"] for x in d["lines"] if x.get("label")])
        up, e = d["upto"], ch["end"]; c0 = C[up][3]; after = C[up + 1:e + 1]
        s["after_the_question"] = {                       # what the answer scene really shows: the script may say only this
            "note": "The candles revealed after the question, as numbers. Say only what these show; if what_happened seems to "
                    "say more, these numbers win.",
            "close_at_question": round(c0, 2),
            "closes_after": [[up + j + 1, round(c[3], 2)] for j, c in enumerate(after)][::max(1, len(after) // 8)],
            "pct_to_last": round((C[e][3] / c0 - 1) * 100, 1),
            "highest_after": round(max(c[1] for c in after), 2) if after else None,
            "lowest_after": round(min(c[2] for c in after), 2) if after else None,
            "levels": [{"label": x.get("label", ""), "price": round(x["price"], 2),
                        "closes_above": sum(c[3] > x["price"] for c in after), "closes_below": sum(c[3] < x["price"] for c in after)}
                       for x in d["lines"]]}
    return s


SITE_FACTS = [   # (web/about.html, 2026-11-10: keep in step with it)
    "A free stock market game for learning to trade; nothing in it is real money and nothing is investment advice.",
    "Every account starts with 1,000 MB (memebucks): practice money with no cash value, never paid out.",
    "A fictional stock market that never closes: 180+ invented companies, indices and funds; every company, person and headline is made up.",
    "News moves prices: rumours, earnings, launches, lawsuits and the odd shock, about companies with their own bosses, products and rivals.",
    "Prices follow the stories, never the players: nobody's trade moves a price.",
    "Trade stocks, the MSI 50 index of the 50 biggest companies, sector funds, 2x and 3x products and tiny 'moonshots'; go long or short; limit, stop-loss and take-profit orders; calls and puts.",
    "Fair by design: simple tricks like buying every dip don't beat holding the market (checked by simulating many markets with dozens of strategies), so skill shows.",
    "114 lessons in 20 units (charts, indicators, orders, risk, shorting, options, the economy, strategy testing, and three Expert units on the order book, volatility and position sizing), each a few minutes, plus chart tests on real game charts. A free account passes two lessons a day; Pro lifts that limit and Expert adds the Expert units.",
    "A new leaderboard every day; ranks count returns, so buying MB can't buy a better rank.",
    "The Daily Chart: two minutes on the same mystery chart as everyone else, a new one each day, with streaks and a result to share.",
    "Every trade costs 0.1% of its size, like a broker's fee, so you learn to count costs; no hidden spread.",
    "Works on a phone; the live market can be watched without signing in.",
]
DAILY_FACTS = [   # (game/daily.py, 2026-11-10: keep in step with it)
    "One chart a day, the same for everyone; a new one at midnight UTC; each day has a number.",
    "One made-up stock with no name, made by the game's own price model: legs, ranges, breakouts, support and resistance, chart patterns.",
    "Start shows 60 candles at once, the lead-in, to read the levels from; then one new candle every second for 120 seconds: two minutes.",
    "1,000 MB of paper money for the game, no fees; it never touches your real MB balance.",
    "Buy 25, 50, 75 or 100% of your cash; Sell 25, 50, 75 or 100% of your shares; selling with none opens a short (at most the account's worth); Buy covers a short.",
    "A trade is priced on the server at the candle showing when it arrives; the candles still to come never leave the server, so nobody can peek.",
    "At the end what you hold is valued at the last close; your score is your return.",
    "One game a day per account; visitors can play without an account but stay off the board.",
    "After the game: your return, your place, everyone's returns as a spread, what the stock itself did (holding), the levels, and the best trades you could have taken.",
    "The board: today's best returns; the last 7 days' top three are kept.",
    "Streaks of days played in a row, your best streak, average and best return, how often you beat just holding.",
    "A result grid of 8 squares (up, down or flat, one per 15 seconds) to share, like the daily word games.",
]


RSI_NOTE = ("The reel's chart draws candles and moving averages only: there is no RSI panel. Show the RSI yourself (a gauge or a needle "
            "with the reading the chart's facts give) and never say 'the panel under the chart'.")


def lru(options, history, key, n=1):
    """The `n` options that went out longest ago (never used first, in the order given), noted in history[key]."""
    used = history.setdefault(key, [])
    pick = sorted(options, key=lambda o: max((i for i, u in enumerate(used) if u == o), default=-1))[:n]
    used.extend(pick); del used[:-300]
    return pick


def lesson(rng, history):
    """One lesson of the site's curriculum as the facts: the one out longest ago, from the track out longest ago. With a real
    chart that shows it when a chart test of its kind exists (LESSON_KIND)."""
    ids = [(t, x) for t in get("/api/learn")["tracks"] if t["id"] in LESSON_TRACKS for x in t["lessons"]]; rng.shuffle(ids)
    used = history.setdefault("lessons", [])
    ago = lambda hit: max((i for i, u in enumerate(used) if hit(u)), default=-1)
    t, x = min(ids, key=lambda tx: (ago(lambda u: u == tx[0]["id"] + "/" + tx[1]["id"]), ago(lambda u: u.startswith(tx[0]["id"] + "/"))))
    used.append(t["id"] + "/" + x["id"]); del used[:-300]
    d = get("/api/learn/lesson/" + x["id"])
    text = [("## " + b["h"]) if b.get("h") else b.get("p") or "; ".join(b["list"]) for b in d["body"] if b.get("h") or b.get("p") or b.get("list")]
    facts = {"lesson": {"title": d["title"], "track": d["track_title"], "level": t.get("tier"), "summary": d["summary"], "text": text},
             "about_the_lesson": "The lesson's whole text. Teach one idea of it in depth and say nothing it does not say.",
             "_subjects": [d["title"]]}
    k = LESSON_KIND.get(x["id"])
    if k == "rsi": facts["about_the_rsi"] = RSI_NOTE
    return facts, [chart_from_drill((drill if k in ("rr", "stop") else teach_drill)(k))] if k else []   # (a stop or a reward-to-risk test has no direction to play out)


def gather(category, rng, history, company=None):
    """The facts for this reel, and the charts the renderer draws. `company`: a remake's company, by name."""
    facts, charts = {}, []
    if category == "Daily recap":                          # tonight's chart and its analysis (analyze.py), from fetch.py's file
        import analyze
        d = json.load(open(os.environ["DAILY_DATA"], encoding="utf-8"))
        A = analyze.analyse(d, os.environ.get("MS_USER", ""))
        C, H = A["C"], A["H"]
        facts = {"chart_number": A["number"], "stock_change_pct": round(A["hold"] * 100, 2), "clock_starts_at_candle": H,
                 "trades": [{"dir": t["dir"], "entry_candle": t["entry"], "exit_candle": t["exit"], "return_pct": round(t["r"] * 100, 2),
                             "why": f"{t['ev']['outcome']} at {t['ev']['price']}"} for t in A["trades"]],
                 "plan_total_pct": round(A["total"] * 100, 2), "plan_beat_holding": bool(A["total"] >= A["hold"]),
                 "best_player_pct": None if A["best_player"] is None else round(A["best_player"] * 100, 2)}   # (how many played is left out: a small number is no advertisement, and it counted the house bots; roadmap RL8, 2026-11-12)
        charts.append({"candles": C, "label": f"Daily Chart #{A['number']}", "upto": len(C) - 1, "end": len(C) - 1, "win": [0, len(C) - 1], "live_from": H})   # (reel.html shades the lead-in and draws a dotted line where the game began)
        facts["charts"] = [chart_summary(0, charts[0])]
        return facts, charts
    if category in EXPLAINERS:
        prev = [x for x in history.get("explainers", []) if x.get("category") == category][-6:]
        if category == "Meme Street explained":
            return {"site": SITE_FACTS, "previous_explainers": prev}, []
        days = sorted(f for f in os.listdir(os.path.join(ROOT, "data")) if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", f))
        d = json.load(open(os.path.join(ROOT, "data", days[-1]), encoding="utf-8")); C = d["game"]["candles"]; H = d["game"].get("history", 60)
        charts.append({"candles": C, "label": f"Daily Chart #{d.get('number')}", "upto": len(C) - 1, "end": len(C) - 1, "win": [0, len(C) - 1], "live_from": H})
        facts = {"daily": DAILY_FACTS, "previous_explainers": prev, "example_chart": {"number": d.get("number"), "lead_in_candles": H,
                 "live_candles": len(C) - H, "stock_change_pct": round((C[-1][3] / C[H - 1][3] - 1) * 100, 2)}}
        facts["charts"] = [chart_summary(0, charts[0])]
        return facts, charts
    if category in DEEP:
        if category == "Strategy test":                    # (src/backtest.py: the next rule in turn that made enough trades to judge)
            import backtest
            tickers = [c["ticker"] for c in json.load(open(PACK, encoding="utf-8"))["companies"]]
            for _ in backtest.TESTS:
                facts, charts = backtest.test(lru(list(backtest.TESTS), history, "tests")[0], get, tickers)
                if facts["sample"]["trades"] >= backtest.ENOUGH: break
            facts["_subjects"] = [facts["strategy"]]
        else:
            facts, charts = lesson(rng, history)
        facts["charts"] = [chart_summary(i, c) for i, c in enumerate(charts)]
        return facts, charts
    if category in ("Stock story", "Chart breakdown", "Breaking news"):
        pack = json.load(open(PACK, encoding="utf-8")) if os.path.exists(PACK) else {"companies": [], "templates": []}
        if company:                                      # (the same company as the reel it remakes, or no remake)
            want = company.lower()
            cos = [c for c in pack["companies"] if c["name"].lower() == want or c["name"].lower().startswith(want + " ")]
            if not cos:
                raise SystemExit(f"no game company called {company!r}: the original reel stays")
        else:
            done = set(history.get("tickers", [])[-30:])
            cos = [c for c in pack["companies"] if c["ticker"] not in done] or pack["companies"]
        rng.shuffle(cos)
        for co in (cos if company else cos + [c for c in pack["companies"] if c not in cos]):   # (the content pack has companies the live game does not list: every unused one is tried, then the ones used lately; trying only 8 left a Stock story unmade whenever the draw was 8 unlisted ones, 2026-11-12)
            try:
                st = get(f"/api/reel/stock/{co['ticker']}?tf=1h"); break
            except urllib.error.HTTPError as e:
                if e.code != 404: raise
        else:
            raise SystemExit("no listed company found: the original reel stays")
        news = [t for t in pack["templates"] if t.get("sector") == co["sector"]][:2]
        facts = {"company": st["name"], "ticker": st["ticker"], "what_it_does": st["desc"], "sector": co["sector"],
                 "price_now": round(st["price"], 2), "good_news_examples": sum((t["up"] for t in news), [])[:3],
                 "bad_news_examples": sum((t["down"] for t in news), [])[:3],
                 "about_the_news_examples": "These headlines are about the company's whole sector, other companies in it included. Use one only "
                                            "when it plainly fits what THIS company does (what_it_does); never give this company a tower, a mine or "
                                            "a product from a headline that is about another business (the critic held a reel for it, 2026-11-12)."}
        if category == "Breaking news" and news:         # (the pack's cross effects: good news here lifts or sinks these sectors, bad news the reverse)
            facts["news_also_moves"] = {"when": f"good news for {co['sector']} (bad news does the reverse)",
                                        "sectors": {k: "up" if v > 0 else "down" for k, v in (news[0].get("betas") or {}).items() if k != "self" and v}}
        C = st["candles"]
        if category == "Chart breakdown":                # (a stock story is just the company: no chart in its facts)
            charts.append({"candles": C, "label": f"{st['name']} ({st['ticker']}) · {st['tf']}", "upto": len(C) - 1,
                           "end": len(C) - 1, "win": [0, len(C) - 1]})
            facts["charts"] = [chart_summary(0, charts[0])]
        history.setdefault("tickers", []).append(co["ticker"])
    else:
        kinds = KINDS[category][:]; rng.shuffle(kinds)
        kinds = lru(kinds, history, "kinds", CHART_COUNT.get(category, 1))   # (the kind out longest ago, over all formats)
        facts["_subjects"] = [SUBJECT.get(k, k) for k in kinds]
        if "rsi" in kinds: facts["about_the_rsi"] = RSI_NOTE
        for k in kinds[:CHART_COUNT.get(category, 1)]:
            charts.append(chart_from_drill(teach_drill(k) if category in TEACH else drill(k)))
    facts["charts"] = [chart_summary(i, c) for i, c in enumerate(charts)]
    return facts, charts


SCHEMA = """Reply with JSON only, no prose, in this shape:
{"title": "cover title, 2 to 5 words", "type": "%s",
 "hooks": ["three different spoken hook lines, best first"],
 "scenes": [ ...in order... ],
 "caption": "the Instagram caption"}
Scene kinds (each has "vo": the spoken line, plain words, max 26 words, contractions welcome):
 {"kind":"hook","vo":"the first hook line","shot":"(when video is available) the cinematic shot behind the hook","text":"the reel's title, 2 to 5 words: its theme (e.g. 'Spot The Doji'), not the line","chart":N or null}
 {"kind":"chart","chart":N,"head":"title, max 5 words: names the idea (e.g. 'The Setup'), not the line","vo":"...","show":candle index shown at the start (optional),
   "cues":[{"say":"exact phrase from vo","do":"reveal","to":index} | {"say":"..","do":"mark","i":index,"label":"max 12 characters","side":"high"|"low"|"vol" (vol: rings that candle's volume bar against the 20-candle average),"tone":"amber|green|red|teal"}
          | {"say":"..","do":"line","price":number,"label":"max 3 words","tone":"amber|green|red|teal"} | {"say":"..","do":"shade","from":index,"to":index,"tone":"green|red|amber"}
          | {"say":"..","do":"zoom","from":index,"to":index} | {"say":"..","do":"arrow","price":number,"i":index,"label":"max 2 words","tone":"red|green|amber|teal"} (a bold arrow pointing at that price at candle i: where a stop or entry goes)]}
   (a chart whose facts list "overlay" draws those moving averages by itself, all the way: sma20 an orange line, sma50 a blue one.
    Say "the orange line" and "the blue line" only on such a chart; never draw them with "line" cues)
 {"kind":"question","chart":N,"badge":"Q1","head":"max 5 words","vo":"asks it and reads the options","labels":["max 4 words", ...]}   (options and answer are added from the facts; "labels" are the short words shown on the option cards, one per option in order, needed whenever an option is over 4 words: "Held support", "Far below")
 {"kind":"answer","chart":N,"vo":"says the answer first, then why, max 26 words","cues":[...]}
 {"kind":"cards","head":"max 5 words","vo":"...","items":[{"text":"max 4 words","sub":"max 7 words","icon":"up|down|warn|check|cross|coin|clock|bolt|chart|shield|people|idea"}],
   "cues":[{"say":"exact phrase","do":"item","i":0}, ...one per item]}
 {"kind":"big","text":"max 7 words, shown huge","vo":"..."}
 {"kind":"stick","head":"max 5 words","vo":"...","chart":N or null (with a chart: one presenter figure beside it),
   "figures":[{"pose":"stand|think|panic|happy|point|pointl|sad|shrug|walk","label":"max 2 words","color":"white|teal|amber"}] (1 to 3 figures; none with a chart beyond the first),
   "cues":[{"say":"exact phrase","do":"pose","fig":0,"pose":"panic"} | {"say":"..","do":"bubble","fig":0,"text":"max 5 words"} | chart cues as above]}
 {"kind":"film","head":"title, max 5 words","vo":"...","shot":"one realistic cinematic shot, 15 to 50 words, written like a
   director's shot list: the subject, what it is doing, where, the light, the camera move. E.g. 'A green dragon hauls a
   wooden crate on chains over a misty mountain ranch at golden hour, wings beating slowly, camera tracking alongside'"}
   (only when video is available: a full-screen realistic video clip with the title and captions over it)
 {"kind":"story","head":"title, max 5 words","vo":"...","layout":"pens|earns|line|storm|candles|hero|flow|grow|risk|compare|network",
   "props":[{"p":"<prop>","color":"teal|green|amber|red|purple|grey","label":"max 3 words, or empty","say":"exact phrase from vo: it pops in then"}]}
   (an animated 2D scene in the house style. Layouts: pens = the company's home: two gated enclosures, each with two of
    props[0] (the animals or products, e.g. dragons) and props[1] in the middle (e.g. a hut); line = props[0] (the company)
    bottom left, then six of props[1] (people) pop up one by one into a line: demand, a waiting list (label props[1]
    'Waiting list'); candles = red candles fall across the whole screen and burst into the next scene: what moves or hurts
    the stock (props[0] may carry the label); earns = how it makes money: props[0] the company (a flier flies from job to
    job), props[1..3] its 3 jobs, each a prop with a 1-3 word label, and each pays out coins on its word; storm = what can
    hurt it: props[0] the company, props[1..3] the risks (a warning or a fitting prop, each labelled), a storm rolls in and
    each risk strikes as lightning on its word; flow = props[:-1] are stations left to right and the last prop travels through them
    (two portals and a crate: teleport freight); network = each prop is a node on a glowing globe, links fill in (2-8; only for a company that really is a network);
    hero = props[0] is the company, big in the middle (a flier circles above its plinth), the rest stand around it;
    grow = up to 5 columns rise one by one on their words (good news, growth); risk = props[0] is the company, the rest
    are warnings or shields that fly in and hit it (bad news); compare = props[0] the old way (shown grey), props[1] the new
    way, props[2] the thing they move; stage = the backdrop for a shot. Props: %s)
   An acted scene (every hook, and a story scene on layout stage) is a SHOT from the library, never free actors or beats (the owner,
    2026-11-08: free arrangements looked ugly): {"layout":"stage","act":"<shot name>","cast":{"<role>":{"p":"<prop>","color":"teal","label":
    "max 3 words, or empty"}},"on":{"<moment>":"exact phrase from vo"}} plus the shot's options. Each moment happens on its phrase, with
    its own motion and sound; positions and sizes are fixed. Shots (name: what it acts out. roles; moments; options):
<<SHOTS>>
 {"kind":"free","vo":"...","text":"the punch caption: 2 to 5 words of the line, in order","hot":"the one word of the text shown in the hot colour","chart":N or null,"show":candle index shown at the start (optional),
   "cues":[chart cues as above (with a chart they draw themselves under your scene), and {"say":"exact phrase from vo","do":"fx","name":"<a name your scene function reads>", ...any fields you need}]}
   (a director reel's own scene: your scene function draws its world, HUD and effects, and a punch headline over the transcript captions; no "head": the HUD takes the title's place)
 {"kind":"outro","text":"max 6 words","vo":"one ask, ending with memestreet.net"}
Top level, next to "scenes": "device": {"metaphor": "what the picture is, one line", "opening": "the first second", "palette": "the two or three colours", "hud": "what the HUD shows and how it changes"},
 and "tok": {"css": "body{background:#0b0906!important}"} for the reel's own background (optional).
After the JSON, ONE fenced block with the scene function (see DIRECTOR REELS):
```js
({t, T, s, i, R, api}) => { ... return html }
```
"""

DIRECTOR = """DIRECTOR REELS (the owner, 2026-11-09: "REALLY over-the-top, cool animations with more expressive explanations; each reel
unique, easy to understand and visually awesome"). Every reel is a short film: ONE visual device of your own invention carries
the whole lesson from the first second to the payoff; a HUD changes under the story; the reel has its own palette and mood;
captions are punches; then the sign-off. Read "exemplar_notes" in the request for the level. Never reuse a device from
"recent_devices" or copy one from the notes: thousands of such reels exist, invent the one that IS this lesson.
You write two things: the JSON script (scenes mostly of kind "free"; "question" and "answer" for a quiz; "chart" when the
chart alone is the picture; "big" and "outro" as before), then, after the JSON, ONE fenced ```js block holding the scene function:
  ({t, T, s, i, R, api}) => { ... return html }
It runs for every frame (30 a second): t is the time in seconds, T the reel's length, s the current scene, i its index, R the
whole timeline (R.scenes, R.charts[n].candles as [open, high, low, close, volume], R.device) and api the helpers. It returns an
HTML string drawn over the chart and under the end card: one <svg width="1080" height="1920" style="position:absolute;left:0;top:0">
with everything you draw, plus api.punch(s, t). It is pure: the same t always draws the same frame (no Math.random, no Date,
no document or window, no state kept between calls), and it never throws (guard every lookup: a chart may be null).
Timing comes from the scene: s.t0/s.t1 (the scene on screen), s.vs/s.ve (its voice line), api.at(s, "exact words") (the second
a phrase of s.vo starts), s.text_t[k] (when punch word k lands), each cue's c.t (from its "say"; a cue {"do":"fx","name":...} is
yours to read; the chart cues draw themselves). R.scenes[k] gives any scene's times, so a counter can keep running across
scenes and the device can persist. Ease everything: api.seg(t,a,b) is 0..1 between a and b; api.io, api.out, api.back are
easings (back overshoots: a pop); api.lerp(a,b,u); api.cl(x,lo,hi) clamps.
Drawing helpers: api.PROP2D[name](colour, u) is the svg of a prop standing on (0,0), about 200 px tall, u seconds alive
(names: %s); api.prop2d({p, color}, x, y, scale, t, t0, j) places one, popping in at t0; api.fig({pose, color, label, x, y,
sc}, t) draws a stick figure standing at x on ground y, sc its size (poses: %s; color any #hex); api.boomFx(cx, cy, u, R, colour)
a burst at u 0..1; api.icon(name) an 84 px icon (up, down, warn, check, cross, coin, clock, bolt, chart, shield, people, idea);
api.esc(text) for every string you print; api.ln(colour, width) and api.bd(colour, width) are stroke-only and filled attribute
strings for paths; api.G, api.RD, api.AM, api.TE the house green, red, amber and teal (your own colours are welcome).
api.chart() is the drawn chart's transform when the scene has a chart, else null: {X(k): candle k's x, Y(price): a price's y,
bw: a candle's width, r: candles revealed so far, n, C: the candles, lo, hi, PL: the plot box {x,y,w,h}}: glow a candle, point at a
price, draw your own marks in real pixels. Setting api.cam = {k, ox, oy} inside your function pushes the camera on the chart
(k 1..1.3 around ox, oy; ease it in and out); the HUD stays put.
Geometry (1080 x 1920; Instagram covers y < 230, y > 1440 and the right 230 px of the lower half): brand header y 250-310
(hidden until scene 1: in scene 0 the template draws your hook at y 236-382, so draw nothing above y 384 in scene 0);
your HUD y 380-500 (a free scene has no head); the world y 520-1290 (when the scene has a chart it fills that band, so draw on
the chart's own pixels or in its margins, never below y 1260); the punch headline at y 1270-1325 (api.punch draws it: keep that band
clear); the transcript captions at y 1384-1440 (the template draws every spoken word there, in every scene); nothing below 1440. Every text you draw is 26 px or more (34+ for anything that matters); the renderer rejects smaller.
Nothing you draw may cover words: the dry run rejects text over other text and a stick figure's head over any text (a speech
bubble goes beside or above the head, never on the face; keep figures, rings and arrows clear of every tag, the chart's own
label and price tag included). A number, a result or a verdict in your HUD appears on the word that says it, never before:
gate it with api.at(s, "the words") or the cue's time. A screen that runs ahead of its voice is the critic's most common reason to hold a reel.
Palette: the reel's own two or three colours on a dark background: "tok": {"css": "body{background:#...!important}"} once,
then your colours in the svg. The brand header stays readable.
The first 3 seconds decide the reel. Scene 0 is a free scene whose punch "text" (2 to 5 short words, from its first
sentence) is the hook: the template draws it whole on the very first frame, large (72 to 90 px) at the top, and keeps the
brand header, the format label and the progress bar hidden until scene 1 starts (api.punch returns nothing in scene 0, so
nothing doubles). The first spoken words are the stake or a question to the viewer: never a label ("Stock story: ..."), a
format promise ("Three chart reads in thirty seconds", "Here are three ..."), a definition ("A stop loss is an order
that ...") or a greeting. Scene 0 opens on a character or an odd object, your device already in motion, never on a chart
or a list: a chart arrives in scene 1 or later.
Seconds 3 to 15 decide who stays: our viewers give a reel about 7 seconds whatever its length, and they leave where the
hook hands over to the lesson. So scene 0 is the hook alone, 16 spoken words at most, and it opens a question it does not
answer: the answer is the payoff, kept for the last scene before the outro. Scene 1 is a second hook, never the start of
the lesson: it raises the stake or turns the first picture ("And that was the good day."), and the picture changes with
it. No background straight after the hook (what the company is, when it began, what a term means): background rides
inside the action, a clause at a time; a Stock story names the company inside that second hook, never as an
introduction. A beat lands at least every 4 seconds of speech (a punch, an fx cue or a chart cue on a word of the line),
so no line is talked over a waiting picture.
Sends and comments: the premise itself gives the viewer someone to send it to ("which level are you", one thing against
another, an absurd made-up company). The reel has one question to the viewer, asked in the hook or the middle, never in
the outro, and it is the first line of the caption. The outro is the sign-off alone, 10 words at most, so the ending
takes two seconds.
Motion: the first five seconds move the most: the device arrives, builds or acts while the hook is spoken (never a finished
picture waiting for the voice; the dry run fails a still opening more than anything else). Then something changes every 2 to
3 seconds (a counter ticks, a thing moves, a tag lands); impacts have weight (a wind-up,
the hit, a 4 px shake for 0.3 s, dust or a ring); things arrive by rising or scaling in with api.back, never by blinking in;
nothing jitters; a repeated action changes something each time (the HUD, a tag, a colour). Big: the device fills the middle of
the frame; figures a third of the frame tall. Sound-off test: the device, the HUD and the punches tell the story alone.
Scene kinds and your function: in "free" scenes you draw everything (world, HUD, effects; with a "chart" the chart draws
itself under you). In "big" and "outro" scenes return '' (the big line and the end card stand alone). In "question" and
"answer" scenes the template draws the chart, the title with its Q badge, the option cards and the countdown (s.options,
s.answer, s.think_t, s.opt_t): draw only your HUD, and only in the strip y 335-372 with no text in it (the title row is
taken), or nothing. A "chart" scene is a free scene without a punch. Keep the device alive across scenes: a counter that
persists, a world that stays and changes.
Performance: under 300 svg elements a frame, no blur filters over big areas, no loops over thousands of points.
Before it is voiced the whole reel is run through your function: a JavaScript error, text on text, text under 26 px, three
seconds with no visible change, or slow frames come back to you as errors to fix; fix the function, keep the device.
EXAMPLES, each a complete reel the renderer has run (copy the craft, never the device):
%s
"""


def examples():
    """The seed reels in src/scenes/: each scene function with its fixture's scenes, for the writer to learn the craft from."""
    out = []
    for f in sorted(glob.glob(os.path.join(HERE, "scenes", "*.js"))):
        name = os.path.basename(f)[:-3]; fx = os.path.join(HERE, "scenes", "fixtures", name, "spec.json"); sp = {}
        if os.path.exists(fx):
            sp = json.load(open(fx, encoding="utf-8")); sp = {k: v for k, v in sp.items() if k in ("device", "tok", "scenes")}
        out.append(f"=== {name}: the JSON (scenes)\n{json.dumps(sp)}\n=== {name}: the scene function\n```js\n{open(f, encoding='utf-8').read().strip()}\n```")
    return "\n".join(out)


_R = open(os.path.join(HERE, "reel.html"), encoding="utf-8").read()
WORLD_PROPS = re.findall(r"^ (\w+)\(c(?:,u)?\)\{", _R[_R.index("const PROP2D={"):_R.index("function prop2d(")], re.M)   # (the 2D story kit in reel.html)
SCHEMA = SCHEMA.replace("<<SHOTS>>", shots.schema())                        # (the scene library: src/shots.py)
WORLD_LAYOUTS = re.findall(r"lay==='(\w+)'", _R)
POSES = re.findall(r"^ ?(\w+):\{la:", _R[_R.index("const POSE={"):_R.index("const MOOD=")], re.M)   # (the stick figure's poses)
WORLD_VERBS = re.findall(r"(\w+):[\d.]+", _R[_R.index("BEAT={"):_R.index("}", _R.index("BEAT={"))])        # (the storyboard verbs reel.html acts)
WORLD_SLOTS = re.findall(r"'?([\w-]+)'?:\[", _R[_R.index("const SLOT={"):_R.index("}", _R.index("const SLOT={"))])
EVENT_VERBS = ("hit", "fall", "launch", "burst", "emit", "grow", "fling", "crack"); LAYOUT_EVENT = {"earns": "emit", "storm": "hit", "candles": "burst", "pens": "pens", "line": "line", "compare": "compare", "flow": "flow", "grow": "rise", "network": "network", "hero": "hero", "risk": "risk", "updown": "updown"}   # (a layout with its own event)
EMITS = ("fire", "coins", "smoke", "sparks", "rain", "hearts")
LAYOUT_PROPS = {"flow": 4, "network": 8, "hero": 5, "grow": 5, "risk": 5, "compare": 3, "pens": 2, "line": 2, "candles": 1, "earns": 4, "storm": 4, "stage": 2, "updown": 2}   # (what each layout in reel.html draws; more are never seen)
FLIERS = ("dragon", "bird", "plane", "drone", "fish", "rocket")   # (a flying hero leaves 3 side slots, not 4)
UNACTED_HOOK = ("Daily recap", "Trader levels", "Explained like you're 5", "Stick skit", "Truth list")   # (recap.html, and stick figures already act every scene)
WORLD_COLOURS = ["teal", "green", "amber", "red", "purple", "white", "grey"]

RULES_ALL = """Rules:
- Something happens in every story scene (the owner, 2026-11-07): one physical event, literal to the line. An acted scene is a shot
  from the library (the owner, 2026-11-08): pick the shot whose action IS the line, cast it with the things the line names, and tie
  its moments to the words; a layout scene (pens, earns, storm, line, compare, flow, grow, network, hero, risk, candles) acts by
  itself. Never a figure of speech (no box hitting a box for 'the market crashed'): the thing the line names does what the line
  says. Two scenes in a row never open with the same event, and a stock story uses at least 3 different ones. Examples:
  "One escaped dragon shut a motorway for a day": shot crash_landing, cast a truck, b dragon, on land 'shut a motorway'.
  "It went up like crazy, then crashed": shot rise_fall, cast hero rocket, on up 'went up', down 'then crashed'.
  "Every rental pays it": shot pour, cast source dragon, pile goldbar, what coins, on pour 'pays it'.
  "Support held 24 times": shot count, cast hero shield (label 'Support'), number '24 times', on count '24 times'.
  Invent your own casting for each line; the shots stay as they are.
- Cast literally (the owner's ratings, 2026-11-08): people are people (sellers, buyers, customers: person props, sellers red),
  a company is shown as what it does (dragons for a dragon ranch, never a generic factory or building), a brand is its
  product, a reservoir is a lake, a record hatch is an egg hatching a baby dragon (reveal), an escape is a dragon breaking
  out of its cage (reveal). Tags name the real thing ('Trucks', 'Customers'), never an idea ('Old way', 'Waiting list').
  If no shot and prop can show a line literally (a sickness, a recall in stores worldwide), act out another line of the
  scene, or use a story layout; never a stand-in. Every prop in a scene is one the line names: nothing extra in a corner.
- Every reel's hook is acted, like a stock story's (the owner, 2026-11-08: "all reels should be the same as the stock
  stories"): a shot (or a story layout) on the hook's words; the chart comes in from scene 1. A chart reel's hook acts out what
  the chart is about to do ("It looked like a small dip": rise_fall with a rocket; "Fear picks a tight stop": shield, guard a
  shield, threat a cloud). A quiz's hook shows the quiz: "Three charts, three questions: how many can you get?" is three_up, cast
  item1 to item3 chart, topper question, on items 'Three charts', topper 'three questions' (never blank bars standing in for
  charts). For trading things use the trading props: chart (a mini chart card), candle (green up, red down), question (a
  question card); they stay upright, so cast them in roles that do not fly or fall. Any reel may add one more story scene for
  its payoff (the moment the lesson lands, acted out); a quiz's reveal stays on the chart. Charts stay charts.
  Every reel opens with its own shot (the owner, round 7): never one in the facts' hook_shots_used_lately.
- One label per idea in a story scene: people queuing are a "queue" prop labelled with who they are ("Customers"), not a person plus separate
  labels. Animated "story" scenes (2D neon line art) show real things: a stock story has 2 or 3 (what the company does, its good news, its bad
  news), and any reel may use one when a real object acts out the line (a company, its product, money moving). A dragon-
  rental firm is a dragon circling its ranch, teleport freight is crates through portals, a recall is warnings hitting
  the company. Never an abstract stand-in for an idea (a box for 'your trade', triangles for 'panic'): if a viewer could
  not tell what it shows in one second with the sound off, use the chart, cards or Rookie and Pro instead. Charts stay charts.
- Video (only when the ask's "video" says it is available): a stock story shows the company's business and its good
  and bad news as 2 or 3 film scenes; every other reel puts one "shot" on its hook (the first thing anyone sees, so make
  it striking). A shot shows the line's subject doing something specific and physical, fictional (no real brands,
  places or people), no text or screens in frame. Charts stay charts.
- Teach a signal by showing it work (the owner, round 7): name the signal, point at it, then reveal what the price did next
  (it went the way the signal says: the facts' example was picked for that), then say why it worked in two or three plain
  reasons (who was buying, what the level meant, what the volume showed). Only then, once and briefly near the end, say it
  does not work every time. Never call a signal "only a clue", "never a promise" or "not a verdict" more than once in a
  reel, and never lead with the doubt: the doubt is a footnote, the signal working is the lesson.
- When the voice describes the price moving ("each step lower than the one before", "it climbs", "then it dropped"),
  the candles draw as it is said: put a reveal cue on that phrase, with the candles before it hidden ("show" earlier).
- One look per idea: a stop or entry is one arrow (cue "arrow"), never a line for each option; in a quiz answer the arrow
  at the right stop is drawn for you.
- Plain words: "slightly below", never "a hair below"; "just above", never "a tad above".
- Say a price the way it is shown on screen: under 10 it keeps its point ('4.91' is 'four point nine one', never 'four ninety-one', which the captions would show as 491); from 10 up, 'two oh three' for 203 is fine.
- Total spoken words 60 to 110 (about 25 to 35 seconds): concise, one idea, every line earning its place, unless the
  reel's description says otherwise. No greeting, no "in this video". Start at the hook.
- The first scene is a hook; the last is the outro. Change what is on screen every scene.
- Every number, name and outcome must come from the facts. Never invent results, prices, people or history.
- Candle indices in cues must be between a chart's first_shown and last. "say" must be words that appear in that scene's vo.
- Show what you say: a scene that talks about candles, the chart, a breakout, volume or wicks has that chart on screen
  (stick scenes too: give them the chart). Talking about volume? Mark the candle with side "vol".
- A mark, shade or zoom only points at candles already on screen at that moment: at or before the scene's "show"
  (or where the scene before it on the same chart ended), or revealed earlier in the same scene.
- Few cuts, like the owner's reference reels: keep one chart on screen and let it evolve from scene to scene (reveal,
  mark, shade, zoom, lines); switch to cards, big text, Rookie and Pro or a story scene only when the chart cannot show
  the point. Every switch of what fills the screen is a cut; a stock story allows 5, any other reel 3 (the outro is free).
- Big text and outro text are words of that scene's line, word for word, in order.
- Titles are titles: each head names that scene's idea, 2 to 5 words, never a copy of what the voice says, and the same
  style through the reel. A hook over a chart puts the reel's theme in its text, as a title; a hook
  with no chart shows its own first words big as they are said, so there the text IS the first words of the line. An answer's title is set for you (it never
  gives the answer away: the highlight shows it).
- A figure's label is its name ("Rookie", "Pro") or role, never a copy of the scene's head.
- Proper capitals everywhere: every sentence, title, head, card, bubble, label and on-screen line starts with a capital
  letter; names keep theirs ("Ember Dragon Ranches", "Rookie", "I"). On-screen text taken from the middle of a line
  still starts with a capital ("Level cost you 11%" reads wrong; take a whole phrase: "This level cost you 11%").
- The caption: first line is the question the reel asks the viewer, whole before the "... more" cut (one line with a
  question mark, under 125 characters), then 2 to 5 short lines that name the topic in the plain words people search for
  ("stop loss", "candlestick chart", "day trading", "stock market"),
  one ask (comment, save or follow), "Practise at memestreet.net", then exactly "Fictional market. Not investment advice.",
  then 3 to 5 hashtags including #MemeStreet. No emoji anywhere. British spelling.
- Talk the way the best finance narrators do (measured on 16 top Shorts): full, flowing sentences of 10 to 20 words,
  joined the way people join them ("so", "and", "but", "because", "which means", "now"), pointing at the chart with
  "here" and "right here". One short punchy fragment ("But then, crash.") at most once in a reel; never stack
  fragments ("Clean. Strong." / "Calm. Boring. Lovely." read like an advert, not a person).
- Sound like a person talking to ONE viewer: "you", contractions, short punchy lines, one surprising real number,
  a question to the viewer now and then. Never read a list aloud. No stiff phrases ("in today's video", "let's dive in",
  "it's important to note", "in conclusion", "delve"). Calm, clear, never hype.
- Write prices the way people say them ("about two ten", "a hundred and twelve"), never with decimals in the spoken line.
- Stick scenes use the two recurring characters: label "Rookie" (white) for the beginner and "Pro" (teal) for the one
  who knows. Same names in every reel.
- The outro is the sign-off alone, 10 words at most, with no promo sentence and no question: one short echo of the hook
  if you like (the replay then loops cleanly), and it always ends with:
  "Join free at memestreet.net." Only a reel about the Daily Chart (the Daily recap) mentions the Daily Chart.
"""
# (the owner, 2026-11-09: every reel is a director reel, so the shot-library, acted-hook, cut-count, video and 60-110 word
#  rules go; the rest stand)
_GONE = ("- Something happens in every story scene", "- Cast literally", "- Every reel's hook is acted", "- Video (only when",
         "- Few cuts, like the owner's reference reels", "- Total spoken words 60 to 110", "- The first scene is a hook")
RULES = "Rules:\n" + "".join(b for b in re.split(r"(?m)(?=^- )", RULES_ALL.split("Rules:\n", 1)[1]) if not b.startswith(_GONE)) + \
    "- Length: 35 to 60 seconds (50 to 150 spoken words), as long as the story earns and no longer; every line earns its place.\n" \
    "  No greeting, no \"in this video\". The first scene opens on the device; the last is the outro.\n"


def claude(messages, system, model=None):
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY is not set (run set_claude_key.ps1)")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", method="POST",
                                 data=json.dumps({"model": MODEL, "max_tokens": 6000, "system": system, "messages": messages}).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return "".join(b.get("text", "") for b in json.loads(r.read())["content"])


EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")


def board_check(k, s, A, B):
    """A scene's storyboard, if it has one: actors that exist on slots that exist, beats whose verbs reel.html acts, on words
    of the line, naming actors of this scene."""
    errs, ids = [], [a.get("id") for a in A]
    if len(A) > 5: errs.append(f"scene {k}: at most 5 actors")
    if len(B) > 8: errs.append(f"scene {k}: at most 8 beats")
    if not all(ids) or len(set(ids)) != len(ids): errs.append(f"scene {k}: every actor needs its own id")
    ats = [a.get("at") for a in A if a.get("at")]; sky = {a.get('id'): a.get('at') for a in A}
    if len(set(ats)) != len(ats) and not s.get("act"): errs.append(f"scene {k}: two actors share a slot; give each its own")
    for a in A:
        if a.get("p") not in WORLD_PROPS: errs.append(f"scene {k}: no prop called {a.get('p')!r} for actor {a.get('id')}; use one of {', '.join(WORLD_PROPS)}")
        if a.get("color", "teal") not in WORLD_COLOURS: errs.append(f"scene {k}: actor {a.get('id')} colour {a.get('color')!r} is not one of {', '.join(WORLD_COLOURS)}")
        if a.get("at") and a["at"] not in WORLD_SLOTS: errs.append(f"scene {k}: actor {a.get('id')} slot {a['at']!r} is not one of {', '.join(WORLD_SLOTS)}")
        if a.get("size", "m") not in ("s", "m", "l"): errs.append(f"scene {k}: actor {a.get('id')} size is s, m or l")
        if a.get("size") == "l" and str(a.get("at", "")).startswith("sky"): errs.append(f"scene {k}: actor {a.get('id')} in the sky is s or m (an l covers the title)")
        if len(str(a.get("label") or "").split()) > 3: errs.append(f"scene {k}: label {a.get('label')!r} is over 3 words")
    for b in B:
        if b.get("do") not in WORLD_VERBS: errs.append(f"scene {k}: no beat called {b.get('do')!r}; use one of {', '.join(WORLD_VERBS)}"); continue
        if b.get("who") not in ids: errs.append(f"scene {k}: beat {b['do']} names actor {b.get('who')!r}, which this scene has not got")
        if b["do"] == "hit" and (b.get("with") not in ids or b.get("with") == b.get("who")): errs.append(f"scene {k}: a hit names the other actor in 'with'")
        if b["do"] in ("move", "launch") and b.get("to") not in WORLD_SLOTS: errs.append(f"scene {k}: {b['do']} needs 'to', one of {', '.join(WORLD_SLOTS)}")
        if b["do"] == "grow" and b.get("to", "l") not in ("s", "m", "l"): errs.append(f"scene {k}: grow 'to' is s, m or l")
        if b["do"] == "grow" and b.get("to", "l") == "l" and str(sky.get(b.get("who"), "")).startswith("sky"): errs.append(f"scene {k}: a sky actor grows to m at most (an l in the sky covers the title)")
        if b["do"] in ("launch", "fall", "hit", "fling") and str(A[ids.index(b.get("who"))].get("p") if b.get("who") in ids else "") in ("candle", "chart", "question"):
            errs.append(f"scene {k}: a {A[ids.index(b['who'])]['p']} never flies, falls or crashes (the owner, 2026-11-08); it grows, tints, bursts or counts where it stands")
        if b["do"] == "fall" and b.get("to") not in (None, "off"): errs.append(f"scene {k}: fall 'to' is left out (the ground) or 'off'")
        if b["do"] == "emit" and b.get("what") not in EMITS: errs.append(f"scene {k}: emit 'what' is one of {', '.join(EMITS)}")
        if b["do"] == "tint" and b.get("color") not in WORLD_COLOURS: errs.append(f"scene {k}: tint needs a colour")
        if b["do"] == "count" and not re.search(r"\d", str(b.get("text", ""))): errs.append(f"scene {k}: count 'text' has the number in it")
        if b.get("say") and b["say"].lower() not in s.get("vo", "").lower(): errs.append(f"scene {k}: beat {b['do']} says {b['say']!r}, which is not in its line")
    return errs


# The first spoken sentence may not be a label, a format promise or a definition (docs/ROADMAP.md A2). A floor, not a
# judge: it catches the openers that waste the first second and cannot rank good ones (the selftest holds its examples).
BAD_OPENER = re.compile(r"""(?ix)^\W*(?:
    (?:here\s+(?:are|is)|here\x27s|today(?:\x27s|\s+(?:we|i|let))|in\s+this\s+(?:reel|video|lesson|one|short)|this\s+(?:reel|video|lesson)|let\x27?s|welcome)\b   # a preamble
  | (?:[\w\x27]+\s){0,2}[\w\x27]+:\s                                                       # a label: "Stock story: ..."
  | (?:\w+\s+){0,4}(?:explained(?=\W*$|\s+in\s)|101\b|quiz\s+time\b|cheat\s+sheet\b)      # a label: "Support and resistance explained"
  | (?:\w+\s+){0,3}(?:lesson|tip|rule|part|mistake|truth|myth)\s+(?:\#|number\s|\d|(?:one|two|three|four|five)\b)   # "Lesson four", "Trading mistake number one"
  | (?:\d+|two|three|four|five|six|seven|eight|nine|ten)\s+(?:[\w,\x27]+\s+){1,4}?
      (?:in\s+(?:\w+\s+)?(?:seconds?|minutes?)|each\b|every\s+(?:trader|beginner|investor)|(?:that|you)\s+(?:\w+\s+)?(?:need|should|must)|to\s+(?:know|avoid|watch|learn))   # a format promise: "Three chart reads in thirty seconds"
  | (?!(?:this|that|these|those|your?|my|it|he|she|they|we|i|the\s+market)\b)[\w\x27 -]{2,40}?\s(?:is|are)\s+(?:an?|the)\s+[\w\x27 -]{2,40}?\s(?:that|where|which|when|used)\b   # a definition: "A stop loss is an order that ..."
  | [\w\x27 -]{2,40}?\s(?:is\s+when|means\s+that|refers\s+to|is\s+defined)\b
)""")
BACKGROUND = re.compile(r"""(?ix)^\W*(?:      # scene 1 is a second hook, not background (docs/ROADMAP.md A3); a floor, as above
    (?:the\s+)?(?:company|firm|business)\s+(?:is|was|makes|sells|builds|runs|started|began)\b                   # "The company makes ..."
  | [\w\x27&. -]{2,40}?\s(?:is|are|was)\s+(?:an?|the)\s+(?:[\w\x27-]+\s+){0,4}?(?:company|firm|business|maker|builder|seller|startup|brand)\b   # "Deepwater Homes is a builder ..."
  | (?:it\s+was\s+)?(?:founded|headquartered|established)\b | (?:based|listed|set\s+up)\s+in\b
  | (?!(?:this|that|these|those|your?|my|it|he|she|they|we|i)\b)[\w\x27 -]{2,40}?\s(?:is|are)\s+(?:an?|the)\s+[\w\x27 -]{2,40}?\s(?:that|where|which|when|used)\b   # a definition
  | [\w\x27 -]{2,40}?\s(?:is\s+when|means\s+that|refers\s+to|is\s+defined|stands\s+for)\b
)""")
SEARCHED = ("trading", "trader", "stock", "chart", "candle", "stop loss", "invest", "support", "resistance", "breakout", "risk", "market")   # (the plain words people type into search: a caption names its topic with one)


def check(spec, facts, charts, category=None):
    """What is wrong with the script, in words Claude can fix."""
    errs = []
    sc = spec.get("scenes") or []
    free = bool(spec.get("scene_js"))                     # a director reel (every reel since 2026-11-09)
    nk = lambda w: re.sub(r"[^a-z0-9%$.]", "", str(w).lower())
    dev = spec.get("device") if isinstance(spec.get("device"), dict) else {}
    if not free or not dev.get("metaphor"):
        errs.append('a director reel (the owner, 2026-11-09): send "device" {metaphor, opening, palette, hud} in the JSON and ONE ```js block after '
                    'it holding the scene function ({t, T, s, i, R, api}) => html (see DIRECTOR REELS)')
    js = spec.get("scene_js") or ""
    body = re.sub(r"^\s*(//[^\n]*\n\s*)*", "", js)          # (a comment may open the block, as the seeds do)
    if js and not (body.startswith("(") and "=>" in js): errs.append("the scene function is one arrow function expression: ({t, T, s, i, R, api}) => { ... }")
    if re.search(r"Math\.random|new Date|\bdocument\.|\bwindow\.", js): errs.append("the scene function is pure: no Math.random, Date, document or window")
    for k, s_ in enumerate(sc):
        if s_.get("kind") == "free":
            tx = str(s_.get("text") or "").split()
            if not 2 <= len(tx) <= 5: errs.append(f"scene {k}: the punch text is 2 to 5 words of the line")
            if s_.get("hot") and nk(s_["hot"]) not in [nk(w) for w in tx]: errs.append(f"scene {k}: hot {s_['hot']!r} must be one of the words of its text")
            if s_.get("head"): errs.append(f"scene {k}: a free scene has no head (the HUD takes the title's place)")
    for d in facts.get("recent_devices") or []:
        for key in ("metaphor", "opening"):
            a, b = str(dev.get(key, "")).lower(), str(d.get(key, "")).lower()
            if a and b and difflib.SequenceMatcher(None, a, b).ratio() > .8: errs.append(f"the device's {key} ({a!r}) is too close to a recent reel's ({b!r}); invent another")
    if not sc or sc[0].get("kind") not in ("hook", "free"): errs.append("the first scene must be a hook (or a free scene that opens on the device)")
    strict = free and category != "Daily recap"              # (the Daily recap is exempt: its chart may open it and its sign-off is fixed)
    if strict and sc:                                        # the first 3 seconds (docs/ROADMAP.md A2)
        s0 = sc[0]; first = re.split(r"(?<=[.?!])\s+", str(s0.get("vo", "")).strip())[0]
        if s0.get("kind") != "free" or not s0.get("text"): errs.append("scene 0 is a free scene with its punch in the text field (2 to 5 short words): the template shows it whole and large on the very first frame")
        if s0.get("chart") is not None: errs.append("scene 0 opens on your device, a character or an odd object already moving, never on a chart: the chart arrives in scene 1 or later")
        if BAD_OPENER.search(first): errs.append(f"the first spoken sentence ({first!r}) is a label, a format promise or a definition: open on the stake or on a question to the viewer")
        errs += [f"the first spoken sentence ({first!r}): {m}" for m in hookscore.run(first)[3]]   # (src/ig/hookscore.py, its dealbreakers only: a greeting, a video preamble, "stop scrolling"; not the score gate retired on 2026-11-07)
        if len(str(s0.get("vo", "")).split()) > 16: errs.append("scene 0 is the hook alone, 16 spoken words at most: by second 5 the reel is in scene 1, the second hook")   # (docs/ROADMAP.md A3)
        nxt = re.split(r"(?<=[.?!])\s+", str(sc[1].get("vo", "")).strip())[0] if len(sc) > 1 else ""
        if BACKGROUND.search(nxt): errs.append(f"scene 1 opens on background ({nxt!r}): it is a second hook that raises the stake; what the company is or what a term means rides inside the action later")
    lo_w, hi_w, outro = LENGTH.get(category or spec.get("type"), (60, 110, True))
    if free and (category or spec.get("type")) not in LENGTH: hi_w = 260 if (category or spec.get("type")) in DEEP else 150   # (in depth: up to 260 words, the owner 2026-11-12)   # (35 to 60 s: the owner, 2026-11-11; was 40 to 120)
    if outro and (not sc or sc[-1].get("kind") != "outro"): errs.append("the last scene must be an outro")
    look = lambda s: ("chart", s.get("chart")) if s.get("chart") is not None and s.get("kind") != "stick" else (s.get("kind"), s.get("layout"))
    body = [s for s in sc if s.get("kind") != "outro"]
    cuts = sum(1 for a, b in zip(body, body[1:]) if look(a) != look(b))
    if cuts > (6 if category == "Stock story" else 3) and not free:   # (what fills the screen changes this often: choppy next to the references)
        errs.append(f"the screen changes {cuts} times before the outro; keep one chart on screen and let it evolve (at most "
                    f"{6 if category == 'Stock story' else 3} switches)")
    worlds = [s for s in sc if s.get("layout")]; events = []
    for k, s in enumerate(sc):
        busy = [c for c in s.get("cues") or [] if c.get("do") in ("mark", "line", "shade") and c.get("from") != "template"]
        if len(busy) > 3: errs.append(f"scene {k}: at most 3 marks, lines or shades on a chart at once (the owner, 2026-11-08: too much on the screen); keep the ones the line says")
        if s.get("kind") == "story" or s.get("layout"):
            P = s.get("props") or []
            if s.get("layout") not in WORLD_LAYOUTS: errs.append(f"scene {k}: layout must be one of {', '.join(WORLD_LAYOUTS)}")
            cap = LAYOUT_PROPS.get(s.get("layout"), 8) - (s.get("layout") == "hero" and (P[:1] or [{}])[0].get("p") in FLIERS)
            A = s.get("actors") or []; Bt = s.get("beats") or []
            if sum(1 for q in P + A if q.get("label")) > (3 if s.get("layout") in ("earns", "storm") else 2): errs.append(f"scene {k}: at most 2 labels in a scene, 3 in earns and storm (the owner: fewer tags, clearer pictures)")
            if not (0 if A else 1) <= len(P) <= cap: errs.append(f"scene {k}: a {s.get('layout')} scene draws 1 to {cap} props; this one has {len(P)}")
            errs += board_check(k, s, A, Bt)
            ev = LAYOUT_EVENT.get(s.get("layout")) or next((b.get("do") for b in Bt if b.get("do") in EVENT_VERBS), None)
            if not ev: errs.append(f"scene {k}: nothing happens; add one beat (hit, fall, launch, emit, grow or burst) that acts out the line")
            if s.get("kind") == "story" and not LAYOUT_EVENT.get(s.get("layout")) and sum(b.get("do") in EVENT_VERBS for b in Bt) < 2:
                errs.append(f"scene {k}: a story scene is alive, never stiff (the owner, 2026-11-08): give it at least 2 event beats on its words")
            if ev and events and events[-1] == ev: errs.append(f"scene {k}: the scene before also opens with a {ev}; make something different happen")
            events.append(ev)
            for q in P:
                if q.get("p") not in WORLD_PROPS: errs.append(f"scene {k}: no prop called {q.get('p')!r}; use one of {', '.join(WORLD_PROPS)}")
                if q.get("color", "teal") not in WORLD_COLOURS: errs.append(f"scene {k}: colour {q.get('color')!r} is not one of {', '.join(WORLD_COLOURS)}")
                if len(str(q.get("label") or "").split()) > 3: errs.append(f"scene {k}: label {q.get('label')!r} is over 3 words")
                if q.get("label") and q["label"].strip().lower().rstrip("s") == str(q.get("p", "")).lower(): errs.append(f"scene {k}: a {q.get('p')} needs no label saying so; label only what the picture cannot say")
                if q.get("say") and q["say"].lower() not in s.get("vo", "").lower(): errs.append(f"scene {k}: prop says {q['say']!r}, which is not in its line")
    if category == "Stock story" and not free:
        if not 5 <= len(worlds) <= 7:
            errs.append(f"a stock story tells the company in 5 to 7 story scenes (kind \"story\" with a layout and props): the hook, "
                        f"what it is, how it earns, why it matters, what's unique, what can hurt it; this script has {len(worlds)}")
        if any(s.get("chart") is not None for s in sc):
            errs.append("a stock story is just the company: no chart scenes (a chart read is the Chart breakdown format)")
        if len(set(events) - {None}) < 3:
            errs.append("a stock story's scenes need at least 3 different kinds of event across the reel (hit, fall, launch, emit, grow, burst)")
        if sc and not sc[0].get("layout"):
            errs.append("a stock story's hook is illustrated: give scene 0 a story layout and props that show the odd fact (its text is the title)")
        for lay, what in (("earns", "how it makes money (layout earns: its 3 jobs)"), ("storm", "what can hurt it (layout storm: 2 or 3 risks)")):
            if not any(s.get("layout") == lay for s in sc): errs.append(f"a stock story has a story scene on {what}, not cards")
    if (category or spec.get("type")) not in UNACTED_HOOK and sc and not sc[0].get("layout") and not free:
        errs.append("the hook is acted out like a stock story's (the owner, 2026-11-08): give scene 0 a shot from the library (or a story layout) "
                    "acting out its words; the chart comes in from scene 1")
    if category == "Chart breakdown" and not free and any(s.get("kind") == "story" or (s.get("kind") not in ("outro",) and s.get("chart") is None) for s in sc[1:]):
        errs.append("a chart breakdown keeps its one chart on screen in every scene after the hook but the outro (no more story scenes)")
    video = facts.get("video", {}).get("available") if isinstance(facts.get("video"), dict) else False
    films = [s for s in sc if s.get("kind") == "film"]
    for k, s in enumerate(sc):
        if s.get("shot") is not None and not 12 <= len(str(s["shot"]).split()) <= 60:
            errs.append(f"scene {k}'s shot must be 12 to 60 words: subject, action, setting, light, camera move")
        if s.get("kind") == "film" and not s.get("shot"): errs.append(f"scene {k} is a film scene with no shot")
    if not video and (films or any(s.get("shot") for s in sc)):
        errs.append("no video this time: use cards, big text or Rookie and Pro instead of film scenes and shots")

    words = sum(len(s.get("vo", "").split()) for s in sc)
    if not lo_w <= words <= hi_w: errs.append(f"the narration is {words} words; it must be {lo_w} to {hi_w}")
    for k, s in enumerate(sc):
        if len(s.get("vo", "").split()) > 26: errs.append(f"scene {k}'s line is too long ({len(s['vo'].split())} words, max 26)")
        ch = s.get("chart")
        if ch is not None and not (isinstance(ch, int) and 0 <= ch < len(charts)): errs.append(f"scene {k} uses chart {ch}, which does not exist")
        for c in s.get("cues", []):
            if c.get("say") and c["say"].lower() not in s.get("vo", "").lower(): errs.append(f"scene {k}: cue phrase {c['say']!r} is not in its line")
            for f in ("to", "i", "from"):
                if f in c and isinstance(ch, int) and 0 <= ch < len(charts) and not 0 <= c[f] < len(charts[ch]["candles"]):
                    errs.append(f"scene {k}: candle {c[f]} is outside chart {ch}")
    errs += shown_check(sc, charts) + speech_check(sc)
    # (no hook-score gate since 2026-11-07: on 48 finance Shorts it did not separate winners (41) from losers (43); the owner retired it)
    for k, s in enumerate(sc):                             # a quiz option's short label, one per option, at most 4 words (every reel since 2026-11-08: long options were cramped)
        dq = (charts[s["chart"]].get("drill") or {}) if s.get("kind") == "question" and isinstance(s.get("chart"), int) and 0 <= s["chart"] < len(charts) else {}
        if s.get("labels") is None and any(len(str(o).split()) > 4 for o in dq.get("options") or []):
            errs.append(f"scene {k}: its options are long; give \"labels\": one short label (max 4 words) per option, in order: {dq['options']}")
        if s.get("labels") is not None:
            d = (charts[s["chart"]].get("drill") or {}) if isinstance(s.get("chart"), int) and 0 <= s["chart"] < len(charts) else {}
            if s.get("kind") != "question" or not isinstance(s["labels"], list) or len(s["labels"]) != len(d.get("options") or []):
                errs.append(f"scene {k}: labels are for a question scene: one per option of its chart ({len(d.get('options') or [])}), in the same order")
            elif any(len(str(x).split()) > 4 for x in s["labels"]):
                errs.append(f"scene {k}: every label is at most 4 words")
    if sc and sc[0].get("kind") == "hook" and sc[0].get("chart") is None and not sc[0].get("layout") and sc[0].get("text") and not free:
        k = lambda x: [re.sub(r"[^a-z0-9']", "", w.lower()) for w in x.split()]
        tx, vx = k(sc[0]["text"]), k(sc[0].get("vo", ""))
        if tx != vx[:len(tx)]: errs.append("the hook's on-screen text must be the first words of the spoken hook, word for word, so it appears as it is said from the first frame")
    spoken = " ".join(x.get("vo", "") for x in sc)
    if re.search(r"\ba (hair|tad)\b", spoken, re.I): errs.append("say 'slightly below' or 'just above', never 'a hair' or 'a tad' (the owner, round 7)")
    doubt = re.findall(r"\b(?:only|just) a clue\b|\bnever a (?:promise|verdict|guarantee)\b|\bnot a (?:promise|verdict|guarantee)\b|\bnot every time\b|"
                       r"\bdoesn't always\b|\bwon't always\b|\bnever certain\b|\bnothing is certain\b|\ba clue\b", spoken, re.I)
    if len(doubt) > 1: errs.append(f"the reel doubts its own signal {len(doubt)} times ({', '.join(doubt)}); say it once, briefly, near the end, "
                                   "and spend the reel showing the signal work (the owner, round 7)")
    if sc and sc[0].get("act") and sc[0]["act"] in (facts.get("hook_shots_used_lately") or []):
        errs.append(f"the hook's shot {sc[0]['act']!r} opened a recent reel; every reel opens with its own (the owner, round 7): pick one of "
                    + ", ".join(x for x in shots.SHOTS if x not in facts["hook_shots_used_lately"]))
    for k, s in enumerate(sc):                             # (a stop answer shows one arrow, drawn for it: never a line per option)
        d = (charts[s["chart"]].get("drill") or {}) if s.get("kind") == "answer" and isinstance(s.get("chart"), int) and 0 <= s["chart"] < len(charts) else {}
        stops = [x["price"] for x in d.get("lines") or [] if x.get("after") and x.get("tone") == "stop"]
        if len(stops) > 1 and any(c.get("do") == "line" and any(abs(c.get("price", 0) - p) <= abs(p) * .002 for p in stops) for c in s.get("cues") or []):
            errs.append(f"scene {k}: no lines for the stop options; the arrow at the right stop is drawn for you")
    acr =sorted({a for a in re.findall(r"[A-Z][A-Z0-9&]{1,5}", spoken) if a not in LEX and a not in ("I", "OK", "UK", "US")})
    if acr: errs.append("write these out or as people say them (the voice reads capitals as letters): " + ", ".join(acr))
    if re.search(r"[0-9]+[.][0-9]{2}", spoken): errs.append("say prices the way people say them, no decimals in a spoken line ('about two ten')")
    # (numbers are written out for the voice, but the detector counts only digits as concrete: score them as digits)
    NW = r"(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|half|point)"
    hs = detect.run(re.sub(rf"\b{NW}(?:[\s-]+(?:and\s+)?{NW})*\b", "9", spoken, flags=re.I), json.load(open(os.path.join(HERE, "ig", "slop.json"), encoding="utf-8")))
    if hs[2] == "FLAGGED":
        weak = "; ".join(f"{n.lower()} {v[0]:.0f}: {v[1]}" for n, v in sorted(hs[0].items(), key=lambda kv: kv[1][0])[:2])
        errs.append(f"the narration reads machine-written (human score {hs[1]:.0f}; weakest: {weak}): vary sentence length, be concrete, talk to 'you', drop stock phrases")
    if sc and sc[-1].get("kind") == "outro":
        ov = sc[-1].get("vo", "").lower()
        if "memestreet.net" not in ov:
            errs.append("the outro must end: \"Join free at memestreet.net.\"")
        if "daily chart" in ov and category not in ("Daily recap", "Daily Chart explained"):
            errs.append("only a reel about the Daily Chart mentions it: end with \"Join free at memestreet.net.\"")
        if strict and category != "Daily Chart explained" and (len(ov.split()) > 10 or "?" in ov):   # (docs/ROADMAP.md A5: the ending takes 2 seconds, not 6)
            errs.append("the outro is the sign-off, 10 words at most: one short echo of the hook if you like, then Join free at memestreet.net. (no promo sentence; the question to the viewer is asked in the hook or the middle)")
    if category == "Loop":                                   # (docs/ROADMAP.md A4: a loop has no sign-off, so its caption carries the address)
        if any(x.get("kind") == "outro" for x in sc): errs.append("a loop has no outro scene: it ends where it began, so the replay is seamless")
        if "memestreet.net" not in str(spec.get("caption", "")).lower(): errs.append("a loop never says the address: put memestreet.net in its caption")
    elif sc and "memestreet.net" not in sc[-1].get("vo", "").lower():
        errs.append("the last scene's line must end by saying memestreet.net (spoken as 'Meem Street dot net')")
    if facts.get("plan_beat_holding") is False:
        early = " ".join(x.get("vo", "") for x in sc[:2]).lower()
        if not re.search(r"\bhold", early) or not re.search(r"\bsetups?\b", early):
            errs.append("buying at the open and holding beat today's trades: own it in the first or second scene (the owner: 'the stock did "
                        "better than us today, but we trade proper setups'); say 'holding' and 'setups'")
    cap = spec.get("caption", "")
    if DISCLAIMER not in cap: errs.append(f"the caption must contain exactly: {DISCLAIMER}")
    if EMOJI.search(cap + json.dumps(sc)): errs.append("no emoji anywhere")
    if "#MemeStreet" not in cap: errs.append("the caption needs #MemeStreet")
    errs += ["the caption: " + c["detail"] for c in igcap.analyse(cap)["checks"] if c["status"] == "FAIL"]   # (src/ig/caption.py: over 5 hashtags, a tag or a blank as the first line, over 2,200 characters)
    if strict:                                               # (docs/ROADMAP.md A9: the question first, the words people search for)
        c1 = (cap.strip().splitlines() or [""])[0]
        if "?" not in c1 or len(c1) > 125: errs.append("the first line of the caption is the question the reel asks the viewer, whole before the ... more cut: one line with a question mark, under 125 characters")
        if not any(w in re.sub(r"#\w+", "", cap.replace(DISCLAIMER, "")).lower() for w in SEARCHED):
            errs.append("the caption names its topic in the plain words people search for (stop loss, candlestick chart, day trading, stock market): none is in its lines")
    return errs


def speech_check(sc):
    """Sentences like a person's (the human Shorts average 16 words a sentence; ours were 5 to 7): flowing on average,
    and never two fragments in a row."""
    errs, frag = [], []
    sents = [x for s in sc for x in re.split(r"(?<=[.?!])\s+", s.get("vo", "").strip()) if x]
    n = sum(len(x.split()) for x in sents)
    if n >= 40 and n / max(1, len(sents)) < 9:
        errs.append(f"the sentences average {n / len(sents):.0f} words: people speak in flowing sentences of 10 to 20 words, joined with so, and, but, because")
    for a, b in zip(sents, sents[1:]):
        if len(a.split()) < 4 and len(b.split()) < 4: frag.append(f"{a} {b}")
    if frag: errs.append("stacked fragments read like an advert, join them into a sentence: " + " | ".join(frag[:4]))
    return errs


CHART_TALK = re.compile(r"\b(candles?|chart|breakout|volume|wicks?)\b", re.I)


def shown_check(sc, charts):
    """The screen shows what the voice says: chart talk has a chart, on-screen text is spoken word for word, a figure is
    not labelled with the title, and marks, shades and zooms land on candles that are already drawn (renderer rules)."""
    errs, end = [], {}
    kw = lambda x: [re.sub(r"[^a-z0-9']", "", w.lower()) for w in x.split() if re.sub(r"[^a-z0-9']", "", w.lower())]
    for k, s in enumerate(sc):
        ch, kind, vo = s.get("chart"), s.get("kind"), s.get("vo", "")
        if ch is None and kind in ("stick", "cards", "big", "film", "story") and CHART_TALK.search(vo):
            errs.append(f"scene {k} talks about {CHART_TALK.search(vo).group(0)!r} but shows no chart: give it the chart, or say only what it shows")
        for t in ([s.get("head")] if kind != "answer" else []) + ([s.get("text")] if kind == "hook" and (ch is not None or s.get("layout")) else []):
            if t and len(kw(t)) >= 3 and any(kw(vo)[j:j + len(kw(t))] == kw(t) for j in range(len(kw(vo)))):
                errs.append(f"scene {k}'s title {t!r} repeats its line: a title names the idea or the theme, not what is said")
        if s.get("text") and kind in ("big", "outro", "free"):
            t, v = kw(s["text"]), kw(vo)
            if not any(v[j:j + len(t)] == t for j in range(len(v) - len(t) + 1)):
                errs.append(f"scene {k}'s on-screen text {s['text']!r} must be words of its line, word for word, in order")
        for f in s.get("figures") or []:
            if f.get("label") and s.get("head") and f["label"].strip().lower() == s["head"].strip().lower():
                errs.append(f"scene {k}: the figure's label repeats the title {s['head']!r}; label it with its name (Rookie, Pro)")
        if not (isinstance(ch, int) and 0 <= ch < len(charts)):
            continue
        C = charts[ch]; n = len(C["candles"]); drill = C.get("drill")
        if kind == "question" and drill: r = C["upto"]                    # (as the renderer will draw it: see finish())
        elif s.get("show") is not None: r = s["show"]
        elif k and sc[k - 1].get("chart") == ch: r = end[k - 1]
        elif kind in ("hook", "chart") and drill: r = C["upto"]
        else: r = n - 1
        if kind == "answer" and drill: r = max(r, C["end"])
        for c in s.get("cues", []):
            if c.get("do") == "reveal" and isinstance(c.get("to"), int): r = max(r, c["to"])
            far = c.get("i") if c.get("do") == "mark" else c.get("to") if c.get("do") in ("shade", "zoom") else None
            if isinstance(far, int) and far > r:
                errs.append(f"scene {k}: the {c['do']} on candle {far} points at a candle not drawn yet (only up to {r} is on screen): reveal it first or use an earlier candle")
        end[k] = r
    seen = {}
    for k, s in enumerate(sc):
        for c in s.get("cues", []):
            if c.get("do") != "line" or not c.get("label") or not isinstance(c.get("price"), (int, float)): continue
            for (ch, lab), p in seen.items():
                same = abs(p - c["price"]) <= 0.001 * max(abs(p), 1e-9)   # (0.1%: an entry and its stop can sit 0.4% apart)
                if ch == s.get("chart") and (lab == c["label"]) != same:
                    errs.append(f"scene {k}: the line {c['label']!r} at {c['price']} " + (f"is the level already called {lab!r}: one level keeps one name in every scene" if same else f"reuses the name of the line at {p}: one name means one level"))
            seen[(s.get("chart"), c["label"])] = c["price"]
    return errs


def stop_key(t):
    """Which of a stop drill's three stops a label or option means: tight (a hair below the entry), below (the support), wide."""
    return "tight" if re.search(r"hair|tight|entry", t, re.I) else "wide" if re.search(r"\bfar\b|wide|never", t, re.I) else "below"


def finish(spec, charts, category):
    """Add what comes from the facts, not from Claude: the options and answers, the drawn lines, the windows."""
    for sc_ in spec.get("scenes", []):                    # (a percentage tag sits above its candle, never under it: the owner, 2026-11-08)
        for c in sc_.get("cues") or []:
            if c.get("do") == "mark" and "%" in str(c.get("label", "")) and c.get("side") == "low": c["side"] = "high"
    named = [(s.get("chart"), c["price"], c["label"]) for s in spec["scenes"] for c in s.get("cues", [])
             if c.get("do") == "line" and c.get("label") and isinstance(c.get("price"), (int, float))]
    def said(vo, lab):                                    # a template line appears when the line names it ('a stop'), else at the start
        words = {"stop": ["stop"], "take": ["target", "take"], "target": ["target"], "entry": ["entry", "buy"], "buy": ["buy", "entry"]}
        first = re.sub(r"[^a-z]", " ", lab.lower()).split()[:1]
        for w in words.get(first[0], first) if first else []:
            m = re.search(r"\b" + re.escape(w) + r"\w*", vo, re.I)
            if m: return m.group(0)
        return ""
    drawn = lambda k, x: any(ck == k and abs(p - x["price"]) <= 0.001 * abs(p) for ck, p, _ in named)   # (the writer drew this level: no second line)
    def name(k, x):                                       # the writer's name for this level, if it drew it: one level, one name
        return next((lab for ck, p, lab in named if ck == k and abs(p - x["price"]) <= 0.001 * abs(p)), x.get("label", ""))[:22]
    for s in spec["scenes"]:
        ch = charts[s["chart"]] if isinstance(s.get("chart"), int) else None
        if not ch:
            s["chart"] = None; continue
        s.setdefault("win", ch["win"])
        d = ch.get("drill")
        tone = lambda x: x.get("tone", "level")
        if s["kind"] == "question" and d:
            s["options"], s["answer"], s["show"] = d["options"], d["answer"], ch["upto"]
            if isinstance(s.get("labels"), list) and len(s["labels"]) == len(d["options"]):   # (version 2: the short labels are shown,
                s["options_full"], s["options"] = d["options"], s["labels"]                   #  the game's own wording kept for the check)
            s["win"] = [ch["win"][0], ch["end"]]
            s.setdefault("cues", []).append({"say": "", "do": "options", "from": "template"})
            s["cues"] += [{"say": said(s.get("vo", ""), name(s["chart"], x)), "do": "line", "price": x["price"], "label": name(s["chart"], x),
                           "tone": tone(x), "from": "template"} for x in d["lines"] if not drawn(s["chart"], x) and not x.get("after")][:2]
        elif s["kind"] == "answer" and d:
            s["reveal_to"], s["carry"] = ch["end"], True
            q = next((x for x in reversed(spec["scenes"][:spec["scenes"].index(s)]) if x.get("kind") == "question"), {})
            s["head"], s["badge"] = "The answer", q.get("badge", "")      # (one title for every answer: the highlight shows which)
            s.setdefault("cues", [])
            after = [x for x in d["lines"] if not drawn(s["chart"], x) and x.get("after")]
            st_ = [x for x in d["lines"] if x.get("after") and x.get("tone") == "stop"]
            if len(st_) > 1:                              # (one arrow at the right stop, never a line per option: the owner, round 7)
                right = next((x for x in st_ if stop_key(x["label"]) == stop_key(d["options"][d["answer"]])), st_[0])
                s["cues"].append({"say": said(s.get("vo", ""), "stop"), "do": "arrow", "price": right["price"], "i": right.get("from"),
                                  "label": "Stop", "tone": "stop", "from": "template"})
                after = [x for x in after if x.get("tone") != "stop"]
            busy = lambda cs: sum(1 for c in cs if c.get("do") in ("mark", "line", "shade"))
            room = max(0, 3 - busy(s["cues"]) - busy(q.get("cues", [])))   # (at most 3 marks, lines or shades at once, the question's carried ones counted: the owner, 2026-11-08; the critic held a fib quiz for a pile of seven, 2026-11-09)
            ans = set(re.findall(r"[a-z0-9.%]+", str(d["options"][d["answer"]]).lower()))
            after.sort(key=lambda x: -len(ans & set(re.findall(r"[a-z0-9.%]+", str(name(s["chart"], x)).lower()))))   # (the level the answer names first)
            add = [{"say": said(s.get("vo", ""), name(s["chart"], x)), "do": "line", "price": x["price"], "label": name(s["chart"], x),
                    "tone": tone(x), "from": "template"} for x in after][:room]
            s["cues"] += add
            mine = {c.get("i") for q in spec["scenes"] if q.get("chart") == s["chart"] for c in q.get("cues", [])
                    if c.get("do") == "mark" and c.get("from") != "template"}      # (a candle the writer marked keeps only its mark)
            s["cues"] += [{"say": "", "do": "mark", "i": m["i"], "label": m.get("label", "")[:14], "side": "high", "from": "template"}
                          for m in d["marks"] if m.get("label") and m["i"] not in mine][:max(0, room - len(add))]
        elif s["kind"] in ("hook", "chart") and s.get("show") is None and d:
            s["show"] = ch["upto"]
    spec["type"] = category
    spec["charts"] = [dict({"candles": c["candles"], "label": c["label"]}, **{k: c[k] for k in ("overlay", "live_from") if c.get(k)}) for c in charts]
    return capitals(spec)


def sentence_case(x):
    """Every sentence and line starts with a capital, and 'i' is 'I' (nothing is ever lowered: names keep their case)."""
    abbr = lambda m: re.search(r"\b(i\.e|e\.g|vs|etc|approx)\.\s+$", m.string[:m.start(2)], re.I)
    x = re.sub(r"(^|[.!?]\s+|\n\s*)([\"'(]?)([a-z])", lambda m: m.group(0) if abbr(m) else m.group(1) + m.group(2) + m.group(3).upper(), x)
    return re.sub(r"\bi(?=\b(?!\.))(?=['\s,.!?]|$)", "I", x)


def capitals(spec):
    """Proper capitals everywhere a viewer reads: titles, heads, hook and big text, cards, bubbles, labels, options,
    the spoken lines (they become the captions) and the post caption."""
    up = lambda x: sentence_case(x) if isinstance(x, str) else x
    for k in ("title", "caption"):
        spec[k] = up(spec.get(k))
    for s in spec["scenes"]:
        for k in ("vo", "head", "text", "badge"):
            if s.get(k): s[k] = up(s[k])
        for it in s.get("items", []):
            for k in ("text", "sub"):
                if it.get(k): it[k] = up(it[k])
        for c in s.get("cues", []) + s.get("figures", []) + s.get("props", []):
            for k in ("text", "label"):
                if c.get(k): c[k] = up(c[k])
        if s.get("options"): s["options"] = [up(o) for o in s["options"]]
    return spec


def system_prompt(category):
    """The writer's standing instructions, always the current rules (a rewrite rebuilds them: a brief saved before a rule
    changed must not hold the writer to the old one)."""
    voice = open(os.path.join(ROOT, "voice.md"), encoding="utf-8").read()      # (a copy of ~/.claude/instagram/voice.md)
    hooks = json.load(open(os.path.join(HERE, "ig", "hooks.json"), encoding="utf-8"))["hooks"]
    rb = os.path.join(ROOT, "RULEBOOK.md")              # (the owner's rulebook: highest priority, read before every reel)
    book = ("THE OWNER'S RULEBOOK. These rules override everything below; follow every one:\n" +
            open(rb, encoding="utf-8").read() + "\n\n") if os.path.exists(rb) else ""
    s = book + ("You write Instagram Reels for Meme Street, a free stock market game with fictional companies "
            "(memestreet.net). Voice profile:\n" + voice + "\n\nHook formulas you may use:\n" +
            "\n".join(f"- {h['name']}: {h['template']}" for h in hooks) + "\n\n" + RULES + "\n" + SCHEMA % (category, ", ".join(WORLD_PROPS))
         + "\n" + DIRECTOR % (", ".join(WORLD_PROPS), ", ".join(POSES), examples()) + FIRST3)
    r = rules_file(category)
    return v2_system(s, r) if r else s


def verdicts():
    """format -> "cut" | "boost" | "keep" | "new" from Instagram's numbers (src/format_scores.py); {} before its first run."""
    try: return {f: x["verdict"] for f, x in json.load(open(os.path.join(ROOT, "state", "format_scores.json"), encoding="utf-8"))["formats"].items()}
    except (OSError, ValueError, KeyError, TypeError): return {}


def choose(home, every, used, last, v, rng, nth=0):
    """The format for a slot. `home`: the slot's turn; `every`: all rotation formats; `used`: out already that day; `last`: the
    formats of the last reels, oldest first; `v`: verdicts(); `nth`: 0, or 1 and 2 for a held slot's second and third try (the next proven ones).
    Never a cut format, never one already out that day; a boosted format joins every turn of two or more and goes first;
    then the one out longest ago."""
    ok = lambda cs: [c for c in dict.fromkeys(cs) if c not in used and v.get(c) != "cut"]
    pool = ok(list(home) + ([c for c in every if v.get(c) == "boost"] if len(set(home)) > 1 else [])) or \
           [c for c in ok(every) if c != "Loop"] or list(dict.fromkeys(home))
    pool.sort(key=lambda c: (v.get(c) != "boost", max((k for k, x in enumerate(last) if x == c), default=-1), rng.random()))
    if nth: pool = [c for c in pool[nth:] if c in last] or pool[nth:] or pool   # (a second or third try: the next format that has passed the critic before, so the slot is not left empty)
    return pool[0]


def recent_formats(n=40):
    """The formats of the last `n` reels that passed the critic (posted or waiting to post), oldest first."""
    q, out = os.path.join(ROOT, "queue"), []
    for x in sorted(os.listdir(q))[-80:] if os.path.isdir(q) else []:
        sp = os.path.join(ROOT, "work", "auto-" + x, "spec.json")
        if os.path.exists(os.path.join(q, x, "approved.json")) and os.path.exists(sp):
            try: out.append(json.load(open(sp, encoding="utf-8")).get("type"))
            except ValueError: pass
    return out[-n:]


def formats_on(day, but=None):
    """The formats of the reels already made for UTC day `day` (YYYY-MM-DD) that passed the critic, slot `but` aside."""
    q, out = os.path.join(ROOT, "queue"), set()
    for x in os.listdir(q) if os.path.isdir(q) else []:
        sp = os.path.join(ROOT, "work", "auto-" + x, "spec.json")
        if x.startswith(day) and x != but and os.path.exists(os.path.join(q, x, "approved.json")) and os.path.exists(sp):
            try: out.add(json.load(open(sp, encoding="utf-8")).get("type"))
            except ValueError: pass
    return out


def brief(slot, category=None, remake=None):
    """Everything the writer needs for one reel: the system prompt, the request (facts included) and the charts."""
    rng = random.Random(slot + os.environ.get("REEL_TRY", ""))   # (a held slot's second try gets another format)
    history = json.load(open(HISTORY)) if os.path.exists(HISTORY) else {}
    if not category and explainer(slot): category, remake = explainer(slot), None   # (an explainer day: it takes the slot's remake too)
    if not category:                                     # (the format of this slot's turn that went out longest ago, so every
        last = recent_formats()                          #  format keeps coming round: the owner, 2026-11-12, "only quiz reels")
        used = formats_on(slot[:10], slot)               # (one reel of each format a day: the owner, 2026-11-12)
        every = [c for cs in ROTATION.values() for c in cs]   # (one cycle through every format, whatever the hour: the owner, 2026-11-12 evening,
        category = choose(every, every, used, last, verdicts(),   #  five reels a day; ROTATION now only lists the formats)
                          rng, int(os.environ.get("REEL_TRY") or 0))   # (Instagram's numbers steer it: the owner, 2026-11-12)
    if remake and {"Chart quiz": "Chart quiz", "Stock story": "Stock story", "Technicals": "Technical lesson",
                   "New-trader challenge": "Trading mistake"}.get(remake.get("type"), "Technical lesson") != category or category in DEEP:
        remake = None                                    # (an old November topic no longer chooses the format; it is kept only when it fits)
    try:
        facts, charts = gather(category, rng, history, remake.get("title") if remake and category == "Stock story" else None)
    except SystemExit:
        if not (remake and category == "Stock story"): raise
        category = "Explained like you're 5"               # (gold, oil, an ETF: not a game company, so an explainer on the topic)
        facts, charts = gather(category, rng, history)
    facts["hook_shots_used_lately"] = [x for x in history.get("acts", []) if x][-5:]   # (every reel opens with its own shot: the owner, round 7)
    system = system_prompt(category)
    import footage                                       # (video only with a Higgsfield key and money left under the monthly cap)
    need = 3 * footage.cost(10) if category == "Stock story" else footage.cost(5)
    facts["video"] = {"available": os.environ.get("HF_VIDEO") == "1" and bool(footage.cred()) and footage.remaining() >= need}   # (off: the neon 3D is the style)
    facts["subjects_of_recent_reels"] = {"note": "What the last reels were about, oldest first. This reel is about its own facts: do not "
                                                 "drift back to these. Support, resistance or 'a level' is the subject only when this "
                                                 "reel's own chart facts are about a level (the owner, 2026-11-12: too many reels "
                                                 "talked about them).", "last": history.get("subjects", [])[-12:]}
    history.setdefault("subjects", []).extend(facts.pop("_subjects", [])); del history["subjects"][:-100]
    facts["recent_devices"] = [d for d in history.get("devices", []) if isinstance(d, dict)][-30:]   # (every reel invents its own device: the owner, 2026-11-09)
    notes = os.path.join(ROOT, "exemplar", "NOTES.md")
    ask = {"category": category, "what_this_reel_is": CATEGORIES[category], "facts": facts,
           "recent_titles_to_avoid": history.get("titles", [])[-20:],
           "exemplar_notes": open(notes, encoding="utf-8").read() if os.path.exists(notes) else ""}
    if CATEGORIES[category].startswith(("VIRAL", "NEW")):
        ask["what_works_now"] = {"note": "Openings of short trading videos that beat their own account's usual views "
                                         "(research 2026-11-04). Use the SHAPE, never the words: write an original line "
                                         "about this reel's own chart.",
                                 "examples": STICK_EVIDENCE if "STICK" in CATEGORIES[category] else
                                 SHORT_EVIDENCE if category in LENGTH else VIRAL_EVIDENCE}
        ev = os.path.join(ROOT, "state", "evidence.json")      # this week's outliers (src/research.py), shapes only
        if os.path.exists(ev):
            ask["what_works_now"]["this_week"] = json.load(open(ev, encoding="utf-8")).get("examples", [])[:8]
    try: ask["our_own_reels"] = json.load(open(os.path.join(ROOT, "state", "own_reels.json"), encoding="utf-8"))   # (our own best and worst openings, measured: src/own_reels.py, docs/ROADMAP.md A10)
    except (OSError, ValueError): pass                   # (not pulled yet, or unreadable: the reel is written without it)
    if remake:
        ask["remake_of"] = {"note": "Make this reel again on the same topic, with the same teaching points and similar "
                                    "explanations, but tighter: no long pauses, every line earns its place. Use the new "
                                    "charts in the facts instead of the old ones. If the topic is something the chart cannot "
                                    "draw (MACD, Bollinger Bands, VWAP, ATR, moving averages on a chart with no overlay, position sizing, an ETF, a "
                                    "commodity), explain it with cards, big text and Rookie and Pro, and use the chart only "
                                    "for what it really shows; never claim the chart shows the indicator.",
                            "title": remake.get("title"), "old_narration": remake.get("narration"), "old_caption": remake.get("caption")}
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    json.dump(history, open(HISTORY, "w"))                  # (the stock just used, so the next story picks another)
    return {"slot": slot, "category": category, "system": system, "ask": ask, "charts": charts}


def parse(raw, B, base=None):
    """The script in Claude's reply (a patch of `base` when one is given), and what is wrong with it."""
    js = next((m for m in re.finditer(r"```[\w-]*[ \t]*\n(.*?)```", raw, re.S) if "=>" in m.group(1) and not m.group(1).lstrip().startswith("{")), None)   # the scene function, in whatever fence (its braces would break the JSON match; a ```json fence holds the script)
    if js: raw = raw[:js.start()] + raw[js.end():]
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        spec = json.loads(m.group(0)) if m else {}
    except ValueError as e:
        try:                                              # (a remark after the JSON, or a second object: the first complete object is the script)
            spec = json.JSONDecoder().raw_decode(raw, raw.index("{"))[0]
        except ValueError:
            return {}, [f"not valid JSON: {e}"]
    if base is not None:
        spec = merge(base, spec)
        for k in ("scene_js", "device", "tok"):
            if k not in spec and base.get(k) is not None: spec[k] = base[k]
    if js: spec["scene_js"] = js.group(1).strip()
    pre = shots.expand_all(spec, WORLD_PROPS)            # (a shot becomes its polished storyboard; a free one is refused)
    return spec, pre + check(spec, B["ask"]["facts"], B["charts"], B["category"])


def merge(base, patch):
    """A rewrite after the critic sends only what changes: {"scenes": {"3": scene, ...}, "title": ...}. The scenes not
    named stay exactly as they were (a whole script, with a list of scenes, replaces the draft)."""
    if isinstance(patch.get("scenes"), list):
        return {k: v for k, v in patch.items() if k != "fixes"}
    s = json.loads(json.dumps(base))
    for k, v in (patch.get("scenes") or {}).items():
        i = int(k)
        if 0 <= i < len(s["scenes"]): s["scenes"][i] = v
        elif i == len(s["scenes"]): s["scenes"].append(v)
    s.update({k: v for k, v in patch.items() if k not in ("scenes", "fixes")})
    return s


def claude_cli(messages, system, model=None, wait=True):
    """The writer through Claude Code on this server, logged in to the owner's plan (CLAUDE_CODE_OAUTH_TOKEN from
    `claude setup-token`): the plan's usage, no API bill. No tools: it only writes."""
    convo = "\n\n".join(("REQUEST:\n" if m["role"] == "user" else "YOUR EARLIER REPLY:\n") + m["content"] for m in messages)
    r = subprocess.run(["claude", "-p", "--output-format", "text", "--model", model or os.environ.get("REEL_CLI_MODEL", "opus"),
                        "--append-system-prompt", system,
                        "--disallowedTools", "Bash,Edit,Write,Read,WebFetch,WebSearch,Glob,Grep,Task,NotebookEdit"],
                       input=convo, capture_output=True, text=True, timeout=900, cwd="/tmp",
                       env={k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"})   # (an API key would be billed instead)
    if wait and r.returncode and re.search(r"hit your|usage limit|rate limit", (r.stderr or "") + r.stdout, re.I):   # (wait=False: src/learn.py skips the day instead)
        print("the writer's plan limit is reached: waiting 15 minutes, then trying again", flush=True)   # (credits come back: carry on then)
        time.sleep(900); return claude_cli(messages, system, model)
    if r.returncode:
        raise SystemExit("claude -p failed: " + (r.stderr or r.stdout)[-400:])
    return r.stdout


def lessons():
    """What the film critic (critic.py) sent earlier reels back for, most often first: the writer reads these before
    every reel, so the next one passes first time."""
    f = os.path.join(ROOT, "state", "lessons.json")
    L = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else []
    L = sorted((x for x in L if x.get("owner") != "renderer"),     # (the renderer's notes are fixed in reel.html, not by the writer)
               key=lambda x: (x.get("count", 1), x.get("last", "")), reverse=True)[:30]
    return ("\n\nThe film critic who reviews every finished reel sent earlier reels back for these. Never repeat them:\n" +
            "\n".join(f"- {x['lesson']}" for x in L)) if L else ""


def learned(path=None):
    """What Instagram's numbers taught us about our own reels (state/learned.md, written once a day by src/learn.py from
    the best and worst reels against the medians): the writer reads it before every reel. "" before its first run."""
    f = path or os.path.join(ROOT, "state", "learned.md")
    try: body = open(f, encoding="utf-8").read().strip()
    except OSError: return ""
    return ("\n\nWHAT INSTAGRAM'S NUMBERS TAUGHT US ABOUT OUR OWN REELS (measured on our account, with the evidence in brackets). "
            "Follow them unless the owner's rulebook says otherwise; a rule that says 'try' is a lead, not a law:\n" + body) if body else ""


def fix_check(raw, notes, base, spec):
    """A rewrite answers every note: each has an entry in "fixes", a note about scene k changes scene k (or its fix
    names the changed scene that carries it), and something changed at all (an unchanged cut is not reviewed again)."""
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        patch = json.loads(m.group(0)) if m else {}
    except ValueError:
        return []                                         # (parse() already said it is not JSON)
    errs, keep = [], lambda s: {k: v for k, v in s.items() if k != "fixes"}
    if keep(spec) == keep(base):
        errs.append("nothing changed: the critic would see the same cut; change what the notes ask")
    sc = patch.get("scenes")
    changed = set(range(len(spec.get("scenes", [])))) if isinstance(sc, list) else {int(k) for k in (sc or {}) if str(k).isdigit()}
    fixes = {f.get("n"): str(f.get("how", "")) for f in patch.get("fixes", []) if isinstance(f, dict)}
    for n, x in enumerate(notes, 1):
        if n not in fixes:
            errs.append(f"note {n} has no entry in \"fixes\" (say how you fixed it)"); continue
        want = {int(k) for k in re.findall(r"scene (\d+)", x.get("where", ""))}
        named = {int(k) for k in re.findall(r"scene (\d+)", fixes[n])}
        if want and not (want | named) & changed:
            errs.append(f"note {n} is about scene {min(want)}, but you did not change it (or name the scene you changed for it)")
        if "caption" in x.get("where", "").lower() and "caption" not in patch and not isinstance(sc, list):
            errs.append(f"note {n} is about the post caption, but you did not send a new \"caption\"")
    return errs


def dry_run(spec, B, work):
    """The scene function through the whole reel before any voice is made (render.py DRY: a JavaScript error, text on text,
    small text, three still seconds, slow frames): its faults, in words the writer can fix."""
    if not spec.get("scene_js"): return []
    d = os.path.join(work or os.path.join(ROOT, "work", "dry"), "dry"); shutil.rmtree(d, ignore_errors=True); os.makedirs(d, exist_ok=True)
    json.dump(finish(json.loads(json.dumps(spec)), B["charts"], B["category"]), open(os.path.join(d, "spec.json"), "w"))
    env = dict(os.environ, DRY="1", PAGE="reel.html")
    for cmd in ([sys.executable, os.path.join(ROOT, "lab", "silent.py"), d], [sys.executable, os.path.join(HERE, "render.py"), d, "-"]):
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=ROOT, timeout=1200)
        if r.returncode:
            o = (r.stderr or "") + (r.stdout or ""); m = re.search(r"DRY: (.*)", o, re.S)
            return ["the scene function failed the dry run: " + (m.group(1) if m else o[-600:]).strip()]
    lo, hi = SECONDS.get(B["category"], (0, 60)); T = json.load(open(os.path.join(d, "timeline.json"), encoding="utf-8")).get("T", 0)   # (docs/ROADMAP.md A3: the length in seconds as well as in words)
    return [] if lo <= T <= hi else [f"at the voice's pace this reel runs {T:.0f} seconds; a {B['category']} runs {lo:g} to {hi:g}: " + ("cut lines" if T > hi else "add a beat")]


def write(B, msgs=None, base=None, notes=None, work=None):
    """Have Claude write the script (or, with `base`, a patch of it that answers `notes`), checked and sent back at
    most four times. The first draft is the big model's (REEL_CLI_MODEL), the fixes the small one's (REEL_FIX_MODEL)."""
    ask = claude_cli if os.environ.get("REEL_WRITER", "cli") == "cli" else claude
    msgs = msgs or [{"role": "user", "content": json.dumps(B["ask"], indent=1)}]
    B = dict(B, system=B["system"] + lessons() + learned())   # (the critic's lessons, then Instagram's: src/learn.py)
    for attempt in range(5):
        raw = ask(msgs, B["system"], model=os.environ.get("REEL_CLI_MODEL", "opus") if attempt == 0 else os.environ.get("REEL_FIX_MODEL", "sonnet"))   # (the big model writes and makes the critic's fix; the small one repairs check failures: a small-model rewrite duplicated scenes, 2026-11-09)
        spec, errs = parse(raw, B, base)
        if base is not None and spec:
            errs += fix_check(raw, notes or [], base, spec)
        if not errs:
            errs = dry_run(spec, B, work)
        if not errs:
            return spec
        print(f"attempt {attempt + 1}: " + "; ".join(errs[:8]), flush=True)
        if work:                                          # (the reply as it came, for debugging a check that keeps failing)
            os.makedirs(work, exist_ok=True); open(os.path.join(work, f"attempt-{attempt + 1}.txt"), "w", encoding="utf-8").write(raw)
        msgs += [{"role": "assistant", "content": raw}, {"role": "user", "content": ("Fix these and reply with only the scenes you change, in the same form: " if base else "Fix these and reply with the whole JSON again: ") + "; ".join(errs)}]
    raise SystemExit("the script did not pass its checks: " + "; ".join(errs))


def revise(work, review):
    """The critic sent the finished reel back: the writer gets its own script and his checked script notes, and rewrites
    only the scenes they name (a patch; the rest is approved and stays as it is, so it is not voiced or reviewed again)."""
    if os.path.exists(os.path.join(work, "STOP")):        # (an operator's stop: the cut stands as it is, the critic's next round holds it)
        print("STOP file in the work dir: no rewrite, the cut stands", flush=True); return
    B = json.load(open(os.path.join(work, "brief.json"), encoding="utf-8"))
    B["system"] = system_prompt(B["category"])          # (today's rules, not the ones saved with the brief)
    draft = open(os.path.join(work, "draft.json"), encoding="utf-8").read()
    sn = lambda x: int((re.findall(r"scene (\d+)", x.get("where", "")) or [999])[0])
    todo = sorted((x for x in review.get("issues", []) if x.get("owner", "script") != "renderer" and x.get("severity", "blocker") == "blocker"), key=sn)   # (blockers only: the notes are for the owner's log, not a rewrite; the owner, 2026-11-07)
    ev = lambda x: "".join(f" [measured: {e['report']}]" for e in x.get("evidence") or [] if isinstance(e, dict) and e.get("report"))
    notes = "\n".join(f"{n}. [{x.get('severity', '')}] {x.get('where', '')}: {x.get('what', '')}{ev(x)} FIX: {x.get('fix', '')}"
                      + (f" (OPEN {x['rounds_open']} ROUNDS: your earlier fixes did not change this on screen; read the scene as rendered below)"
                         if x.get("rounds_open", 0) >= 2 else "") for n, x in enumerate(todo, 1))
    msgs = [{"role": "user", "content": json.dumps(B["ask"], indent=1)}, {"role": "assistant", "content": draft},
            {"role": "user", "content": "A film critic watched the finished reel made from your script and sent it back.\n"
                                        f"His verdict: {review.get('verdict', '')}\nHis scores (8+ on each is needed): {review.get('scores')}\n"
                                        f"His notes (scenes count from 0):\n{notes}\n\n"
                                        f"The noted scenes as they were rendered (times in seconds):\n{rendered(work, todo)}\n\n"
                                        + (f"Scenes {', '.join(map(str, review['stuck_scenes']))} have drawn a major fault two rounds running: "
                                           "tweaking will not fix them. Give each a different approach (another scene kind, another "
                                           "moment of the chart, another prop) or drop it (a quiz may drop that question), within the "
                                           "length rules.\n" if review.get("stuck_scenes") else "") +
                                        "Fix every note. Everything he did not mention is approved: leave it exactly as it is. The scene "
                                        "function is yours: when a note concerns the picture, send a new complete ```js block after the JSON "
                                        "(it replaces the old one); keep the device. "
                                        "Lines and marks marked \"template\" are added from the game's facts: to rename one, add your "
                                        "own line cue at the same price with the name you want; its \"say\" sets when it appears. "
                                        "Where a tag sits, its size and its font belong to the template, not to you.\n"
                                        'Reply with JSON holding only what you change: {"scenes": {"<scene number>": <the whole '
                                        'new scene>, ...}, "fixes": [{"n": <note number>, "how": "scene k: what you changed"}, '
                                        '...one per note]}, plus "title" or "caption" only if a note is about them. To add, '
                                        "remove or reorder scenes, reply with the whole JSON (with \"fixes\") instead."}]
    save(write(B, msgs, json.loads(draft), todo, work), B, work, again=True)


def rendered(work, notes):
    """What the noted scenes really put on screen in the cut he watched (timeline.json): the line, the titles, and
    every cue with its time and whether the writer or the template added it."""
    try:
        R = json.load(open(os.path.join(work, "timeline.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return "(not available)"
    ks = sorted({int(k) for x in notes for k in re.findall(r"scene (\d+)", x.get("where", ""))} & set(range(len(R["scenes"]))))
    out = []
    for k in ks:
        s = R["scenes"][k]
        cues = [f"{c.get('t')}s {c.get('do')} " + " ".join(f"{q}={c[q]}" for q in ("label", "text", "price", "i", "to") if c.get(q) is not None)
                + f" (from {c.get('from', 'you')})" for c in s.get("cues", [])]
        out.append(f"scene {k} ({s.get('kind')}, {s.get('t0')}s-{s.get('t1')}s): vo {s.get('vo')!r}; head {s.get('head')!r}; "
                   f"text {s.get('text')!r}\n  " + "\n  ".join(cues or ["(no cues)"]))
    return "\n".join(out) or "(no scene named)"


def save(spec, B, work, again=False):
    os.makedirs(work, exist_ok=True)
    json.dump(B, open(os.path.join(work, "brief.json"), "w"))          # (for a rewrite after the critic: revise())
    json.dump(spec, open(os.path.join(work, "draft.json"), "w"))
    spec = finish(spec, B["charts"], B["category"])
    json.dump(spec, open(os.path.join(work, "spec.json"), "w"))
    open(os.path.join(work, "caption.txt"), "w", encoding="utf-8").write(spec["caption"].strip() + "\n")
    history = json.load(open(HISTORY)) if os.path.exists(HISTORY) else {}
    if not again: history.setdefault("titles", []).append(spec["title"]); history.setdefault("acts", []).append((spec["scenes"] or [{}])[0].get("act")); history.setdefault("devices", []).append(spec.get("device"))
    if not again and B["category"] in EXPLAINERS:           # (the next explainer of its kind reads these and takes a new angle)
        history.setdefault("explainers", []).append({"category": B["category"], "title": spec["title"], "device": (spec.get("device") or {}).get("metaphor"),
                                                     "lines": [x.get("vo", "") for x in spec["scenes"]][:3]})
    if spec.get("scene_js"): open(os.path.join(work, "scene.js"), "w", encoding="utf-8").write(spec["scene_js"])   # (for humans: the reel's own picture)
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    json.dump(history, open(HISTORY, "w"))
    print(f"{B['category']}: {spec['title']} ({sum(len(s['vo'].split()) for s in spec['scenes'])} words, {len(spec['scenes'])} scenes)")


if __name__ == "__main__":
    a = sys.argv[1:]
    rem = json.load(open(a[a.index("--remake") + 1], encoding="utf-8")) if "--remake" in a else None
    cat = a[a.index("--category") + 1] if "--category" in a else None
    if a[0] == "selftest":
        new = ("Two traders", "Rewind", "Trade diary", "Candles talk", "Instant replay", "Expectation vs reality", "Breaking news")
        assert all(c in CATEGORIES and sum(c in cs for cs in ROTATION.values()) == 2 and (c in KINDS or c == "Breaking news") for c in new)
        assert "THE FIRST 3 SECONDS" in system_prompt("Rewind") and all(c in CATEGORIES for cs in ROTATION.values() for c in cs)
        import tempfile; lf = os.path.join(tempfile.mkdtemp(), "learned.md")
        assert learned(lf) == ""; open(lf, "w", encoding="utf-8").write("# x\n- Open on the stake (8 reels)\n")
        assert "TAUGHT US" in learned(lf) and "- Open on the stake (8 reels)" in learned(lf)
        assert all(sum(c in cs for cs in ROTATION.values()) == 2 and "LENGTH AND DEPTH" in CATEGORIES[c] for c in DEEP)
        H = {"k": ["a", "b", "a"]}
        assert lru(["a", "b", "c"], H, "k") == ["c"] and lru(["a", "b"], H, "k") == ["b"] and lru(["a", "b", "c"], H, "k", 2) == ["a", "c"] and H["k"][-2:] == ["a", "c"]
        assert all(k in KINDS["Chart twist"] for k in ("rsi", "ma", "fib")) and KINDS["Big players"] == ["breakout", "level"] and all(k in SUBJECT for ks in KINDS.values() for k in ks)
        R0 = random.Random(1); ch = lambda home, used=(), last=(), v={}, nth=0: choose(home, ["A", "B", "C", "D"], set(used), list(last), v, R0, nth)
        assert ch(["A", "B"], last="AB") == "A" and ch(["A", "B"], last="BA") == "B"            # (the one out longest ago)
        assert ch(["A", "B"], used="A") == "B" and ch(["A", "B"], last="AB", v={"A": "cut"}) == "B"   # (once a day; never a cut format)
        assert ch(["A", "B"], last="ABD", v={"D": "boost"}) == "D" and ch(["A"], last="AD", v={"D": "boost"}) == "A"   # (the best goes first, but not into a one-format turn)
        assert ch(["A", "B"], last="AB", nth=1) == "B" and ch(["A"], used="A", v={"B": "cut"}) in ("C", "D")   # (a second try: the next in line; a used-up turn: another format)
        assert ch(["A"], used="ABCD") == "A" and ch(["A", "B", "C"], last="B", nth=1) == "B"   # (a second try takes a format that has passed before)
        assert ch(["A", "B", "C"], last="ABC", nth=2) == "C" and ch(["A", "B"], last="AB", nth=2) in ("A", "B")   # (a third try: the one after that; a short turn starts over)
        assert [explainer(f"2026-11-{d:02d}T1800") for d in (10, 13, 16, 19, 22)] == [None, "Meme Street explained", "Daily Chart explained", "Meme Street explained", "Daily Chart explained"]
        assert explainer("2026-11-13T2100") is None and explainer("2026-11-14T1800") is None
        for x, y in [("level cost you 11%", "Level cost you 11%"), ("it fell. then i sold!", "It fell. Then I sold!"),
                     ("at memestreet.net. now", "At memestreet.net. Now"), ("i'm in, i.e. long", "I'm in, i.e. long"),
                     ("Ember Dragon Ranches up", "Ember Dragon Ranches up")]:
            assert sentence_case(x) == y, (x, sentence_case(x))
        base = {"title": "T", "caption": "c", "scenes": [{"vo": "a"}, {"vo": "b"}, {"vo": "c"}]}
        notes = [{"where": "scene 1, 4s", "what": "x"}, {"where": "post caption", "what": "y"}]
        fc = lambda p: fix_check(json.dumps(p), notes, base, merge(base, p))
        assert any("nothing changed" in e for e in fc({"scenes": {}, "fixes": [{"n": 1}, {"n": 2}]}))
        assert any("note 2 has no entry" in e for e in fc({"scenes": {"1": {"vo": "B"}}, "fixes": [{"n": 1, "how": "scene 1"}]}))
        assert any("did not change it" in e for e in fc({"scenes": {"2": {"vo": "C"}}, "caption": "d", "fixes": [{"n": 1, "how": "x"}, {"n": 2}]}))
        assert fc({"scenes": {"2": {"vo": "C"}}, "caption": "d", "fixes": [{"n": 1, "how": "scene 2 carries it"}, {"n": 2}]}) == []
        assert any("post caption" in e for e in fc({"scenes": {"1": {"vo": "B"}}, "fixes": [{"n": 1}, {"n": 2}]}))
        assert "fixes" not in merge(base, {"scenes": {"1": {"vo": "B"}}, "fixes": []})
        cs = lambda a, b: [[1, 1, 1, a]] * 10 + [[1, 1, 1, b]] * 30          # (close a at the question, b after)
        dr = lambda ans, a, b, **k: dict({"candles": cs(a, b), "upto": 9, "options": [ans], "answer": 0}, **k)
        assert played_out(dr("A golden cross", 100, 105)) and not played_out(dr("A golden cross", 100, 95))
        assert played_out(dr("A death cross", 100, 95)) and played_out(dr("A doji", 100, 100)) and not played_out(dr("Neither", 100, 104), strict=True)
        lv = [{"price": 99}]
        assert played_out(dr("Real: it keeps going", 100, 104, kind="breakout", lines=lv)) and not played_out(dr("Fake: back inside", 100, 104, kind="breakout", lines=lv))
        assert [stop_key(x) for x in ("Tight", "Below support", "Wide", "A hair below the entry", "Far below, so it is never hit", "Just below the support")] == \
               ["tight", "below", "wide", "tight", "wide", "below"]
        raw = 'here {"title": "T", "scenes": []} and\n```js\n// DEVICE: a kettle\n({t, api}) => { return `<svg>${t}</svg>` }\n```\n'
        js = next((m for m in re.finditer(r"```[\w-]*[ \t]*\n(.*?)```", raw, re.S) if "=>" in m.group(1) and not m.group(1).lstrip().startswith("{")), None); assert js and "({t" in js.group(1)
        raw2 = '```json\n{"title": "T", "x": "a => b"}\n```\nnotes\n```javascript\n({t}) => 1\n```'
        js2 = next((m for m in re.finditer(r"```[\w-]*[ \t]*\n(.*?)```", raw2, re.S) if "=>" in m.group(1) and not m.group(1).lstrip().startswith("{")), None); assert js2 and js2.group(1).strip() == "({t}) => 1", js2
        assert not any("arrow function" in e for e in check({"scene_js": js.group(1).strip(), "device": {"metaphor": "k"}, "scenes": [], "caption": ""}, {}, [], "One trick"))
        assert json.loads(re.search(r"\{.*\}", raw[:js.start()] + raw[js.end():], re.S).group(0))["title"] == "T"
        fr = {"title": "T", "caption": f"x {DISCLAIMER} #MemeStreet", "device": {"metaphor": "a lift with three cables", "opening": "the car hangs"},
              "scene_js": "({t, api}) => ''", "scenes": [{"kind": "free", "vo": "Six words here are too many yes.", "text": "Six words here are too many", "hot": "zzz"},
                                                         {"kind": "outro", "vo": "Join free at memestreet.net.", "text": "Join free"}]}
        es = check(fr, {"recent_devices": [{"metaphor": "a lift with three cables cut", "opening": "x"}]}, [], "One trick")
        assert any("2 to 5 words" in e for e in es) and any("hot 'zzz'" in e for e in es) and any("too close to a recent" in e for e in es), es
        fr["scenes"][0].update(text="too many yes", hot="many"); fr["device"]["metaphor"] = "a kettle that boils over"
        es = check(fr, {"recent_devices": []}, [], "One trick")
        assert not any("2 to 5 words" in e or "hot" in e or "too close" in e or "must be a hook" in e for e in es), es
        assert not check(dict(fr, scene_js=None), {}, [], "One trick") == [] and any("director reel" in e for e in check(dict(fr, scene_js=None), {}, [], "One trick"))
        assert "- Total spoken words" not in RULES and "- Length: 35 to 60" in RULES and "- Plain words" in RULES
        # the first 3 seconds, the ending and the caption (docs/ROADMAP.md A2, A5, A9)
        floor = lambda x: bool(BAD_OPENER.search(x) or hookscore.run(x)[3])
        bad = ["Three chart reads in thirty seconds.", "Three charts, five seconds each.", "Here are three candles every trader should know.",
               "Stock story: Ember Dragon Ranches.", "Support and resistance explained.", "Today we look at stop losses.", "In this reel I will show you how stops work.",
               "A stop loss is an order that sells when price falls.", "Support is a price level where buyers step in.", "Welcome back to Meme Street.",
               "Hey traders, quick tip for you.", "Let\x27s talk about risk.", "Lesson four: the hammer candle.", "Five mistakes every beginner makes.",
               "Trading mistake number one.", "Chart quiz time.", "A breakout is when price leaves its range.", "3 mistakes you must avoid."]
        good = ["Your boat has holes.", "This candle lied to everyone who sold it.", "Can you call them before the chart does?", "Gains take the stairs.",
                "You lost eleven percent in one candle.", "Why does your stop get hit right before the bounce?", "He sold the bottom.", "Would you buy this candle?",
                "This trader turned a win into a loss in nine seconds.", "Nobody tells you the dip is the entry.", "Your stop is the only thing between you and zero.",
                "The market is a liar and it just lied to you.", "Three red candles in a row and you sold.", "Two traders bought the same candle.",
                "He did one thing wrong: he moved his stop.", "One candle is all that stood between him and zero.", "Nobody explained this candle to you.",
                "Today your stop got hit for the third time."]
        assert all(floor(x) for x in bad) and not any(floor(x) for x in good), ([x for x in bad if not floor(x)], [x for x in good if floor(x)])
        mine = ("scene 0 is a free scene", "scene 0 opens on", "first spoken sentence", "the outro is the sign-off", "16 spoken words", "opens on background")
        for f in sorted(glob.glob(os.path.join(HERE, "scenes", "fixtures", "*", "spec.json"))):      # (the seeds the writer learns from obey the rules it is checked by)
            sp = json.load(open(f, encoding="utf-8")); es = check(sp, {}, sp.get("charts") or [], "One trick")
            assert not any(m in e for e in es for m in mine), (f, [e for e in es if any(m in e for m in mine)])
        ok = dict(fr, caption=f"Which level are you?\nMost people never leave level one of trading.\nPractise at memestreet.net\n{DISCLAIMER}\n#MemeStreet #trading")
        es = check(ok, {}, [], "One trick")
        assert not any(m in e for e in es for m in mine + ("the caption: ", "question the reel asks", "people search for")), es
        no = dict(fr, caption=f"A lesson.\nPractise at memestreet.net\n{DISCLAIMER}\n#MemeStreet #trading #stocks #charts #candles #investing")
        no["scenes"] = [dict(fr["scenes"][0], chart=0, vo="Three chart reads in thirty seconds. Too many yes."), {"kind": "outro", "vo": "Practise spotting the sweep on real charts every single day. Join free at memestreet.net."}]
        es = check(no, {}, [], "One trick")
        for m in ("never on a chart", "format promise", "the outro is the sign-off", "cap of 5", "question the reel asks", "people search for"): assert any(m in e for e in es), (m, es)
        assert not any(m in e for e in check(no, {}, [], "Daily recap") for m in mine + ("question the reel asks", "people search for"))
        # seconds 3 to 15, and the loop (docs/ROADMAP.md A3, A4)
        bg = ["Deepwater Homes is a builder that sells flats under the sea.", "The company makes umbrellas for dragons.", "It was founded in 2019.",
              "A stop loss is an order that sells for you.", "Founded in a garage, it grew fast.", "It is a company with one product.", "Support means that buyers wait there."]
        fine = ["And that was the good day.", "Twenty trades a day felt busy and smart, but every single one cost a spread and a fee.", "Question one.",
                "Price had bounced off this level three times, so every buyer put their stop just under it.", "Seven winning days, one step a day.",
                "Then the cable snapped.", "Deepwater Homes sells them anyway.", "This is the candle that fooled everyone.", "It was a trap.", "Level one: the gambler."]
        assert all(BACKGROUND.search(x) for x in bg) and not any(BACKGROUND.search(x) for x in fine), ([x for x in bg if not BACKGROUND.search(x)], [x for x in fine if BACKGROUND.search(x)])
        es = check(dict(fr, scenes=[dict(fr["scenes"][0], vo=" ".join(["word"] * 17) + "."), {"kind": "free", "vo": "The company makes rain. More words.", "text": "makes rain"}, fr["scenes"][1]]), {}, [], "One trick")
        assert any("16 spoken words" in e for e in es) and any("opens on background" in e for e in es), es
        lp = {"title": "T", "type": "Loop", "caption": f"Would you hold?\nA stop loss in ten seconds of trading.\nmemestreet.net\n{DISCLAIMER}\n#MemeStreet", "device": {"metaphor": "a kettle", "opening": "it boils"},
              "scene_js": "({t, api}) => ''", "scenes": [{"kind": "free", "vo": "Your stop is the only thing between you and zero.", "text": "between you and zero", "hot": "zero"},
                                                         {"kind": "free", "vo": "Move it once and it is gone, which is exactly why", "text": "it is gone", "hot": "gone"}]}
        es = check(lp, {}, [], "Loop"); assert not any(m in e for e in es for m in ("memestreet.net", "outro", "narration is", "16 spoken", "background")), es
        es = check(dict(lp, caption=f"x {DISCLAIMER} #MemeStreet", scenes=lp["scenes"] + [fr["scenes"][1]]), {}, [], "Loop")
        assert any("no outro scene" in e for e in es) and any("put memestreet.net in its caption" in e for e in es), es
        assert ROTATION["1300"].count("Loop") == 2 and "Hard truth" in ROTATION["1200"] and LENGTH["Loop"][2] is False and "Loop" in CATEGORIES and "Loop" in KINDS
        print("ok")
    elif a[0] == "revise":                               # <work> <review.json>: rewrite after the film critic's notes
        revise(a[1], json.load(open(a[2], encoding="utf-8")))
    elif a[0] == "brief":                                  # for a writer elsewhere (a cloud session): <dir>/brief.json
        B = brief(a[1], cat, rem); os.makedirs(a[2], exist_ok=True)
        json.dump(B, open(os.path.join(a[2], "brief.json"), "w"))
        print(f"{a[2]}/brief.json: {B['category']}")
    elif a[0] == "assemble":                             # <dir>/brief.json + <dir>/script.json (the writer's reply) -> spec.json
        B = json.load(open(os.path.join(a[1], "brief.json")))
        spec, errs = parse(open(os.path.join(a[1], "script.json"), encoding="utf-8").read(), B)
        if errs:
            raise SystemExit("fix: " + "; ".join(errs))
        save(spec, B, a[1])
    elif a[0] == "pair":                                 # <slot> <work v1> <work v2>: one brief, the current reel and version 2
        pair(a[1], a[2], a[3], cat)
    else:                                                # <slot> <work>: brief, write, save
        B = brief(a[0], cat, rem)
        if rules_file(B["category"]): B = v2_brief(B, rules_file(B["category"]))
        save(write(B, work=a[1]), B, a[1])
