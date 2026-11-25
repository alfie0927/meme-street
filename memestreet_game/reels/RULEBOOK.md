# Meme Street reels: the owner's rulebook

The owner's rules for every reel. They override every other instruction. New rules from the owner's feedback are added
at the bottom with the date; the writer reads this file before every reel, and rules that can be checked by code are
also checked automatically (make_spec.py, render.py, narrate.py).

## One style for every reel (the owner, 2026-11-22: these lines win over every line below)
- "the reels are horrible. completely remake everything from the ground up ... copy their styles, there should be NO
  differences (except mine is one unique style for all reels)". Every reel is the story explainer (src/explainer/, the
  memestreet-reel skill): since the same evening a flat 2D cartoon explainer copied from the owner's reference (an AMD vs Intel
  story, src/explainer/REFERENCE.md), a new scene every sentence that SHOWS what is said. The 3D one-shot (src/oneshot/), the old
  formats, the town, the serial and the cards are retired.
- The owner on the 3D cut, 2026-11-22: "so many overlapping parts and the audio doesn't sound right sometimes (it should say 'dot
  com' and gopro is pronounced GO-PRO not GPRO) ... shows every part of the story, e.g., shows the GO PRO as it's being made ...
  it shouldn't just be people walking around an office, there should be different scenes for each new stock based on what they
  do and the story told." So: show what the company makes and show it being made; every event its own props; props in grid
  cells, never overlapping (the build measures every frame); the ticker is never said; a word said wrong goes in
  src/explainer/say.json.
- The owner, 2026-11-23, on the flat cut: "it should be 3d like the previous reel was, except it goes through all the events and
  story like this current reel". The reel is drawn as low-poly 3D sets (src/explainer/story3d.js), one per sentence, the camera
  trucking from set to set; the words and figures stay flat on top.
- The owner, 2026-11-23, on that first 3D cut (29 views; 59% gone in the first 3 seconds; those who stayed watched 16 of its 101
  seconds): "i still don't like it... make the reel better. also it's pronounced GO PRO (two words). remake it better. it's only
  got 28 views". What was wrong is now the rule. Every sentence is a SHOT: one or two subjects at real size and the camera
  placed so that they fill the frame, never small props standing in cells of an empty or dark set. The first frame is
  someone USING the product, moving, under a contradiction in two big lines ("NO ADVENTURES / STOCK DOUBLED"), with a headline
  that stays all reel (the first try opened on the product on a stand with its price: the simulated viewers left, "it looks
  like school"); the real chart is on screen within six sentences. The script
  is ONE story with a turn and a last line that stings, never a list of headlines, never "X reported" (the sources go in the
  caption); at most 16 figures; a shot is at least 5 words. Captions are big and outlined. "GoPro" is two stressed words
  (say.json: "Goh Proh"); a pronunciation is checked by the voice's phonemes (`make.py phonemes`), because a transcript reads
  "GoPro" either way; "$4.80" is said "4 dollars 80".
- The owner, 2026-11-23, on the remake: "better. but i think it can still be better. the caption timings can be better, i want
  the music to be better (and not as loud), also at the beginning explain that this is today's mystery chart. also where else you
  can make it better do that too", and a second model reel: "you can use this animation style too" (instagram.com/reel/DgFcR67I_M5,
  a 3D animated story: toy figures with a big round head and a drawn face, saturated patterned sets, close restless shots,
  captions of one to three words). So:
  - The reel is the answer to the game. Its first sentence begins "Today's mystery chart on Meme Street" (a reel made a day late
    says "Yesterday's", later the weekday) and never names the company; its shot is the chart itself, marked "???". The second
    sentence is the reveal ("It was GoPro, the maker of action cameras."). The header reads "TODAY'S MYSTERY CHART" all reel, with
    the company's name from the moment it is said. The last sentence is always "A new mystery chart goes live at midnight."
  - Captions: one to three words at a time (five when the words come fast), on screen whole for at least half a second, each
    word's time taken from its own letters as heard (figures and "GoPro.com" used to pop in on a guess), shown 0.06 s early;
    the words not yet said are dimmed and each lights up as it is said.
  - Music: a light tune of the reel's own (piano, mallets, a soft pulse; it drops out on bad news and comes home at the end), set
    21 dB under the voice by measurement. The bed before was a low drone only 14 dB under. Effects sit 13 to 20 dB under.
  - People are toy figures with drawn faces that show what they feel (calm, joy, smug, shock, sad) and blink. Only the style is
    the model's: none of its characters, costumes or pictures is copied.
- The owner, 2026-11-23, on the mystery-chart cut: "this is way better. make sure the audio is smoother though. it should flow
  like normal human speech. remake with this, then post it". Keep what that cut was (the mystery opening and reveal, the toy
  figures, the captions, the tune). The voice: spoken in breaths of three or four sentences that the voice reads in one go, all
  at ONE speed (1.2: about 5 syllables a second while talking, as the owner's model narrators); its pauses stay where it put
  them and get a person's length (0.28 to 0.42 s between sentences, 0.08 to 0.18 s at a comma, no stop over 0.1 s in
  mid-phrase); every breath at one loudness; the mix at one gain. Never again: a clause spoken on its own, a speed per phrase,
  the same pause every time. Posted that day at 16:55 UTC: instagram.com/reel/DgF24MUDRkL.
- The owner, 2026-11-23, an hour after that post: "these should also upload to youtube as well". Every reel that goes on
  Instagram goes on YouTube as a Short too. The queue already does it (queue_post.sh runs src/post_elsewhere.py after
  post_instagram.py; YouTube is on, public); a reel posted BY HAND gets the same second step (it had been skipped twice).
- The owner, 2026-11-23 evening, sending a third model reel (instagram.com/reel/DgF4yeEhDOA, "How Bats Almost Won WW2") and then,
  on the first try: "you didn't copy the style of the reference reel at all... copy it. make some of the speech a bit slower,
  sometimes words get slurred"; "use all the skills you have to make sure the voiceovers are as realistic as possible"; "make the
  music more exciting, and creative (it's too AI generated and boring rn)"; then, on the result: "i like it. i just won't really
  like the music. change the music up so it's more unique. all daily reels should follow this format now". THE FORMAT NOW:
  - People are flat 2D drawn cut-outs standing in the 3D sets, facing the camera: big white heads, thick black outlines, huge
    eyes, drawn expressions, stick legs (only the model's style; every character is drawn here).
  - No words on the picture but the captions: no header, pill, progress bar, title, stamp or counter. A small letter-spaced
    "MEME STREET" mark top left. Captions in heavy white Montserrat with a dark edge, one to three words, mid-low.
  - Deep focus blur, a colour grade, a camera that drifts.
  - The voice is ElevenLabs ("Liam", a young American narrator) on the Starter plan the account pays for, about 3 words a second
    (never pushed: the other voice slurred at 1.38x); drafts are read by the free voice, only the filmed cut by ElevenLabs.
  - The music is a real track by an independent artist (Jamendo, CC BY, credited in the caption), a different one by title;
    never synthesised (too "AI generated") and never Kevin MacLeod (heard everywhere).
- The owner, 2026-11-23 night: "i don't like this music... use the music that is typically used in these types of reels", and two
  more model reels to use too: instagram.com/reel/DgGTIW0ycZD (flat stick-figure cartoon: one or two words a caption with the word
  that lands in yellow, whip-pan cuts with motion blur, sound effects on every cut and action) and instagram.com/reel/DgD9kbZv3AZ
  ("The Bunker": a place-and-time tag with a series badge at the start, a live counter at the top, an A/B "WHAT WOULD YOU DO?"
  card at the end, "Comment A or B below"). So: the music is the genre's (the channels it copies use sneaky pizzicato orchestral
  comedy, mystery pulses and cinematic cues from a paid library; the free match is Steven O'Brien's cues, CC BY, not in Content ID,
  credited as he asks); captions light the landing word in yellow; every cut is a whip pan; the reel opens with the Daily's tag,
  shows the stock's real price in a counter at the top as the story moves, and ends on the A/B card.
- The owner, 2026-11-24, on the Express reel (128 views): "how did that reel only get 128 views...... i want THOUSANDS", then "make
  the reel better. i want all next reels to push way past this 120 view barrier ... make better such as changing the animation
  style, speed, etc, anything you think". So: 30 to 40 seconds; the first sentence is the surprise (never "Today's mystery chart",
  which now opens the reveal); frame 0 is the chart alone, filling the frame, its line racing, the claim in big words on screen.
- The owner, 2026-11-24, on the short Etsy cut ("that's really good"): "now i want more real and actual animations. like if a
  product is mentioned you can animate the product. make creative animations for everythuing said". So every shot ACTS its
  sentence out: the product assembles, a jump springs up, a blow crashes down and shakes the camera, someone leaving walks off,
  sales fill a cart.
- The owner, 2026-11-24, on the acted cut: "some of the animations are a bit over the top... also the shopping card looks kinda
  ugly. redo, it's getting better. do the same for the 9am and 4pm reels but don't over do the animations". Acts stay small.
- The owner, 2026-11-25, on the grid: "all the thumbnails are the same.... they should be different. and only the daily chart reel
  should have daily #24 on it. also i want stuff to be more inventive and creative". Every reel its own thumbnail design; the DAILY #N
  badge only on the 23:30 story reel; stories told with characters and physical props (the chart as a ramp, a mystery crate, a coin).
- The owner disliked the old look, stories and music; the voice may stay. Budget $0.
- Every reel passes the simulated viewers (lab/audience.py) before it is queued: at least 9 of the 13 watch to the end (the owner's
  bar, 2026-11-22: as many as the best of the copied hits kept; "all 13" is a bar none of the hits passes).
- ONE reel a day, posted at 23:30 UTC, about the day's Daily stock over the Daily's window: why it moved, what happened, the
  characters (by role, tagged on screen), every claim from the researched sources (the owner, 2026-11-22).
- Dynamic and creative: each sentence its own scene, its props popping in on their words; nothing overlaps.
- Facts only from the research; a person named only as a public figure in it; no question, no moral, no call to action.

## Meme Street Daily (the owner, 2026-11-18: these lines win over every older one below)
- memestreet.net is just the Daily now: one real US stock chart a day, two minutes to trade it, its name revealed at the end. Every
  reel is about the Daily ("keep making reels but they need to be related to the daily, so less educational"): fun first, a game
  and a reveal, never a lesson. No lesson, unit, calculator, market page, shop or pass is named or sent to: they are retired.
- These reels name real stocks (the stock of a past Daily, or a real stretch from the reel bank) and their real dates and prices,
  as the facts give them. Never today's Daily stock, never a hint of it. No real person is named. What happened in those months is
  only what facts.reveal.events says; nothing is invented about why a stock moved.
- The address is memestreet.net ("Today's stock is live. Play it at memestreet.net."). The caption's last line: "Practice money only. Not investment advice."
- 2026-11-19, the owner: crazy true stock stories and stock explainers (researched, every claim with its status, fact-checked), and
  sometimes the story told in the 3D toy-block town ("Crazy stock story 3D" is a 3D exception like the serial). Stories and explainers
  may open on Higgsfield cinematic shots (the owner asked for open-higgsfield's look): no real people, no logos, no text in a shot.
- The 23:30 recap names the day's stock, what a candle was, the dates, the levels it tested and, when it moved a lot, the reason from
  the news as the researcher found it (the owner, 2026-11-19).
- 2026-11-19, the owner: "One Million Dollars" (src/roblox_trading.json) remakes the blocky one-million-steps story reel beat for
  beat about trading ("EXACTLY the same but the story is about trading"): it may run as long as that reel (up to 2 minutes, over the
  60-second ceiling), it ends by looping into its first line with no sign-off scene (the caption carries memestreet.net), and its
  narrator counts the chest down out loud, as the original does. Judge it on everything else as usual.
- Never speak a countdown ("three, two, one" in one breath was too fast): a scene asks, then "think" gives the viewer 3 silent seconds
  with a tick each second while the picture counts down (the owner, 2026-11-19).

## Style
- (superseded 2026-11-09, see "Director reels") One consistent 2D house style across the page: near-black background,
  teal / green / red / amber, Cascadia Mono, the small brand header. What stays shared: 9:16, a dark background, flat 2D,
  the small brand header (logo, "Meme Street", the format tag with no episode number), the November cover.
- No 3D, no emoji animations, no realistic AI video. One exception since 2026-11-14, the owner's order: the story serial (the format "Blocky story") is filmed in its own 3D toy-block town.
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
  The captions sit at y 1384, 59 px under the punch headline's line (the owner, 2026-11-12: "still too close to the
  text"; 1332 at first, 1356 on 2026-11-10). 1384 is as low as one line goes inside Instagram's safe zone (1440).

## Voice
- The local Kokoro voice (free; no paid voice, the owner 2026-11-10), at a human pace (about 3.9 words a second while talking), steady (no speeding up or slowing down
  for no reason), natural short pauses at commas and full stops, every word pronounced right.
- "memebucks" is said "meembucks" (the owner, 2026-11-12): `src/pronounce.json` reads it as "Meem Bucks".

## Content
- Concise: one idea, every line earning its place. A director reel runs 35 to 60 seconds (about 50 to 150 spoken
  words; the owner, 2026-11-11: viewers give about 7 seconds); 60 is a ceiling, not a target; the short formats are shorter on purpose (Hard truth 25 to 60 words). The in-depth formats (Technical lesson, Strategy test, Quant lesson, Indicator)
  may run 60 to 100 seconds (the owner, 2026-11-12: "some reels can be very in depth, like quant level explanations").
- Accurate: every number and claim comes from the facts; what the voice says, the screen shows.
- Sign-off: "Join free at memestreet.net." Only a reel about the Daily Chart mentions the Daily Chart.

## Daily recap
- The Daily opens on the decision the viewer would have faced at the day's hardest candle, never on how many played
  or the chart's number (2026-11-12: the two Daily reels that opened on the player count lost 70% of viewers in 3
  seconds; the one that opened on the chart's own event lost 41%).
- Superseded 2026-11-10 (the owner: "make the daily in the same creative style"): the Daily is a director reel like every
  other, its own device and palette, with the day's real chart, trades and scores as the facts (make_reel.sh).
- The Daily's chart shades the lead-in (the candles every player saw before the clock started) with a dotted line where
  the game began; the renderer draws it (the owner, 2026-11-10). No hot-air balloon device (the owner disliked it on #8), and nothing drawn over the
  candles (no line tracing the price): "I want to see the candles".
- ~~Its own format: the day's chart walked through in order at an easy pace, then the scorecard; the cover is
  "Daily Chart #N" over the chart with "Can you beat it?" and the date.~~

## Real news (the format "Market news")
- The owner, 2026-11-12: when a REALLY big real headline breaks, a reel on it, linked to Meme Street, posted as soon as it is made
  (`src/news_reel.py`). It is the one kind of reel that names a real company and a real person, and it comes on top of the day's
  reels. The first, on Jensen Huang leaving Nvidia, was made by hand that day.
- Only what the fact pack holds is said, shown or put in the caption, and every claim keeps its status: "admitted" only when the
  person admitted it; a report is said with its outlet ("the Times reported"); an unproven allegation is left out altogether. Nobody is named
  but the public figures at the centre. No ticker symbol, no advice on the real share, no prediction, no view on guilt.
- The person is a simple cartoon with one or two trademark features (a jacket, the hair, glasses), never a realistic face, and
  nothing cruel happens to the figure beyond the story's own event.
- Never a death, a disaster, violence, war, a crime against a person, someone's health, a child or an election.
- Shape: the story's extraordinary event inside the first second, the number or the name as the first spoken word; what happened,
  in order; the market's move as the device changing size; a question to the viewer (sell or hold?); then Meme Street: made-up
  companies with bosses too, news moves their prices the same way, 100,000 memebucks of practice money (1,000 before 2026-11-15) with no cash value; the sign-off.
- The caption names its sources and says "Not investment advice."

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
- 2026-11-16: Creative animation, and nothing overlaps anything, ever: not a figure over a figure, a figure over a prop, a prop over a prop, a tag over a prop, nor text cut off at the frame's edge (the first one-off, "Thrown Out Of The Club", posted with a figure walking through the bouncer and a tag clipped to "rick"). The dry run rejects these before the voice is made; the critic blocks a cut that shows one.
- 2026-11-08: Props stay upright. A candle, chart card or question card never flies, falls or crashes; it grows, changes colour, bursts or counts where it stands.
- 2026-11-08: Story scenes are alive, not stiff: at least two things happen in each, on their words.

- 2026-11-08 (rating session): No spray effect anywhere. Crashes, falls and knock-aways are dramatic: a hard landing shakes, a winner knocks the loser off the screen, a threat is thrown back.
- 2026-11-08 (rating session): Cast literally: sellers and customers are people, a company is what it does (not a generic factory or building), a brand is its product, a reservoir is a lake that fills, a record hatch is an egg hatching a baby dragon, an escape is a dragon breaking out of a cage, a sick herd shows a sick dragon. Tags name real things ("Customers", "Trucks"), never ideas ("Waiting list", "Old way").
- 2026-11-08 (rating session): Nothing extra in a scene: no stray stacks in a corner, no props floating over a layout, nothing under a prop that the line did not name. A layout is laid out symmetrically and no tag touches a prop.

- 2026-11-08 (rating round 2): Things knocked or thrown away fly in a natural arc and tumble, never glide. Things appear by rising gently into place, never sliding in jerkily. Reactions (hearts, money) start after the landing, from both sides at once. Rain falls from a cloud straight down into what it fills. Something hatching cracks its shell, the top flies off, and the creature peeks out; something caged is seen inside before it breaks out from the centre. A crashing rocket turns over; a crashing plane dives. No number tag when the voice says the number. Coins look like coin stacks; a train has its engine.
- 2026-11-08 (rating round 3): Streams (hearts, coins) flow out of their source one by one to the target, never appear all along the path. Rain falls across the cloud's width, never as one line. No trail behind something rising. A hatchling only peeks its head out. Nothing flashes before it appears. Chart scenes: at most 3 marks, lines or shades at once; a percentage tag sits above its candle; the quiz timer sits low, under the options; a speech bubble keeps its side and its text stays small; big text must make sense on its own.
- 2026-11-08 (rating round 4): Big text says the whole thought plainly, the way the owner put it: "One bounce off support doesn't mean it will hold", never a clipped "One bounce off support is not a hold." Rain comes only from the cloud it falls from. A speech bubble moves with the head that tilts toward it.
- 2026-11-08 (rating round 5): A price that rises then drops is many candles marching across the screen, climbing on "rises" and tumbling on "drops" (shot rally_drop), never one candle. Big text keeps the last chart on screen until its first word. A speech bubble sits above and beside the head, clear of raised arms.
- 2026-11-09 (rating round 7): Teach a signal by showing it work: name it, point at it, reveal the price doing what it says, then say why in two or three plain reasons; only then, once and briefly, that it does not work every time. Never "only a clue" over and over. When the next scene keeps the same chart, the chart stays put (no fade, no pop): only the title and the drawings change, and a level already drawn stays drawn. Every reel opens with its own animation, never one a recent reel used. A line's tag sits at the start of the line and never hops as candles come in. Candles draw at one steady speed. The voice never pauses inside a phrase. "Doji" is said "DOH-jee"; say "slightly below", never "a hair below".- 2026-11-18 (the owner: "continue the reel content but around this project now... keep reels flowing... i want to grow a following for this"): the account now grows a following for the owner's trading toolkit (risk sizing, loss limits, the journal), so the cards teach risk, sizing, orders, limits, the journal and the head (`LESSON_FORMATS[CARD]`); the Daily Chart stays and its reel with it; no reel names or advertises the toolkit until it is listed.

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
- 35 to 60 seconds (the owner, 2026-11-11; the in-depth formats up to 100, 2026-11-12); something changes on screen every 2 to 3 seconds; motion is big and has weight; impacts shake.
- Easy to understand with the sound off: the device, the HUD and the punches tell the story on their own.
- Reels post without the owner's approval (the owner, 2026-11-09). The owner's feedback on posted reels goes under
  "By format" as before.

- One reel of each format a day (the owner, 2026-11-12); the formats take turns, the one out longest ago first.
- Seven new formats on trial since 2026-11-12 (the owner: "create more types of reels, still creative, with a really good
  hook"): Two traders, Rewind, Trade diary, Candles talk, Instant replay, Expectation vs reality, Breaking news. Each opens
  on a character or an odd object with the stake in view, never a bare chart or a list.
- Instagram's numbers decide which formats stay (the owner, 2026-11-12: "make more of those / get rid of ones with high skip
  rates"): `src/format_scores.py`, twice a day. A format with 3 or more scored reels whose median skip rate is 8 points above
  the median of all reels is cut; 8 points below, it is made every day (the best two); at least 9 formats always stay.
- The first 3 seconds, every reel: frame 0 already moving and recognisable at a glance, something extraordinary before 3
  seconds, the punch between 1 and 2 seconds, the first spoken word the subject or "you", readable with the sound off
  (the checklist of the virality skill, in our terms: `FIRST3` in make_spec.py). No "comment a keyword for a DM": nothing here sends DMs.
- Depth and variety (the owner, 2026-11-12: "some of the reels are largely the same. they always talk about
  resistance/support so much. there needs to be more depth in the actual content"): a reel follows ONE idea all the way
  down (the mechanism, the number, the case where it fails) and never skims three. The subject changes from reel to reel:
  every kind of chart test takes its turn (levels and breakouts are two of eleven), and the writer sees what the last
  reels were about. Support or resistance is a reel's subject only when its own chart facts are about a level.
- Technical lessons are back (the owner, 2026-11-12: "what happened to all the technical lessons?"), in depth: one
  lesson of the site's own curriculum per reel, from candlesticks to Kelly sizing and the order book, and only what the
  lesson says.
- Strategy test, "we tested it" (the owner, 2026-11-12: "we tested [X] strategy, here's why it worked/didn't work"): one
  rule run by `src/backtest.py` on every listed stock. Every number in the reel is the test's own, a rule that lost is
  said to have lost, the sample's size is said once, and no reel promises the next trade.
- Deeper and less alike (the owner, 2026-11-15: "the animations are great, but the content is a bit too repetitive. it can
  be on more in depth lessons, e.g. quant stuff... and indicator reels"): two of the day's five reels are in-depth, at
  09:00 and 21:00 (Technical lesson, Strategy test, Quant lesson, Indicator in turn); the other three take turns through
  the rest, Market lesson among them. An in-depth reel opens on the viewer's own money or belief in plain words, never on
  a term, a formula, a setting or a study (reels that opened on a term kept 11 to 15% of viewers); the term arrives as the
  answer. A study is said by what it tested, where and when ("a 2016 study of 97 published signals"): never a
  researcher's name, a fund or a company. An indicator is shown as its true line or strip on a real chart, drawn by the
  template from computed values, with one signal that worked and one that failed, then our own test of it.
- No reel opens like a recent one (the owner, 2026-11-15, "repetitive"): the first three words differ from those of the
  last 40 reels and the first six are no near copy ("One red candle, and your...", "This chart looked..." and "Three
  chart reads..." each went out three times in a week). `check()` in make_spec.py sends a repeat back.
- Fun first, and fewer charts (the owner, 2026-11-16: "create more exciting and interesting reel formats, that do well in my
  niche. they don't even need to involve graphs, as long as they're fun and enjoyable with a meaningful hook"; "all i see
  currently are graph traces, showing trendlines, asking if people would buy"): seven chart-free formats, Money maths, Would
  you rather, Red flags, Tier list, POV, Trader translator and Horror story, each fed real facts (a site lesson, or a sum
  worked out in code). Of a day's three lighter reels at most one shows a chart; the in-depth slots keep theirs. No reel
  opens on "would you buy (sell, hold) here?".
- One-off reels (the owner, 2026-11-16: "there should be 'one off' reels that follow a completely different format, but only
  for one reel. (if they do well compared to other reels, they can be made into a more consistent format). be creative with
  it, it can be anything, so look at ALL reels in my niche"): the 13:00 reel each day is a one-off, a format this account
  has never made, invented by the writer (or taken from `src/one_off_ideas.json`, seeds from the niche's winners: 3,400
  Shorts ranked on 4 to 15 Nov, the Volume money tracker's 623 posts, the wide pull of 16 Nov). It names its format and
  states it in a sentence; its subject is a lesson, a sum, two bets or a company in turn. The scoreboard scores each one-off
  as its own row; one skipped 8 points less than our median becomes a regular format by itself (`state/promoted_formats.json`,
  two turns a day like every new format). A promoted format is still judged like every other and can be cut.

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
- 2026-11-14: the questions were the same three every time (candle name, trend, reward to risk). Change them up: they can be hard and on any concept from the lessons (options, macro, anything). Since then a quiz has one chart question (its kind rotates over quizzes) and two questions from two different lesson tracks, word for word with the lesson's answer; the hook shows question cards, not three charts.
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
### Quant lesson
- (new 2026-11-15: no feedback yet.)
### Indicator
- (new 2026-11-15: no feedback yet.)
### Market lesson
- (new 2026-11-15: no feedback yet.)
### Money maths
- (new 2026-11-16: no feedback yet.)
### Would you rather
- (new 2026-11-16: no feedback yet.)
### Red flags
- (new 2026-11-16: no feedback yet.)
### Tier list
- (new 2026-11-16: no feedback yet.)
### POV
- (new 2026-11-16: no feedback yet.)
### Trader translator
- (new 2026-11-16: no feedback yet.)
### Horror story
- (new 2026-11-16: no feedback yet.)
### One-off
- (new 2026-11-16: no feedback yet. A line here applies to every one-off; a promoted one gets its own heading.)
### Reference card
- 2026-11-17: the owner, "make all reels like this now in this style and upload schedule. remake all reels": every auto reel is a Reference card, each with a look of its own. The story serial, the Daily recap and the news reels keep their own form.
- (new 2026-11-17: no feedback yet. One scene, the hook spoken, then the card fills while the screen holds; dense, nothing touching, every cell from the lesson.)
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
### Blocky story
- 2026-11-14: "in the exemplar folder called '10-42-35' is what the roblox reel should be like": the whole frame is a scene in a blocky game town, a new shot about every 2 seconds, the money on a label on every chest, and one big white outlined word at a time as the caption (no brand header, no top hook, no punch lines).
- 2026-11-14: the one-word caption sits at y 1310 to 1440, on the ground in front of the actors. Over a character's legs it is the format and no fault; over a face or a chest number it is.
- 2026-11-14: "create the story yourself part 2, 3, 4, etc... post them one a day": the serial is `src/stories.json`, one part a day, each part ending on a cliffhanger and teaching one trading idea. Same cast, colours and town in every part. No part shows women as prizes for money (the critic refused "they get every girl" in part 1) or plays being poor for laughs.
- 2026-11-14 (evening): "add music like the roblox videos in the background and also change the voice so it matches too. then add way better animations, like a proper 3D world, where the people are walking around etc (has to be relevant for the scene)": every part is filmed in a real 3D toy-block town (`src/world3d.js`): the place the line happens in, the people it names walking and acting it out, passers-by and traffic behind them, a camera that cuts between close, mid and wide shots. This is the format, and no breach of "No 3D". The town is our own: no game's name, logo, characters or music.
- 2026-11-14 (evening): the serial has its own sound: a bouncy tune of its own under the voice, clearly heard, and a quick, bright narrator (measured on the exemplar: about 4.4 words a second, almost no pauses, a higher pitch than the house voice). Both are right for this format and no fault; the house voice and the house music stay on every other reel.
- 2026-11-14 (evening): "making sure the reels on the days after follow the same animatinos and music and voice": the look, the tune and the voice are fixed in the code (`STYLE` in `src/story_reel.py`, the town in `src/world3d.js`), the same in every part, never chosen per part.
- 2026-11-14 (evening): "on the thumbnail put 'PART 1'": a part's cover is its opening shot with PART N in big yellow letters and the story's title under it. "post this to youtube too": every part goes to YouTube as well as Instagram.
- 2026-11-19, the owner: "everything should be in higgsfield". Every reel's scene 1 is one Higgsfield film shot of its world (no
  real people, no logos, no text, never the chart); stories and explainers may add one more. The 3D town reels have none.
- 2026-11-19, the owner: "all reels should pass ... the critic should just check for any visual errors such as overlapping,
  audio errors such as fast countdowns or voice cutting out early. the reel should fix these and then post", and "the
  story/hook pipeline from your study of thousands of reels is enough to know how to write a proper story with an engaging
  hook". The critic blocks only visual and audio faults; story, hook, content and style are the writer's (the niche study's
  formula) and only notes. After one fix round the reel posts.
- 2026-11-19 late, the owner: "stop doing the higgsfield stuff ... i like the stick man stuff, but i want you to make them reels
  more like stories". No Higgsfield shots (state/video_off is on; the line above about Higgsfield is retired). Every reel is a
  short STORY told with the stick figures: one character the viewer can name (who they are in a few words), what they want,
  the chart as what stands in their way, a turning point at a real candle, and a payoff that resolves it (they win, lose, or
  learn, and the viewer sees why). The format's job (guess the stock, higher or lower, beat the chart, the recap) happens
  inside that story, as the character's choices; the hook opens on the character already in trouble.
- 2026-11-19 late, the owner: "i want MORE scenes, MORE animation, MORE cuts etc going through a story. with depictions of
  things". Every reel: a new picture every 2 to 3 seconds (more, shorter scenes; one or two lines a scene); the thing each
  line names is DRAWN as it is said (the coffee, the rocket, the empty wallet, the crowd), never just written; the camera
  and the characters keep moving; a cut lands on a beat of the story. Keep doing what the best reels on this account did
  (the learned rules from Instagram's numbers come with every brief).
- 2026-11-19 late, the owner: "the stories can also be like a crazy stock story, what happened to the stock, why did it
  happen, explain the whole history behind it, it should be like a history reel". The 13:00 Crazy stock story is a HISTORY
  REEL told by stick figures: the hook, who the company is and how it began, the road to the moment, the moment, why it
  happened (each cause with its source), what came after. 60 to 90 seconds.
- 2026-11-21, the owner: "i'm not a fan of these reels. they should be more 3d animation style". Stories, explainers and the
  Daily's game reels are filmed in the 3D toy-block town (the serial's look: townspeople, chest numbers, the square's big
  screen showing the REAL chart). The stick-figure lines above hold only for a reel that falls back to the flat look (Higher or
  lower, the market reel, the recap, or a slot whose town reel could not be made).
- 2026-11-21, the owner's goal: "remake the entire structure of my reels and how they flow etc, to get 100k views per reel on
  average". The study of the 3D story niche (research/niche3d_2026-11-21.md) found the form of the "In This Town" stories (the
  owner's exemplar is one). The 13:00 reel is one complete story on that form: the rule as the first words ("In this town,
  ..."), "You see,", gags with named neighbours, the narrator's odd place in the rule, one loved person, a crisis the rule
  causes, the rule used as the tool, a twist that proves "what everyone says" wrong, a callback; no sign-off; a question on
  screen at the end. Nothing deadly, no monsters, no trading words in the story.
- 2026-11-22, the owner: "audio that fits, realistic, and the spacing between words is like how a human speaks. nothing is
  rushed, there is time left between some scenes to build suspense etc. the music is more unique and rounded. the visuals also
  flow nicely, the framing is perfect and nothing is rushed as well", with the reel he chose as the model (a "What if" 3D
  explainer, 231,000 likes: 241 words in 96 s, 4.2 words a second while talking, a full stop heard as 0.8 s, a comma 0.4 s, a
  new shot every 3.2 s). Every town reel now speaks at that pace (af_bella at 1.1, no pitch shift, pauses x1.8, 0.75 s between
  scenes), cuts about every 3 seconds with the camera easing, may hold up to four suspense "beat"s of silence (the music drops
  to its pad), has its own music written for its timeline (sounds.score: its own key, tempo, chords and motif, warm and in
  stereo), and captions a phrase at a time with the spoken word lit. The town story is 200 to 270 words.
- 2026-11-22, the owner: "i want to make reels gather hundreds of thousands of views following how other reels did e.g. reels
  like this" (the "What if your reaction time was 10x faster?" reel). On an explainer day the 18:00 reel is a What if
  (src/whatif.py): the premise as a question in the first words and at the top of the frame, at once a consequence with a
  number, the baseline, four to six everyday vignettes small to absurd, "But there's a catch.", the downside with numbers, the
  good news, a verdict question and a last line that lands on the first picture; the power stays in a badge at the top. Second
  person, plain words, no statistics about people or companies.
