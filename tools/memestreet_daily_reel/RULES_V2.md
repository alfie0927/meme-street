# Reels v2: rules for reels people don't skip

Version: 1

Approved by the owner on 2026-11-07 for testing: version-2 reels are made from the same facts as the current reels and
posted as Trial Reels (non-followers only; Instagram shares one with followers if it performs), one pair a day, until
the numbers say which version wins. Where these rules differ from the rulebook, these win for version-2 reels.
Sources: lab/research/ (Instagram's own guidance and Meta's ranking cards, Socialinsider's 9.77M Reels, Emplifi, Buffer;
419 finance Shorts; the owner's exemplar reels; the simulated audience). Instagram first shows a reel to a small
group of non-followers and widens it if they watch, share and like; about 65% of a small account's viewers leave
within 3 seconds.

## The template (src/reel_v2.html), so none of this is a fault
- No brand bar or progress line for the first 3 seconds; they fade in at 3 s.
- The hook text is big and white with its key word in amber; at most 48 fat candles are in view; the newest candles
  replay in the first second; captions are bigger.
- A two-way quiz call is two big green and red buttons; a quiz's options are up from the first frame.
- The sign-off sits over the last chart, dimmed; there is no separate end card.
- Fixed by the owner for every version (2026-11-08): the cover's brand row (logo, name, format tag) is the Daily cover's size and sits where the Daily's does; the hook is an acted story scene (actors and an event on its words, the stock-story style), and the chart comes in from scene 1, at its most dramatic part.
Also fixed by the owner (2026-11-08): the scene library (src/shots.py's shots and the story layouts) is drawn once and rated by the owner; a version may choose shots, casts and words, never change how a shot looks.

## The first three seconds decide
- Frame 1 is the hook. At 0.0 s the screen already shows the on-screen hook (2 to 7 words: the reel's question, dare
  or stake, in other words than the voice) and its acted scene already moving (the event lands in the first 2 s); the
  chart follows at its most dramatic part (the crash, the spike, the decision point). Never open on a title card, an empty chart, a logo or a slow reveal.
- The voice starts on the first frame and says the stake in under 2 seconds: a number with stakes ("This stock fell
  34% in one hour"), a dare ("Only 1 in 5 get this right"), or a question with two or three answers.
- Legible to a stranger: the first line names the real-world idea in plain words ("stop-loss", "support", "breakout"
  said as what it does). A fictional company's name is never the only hook.
- Open specific (in 419 finance Shorts, specific openers were 20 of the 29 winners and 0 of the 19 losers): a
  first-person confession with a stake ("I lost 400 practice MB on one breakout. The volume warned me."), a withheld
  point ("Your support line is drawn. Good, but the volume disagrees."), a concrete surprise with a name and a number
  ("Ember Dragon Ranches lost 31% in a day. Its dragons were fine."), a viewer's real question answered, or a
  two-and-one contrast ("Same level, two charts. One breakout is real, one is a trap.").
- Never open generic: no greeting, no "Ever feel like...", no maxim aimed at "you", no result flex (11 of the 19 losers).

## Keep them watching
- One question, one payoff: tease early, reveal in the last third, no dead air.
- Something visibly changes every 2 to 3 seconds: a candle grows, a mark lands, a zoom, a number ticks.
- The ending is the reveal or the twist. The sign-off is one short spoken line over the last frame, never a separate
  card; the last line leads back to the first, so a replay runs on smoothly.

## Give them a reason to send it
- Each reel has one thing a viewer would forward to a friend: a surprising answer, a "most people get this wrong"
  chart, a relatable trader moment. Ask for one earnest action (comment your answer), never "comment YES" bait, and
  no promo or "follow for more" ending (link and promo endings sat with the losers).

## Formats
- Quiz: one chart, one question that starts an argument (the mechanic alone is average: "Keep two, cut two" and "which
  is better" questions beat plain picture-guessing), two or three options of at most 4 words each ("Tight", "Under
  support", "Far below") given in "labels" (the game's own long options stay underneath), a visible 5-second countdown,
  then the reveal with the candles running. No jargon in the question: say
  what a term does ("the price where you sell if you're wrong") the first time. Ask for the answer in the comments
  before the reveal.
- Stock story: lead with the drama, the crash or spike and its absurd cause ("One escaped dragon cost this stock
  12%"), then what the company does, then the lesson.
- Stick-figure parable: a relatable trader moment ("Day 1 vs day 100", "Me buying the top"), on-screen text and
  counters ticking, music-led, few words.
- Lesson: one rule, shown on a chart, framed as a mistake to stop making ("Stop putting your stop here"), or as
  "X vs Y: which is better?" (3 of 3 such Shorts beat their channel's median at least fourfold).

## Words
- Stakes in money or percent, second person ("you"), concrete over abstract.
- Length stays 30 to 45 seconds (the current 60 to 110 words); 20-30 s and 45-55 s cuts are tested as Trial Reels.

## Versions
- 1 (2026-11-07): the first version, from the research and the owner's seven decisions.
