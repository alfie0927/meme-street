// A text-message story reel: two friends in a chat, bubbles popping in with typing dots, a chart sent as a picture, a big
// headline on top. window.__R = {T, title, who, msgs: [{t, from: "them"|"me", text?, chart?}], end: {t, lines, foot}, prices, cover}
const R = window.__R, c = document.getElementById('c').getContext('2d'), W = 1080, H = 1920;
const cl = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x)), ease = x => 1 - Math.pow(1 - cl(x), 3);
const back = x => { x = cl(x); const k = 1.6; return 1 + (k + 1) * Math.pow(x - 1, 3) + k * Math.pow(x - 1, 2); };
const F = 'Montserrat, sans-serif', TOP = 560, BOT = 1640, PAD = 60, MAXW = 700;
function rr(x, y, w, h, r) { c.beginPath(); c.roundRect(x, y, w, h, r); }
function wrap(text, size, maxw) { c.font = `600 ${size}px ${F}`; const out = []; let line = '';
  for (const w of String(text).split(' ')) { const t = line ? line + ' ' + w : w; if (c.measureText(t).width > maxw && line) { out.push(line); line = w; } else line = t; } if (line) out.push(line); return out; }
function chartImg(x, y, w, h, P) {          // the mystery chart as a picture in the chat
  rr(x, y, w, h, 28); c.fillStyle = '#0b0d14'; c.fill(); const lo = Math.min(...P), hi = Math.max(...P), n = P.length - 1;
  c.save(); rr(x, y, w, h, 28); c.clip(); c.strokeStyle = 'rgba(255,255,255,.07)'; c.lineWidth = 2; for (let i = 1; i < 4; i++) { c.beginPath(); c.moveTo(x, y + i * h / 4); c.lineTo(x + w, y + i * h / 4); c.stroke(); }
  const up = P[n] >= P[0]; c.strokeStyle = up ? '#2bd47d' : '#ff4d5e'; c.lineWidth = 7; c.lineJoin = 'round'; c.beginPath();
  P.forEach((v, i) => { const px = x + 30 + i / n * (w - 60), py = y + h - 40 - (v - lo) / (hi - lo + 1e-9) * (h - 130); i ? c.lineTo(px, py) : c.moveTo(px, py); }); c.stroke();
  c.fillStyle = '#ffd23f'; c.font = `900 52px ${F}`; c.textAlign = 'center'; c.fillText('???', x + w / 2, y + 62); c.fillStyle = '#8a97a3'; c.font = `700 26px ${F}`; c.fillText('MEME STREET · TODAY\'S CHART', x + w / 2, y + h - 12); c.restore();
}
function layout(t) {        // every bubble shown by t, measured, stacked from the top, scrolled so the newest sits above the bottom
  const items = []; let y = 0;
  for (const m of R.msgs) { if (t < m.t) break; const me = m.from === 'me', size = 48;
    let w, h, lines = null; if (m.chart) { w = 640; h = 420; } else { lines = wrap(m.text, size, MAXW - 70); c.font = `600 ${size}px ${F}`; w = Math.min(MAXW, Math.max(...lines.map(l => c.measureText(l).width)) + 70); h = lines.length * 62 + 44; }
    const gap = items.length && items[items.length - 1].me === me ? 12 : 34; y += gap; items.push({m, me, w, h, lines, y, size}); y += h; }
  const typing = R.msgs.find(m => m.from !== 'me' && m.t > t && m.t - t < .75 && !m.notype); if (typing) { y += 34; items.push({typing: true, y, w: 170, h: 96}); y += 96; }
  const scroll = Math.max(0, y - (BOT - TOP)); return {items, scroll};
}
function frame(t) {
  c.fillStyle = '#0d0f17'; c.fillRect(0, 0, W, H);
  // the phone's chat header
  c.fillStyle = '#161925'; c.fillRect(0, 360, W, 170); c.fillStyle = '#ff5d8f'; c.beginPath(); c.arc(130, 445, 52, 0, 7); c.fill();
  c.fillStyle = '#fff'; c.font = `800 50px ${F}`; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(R.who[0], 130, 448);
  c.textAlign = 'left'; c.font = `800 46px ${F}`; c.fillText(R.who, 210, 426); c.fillStyle = '#2bd47d'; c.font = `600 30px ${F}`; c.fillText('online', 210, 472);
  // the bubbles
  const {items, scroll} = layout(t); c.save(); c.beginPath(); c.rect(0, 530, W, BOT - 530 + 120); c.clip();
  for (const it of items) { const y = TOP + it.y - scroll; if (y + it.h < 510) continue;
    if (it.typing) { const x = PAD; rr(x, y, it.w, it.h, 48); c.fillStyle = '#2a2d3a'; c.fill(); for (let k = 0; k < 3; k++) { c.fillStyle = `rgba(255,255,255,${.35 + .65 * Math.max(0, Math.sin(t * 9 - k * .9))})`; c.beginPath(); c.arc(x + 50 + k * 36, y + 48, 12, 0, 7); c.fill(); } continue; }
    const p = back(cl((t - it.m.t) / .22)), x = it.me ? W - PAD - it.w : PAD; c.save(); c.translate(x + (it.me ? it.w : 0), y + it.h); c.scale(p, p); c.translate(-(x + (it.me ? it.w : 0)), -(y + it.h));
    if (it.m.chart) chartImg(x, y, it.w, it.h, R.prices);
    else { rr(x, y, it.w, it.h, 44); c.fillStyle = it.me ? '#2f7cf6' : '#2a2d3a'; c.fill(); c.fillStyle = '#fff'; c.font = `600 ${it.size}px ${F}`; c.textAlign = 'left'; c.textBaseline = 'top';
      it.lines.forEach((l, i) => c.fillText(l, x + 35, y + 24 + i * 62)); }
    c.restore(); }
  c.restore();
  // the input bar
  c.fillStyle = '#161925'; c.fillRect(0, 1700, W, 220); rr(50, 1735, W - 200, 96, 48); c.fillStyle = '#232633'; c.fill(); c.fillStyle = '#6b7080'; c.font = `600 38px ${F}`; c.textAlign = 'left'; c.textBaseline = 'middle'; c.fillText('Message', 95, 1784);
  c.fillStyle = '#2f7cf6'; c.beginPath(); c.arc(W - 100, 1783, 48, 0, 7); c.fill();
  // the headline over the top (the hook, readable on mute, there from frame 0)
  const hl = R.title; c.textAlign = 'center'; c.textBaseline = 'middle'; c.lineJoin = 'round'; let size = 74; c.font = `900 ${size}px ${F}`;
  const L = wrap(hl.toUpperCase(), size, 960); c.font = `900 ${size}px ${F}`;
  L.forEach((l, i) => { const y = 200 + i * 84 - (L.length - 1) * 30; c.lineWidth = 16; c.strokeStyle = '#000'; c.strokeText(l, 540, y); c.fillStyle = i === L.length - 1 ? '#ffd23f' : '#fff'; c.fillText(l, 540, y); });
  // the end card
  if (R.end && t >= R.end.t) { const a = cl((t - R.end.t) / .3); c.fillStyle = `rgba(6,6,12,${.93 * a})`; c.fillRect(0, 0, W, H); c.globalAlpha = a;
    R.end.lines.forEach((l, i) => { const s = i ? 84 : 104; c.font = `900 ${s}px ${F}`; c.lineWidth = 16; c.strokeStyle = '#000'; const y = 820 + i * 120; c.strokeText(l, 540, y); c.fillStyle = i ? '#fff' : '#ffd23f'; c.fillText(l, 540, y); });
    rr(240, 1080, 600, 120, 60); c.fillStyle = '#2f7cf6'; c.fill(); c.fillStyle = '#fff'; c.font = `800 48px ${F}`; c.fillText(R.end.foot, 540, 1141); c.globalAlpha = 1; }
}
function cover() {          // its own thumbnail: the chat at its best moment, one bold line across it
  const C = R.cover || {}; frame(C.t || 6); c.fillStyle = 'rgba(0,0,0,.35)'; c.fillRect(0, 0, W, H);
  c.save(); c.translate(540, 1000); c.rotate(-.06); c.fillStyle = C.color || '#ffd23f'; c.fillRect(-640, -170, 1280, 340); c.restore();
  (C.lines || [R.title]).forEach((l, i, A) => { c.save(); c.translate(540, 1000 + (i - (A.length - 1) / 2) * 140); c.rotate(-.06); c.font = `900 128px ${F}`; c.textAlign = 'center'; c.textBaseline = 'middle'; c.lineWidth = 20; c.lineJoin = 'round'; c.strokeStyle = '#000'; c.strokeText(l, 0, 0); c.fillStyle = '#fff'; c.fillText(l, 0, 0); c.restore(); });
}
window.render = t => { if (window.__coverOn) cover(); else frame(t); };
window.overlaps = () => [];
window.ready = document.fonts.load(`900 40px ${F}`).then(() => document.fonts.load(`600 40px ${F}`)).then(() => { frame(0); return true; });
