// DEVICE: pure chart (the hook stands alone before it: one huge candle and the seller it fooled). The chart scenes draw the candles, the line and the shade; this function adds the one glowing candle,
// the buyers' stops sitting under support (and popping when the sweep hits them), a sellers/buyers tug bar as the HUD,
// and a camera push onto the candle that matters. Palette: the house teal/red on near-black (tok.css left empty).
({t, T, s, i, R, api}) => {
  const {seg, cl, out, back, esc, punch, chart, at, boomFx, G, RD, AM} = api;
  const C = chart();                                   // the chart's pixel transform (null when no chart is drawn)
  let g = '';
  // HUD (y 380..500, in place of a title): who is winning the last six candles
  if (C) {
    const k = Math.min(C.n - 1, Math.floor(C.r)); let up = 0, dn = 0;
    for (let q = Math.max(0, k - 5); q <= k; q++) { const d = C.C[q][3] - C.C[q][0]; if (d >= 0) up += d; else dn -= d; }
    const b = up + dn ? up / (up + dn) : .5, x0 = 90, w = 900, bx = x0 + w * (1 - b);
    g += `<text x="${x0}" y="418" font-size="28" font-weight="800" fill="${RD}">SELLERS</text><text x="${x0 + w}" y="418" text-anchor="end" font-size="28" font-weight="800" fill="${G}">BUYERS</text>`;
    g += `<rect x="${x0}" y="440" width="${w}" height="16" rx="8" fill="${RD}"/><rect x="${bx.toFixed(1)}" y="440" width="${(x0 + w - bx).toFixed(1)}" height="16" rx="8" fill="${G}"/><rect x="${(bx - 5).toFixed(1)}" y="432" width="10" height="32" rx="4" fill="#fff"/>`;
  }
  // the stops under support: little red SL pills, in from scene 1 ('every buyer'), popped one by one in scene 2 ('stops were hit')
  const S1 = R.scenes[1], S2 = R.scenes[2];
  if (C && i >= 1 && i <= 2) {
    const tIn = at(S1, 'every buyer'), tPop = i === 2 ? at(S2, 'stops were hit') : 1e9, y = C.Y(100) + 34;
    for (let q = 0; q < 7; q++) {
      const x = C.X(12 + q * 4), a = back(seg(t, tIn + q * .08, tIn + q * .08 + .35)), p = seg(t, tPop + q * .07, tPop + q * .07 + .4);
      if (a <= 0) continue;
      if (p >= 1) continue;
      if (p > 0) g += boomFx(x, y, p, 60, RD);
      g += `<g transform="translate(${x.toFixed(1)} ${y}) scale(${(a * (1 - p)).toFixed(3)})" opacity="${(1 - p).toFixed(2)}"><rect x="-26" y="-18" width="52" height="36" rx="10" fill="${RD}"/><text y="9" text-anchor="middle" font-size="26" font-weight="800" fill="#07121a">SL</text></g>`;
    }
  }
  // the hook (scene 0, before any chart): the candle that lied, alone and huge. It dumps while the seller points at it,
  // the seller panics and sells on "sold", and on "Watch" the same candle climbs back over its open and closes green
  if (i === 0) {
    const tS = at(s, "sold"), tW = at(s, "Watch"), d = out(seg(t, s.t0, s.t0 + 1.5)), up = out(seg(t, tW, tW + .7)), pul = .6 + .4 * Math.sin(t * 6);
    const x = 680, yo = 720, yc = yo + 300 * d - 440 * up, lo = yo + 300 * d + 60, hi = Math.min(yo - 50, yc - 30), col = yc > yo ? RD : G;   // open, close, low, high (the close falls, then climbs)
    g += `<path d="M120 1210H960" stroke="#2a2f35" stroke-width="4" stroke-linecap="round"/>`;
    g += `<rect x="${x - 110}" y="${(hi - 26).toFixed(1)}" width="220" height="${(lo - hi + 52).toFixed(1)}" rx="18" fill="${AM}" opacity="${(.16 * pul).toFixed(3)}"/><rect x="${x - 110}" y="${(hi - 26).toFixed(1)}" width="220" height="${(lo - hi + 52).toFixed(1)}" rx="18" fill="none" stroke="${AM}" stroke-width="4" opacity="${pul.toFixed(3)}"/>`;
    g += `<path d="M${x} ${hi.toFixed(1)}V${lo.toFixed(1)}" stroke="${col}" stroke-width="12" stroke-linecap="round"/><rect x="${x - 75}" y="${Math.min(yo, yc).toFixed(1)}" width="150" height="${Math.max(8, Math.abs(yc - yo)).toFixed(1)}" rx="8" fill="${col}"/>`;
    g += api.fig({pose: t < tS ? "point" : t < tW + .4 ? "panic" : "sad", x: 300, y: 1210, sc: 2}, t);
    const a = back(seg(t, tS, tS + .35)) * (1 - seg(t, tW + .2, tW + .5));
    if (a > 0) g += `<g transform="translate(300 640) scale(${a.toFixed(3)})"><rect x="-92" y="-40" width="184" height="80" rx="16" fill="${RD}"/><text y="16" text-anchor="middle" font-size="46" font-weight="800" fill="#07121a">SOLD</text></g>`;
  }
  // the glowing candle and the camera push, on the scene's 'glow' cue (cue {do:"fx", name:"glow", i: candle})
  const cue = (s.cues || []).find(c => c.do === 'fx' && c.name === 'glow');
  if (C && cue && cue.i != null && C.r >= cue.i) {
    const x = C.X(cue.i), yh = C.Y(C.C[cue.i][1]), yl = C.Y(C.C[cue.i][2]), a = cl(seg(t, cue.t, cue.t + .6)) * (1 - seg(t, s.t1 - .5, s.t1 - .1)), pul = .6 + .4 * Math.sin((t - cue.t) * 6);
    g += `<rect x="${(x - C.bw).toFixed(1)}" y="${yh - 26}" width="${(2 * C.bw).toFixed(1)}" height="${yl - yh + 52}" rx="14" fill="${AM}" opacity="${(.22 * a * pul).toFixed(3)}"/>`;
    g += `<rect x="${(x - C.bw).toFixed(1)}" y="${yh - 26}" width="${(2 * C.bw).toFixed(1)}" height="${yl - yh + 52}" rx="14" fill="none" stroke="${AM}" stroke-width="4" opacity="${(a * pul).toFixed(3)}"/>`;
    api.cam = {k: 1 + .22 * out(a), ox: x, oy: (yh + yl) / 2};   // the chart leans in on the candle; the HUD stays put
  }
  return `<svg style="position:absolute;left:0;top:0" width="1080" height="1920">${g}</svg>` + punch(s, t);
}
