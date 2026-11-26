// Higher or Lower: a game-show quiz on a real chart (one whose name is already public). Each round the line stops, the viewer has
// 3 seconds to guess, then the line runs on and the answer lands. window.__R = {T, prices, rounds: [{t, a, b}], intro, outro: {t, name, lines}, cover}
const R = window.__R, c = document.getElementById('c').getContext('2d'), W = 1080, H = 1920, F = 'Montserrat, sans-serif';
const cl = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x)), ease = x => 1 - Math.pow(1 - cl(x), 3), back = x => { x = cl(x); const k = 1.7; return 1 + (k + 1) * Math.pow(x - 1, 3) + k * Math.pow(x - 1, 2); };
const P = R.prices, n = P.length - 1, lo = Math.min(...P), hi = Math.max(...P);
const CX = 70, CY = 560, CW = 940, CH = 640, X = i => CX + 30 + i / n * (CW - 60), Y = v => CY + CH - 50 - (v - lo) / (hi - lo + 1e-9) * (CH - 120);
function big(s, x, y, size, fill, rot = 0, stroke = '#000') { c.save(); c.translate(x, y); c.rotate(rot); c.font = `900 ${size}px ${F}`; c.textAlign = 'center'; c.textBaseline = 'middle'; c.lineJoin = 'round';
  c.lineWidth = size * .2; c.strokeStyle = stroke; c.strokeText(s, 0, 0); c.fillStyle = fill; c.fillText(s, 0, 0); c.restore(); }
function rr(x, y, w, h, r) { c.beginPath(); c.roundRect(x, y, w, h, r); }
function state(t) {          // how far the line has run, the round we are in and its phase
  let upto = R.rounds[0].a, cur = null, ph = 'intro', d = 0;
  for (const r of R.rounds) { if (t < r.t) break; cur = r; d = t - r.t;
    if (d < .6) { ph = 'show'; upto = r.a; } else if (d < 3.6) { ph = 'guess'; upto = r.a; } else if (d < 4.7) { ph = 'run'; upto = r.a + (r.b - r.a) * ease((d - 3.6) / 1.1); } else { ph = 'result'; upto = r.b; } }
  if (!cur) upto = R.rounds[0].a * ease(t / 1.4);
  return {upto, cur, ph, d};
}
function frame(t) {
  // a game-show stage: a rich gradient and turning light rays
  const g = c.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#2a0b5e'); g.addColorStop(1, '#0b1a4a'); c.fillStyle = g; c.fillRect(0, 0, W, H);
  c.save(); c.translate(540, 880); c.rotate(t * .15); for (let i = 0; i < 16; i++) { c.rotate(Math.PI / 8); c.fillStyle = i % 2 ? 'rgba(255,255,255,.035)' : 'rgba(255,210,63,.04)'; c.beginPath(); c.moveTo(0, 0); c.lineTo(-180, -1400); c.lineTo(180, -1400); c.fill(); } c.restore();
  const S = state(t), ri = S.cur ? R.rounds.indexOf(S.cur) : -1;
  // the title and the score
  big('HIGHER', 400, 205, 130, '#2bd47d', -.04); big('OR', 760, 205, 80, '#fff', -.04); big('LOWER?', 600, 335, 130, '#ff4d5e', -.04);
  c.font = `800 40px ${F}`; c.textAlign = 'center'; c.fillStyle = '#ffd23f'; c.fillText('REAL STOCK · NAME HIDDEN · ROUND ' + Math.max(1, ri + 1) + ' OF ' + R.rounds.length, 540, 470);
  // the chart card
  rr(CX, CY, CW, CH, 36); c.fillStyle = '#0b0d14'; c.fill(); c.lineWidth = 6; c.strokeStyle = '#ffd23f'; c.stroke();
  c.save(); rr(CX, CY, CW, CH, 36); c.clip(); c.strokeStyle = 'rgba(255,255,255,.06)'; c.lineWidth = 2; for (let k = 1; k < 5; k++) { c.beginPath(); c.moveTo(CX, CY + k * CH / 5); c.lineTo(CX + CW, CY + k * CH / 5); c.stroke(); }
  const k = Math.floor(S.upto), fr = S.upto - k; c.lineWidth = 8; c.lineJoin = 'round';
  const seg = (i0, i1, col) => { c.strokeStyle = col; c.beginPath(); for (let i = i0; i <= i1; i++) i === i0 ? c.moveTo(X(i), Y(P[i])) : c.lineTo(X(i), Y(P[i])); c.stroke(); };
  if (S.ph === 'run' || S.ph === 'result') { seg(0, S.cur.a, '#9aa6b8'); const up = P[S.cur.b] >= P[S.cur.a]; seg(S.cur.a, k, up ? '#2bd47d' : '#ff4d5e'); } else seg(0, k, '#9aa6b8');
  const px = X(k) + (k < n ? (X(k + 1) - X(k)) * fr : 0), py = Y(P[k]) + (k < n ? (Y(P[k + 1]) - Y(P[k])) * fr : 0);
  c.fillStyle = '#fff'; c.beginPath(); c.arc(px, py, 14, 0, 7); c.fill(); c.restore();
  // the buttons and the clock
  const bw = 440, by = 1290; [['HIGHER', '#2bd47d', 70], ['LOWER', '#ff4d5e', 570]].forEach(([s, col, x]) => {
    let on = 1; if (S.ph === 'result') { const up = P[S.cur.b] >= P[S.cur.a]; on = (s === 'HIGHER') === up ? 1 : .25; }
    c.globalAlpha = on; rr(x, by, bw, 170, 40); c.fillStyle = col; c.fill(); c.globalAlpha = 1; big(s + (s === 'HIGHER' ? ' ▲' : ' ▼'), x + bw / 2, by + 88, 72, '#fff', 0, 'rgba(0,0,0,.35)'); });
  if (S.ph === 'guess') { const left = 3 - (S.d - .6), nn = Math.ceil(left); c.strokeStyle = '#ffd23f'; c.lineWidth = 18; c.beginPath(); c.arc(540, 1640, 90, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * (left / 3)); c.stroke();
    big(String(nn), 540, 1645, 120 * (.6 + .4 * back(cl(((S.d - .6) % 1) / .2))), '#fff'); big('GUESS!', 540, 1790, 60, '#ffd23f'); }
  if (S.ph === 'result') { const up = P[S.cur.b] >= P[S.cur.a], ch = (P[S.cur.b] / P[S.cur.a] - 1) * 100, p = back(cl((S.d - 4.7) / .25));
    c.save(); c.translate(540, 880); c.rotate(-.08); c.scale(p, p); rr(-360, -110, 720, 220, 40); c.fillStyle = up ? '#2bd47d' : '#ff4d5e'; c.fill(); c.lineWidth = 10; c.strokeStyle = '#fff'; c.stroke();
    big((up ? 'HIGHER ' : 'LOWER ') + (ch > 0 ? '+' : '') + Math.round(ch) + '%', 0, 4, 92, '#fff', 0, 'rgba(0,0,0,.4)'); c.restore();
    big('did you get it?', 540, 1650, 64, '#fff'); }
  if (!S.cur && t < R.rounds[0].t) { const p = back(cl(t / .3)); c.save(); c.translate(540, 1650); c.scale(p, p); big('3 ROUNDS. GO!', 0, 0, 96, '#ffd23f'); c.restore(); }
  // the reveal and the call
  const O = R.outro; if (t >= O.t) { const a = cl((t - O.t) / .3); c.fillStyle = `rgba(10,6,24,${.92 * a})`; c.fillRect(0, 0, W, H); c.globalAlpha = a;
    big('IT WAS', 540, 560, 80, '#fff'); big(O.name, 540, 700, 130 * back(cl((t - O.t - .2) / .3)), '#ffd23f');
    O.lines.forEach((l, i) => big(l, 540, 940 + i * 110, 76, '#fff'));
    rr(190, 1300, 700, 140, 70); c.fillStyle = '#4cc3cc'; c.fill(); big('memestreet.net', 540, 1372, 70, '#04161a', 0, 'rgba(0,0,0,0)'); c.globalAlpha = 1; }
}
function cover() { const C = R.cover || {}; frame(C.t || 3); const g = c.createLinearGradient(0, 1240, 0, 1920); g.addColorStop(0, 'rgba(11,26,74,.0)'); g.addColorStop(.15, '#141a4e'); g.addColorStop(1, '#0b1a4a'); c.fillStyle = g; c.fillRect(0, 1240, W, 680);
  big('3/3', 540, 1560, 230, '#ffd23f', -.05); big('OR YOU LOSE', 540, 1740, 92, '#fff', -.05); }
window.render = t => window.__coverOn ? cover() : frame(t);
window.overlaps = () => [];
window.ready = document.fonts.load(`900 40px ${F}`).then(() => document.fonts.load(`800 40px ${F}`)).then(() => { frame(0); return true; });
