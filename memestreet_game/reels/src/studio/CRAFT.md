# Motion craft: the rules the studio animates by

Collected on 2026-11-27 from the tools the owner's model reels name, after each was read and checked for anything unsafe:
HyperFrames (heygen-com/hyperframes: `motion.md`, `captions.md`, `vertical.md`, `data.md`, `sound.md`), Motion Skills
(iart-ai: short-form video, kinetic typography, animation principles, chart animation), Remotion's agent skills, and
Lemo-Opuscar's director's notes. Numbers are theirs; where two sources differ the tighter one is kept. A reel breaks one of
these only on purpose.

## The frame (1080 x 1920)
- Words live inside x 60 to 1020 and y 250 to 1600. Instagram covers the top 120 px, the bottom 320 px and the right 120 px
  low down. The key message sits in the centre 900 x 1400.
- Headline at least 84 px, supporting text at least 44 px, captions 56 to 88 px, bold, with a dark outline of 8 to 18 px.
- At a key moment the subject fills at least a third of the frame's height. Captions never cover it.
- One number at a time, the biggest thing on screen, in tabular figures.

## Time
- Hook 0 to 1 s is on screen from frame 0. A 20 s reel: hook 0-1, setup 1-4, body 4-17, payoff 17-20. Lengthen the body,
  never the hook.
- The picture changes every 2 to 4 seconds at UNEVEN intervals. The cheapest change is a punch-in to 110 to 112 percent.
- Shots: 1 to 3 s for hype, 2 to 5 s for a story, 3 to 6 s for an explanation.
- A landed title stays dead still. Hold it 0.5 s plus 0.3 s a word; on-screen text holds letters / 15 + 1.5 s.
- One clear acceleration and one breath in every reel. Do not cut on every beat.
- Put a real silence before the peak, and the most important sound straight after it.

## Movement
- Ease by role, never one ease everywhere: arrivals `expo.out` or `power4.out` (0.3 to 0.6 s), moves `power2.inOut`, exits
  `power3.in` and 40 to 50 percent shorter than the entrance. Linear is for loops only.
- Start the next thing when the last is 30 to 50 percent done. Stagger lines 60 to 100 ms, words 40 to 120 ms, letters 20 to 40 ms.
- Nothing travels more than a third of the screen in one unbroken move, and at most a third of what is on screen moves at once.
- Anticipation 60 to 120 ms before a big move, follow-through 40 to 80 ms after it.
- Use three to five kinds of transition in a reel, each CAUSED by something on screen (a whip follows a thing that moves, a
  zoom goes through a thing). Cut at the fastest frame.
- Characters may step on twos (12 a second); the camera moves on ones.
- Keep every frame a pure function of time: seeded randomness, no carried state.

## Captions
- Real word times only. One to three words a group at high energy, one group at a time, gone hard when the next arrives.
- The word being said is lit in one accent colour and pops: scale 0.6 to 1 on a spring, or 260 ms with a back-out curve.
- Place them 62 to 70 percent down the frame (y about 1190 to 1340).
- A voice-over runs about 2.3 to 2.6 words a second, so a shot lasts its words / 2.5 + 0.4 s.

## Numbers and charts
- Ease the VALUE: ease-out for a count-up (1.2 to 1.6 s, then hold), a spring for a change of rank. Round before formatting.
- Hold a chart's first frame 1 to 1.5 s, give each row 0.3 to 0.6 s, add 0.5 to 1 s on the key moment, hold the end 2 to 3 s.
- Reveal one series at a time.

## Sound
- Every visible action has a sound that matches its material, in three layers: air, hits, music.
- A hit peaks ONE FRAME after its picture and sits 3 to 6 dB over the music. A hit more than 6 dB over reads as a startle; one
  more than 100 ms off reads as a mistake.
- Voice about 10 to 13 dB over the music. The whole reel at -14.5 LUFS (-16 to -14), peaks under -1 dB.
- Change the music when the section changes; drop it out under bad news.

## The ending
- For a loop, the last frame matches the first. 7 to 15 seconds rewatches best.
- The ending echoes the opening and asks the choice.

## What we do not use from these tools
Their installers, sign-ins, cloud renders, usage beacons, paid voices and image generators, and any instruction to act
without asking. HyperFrames' own renderer needs `ffprobe`, which this PC's app-control policy does not allow from an unsigned
download: compositions are written in its format, checked with its `lint` and `check`, and drawn by our own frame grabber.
