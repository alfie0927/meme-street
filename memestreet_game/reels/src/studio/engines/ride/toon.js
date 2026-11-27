// The studio's people: the same cut-out figures as the 3D story reel (a big white head, a drawn face that shows the feeling,
// a coloured costume, stick legs), drawn in code on a canvas. Copied from src/explainer/story3d.js so that file stays untouched.
// window.Toon(S) -> {draw(x, p, t), W, H}; p = {look, color, pose, seed, mir, glasses, tache}.
window.Toon = function (S) {
'use strict';
const INK2 = '#16121c', FACE = {stand: 'calm', walk: 'calm', hold: 'joy', cheer: 'joy', surf: 'joy', point: 'smug', shock: 'shock', sad: 'sad'};
const CW2 = 400, CH2 = 760;                                // the cut-out's canvas (px); it stands 1.9 m tall
const S2shade = (c, k) => S.shade(c || '#888888', k);
function drawToon(x, p, t) {
  const k = p.look, col = p.color, s = Math.sin, sd = p.seed, mood = FACE[p.pose] || 'calm', K = INK2;
  x.clearRect(0, 0, CW2, CH2); x.lineCap = x.lineJoin = 'round';
  const L = (pts, w, c = K) => { x.strokeStyle = c; x.lineWidth = w; x.beginPath(); pts.forEach(([a, b], i) => i ? x.lineTo(a, b) : x.moveTo(a, b)); x.stroke(); };
  const blobp = (path, fill, w = 9) => { x.beginPath(); path(); x.fillStyle = fill; x.fill(); x.lineWidth = w; x.strokeStyle = K; x.stroke(); };
  const bob = p.pose === 'cheer' ? -14 * Math.abs(s(t * 5.5 + sd)) : 3 * s(t * 2 + sd), cx = 200, top = 300 + bob, bot = 560 + bob;
  const sw = p.pose === 'walk' ? 26 * s(t * 8 + sd) : 0;
  L([[cx - 34, bot - 6], [cx - 40 - sw, 712]], 11); L([[cx + 34, bot - 6], [cx + 40 + sw, 712]], 11);
  for (const [fx, d] of [[cx - 40 - sw, -1], [cx + 40 + sw, 1]]) blobp(() => x.ellipse(fx + d * 12, 718, 26, 13, 0, 0, 7), '#2a2530', 6);
  const A = {stand: [.25, .25], walk: [.3 + .4 * s(t * 8 + sd), .3 - .4 * s(t * 8 + sd)], cheer: [2.6 + .25 * s(t * 9 + sd), 2.6 - .25 * s(t * 9 + sd)], point: [p.mir ? 1.55 : .3, p.mir ? .3 : 1.55],
    shock: [2.3, 2.3], sad: [.08, .08], hold: [1.25, 1.25], surf: [1.5 + .15 * s(t * 3), 1.4 - .15 * s(t * 3)]}[p.pose] || [.25, .25];
  const hands = [];
  for (const [i, d] of [[0, -1], [1, 1]]) { const a = A[i], sx = cx + d * 78, sy = top + 46, len = p.pose === 'shock' ? 120 : 150, ex = sx + d * Math.sin(a) * len, ey = sy + Math.cos(a) * len;
    L([[sx, sy], [(sx + ex) / 2 + d * 6, (sy + ey) / 2], [ex, ey]], 10); hands.push([ex, ey]); }
  const bodyCol = k === 'suit' ? '#2b3350' : k === 'worker' ? '#f08a2a' : col || '#3a7bd5';
  blobp(() => { x.moveTo(cx - 70, top + 20); x.quadraticCurveTo(cx, top - 4, cx + 70, top + 20); x.lineTo(cx + 88, bot); x.lineTo(cx - 88, bot); x.closePath(); }, bodyCol);
  if (k === 'suit') { x.fillStyle = '#f4f2ec'; x.beginPath(); x.moveTo(cx - 28, top + 10); x.lineTo(cx, top + 92); x.lineTo(cx + 28, top + 10); x.fill(); x.fillStyle = col || '#d23a4a'; x.beginPath(); x.moveTo(cx - 9, top + 22); x.lineTo(cx + 9, top + 22); x.lineTo(cx + 13, top + 118); x.lineTo(cx, top + 136); x.lineTo(cx - 13, top + 118); x.fill(); L([[cx - 28, top + 10], [cx, top + 92], [cx + 28, top + 10]], 6); }
  else if (k === 'woman') blobp(() => { x.moveTo(cx - 80, bot - 70); x.lineTo(cx + 80, bot - 70); x.lineTo(cx + 104, bot + 26); x.lineTo(cx - 104, bot + 26); x.closePath(); }, S2shade(col, -.15));
  else if (k === 'hoodie') { L([[cx - 34, top + 14], [cx - 26, top + 90]], 6); L([[cx + 34, top + 14], [cx + 26, top + 90]], 6); blobp(() => x.roundRect(cx - 50, bot - 92, 100, 44, 12), S2shade(col, -.18), 6); }
  else for (let b = 0; b < 3; b++) blobp(() => x.arc(cx, top + 70 + b * 56, 7, 0, 7), '#ffffff', 4);
  for (const [hx, hy] of hands) blobp(() => x.arc(hx, hy, 17, 0, 7), '#ffffff', 7);
  const hy = top - 112 + (mood === 'sad' ? 10 : 0), r = 128, tilt = mood === 'sad' ? .08 : .04 * s(t * 1.3 + sd);
  x.save(); x.translate(cx, hy); x.rotate(tilt);
  blobp(() => x.arc(0, 0, r, 0, 7), '#ffffff', 11);
  const hair = ['#1d1a22', '#4a2f1f', '#7a4a26', '#2b2b2b'][sd % 4];
  if (k === 'worker') { blobp(() => { x.arc(0, -36, r * .98, Math.PI * 1.08, Math.PI * 1.92); x.closePath(); }, '#ffcc2e'); blobp(() => x.roundRect(-r - 10, -50, 2 * r + 20, 22, 10), '#ffcc2e', 7); }
  else if (k === 'woman') blobp(() => { x.arc(0, -10, r * 1.02, Math.PI * .95, Math.PI * 2.05); x.lineTo(r, 90); x.quadraticCurveTo(r * .78, 30, r * .7, -40); x.quadraticCurveTo(0, -60, -r * .7, -40); x.quadraticCurveTo(-r * .78, 30, -r, 90); x.closePath(); }, hair);
  else if (sd % 3 === 0) { for (let q = -3; q <= 3; q++) blobp(() => x.ellipse(q * 30, -r + 6 + Math.abs(q) * 4, 26, 34, q * .25, 0, 7), hair, 7); }
  else blobp(() => { x.arc(0, -14, r * .98, Math.PI * 1.1, Math.PI * 1.9); x.quadraticCurveTo(20, -r * .55, -r * .92, -r * .42); x.closePath(); }, hair);
  const blink = (t * .9 + sd * .77) % 3.3 < .13;
  for (const d of [-1, 1]) { const ex = d * 44, ey = 6;
    if (mood === 'sad') L([[ex - d * 30, ey - 48], [ex + d * 22, ey - 62]], 9);
    else if (mood === 'shock') L([[ex - 24, ey - 70], [ex + 24, ey - 70]], 9);
    else if (mood === 'smug') L(d < 0 ? [[ex - 26, ey - 46], [ex + 22, ey - 52]] : [[ex - 22, ey - 66], [ex + 26, ey - 58]], 9);
    else L(d < 0 ? [[ex - 24, ey - 56], [ex + 22, ey - 62]] : [[ex - 22, ey - 62], [ex + 24, ey - 56]], 9);
    if (blink && mood !== 'shock') L([[ex - 24, ey], [ex + 24, ey]], 9);
    else { blobp(() => x.ellipse(ex, ey, mood === 'shock' ? 34 : 30, mood === 'shock' ? 40 : mood === 'smug' ? 22 : 34, 0, 0, 7), '#ffffff', 8);
      x.fillStyle = K; x.beginPath(); x.arc(ex + (mood === 'smug' ? d * 4 : 3), ey + (mood === 'sad' ? 10 : 4), mood === 'shock' ? 10 : 14, 0, 7); x.fill();
      x.fillStyle = '#fff'; x.beginPath(); x.arc(ex + 8, ey - 4, 4.5, 0, 7); x.fill();
      if (mood === 'smug') L([[ex - 30, ey - 8], [ex + 30, ey - 8]], 9); } }
  if (p.glasses) { L([[-14, 6], [14, 6]], 6); for (const d of [-1, 1]) { x.lineWidth = 7; x.strokeStyle = K; x.beginPath(); x.arc(d * 44, 6, 40, 0, 7); x.stroke(); } }
  if (p.tache) blobp(() => { x.moveTo(-58, 56); x.quadraticCurveTo(-30, 30, 0, 50); x.quadraticCurveTo(30, 30, 58, 56); x.quadraticCurveTo(30, 66, 0, 58); x.quadraticCurveTo(-30, 66, -58, 56); }, '#4a4650', 7);
  const my = p.tache ? 80 : 66;
  if (mood === 'joy') { blobp(() => { x.moveTo(-50, my - 6); x.quadraticCurveTo(0, my + 74, 50, my - 6); x.closePath(); }, '#7a1f2b', 8); x.fillStyle = '#ff8c9a'; x.beginPath(); x.ellipse(0, my + 26, 18, 10, 0, 0, 7); x.fill(); }
  else if (mood === 'shock') blobp(() => x.ellipse(0, my + 14, 20, 28, 0, 0, 7), '#3a1218', 8);
  else if (mood === 'sad') { L([[-30, my + 20], [0, my + 6], [30, my + 20]], 9); x.fillStyle = '#8fd0ff'; x.beginPath(); x.moveTo(-66, 30); x.quadraticCurveTo(-54, 60, -66, 70); x.quadraticCurveTo(-78, 60, -66, 30); x.fill(); }
  else if (mood === 'smug') L([[-34, my + 8], [10, my + 14], [40, my - 6]], 9);
  else L([[-32, my + 4], [0, my + 16], [32, my + 4]], 9);
  x.restore();
}
return {draw: drawToon, W: CW2, H: CH2};
};
