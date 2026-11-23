// Meme Street's story reel: the flat layer over the 3D picture (story3d.js draws the picture and calls this).
// It holds what is WRITTEN on a reel: the header (progress bar, the headline that stays, the date), the words slammed on a
// scene (title, counter, stamp), the screens of 3D props (phone, chart, calendar, paper) and the captions, word by word,
// brand names in their colours and figures in gold. Every box it draws is registered (reg) for the overlap check.
// window.__R (make.py) = {T, title, tag, tag2, reveal, brands:[{name,color}], cast:{id:{look,color,tag}}, scenes:[{t0,t1,bg,label,
//   items:[{kind,t,...}]}], caps:[{t0,t1,words:[{text,t0,color}]}], prices:[...], dates:[start,end]}
const R = window.__R; let c = document.getElementById('c').getContext('2d');
const W = 1080, INK = '#15162b', GOLD = '#ffc83d', RED = '#e8394a', GREEN = '#2bd47d', F = 'Fredoka, sans-serif';
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x)), ease = x => 1 - Math.pow(1 - clamp(x), 3);
const back = x => { x = clamp(x); const k = 1.9; return 1 + (k + 1) * Math.pow(x - 1, 3) + k * Math.pow(x - 1, 2); };
let BOX = [];
const reg = (name, x, y, w, h) => BOX.push({name, x, y, w, h});

// ------------------------------------------------------------ drawing helpers
function rr(x, y, w, h, r) { c.beginPath(); c.roundRect(x, y, w, h, r); }
function blob(x, y, w, h, r, fill, line = 6) { rr(x, y, w, h, r); c.fillStyle = fill; c.fill(); if (line) { c.lineWidth = line; c.strokeStyle = INK; c.stroke(); } }
function circ(x, y, r, fill, line = 6) { c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.fillStyle = fill; c.fill(); if (line) { c.lineWidth = line; c.strokeStyle = INK; c.stroke(); } }
function txt(s, x, y, size, color, max = 9e9, weight = 700, align = 'center', edge = 0) {
  s = String(s); c.font = `${weight} ${size}px ${F}`;
  while (size > 14 && c.measureText(s).width > max) { size -= 2; c.font = `${weight} ${size}px ${F}`; }
  c.textAlign = align; c.textBaseline = 'middle';
  if (edge) { c.lineJoin = 'round'; c.lineWidth = edge; c.strokeStyle = INK; c.strokeText(s, x, y); }
  c.fillStyle = color; c.fillText(s, x, y); return c.measureText(s).width;
}
function shade(hex, k) {        // k < 0 darker, > 0 lighter
  const n = parseInt(hex.slice(1), 16); let r = n >> 16, g = n >> 8 & 255, b = n & 255;
  const f = v => Math.round(k < 0 ? v * (1 + k) : v + (255 - v) * k); return `rgb(${f(r)},${f(g)},${f(b)})`;
}
function pill(s, cx, cy, size, fg, bg, max = 900) {
  c.font = `700 ${size}px ${F}`; while (size > 16 && c.measureText(s).width > max) { size -= 2; c.font = `700 ${size}px ${F}`; }
  const w = c.measureText(s).width + size * 1.1, h = size * 1.55;
  blob(cx - w / 2, cy - h / 2, w, h, h / 2, bg, 0); txt(s, cx, cy + 2, size, fg); return [cx - w / 2, cy - h / 2, w, h];
}
const brandColor = name => ((R.brands || []).find(b => b.name.toLowerCase() === String(name || '').toLowerCase()) || (R.brands || [])[0] || {color: '#2f7cf6'}).color;
const wordColor = w => { const k = String(w).toLowerCase().replace(/('s|s')$/, '').replace(/[^a-z0-9]/g, ''), b = (R.brands || []).find(q => q.name.toLowerCase().replace(/[^a-z0-9]/g, '') === k);
  return b ? b.color : /\d/.test(w) ? GOLD : '#fff'; };

// ------------------------------------------------------------ what is drawn flat: each inside its natural box (w x h) at (0,0)
// [natural w, h, draw(it, t, a, dur)] (t = seconds since it appeared, a = its appear progress 0..1)
const K = {
  // the screens of 3D props
  phone: [240, 420, (it, t) => { const col = brandColor(it.brand); blob(20, 0, 200, 420, 34, '#1b1d24'); blob(36, 24, 168, 372, 18, '#f7f8fb', 0);
    blob(36, 24, 168, 70, [18, 18, 0, 0], col, 0); txt(it.title || '', 120, 60, 28, '#fff', 150);
    (it.lines || []).slice(0, 4).forEach((l, i) => { blob(50, 116 + i * 66, 140, 52, 12, i === 0 ? col : '#e4e7ef', 0); txt(l, 120, 143 + i * 66, 22, i === 0 ? '#fff' : INK, 125); });
    if (it.tap) { const p = (t % 1.2) / 1.2; c.globalAlpha = 1 - p; circ(120, 142, 20 + p * 40, 'rgba(255,255,255,.6)', 0); c.globalAlpha = 1; } }],
  chart: [940, 540, (it, t, a, dur) => { blob(4, 4, 932, 532, 26, '#141830', 0); c.lineWidth = 4; c.strokeStyle = '#3a4a7a'; rr(4, 4, 932, 532, 26); c.stroke();
    const P = R.prices || [1, 2], n = P.length - 1, i0 = Math.round(clamp(it.from || 0) * n), i1 = Math.round(clamp(it.to == null ? 1 : it.to) * n);
    const lo = Math.min(...P) * .95, hi = Math.max(...P) * 1.04, X = i => 50 + (i / n) * 840, Y = v => 480 - (v - lo) / (hi - lo) * 380;
    c.strokeStyle = 'rgba(255,255,255,.08)'; c.lineWidth = 2; for (let k = 0; k < 5; k++) { c.beginPath(); c.moveTo(50, 100 + k * 95); c.lineTo(890, 100 + k * 95); c.stroke(); }
    pill(it.title || ((R.brands || [{}])[0].name + ' STOCK').toUpperCase(), 470, 58, it.title === '???' ? 56 : 38, '#fff', it.title === '???' ? '#3a4a7a' : brandColor(), 600);
    const k1 = Math.round(i0 + (i1 - i0) * ease(t / Math.max(1, (dur || 3) * .8))), up = P[i1] >= P[i0], col = up ? GREEN : RED;
    c.lineWidth = 9; c.lineJoin = 'round'; c.strokeStyle = 'rgba(255,255,255,.3)'; c.beginPath(); for (let i = 0; i <= i0; i++) i ? c.lineTo(X(i), Y(P[i])) : c.moveTo(X(i), Y(P[i])); c.stroke();
    c.strokeStyle = col; c.beginPath(); for (let i = i0; i <= k1; i++) i === i0 ? c.moveTo(X(i), Y(P[i])) : c.lineTo(X(i), Y(P[i])); c.stroke();
    circ(X(k1), Y(P[k1]), 14, '#fff', 0); const lx = Math.min(800, Math.max(140, X(k1))), ly = Y(P[k1]) - 62 < 100 ? Y(P[k1]) + 62 : Y(P[k1]) - 62;
    pill('$' + P[k1].toFixed(2), lx, ly, 46, INK, GOLD); }],
  calendar: [240, 260, (it) => { blob(10, 20, 220, 230, 18, '#fff'); blob(10, 20, 220, 70, [18, 18, 0, 0], RED); txt(String(it.month || '').toUpperCase(), 120, 56, 40, '#fff', 190);
    txt(it.day || '', 120, 170, 100, INK, 190); c.fillStyle = INK; c.fillRect(60, 8, 12, 34); c.fillRect(168, 8, 12, 34); }],
  doc: [260, 320, (it) => { blob(20, 10, 220, 300, 8, '#fdfaf2');
    txt(String(it.title || '').toUpperCase(), 130, 60, 32, it.color || RED, 190); c.fillStyle = '#c9c4b5'; for (let k = 0; k < 6; k++) c.fillRect(46, 110 + k * 30, 168 - (k % 3) * 30, 10);
    if (it.text) txt(it.text, 130, 285, 34, INK, 190); }],
  // the words slammed on a scene (one a scene, in the band under the header)
  title: [940, 236, (it) => { const s = String(it.text || '').toUpperCase(), w = s.split(' '); let L = [s];     // the hook's promise: two big lines, the second (the payoff) in gold
    if (s.length > 12 && w.length > 1) { let best = 1, d = 1e9; for (let i = 1; i < w.length; i++) { const q = Math.abs(w.slice(0, i).join(' ').length - w.slice(i).join(' ').length); if (q < d) { d = q; best = i; } } L = [w.slice(0, best).join(' '), w.slice(best).join(' ')]; }
    let size = L.length === 1 ? 150 : 112; c.font = `700 ${size}px ${F}`; while (size > 40 && Math.max(...L.map(l => c.measureText(l).width)) > 900) { size -= 4; c.font = `700 ${size}px ${F}`; }
    const sp = c.measureText(' ').width, lh = size * 1.05, y0 = 118 - (L.length - 1) * lh / 2;
    L.forEach((l, i) => { const ws = l.split(' '), tw = c.measureText(l).width; let x = 470 - tw / 2; for (const q of ws) { const ww = c.measureText(q).width; txt(q, x + ww / 2, y0 + i * lh, size, i && wordColor(q) === '#fff' ? GOLD : wordColor(q), 9e9, 700, 'center', size * .22); c.font = `700 ${size}px ${F}`; x += ww + sp; } }); }],
  counter: [640, 236, (it, t, a, dur) => { const v = (+it.to || 0) * ease(t / Math.min(1.1, Math.max(.3, (dur || 3) * .45))), d = Number.isInteger(+it.to) ? 0 : 2;
    txt((it.prefix || '') + v.toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d}) + (it.suffix || ''), 320, 92, 150, it.color || GREEN, 620, 700, 'center', 22);
    if (it.text) pill(String(it.text).toUpperCase(), 320, 200, 36, '#fff', '#14182b', 540); }],
  stamp: [560, 180, (it) => { c.save(); c.translate(280, 90); c.rotate(-.1); const col = it.color || RED; rr(-240, -58, 480, 116, 16); c.fillStyle = 'rgba(255,255,255,.94)'; c.fill();   // (rotated, it still fits its box)
    c.lineWidth = 12; c.strokeStyle = col; c.stroke(); txt(String(it.text || '').toUpperCase(), 0, 5, 82, col, 430); c.restore(); }],
};

// ------------------------------------------------------------ header and captions (fixed over every scene)
function header(t, label) {      // the third model's mark: small, letter-spaced, top left
  c.save(); c.globalAlpha = .8; c.font = `600 26px Montserrat, ${F}`; c.letterSpacing = '4px'; c.textAlign = 'left'; c.textBaseline = 'middle'; c.shadowColor = 'rgba(0,0,0,.45)'; c.shadowBlur = 6;
  c.fillStyle = '#fff'; c.fillText('\u2205 MEME STREET', 64, 226); c.restore();
  reg('header', 0, 0, W, 250);
}
function captions(t) {             // as the third model: Montserrat, heavy, white with a dark edge and shadow, one or two words, mid-low
  const cap = (R.caps || []).find(q => t >= q.t0 && t < q.t1); if (!cap) return;
  const s = cap.words.map(w => w.text).join(' '); let size = 70; c.font = `800 ${size}px Montserrat, ${F}`;
  while (c.measureText(s).width > 880 && size > 44) { size -= 2; c.font = `800 ${size}px Montserrat, ${F}`; }
  const w = c.measureText(s).width, y = 1330;
  c.save(); c.textAlign = 'center'; c.textBaseline = 'middle'; c.lineJoin = 'round'; c.globalAlpha = clamp((t - cap.t0) / .04);
  c.shadowColor = 'rgba(0,0,0,.55)'; c.shadowBlur = 12; c.shadowOffsetY = 3; c.lineWidth = size * .14; c.strokeStyle = '#141018'; c.strokeText(s, 540, y);
  c.shadowColor = 'transparent'; c.fillStyle = '#ffffff'; c.fillText(s, 540, y); c.restore();
  reg('caption', 540 - w / 2 - 10, y - size * .7, w + 20, size * 1.4);
}
window.S2 = {K, INK, GOLD, RED, GREEN, header, captions, pill, txt, blob, rr, circ, shade, brandColor, clamp, ease, back, reg,
  boxes: () => BOX, reset: () => { BOX = []; }, ctx: x => { const o = c; c = x; return o; }};
window.ready = Promise.all([document.fonts.load(`700 40px Fredoka`), document.fonts.load(`800 40px Montserrat`), document.fonts.load(`600 26px Montserrat`)]).then(() => document.fonts.ready).then(() => true);
