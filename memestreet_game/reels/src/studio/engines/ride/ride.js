/* The studio's daily reel, "the ride": the day's mystery chart is a landscape (a ridge whose skyline IS the price line, a road
   along its edge), and what the company makes rides that road in ONE continuous shot while the story is told: every event is a
   set piece standing at its own place on the chart, and the product is there, at that price, when the narrator gets to it.
   It opens on the chart building itself with a mystery crate at its start (the Triple Hook is said over it), the crate bursts on
   the reveal, and it ends on the whole chart with the vote.
   window.__R = {T, prices, dates: [start, end], cuts: [each sentence's start], words: [[word, t0, t1, sentence]], caps, tag, name,
     color, number, product, label, reveal: sentence index, shots: [{cam, to, focus, dist, cut}], places: [{at, kind, ...}],
     band: [{i, kind: title|counter|stamp, on, text, ...}], leak: [f0, f1], storm: [f0, f1], smoke: [f0, f1], choice, vote: sentence
     index, cover}.  Everything is a pure function of t. Models: ../../../explainer/models3d.js; people: toon.js. */
(function () {
'use strict';
const T3 = THREE, R = window.__R, W = 1080, H = 1920, Q = window.__Q || 2 / 3, FONT = 'Montserrat, sans-serif', PI = Math.PI;
const cl = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x)), lerp = (a, b, k) => a + (b - a) * k, ss = x => { x = cl(x); return x * x * (3 - 2 * x); };
const eo = x => 1 - Math.pow(1 - cl(x), 4), back = x => { x = cl(x); const k = 1.9; return 1 + (k + 1) * Math.pow(x - 1, 3) + k * Math.pow(x - 1, 2); };
const hs = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }, norm = s => String(s).toLowerCase().replace(/[^a-z0-9$%]/g, '');
const cv = document.getElementById('gl'), ox = document.getElementById('c').getContext('2d');
const rn = new T3.WebGLRenderer({canvas: cv, antialias: Q >= 1, preserveDrawingBuffer: true}); rn.setSize(Math.round(W * Q), Math.round(H * Q), false); rn.setPixelRatio(1);
rn.shadowMap.enabled = true; rn.shadowMap.type = T3.PCFSoftShadowMap; T3.ColorManagement.legacyMode = false; rn.outputEncoding = T3.sRGBEncoding; rn.toneMapping = T3.ACESFilmicToneMapping; rn.toneMappingExposure = 1.02; rn.localClippingEnabled = true;
const scene = new T3.Scene(), cam = new T3.PerspectiveCamera(40, W / H, .3, 3000);

// ---------------------------------------------------------------- what models3d.js needs from its host
let sctx = ox;
const S = {ctx(x) { const o = sctx; sctx = x; return o; },
  shade(hex, k) { const c = new T3.Color(hex || '#888888'), t = k < 0 ? 0 : 1, a = Math.abs(k); return '#' + new T3.Color(lerp(c.r, t, a), lerp(c.g, t, a), lerp(c.b, t, a)).getHexString(); },
  txt(s, x, y, size, color, max = 9e9, weight = 800, align = 'center') { const c = sctx; c.font = `${weight} ${size}px ${FONT}`; const w = c.measureText(s).width; if (w > max) c.font = `${weight} ${size * max / w}px ${FONT}`; c.textAlign = align; c.textBaseline = 'middle'; c.fillStyle = color; c.fillText(s, x, y); }};
function canvasTex(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; const x = c.getContext('2d'); if (draw) draw(x, w, h); const t = new T3.CanvasTexture(c); t.encoding = T3.sRGBEncoding; t.anisotropy = 8; t.userData = {c, x}; return t; }
const glowM = (col, k = 1.5) => new T3.MeshBasicMaterial({color: new T3.Color(col).multiplyScalar(k)});
function label(text, w, h, fg = '#fff', bg = '#14182b', px = 160) { const t = canvasTex(Math.round(px * w / h), px, (x, cw, ch) => { x.fillStyle = bg; x.fillRect(0, 0, cw, ch); const o = S.ctx(x); S.txt(String(text).toUpperCase(), cw / 2, ch / 2 + 4, ch * .6, fg, cw * .9, 900); S.ctx(o); }); return new T3.Mesh(new T3.PlaneGeometry(w, h), new T3.MeshBasicMaterial({map: t})); }
const MOD = window.Models3D({T3, S, rn, canvasTex, label, glowM}), TOON = window.Toon(S);
const M = (col, o = {}) => new T3.MeshStandardMaterial(Object.assign({color: col, roughness: .8}, o));
const mk = (g, m, sh = true) => { const x = new T3.Mesh(g, m); x.castShadow = sh; x.receiveShadow = true; return x; }, at = (m, x, y, z) => { m.position.set(x, y, z); return m; };

// ---------------------------------------------------------------- the chart as a landscape
const P0 = R.prices, n = P0.length - 1, lo = Math.min(...P0), hi = Math.max(...P0), hiI = P0.indexOf(hi), loI = P0.lastIndexOf(lo);
const L = 170, HH = Math.max(16, Math.min(46, 46 * Math.log(hi / lo) / Math.log(4))), BASE = 8, RW = 7, DEEP = 46,      // (the hills are as tall as the move was big: a 30% chart is gentle, a tenfold one a mountain)
  HH_ = 0, COL = R.color || '#2f7cf6', up = P0[n] >= P0[0];
const KN = hi / lo < 1.6 ? 16 : 26, keep = new Set([0, n, hiI, loI]); for (let k = 1; k < KN; k++) keep.add(Math.round(k / KN * n));      // (a small move is smoothed more: its daily noise is not a landscape)
const KI = [...keep].sort((a, b) => a - b), KY = KI.map(i => BASE + (P0[i] - lo) / (hi - lo || 1) * HH);
function yAt(f) {                    // the road's height at a fraction of the chart: a smooth line through the kept days (the high and the low among them)
  const x = cl(f) * n; let k = 0; while (k < KI.length - 2 && KI[k + 1] < x) k++;
  const s = cl((x - KI[k]) / (KI[k + 1] - KI[k])), a = KY[Math.max(0, k - 1)], b = KY[k], c = KY[k + 1], d = KY[Math.min(KY.length - 1, k + 2)];
  return .5 * ((2 * b) + (-a + c) * s + (2 * a - 5 * b + 4 * c - d) * s * s + (-a + 3 * b - 3 * c + d) * s * s * s); }
const slope = f => (yAt(f + .002) - yAt(f - .002)) / (.004 * L), priceAt = f => { const x = cl(f) * n, i = Math.min(n - 1, Math.floor(x)); return lerp(P0[i], P0[i + 1], x - i); };
const F = v => v === 'peak' ? hiI / n : v === 'low' ? loI / n : v === 'end' ? 1 : v === 'start' ? 0 : +v;
const grow = new T3.Plane(new T3.Vector3(-1, 0, 0), 1e9);          // the hook: the landscape builds itself from the left
{ const NS = 900, f0 = -.16, f1 = 1.14, road = [], land = [], face = [], ruv = [], luv = [], fuv = [], idx = [];
  for (let i = 0; i <= NS; i++) { const f = lerp(f0, f1, i / NS), x = f * L, y = yAt(f);
    road.push(x, y, RW / 2, x, y, -RW / 2); ruv.push(x / 9, 0, x / 9, 1); land.push(x, y - .02, -RW / 2, x, y - .02, -DEEP); luv.push(x / 12, 0, x / 12, 4);
    face.push(x, y, RW / 2, x, 0, RW / 2); fuv.push(x / L, y / (BASE + HH + 2), x / L, 0);
    if (i < NS) { const a = i * 2; idx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); } }
  const geo = (p, uv) => { const g = new T3.BufferGeometry(); g.setAttribute('position', new T3.Float32BufferAttribute(p, 3)); g.setAttribute('uv', new T3.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals(); return g; };
  const asph = canvasTex(256, 128, (x, w, h) => { x.fillStyle = '#3b3f52'; x.fillRect(0, 0, w, h); for (let k = 0; k < 500; k++) { x.fillStyle = hs(k) > .5 ? '#454a5f' : '#343849'; x.fillRect(hs(k + 1) * w, hs(k + 2) * h, 3, 2); }
    x.fillStyle = '#f4f1e6'; x.fillRect(0, 6, w, 5); x.fillRect(0, h - 11, w, 5); x.fillStyle = '#ffc83d'; x.fillRect(20, h / 2 - 4, 120, 8); }); asph.wrapS = T3.RepeatWrapping;
  const grass = canvasTex(128, 128, (x, w, h) => { x.fillStyle = up ? '#58b368' : '#6aa972'; x.fillRect(0, 0, w, h); for (let k = 0; k < 260; k++) { x.fillStyle = hs(k) > .5 ? '#66c477' : '#4a9d5a'; x.fillRect(hs(k + 5) * w, hs(k + 9) * h, 4, 4); } }); grass.wrapS = grass.wrapT = T3.RepeatWrapping;
  const step = [.1, .25, .5, 1, 2, 5, 10, 25, 50, 100].find(s => (hi - lo) / s <= 7) || 100;
  const wallT = canvasTex(64, 1024, (x, w, h) => { const g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, S.shade(COL, .12)); g.addColorStop(.5, S.shade(COL, -.25)); g.addColorStop(1, S.shade(COL, -.62)); x.fillStyle = g; x.fillRect(0, 0, w, h);
    x.fillStyle = 'rgba(255,255,255,.34)'; for (let p = Math.ceil(lo / step) * step; p <= hi + 1e-9; p += step) { const y = BASE + (p - lo) / (hi - lo || 1) * HH; x.fillRect(0, h - y / (BASE + HH + 2) * h - 2, w, 4); } });
  const cp = {clippingPlanes: [grow]};
  const r1 = mk(geo(road, ruv), new T3.MeshStandardMaterial(Object.assign({map: asph, roughness: .85}, cp)), false), l1 = mk(geo(land, luv), new T3.MeshStandardMaterial(Object.assign({map: grass, roughness: 1}, cp)), false);
  const w1 = mk(geo(face, fuv), new T3.MeshStandardMaterial(Object.assign({map: wallT, roughness: .7, side: T3.DoubleSide}, cp)), false); scene.add(r1, l1, w1);
  const top = []; for (let i = 0; i <= 400; i++) { const f = i / 400; top.push(new T3.Vector3(f * L, yAt(f) - .34, RW / 2 + .14)); }      // the price line itself, a bright edge on the cliff
  scene.add(mk(new T3.TubeGeometry(new T3.CatmullRomCurve3(top), 800, .2, 6), new T3.MeshBasicMaterial(Object.assign({color: new T3.Color(up ? '#2bd47d' : '#ff4a5c').multiplyScalar(1.5)}, cp)), false)); }
// sky, sun, ground, far town, clouds, trees on the land
const skyT = canvasTex(8, 512, (x, w, h) => { const g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#2c5fe0'); g.addColorStop(.48, '#86bcff'); g.addColorStop(.66, '#ffe2bd'); g.addColorStop(1, '#ffc08a'); x.fillStyle = g; x.fillRect(0, 0, w, h); });
const stormT = canvasTex(8, 512, (x, w, h) => { const g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#181c33'); g.addColorStop(.5, '#3a3f5c'); g.addColorStop(.7, '#6b5f78'); g.addColorStop(1, '#8a6a70'); x.fillStyle = g; x.fillRect(0, 0, w, h); });
const sky = new T3.Mesh(new T3.SphereGeometry(1600, 32, 16), new T3.MeshBasicMaterial({map: skyT, side: T3.BackSide, fog: false})), sky2 = new T3.Mesh(new T3.SphereGeometry(1590, 32, 16), new T3.MeshBasicMaterial({map: stormT, side: T3.BackSide, fog: false, transparent: true, opacity: 0})); scene.add(sky, sky2);
scene.fog = new T3.Fog('#ffd9bb', 220, 1300); const hemi = new T3.HemisphereLight('#dcebff', '#7a8f5a', .95), sun = new T3.DirectionalLight('#fff0d2', 2.3); scene.add(hemi, sun, sun.target);
Object.assign(sun.shadow.camera, {left: -38, right: 38, top: 38, bottom: -38, near: 1, far: 260}); sun.shadow.mapSize.set(2048, 2048); sun.shadow.bias = -.0005; sun.castShadow = true;
const ground = mk(new T3.PlaneGeometry(5000, 5000), M('#8fc47a'), false); ground.rotation.x = -PI / 2; ground.position.set(L / 2, 0, 0); scene.add(ground);
for (let k = 0; k < 30; k++) { const w = 9 + hs(k) * 12, h = 16 + hs(k + 3) * 46, col = ['#f09a7c', '#7fbfe8', '#f5d37a', '#b79ae8', '#7fd3a8'][k % 5];
  const t = canvasTex(64, 128, (x, cw, ch) => { x.fillStyle = col; x.fillRect(0, 0, cw, ch); for (let r = 0; r < 9; r++) for (let c = 0; c < 4; c++) { x.fillStyle = hs(k * 31 + r * 7 + c) > .3 ? '#eaf5ff' : S.shade(col, -.3); x.fillRect(7 + c * 14, 6 + r * 13, 9, 9); } });
  scene.add(at(mk(new T3.BoxGeometry(w, h, w), [M(col), M(col), M(col), M(col), new T3.MeshStandardMaterial({map: t}), M(col)], false), -40 + k * 8.4 + hs(k + 9) * 4, h / 2, -DEEP - 60 - (k % 3) * 34)); }
for (let k = 0; k < 16; k++) { const c = new T3.Group(); for (let j = 0; j < 4; j++) c.add(at(new T3.Mesh(new T3.SphereGeometry(7 + hs(k * 7 + j) * 6, 12, 8), new T3.MeshBasicMaterial({color: '#ffffff', fog: false, transparent: true, opacity: .92})), j * 9 - 14, hs(k + j) * 4, 0)); scene.add(at(c, -80 + k * 22, BASE + HH + 26 + hs(k + 3) * 50, -DEEP - 40 - hs(k + 9) * 240)); }
for (let k = 0; k < 44; k++) { const f = -.1 + k / 43 * 1.2, z = -RW / 2 - 9 - hs(k) * 30, s = 1.6 + hs(k + 4) * 1.6, g = new T3.Group();
  g.add(at(mk(new T3.CylinderGeometry(.22 * s, .3 * s, 1.6 * s, 7), M('#7a5230')), 0, .8 * s, 0)); g.add(at(mk(new T3.IcosahedronGeometry(1.25 * s, 1), M(hs(k + 2) > .5 ? '#3f9d55' : '#55b869', {flatShading: true})), 0, 2.4 * s, 0)); g.position.set(f * L, yAt(f), z); g.userData.f = f; scene.add(g); (scene.userData.grown = scene.userData.grown || []).push(g); }

// ---------------------------------------------------------------- the hero: the product on the road (a car or a van drives itself; anything else rides a trolley)
const hero = new T3.Group(), body = new T3.Group(), wheels = []; hero.add(body); scene.add(hero);
{ const kind = R.product || 'box', p = MOD.product(kind, COL, R.label || ''), SC = 2.25;
  if (kind === 'car' || kind === 'van') { p.scale.setScalar(SC); body.add(p); p.userData.late.slice(-4).forEach(w => wheels.push([w, .155 * SC])); hero.userData.len = 2 * SC; hero.userData.top = (kind === 'van' ? 1.02 : .7) * SC; }
  else { const b = new T3.Box3().setFromObject(p), sz = b.getSize(new T3.Vector3()), s = 2.3 / Math.max(sz.x, sz.y * 1.1), deck = MOD.rbox(4.4, .28, 2.9, .08, MOD.PM('#2b2f3a', {roughness: .4})); p.scale.setScalar(s);
    body.add(at(deck, 0, .78, 0)); body.add(at(MOD.rbox(4.5, .1, 3, .04, MOD.GOLD), 0, .95, 0)); p.position.y = 1.0; body.add(p);
    for (const [x, z] of [[-1.5, 1.25], [1.5, 1.25], [-1.5, -1.25], [1.5, -1.25]]) { const w = new T3.Group(); w.add(MOD.cyl(.52, .52, .36, MOD.RUBBER, 24, 'z'), MOD.cyl(.3, .3, .4, MOD.CHROME, 16, 'z')); for (let k = 0; k < 4; k++) { const sp = MOD.box(.5, .1, .42, MOD.STEEL); sp.rotation.z = k * PI / 4; w.add(sp); } body.add(at(w, x, .52, z)); wheels.push([w, .52]); }
    hero.userData.len = 4.4; hero.userData.top = 1 + sz.y * s; }
  hero.traverse(m => { if (m.isMesh) m.castShadow = true; }); }
// the mystery crate over it until the reveal
const crate = new T3.Group(), planks = []; scene.add(crate);
{ const cw = hero.userData.len + 1.6, ch = hero.userData.top + 1.3, cd = 4.6, WOOD = MOD.PM('#c9955a', {roughness: .8, envMapIntensity: .15}), DARK = MOD.PM('#8a5f33', {roughness: .8});
  const q = canvasTex(256, 256, (x, w, h) => { x.fillStyle = '#c9955a'; x.fillRect(0, 0, w, h); x.fillStyle = 'rgba(90,55,20,.25)'; for (let k = 0; k < 6; k++) x.fillRect(0, k * 43, w, 4); const o = S.ctx(x); S.txt('???', w / 2, h / 2 + 6, 150, '#3a2410', w * .9, 900); S.ctx(o); }), QM = new T3.MeshStandardMaterial({map: q, roughness: .8});
  for (const [w, h, d, x, y, z, m] of [[cw, ch, .25, 0, ch / 2, cd / 2, QM], [cw, ch, .25, 0, ch / 2, -cd / 2, WOOD], [.25, ch, cd, cw / 2, ch / 2, 0, QM], [.25, ch, cd, -cw / 2, ch / 2, 0, QM], [cw + .3, .25, cd + .3, 0, ch, 0, WOOD]]) {
    const pl = mk(new T3.BoxGeometry(w, h, d), m.map ? [WOOD, WOOD, WOOD, WOOD, w > 1 ? m : WOOD, w > 1 ? WOOD : WOOD].map((mm, k) => (w > 1 ? (k === 4 || k === 5) : (k === 0 || k === 1)) ? m : mm) : m); pl.position.set(x, y, z); pl.userData.home = pl.position.clone(); pl.userData.out = new T3.Vector3(x, y - ch / 2 + 3, z).normalize(); crate.add(pl); planks.push(pl); }
  for (const x of [-cw / 2, cw / 2]) for (const z of [-cd / 2, cd / 2]) { const e = mk(new T3.BoxGeometry(.4, ch + .1, .4), DARK); e.position.set(x, ch / 2, z); e.userData.home = e.position.clone(); e.userData.out = new T3.Vector3(x, 2, z).normalize(); crate.add(e); planks.push(e); } }

// ---------------------------------------------------------------- the set pieces: each stands at its own place on the chart
const PLACES = [];
function sprite(look, color, seed, pose) { const tex = canvasTex(TOON.W, TOON.H), sp = new T3.Sprite(new T3.SpriteMaterial({map: tex, transparent: true, alphaTest: .35})), hgt = 4.2; sp.center.set(.5, 0); sp.scale.set(hgt * TOON.W / TOON.H, hgt, 1);
  const p = {look, color, pose, seed, mir: false, glasses: false, tache: seed % 3 === 1}; return {sp, tick: t => { TOON.draw(tex.userData.x, p, t); tex.needsUpdate = true; }}; }
function board(text, sub, col) { const g = new T3.Group(), w = 9.4, h = 5, t = canvasTex(768, 410, (x, cw, ch) => { x.fillStyle = col; x.fillRect(0, 0, cw, ch); x.fillStyle = 'rgba(0,0,0,.18)'; x.fillRect(0, ch * .66, cw, ch * .34); const o = S.ctx(x);
    S.txt(String(text).toUpperCase(), cw / 2, ch * (sub ? .36 : .5), ch * (sub ? .38 : .46), '#ffffff', cw * .9, 900); if (sub) S.txt(String(sub).toUpperCase(), cw / 2, ch * .83, ch * .19, '#ffe9a8', cw * .9, 800); S.ctx(o); });
  g.add(at(MOD.rbox(w + .5, h + .5, .4, .1, MOD.PM('#1b2038', {roughness: .4})), 0, 5 + h / 2, 0)); g.add(at(new T3.Mesh(new T3.PlaneGeometry(w, h), new T3.MeshBasicMaterial({map: t})), 0, 5 + h / 2, .22));
  for (const x of [-3.2, 3.2]) g.add(at(MOD.cyl(.22, .28, 5.2, MOD.STEEL, 12), x, 2.6, -.1)); for (const x of [-3.6, 0, 3.6]) g.add(at(MOD.ball(.2, MOD.PM('#fff3c4', {emissive: '#ffe9a8', emissiveIntensity: 2})), x, 5 + h + .5, .5)); return g; }
function place(pl) { const f = F(pl.at), g = new T3.Group(), ticks = []; let z = -RW / 2 - 4, ry = 0;
  if (pl.kind === 'board') g.add(board(pl.text, pl.sub, pl.color || COL));
  else if (pl.kind === 'arch') { z = 0; ry = 0; const col = pl.color || COL, lab = label(pl.text, 8.4, 2.1, '#fff', col); lab.rotation.y = -PI / 2; g.add(at(lab, -.36, 9.3, 0));
    g.add(at(MOD.rbox(.7, 2.6, RW + 3.2, .12, MOD.PM(col, {roughness: .4})), 0, 9.3, 0)); for (const s of [-1, 1]) { g.add(at(MOD.rbox(.7, 10.6, .7, .12, MOD.PM('#f4f2ec', {roughness: .5})), 0, 5.3, s * (RW / 2 + 1.2))); for (let k = 0; k < 4; k++) g.add(at(MOD.box(.74, .5, .74, MOD.PM(col, {roughness: .4})), 0, 1 + k * 2.4, s * (RW / 2 + 1.2))); } }
  else if (pl.kind === 'crowd') { z = -RW / 2 - 3.4; ry = 0; const cols = ['#e8394a', '#2f7cf6', '#9b59d0', '#22b573', '#f28c28'], looks = ['casual', 'woman', 'hoodie', 'woman', 'casual'];
    for (let k = 0; k < 5; k++) { const s = sprite(looks[k], cols[k], k + 3 + (pl.seed || 0), pl.pose || 'cheer'); s.sp.position.set((k - 2) * 2.3, 0, -(k % 2) * 1.4); g.add(s.sp); ticks.push(s.tick); } }
  else if (pl.kind === 'person') { z = -RW / 2 - 3; ry = 0; const s = sprite(pl.look || 'suit', pl.color || '#2b6cb0', pl.seed || 4, pl.pose || 'point'); s.sp.scale.multiplyScalar(1.25); g.add(s.sp); ticks.push(s.tick);
    if (pl.text) { const t = label(pl.text, 5.6, 1, '#15162b', '#ffffff', 120); g.add(at(t, 0, 6.3, 0)); } }
  else { z = -RW / 2 - 5; ry = .3; let m;                                                              // a thing: the same realistic models as the story reel, large
    if (pl.kind === 'cash') { m = MOD.cash(); m.scale.setScalar(3.4); }
    else if (pl.kind === 'parcels') { m = new T3.Group(); for (const [x, y, zz, r] of [[-2.1, 0, 0, .1], [2.1, 0, 0, -.12], [0, 2.9, 0, .06]]) { const b = MOD.parcel(pl.text || ''); b.scale.setScalar(3.6); b.position.set(x, y, zz); b.rotation.y = r; m.add(b); } }
    else if (pl.kind === 'tv') { m = new T3.Group(); const tv = MOD.tv(3, 1.95, 1.025); tv.scale.setScalar(2.3); m.add(at(tv, 0, 4.6, 0));
      const t = canvasTex(448, 280, (x, cw, ch) => { x.fillStyle = '#16204a'; x.fillRect(0, 0, cw, ch); x.fillStyle = '#e8394a'; x.fillRect(0, 0, cw, ch * .22); const o = S.ctx(x); S.txt('BREAKING', cw / 2, ch * .12, ch * .15, '#fff', cw * .9, 900); (pl.lines || []).slice(0, 3).forEach((l, i) => S.txt(String(l).toUpperCase(), cw / 2, ch * (.42 + i * .22), ch * .17, '#fff', cw * .9, 900)); S.ctx(o); });
      m.add(at(new T3.Mesh(new T3.PlaneGeometry(2.8 * 2.3, 1.75 * 2.3), new T3.MeshBasicMaterial({map: t})), 0, 4.6, .19)); }
    else { m = MOD.product(pl.kind, pl.color || COL, pl.text || ''); const b = new T3.Box3().setFromObject(m), s = 5 / Math.max(b.getSize(new T3.Vector3()).x, b.getSize(new T3.Vector3()).y); m.scale.setScalar(s); }
    g.add(m); if (pl.tag) g.add(at(label(pl.tag, 6.4, 1.5, '#15162b', '#ffc83d', 140), 0, 9.6, 0)); }
  g.traverse(m => { if (m.isMesh) m.castShadow = true; }); const dx = pl.kind === 'arch' ? 0 : 1.5; g.position.set(f * L + dx, yAt(f + dx / L), pl.z != null ? pl.z : z); g.rotation.y = pl.ry != null ? pl.ry : ry; scene.add(g);      // (a sign stands a little ahead of its moment, so the camera behind the product sees it)
  PLACES.push({pl, f, g, ticks}); }
(R.places || []).forEach(place);

// ---------------------------------------------------------------- time: where the product is, and what the camera does, sentence by sentence
const CUT = R.cuts, NSH = CUT.length, SH = R.shots, T = R.T, t0 = i => CUT[Math.min(i, NSH - 1)], t1 = i => i + 1 < NSH ? CUT[i + 1] : T;
const REV = R.reveal != null ? R.reveal : 0, REVT = (() => { const w = (R.words || []).filter(w => w[3] === REV && norm(R.name) && norm(w[0]).startsWith(norm(R.name).slice(0, 5))); return w.length ? w[0][1] - .08 : t0(REV) + .6; })();
const TO = []; { let f = 0; for (let i = 0; i < NSH; i++) { const a = f; if (SH[i] && SH[i].to != null) f = F(SH[i].to); TO.push([a, f]); } }
function heroF(t) { let i = 0; while (i < NSH - 1 && t >= CUT[i + 1]) i++; const [a, b] = TO[i]; if (a === b) return a; return lerp(a, b, ss((t - t0(i)) / Math.max(.2, .62 * (t1(i) - t0(i))))); }      // (it gets to the sentence's place early and lingers there while the narrator explains it)
const FT = []; for (let k = 0; k <= Math.ceil(T * 30); k++) FT.push(heroF(k / 30));
const tAt = f => { for (let k = 1; k < FT.length; k++) if (FT[k] >= f) return (k - 1 + (f - FT[k - 1]) / Math.max(1e-9, FT[k] - FT[k - 1])) / 30; return T + 9; };          // when the product reaches a place
PLACES.forEach(p => { p.t = tAt(p.f); p.tin = p.pl.kind === 'arch' || t0(REV + 1) > tAt(Math.max(0, p.f - .1)) ? -9 : tAt(Math.max(0, p.f - .1)); if (p.pl.show != null) p.tin = t0(p.pl.show) + .15; });
const wordT = (i, on) => { const w = (R.words || []).filter(w => w[3] === i && on && norm(w[0]).startsWith(norm(on))); return w.length ? w[0][1] - .06 : t0(i) + .25; };
const BAND = (R.band || []).map(b => Object.assign({}, b, {t: b.t != null ? b.t : wordT(b.i, b.on), end: b.end != null ? b.end : t1(b.until != null ? b.until : b.i)}));
const VOTE = R.vote != null ? t0(R.vote) : T + 9, LEAK = R.leak ? R.leak.map(F) : null, STORM = R.storm ? R.storm.map(F) : null, SMOKE = R.smoke ? R.smoke.map(F) : null;
const heroPos = f => new T3.Vector3(f * L, yAt(f), 0);
function pose(i, t) {                // a shot's camera: [position, target, fov]
  const s = SH[i] || {}, f = heroF(t), p = heroPos(f), lt = t - t0(i), k = s.cam || 'chase', D = s.dist || 1;
  const over = (x, h) => yAt(x / L) + h; let sx = 0; PLACES.forEach(q => { const d = q.g.position.x - p.x; if (t >= q.tin && q.pl.kind !== 'arch' && Math.abs(d) < 14 && (!sx || Math.abs(d) < Math.abs(sx))) sx = d; }); sx *= .5;      // (a sign that is up pulls the frame halfway toward it)               // (a camera never sits inside the hill: at least h over the road where it stands)
  if (k === 'wide') { const a = s.focus ? F(s.focus[0]) : .5, b = s.focus ? F(s.focus[1]) : .5, u = ss(lt / Math.max(.3, t1(i) - t0(i))), fc = lerp(a, b, u), d = lerp((s.d0 || 330) * D, (s.d1 || s.d0 || 330) * D, u);
    const P = new T3.Vector3(fc * L, BASE + HH * .5, d), Q = new T3.Vector3(fc * L, lerp(yAt(fc), BASE + HH * .46, cl(d / 300)), 0);
    if (s.open) { const c = heroPos(0), w = ss(lt / (s.open * (t1(i) - t0(i)))); return [new T3.Vector3(c.x + 10, c.y + 7.5, 23).lerp(P, w), new T3.Vector3(c.x + .4, c.y + 3.1, 0).lerp(Q, w), lerp(44, 38, w)]; }      // (the opening: close on the mystery crate, three-quarters on, then out to the whole chart)
    return [P, Q, 38]; }
  if (k === 'side') return [new T3.Vector3(p.x + .3 + sx, p.y + 4.4, (26 - lt * .6) * D + Math.abs(sx)), new T3.Vector3(p.x + .3 + sx, p.y + 3.6, 0), 38];          // (a tall frame is narrow: the product is centred and far enough to fit across it)
  if (k === 'far') return [new T3.Vector3(p.x + 3, p.y + 6, 44 * D), new T3.Vector3(p.x + 3, p.y + 3, -4), 36];                // the product small on its road, the land's shape around it
  if (k === 'front') return [new T3.Vector3(p.x + 12.5 * D + sx * .3, Math.max(p.y + 3.6, over(p.x + 12.5 * D, 2.4)), 5 + Math.sin(lt * .7)), new T3.Vector3(p.x - 1 + sx, p.y + 1.6 + Math.abs(sx) * .2, -Math.abs(sx) * .3), 42];
  if (k === 'low') return [new T3.Vector3(p.x + 8 * D, Math.max(p.y + .9, over(p.x + 8 * D, .9)), 7.5), new T3.Vector3(p.x, p.y + 2, -1), 46];
  if (k === 'drone') return [new T3.Vector3(p.x - 9, p.y + 20 * D, 15), new T3.Vector3(p.x + 7, p.y, -1), 44];
  const ah = yAt(f + 10 / L) - p.y; return [new T3.Vector3(p.x - 11.5 * D, Math.max(p.y + 5.4 + Math.max(0, -ah) * .3, over(p.x - 11.5 * D, 3)), 2.4 + .6 * Math.sin(lt * .6)), new T3.Vector3(p.x + 3, p.y + 1 + ah * .15, 0), 48];      // (the product a little under the middle, the road ahead filling the frame above it)      // chase: behind it, the road ahead rising or falling up the frame
}
function camera(t) { let i = 0; while (i < NSH - 1 && t >= CUT[i + 1]) i++; let [p, q, fov] = pose(i, t); const lt = t - t0(i), BL = .55;
  if (i > 0 && lt < BL && !(SH[i] || {}).cut) { const [p0, q0, f0] = pose(i - 1, t), k = ss(lt / BL); p = p0.lerp(p, k); q = q0.lerp(q, k); fov = lerp(f0, fov, k); }      // one continuous shot: each camera eases out of the last
  const sh = window.__shake || 0; cam.position.copy(p); if (sh) { cam.position.x += Math.sin(t * 61) * sh; cam.position.y += Math.cos(t * 53) * sh; } cam.fov = fov; cam.updateProjectionMatrix(); cam.lookAt(q); return i; }

// ---------------------------------------------------------------- what moves by itself: coins, smoke, the storm
const COINS = []; if (LEAK) for (let k = 0; k < 16; k++) { const f = lerp(LEAK[0], LEAK[1], (k + .5) / 16), c = MOD.coin(.42); c.castShadow = true; scene.add(c); COINS.push({c, f, t: tAt(f), k}); }
const PUFFS = []; if (SMOKE) { const pt = canvasTex(64, 64, (x, w, h) => { const g = x.createRadialGradient(32, 32, 2, 32, 32, 30); g.addColorStop(0, 'rgba(60,60,70,.95)'); g.addColorStop(1, 'rgba(60,60,70,0)'); x.fillStyle = g; x.fillRect(0, 0, w, h); });
  for (let k = 0; k < 14; k++) { const s = new T3.Sprite(new T3.SpriteMaterial({map: pt, transparent: true, depthWrite: false})); scene.add(s); PUFFS.push(s); } }

// ---------------------------------------------------------------- the flat layer
const INK = '#0b1026', GOLD = '#ffc83d';
function rr(x, y, w, h, r) { ox.beginPath(); ox.roundRect(x, y, w, h, r); }
function text(s, x, y, size, col, o = {}) { ox.font = `${o.weight || 900} ${size}px ${FONT}`; ox.textAlign = o.align || 'center'; ox.textBaseline = 'middle'; if (o.max && ox.measureText(s).width > o.max) ox.font = `${o.weight || 900} ${size * o.max / ox.measureText(s).width}px ${FONT}`;
  if (o.stroke) { ox.lineJoin = 'round'; ox.lineWidth = o.stroke; ox.strokeStyle = o.ink || INK; ox.strokeText(s, x, y); } ox.fillStyle = col; ox.fillText(s, x, y); return ox.measureText(s).width; }
function pill(s, cx, cy, size, fg, bg, o = {}) { ox.font = `900 ${size}px ${FONT}`; const w = ox.measureText(s).width + size * 1.3, h = size * 1.9; ox.fillStyle = bg; rr(cx - w / 2, cy - h / 2, w, h, h / 2); ox.fill(); if (o.edge) { ox.lineWidth = 4; ox.strokeStyle = o.edge; ox.stroke(); } text(s, cx, cy + 2, size, fg); return w; }
const toPx = v => { const p = v.clone().project(cam); return [(p.x + 1) / 2 * W, (1 - p.y) / 2 * H, p.z]; };
const money = p => '$' + (p >= 100 ? p.toFixed(0) : p.toFixed(2));
const MON = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'], D0 = Date.parse(R.dates[0]), D1 = Date.parse(R.dates[1]);
function overlay(t, shot, f, hp) {
  ox.clearRect(0, 0, W, H); const cover = window.__coverOn, shown = t >= REVT;
  const g = ox.createLinearGradient(0, 0, 0, 330); g.addColorStop(0, 'rgba(8,10,26,.62)'); g.addColorStop(1, 'rgba(8,10,26,0)'); ox.fillStyle = g; ox.fillRect(0, 0, W, 330);
  const g2 = ox.createLinearGradient(0, 1130, 0, H); g2.addColorStop(0, 'rgba(8,10,26,0)'); g2.addColorStop(.45, 'rgba(8,10,26,.5)'); g2.addColorStop(1, 'rgba(8,10,26,.82)'); ox.fillStyle = g2; ox.fillRect(0, 1130, W, H - 1130);
  // the header: whose chart this is
  const k = back(cl((t - REVT) / .35)); if (!shown || k < 1) { ox.save(); ox.globalAlpha = shown ? 1 - k : 1; pill(R.tag || "TODAY'S MYSTERY CHART", W / 2, 170, 36, '#fff', 'rgba(20,24,48,.9)', {edge: 'rgba(255,255,255,.35)'}); ox.restore(); }
  if (shown) { ox.save(); ox.translate(W / 2, 170); ox.scale(k, k); pill('IT WAS ' + String(R.name).toUpperCase(), 0, 0, 40, '#fff', COL, {edge: '#ffffff'}); ox.restore(); }
  if (R.number && !cover) text('MEME STREET  ·  DAILY #' + R.number, W / 2, 234, 26, 'rgba(255,255,255,.85)', {weight: 800});
  if (cover) { pill('DAILY #' + (R.number || ''), W / 2, 330, 58, INK, GOLD); }
  // the band: the hook's words, a figure counting, a stamp
  for (const b of BAND) { const lt = t - b.t; if (lt < 0 && !(cover && b.kind === 'title')) continue; if (t > b.end && !(cover && b.kind === 'title')) continue;
    if (b.kind === 'title') { const L2 = String(b.text).toUpperCase().split('|'), a = cover ? 1 : Math.min(1, back((lt + .25) / .3)), out = cover ? 1 : 1 - cl((t - b.end + .25) / .25), y0 = cover ? 1290 : 392, sz = cover ? 118 : 104;
      ox.save(); ox.globalAlpha = out; ox.translate(W / 2, y0); ox.scale(a, a); L2.forEach((s, j) => text(s, 0, (j - (L2.length - 1) / 2) * sz * 1.12, sz, j === L2.length - 1 && L2.length > 1 ? GOLD : '#fff', {stroke: 18, max: 960})); ox.restore(); }
    else if (b.kind === 'counter') { const u = eo(lt / 1.3), v = b.to * u, s = (b.prefix || '') + (b.dec ? v.toFixed(b.dec) : Math.round(v).toLocaleString('en-US')) + (b.suffix || ''), a = back(lt / .3);
      ox.save(); ox.translate(W / 2, 410); ox.scale(a, a); text(s, 0, 0, 150, b.color || GOLD, {stroke: 20, max: 940}); if (b.text) text(String(b.text).toUpperCase(), 0, 112, 46, '#fff', {stroke: 12, max: 900}); ox.restore(); }
    else if (b.kind === 'stamp') { const a = lt < .16 ? lerp(2.6, 1, eo(lt / .16)) : 1 + .03 * Math.sin((lt - .16) * 30) * Math.max(0, 1 - (lt - .16) / .3), y = b.y || 420;
      ox.save(); ox.translate(W / 2, y); ox.rotate(-.07); ox.scale(a, a); ox.globalAlpha = cl(lt / .06); const col = b.color || '#ff3b4f'; ox.font = `900 132px ${FONT}`; const w = Math.min(900, ox.measureText(String(b.text).toUpperCase()).width + 90);
      ox.fillStyle = 'rgba(8,10,26,.55)'; rr(-w / 2, -96, w, 192, 26); ox.fill(); ox.lineWidth = 12; ox.strokeStyle = col; rr(-w / 2, -96, w, 192, 26); ox.stroke(); text(String(b.text).toUpperCase(), 0, 6, 132, col, {max: w - 70}); ox.restore(); } }
  // the price, riding with the product; the month
  if (shown && t < VOTE && hp && !cover) { const [x, y] = hp, p = priceAt(f), d = p - priceAt(Math.max(0, f - .03)), col = d >= 0 ? '#2bd47d' : '#ff4a5c', a = back(cl((t - REVT - .3) / .3));
    ox.save(); ox.translate(cl(x, 150, W - 150), cl(y - 44, 540, 1180)); ox.scale(a, a); pill(money(p), 0, 0, 50, '#fff', 'rgba(11,16,38,.92)', {edge: col}); ox.restore();
    const dt = new Date(lerp(D0, D1, f)); text(MON[dt.getUTCMonth()] + ' ' + dt.getUTCFullYear(), W / 2, 282, 30, '#fff', {weight: 800, stroke: 8}); }
  // rain
  const st = stormK(f, t); if (st > 0 && !cover) { ox.strokeStyle = `rgba(200,215,255,${.5 * st})`; ox.lineWidth = 3; ox.beginPath(); for (let k = 0; k < 90; k++) { const x = hs(k) * 1300 - 100, y = ((hs(k + 50) * 2300 + t * (1700 + hs(k + 9) * 500)) % 2300) - 200; ox.moveTo(x, y); ox.lineTo(x - 26, y + 74); } ox.stroke(); }
  // paper and confetti bursts, seeded: each a pure function of the time since it fired
  for (const b of BURSTS) { const lt = t - b.t; if (lt < 0 || lt > 1.5) continue; for (let k = 0; k < b.n; k++) { const a = hs(k * 3 + b.seed) * PI * 2, v = 380 + hs(k + b.seed) * 620, x = b.x + Math.cos(a) * v * lt, y = b.y + Math.sin(a) * v * lt * .8 + 900 * lt * lt - 260 * lt;
      ox.save(); ox.translate(x, y); ox.rotate(a + lt * (6 + hs(k) * 8)); ox.globalAlpha = cl(1.5 - lt, 0, 1); ox.fillStyle = b.cols[k % b.cols.length]; ox.fillRect(-b.w / 2, -b.h / 2, b.w, b.h); ox.restore(); } }
  // the captions: one to three words, the word being said lit and popped
  if (!cover && t < VOTE + 99) for (const c of R.caps || []) { if (t < c.t0 || t >= c.t1) continue; const ws = c.words, sz = ws.map(w => w.text).join(' ').length > 16 ? 76 : 88; ox.font = `900 ${sz}px ${FONT}`;
    const gap = sz * .28, wd = ws.map(w => ox.measureText(w.text).width), tot = wd.reduce((a, b) => a + b, 0) + gap * (ws.length - 1), sc = Math.min(1, 960 / tot); let x = W / 2 - tot * sc / 2; const y = t >= VOTE ? 1560 : 1335;
    ws.forEach((w, j) => { const said = t >= w.t0, lt = t - w.t0, pop = said ? 1 + .2 * Math.max(0, 1 - lt / .2) : 1, cx = x + wd[j] * sc / 2; ox.save(); ox.translate(cx, y - (said ? 10 * Math.max(0, 1 - lt / .2) : 0)); ox.scale(sc * pop, sc * pop);
      ox.globalAlpha = said ? 1 : .42; text(w.text, 0, 0, sz, said ? (w.color || (w.hot ? GOLD : '#fff')) : '#fff', {stroke: 16}); ox.restore(); x += (wd[j] + gap) * sc; }); }
  // the vote, then the midnight line
  if (t >= VOTE && !cover) { const lt = t - VOTE, a = eo(lt / .4), c = R.choice || {}; ox.fillStyle = `rgba(8,10,26,${.72 * a})`; ox.fillRect(0, 0, W, H); ox.save(); ox.translate(0, (1 - a) * 80); ox.globalAlpha = a;
    text((c.q || 'WHAT WOULD YOU DO?').toUpperCase(), W / 2, 600, 74, '#fff', {max: 940}); const opts = ['a', 'b', 'c'].filter(k => c[k]);
    opts.forEach((k, j) => { const y = 780 + j * 190, b = back(cl((lt - .25 - j * .16) / .3)), col = ['#2f7cf6', '#e8394a', '#22b573'][j]; ox.save(); ox.translate(W / 2, y); ox.scale(b, b); ox.fillStyle = col; rr(-430, -74, 860, 148, 34); ox.fill();
      ox.fillStyle = '#fff'; rr(-398, -46, 92, 92, 22); ox.fill(); text(k.toUpperCase(), -352, 3, 62, col); text(String(c[k]).toUpperCase(), 40, 3, 54, '#fff', {max: 600}); ox.restore(); });
    const last = t - t0(NSH - 1); if (last > 0 && NSH - 1 > (R.vote || 0)) { const m = back(cl(last / .3)); ox.save(); ox.translate(W / 2, 440); ox.scale(m, m); pill('NEW MYSTERY CHART AT MIDNIGHT', 0, 0, 42, INK, GOLD); ox.restore(); }
    const y2 = 780 + opts.length * 190 + 10, b2 = cl((lt - .8) / .3); ox.globalAlpha = a * b2; text('COMMENT ' + opts.map(k => k.toUpperCase()).join(' OR ') + '  ↓', W / 2, y2, 46, GOLD); text('memestreet.net', W / 2, y2 + 86, 42, '#fff', {weight: 800}); ox.restore(); }
  if (cover) text('memestreet.net', W / 2, 1590, 44, '#fff', {weight: 800});
}
const BURSTS = [];
const stormK = (f, t) => STORM ? ss((f - STORM[0]) / .05) * (1 - ss((f - STORM[1]) / .04)) : 0;

// ---------------------------------------------------------------- one frame
const GROW = Math.min(2.2, t1(0) - .1);
function render(t) {
  t = Math.max(0, Math.min(T, t)); const f = heroF(t), p = heroPos(f), sl = slope(f), shown = t >= REVT, cover = window.__coverOn;
  grow.constant = cover ? 1e9 : lerp(.07 * L, 1.16 * L, ss(t / GROW)) + (t >= GROW ? 1e9 : 0);          // (frame 0 already holds the crate on its first stretch of road)                       // the landscape builds itself over the hook's first seconds
  (scene.userData.grown || []).forEach(g => { g.visible = g.userData.f * L < grow.constant - 2; });
  hero.position.copy(p); hero.rotation.z = Math.atan(sl); hero.visible = shown; const dist = f * L, v = (heroF(t + .03) - heroF(t - .03)) / .06 * L;
  body.position.y = .05 * Math.sin(dist * 1.3) * cl(Math.abs(v) / 6); body.rotation.z = -.012 * cl(v / 12, -1, 1) + .01 * Math.sin(dist * .9); wheels.forEach(([w, r]) => { w.rotation.z = -dist / r; });
  // the crate: it shakes before the reveal, then its sides fly off
  const rt = t - REVT; crate.position.copy(heroPos(0)); crate.rotation.z = Math.atan(slope(0)) + (rt > -.7 && rt < 0 ? .03 * Math.sin(t * 60) : 0); crate.visible = rt < 1.2;
  planks.forEach((pl, k) => { const u = Math.max(0, rt); pl.position.copy(pl.userData.home).addScaledVector(pl.userData.out, u * (15 + hs(k) * 9)); pl.position.y -= 12 * u * u; pl.rotation.set(u * (3 + hs(k) * 5), u * 4 * (hs(k + 2) - .5), u * (2 + hs(k + 4) * 6)); });
  // the set pieces pop up as the product nears them
  PLACES.forEach(q => { const a = back(cl((t - q.tin) / .35)); q.g.visible = a > .001 && q.f * L < grow.constant - 2; q.g.scale.setScalar(Math.max(.001, a)); q.ticks.forEach(k => k(t)); });
  COINS.forEach(({c, t: tb, k}) => { const lt = t - tb; c.visible = lt > 0 && lt < 2.6; if (!c.visible) return; const b = heroPos(heroF(tb)), vx = -3 - hs(k) * 4, vy = 6 + hs(k + 3) * 5, vz = (hs(k + 7) - .5) * 9, x = b.x - hero.userData.len / 2 + vx * lt, fl = yAt(x / L) + .2; let y = b.y + 1.6 + vy * lt - 16 * lt * lt;
    if (y < fl) y = fl + Math.abs(Math.sin((lt) * 9)) * Math.max(0, 1.2 - lt * .6); c.position.set(x, y, vz * lt); c.rotation.set(lt * 9 + k, k, lt * 7); });
  if (SMOKE) { const on = f >= SMOKE[0] && f <= SMOKE[1] && shown; PUFFS.forEach((s, k) => { const u = (t * .7 + k / PUFFS.length) % 1; s.visible = on; s.position.set(p.x + hero.userData.len * .32 - u * 2.5, p.y + hero.userData.top * .8 + u * 5.5, .4 + (hs(k) - .5) * 1.2); const z = 1.2 + u * 3.6; s.scale.set(z, z, 1); s.material.opacity = .75 * (1 - u); }); }
  const st = stormK(f, t); sky2.material.opacity = st; hemi.intensity = lerp(.95, .5, st); sun.intensity = lerp(2.3, .9, st) * (1 + (st > .5 ? 1.6 * Math.max(0, Math.sin(t * 2.1) - .96) * 25 : 0)); scene.fog.color.set(st > .5 ? '#6b6478' : '#ffd9bb');
  const shot = camera(t); sun.position.set(cam.position.x - 40, cam.position.y + 70, 55); sun.target.position.set(p.x, p.y, 0); sky.position.copy(cam.position); sky2.position.copy(cam.position);
  rn.render(scene, cam); const hp = toPx(new T3.Vector3(p.x, p.y + hero.userData.top + 1.2, 0)); overlay(t, shot, f, hp[2] < 1 ? hp : null);
}
// what is heard when something is seen (studio.py saves this next to the timeline; sound.py plays it)
const EV = [[0, 'riser'], [GROW, 'thud'], [REVT - .7, 'riser'], [REVT, 'boom'], [REVT + .08, 'sparkle']];
BAND.forEach(b => { if (b.kind === 'stamp') EV.push([b.t, 'thud']); else if (b.kind === 'counter') EV.push([b.t, 'rise'], [b.t + 1.3, 'ding']); else if (b.t > .2) EV.push([b.t, 'pop']); });
PLACES.forEach(q => { if (q.tin > 0) EV.push([q.tin, 'pop']); if (q.pl.kind === 'arch' && q.t < T) { EV.push([q.t, 'ding']); BURSTS.push({t: q.t, x: W / 2, y: 760, n: 46, seed: 11, w: 16, h: 26, cols: ['#e8394a', '#2f7cf6', '#ffc83d', '#2bd47d', '#ffffff']}); } if (q.pl.burst) { EV.push([q.t, 'swish']); BURSTS.push({t: q.t, x: W / 2, y: 820, n: 40, seed: 5, w: 34, h: 46, cols: ['#ffffff', '#f3efe2', '#e6f0ff']}); } });
for (let i = 1; i < NSH; i++) if (i !== REV) EV.push([CUT[i], (SH[i] || {}).cut ? 'whoosh' : 'swish', .6]);
COINS.forEach(({t}, k) => { if (k % 4 === 0 && t < T) EV.push([t + .25, 'coin', .8]); }); if (STORM) EV.push([tAt(STORM[0] + .03), 'boom', .9]); if (VOTE < T) EV.push([VOTE, 'whoosh'], [VOTE + .3, 'pop'], [VOTE + .46, 'pop'], [VOTE + .9, 'ding'], [t0(NSH - 1), 'pop']);
window.__events = () => EV.filter(e => e[0] >= 0 && e[0] < T).map(e => [+e[0].toFixed(3), e[1]].concat(e.length > 2 ? [e[2]] : [])).sort((a, b) => a[0] - b[0]);
window.render = render; window.overlaps = () => [];
window.__places = t => { render(t); return PLACES.map(q => ({kind: q.pl.kind, f: +q.f.toFixed(3), tin: +q.tin.toFixed(2), t: +q.t.toFixed(2), vis: q.g.visible, sc: +q.g.scale.x.toFixed(2), pos: q.g.position.toArray().map(v => +v.toFixed(1)), hero: +heroF(t).toFixed(3)})); };      // (for looking: where each set piece is and whether it shows)
window.ready = document.fonts.load(`900 40px ${FONT}`).then(() => document.fonts.ready).then(() => { render(0); });
})();
