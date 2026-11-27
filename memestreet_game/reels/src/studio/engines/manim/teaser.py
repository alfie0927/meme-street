"""The 04:00 reel, "the new chart": an analyst's board that draws itself (engine manim, style blueprint).

It shows ONLY the trading days before the game (props.history, props.number) and reads them the way a trader reads a chart,
one mark at a time: the high, the low, the range, the last price, the direction of the last ten days. Then the days still to
come open as a hatched unknown and three arrows ask the day's vote. Every mark is worked out from the array, so no shape is
assumed; no name, no ticker, no date and nothing after the last day of history is ever drawn (BIBLE rule 2).

Two tracks: the header's hook cards run on the reel's clock (props.cards: [from, to, [[words, size, colour], ...]]), and the
board is the list of plays in film(), each starting at a fixed second (at). It prints its `events` at the end: copy them into
reel.json when a beat moves.
"""
from manim import *
from xml.sax.saxutils import escape
import json, os
import numpy as np

if config.pixel_width >= config.pixel_height:       # no upright size on the command line: the reel's own. (studio.py's stills ask for 540 x 960 at 15 a second: a quick look)
    config.pixel_width, config.pixel_height, config.frame_rate = 1080, 1920, 30
config.frame_height = 16.0; config.frame_width = 9.0
NAVY, GRID, INK, CYAN, GOLD = "#0a1c40", "#7db2ff", "#f2f7ff", "#9fe3ff", "#ffc83d"
LIT, EDGE = "#1a4f9c", "#071530"                    # the sheet: lit where the board is, dark at its corners
config.background_color = NAVY
FONT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "Montserrat.ttf")
FPS = config.frame_rate; PAL = {"ink": INK, "cyan": CYAN, "gold": GOLD}
ROUND = dict(cap_style=CapStyleType.ROUND, joint_type=LineJointType.ROUND)
F = lambda s: (max(1, round(s * FPS)) - .5) / FPS  # a run time of a whole number of frames (np.arange rounds an exact one UP now and then)
EXPO, CUBIC, BACK = rate_functions.ease_out_expo, rate_functions.ease_in_out_cubic, rate_functions.ease_out_back


TRACK = .08                                         # capitals are set open, as on a drawing's title block: this share of the type size between letters


def T(s, size, color=INK, weight=BOLD):
    return MarkupText(f'<span letter_spacing="{int(size / 4.8 * 1024 * TRACK)}">{escape(str(s))}</span>', font="Montserrat", weight=weight, font_size=size, color=color, warn_missing_font=False)


class Figures:
    """Numbers set from glyphs that are made once. A count needs a new label on every frame: a new Text for each is slow (seconds,
    on Windows) and its width jitters. Here every figure sits in a cell of one width (tabular), after `word`, on one baseline."""
    CH = "0123456789$.,%+-"

    def __init__(s, size, color=INK, weight=BOLD, word=""):
        t = T((word + " " if word else "") + s.CH, size, color, weight); k = len(word.replace(" ", "")); gap = lambda i: float(t[i + 1].get_left()[0] - t[i].get_right()[0])
        s.word = VGroup(*t[:k]); s.g = dict(zip(s.CH, t[k:])); s.cell = max(s.g[c].width for c in "0123456789")
        s.gap = sum(gap(k + i) for i in range(9)) / 9; s.space = gap(k - 1) if k else size / 72 * .35      # (as the type itself sets them: between two figures, after the word)

    def __call__(s, text):
        out = VGroup(*[m.copy() for m in s.word]); x = s.word.get_right()[0] + s.space if len(s.word) else 0.0
        for c in text:
            if c == " ": x += s.space; continue
            m = s.g[c].copy(); w = s.cell if c.isdigit() else m.width
            out.add(m.shift(RIGHT * (x + w / 2 - m.get_center()[0]))); x += w + s.gap
        return out


def paper(h, w):
    """The sheet under the drawing, as the camera's background (h x w pixels, RGBA): lit where the board is, dark at the corners.
    A flat navy field with thin lines on it reads as an empty frame, to the eye and to check.py (its 10th and 90th percentile of
    brightness must lie 30 apart on frame 0). Half a level of fixed grain keeps the slope from banding."""
    y, x = np.mgrid[0:h, 0:w]; r = np.clip(np.hypot((x / w - .5) / .75, (y / h - .47) / .62), 0, 1)[..., None]; k = r * r * (3 - 2 * r)
    rgb = (color_to_rgb(LIT) * (1 - k) + color_to_rgb(EDGE) * k) * 255 + np.random.default_rng(7).uniform(-.5, .5, (h, w, 1))
    return np.dstack([np.clip(np.rint(rgb), 0, 255), np.full((h, w), 255.0)])


def fit(m, w):                                      # whatever the props say, a word never leaves its place
    return m.scale_to_fit_width(w) if m.width > w else m


def poly(pts, color=INK, width=5.0):                # a chalk stroke through the points: thin, round ends, round corners
    return VMobject(stroke_color=color, stroke_width=width, **ROUND).set_points_as_corners([np.array(p, float) for p in pts])


def dashes(a, b, n, color=CYAN, width=2.5, opacity=1.0):   # n dashes: the same count at any length, so a level can be drawn dash by dash
    a, b = np.array(a, float), np.array(b, float)
    return VGroup(*[poly([a + (b - a) * (i / n), a + (b - a) * ((i + .55) / n)], color, width).set_stroke(opacity=opacity) for i in range(n)])


def head(tip, u, size, color, width):               # an open arrow head at tip, pointing along u
    return poly([tip - size * rotate_vector(u, .5), tip, tip - size * rotate_vector(u, -.5)], color, width)


def arrow(a, b, color=INK, width=4.5, size=.26):    # a chalk arrow: [the stroke, the head]
    a, b = np.array(a, float), np.array(b, float); u = (b - a) / max(np.linalg.norm(b - a), 1e-9)
    return VGroup(poly([a, b], color, width), head(b, u, size, color, width))


def dim(a, b, words, size=27, color=CYAN):
    """A dimension line as on a drawing (level, a to b): end ticks, the words in a gap in its middle. -> (linework, words)"""
    a, b = np.array(a, float), np.array(b, float); mid = (a + b) / 2
    t = fit(T(words, size, color, SEMIBOLD), max(abs(b[0] - a[0]) - .8, .4)).move_to(mid); gap = RIGHT * (t.width / 2 + .16)
    tick = lambda p: poly([p + UP * .13, p + DOWN * .13], color, 2.5)
    return VGroup(tick(a), poly([a, mid - gap], color, 2.5), poly([mid + gap, b], color, 2.5), tick(b)), t


class Teaser(Scene):
    def construct(self):
        self.camera.background = paper(self.camera.pixel_height, self.camera.pixel_width).astype(self.camera.pixel_array_dtype)
        with register_font(FONT_FILE): self.film(json.load(open(os.environ["STUDIO_PROPS"], encoding="utf-8")))

    def at(self, t):                                # wait for second t of the reel (things keep moving while it waits)
        k = round((t - self.renderer.time) * FPS)
        assert k >= -1, f"the beat at {t}s starts {-k} frames late"
        if k > 0: self.wait((k - .5) / FPS, frozen_frame=False)

    def film(self, R):
        H = [float(v) for v in R["history"]]; n = len(H); NEXT = int(R.get("next", 120)); now = lambda: self.renderer.time
        hi, lo, last = max(H), min(H), H[-1]; ih, il = H.index(hi), H.index(lo); span = max(hi - lo, 1e-9)
        k10 = max(0, n - 11); chg = (last / H[k10] - 1) * 100; rng = (hi - lo) / lo * 100; money = lambda v: f"${v:,.2f}"
        E = []; ev = lambda kind: E.append([round(now(), 2), kind])
        assert n >= 12, "the board needs at least twelve days of history"

        # ---- three framings of the same days: the whole board, the punch-in on the last days, the pull-back that shows what is not known
        XL, XR, YT, YB = -3.9, 2.85, 2.25, -3.75; yc = (YT + YB) / 2; s1 = (YT - YB) / span
        L1 = lambda d, p: np.array([XL + d / (n - 1) * (XR - XL), YB + (p - lo) * s1, 0.0])
        W = min(20, n - 1); wl, wh = min(H[-W - 1:]), max(H[-W - 1:]); PX, PW = .6, 5.1          # the last W days, from the frame's left edge to x = PX
        sP = min(max(s1, (YT - YB) / max(wh - wl, 1e-9)), s1 * (PW / W) / ((XR - XL) / (n - 1)))    # the price axis fits those days, and never zooms harder than the time axis
        P = lambda d, p: np.array([PX - (n - 1 - d) * PW / W, yc + (p - (wh + wl) / 2) * sP, 0.0])
        ZL, ZR, ZT, ZB = -4 + 8 * n / (n + NEXT), 4.0, 2.95, -1.45; zc = (ZT + ZB) / 2             # the unknown, to scale: NEXT days beside n
        L2 = lambda d, p: np.array([-4 + d / (n - 1) * (ZL + 4), zc + (p - last) * 2.0 / span, 0.0])  # the last price at mid height: the fan is even
        pts = lambda L, a=0, b=None: [L(j, H[j]) for j in range(a, n if b is None else b)]

        # ---- the sheet: the grid, the title strip, the hook cards
        grid = VGroup(*[Line([x, -11, 0], [x, 11, 0], stroke_color=GRID, stroke_width=1, stroke_opacity=.3 if i % 4 == 0 else .12) for i, x in enumerate(np.arange(-6, 6.01, .5))],
                      *[Line([-6, y, 0], [6, y, 0], stroke_color=GRID, stroke_width=1, stroke_opacity=.3 if i % 4 == 0 else .12) for i, y in enumerate(np.arange(-11, 11.01, .5))]).set_z_index(0)
        rule = lambda y: Line([-4, y, 0], [4, y, 0], stroke_color=CYAN, stroke_width=1.5, stroke_opacity=.7)
        strip = VGroup(rule(5.86), rule(5.36), T("MEME STREET", 27, CYAN, SEMIBOLD).move_to([-4, 5.61, 0], aligned_edge=LEFT),
                       T(f"DAILY #{R['number']}", 27, INK, SEMIBOLD).move_to([4, 5.61, 0], aligned_edge=RIGHT)).set_z_index(7)
        self.add(grid, strip)
        for t0, t1, lines in R["cards"]:
            g = VGroup(*[fit(T(s, size, PAL[c]), 7.8) for s, size, c in lines]).arrange(DOWN, buff=.26).move_to([0, 4.25, 0]).set_z_index(7)
            for i, m in enumerate(g):
                def upd(m, home=m.get_center().copy(), d=.08 * i, t0=t0, t1=t1):      # in from below (the first card is there on frame 0); out upward, faster, and gone before the next one arrives
                    a = 1.0 if t0 <= 0 else EXPO(float(np.clip((now() - t0 - d) / .45, 0, 1))); b = rate_functions.ease_in_cubic(float(np.clip((now() - t1 + .27) / .22, 0, 1)))
                    m.move_to(home + UP * (.35 * (a - 1) + .3 * b)).set_opacity(a * (1 - b))
                m.add_updater(upd); upd(m)
            self.add(g)

        def tally(figs, fmt, v0, place, slide, maxw=3.9, turn=0):
            """A number that counts as it arrives: -> (the label, its value, its arrival 0..1). place(m) puts it where it belongs."""
            v, a = ValueTracker(v0), ValueTracker(0)
            def make():
                m = fit(figs(fmt(v.get_value())), maxw)
                return place(m.rotate(turn) if turn else m).shift(slide * (a.get_value() - 1)).set_opacity(a.get_value()).set_z_index(7)
            m = always_redraw(make); self.add(m); return m, v, a

        # ---- 0.0  the line is already being drawn
        p = ValueTracker(.35 * (n - 1)); ps = ValueTracker(1)                    # (ps: the pen's size, smaller once the board is small)
        def trace():                                 # the days drawn so far
            v = p.get_value(); i = min(int(v), n - 1); q = pts(L1, 0, i + 1)
            if i < n - 1 and v > i: q.append(L1(v, H[i] + (H[i + 1] - H[i]) * (v - i)))
            return q
        def under(q):                                # the ground under them, down to the low: the chart has a body from frame 0
            foot = [np.array([q[-1][0], YB, 0.0]), np.array([q[0][0], YB, 0.0]), q[0]]
            return VMobject(stroke_width=0).set_points_as_corners(q + foot).set_fill([CYAN, CYAN], [.3, 0.0]).set_sheen_direction(DOWN).set_z_index(1)
        line = always_redraw(lambda: poly(trace(), INK, 5).set_z_index(3)); area = always_redraw(lambda: under(trace()))
        pen = VGroup(Circle(radius=.24, stroke_width=0, fill_color=GOLD, fill_opacity=.25), Dot(radius=.1, color=GOLD)).set_z_index(6)
        pen.add_updater(lambda m: m.move_to(line.get_end()))
        d1, d1t = dim([XL, -4.95, 0], [XR, -4.95, 0], f"{n} TRADING DAYS"); d1.set_z_index(2); d1t.set_z_index(7)
        self.add(area, line, pen); ev("riser")
        self.play(p.animate(run_time=F(2.2), rate_func=rate_functions.ease_out_sine).set_value(n - 1), Create(d1, lag_ratio=.3, run_time=F(1.0)), FadeIn(d1t, shift=UP * .15, run_time=F(.6)))
        line.clear_updaters(); pen.clear_updaters(); area.clear_updaters()

        def ride(a, b, rt):                          # the pen runs along the line from day a to day b
            if a != b: self.play(MoveAlongPath(pen, poly([L1(j, H[j]) for j in range(a, b + (1 if b > a else -1), 1 if b > a else -1)])), run_time=F(rt), rate_func=smooth)

        def level(i, word, up):                      # a ring on the day, a dashed level through it, its price counting in on the free side of the level
            pt = L1(i, H[i]); ring = Circle(radius=.13, stroke_color=CYAN, stroke_width=3).move_to(pt).set_z_index(5)
            dl = dashes([-3.95, pt[1], 0], [3.55, pt[1], 0], 30).set_z_index(2)
            place = lambda m: m.move_to([float(np.clip(pt[0], -3.95 + m.width / 2, 3.0 - m.width / 2)), pt[1] + (.4 if up else -.4), 0])
            lab, v, a = tally(Figures(30, INK, SEMIBOLD, word), money, last, place, UP * (.2 if up else -.2))
            ev("tick")
            self.play(GrowFromCenter(ring, run_time=F(.25), rate_func=BACK), Create(dl, lag_ratio=.15, run_time=F(.5)), a.animate(run_time=F(.35), rate_func=EXPO).set_value(1),
                      v.animate(run_time=F(.5), rate_func=rate_functions.ease_out_cubic).set_value(H[i]))
            lab.clear_updaters(); return [ring, dl, lab]

        self.at(2.2); ride(n - 1, ih, .6)
        self.at(2.8); marks = level(ih, "HIGH", True)
        self.at(3.3); ride(ih, il, .65)
        self.at(3.95); marks += level(il, "LOW", False)

        # ---- 4.5  the range: a band between the two levels, measured as on a drawing
        self.at(4.5); xd = 3.3
        band = Rectangle(width=7.5, height=YT - YB, stroke_width=0, fill_color=CYAN, fill_opacity=.07).move_to([-.2, yc, 0]).set_z_index(1)
        rd = VGroup(poly([[xd, YB + .05, 0], [xd, YT - .05, 0]], CYAN, 3), head(np.array([xd, YT - .05, 0]), UP, .16, CYAN, 3), head(np.array([xd, YB + .05, 0]), DOWN, .16, CYAN, 3)).set_z_index(2)
        rl, v, a = tally(Figures(27, CYAN, SEMIBOLD, "RANGE"), lambda x: f"{x:.1f}%", 0, lambda m: m.move_to([3.68, yc, 0]), UP * .25, YT - YB - .6, PI / 2)
        ev("pop")
        self.play(GrowFromEdge(band, DOWN, run_time=F(.5), rate_func=rate_functions.ease_out_cubic), Create(rd, lag_ratio=.4, run_time=F(.6)), a.animate(run_time=F(.4), rate_func=EXPO).set_value(1),
                  v.animate(run_time=F(.8), rate_func=rate_functions.ease_out_cubic).set_value(rng))
        rl.clear_updaters(); marks += [band, rd, rl, d1, d1t, area]

        # ---- 5.4  back to the last price, and the camera goes in on it
        self.at(5.4); ride(il, n - 1, .6)
        ping = always_redraw(lambda: Circle(radius=(.14 + .5 * ((now() * 1.25) % 1)) * ps.get_value(), stroke_color=GOLD, stroke_width=3, stroke_opacity=1 - (now() * 1.25) % 1).move_to(pen).set_z_index(6))
        pen.add_updater(lambda m: m.scale_to_fit_width(.48 * ps.get_value()).move_to(line.get_end())); self.add(ping)
        self.at(6.0); ev("swish")
        self.play(FadeOut(VGroup(*marks), run_time=F(.3)), Transform(line, poly(pts(P), INK, 5), run_time=F(.9), rate_func=CUBIC),
                  grid.animate(run_time=F(.9), rate_func=CUBIC).scale(1.14, about_point=L1(n - 1, last)))
        pl = P(n - 1, last); X = 1.3; ytag = float(np.clip(pl[1], YB + .3, YT - .3)); yb = ytag - 2.2 if ytag > yc else ytag + 2.2
        cap = lambda s, y: fit(T(s, 27, INK, SEMIBOLD), 2.65).move_to([X, y + .56, 0], aligned_edge=LEFT).set_z_index(7)
        big = Figures(52, GOLD); c1 = cap("LAST PRICE", ytag); tag, v, a = tally(big, money, H[k10], lambda m: m.move_to([X, ytag, 0], aligned_edge=LEFT), RIGHT * .3, 2.65)
        self.at(6.9); ev("pop")
        self.play(FadeIn(c1, shift=RIGHT * .2, run_time=F(.35), rate_func=EXPO), a.animate(run_time=F(.35), rate_func=EXPO).set_value(1), v.animate(run_time=F(.5), rate_func=rate_functions.ease_out_cubic).set_value(last))
        tag.clear_updaters()

        # ---- 7.6  the last ten days: lit on the line, then one arrow from where it was to where it is
        self.at(7.6); a10 = P(k10, H[k10]); u = (pl - a10) / max(np.linalg.norm(pl - a10), 1e-9)
        sub = poly(pts(P, k10), GOLD, 6).set_z_index(4); r10 = Circle(radius=.13, stroke_color=GOLD, stroke_width=3).move_to(a10).set_z_index(5)
        self.play(GrowFromCenter(r10, run_time=F(.25), rate_func=BACK), Create(sub, run_time=F(.5)))
        chord = arrow(a10 + u * .16, pl - u * .3, GOLD, 3.5, .22).set_z_index(5); ev("click")
        self.play(Create(chord, lag_ratio=.6, run_time=F(.4)))
        c2 = cap(f"LAST {n - 1 - k10} DAYS", yb); pct, v, a = tally(big, lambda x: f"{x:+.1f}%", 0, lambda m: m.move_to([X, yb, 0], aligned_edge=LEFT), RIGHT * .3, 2.65)
        self.at(8.5); ev("tick")
        self.play(FadeIn(c2, shift=RIGHT * .2, run_time=F(.35), rate_func=EXPO), a.animate(run_time=F(.35), rate_func=EXPO).set_value(1), v.animate(run_time=F(.8), rate_func=rate_functions.ease_out_cubic).set_value(chg))
        pct.clear_updaters()

        # ---- 9.7  the pull-back: the days we know shrink to their true share of the board
        self.at(9.7); ev("swish"); o = L2(n - 1, last)
        self.play(FadeOut(VGroup(c1, tag, c2, pct, r10, chord), run_time=F(.25)), Transform(line, poly(pts(L2), INK, 3.5), run_time=F(.9), rate_func=CUBIC), Transform(sub, poly(pts(L2, k10), GOLD, 3.5), run_time=F(.9), rate_func=CUBIC),
                  ps.animate(run_time=F(.9), rate_func=CUBIC).set_value(.7), grid.animate(run_time=F(.9), rate_func=CUBIC).scale(.8, about_point=o))

        # ---- 10.6  the fog: the days to come, hatched, and how little of the board the known days are
        f = ValueTracker(0)
        def fog():
            xr = ZL + (ZR - ZL) * max(f.get_value(), .002); ph = (now() * .25) % .34
            g = VGroup(Rectangle(width=xr - ZL, height=ZT - ZB, stroke_width=0, fill_color=CYAN, fill_opacity=.06).move_to([(ZL + xr) / 2, zc, 0]))
            for c in np.arange(ZB - xr + ph, ZT - ZL, .34):                  # the hatch: y = x + c, cut to the zone, marching slowly
                x0, x1 = max(ZL, ZB - c), min(xr, ZT - c)
                if x1 - x0 > .03: g.add(Line([x0, x0 + c, 0], [x1, x1 + c, 0], stroke_color=CYAN, stroke_width=1.5, stroke_opacity=.32))
            return g.set_z_index(1)
        haze = always_redraw(fog); today = dashes([ZL, ZB, 0], [ZL, ZT, 0], 16).set_z_index(2)
        yh, yl = L2(0, hi)[1], L2(0, lo)[1]; YD = ZB - .5                     # (YD: the row of the two dimension lines)
        lv = VGroup(dashes([-4, yh, 0], [4, yh, 0], 34, CYAN, 2, .6), dashes([-4, yl, 0], [4, yl, 0], 34, CYAN, 2, .6)).set_z_index(2)
        small = Figures(27, INK, SEMIBOLD); lt = VGroup(fit(small(money(hi)), 2.4).move_to([-4, yh + .32, 0], aligned_edge=LEFT), fit(small(money(lo)), 2.4).move_to([-4, yl - .32, 0], aligned_edge=LEFT)).set_z_index(7)
        da, dat = dim([-4, YD, 0], [ZL, YD, 0], f"{n} DAYS"); db, dbt = dim([ZL, YD, 0], [ZR, YD, 0], f"NEXT {NEXT} DAYS"); VGroup(da, db).set_z_index(2); VGroup(dat, dbt).set_z_index(7)
        self.at(10.6); self.add(haze); ev("whoosh")
        self.play(f.animate(run_time=F(.7), rate_func=rate_functions.ease_out_cubic).set_value(1), Create(today, lag_ratio=.2, run_time=F(.4)), Create(lv, lag_ratio=.1, run_time=F(.7)),
                  FadeIn(lt, run_time=F(.4)), Create(VGroup(da, db), lag_ratio=.3, run_time=F(.7)), FadeIn(VGroup(dat, dbt), shift=UP * .15, run_time=F(.6)))
        qm = T("?", 190, GOLD).move_to([(ZL + ZR) / 2, zc, 0]).set_z_index(7)
        self.at(11.3); ev("pop"); self.play(GrowFromCenter(qm, run_time=F(.4), rate_func=BACK))

        # ---- 12.1  the question takes the header: its mark flies up out of the fog
        C = R["choice"]; w = str(C["q"]).upper().split(); cut = (len(w) + 1) // 2 if len(w) > 2 else len(w)
        Q = VGroup(*[fit(T(s, 56, INK), 7.8) for s in (" ".join(w[:cut]), " ".join(w[cut:])) if s]).arrange(DOWN, buff=.28).move_to([0, 4.25, 0]).set_z_index(7)
        end = Q[-1][-1] if str(C["q"]).strip().endswith("?") else None
        if end is not None: end.set_color(GOLD)
        self.at(12.1); ev("ding")
        self.play(FadeIn(VGroup(*[g for m in Q for g in m if g is not end]), shift=UP * .3, run_time=F(.45), rate_func=EXPO),
                  ReplacementTransform(qm, end, run_time=F(.6), rate_func=CUBIC) if end is not None else FadeOut(qm, run_time=F(.3)))

        # ---- 12.8  three arrows fan out of the last price (up, level, down), each with its answer
        fan = []; opts = [k for k in "abc" if C.get(k)]; late = lambda t: BACK(float(np.clip(t * 2 - 1, 0, 1)))        # (the badge lands as its arrow arrives)
        for i, (k, ty) in enumerate(zip(opts, (zc + 1.7, zc, zc - 1.7) if len(opts) > 2 else (zc + 1.7, zc - 1.7))):
            tip = np.array([3.31, ty, 0]); uu = (tip - o) / np.linalg.norm(tip - o); ar = arrow(o + uu * .28, tip, INK, 5, .26).set_z_index(5)
            bd = VGroup(Circle(radius=.27, stroke_color=GOLD, stroke_width=3, fill_color=NAVY, fill_opacity=1), T(k.upper(), 27, INK)).move_to([3.68, ty, 0]).set_z_index(7)
            y = YD - .65 - .6 * i; b = VGroup(Circle(radius=.24, stroke_color=GOLD, stroke_width=3), T(k.upper(), 27, GOLD)).move_to([-3.72, y, 0])
            row = VGroup(b, fit(T(str(C[k]).upper(), 30, INK, SEMIBOLD), 7.0).move_to([-3.28, y, 0], aligned_edge=LEFT)).set_z_index(7)
            self.at(12.8 + .4 * i); ev("swish"); E.append([round(now() + .2, 2), "pop"])
            self.play(GrowFromPoint(ar, o, run_time=F(.4), rate_func=rate_functions.ease_out_cubic), GrowFromCenter(bd, run_time=F(.4), rate_func=late), FadeIn(row, shift=RIGHT * .3, run_time=F(.4), rate_func=late))
            fan.append((ar, bd, b))

        # ---- 14.3  the promise and the address
        for i, (s, c) in enumerate(R["foot"]):
            m = fit(T(s, 30, PAL[c], SEMIBOLD), 7.6).move_to([0, YD - 2.55 - .55 * i, 0]).set_z_index(7)
            self.at(14.3 + .4 * i); ev("tick"); self.play(FadeIn(m, shift=UP * .2, run_time=F(.35), rate_func=EXPO))

        # ---- 15.6  the hold: each answer lights in turn (the dot still pulses, the fog still marches)
        for i, (ar, bd, b) in enumerate(fan):
            self.at(15.6 + .85 * i)
            self.play(ar.animate(run_time=F(.8), rate_func=there_and_back).set_color(GOLD), bd.animate(run_time=F(.8), rate_func=there_and_back).scale(1.2), b.animate(run_time=F(.8), rate_func=there_and_back).scale(1.25))
        self.at(float(R["T"])); print("events " + json.dumps(E), flush=True)
