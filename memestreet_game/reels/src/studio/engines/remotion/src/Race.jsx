// The 16:00 reel "the race": $1,000 on each of seven of the game's revealed stocks, as a bar chart race. Its look is Swiss
// data design: paper, one ink, one sans-serif, one signal colour a stock, a strict grid. ALL of its data comes in as props
// (reels/race-1600/reel.json, written by that folder's make_reel.mjs); the arithmetic is raceMath.mjs.
import React, {useMemo} from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring, Easing, staticFile, delayRender, continueRender} from 'remotion';
import {build, money} from './raceMath.mjs';

if (typeof document !== 'undefined') {            // one variable font file (weights 100 to 900), waited for before any frame is drawn
  const wait = delayRender('Montserrat'), face = new FontFace('Montserrat', `url(${staticFile('Montserrat.ttf')})`, {weight: '100 900'});
  face.load().then(() => { document.fonts.add(face); continueRender(wait); });
}

// The grid (px). Everything sits inside x 104-976, y 290-1510, so that the 110 percent punch-in about (ZX, ZY), the
// leader's row, still keeps every word inside the safe zone (x 60-1020, y 250-1600).
const X0 = 104, X1 = 976, W = X1 - X0, CX = 160, BW = X1 - CX, Y0 = 614, PITCH = 110, BAR_Y = 54, BAR_H = 40, ZX = 540, ZY = 660, CAP_Y = 364, TR_H = 128;
const OUT = Easing.out(Easing.exp), IN = Easing.in(Easing.cubic), INOUT = Easing.inOut(Easing.quad), LIN = x => x;
const ramp = (t, a, b, easing = OUT) => interpolate(t, [a, b], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing});
const txt = (size, weight, more) => ({fontSize: size, fontWeight: weight, lineHeight: 1, whiteSpace: 'nowrap', ...more});
const Crown = ({k, color}) => <svg width="42" height="30" viewBox="0 0 42 30" style={{alignSelf: 'center', transform: `scale(${k})`, flex: 'none'}}>
  <path d="M2 28V7l10 10L21 2l9 15L40 7v21z" fill={color} /></svg>;

export const Race = P => {
  const f = useCurrentFrame(), {fps} = useVideoConfig(), t = f / fps, S = P.series, {paper, ink, grey, track} = P;
  const R = useMemo(() => build(P, fps), [P.series, P.keys, P.T, P.stake, fps]);
  const q = R.F[Math.min(f, R.F.length - 1)], first = R.F[0], end = R.F[R.F.length - 1], pk = R.peak, win = end.lead, second = end.rank.indexOf(1), fin = P.finish, tc = P.card.t;
  const zoom = 1 + .1 * P.zooms.reduce((a, [z0, z1]) => a + ramp(t, z0, z0 + .35, INOUT) - ramp(t, z1, z1 + .35, INOUT), 0);
  const cap = P.captions.find(c => t >= c[0] && t < c[1]), gone = ramp(t, tc, tc + .2, IN), bx = v => v / q.axis * BW;
  const pop = (at, cfg) => spring({frame: f - Math.round(at * fps), fps, config: cfg || {damping: 11, stiffness: 190}});

  const caption = cap && (() => {                 // one caption at a time in its own band: a small line, a big line, sometimes a tag
    const [a, b, small, big, size, ci, tag] = cap, e = a < 0 ? 1 : ramp(t, a, a + .3), e2 = a < 0 ? 1 : ramp(t, a + .07, a + .4), col = ci == null ? ink : S[ci].color;
    return <div style={{position: 'absolute', left: X0, top: CAP_Y, width: W, height: 200, opacity: 1 - ramp(t, b - .14, b, IN)}}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: 52, opacity: e, transform: `translateY(${(1 - e) * 20}px)`}}>
        <span style={txt(42, 700, {letterSpacing: '.04em'})}>{small}</span>
        {tag ? <span style={txt(34, 800, {background: col, color: paper, padding: '9px 16px', transformOrigin: '100% 50%', transform: `scale(${pop(a + .45)})`})}>{tag}</span> : null}
      </div>
      <div style={{position: 'absolute', left: 0, bottom: 0, opacity: e2, transform: `translateY(${(1 - e2) * 44}px)`, ...txt(size, 900, {color: col, letterSpacing: '-.02em'})}}>{big.replace('{fall}', Math.round((1 - q.v[pk.i] / pk.v) * 100))}</div>
    </div>;
  })();

  const rows = S.map((s, i) => {                  // a row is an opaque card: in an overtake the one going up slides over the one going down
    const k0 = first.rank[i], v = q.v[i] * ramp(t, -.35 + .05 * k0, .65 + .05 * k0, Easing.out(Easing.cubic)), dim = q.rank[i] > 1 ? 1 - .65 * ramp(t, fin + .9, fin + 1.3, INOUT) : 1;
    const passed = 1 - Math.max(0, ...S.map((_, j) => q.vel[j] < q.vel[i] ? ramp(1 - Math.abs(q.pos[i] - q.pos[j]), .05, .18, LIN) : 0));   // a row's words fade out for as long as a row going up faster is over it: never half-covered words
    const mark = (val, color) => bx(val) <= BW + 2 ? <div style={{position: 'absolute', left: bx(val) - 2, top: -4, width: 4, height: BAR_H + 8, background: color}} /> : null;
    return <div key={s.ticker} style={{position: 'absolute', left: CX, top: 0, width: BW, height: PITCH, background: paper, transform: `translateY(${Y0 + q.pos[i] * PITCH}px)`, zIndex: 1000 - Math.round(q.vel[i] * 100)}}>
      <div style={{opacity: dim}}>
        <div style={{position: 'absolute', left: 0, top: 4, width: BW, display: 'flex', alignItems: 'baseline', gap: 14, opacity: passed}}>
          <span style={txt(38, 800)}>{s.name.toUpperCase()}</span>
          <span style={txt(28, 500, {color: grey})}>{s.years}</span>
          {q.lead === i ? <Crown k={spring({frame: f - q.since, fps, config: {damping: 10, stiffness: 200}})} color={ink} /> : null}
          {i === win && t >= fin + .45 ? <span style={txt(26, 800, {background: ink, color: paper, padding: '6px 12px', alignSelf: 'center', transform: `scale(${pop(fin + .45)})`})}>WINNER</span> : null}
          {i === pk.i && t >= fin + 1.3 ? <span style={txt(28, 800, {color: s.color, opacity: ramp(t, fin + 1.3, fin + 1.6)})}>PEAK {money(pk.v)}</span> : null}
          <span style={txt(46, 800, {marginLeft: 'auto'})}>{money(v)}</span>
        </div>
        <div style={{position: 'absolute', left: 0, top: BAR_Y, width: BW, height: BAR_H, background: track}}>
          <div style={{position: 'absolute', left: 0, top: 0, width: Math.min(BW, bx(v)), height: BAR_H, background: s.color}} />
          {P.ticks.filter(x => x <= q.axis).map(x => x === P.stake                                   /* the stake's line in ink, the round thousands as notches */
            ? <div key={x} style={{position: 'absolute', left: Math.min(BW - 3, bx(x) - 1.5), top: -4, width: 3, height: BAR_H + 8, background: ink}} />
            : <div key={x} style={{position: 'absolute', left: bx(x) - 1, top: 0, width: 2, height: BAR_H, background: paper}} />)}
          {i === pk.i && f > pk.f && bx(pk.v - v) > 8 ? mark(pk.v, s.color) : null}                                        {/* the high-water mark it leaves behind */}
          {i === second && t >= fin + .7 ? <div style={{opacity: ramp(t, fin + .7, fin + .9)}}>{mark(end.v[win], S[win].color)}</div> : null}   {/* the winner's line on the runner-up's bar */}
        </div>
      </div>
    </div>;
  });

  const race = <div style={{opacity: 1 - gone, transform: `translateY(${-24 * gone}px)`}}>
    {caption}
    <div style={{position: 'absolute', left: X0, top: 576, width: W, height: 3, background: ink}} />
    {P.ticks.map((x, k) => {                      // the scale: a label only where it has room
      const px = CX + bx(x), o = ramp(q.axis / x, .98, 1, LIN) * (k ? ramp(bx(x) - bx(P.ticks[k - 1]), 100, 130, LIN) : 1);
      return <div key={x} style={{position: 'absolute', left: px - 200, top: 585, width: 200, textAlign: 'right', opacity: o, ...txt(24, 600, {color: grey})}}>{money(x)}</div>;
    })}
    {S.map((_, k) => {                            // the places, fixed: rows move between them
      const w = k ? 0 : ramp(t, fin + .45, fin + .7);
      return <div key={k} style={{position: 'absolute', left: X0, top: Y0 + k * PITCH + 2, width: 42, height: 42, display: 'flex', alignItems: 'center', justifyContent: 'center', background: w > .5 ? ink : 'none', transform: `scale(${1 + .25 * Math.sin(Math.PI * w)})`, ...txt(32, w > .5 ? 800 : 500, {color: w > .5 ? paper : grey})}}>{k + 1}</div>;
    })}
    {rows}
    <div style={{position: 'absolute', left: X0, top: Y0 + S.length * PITCH + 6, width: W, height: 3, background: track}} />
    <div style={{position: 'absolute', left: X0, top: Y0 + S.length * PITCH + 4, width: W * q.d / R.last, height: 7, background: ink}} />
    <div style={{position: 'absolute', left: X0, top: 1410, display: 'flex', alignItems: 'baseline', gap: 12}}>
      <span style={txt(30, 700, {color: grey})}>DAY</span><span style={txt(86, 900, {letterSpacing: '-.02em'})}>{Math.ceil(q.d - 1e-6)}</span><span style={txt(30, 700, {color: grey})}>OF {R.last}</span>
    </div>
    <div style={{position: 'absolute', right: 1080 - X1, top: 1404, textAlign: 'right', ...txt(29, 600, {lineHeight: '35px'})}}>{P.note.map(l => <div key={l}>{l}</div>)}</div>
  </div>;

  const card = t >= tc && (() => {                // the choice: the rocket's own line up to its peak, the question, three answers
    const s = S[pk.i], pd = Math.round(pk.d), CH = 330, CW = W - 260, x = d => d / pd * CW, y = v => CH - 10 - v / pk.v * (CH - 40), val = d => P.stake * s.chart[d] / s.chart[0];
    const rise = (at, d = 36) => { const e = ramp(t, tc + at, tc + at + .4); return {opacity: e, transform: `translateY(${(1 - e) * d}px)`}; };
    const draw = ramp(t, tc + .15, tc + .95, Easing.out(Easing.cubic)), lit = t < tc + 1.7 ? -1 : Math.floor((t - tc - 1.7) / .5) % 3, A = ['a', 'b', 'c'].filter(k => P.choice[k]);
    return <div>
      <div style={{position: 'absolute', left: X0, top: CAP_Y + 4, ...txt(42, 700, {letterSpacing: '.04em'}), ...rise(.1, 20)}}>{P.card.lines[0]}</div>
      <div style={{position: 'absolute', left: X0, top: 436, width: W, height: CH, opacity: ramp(t, tc + .1, tc + .25)}}>
        <div style={{position: 'absolute', left: 0, top: y(P.stake), width: CW, height: 2, background: track}} />
        <div style={{position: 'absolute', left: 0, top: y(P.stake) + 12, ...txt(26, 600, {color: grey})}}>{money(P.stake)}</div>
        <div style={{position: 'absolute', left: 0, top: 0, width: draw * (CW + 6), height: CH, overflow: 'hidden'}}>
          <svg width={W} height={CH}><path d={'M' + [...Array(pd + 1).keys()].map(d => `${x(d).toFixed(1)} ${y(val(d)).toFixed(1)}`).join('L')} fill="none" stroke={s.color} strokeWidth="8" strokeLinejoin="round" strokeLinecap="round" /></svg>
        </div>
        <div style={{position: 'absolute', left: CW - 13, top: y(pk.v) - 13, width: 26, height: 26, borderRadius: 13, background: ink, transform: `scale(${pop(tc + .95)})`}} />
        <div style={{position: 'absolute', left: CW + 26, top: y(pk.v) - 26, ...txt(52, 900, {color: s.color, letterSpacing: '-.02em'}), ...rise(.95, 0)}}>{money(pk.v)}</div>
      </div>
      <div style={{position: 'absolute', left: X0, top: 800, ...txt(54, 800), ...rise(.3)}}>{P.card.lines[1]}</div>
      <div style={{position: 'absolute', left: X0, top: 870, ...txt(80, 900, {letterSpacing: '-.02em'}), ...rise(.42)}}>{P.card.lines[2]}</div>
      {A.map((k, j) => <div key={k} style={{position: 'absolute', left: X0, top: 990 + j * 118, width: W, height: 118, ...rise(.6 + .15 * j)}}>
        <div style={{position: 'absolute', left: 0, top: 0, width: W, height: 2, background: j ? track : ink}} />
        <div style={{position: 'absolute', left: 0, top: 16, width: 88, height: 88, display: 'flex', alignItems: 'center', justifyContent: 'center', background: lit === j ? s.color : ink, ...txt(58, 900, {color: paper})}}>{k.toUpperCase()}</div>
        <div style={{position: 'absolute', left: 116, top: 30, ...txt(60, 800)}}>{String(P.choice[k]).toUpperCase()}</div>
      </div>)}
      <div style={{position: 'absolute', left: X0, top: 990 + A.length * 118, width: W, height: 3, background: ink, opacity: ramp(t, tc + 1.2, tc + 1.4)}} />
      <div style={{position: 'absolute', left: X0, top: 1010 + A.length * 118, width: W, display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', ...rise(1.2, 20)}}>
        <span style={txt(44, 800)}>{P.card.foot}</span><span style={txt(30, 600, {color: grey})}>{P.card.site}</span>
      </div>
    </div>;
  })();

  return <AbsoluteFill style={{background: paper, color: ink, fontFamily: 'Montserrat', fontVariantNumeric: 'tabular-nums', overflow: 'hidden'}}>
    <AbsoluteFill style={{transform: `scale(${zoom})`, transformOrigin: `${ZX}px ${ZY}px`}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height: 340, background: ink}} />
      <div style={{position: 'absolute', left: X0, top: 290, width: W, display: 'flex', justifyContent: 'space-between', color: paper}}>
        <span style={txt(34, 800, {letterSpacing: '.03em'})}>{P.kicker[0]}</span><span style={txt(34, 500, {letterSpacing: '.03em'})}>{P.kicker[1]}</span>
      </div>
      <svg width={W} height={TR_H + 4} style={{position: 'absolute', left: X0, top: 262 - TR_H, overflow: 'visible'}}>
        {q.d > 0 && S.map((s, i) => <polyline key={s.ticker} fill="none" stroke={s.color} strokeWidth="4" strokeLinejoin="round" strokeLinecap="round" points={[...Array(Math.floor(q.d) + 1).keys()]
          .map(d => [d, P.stake * s.chart[d] / s.chart[0]]).concat([[q.d, q.v[i]]]).map(([d, v]) => `${(d / R.last * W).toFixed(1)},${(TR_H - v / pk.v * TR_H).toFixed(1)}`).join(' ')} />)}
      </svg>
      {race}
      {card}
    </AbsoluteFill>
  </AbsoluteFill>;
};
