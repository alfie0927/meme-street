# Meme Street reels: the owner's rulebook

The owner's rules for every reel. They override every other instruction. New rules from the owner's feedback are added
at the bottom with the date; the writer reads this file before every reel, and rules that can be checked by code are
also checked automatically (make_spec.py, render.py, narrate.py).

## Style
- One consistent 2D house style across the page: near-black background, teal / green / red / amber, Cascadia Mono, the
  small brand header (logo, "Meme Street", the format tag with no episode number). Each format may have its own layout
  inside that style.
- No 3D, no emoji animations, no realistic AI video.
- Charts sit full width on the page: no panel box, no axis numbers; volume bars only when the reel is about volume.
- Few cuts: keep one chart on screen and let it evolve (reveal, mark, shade, zoom, lines). At most 3 switches of what
  fills the screen before the outro (5 in a stock story).
- Motion is smooth and slow: nothing jerky, no moving backgrounds, nothing that looks off or randomly placed.
- Never an abstract stand-in for an idea (a box for "your trade", triangles for "panic"). If it cannot be read in one
  second with the sound off, use the chart, cards or Rookie and Pro instead.

## Stock stories
- 2 or 3 animated 2D scenes in the PhaseJump look (flat neon line art) showing what the company does and its good and
  bad news, with real things acting out the line.
- One label per idea: a waiting list is a queue of people labelled "Waiting list", not a person plus extra labels.

## Text
- Titles are titles: the hook's title is the reel's theme, each scene head names its idea; never a copy of the line.
  An answer's title is "The answer" (the highlight shows which option).
- Proper capitals everywhere: every sentence, title, label, card and caption starts with a capital; names keep theirs.
- Captions: one-line phrases that start at a sentence or clause, appear smoothly word by word as said, and stay up for
  context. Numbers in captions are digits ("203", "12%"), never spelled out.

## Voice
- Sarah (ElevenLabs), at a human pace (about 3.9 words a second while talking), steady (no speeding up or slowing down
  for no reason), natural short pauses at commas and full stops, every word pronounced right.

## Content
- Concise: 60 to 110 spoken words, one idea, every line earning its place.
- Accurate: every number and claim comes from the facts; what the voice says, the screen shows.
- Sign-off: "Join free at memestreet.net." Only a reel about the Daily Chart mentions the Daily Chart.

## Daily recap
- Its own format: the day's chart walked through in order at an easy pace, then the scorecard; the cover is
  "Daily Chart #N" over the chart with "Can you beat it?" and the date.

## Thumbnails
- The November template: brand header, the reel's main chart (or story scene) in a framed panel, the big title below,
  memestreet.net at the foot.

## Running
- Posts go out on schedule: reels are made ahead. Conserve credits (Claude plan, ElevenLabs).

## Added from the owner's feedback
<!-- newest last: "- YYYY-MM-DD: rule" -->
- 2026-11-07: The voice is Kokoro (af_heart) again, not ElevenLabs (REEL_VOICE=kokoro), with words it says wrongly fixed in pronounce.json.
- 2026-11-07: Captions ease in word by word and each line eases out before the next; a line never leaves one word on its own.
- 2026-11-07: A stock story is just the company, never its chart: the seven beats of the November stories (an illustrated odd fact, what it is, how it makes money, why it matters, what's unique, risks and what moves it, the sign-off), with richer animation. Reading a stock's chart is a separate format with its own structure (Chart breakdown).
