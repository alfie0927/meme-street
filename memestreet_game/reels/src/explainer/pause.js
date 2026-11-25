// The pause challenge: the real game, recorded (capture.py), played fast, then frozen with "PAUSE. BUY OR SHORT?".
// window.__R = {T, dir: file URL of the shots, log: [[t, file]], before, map: [[rt, ct], ...] (reel time -> capture time, piecewise linear),
//   freeze, caps: [{t0, t1, text}], end, cover}
const R = window.__R, c = document.getElementById('c').getContext('2d'), W = 1080, H = 1920, F = 'Montserrat, sans-serif';
const cl = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x)), back = x => { x = cl(x); const k = 1.7; return 1 + (k + 1) * Math.pow(x - 1, 3) + k * Math.pow(x - 1, 2); };
const IMG = {};
const load = f => IMG[f] || (IMG[f] = new Promise(r => { const i = new Image(); i.onload = () => r(i); i.onerror = () => r(null); i.src = R.dir + '/' + f; }));
function capT(rt) { const M = R.map; if (rt <= M[0][0]) return null; for (let i = 1; i < M.length; i++) if (rt <= M[i][0]) { const [a, ca] = M[i - 1], [b, cb] = M[i]; return ca + (cb - ca) * (rt - a) / (b - a); } return M[M.length - 1][1]; }
function shotAt(ct) { let f = R.log[0][1]; for (const [t, n] of R.log) { if (t > ct) break; f = n; } return f; }
function big(s, x, y, size, fill, rot = 0, stroke = '#000') { c.save(); c.translate(x, y); c.rotate(rot); c.font = `900 ${size}px ${F}`; c.textAlign = 'center'; c.textBaseline = 'middle'; c.lineJoin = 'round';
  c.lineWidth = size * .2; c.strokeStyle = stroke; c.strokeText(s, 0, 0); c.fillStyle = fill; c.fillText(s, 0, 0); c.restore(); }
async function draw(t) {
  const ct = capT(t), f = ct == null ? R.before : shotAt(ct), img = await load(f), frozen = t >= R.freeze;
  c.fillStyle = '#0b0d10'; c.fillRect(0, 0, W, H);
  if (img) { const sy = 300, sh = 1300, zoom = frozen ? 1 + .06 * cl((t - R.freeze) / .25) : 1, dw = 1080 * zoom, dh = sh * zoom;      // (the timer, the chart and the Buy / Short buttons, filling the middle)
    c.drawImage(img, 0, sy, 1080, sh, 540 - dw / 2, 1130 - dh / 2, dw, dh); }
  // the headline band (frame 0: the claim, readable on mute)
  const g = c.createLinearGradient(0, 0, 0, 470); g.addColorStop(0, '#0b0d10'); g.addColorStop(1, 'rgba(11,13,16,.0)'); c.fillStyle = g; c.fillRect(0, 0, W, 470);
  c.save(); c.translate(540, 220); c.rotate(-.03); const pw = 760; c.fillStyle = '#e8394a'; c.beginPath(); c.roundRect(-pw / 2, -78, pw, 156, 26); c.fill(); c.restore();
  big('PAUSE CHALLENGE', 540, 220, 88, '#fff', -.03, '#5a0c14'); big('real stock · name hidden', 540, 345, 46, '#ffd23f');
  // the words as they are said
  const cap = (R.caps || []).find(q => t >= q.t0 && t < q.t1);
  if (cap && !frozen) { const p = back(cl((t - cap.t0) / .15)); c.save(); c.translate(540, 1830); c.scale(p, p); big(cap.text, 0, 0, 92, cap.hot ? '#ffd23f' : '#fff'); c.restore(); }
  // the freeze: a flash, PAUSE, the question, a 3-2-1
  if (frozen) { const d = t - R.freeze;
    if (d < .12) { c.fillStyle = `rgba(255,255,255,${.6 * (1 - d / .12)})`; c.fillRect(0, 0, W, H); }
    c.fillStyle = 'rgba(0,0,0,.35)'; c.fillRect(0, 520, W, 1400);
    const p = back(cl(d / .2)); c.save(); c.translate(540, 900); c.scale(p, p);
    c.fillStyle = '#fff'; c.fillRect(-150, -110, 100, 220); c.fillRect(50, -110, 100, 220); c.restore();
    big('PAUSE!', 540, 1130, 170 * back(cl(d / .2)), '#ffffff');
    if (d > .5) { const q = back(cl((d - .5) / .2)); c.save(); c.translate(540, 1330); c.scale(q, q); big('BUY OR SHORT?', 0, 0, 104, '#ffd23f'); c.restore(); }
    if (d > 1 && t < R.end) { const n = 3 - Math.floor(d - 1); if (n > 0) { const fr = (d - 1) % 1; c.strokeStyle = '#ffd23f'; c.lineWidth = 16; c.beginPath(); c.arc(540, 1560, 80, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * (1 - fr)); c.stroke(); big(String(n), 540, 1563, 96, '#fff'); } } }
  if (t >= R.end) { const a = cl((t - R.end) / .3); c.fillStyle = `rgba(6,6,12,${.9 * a})`; c.fillRect(0, 0, W, H); c.globalAlpha = a;
    big('COMMENT', 540, 760, 120, '#fff'); big('BUY OR SHORT', 540, 900, 110, '#ffd23f'); big('then play it at', 540, 1080, 56, '#fff');
    c.fillStyle = '#4cc3cc'; c.beginPath(); c.roundRect(190, 1150, 700, 130, 65); c.fill(); big('memestreet.net', 540, 1216, 64, '#04161a', 0, 'rgba(0,0,0,0)'); c.globalAlpha = 1; }
}
async function cover() {    // its own thumbnail: the frozen game, two pause bars, one question
  await draw(R.freeze - .05); c.fillStyle = '#0b0d10'; c.fillRect(250, 470, 360, 90);      // (no DAILY #N on this reel: only the 23:30 story reel carries it)
  c.fillStyle = 'rgba(0,0,0,.4)'; c.fillRect(0, 470, W, 1450); c.fillStyle = '#fff'; c.fillRect(390, 820, 100, 220); c.fillRect(590, 820, 100, 220);
  big('WOULD YOU', 540, 1500, 120, '#fff', -.04); big('BUY THIS?', 540, 1650, 140, '#ffd23f', -.04);
}
window.render = t => window.__coverOn ? cover() : draw(t);
window.overlaps = () => [];
window.ready = document.fonts.load(`900 40px ${F}`).then(() => load(R.before)).then(() => true);
