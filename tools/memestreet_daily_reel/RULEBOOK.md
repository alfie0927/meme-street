# Meme Street reels: the owner's rulebook

The owner's rules for every reel. They override every other instruction. New rules from the owner's feedback are added
at the bottom with the date; the writer reads this file before every reel, and rules that can be checked by code are
also checked automatically (make_spec.py, render.py, narrate.py).

## Style
- (superseded 2026-11-09, see "Director reels") One consistent 2D house style across the page: near-black background,
  teal / green / red / amber, Cascadia Mono, the small brand header. What stays shared: 9:16, a dark background, flat 2D,
  the small brand header (logo, "Meme Street", the format tag with no episode number), the November cover.
- No 3D, no emoji animations, no realistic AI video.
- Charts sit full width on the page: no panel box, no axis numbers; volume bars only when the reel is about volume.
- (superseded 2026-11-09) Few cuts: keep one chart on screen and let it evolve. Still true for charts: when the next
  scene keeps the same chart, the chart stays put.
- (superseded 2026-11-09) Motion is smooth and slow. Now: motion is big and expressive, but every motion is eased,
  has weight and a reason; nothing jerky for no reason, no swimming background, nothing randomly placed.
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
- Captions: every spoken word is captioned, in every scene (the owner, 2026-11-09: "subtitles for ALL of the audio"). In a
  director reel a 3 to 5 word punch headline with one word in the reel's hot colour lands above them as the words are said.
  Elsewhere: one-line phrases word by word as said. Numbers are digits ("203", "12%").

## Voice
- Sarah (ElevenLabs), at a human pace (about 3.9 words a second while talking), steady (no speeding up or slowing down
  for no reason), natural short pauses at commas and full stops, every word pronounced right.

## Content
- Concise: one idea, every line earning its place. A director reel runs 40 to 120 seconds (about 60 to 300 spoken
  words) when the story earns it; the short formats are shorter on purpose (Hard truth 25 to 60 words).
- Accurate: every number and claim comes from the facts; what the voice says, the screen shows.
- Sign-off: "Join free at memestreet.net." Only a reel about the Daily Chart mentions the Daily Chart.

## Daily recap
- Superseded 2026-11-10 (the owner: "make the daily in the same creative style"): the Daily is a director reel like every
  other, its own device and palette, with the day's real chart, trades and scores as the facts (make_reel.sh).
- The Daily's chart shades the lead-in (the candles every player saw before the clock started) with a dotted line where
  the game began; the renderer draws it (the owner, 2026-11-10). No hot-air balloon device (the owner disliked it on #8), and nothing drawn over the
  candles (no line tracing the price): "I want to see the candles".
- ~~Its own format: the day's chart walked through in order at an easy pace, then the scorecard; the cover is
  "Daily Chart #N" over the chart with "Can you beat it?" and the date.~~

## Thumbnails
- The November template: brand header, the reel's main chart (or story scene) in a framed panel, the big title below,
  memestreet.net at the foot.
- A director reel's cover is its longest free scene caught at 60%, the scene layer moved and clipped into the panel like
  the stage, its punch removed: nothing of the reel's HUD, lamps or punch may ride over the brand row or the title
  (the owner, 2026-11-09: "the thumbnails suck").
- Sound: the scene-change whoosh only when the screen changes; the same chart carried on, or one free world after another,
  changes silently (the owner, 2026-11-09).

## Running
- Posts go out on schedule: reels are made ahead. Conserve credits (Claude plan, ElevenLabs).

## Added from the owner's feedback
<!-- newest last: "- YYYY-MM-DD: rule" -->
- 2026-11-07: The voice is Kokoro (af_heart) again, not ElevenLabs (REEL_VOICE=kokoro), with words it says wrongly fixed in pronounce.json.
- 2026-11-07: Captions ease in word by word and each line eases out before the next; a line never leaves one word on its own.
- 2026-11-07: A stock story is just the company, never its chart: the seven beats of the November stories (an illustrated odd fact, what it is, how it makes money, why it matters, what's unique, risks and what moves it, the sign-off), with richer animation. Reading a stock's chart is a separate format with its own structure (Chart breakdown).
- 2026-11-07: Story scenes are literal and creative, never abstract: a ranch is fenced pens with the animals and a hut; demand is people joining a line one by one; what moves a stock can be candles falling across the screen and bursting into the next scene. At most 2 labels a scene, never one naming the obvious; nothing cut off at the edges.
- 2026-11-07: The sign-off comes in slowly and gently (no sudden cut) and holds a moment.
- 2026-11-07: Daily recap: when just buying at the open and holding beat the day's best trades, own it early and in our voice: 'the stock did better than us today, but we trade proper setups' (not hope). Never hide it.
- 2026-11-08: All reels are made like the stock stories: every reel's hook is an acted story scene (actors and an event on its words), the Kokoro voice, the November cover. Exempt: the Daily recap and the stick-figure formats, which already act every scene. (superseded 2026-11-09: every reel opens on its own device, drawn by its own scene function; the Kokoro voice and the cover stay.)
- 2026-11-07: Something literal happens in every story scene: a truck drives into the escaped dragon with a boom, a rocket launches and crashes, coins pour out of a job. Never a still picture with tags; never a figure of speech.
- 2026-11-07: Stock stories are fully illustrated and alive, never stiff: no text-list scenes (how it earns is the company doing each job and getting paid; what can hurt it is a storm whose lightning strikes on each risk), a living edge-to-edge world (sky, stars, drifting clouds, sliding hills), scenes that slide into each other, and characters that act (a dragon breathes fire).

- 2026-11-08: The voice keeps one speed through the whole reel and across all reels: never slowing down or speeding up between lines (Kokoro at 1.0 for every line).
- 2026-11-08: Nothing overlaps: an acted opening scene stands alone (the chart and its tags come in from scene 1), and no tag sits on another prop, a cloud or another tag; a tag that has no room above its prop goes beside it.
- 2026-11-08: A tag appears when its words are said, never before, and stays up while its prop is on screen: it never blinks off and back on.
- 2026-11-08: Props stay upright. A candle, chart card or question card never flies, falls or crashes; it grows, changes colour, bursts or counts where it stands.
- 2026-11-08: Story scenes are alive, not stiff: at least two things happen in each, on their words.

- 2026-11-08 (rating session): No spray effect anywhere. Crashes, falls and knock-aways are dramatic: a hard landing shakes, a winner knocks the loser off the screen, a threat is thrown back.
- 2026-11-08 (rating session): Cast literally: sellers and customers are people, a company is what it does (not a generic factory or building), a brand is its product, a reservoir is a lake that fills, a record hatch is an egg hatching a baby dragon, an escape is a dragon breaking out of a cage, a sick herd shows a sick dragon. Tags name real things ("Customers", "Trucks"), never ideas ("Waiting list", "Old way").
- 2026-11-08 (rating session): Nothing extra in a scene: no stray stacks in a corner, no props floating over a layout, nothing under a prop that the line did not name. A layout is laid out symmetrically and no tag touches a prop.

- 2026-11-08 (rating round 2): Things knocked or thrown away fly in a natural arc and tumble, never glide. Things appear by rising gently into place, never sliding in jerkily. Reactions (hearts, money) start after the landing, from both sides at once. Rain falls from a cloud straight down into what it fills. Something hatching cracks its shell, the top flies off, and the creature peeks out; something caged is seen inside before it breaks out from the centre. A crashing rocket turns over; a crashing plane dives. No number tag when the voice says the number. Coins look like coin stacks; a train has its engine.
- 2026-11-08 (rating round 3): Streams (hearts, coins) flow out of their source one by one to the target, never appear all along the path. Rain falls across the cloud's width, never as one line. No trail behind something rising. A hatchling only peeks its head out. Nothing flashes before it appears. Chart scenes: at most 3 marks, lines or shades at once; a percentage tag sits above its candle; the quiz timer sits low, under the options; a speech bubble keeps its side and its text stays small; big text must make sense on its own.
- 2026-11-08 (rating round 4): Big text says the whole thought plainly, the way the owner put it: "One bounce off support doesn't mean it will hold", never a clipped "One bounce off support is not a hold." Rain comes only from the cloud it falls from. A speech bubble moves with the head that tilts toward it.
- 2026-11-08 (rating round 5): A price that rises then drops is many candles marching across the screen, climbing on "rises" and tumbling on "drops" (shot rally_drop), never one candle. Big text keeps the last chart on screen until its first word. A speech bubble sits above and beside the head, clear of raised arms.
- 2026-11-09 (rating round 7): Teach a signal by showing it work: name it, point at it, reveal the price doing what it says, then say why in two or three plain reasons; only then, once and briefly, that it does not work every time. Never "only a clue" over and over. When the next scene keeps the same chart, the chart stays put (no fade, no pop): only the title and the drawings change, and a level already drawn stays drawn. Every reel opens with its own animation, never one a recent reel used. A line's tag sits at the start of the line and never hops as candles come in. Candles draw at one steady speed. The voice never pauses inside a phrase. "Doji" is said "DOH-jee"; say "slightly below", never "a hair below".
## Director reels (the owner, 2026-11-09: "I want you to be autonomous. I want you to be CREATIVE. These reels aren't going to be successful if they're run-of-the-mill explanation reels. REALLY over-the-top, cool animations with more expressive explanations. Each reel unique, easy to understand and visually awesome.")
- Every reel is a short film with ONE visual device that carries the whole lesson, set up in the first second and paid
  off at the end (a boulder that cracks on the hundredth hit, a lift whose cables are cut, a weather forecast, two divers;
  see exemplar/NOTES.md for the craft). The device is invented fresh for each reel: never one of the last 30 reels'
  devices, never a reference reel's device copied (the owner: "those are just exemplars; use your own creativity").
- A HUD that changes under the story (a counter, an account line, a bar, a date), in the title's place.
- Each reel owns its palette and mood (two or three colours, dark background); shared: 9:16, flat 2D, the brand header,
  the cover, the Kokoro voice at one speed, the sign-off.
- Punch headline: 3 to 5 words of the line in capitals at y 1270, one in the hot colour; the transcript captions run
  under it for every spoken word (the owner, 2026-11-09: subtitles for all of the audio).
- 40 to 120 seconds; something changes on screen every 2 to 3 seconds; motion is big and has weight; impacts shake.
- Easy to understand with the sound off: the device, the HUD and the punches tell the story on their own.
- Reels post without the owner's approval (the owner, 2026-11-09). The owner's feedback on posted reels goes under
  "By format" as before.

## By format (the owner's feedback on each type as it posts; a reel of that type follows its lines)
<!-- "### Format name" then "- YYYY-MM-DD: rule", newest last -->
Each format is watched (the owner reviews its posts) until 5 posts in a row draw no complaint; then it is trusted and posts
without review. A complaint puts it back to watched. Status: every format watched (2026-11-08).
### Chart quiz
- 2026-11-08 (round 5): the new Guess the move is good; its opening can be more creative than a lone question card, and the question card is a little smaller.
- 2026-11-08: The deleted 21:00 Guess the move was ugly: props over the chart in the opening, long options squeezed into tiny three-line text, a faint company line. Every quiz and Guess the move now shows short option labels (max 4 words) in bigger text, and the company line is bright.
- 2026-11-08 (rating session): the three-cards-and-a-question hook is good; no spray over the cards.
- 2026-11-08: The quiz itself is good: keep its questions, answer cards and reveals as they are.
- 2026-11-08: The hook acts out its words with real things: "Three charts, three questions" is three chart cards and a question card, never blank bars or shapes standing in.
- 2026-11-08: The Q1, Q2 badge has no shadow and sits on the same line as the headline text.
- 2026-11-09 (round 7): a stop answer shows one arrow at the right stop, never a line for every option ("Wide" on the chart was hard to read). No pause before a word mid-sentence.
### One trick
- 2026-11-08: The opening was ugly: a candle flying up and falling at an angle over the chart, with tags on top of a clock. Keep the opening clean: one simple acted scene, upright props, no chart behind it.
- 2026-11-09 (round 7): ugly. Same chart in the next scene: keep it, just change the tag. Its opening was the same animation as other reels; each reel needs its own.
### Chart twist
- 2026-11-08: The opening was ugly: a falling red bar crossing a shield on top of the chart. Same fix as One trick: the opening stands alone, upright props, nothing overlapping.
- 2026-11-09 (round 7): good.
### Stock story
- 2026-11-08 (rating session): liked: the hero scene (the company big in the middle), the line of buyers, the risk scene. Earns: show the company as itself, not a factory. Storm: the third risk sits above the company, tags never on props. Grow: profit rises on its own; a price that drives it rises separately.
- 2026-11-08: FogWorks was OK but stiff: more happens in every scene. Tags come on their words (not "Mist machines" before it is said), never vanish and come back, and go beside a prop when something is above it ("District" out to the side, not on the cloud).
### Hard truth
- 2026-11-08 (round 5): good; the big-text line keeps the chart from the scene before on screen until the words come in.
- 2026-11-08: Remade with the voice at one steady speed.
### Trading mistake
- 2026-11-08 (round 5): good. Say "if you had to guess", never "be honest, you'd guess". The opening is candles marching across, rising on 'rises' and dropping on 'drops'.
### Big players
- 2026-11-09 (round 7): good. When the next scene keeps the same chart and level, keep the level on screen and just remove the old tag ("Closes below").
### Chart breakdown
- 2026-11-09 (round 7): good. Same chart in the next scene: keep it there. No pause before a number ("36").
### Technical lesson
- 2026-11-09 (round 7): ugly. A new opening animation for each one. The orange and blue average lines the voice names are drawn. Show the signal working (a golden cross, then the rise), then why, then one short "not every time".
### Myth or fact
- 2026-11-09 (round 7): ugly. The "Your call" tag sits at the start of its line so it does not jump as the price moves. Same chart: no transition.
### Speed cheat sheet
- 2026-11-09 (round 7): ugly. "Doji" is "DOH-jee". No odd pauses.
### Stick skit
- 2026-11-09 (round 7): same chart in the next scene: no transition, only the people switch. Candles draw at one steady, slightly slower speed. The message must be clearer.
### Explained like you're 5
- 2026-11-09 (round 7): ugly. The candles draw while the voice says "each step is lower than the one before".
### Trader levels
- 2026-11-09 (round 7): good.
