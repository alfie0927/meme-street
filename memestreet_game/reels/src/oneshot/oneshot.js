/* The one-shot 3D reel (the owner, 2026-11-22: "completely remake everything from the ground up ... copy their styles, there
   should be NO differences"). The copied production is MagnatesMedia's "Funny Pricing Tactic" (research/library/production.md,
   COPY SPEC A, variant): one dim teal-grey place lit by warm lamps, faceless low-poly people, a camera that never rests and
   never cuts, strong depth-of-field blur, amber capitals in a black box, full-screen green/red figure cards.
   Everything on screen is a pure function of t (render(t)), so any frame can be drawn alone.
   People and props are CC0 (Quaternius, Kenney, CreativeTrio via poly.pizza; assets/CREDITS.json). */
(function () {
'use strict';
const T3 = THREE, R = window.__R || {}, CW = +(R.cw || 720), CH = Math.round(CW * 16 / 9);
const BASE = 'assets/';
const cl = (x, a, b) => Math.max(a, Math.min(b, x)), lerp = (a, b, k) => a + (b - a) * k;
const ease = k => k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
const hsh = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

// ---------- renderer, camera, post (depth of field like the exemplar's lens)
const cv = document.getElementById('gl');
const rn = new T3.WebGLRenderer({ canvas: cv, antialias: false, preserveDrawingBuffer: true });
rn.setSize(CW, CH, false); rn.setPixelRatio(1);
rn.outputEncoding = T3.sRGBEncoding; rn.toneMapping = T3.ACESFilmicToneMapping; rn.toneMappingExposure = 1.15;
rn.shadowMap.enabled = true; rn.shadowMap.type = T3.PCFSoftShadowMap;
const scene = new T3.Scene(), cam = new T3.PerspectiveCamera(42, CW / CH, .25, 60);
const fill = new T3.PointLight('#ffd9b0', .55, 7, 1.5); scene.add(fill);
const comp = new T3.EffectComposer(rn); comp.setSize(CW, CH);
comp.addPass(new T3.RenderPass(scene, cam));
const bokeh = new T3.BokehPass(scene, cam, { focus: 4, aperture: R.aperture || .012, maxblur: R.maxblur || .022, width: CW, height: CH });
comp.addPass(bokeh);

// ---------- loading
const loader = new T3.GLTFLoader(), cache = {};
const load = p => cache[p] || (cache[p] = new Promise((ok, no) => loader.load(BASE + p, ok, undefined, e => no(new Error(p + ': ' + (e && e.message || e))))));

// A prop scaled to a real size: {h: metres tall} or {w: metres wide}; its feet on the floor.
async function prop(name, o) {
  const g = (await load('props/' + name + '.glb')).scene.clone(true);
  const b = new T3.Box3().setFromObject(g), s = new T3.Vector3(); b.getSize(s);
  const k = o.h ? o.h / s.y : o.w ? o.w / Math.max(s.x, s.z) : (o.s || 1);
  g.scale.setScalar(k); const b2 = new T3.Box3().setFromObject(g), c = new T3.Vector3(); b2.getCenter(c);
  const wrap = new T3.Group(); g.position.set(-c.x, -b2.min.y, -c.z); wrap.add(g);
  wrap.position.set(o.x || 0, o.y || 0, o.z || 0); wrap.rotation.y = o.ry || 0;
  g.traverse(m => { if (m.isMesh) { m.castShadow = o.shadow !== false; m.receiveShadow = true; } });
  if (o.grade !== false) grade(wrap);
  scene.add(wrap); return wrap;
}

// A person: the model cloned with its skeleton, the face blanked (eyes and brows take the skin's colour: faceless, as the
// exemplar), a mixer to sample any clip at any time.
const SKIN = ['#8d5a3b', '#c58c64', '#e0b08a', '#6b4430', '#b7774f'];
async function person(o) {
  const gl = await load('people/' + o.who + '.glb');
  const g = T3.SkeletonUtils.clone(gl.scene); let skin = null;
  g.traverse(m => {
    if (!m.isMesh) return; m.castShadow = true; m.receiveShadow = true;
    const ms = Array.isArray(m.material) ? m.material : [m.material];
    m.material = ms.map(x => x.clone()); if (!Array.isArray(m.material) || m.material.length === 1) m.material = m.material[0];
    (Array.isArray(m.material) ? m.material : [m.material]).forEach(x => { x.flatShading = true; x.needsUpdate = true; if (/^skin$/i.test(x.name)) skin = x; });
  });
  const tone = new T3.Color(o.skin || SKIN[o.n % SKIN.length]);
  g.traverse(m => { if (!m.isMesh) return; (Array.isArray(m.material) ? m.material : [m.material]).forEach(x => {
    if (/^skin/i.test(x.name) && !R.rawSkin) x.color.copy(tone);
    if (/eye|brow|details/i.test(x.name)) x.color.copy(tone);      // faceless
    else if (!/^skin|hair/i.test(x.name) && x.color) { const h = {}; x.color.getHSL(h); if (h.l < .3) x.color.setHSL(h.h, h.s * .7, .3 + h.l * .5); }
  }); });
  const b = new T3.Box3().setFromObject(g), s = new T3.Vector3(); b.getSize(s); g.scale.setScalar((o.h || 1.78) / s.y);
  const root = new T3.Group(); root.add(g); scene.add(root);
  const mixer = new T3.AnimationMixer(g), clips = {};
  for (const c of gl.animations) clips[c.name.split('|').pop().replace(/^(Man|Female)_/, '')] = c;
  return { o, root, mixer, clips };
}

// ---------- the places (one per reel; the exemplar is one shop, ours are the places money stories happen)
function tex(draw, w = 512, h = 512, rep = [1, 1]) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new T3.CanvasTexture(c); t.wrapS = t.wrapT = T3.RepeatWrapping; t.repeat.set(rep[0], rep[1]); t.encoding = T3.sRGBEncoding; t.anisotropy = 4; return t;
}
const noise = (x, w, h, base, amp, seed) => { x.fillStyle = base; x.fillRect(0, 0, w, h); for (let i = 0; i < 2600; i++) { const r = hsh(i + seed), q = hsh(i * 3.1 + seed); x.fillStyle = `rgba(${r > .5 ? 255 : 0},${r > .5 ? 255 : 0},${r > .5 ? 255 : 0},${amp * hsh(i * 7.7 + seed)})`; x.fillRect(r * w, q * h, 3 + 6 * hsh(i + 9), 3 + 6 * hsh(i + 11)); } };
const TILE = tex((x, w, h) => { for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { x.fillStyle = (i + j) % 2 ? '#4a4f4c' : '#5c615c'; x.fillRect(i * w / 4, j * h / 4, w / 4, h / 4); } noise(x, w, h, 'rgba(0,0,0,0)', .05, 3); x.strokeStyle = 'rgba(0,0,0,.35)'; x.lineWidth = 3; for (let i = 0; i <= 4; i++) { x.beginPath(); x.moveTo(i * w / 4, 0); x.lineTo(i * w / 4, h); x.moveTo(0, i * h / 4); x.lineTo(w, i * h / 4); x.stroke(); } }, 512, 512, [6, 10]);
const WALL = tex((x, w, h) => { noise(x, w, h, '#93a19c', .07, 7); x.fillStyle = 'rgba(0,0,0,.18)'; x.fillRect(0, h * .62, w, h * .38); x.fillStyle = 'rgba(0,0,0,.35)'; x.fillRect(0, h * .615, w, 5); }, 512, 512, [3, 1]);
const CEIL = tex((x, w, h) => { noise(x, w, h, '#5a5f5c', .07, 11); x.strokeStyle = 'rgba(20,20,20,.55)'; x.lineWidth = 4; for (let i = 0; i <= 4; i++) { x.beginPath(); x.moveTo(i * w / 4, 0); x.lineTo(i * w / 4, h); x.moveTo(0, i * h / 4); x.lineTo(w, i * h / 4); x.stroke(); } }, 512, 512, [5, 8]);
const std = (o) => new T3.MeshStandardMaterial(Object.assign({ roughness: .85, metalness: 0 }, o));

function room(W, D, H, wall) {
  const floor = new T3.Mesh(new T3.PlaneGeometry(W, D), std({ map: TILE, roughness: .55 })); floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
  const ceil = new T3.Mesh(new T3.PlaneGeometry(W, D), std({ map: CEIL })); ceil.rotation.x = Math.PI / 2; ceil.position.y = H; scene.add(ceil);
  const wm = std({ map: WALL, color: wall || '#ffffff' });
  for (const [w, x, z, ry] of [[W, 0, -D / 2, 0], [W, 0, D / 2, Math.PI], [D, -W / 2, 0, Math.PI / 2], [D, W / 2, 0, -Math.PI / 2]]) {
    const m = new T3.Mesh(new T3.PlaneGeometry(w, H), wm); m.position.set(x, H / 2, z); m.rotation.y = ry; m.receiveShadow = true; scene.add(m);
  }
}
function windowLight(x, y, z, w, h, ry) {             // a bright window: the exemplar's back-wall glow
  const sky = tex((c, W, Hh) => { const g = c.createLinearGradient(0, 0, 0, Hh); g.addColorStop(0, '#f4f8ff'); g.addColorStop(1, '#bcd3e6'); c.fillStyle = g; c.fillRect(0, 0, W, Hh);
    c.fillStyle = 'rgba(120,140,150,.45)'; for (let i = 0; i < 9; i++) c.fillRect(i * W / 9, Hh * (.55 + .3 * hsh(i)), W / 11, Hh); c.fillStyle = '#2a2f30'; const n = Math.max(2, Math.round(w / 1.1));
    for (let i = 0; i <= n; i++) c.fillRect(i * (W - 14) / n, 0, 14, Hh); c.fillRect(0, 0, W, 14); c.fillRect(0, Hh - 14, W, 14); c.fillRect(0, Hh / 2 - 5, W, 10); }, 512, 256);
  const m = new T3.Mesh(new T3.PlaneGeometry(w, h), new T3.MeshBasicMaterial({ map: sky, toneMapped: false })); m.position.set(x, y, z); m.rotation.y = ry || 0; scene.add(m);
  const s = new T3.SpotLight('#cfe3ff', 1.1, 22, .9, .8, 1.2); s.position.set(x, y + .4, z + (ry ? 0 : .6)); s.target.position.set(x * .5, 0, z + (ry ? 0 : 6)); scene.add(s, s.target);
}
async function lamp(x, z, H, shadow) {                 // a warm ceiling lamp: a fixture and its light
  const tube = new T3.Mesh(new T3.BoxGeometry(1.3, .05, .22), new T3.MeshBasicMaterial({ color: '#fff1d6' })); tube.position.set(x, H - .03, z); scene.add(tube);
  const l = new T3.PointLight('#ffa64d', 3.2, 8.5, 1.7); l.position.set(x, H - .35, z);
  if (shadow) { l.castShadow = true; l.shadow.mapSize.set(512, 512); l.shadow.bias = -.002; }
  scene.add(l);
}
// A monitor's screen: a price chart (Meme Street's subject) as an emissive plane.
function chartTex(seed, up) {
  return tex((x, w, h) => {
    x.fillStyle = '#0b1418'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(120,160,170,.15)'; x.lineWidth = 1;
    for (let i = 1; i < 6; i++) { x.beginPath(); x.moveTo(0, i * h / 6); x.lineTo(w, i * h / 6); x.stroke(); }
    let p = h * .6; const n = 26, cw = w / n;
    for (let i = 0; i < n; i++) { const d = (hsh(i * 13 + seed) - .5) * h * .12 + (up ? -h * .012 : h * .012); const o = p, c = cl(p + d, h * .12, h * .9); const hi = Math.min(o, c) - hsh(i + seed) * 14, lo = Math.max(o, c) + hsh(i * 2 + seed) * 14;
      x.strokeStyle = x.fillStyle = c < o ? '#2fd27a' : '#e2483f'; x.beginPath(); x.moveTo(i * cw + cw / 2, hi); x.lineTo(i * cw + cw / 2, lo); x.stroke(); x.fillRect(i * cw + cw * .2, Math.min(o, c), cw * .6, Math.max(2, Math.abs(c - o))); p = c; }
  }, 512, 320);
}
async function screenOn(g, seed, up) {                 // put a chart on a monitor model's front face
  const b = new T3.Box3().setFromObject(g), s = new T3.Vector3(), c = new T3.Vector3(); b.getSize(s); b.getCenter(c);
  const m = new T3.Mesh(new T3.PlaneGeometry(s.x * .86, s.y * .55), new T3.MeshBasicMaterial({ map: chartTex(seed, up), toneMapped: false }));
  m.position.set(c.x, c.y + s.y * .12, b.max.z + .004); scene.add(m);
  const l = new T3.PointLight('#7fd6c4', .25, 2.2, 2); l.position.set(c.x, c.y, b.max.z + .3); scene.add(l);
}

function wallChart(x, y, z, w, ry, seed) {           // a framed chart on a wall
  const m = new T3.Mesh(new T3.PlaneGeometry(w, w * .62), new T3.MeshBasicMaterial({ map: chartTex(seed * 5 + 3, seed % 2), toneMapped: false }));
  const f = new T3.Mesh(new T3.BoxGeometry(w + .08, w * .62 + .08, .04), std({ color: '#1b1d1e' }));
  for (const o of [f, m]) { o.position.set(x, y, z); o.rotation.y = ry; scene.add(o); }
  m.translateZ(.025);
}
function poster(x, y, z, w, ry, seed) {              // a framed print: soft colour fields (no text, no logos)
  const m = new T3.Mesh(new T3.PlaneGeometry(w, w * 1.3), new T3.MeshStandardMaterial({ roughness: .8, map: tex((c, W, H) => {
    const cols = ['#c9874f', '#6d8a8a', '#d8c7a3', '#8b5a4a', '#4f6670', '#b8a06a']; c.fillStyle = cols[seed % 6]; c.fillRect(0, 0, W, H);
    for (let i = 0; i < 4; i++) { c.fillStyle = cols[(seed + i + 1) % 6]; c.globalAlpha = .8; c.beginPath(); c.arc(W * hsh(seed + i), H * hsh(seed * 3 + i), W * (.15 + .25 * hsh(i + seed * 7)), 0, 7); c.fill(); }
    c.globalAlpha = 1; }, 256, 332) }));
  const f = new T3.Mesh(new T3.BoxGeometry(w + .08, w * 1.3 + .08, .03), std({ color: '#2a2420' }));
  for (const o of [f, m]) { o.position.set(x, y, z); o.rotation.y = ry; scene.add(o); }
  m.translateZ(.02);
}
function grade(g) {                                    // props in the place's muted palette (the exemplar's colours are dulled, never toy-bright)
  g.traverse(m => { if (!m.isMesh) return; (Array.isArray(m.material) ? m.material : [m.material]).forEach(x => { if (x.color) { const h = {}; x.color.getHSL(h); x.color.setHSL(h.h, h.s * .6, Math.max(h.l * .85, .16)); } }); });
}
// Every screen in the reel (the wall display, the laptop, the full-screen terminal) is drawn by paint() from an entry of the
// script: {t0, t1, lines (typed), chart (the real price line up to a point of the period: 0..1), news (a headline), count}.
const money = (v, pre, suf, dp) => (pre || '') + v.toLocaleString('en-US', { minimumFractionDigits: dp || 0, maximumFractionDigits: dp || 0 }) + (suf || '');
const F = (px) => `700 ${px}px 'Montserrat', sans-serif`;
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
function dateAt(k) {                                   // a point of the period -> 'Nov 2020' (trading days spread evenly)
  if (!R.dates) return ''; const a = Date.parse(R.dates[0]), b = Date.parse(R.dates[1]), d = new Date(a + (b - a) * cl(k, 0, 1));
  return MON[d.getUTCMonth()] + ' ' + d.getUTCFullYear();
}
function fitFont(x, lines, px, w) { let fs = px; x.font = F(fs); while (fs > 30 && Math.max(...lines.map(l => x.measureText(l).width)) > w) { fs -= 4; x.font = F(fs); } return fs; }
function paint(x, W, H, e, t, prev) {
  // the frame: dark terminal, grid, a header with the ticker
  x.fillStyle = '#06110e'; x.fillRect(0, 0, W, H);
  x.strokeStyle = 'rgba(120,200,170,.10)'; x.lineWidth = 2; for (let i = 1; i < 8; i++) { x.beginPath(); x.moveTo(0, i * H / 8); x.lineTo(W, i * H / 8); x.stroke(); }
  const hh = Math.round(H * .07); x.fillStyle = '#0f2a22'; x.fillRect(0, 0, W, hh); x.fillStyle = '#7fe0c0'; x.font = F(Math.round(hh * .55)); x.textBaseline = 'middle'; x.textAlign = 'left';
  x.fillText((R.ticker || 'MARKET') + '   ' + (e && e.chart != null ? dateAt(chartK(e, t, prev)) : '\u25CF LIVE'), W * .03, hh / 2);
  if (!e) return;
  const u = t - e.t0, dur = Math.max(.5, e.t1 - e.t0); let top = hh + H * .05;
  if (e.news) {                                        // breaking news: a red band and the headline, typed
    const bh = Math.round(H * .09); x.fillStyle = '#c8121a'; x.fillRect(0, top, W, bh); x.fillStyle = '#fff'; x.font = F(Math.round(bh * .55));
    x.fillText('BREAKING', W * .04, top + bh / 2); top += bh + H * .05;
    const L = [].concat(e.news); const fs = fitFont(x, L, Math.round(H * .085), W * .92); x.fillStyle = '#fff'; let left = Math.floor(u * 32);
    L.forEach((ln, i) => { x.fillText(ln.slice(0, Math.max(0, left)), W * .04, top + fs * .6 + i * fs * 1.25); left -= ln.length; });
    top += L.length * fs * 1.25 + H * .03;
  }
  if (e.lines) {                                       // an order or a note, typed 28 letters a second with a cursor
    const fs = fitFont(x, e.lines, Math.round(H * (e.chart != null ? .07 : .1)), W * .92); x.fillStyle = '#eafff6'; let left = Math.floor(u * 28);
    e.lines.forEach((ln, i) => { const s = ln.slice(0, Math.max(0, left)); left -= ln.length;
      x.fillText(s + (left < 0 && left > -ln.length && Math.floor(t * 3) % 2 ? '_' : ''), W * .04, top + fs * .6 + i * fs * 1.3); });
    top += e.lines.length * fs * 1.3 + H * .03;
  }
  if (e.chart != null && R.prices) {                   // the real price line of the period, drawn up to its point across the sentence
    const P = R.prices, lo = Math.min(...P), hi = Math.max(...P), k = chartK(e, t, prev), n = Math.max(1, Math.round(k * (P.length - 1)));
    const x0 = W * .05, x1 = W * .95, y0 = Math.max(top, H * .3), y1 = H * (e.count ? .66 : .9);
    const X = i => x0 + (x1 - x0) * i / (P.length - 1), Y = v => y1 - (y1 - y0) * (v - lo) / (hi - lo || 1);
    const up = P[n] >= P[0]; x.strokeStyle = up ? '#35e08a' : '#ff4b45'; x.lineWidth = Math.max(4, W * .008); x.lineJoin = 'round'; x.beginPath();
    for (let i = 0; i <= n; i++) i ? x.lineTo(X(i), Y(P[i])) : x.moveTo(X(i), Y(P[i])); x.stroke();
    x.fillStyle = x.strokeStyle; x.beginPath(); x.arc(X(n), Y(P[n]), W * .014, 0, 7); x.fill();
    const lab = '$' + P[n].toFixed(2); x.font = F(Math.round(H * .06)); const lw = x.measureText(lab).width;
    x.fillStyle = '#eafff6'; x.fillText(lab, Math.min(X(n) + W * .02, W - lw - W * .02), Math.max(y0 + H * .03, Y(P[n]) - H * .05));
  }
  if (e.count) {                                       // a number that rolls to its end
    const k = 1 - Math.pow(1 - cl(u / 1.8, 0, 1), 3), v = (e.count.from || 0) + (e.count.to - (e.count.from || 0)) * k;
    const txt = money(v, e.count.prefix, e.count.suffix, Number.isInteger(e.count.to) ? 0 : 2); const fs = fitFont(x, [txt], Math.round(H * .17), W * .9);
    x.fillStyle = '#35e08a'; x.shadowColor = 'rgba(53,224,138,.7)'; x.shadowBlur = 30; x.textAlign = 'center';
    x.fillText(txt, W / 2, e.chart != null ? H * .8 : H * .58); x.shadowBlur = 0; x.textAlign = 'left';
  }
}
function chartK(e, t, prev) {                          // how far along the period the line is at t: from the last chart's point to this one's
  const from = prev != null ? prev : 0, to = e.chart === true ? 1 : +e.chart;
  return lerp(from, to, ease(cl((t - e.t0) / Math.max(.5, (e.t1 - e.t0) * .8), 0, 1)));
}
function entryAt(list, t) { let e = null, prev = null; for (const q of list || []) { if (t >= q.t0) { if (e && e.chart != null) prev = e.chart === true ? 1 : +e.chart; e = q; } } return [e, prev]; }

function screenMesh(w, h, px) {                        // a canvas-textured plane: what a screen shows
  const c = document.createElement('canvas'); c.width = px; c.height = Math.round(px * h / w);
  const tx = new T3.CanvasTexture(c); tx.encoding = T3.sRGBEncoding; tx.anisotropy = 4;
  return { c, x: c.getContext('2d'), tx, m: new T3.Mesh(new T3.PlaneGeometry(w, h), new T3.MeshBasicMaterial({ map: tx, toneMapped: false })) };
}
let DISP = null, LAP = null;
function display(x, y, z, w, h, ry) {                  // the wall display
  const s = screenMesh(w, h, 1024), f = new T3.Mesh(new T3.BoxGeometry(w + .12, h + .12, .06), std({ color: '#111314' }));
  for (const o of [f, s.m]) { o.position.set(x, y, z); o.rotation.y = ry || 0; scene.add(o); }
  s.m.translateZ(.035);
  const glow = new T3.PointLight('#7fe0c0', .5, 4.5, 1.6); glow.position.copy(s.m.position); glow.translateZ(.6); scene.add(glow);
  DISP = Object.assign(s, { pos: new T3.Vector3(x, y, z) });
}
function laptop(x, y, z, ry) {                         // a low-poly laptop facing +z (turned by ry); its screen is the LAP canvas
  const g = new T3.Group(), dark = std({ color: '#2b2f33', roughness: .5 });
  const base = new T3.Mesh(new T3.BoxGeometry(.36, .02, .25), dark); base.position.set(0, .01, 0); g.add(base);
  const keys = new T3.Mesh(new T3.PlaneGeometry(.3, .12), std({ color: '#15181a' })); keys.rotation.x = -Math.PI / 2; keys.position.set(0, .021, .02); g.add(keys);
  const lid = new T3.Group(); lid.position.set(0, .02, -.12); lid.rotation.x = -.28; g.add(lid);
  const back = new T3.Mesh(new T3.BoxGeometry(.36, .23, .012), dark); back.position.set(0, .115, 0); lid.add(back);
  const s = screenMesh(.33, .2, 800); s.m.position.set(0, .115, .007); lid.add(s.m);
  const glow = new T3.PointLight('#9fe8d0', .35, 1.6, 2); glow.position.set(0, .2, .25); g.add(glow);
  g.position.set(x, y, z); g.rotation.y = ry || 0; scene.add(g);
  g.updateMatrixWorld(true); const pos = new T3.Vector3(); s.m.getWorldPosition(pos);
  LAP = Object.assign(s, { pos });
}
function drawScreens(t) {
  if (DISP) { const [e, p] = entryAt(R.screen, t); paint(DISP.x, DISP.c.width, DISP.c.height, e, t, p); DISP.tx.needsUpdate = true; }
  if (LAP) { const [e, p] = entryAt(R.lap, t); paint(LAP.x, LAP.c.width, LAP.c.height, e || { t0: -9, t1: -8, chart: 1 }, t, p); LAP.tx.needsUpdate = true; }
}
const SETS = {
  async office() {                                     // a trading office: rows of desks with charts, the window at the back
    const W = 9, D = 16, H = 3.4; room(W, D, H, '#8fa09c');
    scene.add(new T3.HemisphereLight('#b9cac6', '#3d3128', .55)); scene.fog = new T3.Fog('#2e3532', 10, 28);
    windowLight(W / 2 - .02, 1.8, -3.2, 3.6, 1.5, -Math.PI / 2); display(0, 1.8, -D / 2 + .03, 2.6, 1.5, 0);
    for (const z of [-5, -1, 3]) await lamp(0, z, H, z === -1);
    let k = 0;
    for (const z of [-5.5, -2.5, .5]) for (const x of [-2.6, 2.6]) {
      await prop('desk', { x, z, w: 1.7 });
      if (x === -2.6 && z === .5) laptop(x, .885, z + .26, 0); else { const mo = await prop('monitor', { x, y: .76, z: z - .25, h: .48 }); await screenOn(mo, ++k * 7, k % 2); }
      await prop('office_chair', { x, z: z + (x === -2.6 && z === .5 ? .6 : .75), h: 1.0, ry: Math.PI });
    }
    await prop('houseplant', { x: -3.9, z: -7.2, h: 1.4 }); await prop('houseplant_2', { x: 3.9, z: 4.5, h: 1.2 }); await prop('houseplant_3', { x: -3.9, z: 5.5, h: 1.1 });
    for (const z of [-3.6, -.4, 2.8]) { await prop('bookshelf', { x: 4.15, z, h: 2.1, ry: -Math.PI / 2 }); await prop('shelf_small', { x: -4.2, z: z + .6, h: 1.1, ry: Math.PI / 2 }); }
    for (const [x, z, ry, w] of [[-4.48, -3, Math.PI / 2, 1.6], [-4.48, 1.2, Math.PI / 2, 1.2], [4.48, -5.6, -Math.PI / 2, 1.3]]) wallChart(x, 1.75, z, w, ry, z | 0);
    await prop('mug_with_office_tool', { x: -2.1, y: .76, z: -2.4, h: .14 });
    return { W, D, H };
  },
  async home() {                                       // a small flat in the evening: a couch, the TV with a chart, the laptop desk
    const W = 7, D = 11, H = 2.9; room(W, D, H, '#a39a8c');
    scene.add(new T3.HemisphereLight('#c7c0b4', '#3d3128', .5)); scene.fog = new T3.Fog('#2f2b27', 8, 22);
    windowLight(W / 2 - .02, 1.6, -3.6, 2.0, 1.3, -Math.PI / 2); display(0, 1.55, -D / 2 + .03, 2.0, 1.2, 0);
    for (const z of [-2.5, 2]) await lamp(0, z, H, z === -2.5);
    await prop('shelf_small', { x: 0, z: -D / 2 + .35, w: 1.7 });
    await prop('couch_large', { x: 0, z: -1.2, w: 2.3, ry: Math.PI });
    await prop('desk_2', { x: -2.6, z: -3.6, w: 1.4, ry: Math.PI / 2 }); laptop(-2.5, .76, -3.6, Math.PI / 2);
    await prop('office_chair', { x: -1.9, z: -3.6, h: 1.0, ry: -Math.PI / 2 });
    await prop('houseplant', { x: 3.0, z: -4.9, h: 1.3 }); await prop('potted_plant', { x: -3.1, z: 3.8, h: 1.0 }); await prop('bookshelf', { x: 3.25, z: 1.2, h: 1.9, ry: -Math.PI / 2 });
    wallChart(-3.48, 1.6, .8, 1.0, Math.PI / 2, 7); wallChart(-3.48, 1.65, -1.6, .8, Math.PI / 2, 9);
    await prop('bookshelf', { x: -3.25, z: 3.0, h: 1.9, ry: Math.PI / 2 }); await prop('shelf_small', { x: 3.3, z: -1.6, h: 1.0, ry: -Math.PI / 2 });
    await prop('houseplant_2', { x: 3.3, z: -1.6, y: 1.0, h: .5 }); await prop('couch_small', { x: 2.6, z: 3.6, w: 1.4, ry: -Math.PI / 2 });
    await prop('potted_plant_2', { x: -3.0, z: -4.9, h: 1.2 }); await prop('chair', { x: 1.5, z: -4.6, h: .9, ry: Math.PI * .8 });
    for (const [x, z, ry, w, s] of [[3.48, 3.4, -Math.PI / 2, .9, 3], [3.48, 0.2, -Math.PI / 2, .7, 5], [-1.6, -5.48, 0, .7, 11]]) poster(x, 1.7, z, w, ry, s);
    return { W, D, H };
  },
  async shop() {                                       // a corner shop: the exemplar's own place
    const W = 8, D = 14, H = 3.3; room(W, D, H, '#9aa49a');
    scene.add(new T3.HemisphereLight('#bfcac4', '#3d3128', .55)); scene.fog = new T3.Fog('#2f3431', 9, 26);
    windowLight(2.75, 1.7, -D / 2 + .02, 1.6, 1.4); display(0, 2.1, -D / 2 + .03, 2.2, 1.15, 0);
    for (const z of [-4, 0, 4]) await lamp(0, z, H, z === 0);
    for (const z of [-4.5, -1.5, 1.5]) { await prop('shelf_tall', { x: -3.4, z, h: 2.1, ry: Math.PI / 2 }); await prop('shelf_tall', { x: 3.4, z, h: 2.1, ry: -Math.PI / 2 }); }
    await prop('counter_straight', { x: 0, z: -5.4, w: 2.4 }); await prop('bottles', { x: -.5, y: .95, z: -5.4, h: .35 });
    return { W, D, H };
  },
};

// ---------- the reel: the set, the cast, the one camera move, the dive into the laptop, tags, captions and cards
let cast = [], ready = false;
window.ready = (async () => {
  await document.fonts.ready;
  await SETS[R.set || 'office']();
  let n = 0;
  for (const a of R.actors || []) { const p = await person(Object.assign({ n: n++ }, a)); cast.push(p); }
  ready = true;
})().catch(e => { document.title = 'ERR ' + e.message; throw e; });

// An actor at time t: where it stands, which way it faces, which clip at which point. a.path: [[t, x, z], ...] (walks
// between points, faces where it walks); a.acts: [[t, clip], ...]; a.faceAt: [[t, radians]] (the way to face on arriving).
function pose(p, t) {
  const a = p.o, P = a.path || [[0, a.x || 0, a.z || 0]];
  let i = 0; while (i < P.length - 1 && t >= P[i + 1][0]) i++;
  const A = P[i], B = P[i + 1] || A, k = B === A ? 0 : cl((t - A[0]) / Math.max(.01, B[0] - A[0]), 0, 1);
  const x = lerp(A[1], B[1], k), z = lerp(A[2], B[2], k), moving = B !== A && k >= 0 && k < 1 && t >= A[0];
  let face = a.face != null ? a.face : 0;
  if (moving) face = Math.atan2(B[1] - A[1], B[2] - A[2]);
  else if (a.faceAt) {                                  // arrived: turn from the walk's way to the place's own way over 0.6 s
    const walked = i > 0 ? Math.atan2(A[1] - P[i - 1][1], A[2] - P[i - 1][2]) : (a.face || 0);
    const Fq = a.faceAt.filter(q => q[0] <= t).pop(); face = walked;
    if (Fq) { let d = Fq[1] - walked; d = Math.atan2(Math.sin(d), Math.cos(d)); face = walked + d * cl((t - Math.max(A[0], Fq[0])) / .6, 0, 1); }
  }
  const acts = a.acts || [[0, 'Idle']]; let j = 0; while (j < acts.length - 1 && t >= acts[j + 1][0]) j++;
  return { x, z, face, clip: acts[j][1], since: t - acts[j][0], prev: j > 0 ? acts[j - 1][1] : null, pt: j > 0 ? t - acts[j - 1][0] : 0 };
}
const SEAT = R.seat || { y: -.08, back: .05 };          // the Sitting clip's hips over the chair (tuned on stills)
const TYPE = R.typePose || { ua: -.9, la: -.9, spread: .25 };
function drawCast(t) {
  for (const p of cast) {
    const s = pose(p, t), typing = s.clip === 'Type', clip = typing ? 'Sitting' : s.clip;
    p.root.position.set(s.x, /Sitting/.test(clip) ? SEAT.y : 0, s.z); p.root.rotation.y = s.face;
    p.mixer.stopAllAction();
    const play = (name, time, w) => { const c = p.clips[name] || p.clips.Idle || Object.values(p.clips)[0]; const ac = p.mixer.clipAction(c); ac.reset(); ac.play(); ac.time = c.duration ? (/Sitting/.test(name) ? c.duration * .5 : /Death/.test(name) ? Math.min(time, c.duration - .01) : time % c.duration) : 0; ac.setEffectiveWeight(w); };
    const prevClip = s.prev === 'Type' ? 'Sitting' : s.prev, fade = /Sitting/.test(clip) && /Sitting/.test(prevClip || '') ? 1 : cl(s.since / .35, 0, 1);
    play(clip, s.since, fade); if (prevClip && fade < 1) play(prevClip, s.pt, 1 - fade);
    p.mixer.update(0);
    if (typing) {                                       // hands to the keys, tapping (the clips have no typing: posed here)
      if (!p.bones) { p.bones = {}; p.root.traverse(b => { if (b.isBone) p.bones[b.name] = b; }); }
      for (const [side, ph] of [['L', 0], ['R', 1.7]]) {
        const ua = p.bones['UpperArm.' + side] || p.bones['UpperArm' + side], la = p.bones['LowerArm.' + side] || p.bones['LowerArm' + side], sg = side === 'L' ? 1 : -1;
        if (ua) { ua.rotation.x += TYPE.ua; ua.rotation.z += sg * TYPE.spread; }
        if (la) la.rotation.x += TYPE.la + .12 * Math.sin(t * 17 + ph) * Math.max(0, Math.sin(t * 5.3 + ph));
      }
    }
  }
}

// The camera: keyframes [t, x, y, z, lx, ly, lz, fov] through which a Catmull-Rom curve runs, a slow drift on top, so it never
// rests (the exemplar: 0% still frames). R.look: [[t0, t1, 'wall' | 'lap' | actor index]] says what it looks at and holds sharp.
function camAt(t) {
  const K = R.cam || [[0, 0, 1.6, 6, 0, 1.4, 0], [R.T || 8, 0, 1.5, 2, 0, 1.3, -4]];
  let i = 0; while (i < K.length - 2 && t >= K[i + 1][0]) i++;
  const P0 = K[Math.max(0, i - 1)], P1 = K[i], P2 = K[Math.min(K.length - 1, i + 1)], P3 = K[Math.min(K.length - 1, i + 2)];
  const u = cl((t - P1[0]) / Math.max(.01, P2[0] - P1[0]), 0, 1), w = u * u * (3 - 2 * u);   // (smoothstep: no overshoot through a person)
  const cr = j => { const g = q => q[j] != null ? q[j] : 42; return lerp(g(P1), g(P2), w); };
  const fov = cl(cr(7), 8, 60), dr = .05 * fov / 42;
  cam.position.set(cr(1) + dr * Math.sin(t * .7), cr(2) + dr * .5 * Math.sin(t * 1.1 + 1), cr(3) + dr * Math.cos(t * .5));
  if (Math.abs(cam.fov - fov) > 1e-3) { cam.fov = fov; cam.updateProjectionMatrix(); }
  const look = new T3.Vector3(cr(4), cr(5), cr(6));
  const L = (R.look || []).find(q => t >= q[0] && t < q[1]), on = L ? L[2] : 0;
  let target = null;
  if (on === 'wall' && DISP) target = DISP.pos.clone();
  else if (on === 'lap' && LAP) target = LAP.pos.clone();
  else if (cast[on]) { const r = cast[on].root.position; look.x = lerp(look.x, r.x, .85); look.z = lerp(look.z, r.z, .85); target = new T3.Vector3(r.x, 1.4, r.z); }
  if (target && (on === 'wall' || on === 'lap')) look.copy(target);
  cam.lookAt(look); fill.position.copy(cam.position); fill.position.y += .5;
  bokeh.uniforms.focus.value = cam.position.distanceTo(target || look);
}

// The dive: as the camera zooms into the laptop, the laptop's screen becomes the whole frame (a sharp full-screen terminal),
// then hands back to the room as it pulls out. R.term: [{t0, t1, ...entry}]; 0.3 s cross-fades at both ends.
const term = document.getElementById('term'), tx2 = term.getContext('2d');
function dive(t) {
  const d = (R.term || []).find(q => t >= q.t0 - .3 && t < q.t1 + .3);
  if (!d) { term.style.opacity = 0; return false; }
  const a = Math.min(cl((t - (d.t0 - .3)) / .3, 0, 1), cl((d.t1 + .3 - t) / .3, 0, 1)); term.style.opacity = a;
  const [e, p] = entryAt(R.lap, t); tx2.fillStyle = '#06110e'; tx2.fillRect(0, 0, 1080, 1920);
  tx2.save(); tx2.translate(0, 200); paint(tx2, 1080, 1200, e || d, t, p); tx2.restore();   // (the terminal keeps to y 200-1400: the caption's band stays plain)
  return a > .5;
}

// Tags: who a character is, above the head from the moment the story turns to them (R.tags: [{who, text, t0, t1}]). Kept in
// the frame, above the caption band and clear of each other; hidden behind a card or the terminal.
const tagBox = document.getElementById('tags'), tagEls = {};
function tags(t, hidden) {
  const shown = [];
  for (const g of R.tags || []) {
    const el = tagEls[g.text] || (tagEls[g.text] = Object.assign(tagBox.appendChild(document.createElement('div')), { className: 'tag', textContent: g.text }));
    const p = cast[g.who]; let ok = !hidden && p && t >= g.t0 && t < g.t1;
    if (ok) {
      const h = new T3.Vector3(); (p.head || (p.head = (() => { let b = null; p.root.traverse(n => { if (n.isBone && n.name === 'Head_end') b = n; }); return b; })()) || p.root).getWorldPosition(h);
      if (!p.head) h.y += 1.9; h.y += .22; h.project(cam);
      let X = (h.x + 1) / 2 * 1080, Y = (1 - h.y) / 2 * 1920;
      ok = h.z < 1 && X > 60 && X < 1020 && Y > 300;
      X = cl(X, 220, 860); Y = cl(Y, 330, 1380);
      for (const q of shown) if (Math.abs(q[0] - X) < 400 && Math.abs(q[1] - Y) < 90) Y = q[1] - 100;   // (never on another tag)
      if (ok) { shown.push([X, Y]); el.style.left = X + 'px'; el.style.top = Y + 'px'; el.style.opacity = Math.min(1, (t - g.t0) / .25, (g.t1 - t) / .25); }
    }
    el.style.display = ok ? 'block' : 'none';
  }
}

// Captions: amber capitals in a black box, one line, hard swap (production.md COPY SPEC A, variant).
const capEl = document.getElementById('cap'), cardEl = document.getElementById('card');
function caption(t) {
  const c = (R.caps || []).find(c => t >= c.t0 && t < c.t1);
  capEl.style.display = c ? 'block' : 'none'; if (c && capEl.textContent !== c.text) capEl.textContent = c.text;
}
function cards(t) {                                    // a full-screen figure card: green over red, figures glowing white
  const c = (R.cards || []).find(c => t >= c.t0 && t < c.t1);
  cardEl.style.display = c ? 'flex' : 'none';
  if (c) { cardEl.querySelector('.top b').textContent = c.top; cardEl.querySelector('.bot b').textContent = c.bot;
    for (const b of cardEl.querySelectorAll('b')) b.style.fontSize = Math.min(200, Math.floor(1500 / Math.max(4, b.textContent.length))) + 'px';
    cardEl.style.opacity = Math.min((t - c.t0) / .12, (c.t1 - t) / .12, 1); }
  return !!c;
}

window.render = function (t) {
  if (!ready) throw new Error('not ready');
  drawCast(t); drawScreens(t); camAt(t); comp.render();
  const full = dive(t), card = cards(t); tags(t, full || card); caption(t);
};
})();
