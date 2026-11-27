# The studio's engines: how a reel is drawn, looked at and rendered

A reel is a folder `studio/reels/<name>/` holding `reel.json` (see the top of `studio.py`). Its `engine` says who draws it and
its `entry` says what. All four draw 1080 x 1920 at 30 frames a second, and every frame is a pure function of time (seeded
randomness, nothing carried from the frame before): frames are drawn out of order by several workers.

Before anything on this PC: `source D:/reel-tmp/studio_env/env.sh` (ffmpeg, the browser, Manim's Python, temp folders on D:
because C: is nearly full). Run `python studio.py ...` from `memestreet_game/reels/src/studio/`.

| Engine | What it is | `entry` | Its data |
|---|---|---|---|
| `hf` | A HyperFrames composition: HTML + CSS + a paused GSAP timeline | `<project>/index.html` under `engines/hf/` | `window.__R` (the timeline) in `window.__build(R)` |
| `remotion` | A React composition (Remotion 4) | the composition's id in `engines/remotion/src/Root.jsx` | its props |
| `manim` | A Manim scene (maths, graphs, lines being drawn) | `file.py::Scene` under `engines/manim/` | the JSON file named by the env var `STUDIO_PROPS` |
| `page` | One of our own pages (`engines/ride/ride.html`, three.js) | the page's path under `engines/` | `window.__R` |

## The loop for making one
1. Write `reel.json`. `python studio.py lint <dir>` must print `ok` (the Triple Hook, the choice, the length).
2. `python studio.py fake <dir>` writes `work/timeline.json`: `props` plus, for a narrated reel, estimated word times
   (`words`, `caps`, `cuts`, `T`). A silent reel gives its own length in `props.T`.
3. `python studio.py stills <dir> "[0, 0.5, 1, 2, 4, ...]"` draws one picture at each second into `stills/` and a `sheet.jpg`.
   **Open them with the Read tool and LOOK.** This is the only way to know what was made. Repeat 3 until every still is right.
4. `python studio.py render <dir>` writes `work/silent.mp4` and `out/cover.jpg`. One full render at the end, not one a change.
5. Sound (`sound.py`, on the reel server), then `python studio.py check <dir>` and `python studio.py pack <dir>`.

## hf (HyperFrames)
```html
<div id="root" data-composition-id="main" data-start="0" data-duration="20" data-width="1080" data-height="1920" data-fps="30">
  <div id="title" class="clip" data-start="0" data-duration="4" data-track-index="1">...</div>
</div>
<script src="vendor/gsap.min.js"></script>
<script>
  window.__build = R => {                       // build the DOM and ONE paused timeline from the reel's data
    const tl = gsap.timeline({paused: true});
    tl.from('#title', {y: 200, opacity: 0, duration: .5, ease: 'expo.out'}, 0);
    tl.to({}, {duration: R.T}, 0);              // the timeline is as long as the reel
    window.__timelines = {main: tl};
  };
</script>
<script src="vendor/hfplay.js"></script>          <!-- always last: it calls __build(window.__R), then render(t) seeks the timeline -->
```
- `vendor/gsap.min.js` and `vendor/hfplay.js` are copied in by `studio.py` (`prepare_hf`); never edit them there.
- Everything the page loads is inside its own folder (HyperFrames' rule): fonts as `@font-face` files in the folder, no CDN, no
  network at all.
- Only GSAP moves things. No CSS animations or transitions, no `requestAnimationFrame`, no `Date.now()`, no `Math.random()`
  (use a seeded function): the grabber seeks to a time and takes a picture.
- A canvas layer listens for `hf-seek` (`e.detail.time`) and draws that time.
- `python studio.py check` also runs HyperFrames' own `lint` and `check` (overlaps, contrast, the 9:16 safe zone).

## remotion
- Add a `<Composition id="..." component={...} durationInFrames={...} fps={30} width={1080} height={1920} defaultProps={...}
  calculateMetadata={({props}) => ({durationInFrames: Math.round(props.T * 30)})} />` to `src/Root.jsx`, its code in its own file
  beside it. JavaScript and JSX only (no TypeScript set up).
- Movement only from `useCurrentFrame()` with `interpolate()` (clamped) and `spring()`. CSS animations do not render.
- Fonts: `@font-face` from a file with `staticFile()` (put it in `engines/remotion/public/`), and wait for it with
  `delayRender` / `continueRender`.
- No Remotion cloud, Lambda, licence key prompts or map keys. (Remotion is free for one person or a company of up to three.)

## manim
- `from manim import *`, set `config.pixel_width, config.pixel_height, config.frame_rate = 1080, 1920, 30` and
  `config.frame_height = 16.0; config.frame_width = 9.0` at the top of the file (see `engines/manim/smoke.py`).
- Read the data with `json.load(open(os.environ["STUDIO_PROPS"]))`. The scene's total run time must equal `props.T`
  (end with `self.wait(...)` to make it so).
- Text with `Text(..., font="Montserrat", weight=BOLD)` after `register_font` of the font file; no LaTeX (it is not
  installed): no `Tex`, `MathTex` or axis numbers that need it (`Axes(..., axis_config={"include_numbers": False})`).

## page
See `engines/ride/ride.js`: `window.ready` (a promise), `window.render(t)`, optional `window.__events()` (what is heard),
`window.__coverOn` (true while the cover is taken).

## What every reel gives the sound step
`reel.json` `events`: `[[seconds, kind], ...]` for everything that lands, bursts, counts or cuts. Kinds: `pop whoosh swish
thud ding rise boom tick coin click snap drop riser crumble sparkle buzz`. `music`: one of `Comical`, `Kidding Around`,
`Fun and Games`, `Playful`, `Just Kidding`, `The Snail`, `Bob`, `Fun Jazz`, `Classical Jazz`, `Secret Garden`, `Shock and
Awe`, `Keep Smiling`, `Little Bells`, `Comical 2`.
