// The "In this town" blocky story reel (the owner, 2026-11-25: a model reel in the Roblox-story genre, "make the reel about HUSS HUSS
// but about trading ... EXACTLY the same animation style"). Its style, rebuilt here from scratch: blocky people with big rounded heads
// and drawn faces that blink and feel, warm night lights, string lights, fireworks and confetti, close shallow-focus shots, hard cuts,
// one yellow word at a time. None of the model's characters, places or pictures: our town, our hero, our story.
// window.__R (huss.py) = {T, shots: [{t0, t1, set, cast, crowd, prop, monitor, bear, portal, cam, card, fx}], caps: [{t0, t1, text}], prices}
const T3 = THREE, R = window.__R, W = 1080, H = 1920, Q = window.__Q || 2 / 3, CW = Math.round(W * Q), CH = Math.round(H * Q);
T3.ColorManagement.legacyMode = false;
const cl = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x)), lerp = (a, b, k) => a + (b - a) * k, ease = k => k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
const hs = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const back = x => { x = cl(x); const k = 1.7; return 1 + (k + 1) * Math.pow(x - 1, 3) + k * Math.pow(x - 1, 2); };

const cv = document.getElementById('gl'), oc = document.getElementById('c'), ox = oc.getContext('2d');
const rn = new T3.WebGLRenderer({canvas: cv, antialias: false, preserveDrawingBuffer: true});
rn.setSize(CW, CH, false); rn.setPixelRatio(1); rn.shadowMap.enabled = true; rn.shadowMap.type = T3.PCFSoftShadowMap;
const scene = new T3.Scene(), cam = new T3.PerspectiveCamera(32, CW / CH, .05, 400);
const comp = new T3.EffectComposer(rn, new T3.WebGLRenderTarget(CW, CH, {type: T3.HalfFloatType, samples: Q >= 1 ? 4 : 0}));
comp.addPass(new T3.RenderPass(scene, cam));
const bokeh = new T3.BokehPass(scene, cam, {focus: 3, aperture: .012, maxblur: .016, width: CW, height: CH}); comp.addPass(bokeh);
const grade = new T3.ShaderPass({uniforms: {tDiffuse: {value: null}, warm: {value: .5}, vig: {value: .35}},
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }',
  fragmentShader: `uniform sampler2D tDiffuse; uniform float warm, vig; varying vec2 vUv;
    void main(){ vec3 x = texture2D(tDiffuse, vUv).rgb; x = clamp((x * (2.51 * x + .03)) / (x * (2.43 * x + .59) + .14), 0., 1.); x = pow(x, vec3(1. / 2.2));
      float l = dot(x, vec3(.299, .587, .114)); x = mix(vec3(l), x, 1.22); x *= mix(vec3(1.), vec3(1.06, 1.0, .9), warm);
      vec2 d = vUv - .5; x *= 1. - vig * dot(d * vec2(1., .7), d * vec2(1., .7)) * 2.2; gl_FragColor = vec4(x, 1.); }`});
comp.addPass(grade);

// ---------------------------------------------------------------- materials and shapes
const MC = {};
const M = (col, o = {}) => { const k = col + JSON.stringify(o); return MC[k] || (MC[k] = new T3.MeshStandardMaterial(Object.assign({color: col, roughness: .62, metalness: 0}, o))); };
const glow = (col, k = 2.2) => new T3.MeshBasicMaterial({color: new T3.Color(col).multiplyScalar(k), toneMapped: false});
function tex(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; const x = c.getContext('2d'); if (draw) draw(x, w, h);
  const t = new T3.CanvasTexture(c); t.encoding = T3.sRGBEncoding; t.anisotropy = 8; t.userData = {c, x}; return t; }
const GC = {};
function rboxG(w, h, d, r) {      // a box with rounded edges (Roblox parts are soft-cornered)
  const k = [w, h, d, r].join(); if (GC[k]) return GC[k]; r = Math.min(r, w / 2 - .001, h / 2 - .001, d / 2 - .001);
  const s = new T3.Shape(), x = -w / 2 + r, y = -h / 2 + r, ww = w - 2 * r, hh = h - 2 * r;
  s.moveTo(x, y - r); s.lineTo(x + ww, y - r); s.quadraticCurveTo(x + ww + r, y - r, x + ww + r, y); s.lineTo(x + ww + r, y + hh); s.quadraticCurveTo(x + ww + r, y + hh + r, x + ww, y + hh + r);
  s.lineTo(x, y + hh + r); s.quadraticCurveTo(x - r, y + hh + r, x - r, y + hh); s.lineTo(x - r, y); s.quadraticCurveTo(x - r, y - r, x, y - r);
  const g = new T3.ExtrudeGeometry(s, {depth: d - 2 * r, bevelEnabled: true, bevelThickness: r, bevelSize: 0, bevelSegments: 4, curveSegments: 6}); g.translate(0, 0, -(d - 2 * r) / 2); g.computeVertexNormals();
  return GC[k] = g;
}
const mesh = (g, m, sh = true) => { const o = new T3.Mesh(g, m); o.castShadow = sh; o.receiveShadow = true; return o; };
const rbox = (w, h, d, col, r = .06, o) => mesh(rboxG(w, h, d, r), typeof col === 'string' ? M(col, o) : col);
const box = (w, h, d, col, o) => mesh(GC['b' + [w, h, d]] || (GC['b' + [w, h, d]] = new T3.BoxGeometry(w, h, d)), typeof col === 'string' ? M(col, o) : col);
const cyl = (r1, r2, h, col, seg = 20) => mesh(new T3.CylinderGeometry(r1, r2, h, seg), typeof col === 'string' ? M(col) : col);
const ball = (r, col, seg = 20) => mesh(new T3.SphereGeometry(r, seg, seg * 3 / 4), typeof col === 'string' ? M(col) : col);
const at = (o, x, y, z, ry = 0) => { o.position.set(x, y, z); o.rotation.y = ry; return o; };
const grp = (...a) => { const g = new T3.Group(); a.forEach(o => g.add(o)); return g; };
const DYN = [];     // [texture, draw(x, w, h, t), its shot's group] redrawn every frame while on screen
let CUR = null;

// ---------------------------------------------------------------- faces: drawn as the genre draws them (thick brows, glossy eyes, a mouth that says it all)
const FACES = {};
function faceTex(mood, blink, extra) {
  const key = mood + blink + (extra || ''); if (FACES[key]) return FACES[key];
  return FACES[key] = tex(256, 256, (x) => {
    const ink = '#2a1d16', eye = (cx, cy, s = 1) => { if (blink) { x.strokeStyle = ink; x.lineWidth = 9; x.lineCap = 'round'; x.beginPath(); x.moveTo(cx - 17, cy + 2); x.quadraticCurveTo(cx, cy + 9, cx + 17, cy + 2); x.stroke(); return; }
      x.fillStyle = ink; x.beginPath(); x.ellipse(cx, cy, 14 * s, 21 * s, 0, 0, 7); x.fill(); x.fillStyle = '#fff'; x.beginPath(); x.arc(cx + 5 * s, cy - 8 * s, 5.5 * s, 0, 7); x.fill(); x.beginPath(); x.arc(cx - 4 * s, cy + 7 * s, 2.5 * s, 0, 7); x.fill(); };
    const brow = (cx, cy, ang, w = 46, th = 13) => { x.save(); x.translate(cx, cy); x.rotate(ang); x.fillStyle = ink; x.beginPath(); x.roundRect(-w / 2, -th / 2, w, th, th / 2); x.fill(); x.restore(); };
    const L = 92, Rr = 164, ey = 118;
    if (mood === 'determined') { brow(L, 84, .32); brow(Rr, 84, -.32); eye(L, ey + 4, .95); eye(Rr, ey + 4, .95); x.strokeStyle = ink; x.lineWidth = 9; x.lineCap = 'round'; x.beginPath(); x.moveTo(108, 182); x.quadraticCurveTo(128, 176, 150, 183); x.stroke(); }
    else if (mood === 'happy' || mood === 'grin') { brow(L, 76, -.18); brow(Rr, 76, .18); if (mood === 'happy') { eye(L, ey); eye(Rr, ey); } else { x.strokeStyle = ink; x.lineWidth = 10; x.lineCap = 'round'; [L, Rr].forEach(c => { x.beginPath(); x.arc(c, ey + 8, 15, Math.PI * 1.1, Math.PI * 1.9); x.stroke(); }); }
      x.fillStyle = '#5b1e22'; x.beginPath(); x.moveTo(90, 160); x.quadraticCurveTo(128, 232, 166, 160); x.closePath(); x.fill(); x.fillStyle = '#fff'; x.fillRect(98, 160, 60, 11); x.fillStyle = '#ef7f8a'; x.beginPath(); x.ellipse(128, 196, 20, 10, 0, 0, 7); x.fill(); }
    else if (mood === 'shock') { brow(L, 62, -.1, 42); brow(Rr, 62, .1, 42); [L, Rr].forEach(c => { x.fillStyle = '#fff'; x.beginPath(); x.arc(c, ey, 22, 0, 7); x.fill(); x.lineWidth = 5; x.strokeStyle = ink; x.stroke(); if (!blink) { x.fillStyle = ink; x.beginPath(); x.arc(c, ey, 8, 0, 7); x.fill(); } });
      x.fillStyle = '#4a1a1e'; x.beginPath(); x.ellipse(128, 188, 18, 24, 0, 0, 7); x.fill(); }
    else if (mood === 'sad' || mood === 'worried') { brow(L, 82, -.35); brow(Rr, 82, .35); eye(L, ey + 6, .9); eye(Rr, ey + 6, .9); x.strokeStyle = ink; x.lineWidth = 9; x.lineCap = 'round'; x.beginPath();
      if (mood === 'sad') { x.moveTo(104, 192); x.quadraticCurveTo(128, 176, 152, 192); } else { x.moveTo(100, 184); [110, 120, 130, 140, 150].forEach((px, i) => x.lineTo(px + 4, 184 + (i % 2 ? -6 : 6))); } x.stroke();
      if (mood === 'worried') { x.fillStyle = '#8fd0ff'; x.beginPath(); x.moveTo(196, 70); x.quadraticCurveTo(212, 100, 196, 110); x.quadraticCurveTo(180, 100, 196, 70); x.fill(); } }
    else if (mood === 'smug') { brow(L, 86, .12); brow(Rr, 78, -.25); eye(L, ey + 4, .9); eye(Rr, ey + 2, .9); x.strokeStyle = ink; x.lineWidth = 9; x.lineCap = 'round'; x.beginPath(); x.moveTo(100, 180); x.quadraticCurveTo(140, 196, 162, 168); x.stroke(); }
    else { brow(L, 80, 0); brow(Rr, 80, 0); eye(L, ey); eye(Rr, ey); x.strokeStyle = ink; x.lineWidth = 9; x.lineCap = 'round'; x.beginPath(); x.moveTo(108, 180); x.quadraticCurveTo(128, 190, 150, 180); x.stroke(); }
    if (extra === 'tache') { x.fillStyle = '#2a1d16'; x.beginPath(); x.moveTo(84, 168); x.quadraticCurveTo(128, 140, 172, 168); x.quadraticCurveTo(150, 158, 128, 166); x.quadraticCurveTo(106, 158, 84, 168); x.fill(); }
    if (extra === 'cheeks') { x.fillStyle = 'rgba(255,120,120,.35)'; x.beginPath(); x.ellipse(66, 160, 18, 11, 0, 0, 7); x.ellipse(190, 160, 18, 11, 0, 0, 7); x.fill(); }
  });
}

// ---------------------------------------------------------------- people: Roblox-like parts (a big rounded head, a block torso, arms and legs on hinges)
const LOOKS = {
  hero: {shirt: '#f4f2ee', pants: '#1f2a4a', skin: '#f2c9a0', hair: 'cap', cap: '#d9302b', hairCol: '#6b3b1f', face: 'determined'},
  neighbor: {shirt: '#e0457b', pants: '#1f8a5c', skin: '#f2c9a0', hair: 'curly', hairCol: '#d4641c', face: 'grin', hat: 'party', extra: 'cheeks'},
  boss: {shirt: '#7d1d2a', pants: '#2a1a22', skin: '#c98d62', hair: 'slick', hairCol: '#221a1a', face: 'smug', suit: true, extra: 'tache'},
  mayor: {shirt: '#1d2440', pants: '#141a30', skin: '#e9b98f', hair: 'none', face: 'happy', hat: 'top', suit: true, sash: true, extra: 'tache'},
  rockguy: {shirt: '#f08a24', pants: '#2b2f3a', skin: '#8a5a3c', hair: 'none', face: 'grin', hat: 'beanie', extra: 'beard'},
};
const PARTY = [['#7a4bd6', '#1f2a4a', '#f2c9a0', 'bun', '#2a1d16'], ['#2ec4b6', '#f4f2ee', '#c98d62', 'curly', '#1a1210'], ['#ffb020', '#3a2a6a', '#f2c9a0', 'spiky', '#e8c15a'],
  ['#4bb3ff', '#22304a', '#8a5a3c', 'short', '#1a1210'], ['#ff5d6c', '#f4f2ee', '#f2c9a0', 'long', '#7a3b1a'], ['#2bd47d', '#1a1a2a', '#e9b98f', 'short', '#4a2a1a'],
  ['#f4f2ee', '#c0354a', '#c98d62', 'bun', '#1a1210'], ['#9b59d0', '#2a2a2a', '#f2c9a0', 'spiky', '#2a1d16']];
function hairOn(head, kind, col, k) {
  const g = new T3.Group(); head.add(g);
  if (kind === 'cap') { g.add(at(rbox(.66, .2, .66, col.cap, .08), 0, .27, 0)); g.add(at(rbox(.5, .05, .32, col.cap, .02), 0, .2, .42)); g.add(at(rbox(.66, .12, .1, col.hairCol, .03), 0, .12, -.3));
    g.add(at(rbox(.08, .2, .5, col.hairCol, .03), -.3, .06, -.02)); g.add(at(rbox(.08, .2, .5, col.hairCol, .03), .3, .06, -.02)); g.add(at(cyl(.035, .035, .03, col.cap), 0, .38, 0)); }
  else if (kind === 'curly' || kind === 'spiky') for (let i = 0; i < 9; i++) { const a = (i / 9) * Math.PI * 2, o = kind === 'curly' ? ball(.12, col.hairCol, 10) : rbox(.14, .2, .14, col.hairCol, .04); o.position.set(Math.cos(a) * .22, .3 + hs(i + k) * .05, Math.sin(a) * .22 - .03); g.add(o); }
  else if (kind === 'bun') { g.add(at(rbox(.66, .14, .66, col.hairCol, .06), 0, .29, -.01)); g.add(at(ball(.14, col.hairCol, 12), 0, .4, -.18)); }
  else if (kind === 'long') { g.add(at(rbox(.68, .16, .68, col.hairCol, .06), 0, .28, -.01)); g.add(at(rbox(.7, .52, .14, col.hairCol, .05), 0, -.02, -.3)); }
  else if (kind === 'short' || kind === 'slick') g.add(at(rbox(.66, .13, .66, col.hairCol, .06), 0, .29, kind === 'slick' ? -.03 : 0));
  if (col.hat === 'party') { const c = mesh(new T3.ConeGeometry(.18, .48, 18), M('#ffd23f')); c.position.set(.06, .55, 0); c.rotation.z = -.15; g.add(c); const p = ball(.06, '#ff5d8f', 10); p.position.set(.1, .8, 0); g.add(p);
    for (let i = 0; i < 3; i++) { const r = mesh(new T3.TorusGeometry(.15 - i * .04, .02, 6, 18), M(['#2ec4b6', '#ff5d8f', '#7a4bd6'][i])); r.rotation.x = Math.PI / 2; r.position.set(.06 - i * .013, .38 + i * .12, 0); g.add(r); } }
  if (col.hat === 'top') { g.add(at(cyl(.3, .3, .5, '#141414'), 0, .58, 0)); g.add(at(cyl(.46, .46, .04, '#141414'), 0, .34, 0)); g.add(at(cyl(.305, .305, .08, '#d4a72c'), 0, .4, 0)); }
  if (col.hat === 'beanie') g.add(at(rbox(.68, .24, .68, '#2a6fd6', .1), 0, .27, 0));
}
function person(look, seed = 1) {
  const L = typeof look === 'string' ? LOOKS[look] : look, root = new T3.Group(), body = new T3.Group(); root.add(body);
  const torso = rbox(.72, .74, .38, L.shirt, .05); torso.position.y = 1.15; body.add(torso);
  if (L.suit) { torso.add(at(box(.24, .5, .02, '#f4f2ee'), 0, .1, .19)); torso.add(at(box(.08, .4, .025, L.sash ? '#d4a72c' : '#1b1b28'), 0, .05, .2)); }
  if (L.sash) { const s = box(.12, 1, .03, '#6a3fbf'); s.rotation.z = .7; s.position.set(0, 0, .2); torso.add(s); }
  if (!L.suit && L.shirt === '#f4f2ee') torso.add(at(box(.3, .06, .02, '#e6e3dc'), 0, .34, .19));
  const head = new T3.Group(); head.position.y = 1.52 + .3; body.add(head);
  head.add(rbox(.62, .6, .6, L.skin, .14)); const face = new T3.Mesh(new T3.PlaneGeometry(.56, .56), new T3.MeshStandardMaterial({map: faceTex(L.face, 0, L.extra), transparent: true, roughness: .6})); face.position.z = .302; head.add(face);
  if (L.extra === 'beard') head.add(at(rbox(.5, .1, .06, '#2a1d16', .04), 0, -.27, .29));
  hairOn(head, L.hair, L, seed);
  const limb = (w, h, col, x, y) => { const pivot = new T3.Group(); pivot.position.set(x, y, 0); const m = rbox(w, h, w, col, .05); m.position.y = -h / 2; pivot.add(m); return pivot; };
  const aCol = L.suit ? L.shirt : L.skin, armL = limb(.32, .74, aCol, -.53, 1.5), armR = limb(.32, .74, aCol, .53, 1.5);
  if (!L.suit) { [armL, armR].forEach(a => { const sl = rbox(.34, .26, .34, L.shirt, .05); sl.position.y = -.12; a.add(sl); }); }
  [armL, armR].forEach(a => { const hd = rbox(.3, .16, .3, L.skin, .06); hd.position.y = -.74; a.add(hd); });
  const legL = limb(.34, .78, L.pants, -.18, .78), legR = limb(.34, .78, L.pants, .18, .78); body.add(armL, armR, legL, legR);
  [legL, legR].forEach(l => { const sh = rbox(.36, .14, .42, '#1b1b1f', .05); sh.position.set(0, -.74, .04); l.add(sh); });
  const p = {root, body, head, face, torso, armL, armR, legL, legR, L, seed, mood: L.face, ghosts: []};
  return p;
}
function ghostsFor(p) {       // the HUSS blur: two see-through copies of each arm a moment behind it
  if (p.ghosts.length) return; for (const a of [p.armL, p.armR]) for (let k = 1; k <= 3; k++) { const g = a.clone(true); g.traverse(m => { if (m.isMesh) { m.material = m.material.clone(); m.material.transparent = true; m.material.opacity = .32 / k; m.castShadow = false; } }); a.parent.add(g); p.ghosts.push([g, a, k]); }
}
function pose(p, kind, t, lt) {      // the parts by the pose and the time
  const s = Math.sin, sd = p.seed, br = .012 * s(t * 2.2 + sd);
  let aL = [.05, .08], aR = [.05, -.08], lg = [0, 0], by = 0, tilt = 0, hy = 0;
  if (kind === 'huss' || kind === 'hussfast') { const f = kind === 'hussfast' ? 22 : 15, w = s(t * f + sd); aL = [-1.15 - .15 * Math.abs(w), .45 + .55 * w]; aR = [-1.15 - .15 * Math.abs(w), -.45 + .55 * w]; by = .02 * Math.abs(s(t * f * 2)); hy = .05 * s(t * f); }
  else if (kind === 'cheer' || kind === 'dance') { const w = s(t * (kind === 'dance' ? 7 : 9) + sd); aL = [-2.7 + .3 * w, .35]; aR = [-2.7 - .3 * w, -.35]; by = .06 * Math.abs(s(t * 7 + sd)); tilt = .08 * w; }
  else if (kind === 'stretch') { const u = cl(lt / .6); aL = [-3 * u, .25 + .2 * s(t * 3)]; aR = [-3 * u, -.25 - .2 * s(t * 3)]; tilt = .1 * s(t * 2.4); }
  else if (kind === 'point') { aR = [-1.5, -.1]; aL = [.05, .1]; }
  else if (kind === 'wave') { aR = [-2.6, -.4 + .4 * s(t * 10)]; }
  else if (kind === 'think') { aR = [-2.3, .7]; aL = [-.6, .5]; hy = .15; }
  else if (kind === 'tremble') { const j = .05 * s(t * 47 + sd); aL = [-1.1 + j, .4]; aR = [-1.1 - j, -.4]; by = .006 * s(t * 53); }
  else if (kind === 'shock') { aL = [-1.9, .9]; aR = [-1.9, -.9]; by = .04 * Math.max(0, 1 - lt * 3); }
  else if (kind === 'sad') { aL = [.1, .05]; aR = [.1, -.05]; tilt = 0; hy = -.12; }
  else if (kind === 'hold') { aL = [-1.2, .2]; aR = [-1.2, -.2]; }
  else if (kind === 'walk') { const w = s(t * 7 + sd); aL = [.5 * w, .06]; aR = [-.5 * w, -.06]; lg = [-.5 * w, .5 * w]; by = .03 * Math.abs(w); }
  else if (kind === 'sit') { lg = [-1.57, -1.57]; by = -.66; aL = [-.9, .3]; aR = [-.9, -.3]; }
  else if (kind === 'run') { const w = s(t * 12 + sd); aL = [.9 * w, .1]; aR = [-.9 * w, -.1]; lg = [-.8 * w, .8 * w]; by = .07 * Math.abs(w); }
  p.armL.rotation.set(aL[0], 0, aL[1]); p.armR.rotation.set(aR[0], 0, aR[1]); p.legL.rotation.x = lg[0]; p.legR.rotation.x = lg[1];
  p.body.position.y = by + br; p.body.rotation.z = tilt * .5; p.head.rotation.x = -hy * .5 + (kind === 'sad' ? .25 : 0); p.head.rotation.z = tilt * .4;
  const mood = p.mood, blink = (t * .8 + sd * .37) % 3.1 < .12 && mood !== 'grin' ? 1 : 0; p.face.material.map = faceTex(mood, blink, p.L.extra);
  for (const [g, a, k] of p.ghosts) { const tt = t - k * .018; const w = s(tt * (kind === 'hussfast' ? 22 : 15) + sd); g.visible = kind.startsWith('huss'); g.rotation.set(a.rotation.x - .1 * Math.abs(w), 0, (a === p.armL ? .45 : -.45) + .55 * w); }
}

// ---------------------------------------------------------------- the sky, the window, the screens
function sky(x, w, h, t, night = 1) {
  const g = x.createLinearGradient(0, 0, 0, h); if (night) { g.addColorStop(0, '#0d1033'); g.addColorStop(.6, '#2a2266'); g.addColorStop(1, '#5a3b7a'); } else { g.addColorStop(0, '#5fb6ff'); g.addColorStop(1, '#c7ecff'); }
  x.fillStyle = g; x.fillRect(0, 0, w, h);
  if (night) { for (let i = 0; i < 70; i++) { x.fillStyle = `rgba(255,255,255,${.4 + .5 * hs(i)})`; x.fillRect(hs(i + 3) * w, hs(i + 9) * h * .6, 2, 2); }
    for (let k = 0; k < 6; k++) { const per = 2.3 + hs(k) * 1.4, ph = ((t + hs(k + 20) * 5) % per) / per, cx = (.1 + .8 * hs(k + 40 + Math.floor((t + hs(k + 20) * 5) / per))) * w, cy = (.12 + .3 * hs(k + 60)) * h, col = ['#ffd23f', '#ff5d8f', '#7fc4ff', '#2bd47d', '#ffffff', '#ff9f43'][k];
      if (ph < .25) { x.strokeStyle = col; x.lineWidth = 3; x.beginPath(); x.moveTo(cx, h); x.lineTo(cx, cy + (h - cy) * (1 - ph / .25)); x.stroke(); continue; }
      const u = (ph - .25) / .75, r = u * .16 * w; x.globalAlpha = 1 - u; x.fillStyle = col;
      for (let i = 0; i < 26; i++) { const a = i / 26 * Math.PI * 2; x.beginPath(); x.arc(cx + Math.cos(a) * r, cy + Math.sin(a) * r + u * u * 40, 4 * (1 - u) + 1.5, 0, 7); x.fill(); } x.globalAlpha = 1; } }
  else for (let k = 0; k < 4; k++) { x.fillStyle = 'rgba(255,255,255,.9)'; const cx = ((hs(k) * w + t * 6) % (w + 200)) - 100, cy = (.1 + .25 * hs(k + 5)) * h; [0, 40, -40, 70].forEach((d, i) => { x.beginPath(); x.arc(cx + d, cy + (i > 1 ? 12 : 0), 46 - i * 6, 0, 7); x.fill(); }); }
}
function windowView(x, w, h, t) {      // the party outside, seen through the hero's window
  sky(x, w, h, t, 1); x.fillStyle = '#1b1640'; for (let i = 0; i < 6; i++) { const bx = i * w / 5 - 20; x.fillRect(bx, h * .55 - hs(i) * 60, w / 6, h); }
  for (let i = 0; i < 26; i++) { const ly = h * .5 + 18 * Math.sin(i / 25 * Math.PI); x.fillStyle = ['#ffd23f', '#ff5d8f', '#7fc4ff', '#2bd47d'][i % 4]; x.globalAlpha = .7 + .3 * Math.sin(t * 4 + i); x.beginPath(); x.arc(i / 25 * w, ly, 6, 0, 7); x.fill(); } x.globalAlpha = 1;
  for (let i = 0; i < 12; i++) { const px = (i + .5) / 12 * w, b = 10 * Math.abs(Math.sin(t * 6 + i)), c = PARTY[i % PARTY.length]; x.fillStyle = c[0]; x.fillRect(px - 14, h * .78 - b, 28, 40); x.fillStyle = c[2]; x.fillRect(px - 11, h * .78 - 26 - b, 22, 22);
    x.fillStyle = c[0]; x.fillRect(px - 22, h * .7 - b - 10 * Math.abs(Math.sin(t * 8 + i)), 7, 26); x.fillRect(px + 15, h * .7 - b - 10 * Math.abs(Math.cos(t * 8 + i)), 7, 26); }
}
const PRICES = () => (R.prices && R.prices.length > 4 ? R.prices : [20, 22, 19, 25, 24, 28, 26, 31, 29, 34, 33, 38]);
function screenUI(x, w, h, t, mode, lt) {   // the hero's monitor: Meme Street's Daily, our own game
  x.fillStyle = '#0b0d14'; x.fillRect(0, 0, w, h); x.fillStyle = '#141826'; x.fillRect(0, 0, w, 70);
  x.font = '800 34px Montserrat, sans-serif'; x.fillStyle = '#4cc3cc'; x.textBaseline = 'middle'; x.fillText('MEME STREET', 26, 36); x.fillStyle = '#8a97a3'; x.font = '700 24px Montserrat, sans-serif';
  x.fillText(mode === 'midnight' || mode === 'flat' || mode === 'glitch' ? 'NEW MYSTERY CHART · 00:00' : 'DAILY · MYSTERY CHART', 26 + 250, 38);
  const P = PRICES(), n = P.length - 1, lo = Math.min(...P), hi = Math.max(...P), X = i => 40 + i / n * (w - 80), Y = v => h - 190 - (v - lo) / (hi - lo + 1e-9) * (h - 330);
  let k = mode === 'trade' || mode === 'daily' ? Math.min(n, Math.floor(n * (.25 + .75 * cl(lt / 3)))) : n;
  x.strokeStyle = 'rgba(255,255,255,.06)'; x.lineWidth = 2; for (let i = 0; i < 5; i++) { x.beginPath(); x.moveTo(30, 110 + i * (h - 330) / 4); x.lineTo(w - 30, 110 + i * (h - 330) / 4); x.stroke(); }
  if (mode === 'flat' || mode === 'glitch' || mode === 'portal' || mode === 'midnight') {
    x.strokeStyle = '#e8394a'; x.lineWidth = 8; x.beginPath(); const yy = h / 2 - 40; x.moveTo(40, yy); const span = mode === 'midnight' ? cl(lt / 2) : 1; x.lineTo(40 + (w - 80) * span, yy); x.stroke();
    if (mode !== 'midnight') { const dive = mode === 'portal' ? cl(lt / .8) : mode === 'glitch' ? .15 * cl(lt / 2) : 0; if (dive > 0) { x.lineWidth = 12; x.beginPath(); x.moveTo(w - 40, yy); x.lineTo(w / 2 + (w / 2 - 40) * (1 - dive), yy + dive * 30); x.stroke(); } }
    if (mode === 'glitch') { for (let i = 0; i < 8; i++) { const gy = hs(Math.floor(t * 18) + i) * h; x.drawImage(x.canvas, 0, gy, w, 18, (hs(i + Math.floor(t * 18)) - .5) * 60, gy, w, 18); } }
    x.fillStyle = '#ffd23f'; x.font = '800 40px Montserrat, sans-serif'; x.fillText('???', w / 2 - 34, 100);
  } else {
    const up = mode === 'win' || P[k] >= P[0]; x.strokeStyle = up ? '#2bd47d' : '#e8394a'; x.lineWidth = 7; x.lineJoin = 'round'; x.beginPath(); for (let i = 0; i <= k; i++) i ? x.lineTo(X(i), Y(P[i])) : x.moveTo(X(i), Y(P[i])); x.stroke();
    x.fillStyle = '#fff'; x.beginPath(); x.arc(X(k), Y(P[k]), 10, 0, 7); x.fill();
    x.fillStyle = '#ffd23f'; x.font = '800 40px Montserrat, sans-serif'; x.fillText('???', w / 2 - 34, 100);
    if (mode === 'win') { x.fillStyle = 'rgba(43,212,125,.92)'; x.beginPath(); x.roundRect(w / 2 - 190, h / 2 - 150, 380, 130, 24); x.fill(); x.fillStyle = '#06210f'; x.font = '900 84px Montserrat, sans-serif'; x.textAlign = 'center'; x.fillText('+40%', w / 2, h / 2 - 82); x.textAlign = 'left'; }
  }
  [['BUY', '#2bd47d'], ['SELL', '#e8394a'], ['SHORT', '#7a4bd6']].forEach(([s, c], i) => { const bx = 30 + i * (w - 60) / 3, on = mode === 'trade' && Math.floor(t * 6) % 3 === i; x.fillStyle = c; x.globalAlpha = on ? 1 : .75; x.beginPath(); x.roundRect(bx + 8, h - 130, (w - 60) / 3 - 16, 96, 18); x.fill(); x.globalAlpha = 1;
    x.fillStyle = '#fff'; x.font = '900 40px Montserrat, sans-serif'; x.textAlign = 'center'; x.fillText(s, bx + (w - 60) / 6, h - 82); x.textAlign = 'left'; });
  if (mode === 'trade') { x.fillStyle = '#fff'; x.font = '800 30px Montserrat, sans-serif'; x.textAlign = 'right'; x.fillText('1:' + String(59 - Math.floor(lt * 7) % 60).padStart(2, '0'), w - 26, 38); x.textAlign = 'left'; }
}
function swirl(x, w, h, t) {      // the portal: a hole in the chart, turning
  x.clearRect(0, 0, w, h); const cx = w / 2, cy = h / 2;
  for (let r = w / 2; r > 4; r -= 6) { const a = t * 3 + r * .05, k = r / (w / 2); x.fillStyle = `hsl(${270 + 40 * Math.sin(a)}, 90%, ${12 + 50 * (1 - k)}%)`; x.globalAlpha = .9;
    x.beginPath(); x.ellipse(cx + Math.cos(a) * 4, cy + Math.sin(a) * 4, r, r, 0, 0, 7); x.fill(); }
  x.globalAlpha = 1; x.strokeStyle = 'rgba(255,190,255,.8)'; x.lineWidth = 6;
  for (let i = 0; i < 7; i++) { x.beginPath(); for (let u = 0; u < 1; u += .02) { const a = t * 2.4 + i / 7 * Math.PI * 2 + u * 9, rr = (1 - u) * w / 2; u ? x.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr) : x.moveTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr); } x.stroke(); }
  x.fillStyle = '#05000a'; x.beginPath(); x.arc(cx, cy, w * .14, 0, 7); x.fill();
}
function labelTex(lines, opt = {}) {
  return tex(opt.w || 512, opt.h || 256, (x, w, h) => { x.fillStyle = opt.bg || '#fff'; x.fillRect(0, 0, w, h); x.textAlign = 'center'; x.textBaseline = 'middle';
    lines.forEach(([s, size, col, y]) => { x.font = `800 ${size}px Fredoka, Montserrat, sans-serif`; x.fillStyle = col || '#1b1b28'; x.fillText(s, w / 2, y * h, w * .92); }); });
}
const plane = (w, h, t, basic = false) => new T3.Mesh(new T3.PlaneGeometry(w, h), basic ? new T3.MeshBasicMaterial({map: t, toneMapped: false}) : new T3.MeshStandardMaterial({map: t, roughness: .8}));

// ---------------------------------------------------------------- props
const PROPS = {
  desk(g) { const d = new T3.Group(); d.add(at(rbox(2.6, .12, 1, '#8a5a34', .03), 0, 1.0, 0)); d.add(at(rbox(2.5, .9, .08, '#6b4426', .02), 0, .55, .42));
    d.add(at(box(2.62, .05, 1.02, '#a06c40'), 0, 1.07, 0)); for (let i = 0; i < 6; i++) d.add(at(box(.38, .9, .02, '#7a4e2c'), -1.05 + i * .42, .55, .47)); g.add(at(d, 0, 0, .6)); return d; },
  monitor(g, mode) { const m = new T3.Group(); m.add(at(rbox(1.16, .74, .07, '#1b1d24', .03), 0, .5, 0)); const t = tex(768, 512); DYN.push([t, (x, w, h, tt, lt) => screenUI(x, w, h, tt, g.userData.mode || mode, lt), CUR]);
    const s = plane(1.08, .68, t, true); s.position.set(0, .5, .036); m.add(s); m.add(at(box(.08, .3, .08, '#2a2c34'), 0, .14, -.04)); m.add(at(rbox(.44, .04, .3, '#2a2c34', .02), 0, .02, 0)); m.userData.screen = s; return m; },
  keyboard() { const k = new T3.Group(); k.add(rbox(.9, .05, .3, '#2a2c34', .02)); for (let r = 0; r < 3; r++) for (let c = 0; c < 10; c++) k.add(at(rbox(.07, .03, .07, '#e8e8ee', .01), -.38 + c * .085, .035, -.09 + r * .09)); return k; },
  clock(time = '5:00') { const c = new T3.Group(); c.add(at(cyl(.2, .2, .1, '#d9302b', 24), 0, .24, 0)); c.children[0].rotation.x = Math.PI / 2;
    const f = plane(.3, .3, tex(256, 256, (x, w, h) => { x.fillStyle = '#fff'; x.beginPath(); x.arc(w / 2, h / 2, w / 2, 0, 7); x.fill(); x.fillStyle = '#1b1b28'; x.font = '800 86px Montserrat'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(time, w / 2, h / 2 + 4); }), true);
    f.material.transparent = true; f.position.set(0, .24, .056); c.add(f); for (const s of [-1, 1]) c.add(at(ball(.07, '#d9302b', 12), s * .13, .44, 0)); c.add(at(box(.04, .1, .04, '#333'), -.12, .07, 0), at(box(.04, .1, .04, '#333'), .12, .07, 0)); return c; },
  mug() { const m = new T3.Group(); m.add(at(cyl(.08, .07, .18, '#4cc3cc'), 0, .09, 0)); m.add(at(cyl(.07, .07, .01, '#3b2416'), 0, .175, 0)); return m; },
  rock() { const r = mesh(new T3.DodecahedronGeometry(.16, 0), M('#8f8f98', {flatShading: true})); r.scale.set(1.2, .85, 1); return r; },
  plate() { const p = new T3.Group(); p.add(at(cyl(.26, .22, .03, '#fafafa'), 0, .015, 0)); p.add(at(cyl(.07, .07, .02, '#fff'), -.06, .04, 0), at(cyl(.035, .035, .025, '#ffb020'), -.06, .05, 0)); p.add(at(rbox(.22, .02, .06, '#b3472b', .01), .08, .04, .03)); return p; },
};
function building(w, h, col, roof, rng) { const b = new T3.Group(); b.add(at(rbox(w, h, 4, col, .05), 0, h / 2, 0)); const r = mesh(new T3.ConeGeometry(w * .78, h * .45, 4), M(roof)); r.rotation.y = Math.PI / 4; r.position.y = h + h * .22; b.add(r);
  for (let i = 0; i < Math.floor(w / 1.2); i++) for (let j = 0; j < Math.floor(h / 1.6); j++) { const lit = hs(rng + i * 7 + j * 13) > .35; b.add(at(box(.6, .7, .05, lit ? glow('#ffd88a', 1.4) : M('#2a2548')), -w / 2 + .9 + i * 1.2, 1 + j * 1.6, 2.02)); }
  return b; }
function stringLights(g, x0, x1, y, z, n, sag = .5) { for (let i = 0; i <= n; i++) { const u = i / n, b = ball(.06, glow(['#ffd23f', '#ff5d8f', '#7fc4ff', '#2bd47d', '#ff9f43'][i % 5], 3), 8); b.castShadow = false; b.position.set(lerp(x0, x1, u), y - sag * Math.sin(Math.PI * u), z); g.add(b); } }
function confetti(g, n, area, y0) {     // falling confetti, a pure function of time (frames are drawn out of order)
  const geo = new T3.PlaneGeometry(.07, .04), mats = ['#ffd23f', '#ff5d8f', '#7fc4ff', '#2bd47d', '#ffffff', '#b98cff'].map(c => new T3.MeshBasicMaterial({color: c, side: T3.DoubleSide})); const ps = [];
  for (let i = 0; i < n; i++) { const m = new T3.Mesh(geo, mats[i % mats.length]); g.add(m); ps.push(m); }
  return t => ps.forEach((m, i) => { const fall = (t * (.5 + hs(i) * .5) + hs(i + 3) * y0) % y0; m.position.set((hs(i + 7) - .5) * area + .2 * Math.sin(t * 2 + i), y0 - fall, (hs(i + 11) - .5) * area * .6); m.rotation.set(t * 3 + i, t * 2.3 + i * .7, 0); });
}

// ---------------------------------------------------------------- the sets (each shot builds its own, around the origin; the camera looks at it)
function skyDome(g, night, ry = 0) { const t = tex(512, 768); DYN.push([t, (x, w, h, tt) => sky(x, w, h, tt, night), CUR]); const p = plane(80, 120, t, true); p.position.set(0, 30, -40); g.add(p); return p; }
function lightsFor(g, night, warm = 1) {
  g.add(new T3.HemisphereLight(night ? '#6a6fd6' : '#dff1ff', night ? '#3a2240' : '#c8b08a', night ? .55 : 1.1));
  const k = new T3.DirectionalLight(night ? '#9fb0ff' : '#fff4dd', night ? .7 : 1.8); k.position.set(4, 9, 7); k.castShadow = true; k.shadow.mapSize.set(2048, 2048); k.shadow.bias = -.0004;
  Object.assign(k.shadow.camera, {left: -6, right: 6, top: 7, bottom: -3, near: 1, far: 30}); g.add(k, k.target);
  if (night && warm) { const l = new T3.PointLight('#ffb35a', 1.6, 9, 1.6); l.position.set(-1.5, 2.6, 2); g.add(l); const l2 = new T3.PointLight('#ff6fb0', 1, 8, 1.6); l2.position.set(2, 2.4, 1.5); g.add(l2); }
}
const SETS = {
  street(g, sh) {      // the party: night, string lights, lanterns, balloons, houses, pines, fireworks, confetti
    lightsFor(g, 1); skyDome(g, 1);
    const ft = tex(512, 512, (x, w, h) => { x.fillStyle = '#c9a9c4'; x.fillRect(0, 0, w, h); x.strokeStyle = '#a98aa6'; x.lineWidth = 4; for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) x.strokeRect(i * 64 + (j % 2) * 32, j * 64, 64, 64);
      for (let i = 0; i < 60; i++) { x.fillStyle = ['#ffd23f', '#ff5d8f', '#7fc4ff', '#2bd47d', '#b98cff'][i % 5]; x.beginPath(); x.arc(hs(i) * w, hs(i + 9) * h, 9, 0, 7); x.fill(); } });
    ft.wrapS = ft.wrapT = T3.RepeatWrapping; ft.repeat.set(6, 6); const fl = new T3.Mesh(new T3.PlaneGeometry(40, 40), new T3.MeshStandardMaterial({map: ft, roughness: .9})); fl.rotation.x = -Math.PI / 2; fl.receiveShadow = true; g.add(fl);
    [[-7, -8, 4, 6, '#e9d7b9', '#a43a3a'], [-2, -11, 5, 7, '#cfe6f5', '#3a5aa4'], [4, -9, 4.5, 6.5, '#f5e3c6', '#2e8a6a'], [9, -8, 4, 5, '#e8c4d8', '#7a3a8a']].forEach(([x, z, w, h, c, r], i) => g.add(at(building(w, h, c, r, i * 31), x, 0, z)));
    for (let i = 0; i < 6; i++) { const tr = grp(at(cyl(.12, .16, 1, '#5a3a22'), 0, .5, 0), at(mesh(new T3.ConeGeometry(.9, 2.2, 8), M('#2d6b4a')), 0, 2, 0), at(mesh(new T3.ConeGeometry(.65, 1.6, 8), M('#3a8a5a')), 0, 3, 0)); g.add(at(tr, -10 + i * 4, 0, -14 - (i % 2) * 2)); }
    for (const x of [-3.4, 3.4]) { g.add(at(cyl(.06, .08, 4, '#3a3a4a'), x, 2, -1.5)); g.add(at(ball(.22, glow('#ffd88a', 2.5), 14), x, 4.05, -1.5)); }
    stringLights(g, -3.4, 3.4, 3.8, -1.5, 26, .7); stringLights(g, -6, 6, 4.4, -5, 34, .9); stringLights(g, -3.4, -8, 3.8, -6, 18, .6);
    for (let i = 0; i < 7; i++) { const b = grp(at(ball(.28, M(['#ff5d8f', '#ffd23f', '#7fc4ff', '#b98cff', '#2bd47d'][i % 5], {roughness: .25}), 16), 0, 0, 0)); b.position.set(-4 + i * 1.4, 2.6 + hs(i) * 1.2, -3 - hs(i + 1) * 3); g.add(b); g.userData.balloons = (g.userData.balloons || []).concat([b]); }
    g.userData.tick = confetti(g, sh.noconfetti ? 0 : 160, 9, 5);
    if (sh.bigscreen) { const t = tex(768, 512); DYN.push([t, (x, w, h, tt, lt) => screenUI(x, w, h, tt, sh.bigscreen.mode, lt), CUR]); const bs = plane(6.4, 4.26, t, true); bs.position.set(sh.bigscreen.x || 0, 5.2, -6.5); g.add(bs);
      g.add(at(rbox(6.8, 4.6, .3, '#1b1d24', .08), sh.bigscreen.x || 0, 5.2, -6.7), at(box(.3, 3, .3, '#2a2c34'), (sh.bigscreen.x || 0) - 2.5, 1.5, -6.7), at(box(.3, 3, .3, '#2a2c34'), (sh.bigscreen.x || 0) + 2.5, 1.5, -6.7)); }
  },
  room(g, sh) {        // the hero's room at night: his desk, his monitor, the party in the window behind him
    lightsFor(g, 1, 0); const lamp = new T3.PointLight('#ffc27a', 2.2, 7, 1.6); lamp.position.set(.9, 2.2, 1.4); lamp.castShadow = true; g.add(lamp);
    const fill = new T3.PointLight('#7f8cff', .8, 9, 1.6); fill.position.set(-1.6, 2.4, -1); g.add(fill);
    const wall = box(10, 5, .2, '#2e5fa8'); wall.position.set(0, 2.5, -1.7); g.add(wall);
    const tt = tex(512, 768, (x, w, h) => { x.fillStyle = '#3a6fbe'; x.fillRect(0, 0, w, h); x.fillStyle = 'rgba(255,255,255,.06)'; for (let i = 0; i < 16; i++) x.fillRect(i * 32, 0, 3, h); });
    wall.material = new T3.MeshStandardMaterial({map: tt, roughness: .9});
    const wv = tex(640, 480); DYN.push([wv, (x, w, h, t) => windowView(x, w, h, t), CUR]); const win = plane(3.2, 2.2, wv, true); win.position.set(-.4, 2.55, -1.58); g.add(win);
    g.add(at(box(3.4, .12, .12, '#f4f2ee'), -.4, 3.7, -1.55), at(box(3.4, .12, .12, '#f4f2ee'), -.4, 1.4, -1.55), at(box(.12, 2.4, .12, '#f4f2ee'), -2.05, 2.55, -1.55), at(box(.12, 2.4, .12, '#f4f2ee'), 1.25, 2.55, -1.55), at(box(.08, 2.3, .08, '#f4f2ee'), -.4, 2.55, -1.55));
    const ft = tex(256, 256, (x, w, h) => { x.fillStyle = '#9a6a3e'; x.fillRect(0, 0, w, h); x.fillStyle = '#86592f'; for (let i = 0; i < 8; i++) x.fillRect(0, i * 32, w, 3); for (let i = 0; i < 8; i++) x.fillRect((i * 97) % w, i * 32, 3, 32); });
    ft.wrapS = ft.wrapT = T3.RepeatWrapping; ft.repeat.set(5, 5); const fl = new T3.Mesh(new T3.PlaneGeometry(12, 12), new T3.MeshStandardMaterial({map: ft, roughness: .8})); fl.rotation.x = -Math.PI / 2; fl.receiveShadow = true; g.add(fl);
    PROPS.desk(g); const mon = PROPS.monitor(g, (sh.monitor || {}).mode || 'daily'); mon.position.set(-.75, 1.08, .55); mon.rotation.y = .5; g.add(mon); g.userData.monitor = mon;
    g.add(at(PROPS.keyboard(), 0, 1.09, .5)); g.add(at(PROPS.clock(sh.clock || '5:00'), .95, 1.08, .55, -.4)); g.add(at(PROPS.mug(), .55, 1.08, .75));
    for (let i = 0; i < 5; i++) g.add(at(rbox(.3, .04, .4, '#f4f2ee', .01), 1.1, 1.09 + i * .045, .3, hs(i) * .3));
    for (let i = 0; i < 4; i++) { const n = box(.12, .12, .005, ['#ffd23f', '#ff5d8f', '#7fc4ff', '#2bd47d'][i]); n.position.set(-1.7 + i * .22, 1.9 + (i % 2) * .2, -1.58); g.add(n); }
  },
  office(g, sh) {      // Big Bull Capital: bright, a big logo, the boss's desk
    lightsFor(g, 0); const wall = box(12, 5, .2, '#efe6d6'); wall.position.set(0, 2.5, -1.8); g.add(wall);
    const logo = plane(3.2, .9, labelTex([[sh.logo || 'BIG BULL CAPITAL', 64, sh.logoCol || '#7d1d2a', .5]], {bg: '#f7f0e2', w: 1024, h: 288})); logo.position.set(0, 3.3, -1.68); g.add(logo);
    g.add(at(box(12, .3, .3, '#2ec4b6'), 0, .15, -1.65), at(box(12, .12, .25, '#ffb020'), 0, 1.8, -1.65));
    const fl = box(14, .1, 12, '#d8d0c4'); fl.position.y = -.05; g.add(fl);
    g.add(at(rbox(2.8, .14, 1.1, '#f4f2ee', .04), 0, 1.0, .6), at(rbox(2.7, .95, .1, '#2ec4b6', .03), 0, .5, 1.12));
    const mon = PROPS.monitor(g, (sh.monitor || {}).mode || 'daily'); mon.position.set(.85, 1.07, .55); mon.rotation.y = -.5; g.add(mon); g.userData.monitor = mon;
    for (const x of [-4, 4]) { const p = grp(at(cyl(.3, .24, .5, '#c86a3a'), 0, .25, 0), at(ball(.5, '#3a8a5a', 10), 0, .85, 0), at(ball(.38, '#4caa6a', 10), .2, 1.2, .1)); g.add(at(p, x, 0, -1)); }
    g.add(at(PROPS.mug(), -.8, 1.07, .7));
  },
  day(g, sh) {        // the street by day: houses and a lemonade stand
    lightsFor(g, 0); skyDome(g, 0); const fl = box(40, .1, 40, '#8fcf6a'); fl.position.y = -.05; g.add(fl); const road = box(40, .02, 3, '#5a5a66'); road.position.set(0, .01, 3.2); g.add(road);
    [[-6, -7, 4, 4, '#f5e3c6', '#c0392b'], [0, -9, 5, 5, '#cfe6f5', '#2e6fa8'], [6, -7, 4, 4.5, '#fde2e4', '#8a3a8a']].forEach(([x, z, w, h, c, r], i) => g.add(at(building(w, h, c, r, 90 + i), x, 0, z)));
    const st = new T3.Group(); st.add(at(rbox(2, 1, .9, '#d9a066', .03), 0, .5, 0)); for (let i = 0; i < 6; i++) st.add(at(box(.34, .1, 1.1, i % 2 ? '#fff' : '#ffd23f'), -.85 + i * .34, 2.05, 0));
    st.add(at(box(.08, 1.6, .08, '#8a5a34'), -.95, 1.3, .4), at(box(.08, 1.6, .08, '#8a5a34'), .95, 1.3, .4));
    const sign = plane(1.8, .55, labelTex([[(sh.sign || 'LEMONADE'), 120, sh.signCol || '#1b1b28', .5]], {bg: '#fff7c2', w: 1024, h: 312})); sign.position.set(0, .62, .46); st.add(sign);
    for (let i = 0; i < 3; i++) st.add(at(cyl(.07, .06, .2, '#fff2a0'), -.4 + i * .4, 1.1, .1)); g.add(at(st, 0, 0, .9));
  },
  black(g) { const b = box(30, 30, .1, '#05030a'); b.position.z = -3; g.add(b); g.add(new T3.AmbientLight('#ffffff', .2)); },
  letter(g, sh) {      // the letter on the table
    lightsFor(g, 0, 0); const tb = box(4, .1, 3, '#8a5a34'); tb.position.y = .95; g.add(tb);
    const lt = plane(.9, 1.15, labelTex([['BIG BULL CAPITAL', 56, '#7d1d2a', .12], ['Dear trader,', 46, '#333', .3], ...((sh.letter || ['Thank you for', 'selling my tie.']).map((s, i) => [s, 64, '#1b1b28', .5 + i * .14]))], {w: 768, h: 1000, bg: '#fdfaf2'}));
    lt.rotation.x = -Math.PI / 2; lt.rotation.z = .08; lt.position.set(0, 1.01, 0); g.add(lt);
  },
};

// ---------------------------------------------------------------- the bear (the cliffhanger): blocky, huge, red-eyed, out of the portal
function bear() {
  const b = new T3.Group(), fur = '#3b2618', muz = '#8a6040'; const body = rbox(2.2, 2.4, 1.6, fur, .3); body.position.y = 1.6; b.add(body);
  const head = new T3.Group(); head.position.set(0, 3.35, .15); b.add(head); head.add(rbox(1.6, 1.3, 1.3, fur, .3)); head.add(at(rbox(.7, .45, .45, muz, .15), 0, -.2, .72)); head.add(at(rbox(.26, .16, .1, '#140c08', .05), 0, -.08, .96));
  for (const s of [-1, 1]) { head.add(at(rbox(.42, .42, .25, fur, .12), s * .62, .7, 0)); head.add(at(rbox(.22, .22, .1, muz, .06), s * .62, .7, .1)); const e = ball(.12, glow('#ff2020', 4), 14); e.position.set(s * .36, .18, .66); head.add(e); }
  const jaw = new T3.Group(); jaw.position.set(0, -.42, .6); head.add(jaw); jaw.add(at(rbox(.62, .16, .4, muz, .06), 0, -.08, .12)); for (let i = 0; i < 5; i++) { const tth = mesh(new T3.ConeGeometry(.045, .14, 6), M('#f4f2ee')); tth.position.set(-.2 + i * .1, .04, .26); jaw.add(tth); }
  for (let i = 0; i < 5; i++) { const tth = mesh(new T3.ConeGeometry(.045, .14, 6), M('#f4f2ee')); tth.rotation.x = Math.PI; tth.position.set(-.2 + i * .1, -.38, .86); head.add(tth); }
  const arms = []; for (const s of [-1, 1]) { const a = new T3.Group(); a.position.set(s * 1.3, 2.5, .1); a.add(at(rbox(.7, 1.8, .7, fur, .25), 0, -.8, 0)); for (let i = 0; i < 3; i++) { const c = mesh(new T3.ConeGeometry(.06, .3, 6), M('#e8e2d6')); c.rotation.x = Math.PI * .9; c.position.set(-.2 + i * .2, -1.75, .32); a.add(c); } b.add(a); arms.push(a); }
  b.userData = {head, jaw, arms}; return b;
}

// ---------------------------------------------------------------- the inventive props (2026-11-25, the owner: "more inventive and creative")
function rampOf(sh) {        // the real price line as a giant ramp across the plaza: people ride it, slide down it, stand on its peak
  const r = sh.ramp, P0 = r.prices || R.prices || [1, 2], i0 = Math.floor((r.from || 0) * (P0.length - 1)), i1 = Math.ceil((r.to == null ? 1 : r.to) * (P0.length - 1)), P = P0.slice(i0, i1 + 1);
  const lo = Math.min(...P), hi = Math.max(...P), w = r.w || 4.6, hgt = r.h || 6, X = i => -w / 2 + i / (P.length - 1) * w, Y = v => .25 + (v - lo) / (hi - lo + 1e-9) * hgt;
  const pts = P.map((v, i) => new T3.Vector3(X(i), Y(v), 0)), curve = new T3.CatmullRomCurve3(pts, false, 'centripetal', .3);
  const up = P[P.length - 1] >= P[0], col = r.color || (up ? '#2bd47d' : '#e8394a');
  const g = new T3.Group(), track = mesh(new T3.TubeGeometry(curve, Math.max(60, P.length * 3), .28, 10, false), M(col, {roughness: .35, emissive: new T3.Color(col).multiplyScalar(.25)}));
  g.add(track); const N = 14; for (let i = 0; i <= N; i++) { const q = curve.getPointAt(i / N); g.add(at(cyl(.07, .07, q.y, '#3a3a4a', 8), q.x, q.y / 2, 0)); }
  const lt = labelTex([[r.label || '???', 120, '#ffd23f', .5]], {bg: '#1b1d2c', w: 512, h: 200}), sign = plane(1.6, .62, lt, true); const top = curve.getPointAt(0); sign.position.set(top.x, top.y + 1.1, 0); g.add(sign);
  g.userData = {curve, P, lo, hi}; return g;
}
function crate(sh) {          // a huge mystery crate: ??? on every face; at `open` its lid flies off and the name rises out on a sign
  const g = new T3.Group(), wood = '#c98d4a', S = 2.4;
  g.add(at(rbox(S, S, S, wood, .08), 0, S / 2, 0)); const qt = labelTex([['???', 200, '#1b1b28', .52]], {bg: '#f2d6a2', w: 512, h: 512});
  for (const [x, z, ry] of [[0, S / 2 + .01, 0], [S / 2 + .01, 0, Math.PI / 2], [-S / 2 - .01, 0, -Math.PI / 2]]) { const f = plane(S * .8, S * .8, qt); f.position.set(x, S / 2, z); f.rotation.y = ry; g.add(f); }
  for (const y of [.15, S - .15]) for (const z of [S / 2 + .02, -S / 2 - .02]) g.add(at(box(S + .04, .18, .05, '#8a5a2a'), 0, y, z));
  const lid = rbox(S + .1, .2, S + .1, '#b07a3c', .06); lid.position.y = S + .1; g.add(lid);
  const name = plane(2.6, .9, labelTex([[sh.crate.name || 'ETSY', 150, '#ffffff', .5]], {bg: sh.crate.color || '#f1641e', w: 900, h: 312}), true); name.position.set(0, S * .6, 0); name.visible = false; g.add(name);
  g.userData = {lid, name, S}; return g;
}
function coin() { const g = new T3.Group(); const c = cyl(1.1, 1.1, .22, M('#f7a51a', {metalness: .6, roughness: .3}), 40); c.rotation.x = Math.PI / 2; g.add(c);
  const f = plane(1.7, 1.7, tex(512, 512, (x, w, h) => { x.fillStyle = '#f7a51a'; x.beginPath(); x.arc(w / 2, h / 2, w / 2, 0, 7); x.fill(); x.strokeStyle = '#c47a0a'; x.lineWidth = 22; x.beginPath(); x.arc(w / 2, h / 2, w / 2 - 30, 0, 7); x.stroke();
    x.fillStyle = '#fff6dc'; x.font = '900 300px Montserrat, sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText('\u20BF', w / 2, h / 2 + 14); }), true); f.material.transparent = true; f.position.z = .115; g.add(f);
  const b = f.clone(); b.rotation.y = Math.PI; b.position.z = -.115; g.add(b); return g; }

// ---------------------------------------------------------------- build every shot
const SH = [];
function build() {
  for (const [k, sh] of R.shots.entries()) {
    const g = new T3.Group(); g.visible = false; scene.add(g); CUR = g; (SETS[sh.set] || SETS.room)(g, sh); g.userData.k = k;
    const cast = (sh.cast || []).map((c, i) => { const p = person(c.look || c.who, (c.seed || 1) + i * 3); p.mood = c.face || p.L.face; at(p.root, (c.at || [0, 0])[0], 0, (c.at || [0, 0])[1], c.ry || 0); g.add(p.root);
      if ((c.pose || '').startsWith('huss')) ghostsFor(p); if (c.prop) { const pr = (PROPS[c.prop] || PROPS.rock)(); pr.position.set(0, -.86, .1); p.armR.add(pr); } return [p, c]; });
    if (sh.crowd) { const n = sh.crowd.n || 10; for (let i = 0; i < n; i++) { const c = PARTY[i % PARTY.length], L = {shirt: c[0], pants: c[1], skin: c[2], hair: c[3], hairCol: c[4], face: sh.crowd.face || (i % 3 ? 'happy' : 'grin'), hat: i % 4 === 0 ? 'party' : null};
      const p = person(L, i * 5 + 2), row = Math.floor(i / 5); at(p.root, (i % 5 - 2) * 1.05 + (row % 2) * .5 + (hs(i) - .5) * .3, 0, -1 - row * 1.3 - hs(i + 3) * .4, (hs(i + 5) - .5) * .6); g.add(p.root); cast.push([p, {pose: sh.crowd.pose || 'dance', crowd: 1}]); } }
    let B = null; if (sh.bear) { B = bear(); g.add(B); }
    let RP = null; if (sh.ramp) { RP = rampOf(sh); RP.position.set(sh.ramp.x || 0, 0, sh.ramp.z || -1.2); g.add(RP); }
    let CR = null; if (sh.crate) { CR = crate(sh); CR.position.set(sh.crate.x || 0, 0, sh.crate.z || -1); g.add(CR); }
    let CO = null; if (sh.coin) { CO = coin(); g.add(CO); }
    let portal = null; if (sh.portal) { const t = tex(512, 512); DYN.push([t, (x, w, h, tt) => swirl(x, w, h, tt), CUR]); portal = new T3.Mesh(new T3.CircleGeometry(1.8, 48), new T3.MeshBasicMaterial({map: t, transparent: true, toneMapped: false}));
      portal.position.set(sh.portal.x || -.4, sh.portal.y || 2.5, sh.portal.z || -1.5); g.add(portal); const pl = new T3.PointLight('#c040ff', 3, 10, 1.4); pl.position.set(portal.position.x, portal.position.y, portal.position.z + 1); g.add(pl); g.userData.plight = pl; }
    if (sh.monitor && g.userData.monitor) g.userData.mode = sh.monitor.mode;
    SH.push({sh, g, cast, B, portal, RP, CR, CO});
  }
}

// ---------------------------------------------------------------- the camera: framed on whom the shot is about, a slow push, a handheld drift
const V3 = (a) => new T3.Vector3(a[0], a[1], a[2]);
function camFor(s, lt, t) {
  const sh = s.sh, c = sh.cam || {}, main = s.cast[0] ? s.cast[0][0].root.position : new T3.Vector3(), d = Math.max(.6, sh.t1 - sh.t0), u = cl(lt / d);
  const preset = {face: [[0, 1.95, 3.1], [0, 1.78, 0], 30], mid: [[0, 1.9, 5.4], [0, 1.45, 0], 32], wide: [[0, 2.6, 11], [0, 1.6, -1], 34], top: [[0, 2.9, 2.4], [0, 1.1, .45], 34],
    low: [[0, .9, 4.6], [0, 1.6, 0], 34], monitor: [[.35, 1.62, -.55], [-.75, 1.58, .55], 34], over: [[.9, 2.2, -1.6], [-.3, 1.4, .6], 38]}[c.shot || 'mid'];
  let p = V3(c.p || preset[0]), l = V3(c.l || preset[1]); const off = c.p ? new T3.Vector3() : (['monitor', 'over'].includes(c.shot) ? new T3.Vector3() : new T3.Vector3(main.x, 0, main.z)); p.add(off); l.add(off);
  const push = c.push == null ? .12 : c.push; p.lerp(l, push * ease(u)); const side = c.side == null ? .08 : c.side; p.x += side * (1 - 2 * u);
  p.x += .02 * Math.sin(t * .9) + .012 * Math.sin(t * 2.1); p.y += .015 * Math.sin(t * 1.3);
  let sk = c.shake || 0; if (s.B) sk = Math.max(sk, .05 * Math.max(0, Math.sin(lt * 3))); if (sk) { p.x += sk * Math.sin(t * 61); p.y += sk * Math.sin(t * 47); }
  return [p, l, c.fov || preset[2]];
}

// ---------------------------------------------------------------- one frame
function shotAt(t) { const k = R.shots.findIndex(s => t < s.t1); return k < 0 ? R.shots.length - 1 : k; }
function render(t) {
  const k = shotAt(t), s = SH[k], sh = s.sh, lt = t - sh.t0;
  SH.forEach((q, i) => { q.g.visible = i === k; });
  scene.background = new T3.Color(sh.set === 'day' || sh.set === 'office' ? '#bfe6ff' : '#0f0d24'); scene.fog = sh.set === 'street' ? new T3.Fog('#2a2050', 14, 45) : null;
  grade.uniforms.warm.value = sh.set === 'room' ? .7 : .45; grade.uniforms.vig.value = sh.bear || sh.portal ? .6 : .35;
  for (const [p, c] of s.cast) { let ps = c.pose || 'stand'; if (c.then && lt > c.then[0]) ps = c.then[1]; if (c.face2 && lt > c.face2[0]) p.mood = c.face2[1]; pose(p, ps, t, lt);
    if (c.walk) { const u = cl(lt / Math.max(.5, sh.t1 - sh.t0)); p.root.position.x = lerp(c.walk[0][0], c.walk[1][0], u); p.root.position.z = lerp(c.walk[0][1], c.walk[1][1], u); }
    if (c.grow) p.root.scale.setScalar(lerp(c.grow[0], c.grow[1], ease(cl(lt / 1.2)))); }
  if (s.g.userData.tick) s.g.userData.tick(t);
  (s.g.userData.balloons || []).forEach((b, i) => { b.position.y += Math.sin(t * 1.2 + i) * .002; b.rotation.z = .1 * Math.sin(t + i); });
  if (s.B) { const b = sh.bear, B = s.B, u = cl(lt / (b.in || 1.6)); const z0 = b.from == null ? -3.5 : b.from, z1 = b.to == null ? -1 : b.to; B.position.set(b.x == null ? -.3 : b.x, b.y || 0, lerp(z0, z1, ease(u)));
    const sc = b.grow ? lerp(b.grow[0], b.grow[1], ease(cl(lt / 1.4))) : (b.scale || 1); B.scale.setScalar(sc * (b.emerge ? .3 + .7 * ease(u) : 1));
    B.userData.jaw.rotation.x = (b.roar ? .55 : .12) * Math.max(0, Math.sin(lt * (b.roar ? 3.2 : 1.5))); B.userData.head.rotation.y = .12 * Math.sin(t * .8); B.userData.arms.forEach((a, i) => { a.rotation.x = -.5 - .4 * Math.sin(t * 2 + i * 2); });
    if (b.walk) B.position.x = lerp(b.walk[0], b.walk[1], cl(lt / (sh.t1 - sh.t0))); }
  if (s.RP) for (const [p, c] of s.cast) if (c.ride) { const u = lerp(c.ride[0], c.ride[1], (c.ride[2] ? ease : (x => x))(cl(lt / Math.max(.6, sh.t1 - sh.t0 - .2)))), cu = s.RP.userData.curve, q = cu.getPointAt(cl(u)), tg = cu.getTangentAt(cl(u));
      p.root.position.set(q.x + s.RP.position.x, q.y + .2, s.RP.position.z + .05); p.root.rotation.set(0, c.ry || 0, Math.atan2(tg.y, tg.x) * .6); }
  if (s.CR) { const o = sh.crate.open, d = lt - (o == null ? 99 : o), U = s.CR.userData; s.CR.rotation.z = d < 0 ? .03 * Math.sin(t * 30) * cl(lt / 1) * (sh.crate.rattle ? 1 : 0) : 0;
    if (d > 0) { U.lid.position.set(1.8 * d, U.S + .1 + 4 * d - 6 * d * d, 0); U.lid.rotation.z = -3 * d; U.lid.visible = d < 1.2; U.name.visible = true; U.name.position.y = U.S * .6 + 1.4 * ease(cl(d / .6)); } }
  if (s.CO) { const c = sh.coin; let x = c.x || 0, y = c.y == null ? 1.2 : c.y; if (c.roll) { const u = cl(lt / Math.max(.6, sh.t1 - sh.t0)); x = lerp(c.roll[0], c.roll[1], u); y = 1.1 + (c.drop ? 2.5 * Math.max(0, 1 - lt / .5) ** 2 : 0); s.CO.rotation.z = -(x - c.roll[0]) / 1.1; }
    else { s.CO.rotation.y = t * (c.spin || 1.6); y += .1 * Math.sin(t * 2); } s.CO.position.set(x, y, c.z || 0); s.CO.scale.setScalar(c.scale || 1); }
  if (s.portal) { const pu = sh.portal.grow ? ease(cl(lt / 1.2)) : 1; s.portal.scale.setScalar(.05 + .95 * pu); s.portal.rotation.z = -t * .6; s.g.userData.plight.intensity = 2 + 1.5 * Math.sin(t * 9); }
  for (const [tx, draw, owner] of DYN) { const o = tx.userData; if (!o.c || (owner && owner !== s.g)) continue; draw(o.x, o.c.width, o.c.height, t, lt); tx.needsUpdate = true; }
  const [p, l, fov] = camFor(s, lt, t); cam.position.copy(p); cam.lookAt(l); cam.fov = fov; cam.updateProjectionMatrix();
  bokeh.uniforms.focus.value = p.distanceTo(l); bokeh.uniforms.aperture.value = (sh.cam || {}).aperture || .012;
  comp.render();
  // the flat layer: a white pop on the cut, the yellow word, the card
  ox.clearRect(0, 0, W, H);
  if (lt < .08 && k > 0 && sh.flash !== false) { ox.fillStyle = `rgba(255,255,255,${.25 * (1 - lt / .08)})`; ox.fillRect(0, 0, W, H); }
  if (sh.dark) { ox.fillStyle = `rgba(0,0,0,${cl(lt / .4) * sh.dark})`; ox.fillRect(0, 0, W, H); }
  const cap = (R.caps || []).find(q => t >= q.t0 && t < q.t1);
  if (cap && !sh.card) { const pp = back(cl((t - cap.t0) / .12)), size = cap.text.length > 9 ? 70 : 82; ox.save(); ox.translate(540, 1318); ox.scale(pp, pp); ox.font = `700 ${size}px Fredoka, Montserrat, sans-serif`; ox.textAlign = 'center'; ox.textBaseline = 'middle'; ox.lineJoin = 'round';
    ox.lineWidth = size * .2; ox.strokeStyle = '#3a2208'; ox.strokeText(cap.text, 0, 0); ox.fillStyle = '#ffd43a'; ox.fillText(cap.text, 0, 0); ox.restore(); }
  for (const [p, c] of s.cast) if (c.say2 && lt > (c.say2[0] || 0) && !window.__coverOn) {      // a speech bubble over a head
    const v = new T3.Vector3(); p.head.getWorldPosition(v); v.y += .7 * p.root.scale.y; v.project(cam); const bx = (v.x + 1) / 2 * W, by = (1 - v.y) / 2 * H, txt = c.say2[1], pp = back(cl((lt - c.say2[0]) / .2));
    ox.save(); ox.translate(cl(bx, 230, W - 230), cl(by - 60, 300, 1100)); ox.scale(pp, pp); ox.font = '700 54px Fredoka, Montserrat, sans-serif'; const tw = Math.min(760, ox.measureText(txt).width + 70);
    ox.fillStyle = '#ffffff'; ox.strokeStyle = '#1b1b28'; ox.lineWidth = 8; ox.beginPath(); ox.roundRect(-tw / 2, -62, tw, 104, 40); ox.fill(); ox.stroke(); ox.beginPath(); ox.moveTo(-20, 40); ox.lineTo(0, 82); ox.lineTo(24, 40); ox.closePath(); ox.fill(); ox.stroke();
    ox.fillStyle = '#1b1b28'; ox.textAlign = 'center'; ox.textBaseline = 'middle'; ox.fillText(txt, 0, -10, 700); ox.restore(); }
  if (window.__coverOn && R.cover) { thumb(R.cover); return; }
  if (sh.card) { const a = cl(lt / .3); ox.fillStyle = `rgba(4,2,10,${.9 * a})`; ox.fillRect(0, 0, W, H); ox.globalAlpha = a; ox.textAlign = 'center'; ox.textBaseline = 'middle';
    ox.font = '700 120px Fredoka, Montserrat, sans-serif'; ox.lineWidth = 22; ox.lineJoin = 'round'; ox.strokeStyle = '#3a2208'; (sh.card.lines || [sh.card]).forEach((s2, i) => { const y = 880 + i * 140; ox.strokeText(s2, 540, y); ox.fillStyle = i ? '#ffffff' : '#ffd43a'; ox.fillText(s2, 540, y); });
    ox.font = '700 44px Montserrat, sans-serif'; ox.fillStyle = '#ffffff'; ox.fillText(sh.card.foot || 'memestreet.net', 540, 1240); ox.globalAlpha = 1; }
}
function thumb(C) {           // the thumbnail: each reel its own design; only the Daily's story reel carries the DAILY #N badge
  const L = C.lines || [R.title], col = C.color || '#ffd43a', style = C.style || 'top'; ox.clearRect(0, 0, W, H);
  const big = (s, x, y, size, fill, stroke = '#1a1020', rot = 0) => { ox.save(); ox.translate(x, y); ox.rotate(rot); ox.font = `700 ${size}px Fredoka, Montserrat, sans-serif`; ox.textAlign = 'center'; ox.textBaseline = 'middle'; ox.lineJoin = 'round';
    while (ox.measureText(s).width > 980 && size > 60) { size -= 4; ox.font = `700 ${size}px Fredoka, Montserrat, sans-serif`; } ox.lineWidth = size * .22; ox.strokeStyle = stroke; ox.strokeText(s, 0, 0); ox.fillStyle = fill; ox.fillText(s, 0, 0); ox.restore(); };
  if (style === 'top') { const g = ox.createLinearGradient(0, 200, 0, 760); g.addColorStop(0, 'rgba(10,6,20,.75)'); g.addColorStop(1, 'rgba(10,6,20,0)'); ox.fillStyle = g; ox.fillRect(0, 0, W, 760);
    L.forEach((l, i) => big(l.toUpperCase(), 540, 360 + i * 150, 150, i === L.length - 1 ? col : '#ffffff')); }
  else if (style === 'ribbon') { ox.save(); ox.translate(540, 1180); ox.rotate(-.07); ox.fillStyle = col; ox.fillRect(-640, -150, 1280, 300); ox.restore(); L.forEach((l, i) => big(l.toUpperCase(), 540, 1110 + i * 140 - (L.length - 1) * 20, 130, '#ffffff', '#1a1020', -.07)); }
  else if (style === 'bubble') { ox.save(); ox.translate(540, 470); ox.rotate(-.04); ox.fillStyle = '#fff'; ox.strokeStyle = '#1b1b28'; ox.lineWidth = 14; ox.beginPath(); ox.roundRect(-430, -190, 860, 380, 90); ox.fill(); ox.stroke();
    ox.beginPath(); ox.moveTo(-40, 185); ox.lineTo(10, 300); ox.lineTo(70, 185); ox.closePath(); ox.fill(); ox.stroke(); ox.restore(); L.forEach((l, i) => big(l.toUpperCase(), 540, 420 + i * 130 - (L.length - 1) * 40, 120, i === L.length - 1 ? col : '#1b1b28', '#ffffff')); }
  else { const g = ox.createLinearGradient(0, 1100, 0, 1700); g.addColorStop(0, 'rgba(10,6,20,0)'); g.addColorStop(1, 'rgba(10,6,20,.85)'); ox.fillStyle = g; ox.fillRect(0, 1100, W, 820);
    L.forEach((l, i) => big(l.toUpperCase(), 540, 1380 + i * 150 - (L.length - 1) * 75, 150, i === L.length - 1 ? col : '#ffffff')); }
  if (C.badge) { ox.save(); ox.font = '800 44px Montserrat, sans-serif'; ox.letterSpacing = '5px'; const bw = ox.measureText(C.badge).width + 70; ox.fillStyle = '#ffc83d'; ox.beginPath(); ox.roundRect(540 - bw / 2, 250, bw, 84, 42); ox.fill();
    ox.fillStyle = '#111'; ox.textAlign = 'center'; ox.textBaseline = 'middle'; ox.fillText(C.badge, 540, 294); ox.restore(); }
}
window.render = render;
window.overlaps = () => [];
window.ready = Promise.all([document.fonts.load('700 40px Fredoka'), document.fonts.load('800 40px Montserrat')]).then(() => document.fonts.ready).then(() => { build(); render(0); return true; });
