// The race's arithmetic, with no React in it. Race.jsx draws from build(); reels/race-1600/make_reel.mjs runs the same
// code under node to check the figures and to list the moments that are heard. Every frame is a pure function of
// (props, frame number): the springs are simulated once from frame 0, the same way on every worker.
export const money = v => '$' + String(Math.round(v)).replace(/\B(?=(\d{3})+(?!\d))/g, ',');

export function pchip(K) {             // [[x, y], ...] -> f(x): a monotone cubic (smooth speed, dead still where two keys share a y)
  const n = K.length, h = [], d = [], m = new Array(n).fill(0);
  for (let i = 0; i < n - 1; i++) { h[i] = K[i + 1][0] - K[i][0]; d[i] = (K[i + 1][1] - K[i][1]) / h[i]; }
  for (let i = 1; i < n - 1; i++) if (d[i - 1] * d[i] > 0) { const a = 2 * h[i] + h[i - 1], b = h[i] + 2 * h[i - 1]; m[i] = (a + b) / (a / d[i - 1] + b / d[i]); }
  m[0] = d[0]; m[n - 1] = d[n - 2];    // (the ends keep their speed: the race starts at once and stops dead on the line)
  return x => {
    if (x <= K[0][0]) return K[0][1];
    if (x >= K[n - 1][0]) return K[n - 1][1];
    let i = 0; while (x > K[i + 1][0]) i++;
    const s = (x - K[i][0]) / h[i], s2 = s * s, s3 = s2 * s;
    return (2 * s3 - 3 * s2 + 1) * K[i][1] + (s3 - 2 * s2 + s) * h[i] * m[i] + (3 * s2 - 2 * s3) * K[i + 1][1] + (s3 - s2) * h[i] * m[i + 1];
  };
}

// How the picture moves (seconds). The axis looks AHEAD, so every bar pulls back before a jump and the jump is seen as a
// bar shooting out; it HOLDs a record, so a fall is seen as a bar falling; then it closes in again at TAU.
const AHEAD = .5, HOLD = 1.6, TAU = 1, BOX = .25, STIFF = 320, DAMP = 26;
const SOFT = [1, 2, 3, 4, 3, 2, 1];    // a value shown is the mean of +-0.1 s of screen time: exact wherever the days pass slowly, calm where 15 pass in a second
const LAG = [0, -2, -3, -5, -6];       // a rank is taken on the last 0.2 s,
const CLEAR = .008;                    // and a row passes another only once it is clear of it by this share of the stake: the bar passes first, visibly, then the row follows; two bars a few dollars apart do not flutter

export function build(P, fps = 30) {
  const S = P.series, n = S.length, N = Math.round(P.T * fps) + 1, last = S[0].chart.length - 1, day = pchip(P.keys), D = f => day(f / fps);
  const raw = (i, d) => { const c = S[i].chart, k = Math.min(last - 1, Math.floor(d)); return P.stake * (c[k] + (c[k + 1] - c[k]) * (d - k)) / c[0]; };
  const memo = new Map(), vals = f => { if (!memo.has(f)) memo.set(f, S.map((_, i) => SOFT.reduce((a, w, k) => a + w * raw(i, D(f + k - 3)), 0) / 16)); return memo.get(f); };

  const top = []; for (let f = 0; f < N + Math.ceil((AHEAD + BOX) * fps) + 1; f++) top.push(Math.max(...vals(f)));
  const env = top.map((_, f) => {      // the highest value from the start to a little ahead, an old record fading after HOLD
    const to = Math.min(top.length - 1, f + Math.round(Math.min(AHEAD, f / fps / 2) * fps)); let m = 0;
    for (let g = 0; g <= to; g++) { const dt = (f - g) / fps; m = Math.max(m, top[g] * (dt <= HOLD ? 1 : Math.exp(-(dt - HOLD) / TAU))); }
    return m;
  });
  const b = Math.round(BOX * fps), axis = f => { let a = 0; for (let j = -b; j <= b; j++) a += env[Math.min(env.length - 1, Math.max(0, f + j))]; return Math.max(top[f], a / (2 * b + 1)); };

  const F = [], vel = S.map(() => 0), heard = [], o = S.map((_, i) => i), gap = P.stake * CLEAR * LAG.length; let pos, lead = -1, since = 0, prev, peak = {v: 0};
  for (let f = 0; f < N; f++) {
    const v = vals(f), m = S.map((_, i) => LAG.reduce((a, k) => a + vals(f + k)[i], 0)), r = [];
    for (let again = true; again;) { again = false; for (let k = 0; k < n - 1; k++) if (m[o[k + 1]] - m[o[k]] > gap) { [o[k], o[k + 1]] = [o[k + 1], o[k]]; again = true; } }
    o.forEach((i, k) => { r[i] = k; }); pos = pos || r.slice();
    for (let s = 0; s < 4; s++) for (let i = 0; i < n; i++) { vel[i] += (-STIFF * (pos[i] - r[i]) - DAMP * vel[i]) / (fps * 4); pos[i] += vel[i] / (fps * 4); }
    const now = Math.max(...m) - Math.min(...m) > gap ? o[0] : -1;     // nobody leads while all are level
    if (now !== lead) { lead = now; since = f; heard.push([f / fps, 'lead']); }
    else if (prev && r.some((x, i) => x !== prev[i])) heard.push([f / fps, 'pass']);
    const hi = v.indexOf(Math.max(...v)); if (v[hi] > peak.v) peak = {i: hi, v: v[hi], d: D(f), f};
    F.push({d: D(f), v, rank: r, pos: pos.slice(), vel: vel.slice(), axis: axis(f), lead, since}); prev = r;
  }
  return {F, peak, heard, last};     // peak: {i: the series, v: its dollars, d: the day, f: the frame}; heard: [seconds, 'lead' | 'pass'] for the sound step
}
