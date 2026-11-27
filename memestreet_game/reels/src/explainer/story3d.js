/* Meme Street's story reel, the 3D picture. The owner, 2026-11-22: "it should be 3d like the previous reel was, except it goes
   through all the events and story like this current reel"; 2026-11-23, on the first 3D cut (small props standing in grid cells
   of dark, empty sets): "i still don't like it... make the reel better".
   So every sentence is a SHOT, not a grid: its own low-poly set at real scale, one or two subjects standing in it at real size,
   and the camera placed so that they fill the frame (the camera is fitted to the subjects, never the subjects to a cell). The
   sets stand in a row and the camera flies from one to the next; inside a shot it pushes in. What is written (header, the words
   slammed on a scene, tags, captions) is story.js's flat layer on top.
   Nothing overlaps: subjects stand side by side with a gap, the camera is solved so their boxes stay inside the picture zone,
   the words have their own band, and overlaps(t) measures every box (make.py does not make a reel that has one).
   The people (the owner, 2026-11-23, sending a second model reel: "you can use this animation style too"): toy figures with a
   big round head, a face DRAWN on it that changes with what they feel (calm, joy, smug, shock, sad; they blink), a dark outline,
   short arms and legs moved here in code (no rig), so a pose is a few numbers. Only the style is that reel's: no character,
   costume or picture of it is copied.
   Everything is a pure function of t (render(t)). The furniture is CC0 (../oneshot/assets/CREDITS.json). */
(function () {
'use strict';
const T3 = THREE, R = window.__R, S = window.S2, W = 1080, H = 1920, Q = window.__Q || 2 / 3, CW = Math.round(W * Q), CH = Math.round(H * Q);
const GAP = 30, FOV = 45, FLY = .32;
const BAND = [70, 262, 940, 236], ZONE = band => band ? [82, 524, 916, 736] : [82, 274, 916, 986];     // px: the words' band, the picture zone
T3.ColorManagement.legacyMode = false;       // colours are written as on screen (sRGB) and lit in linear light
const cl = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x)), lerp = (a, b, k) => a + (b - a) * k;
const ease = k => k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
const hsh = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

const cv = document.getElementById('gl'), oc = document.getElementById('c'), ox = oc.getContext('2d');
const rn = new T3.WebGLRenderer({canvas: cv, antialias: false, preserveDrawingBuffer: true});
rn.setSize(CW, CH, false); rn.setPixelRatio(1); rn.shadowMap.enabled = true; rn.shadowMap.type = T3.PCFSoftShadowMap;
const scene = new T3.Scene(), cam = new T3.PerspectiveCamera(FOV, CW / CH, .3, 220);
// the lens: the scene in linear light -> depth of field (the far set soft, as the earlier 3D reel) -> film curve and screen colours
const comp = new T3.EffectComposer(rn, new T3.WebGLRenderTarget(CW, CH, {type: T3.HalfFloatType, samples: Q >= 1 ? 4 : 0}));
comp.addPass(new T3.RenderPass(scene, cam));
const bokeh = new T3.BokehPass(scene, cam, {focus: 8, aperture: .0055, maxblur: .012, width: CW, height: CH});      // (the third model's lens: the set behind melts away) comp.addPass(bokeh);
comp.addPass(new T3.ShaderPass({uniforms: {tDiffuse: {value: null}}, vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }',
  fragmentShader: 'uniform sampler2D tDiffuse; varying vec2 vUv; void main(){ vec3 x = texture2D(tDiffuse, vUv).rgb * .95; x = clamp((x * (2.51 * x + .03)) / (x * (2.43 * x + .59) + .14), 0., 1.); x = pow(x, vec3(1. / 2.2)); float l = dot(x, vec3(.299, .587, .114)); x = mix(vec3(l), x, 1.18); x *= vec3(1.04, .99, 1.03); vec2 d = vUv - .5; x *= 1. - .55 * dot(d * vec2(1.2, .9), d * vec2(1.2, .9)); gl_FragColor = vec4(clamp(x, 0., 1.), 1.); }'}));

// ---------------------------------------------------------------- materials, textures
const MC = {};
const M = (col, o = {}) => { const k = col + JSON.stringify(o); return MC[k] || (MC[k] = new T3.MeshStandardMaterial(Object.assign({color: col, roughness: .75, metalness: .05, flatShading: true}, o))); };
function canvasTex(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; const x = c.getContext('2d'); if (draw) draw(x, w, h);
  const t = new T3.CanvasTexture(c); t.encoding = T3.sRGBEncoding; t.anisotropy = 8; t.userData = {c, x}; return t; }
const lit = (map, k = 1.25) => new T3.MeshBasicMaterial({map, color: new T3.Color(k, k, k)});                 // a screen: it shines by itself
const glowM = (col, k = 1.5) => new T3.MeshBasicMaterial({color: new T3.Color(col).multiplyScalar(k)});
const DYN = [];      // textures redrawn every frame: [texture, (x, w, h, t) => {}, item]
function drawK(kind, it, lt, x, w, h, bgc) {     // one of story.js's flat drawings filling a texture
  const k = S.K[kind], old = S.ctx(x); x.save(); x.clearRect(0, 0, w, h); if (bgc) { x.fillStyle = bgc; x.fillRect(0, 0, w, h); }
  const s = Math.min(w / k[0], h / k[1]); x.translate((w - k[0] * s) / 2, (h - k[1] * s) / 2); x.scale(s, s); k[2](it, lt, 1, it.dur || 3); x.restore(); S.ctx(old);
}
function screen(w, h, px, draw, it) {            // a lit screen plane, redrawn every frame while its prop is on camera
  const t = canvasTex(Math.round(px * w / h), px), m = new T3.Mesh(new T3.PlaneGeometry(w, h), lit(t));
  draw(t.userData.x, t.userData.c.width, t.userData.c.height, 0); DYN.push([t, draw, it]); return m;
}
function label(text, w, h, fg = '#fff', bg = '#14182b', px = 160) {
  const t = canvasTex(Math.round(px * w / h), px, (x, cw, ch) => { x.fillStyle = bg; x.fillRect(0, 0, cw, ch); const old = S.ctx(x); S.txt(String(text).toUpperCase(), cw / 2, ch / 2 + 4, ch * .62, fg, cw * .9); S.ctx(old); });
  return new T3.Mesh(new T3.PlaneGeometry(w, h), lit(t, 1.1));
}
const box = (w, h, d, col, o) => { const m = new T3.Mesh(new T3.BoxGeometry(w, h, d), M(col, o)); m.castShadow = m.receiveShadow = true; return m; };
const cyl = (r1, r2, h, col, seg = 12, o) => { const m = new T3.Mesh(new T3.CylinderGeometry(r1, r2, h, seg), M(col, o)); m.castShadow = true; m.receiveShadow = true; return m; };
const ball = (r, col, o) => { const m = new T3.Mesh(new T3.IcosahedronGeometry(r, 1), M(col, o)); m.castShadow = true; return m; };
const cone = (r, h, col, seg = 6, o) => { const m = new T3.Mesh(new T3.ConeGeometry(r, h, seg), M(col, o)); m.castShadow = true; return m; };
const at = (m, x, y, z, ry = 0) => { m.position.set(x, y, z); m.rotation.y = ry; return m; };
const grp = (...a) => { const g = new T3.Group(); a.forEach(m => g.add(m)); return g; };
const brand = n => S.brandColor(n);

// ---------------------------------------------------------------- models
const loader = new T3.GLTFLoader(), cache = {};
const load = p => cache[p] || (cache[p] = new Promise((ok, no) => loader.load('../oneshot/assets/' + p, ok, undefined, e => no(new Error(p)))));
async function glb(name, h) {                    // a piece of furniture, h tall, standing on the floor at its centre
  const g = (await load('props/' + name + '.glb')).scene.clone(true), b = new T3.Box3().setFromObject(g), s = new T3.Vector3(); b.getSize(s);
  g.scale.setScalar(h / s.y); const b2 = new T3.Box3().setFromObject(g), c = new T3.Vector3(); b2.getCenter(c); g.position.set(-c.x, -b2.min.y, -c.z);
  g.traverse(m => { if (m.isMesh) { m.castShadow = m.receiveShadow = true; } }); return grp(g);
}
// The people, as the owner's third model reel draws them (2026-11-23, "How Bats Almost Won WW2": "copy the style"): flat 2D
// cartoon cut-outs standing in the 3D world, always facing the camera: a big white head with a thick black outline, huge
// eyes, a drawn mouth that shows the feeling, a coloured costume with an outline, stick legs, thin arms with round hands.
// Only the style is the model's: these people are drawn here from nothing.
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
function toon(look, color, seed, pose) {          // -> {root: a group holding a camera-facing cut-out, its feet at y 0}
  const tex = canvasTex(CW2, CH2), sp = new T3.Sprite(new T3.SpriteMaterial({map: tex, transparent: true, alphaTest: .35})), H = 1.9, Wd = H * CW2 / CH2;
  sp.center.set(.5, 0); sp.scale.set(Wd, H, 1); const root = grp(sp), head = new T3.Group(); head.position.set(0, H * (1 - (300 - 112) / CH2) + .02, 0); root.add(head);
  const sh = new T3.Mesh(new T3.CircleGeometry(.34, 24), new T3.MeshBasicMaterial({color: '#000000', transparent: true, opacity: .25, depthWrite: false})); sh.rotation.x = -Math.PI / 2; sh.position.y = .01; root.add(sh);
  const p = {root, sp, head, tex, look: look || 'casual', color, pose: pose || 'stand', seed, mir: false, glasses: look === 'suit' && seed % 2 === 0, tache: seed % 3 === 1};
  root.userData.proxy = [-Wd * .5, 0, -.15, Wd * .5, H, .15]; drawToon(tex.userData.x, p, 0); tex.needsUpdate = true; return p;
}
function poseToon(p, t) { drawToon(p.tex.userData.x, p, t); p.tex.needsUpdate = true; }
function proxyOf(p) { return p.root.userData.proxy; }
const actor = (look, color, seed, pose) => toon(look, color, seed, pose);
const seedOf = id => [...String(id)].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) % 9973, 7);      // (one cast member looks the same in every shot: hair, glasses, moustache)

// The product: what the company makes, modelled from its real parts in models3d.js (2026-11-26, the owner: "more realistic ...
// have more panels so it can BE a car"). About 1 unit wide (a car or van about 2 long); userData.late = the parts the factory fits last.
const MOD = window.Models3D({T3, S, rn, canvasTex, label, glowM}), BIG = k => k === 'car' || k === 'van';
const productMesh = (kind, col, text) => MOD.product(kind, col, text);

// ---------------------------------------------------------------- the subjects of a shot: (it) -> {g: a group at real size, its base at y 0, facing +z; tick(t); lift: its base above the floor}
const PROPS = {
  person(it) { const c = R.cast[it.who] || {}, p = actor(c.look, c.color, seedOf(it.who), it.pose); return {g: p.root, actor: p, tick: t => poseToon(p, t)}; },
  crowd(it) { const g = new T3.Group(), P = [], cols = ['#e8394a', '#2f7cf6', '#9b59d0', '#22b573', '#f28c28'], looks = ['casual', 'woman', 'hoodie', 'woman', 'casual'], pos = [[-.5, 0], [.5, 0], [-1, -.8], [0, -.85], [1, -.8]];
    for (let i = 0; i < 5; i++) { const p = actor(looks[i], cols[i], i + 3 + (it.seed || 0), it.pose); p.root.position.set(pos[i][0], 0, pos[i][1]); p.root.rotation.y = -pos[i][0] * .14; g.add(p.root); P.push(p); }     // two in front, three behind
    return {g, tick: t => P.forEach(p => poseToon(p, t))}; },
  building(it) { const g = MOD.tower(brand(it.brand)); g.add(at(MOD.rbox(2.46, .78, .06, .02, MOD.DARK), 0, 5.02, 1.07)); g.add(at(label(it.text || '', 2.3, .62, '#fff', '#14182b'), 0, 5.02, 1.105)); return {g}; },      // (an office tower with a glass wall, doors and a canopy; it was one box with a picture of windows)
  factory(it) { const col = brand(it.brand), g = new T3.Group(), N = BIG(it.product) ? 2 : 3, L = 3.6, X = MOD, OR = X.PM('#f29a2e', {roughness: .35, envMapIntensity: .7}), DK = X.PM('#2b2f3a', {roughness: .45, envMapIntensity: .5});
    // the product being made: a conveyor (a rubber belt between steel rails, a roller at each end, legs with feet), two jointed robot arms with grippers fitting its parts, a scanner on a painted gantry
    g.add(at(X.rbox(L, .1, .82, .03, X.RUBBER), 0, 1, 0)); for (const z of [-.45, .45]) g.add(at(X.rbox(L + .12, .2, .07, .02, X.STEEL), 0, .95, z)); for (const x of [-L / 2, L / 2]) g.add(at(X.cyl(.1, .1, .84, X.STEEL, 20, 'z'), x, .98, 0));
    for (let k = 0; k < 4; k++) for (const z of [-.4, .4]) { const x = -L / 2 + .25 + k * (L - .5) / 3; g.add(at(X.rbox(.1, .86, .1, .02, X.STEEL), x, .43, z)); g.add(at(X.rbox(.22, .04, .22, .015, DK), x, .02, z)); }
    for (const z of [-.4, .4]) g.add(at(X.rbox(L - .4, .06, .05, .015, X.STEEL), 0, .3, z)); for (let k = 0; k < 9; k++) g.add(at(box(.06, .012, .8, '#f2c12e'), -L / 2 + .2 + k * (L - .4) / 8, 1.053, 0));
    g.add(at(X.rbox(.22, 2.9, .22, .05, OR), 0, 1.45, -.85)); g.add(at(X.rbox(.3, .2, 1.25, .05, OR), 0, 2.8, -.3)); g.add(at(X.rbox(.56, .3, .56, .06, DK), 0, 2.56, 0));
    const lamp = at(ball(.1, '#7dffb0', {emissive: '#3dff8a', emissiveIntensity: 3}), 0, 2.38, 0); g.add(lamp);
    const beam = new T3.Mesh(new T3.ConeGeometry(.42, 1.3, 16, 1, true), new T3.MeshBasicMaterial({color: new T3.Color('#7dffb0'), transparent: true, opacity: .22, side: T3.DoubleSide, depthWrite: false})); g.add(at(beam, 0, 1.72, 0));
    g.add(at(label(it.text || '', 2.6, .54, '#fff', '#14182b'), 0, 3.4, -.3)); g.add(at(X.rbox(2.8, .7, .1, .03, X.PM('#14182b', {roughness: .3})), 0, 3.4, -.37)); g.add(at(X.rbox(.1, .4, .1, .02, X.STEEL), 0, 3.0, -.37));
    const arms = [-1.1, 1.1].map(x => { const a = new T3.Group(), el = new T3.Group(); g.add(at(X.rbox(.36, 1, .36, .05, DK), x, .5, -.78));
      a.add(at(X.cyl(.2, .24, .24, DK, 24), 0, .12, 0)); a.add(at(X.cyl(.075, .085, 1.1, OR, 16), 0, .75, 0)); a.add(at(X.ball(.13, DK), 0, 1.3, 0)); el.position.y = 1.3; a.add(el);
      el.add(at(X.cyl(.06, .07, .8, OR, 16), 0, -.4, 0)); el.add(at(X.rbox(.26, .12, .26, .04, DK), 0, -.84, 0)); for (const sd of [-1, 1]) el.add(at(X.rbox(.04, .14, .1, .012, X.STEEL), sd * .08, -.95, 0));
      const sp = ball(.08, '#fff3b0', {emissive: '#ffd24a', emissiveIntensity: 5}); sp.position.y = -1.04; el.add(sp); at(a, x, 1, -.78); g.add(a); return {a, el, sp, x}; });
    const items = Array.from({length: N}, () => { const m = productMesh(it.product || 'box', col, ''); m.scale.setScalar(Math.min(.8, ((L - .9) / N - .08) / new T3.Box3().setFromObject(m).getSize(new T3.Vector3()).x)); g.add(m); return m; });      // (as big as leaves a gap between two on the belt)
    return {g, tick: t => { items.forEach((m, k) => { const u = (t * .2 + k / N) % 1, x = -L / 2 + .45 + u * (L - .9); m.position.set(x, 1.05, 0); m.userData.late.forEach(q => { q.visible = x > 0; }); });   // (its last parts go on under the scanner)
      arms.forEach(({a, el, sp, x}, i) => { const near = Math.min(...items.map(m => Math.abs(m.position.x - x))), dn = cl(1 - near / .4); el.rotation.x = -(1.3 - .5 * dn); a.rotation.y = .1 * Math.sin(t * 2 + i); sp.visible = dn > .6 && Math.sin(t * 40 + i) > -.2; });
      lamp.material.emissiveIntensity = 2 + 2 * Math.sin(t * 6); }}; },
  product(it) { const kind = it.product || 'box', g = productMesh(kind, brand(it.brand), it.text), w = new T3.Group(); g.scale.setScalar(2); g.position.y = .18; w.add(g);      // the product itself, big, standing on a lit turntable that turns it (2026-11-26: it used to float over a small disc)
    w.add(MOD.turntable(BIG(kind) ? 2.3 : 1.25, brand(it.brand)));
    const glow = new T3.PointLight('#fff1cf', .9, 6); glow.position.set(0, 1.6, 2.2); w.add(glow);
    return {g: w, tick: t => { g.rotation.y = .5 * Math.sin(t * .9); }}; },
  store(it) { const col = brand(it.brand), g = new T3.Group(), X = MOD, WH = X.PM('#fbfaf6', {roughness: .5});      // a shop front (2026-11-26: a plastered wall on a step, a striped awning with a scalloped edge, a framed window, a door with a glass pane)
    g.add(at(X.rbox(3.8, 3, 1.6, .04, X.PM('#f3e6cd', {roughness: .85, envMapIntensity: .15})), 0, 1.5, 0)); g.add(at(X.rbox(4, .22, 1.8, .06, X.PM(S.shade(col, -.2), {roughness: .5})), 0, 3.1, 0)); g.add(at(X.rbox(4.1, .12, 2.5, .04, X.PM('#b9b3a7', {roughness: .8})), 0, .0, .3));
    const awn = canvasTex(512, 64, (x, w, h) => { for (let k = 0; k < 8; k++) { x.fillStyle = k % 2 ? '#fff' : col; x.fillRect(k * 64, 0, 64, h); } });
    const a = new T3.Mesh(new T3.BoxGeometry(3.9, .08, 1), [M('#ddd'), M('#ddd'), new T3.MeshStandardMaterial({map: awn}), M('#ddd'), M('#ddd'), M('#ddd')]); a.rotation.x = .4; a.castShadow = true; g.add(at(a, 0, 2.5, 1.2));
    for (let k = 0; k < 8; k++) { const sc = new T3.Mesh(new T3.CylinderGeometry(.244, .244, .03, 20, 1, false, -Math.PI / 2, Math.PI), X.PM(k % 2 ? '#ffffff' : col, {roughness: .8, side: T3.DoubleSide})); sc.rotation.x = Math.PI / 2; sc.castShadow = true; g.add(at(sc, -1.706 + k * .4875, 2.3, 1.66)); }
    g.add(at(label(it.text || 'STORE', 3, .6, '#fff', '#14182b'), 0, 3.52, .5)); g.add(at(X.rbox(3.2, .7, .1, .03, X.PM('#14182b', {roughness: .3})), 0, 3.52, .44));
    g.add(at(X.rbox(2.44, 1.89, .06, .02, WH), -.6, 1.3, .775)); g.add(at(X.rbox(2.3, 1.75, .05, .01, X.PM('#c4e6fa', {roughness: .06, metalness: .3, envMapIntensity: 1.2, emissive: '#bfe3ff', emissiveIntensity: .15})), -.6, 1.3, .8));
    for (let r = 0; r < 2; r++) { g.add(at(X.rbox(2.2, .06, .34, .015, X.PM('#8a6a48', {roughness: .6})), -.6, .55 + r * .8, .9)); for (let k = 0; k < 3; k++) { const m = productMesh(it.product || 'box', col, ''); m.scale.setScalar(BIG(it.product) ? .33 : .5); g.add(at(m, -1.3 + k * .7, .58 + r * .8, .9)); } }
    g.add(at(X.rbox(.97, 2.05, .06, .02, WH), 1.3, 1.03, .79)); g.add(at(X.rbox(.85, 1.95, .06, .02, X.PM('#7a4a2a', {roughness: .4, envMapIntensity: .5})), 1.3, .98, .81)); g.add(at(X.rbox(.55, .8, .066, .01, X.GLASS), 1.3, 1.38, .812)); g.add(at(X.rbox(.03, .3, .04, .012, X.CHROME), 1, 1, .86));
    const sign = it.sign ? at(label(it.sign, 1.9, .52, '#fff', '#e8394a'), -.6, 1.92, 1.74) : null; if (sign) { g.add(sign); for (const x of [-1.4, .2]) g.add(at(box(.03, .3, .03, '#555'), x, 2.2, 1.72)); }   // (a banner hung from the awning)
    return {g}; },
  monitor(it) { const g = new T3.Group(), X = MOD, BG = X.PM('#e4dfd0', {roughness: .6, envMapIntensity: .3}), BG2 = X.PM('#cdc7b6', {roughness: .6, envMapIntensity: .3});      // an old desktop computer: a rounded case, a recessed screen, a keyboard with keys
    g.add(at(X.rbox(1.6, 1.25, 1.1, .09, BG), 0, 1.15, 0)); g.add(at(X.rbox(1.42, 1.07, .06, .03, BG2, .1), 0, 1.18, .535)); g.add(at(X.rbox(.5, .3, .5, .06, BG2), 0, .42, 0)); g.add(at(X.rbox(1.8, .14, .78, .04, BG), 0, .07, .3));
    g.add(at(X.keyboard(1.6, .5, '#d9d4c5', '#f3f0e7'), 0, .142, .36)); g.add(at(X.ball(.02, X.PM('#35ff7a', {emissive: '#35ff7a', emissiveIntensity: 2})), .62, .62, .556)); for (let k = 0; k < 5; k++) g.add(at(X.box(.5, .012, .03, X.DARK), -.3, 1.776, -.3 + k * .09));
    g.add(at(screen(1.3, .95, 256, (x, w, h, t) => { x.fillStyle = '#0f2a1a'; x.fillRect(0, 0, w, h); const old = S.ctx(x); let left = t * 22;
      (it.lines || ['C:\\>_']).slice(0, 3).forEach((l, i) => { const s = String(l).slice(0, Math.max(0, Math.floor(left))); left -= String(l).length; S.txt(s, 18, 50 + i * 70, 44, '#57f28a', w - 30, 600, 'left'); }); S.ctx(old); }, it), 0, 1.18, .57)); return {g, lift: .5}; },
  phone(it) { const g = new T3.Group(), p = new T3.Group(); p.add(at(MOD.phoneShell(1.14, 2.2, .14, 1.02, 2.04), 0, 1.1, 0)); p.add(at(screen(1.02, 2.04, 640, (x, w, h, t) => drawK('phone', it, t, x, w, h, '#1b1d24'), it), 0, 1.1, .075)); p.scale.setScalar(1.3); g.add(p);
    return {g, lift: .3, tick: t => { p.rotation.y = .22 * Math.sin(t * .9); }}; },
  cart(it) { const g = new T3.Group(), col = brand(it.brand), N = 4, items = [];      // a shopping bag in the brand's colour, the products dropping into it (sales, shoppers, orders)
    const W = 1.9, Hb = 2.1, D = 1.05, body = MOD.rbox(W, Hb, D, .03, MOD.PM(col, {roughness: .75, envMapIntensity: .25})); g.add(at(body, 0, Hb / 2, 0));
    g.add(at(MOD.rbox(W + .04, .16, D + .04, .03, MOD.PM(S.shade(col, -.18), {roughness: .75, envMapIntensity: .25})), 0, Hb - .08, 0));
    for (const z of [D / 2 + .01, -D / 2 - .01]) { const h = new T3.Mesh(new T3.TorusGeometry(.42, .05, 8, 24, Math.PI), M('#f4efe6')); h.position.set(0, Hb, z); g.add(h); }
    const nm = label(String(it.brand || 'SHOP'), 1.5, .5, '#fff', S.shade(col, -.25)); nm.position.set(0, Hb * .52, D / 2 + .012); g.add(nm);
    for (let k = 0; k < N; k++) { const m = productMesh(it.product || 'box', S.shade(col, .35), ''); m.scale.setScalar(.36); m.userData.rest = new T3.Vector3(-.55 + (k % 2) * 1.1 + (k > 1 ? .3 : 0), Hb - .05 + (k > 1 ? .12 : 0), (k % 2 ? .12 : -.12)); m.visible = false; g.add(m); items.push(m); }
    return {g, tick: lt => items.forEach((m, k) => { const u = cl((lt - .3 - k * .38) / .35), r = m.userData.rest; m.visible = u > 0; m.position.set(r.x, r.y + (window.__measuring ? 0 : 1.6) * (1 - u) * (1 - u), r.z); m.rotation.y = .4 * k + (1 - u) * 1.2; })}; },
  chart(it) { const g = new T3.Group(); g.add(at(MOD.rbox(4.2, 3.7, .18, .05, MOD.PM('#232a4d', {roughness: .25, envMapIntensity: .8}), .12), 0, 2.55, 0));      // (2026-11-24: squarer, so the hook's chart fills a tall frame) for (const x of [-1.6, 1.6]) g.add(at(box(.14, .8, .14, '#3a4370'), x, .4, 0)); g.add(at(box(4, .1, .7, '#3a4370'), 0, .05, 0));
    g.add(at(screen(4.04, 3.5, 720, (x, w, h, t) => drawK('chart', it, t, x, w, h, '#141830'), it), 0, 2.55, .1)); return {g}; },
  bars(it) { const B = (it.bars || []).slice(0, 3), mx = Math.max(1e-9, ...B.map(b => +b.value || 0)), g = new T3.Group(), cols = ['#2f7cf6', '#9b59d0', '#22b573'], bs = [], HT = 2.6;
    g.add(at(MOD.rbox(B.length * 1.5 + .3, .12, 1.2, .03, MOD.PM('#20243a', {roughness: .3})), 0, .06, 0));
    B.forEach((b, i) => { const x = (i - (B.length - 1) / 2) * 1.5, col = (R.brands || []).some(q => q.name.toLowerCase() === String(b.label).toLowerCase()) ? brand(b.label) : cols[i], h = HT * (+b.value || 0) / mx;
      const m = MOD.rbox(1, 1, 1, .05, MOD.PM(col, {roughness: .3, envMapIntensity: .8})); g.add(m); const top = b.text ? label(b.text, 1.3, .4, '#fff', '#14182b') : null; if (top) g.add(top); g.add(at(label(b.label, 1.3, .36), x, .32, .62)); bs.push([m, h, x, top]); });
    return {g, tick: t => bs.forEach(([m, h, x, l]) => { const hh = Math.max(.02, h * S.ease(t / 1.2)); m.scale.y = hh; m.position.set(x, .55 + hh / 2, 0); if (l) l.position.set(x, .55 + hh + .3, .1); })}; },
  calendar(it) { const g = new T3.Group(), p = grp(at(MOD.rbox(1.5, 1.62, .12, .03, MOD.WHITE), 0, .81, 0), at(screen(1.44, 1.56, 320, (x, w, h) => drawK('calendar', it, 0, x, w, h, '#fff'), it), 0, .81, .065)); g.add(p);
    for (let k = 0; k < 6; k++) { const r = new T3.Mesh(new T3.TorusGeometry(.075, .014, 8, 16), MOD.CHROME); r.rotation.y = Math.PI / 2; p.add(at(r, -.55 + k * .22, 1.62, 0)); }      // (the rings its pages hang on)
    return {g, lift: .45, tick: t => { p.rotation.z = .05 * Math.sin(t * 1.5); p.rotation.y = .15 * Math.sin(t * .8); }}; },
  money(it) { const g = MOD.cash();      // (a case of banded notes; it was a green ball with a $ on it)
    const coins = []; if (it.rain) for (let k = 0; k < 9; k++) { const c = MOD.coin(.13); g.add(c); coins.push(c); }
    if (it.text) g.add(at(label(it.text, 1.2, .36, '#15162b', '#ffc83d'), 0, 1.78, -.5));
    return {g, tick: t => coins.forEach((c, k) => { const u = (t * .6 + k / 9) % 1; c.position.set(-.8 + hsh(k) * 1.6, 1.7 - u * 1.3, .55 + hsh(k + 3) * .3); c.rotation.set(t * 4 + k, k, t * 3); })}; },
  podium(it) { const g = new T3.Group(), P = [];
    for (const [n, x, h, col, who] of [['2', -1.3, .8, '#c9cfdc', it.second], ['1', 0, 1.2, '#ffc83d', it.first], ['3', 1.3, .55, '#c98d4e', it.third]]) {
      g.add(at(MOD.rbox(1.25, h, 1, .04, MOD.PM(col, {metalness: .7, roughness: .3, envMapIntensity: 1})), x, h / 2, 0)); g.add(at(label(n, .5, .5, '#15162b', col), x, h * .5, .51));
      if (who && R.cast[who]) { const c = R.cast[who], p = actor(c.look, c.color, seedOf(who), n === '1' ? 'cheer' : 'sad'); p.root.position.set(x, h, 0); g.add(p.root); P.push(p); } }
    return {g, tick: t => P.forEach(p => poseToon(p, t))}; },
  news(it) { const g = new T3.Group(); g.add(at(MOD.tv(3, 1.95, 1.025), 0, 2, 0));
    g.add(at(screen(2.8, 1.75, 448, (x, w, h, t) => { x.fillStyle = '#16204a'; x.fillRect(0, 0, w, h); x.fillStyle = '#e8394a'; x.fillRect(0, 0, w, h * .22); const old = S.ctx(x);
      S.txt(Math.sin(t * 6) > -.6 ? 'BREAKING' : '', w / 2, h * .11 + 2, h * .15, '#fff'); (it.lines || []).slice(0, 3).forEach((l, i) => S.txt(String(l).toUpperCase(), w / 2, h * (.38 + i * .2), h * .15, '#fff', w * .9)); S.ctx(old); }, it), 0, 2, .076)); return {g}; },
  doc(it) { const g = new T3.Group(), p = grp(      // (a paper on a clipboard)
      at(box(1.3, 1.62, .03, '#fdfaf2'), 0, 0, 0), at(screen(1.26, 1.55, 400, (x, w, h) => drawK('doc', it, 0, x, w, h, '#fdfaf2'), it), 0, 0, .02),
      at(MOD.rbox(1.46, 1.84, .04, .018, MOD.PM('#8a5a33', {roughness: .55}), .05), 0, -.03, -.036), at(MOD.rbox(.5, .16, .05, .022, MOD.CHROME), 0, .83, .03), at(MOD.rbox(.22, .1, .07, .03, MOD.CHROME), 0, .9, .03)); p.position.y = .81; g.add(p);
    return {g, lift: .45, tick: t => { p.rotation.set(.06 * Math.sin(t), .28 * Math.sin(t * .8), .05); }}; },
  arrow(it) { const up = it.dir !== 'down', col = up ? '#2bd47d' : '#e8394a', sh = new T3.Shape();
    sh.moveTo(0, 1.3); sh.lineTo(.8, .4); sh.lineTo(.32, .4); sh.lineTo(.32, -1); sh.lineTo(-.32, -1); sh.lineTo(-.32, .4); sh.lineTo(-.8, .4); sh.closePath();
    const m = MOD.ext(sh, .34, MOD.PM(col, {emissive: col, emissiveIntensity: .22, roughness: .22, envMapIntensity: .9}), .05); const a = grp(m); if (!up) a.rotation.z = Math.PI;
    const g = grp(at(a, 0, up ? 1 : 1.3, 0)); if (it.text) g.add(at(label(it.text, 1.6, .5, '#fff', '#14182b'), 0, 2.72, 0));
    return {g, lift: .3, tick: t => { a.rotation.y = .45 * Math.sin(t * 1.4); a.position.y = (up ? 1 : 1.3) + (up ? 1 : -1) * .04 * (1 - Math.cos(t * 3)); }}; },
  trophy(it) { const g = MOD.trophy();
    const conf = []; for (let k = 0; k < 16; k++) { const c = new T3.Mesh(new T3.PlaneGeometry(.09, .15), new T3.MeshBasicMaterial({color: ['#e8394a', '#2f7cf6', '#ffc83d', '#2bd47d'][k % 4], side: T3.DoubleSide})); g.add(c); conf.push(c); }
    return {g, lift: .3, tick: t => conf.forEach((c, k) => { const u = (t * .5 + k / 16) % 1; c.position.set(-.8 + hsh(k) * 1.6, 1.95 - u * 1.9, -.2 + hsh(k + 1) * .5); c.rotation.set(t * 5 + k, t * 3, k); })}; },
  bulb(it) { const made = MOD.bulb(), g = made.g, b = made.glass;
    for (let k = 0; k < 8; k++) { const r = box(.05, .22, .05, '#ffe46b', {emissive: '#ffcc33', emissiveIntensity: 1.5}); r.position.set(Math.cos(k * .785) * .7, 1.06 + Math.sin(k * .785) * .7, 0); r.rotation.z = k * .785 - Math.PI / 2; if (k !== 6) g.add(r); }
    const l = new T3.PointLight('#ffd27a', 1.2, 5); l.position.set(0, 1, 1); g.add(l); if (it.text) g.add(at(label(it.text, 1.5, .4, '#15162b', '#ffc83d'), 0, -.05, 0));
    return {g, lift: .5, tick: t => { b.material.emissiveIntensity = 1 + .5 * Math.sin(t * 5); }}; },
  rocket(it) { const g = new T3.Group(), made = MOD.rocket(), r = made.r, fl = made.flame; g.add(r);
    return {g, lift: .2, tick: t => { r.position.y = 1.05 + Math.min(.5, t * .16) + .03 * Math.sin(t * 9); fl.scale.y = .8 + .3 * Math.sin(t * 30); r.rotation.y = t * .5; }}; },
  boxes(it) { const g = new T3.Group(); for (const [x, y, z, ry] of [[-.58, 0, 0, .1], [.58, 0, 0, -.12], [0, .8, 0, .06]]) { const b = productMesh('box', '#c98d4e', it.text || ''); g.add(at(b, x, y, z, ry)); } return {g}; },
  action(it) { const sport = it.sport || 'surf', g = new T3.Group(), X = MOD, p = actor('casual', it.color || '#e8394a', 5, 'surf'), cam1 = productMesh('camera', '#3a3d45', ''); cam1.scale.setScalar(.26);
    p.head.add(at(cam1, 0, .32, .02)); const body = grp(p.root), rider = grp(body), RED = X.PM('#e8394a', {roughness: .25, envMapIntensity: .9}); body.rotation.y = -.5; let y0 = 0;    // the camera rides on their head; they stand side-on
    if (sport === 'surf') { const w = new T3.Mesh(new T3.SphereGeometry(1.7, 40, 20, 0, Math.PI * 2, 0, Math.PI / 2), X.PM('#1f8fd8', {roughness: .12, metalness: .2, envMapIntensity: 1.1})); w.scale.set(.8, .42, .7); w.castShadow = true; g.add(at(w, 0, 0, -.15));
      for (let k = 0; k < 7; k++) g.add(at(X.ball(.18 + hsh(k) * .1, X.WHITE), -1.08 + k * .36, .5 - Math.abs(k - 3) * .1, -.95)); y0 = .72;
      const bs = new T3.Shape(); bs.moveTo(-1.1, 0); bs.quadraticCurveTo(-1.1, .25, -.6, .26); bs.lineTo(.5, .24); bs.quadraticCurveTo(1.15, .14, 1.22, 0); bs.quadraticCurveTo(1.15, -.14, .5, -.24); bs.lineTo(-.6, -.26); bs.quadraticCurveTo(-1.1, -.25, -1.1, 0);      // a surfboard: a pointed nose, a round tail, a stripe
      const board = X.ext(bs, .08, X.PM('#ffc83d', {roughness: .2, envMapIntensity: .9}), .03); board.rotation.x = -Math.PI / 2; rider.add(at(board, 0, -.05, 0)); rider.add(at(X.box(2, .012, .07, RED), .02, -.004, 0)); }
    else if (sport === 'ski') { g.add(at(X.ball(1, X.PM('#f6faff', {roughness: .6, envMapIntensity: .5}), 1.8, .3, 1.1), 0, .04, 0)); y0 = .36;
      for (const z of [-.16, .16]) { rider.add(at(X.rbox(1.9, .035, .12, .014, RED), 0, -.02, z)); const tip = X.rbox(.24, .035, .12, .014, RED); tip.rotation.z = .5; rider.add(at(tip, 1.04, .035, z)); } }
    else { y0 = .52; const tb = (a, b, r = .028, m = RED) => g.add(X.tube(a[0], a[1], 0, b[0], b[1], 0, r, m)), A = [-.72, .48], B = [-.12, .42], St = [-.3, .98], H = [.42, .95], H2 = [.5, .78], F = [.72, .48];      // a bicycle: spoked wheels, a frame of tubes, a saddle, bars, a crank
      for (const x of [-.72, .72]) { const wl = grp(new T3.Mesh(new T3.TorusGeometry(.42, .045, 10, 40), X.RUBBER), new T3.Mesh(new T3.TorusGeometry(.375, .014, 8, 40), X.STEEL), X.cyl(.04, .04, .1, X.STEEL, 12, 'z')); for (let k = 0; k < 12; k++) wl.add(X.tube(0, 0, 0, Math.cos(k * Math.PI / 6) * .37, Math.sin(k * Math.PI / 6) * .37, 0, .004, X.STEEL)); wl.children.forEach(m => { m.castShadow = true; }); g.add(at(wl, x, .48, 0)); }
      tb(A, B); tb(B, St); tb(A, St, .018); tb(St, H); tb(B, H2, .032); tb(H, H2, .034); tb(H2, F, .022); tb(St, [-.33, 1.1], .02, X.STEEL); tb(H, [.44, 1.08], .02, X.STEEL);
      g.add(at(X.rbox(.3, .05, .13, .02, X.DARK), -.35, 1.12, 0)); g.add(X.tube(.44, 1.08, -.26, .44, 1.08, .26, .018, X.DARK)); g.add(at(X.cyl(.1, .1, .012, X.STEEL, 24, 'z'), -.12, .42, .05)); g.add(X.tube(-.12, .42, .06, -.02, .26, .06, .014, X.DARK)); g.add(at(X.rbox(.12, .025, .08, .01, X.DARK), -.02, .26, .1)); }
    rider.position.y = y0; g.add(rider);
    return {g, tick: t => { poseToon(p, t); rider.rotation.z = .09 * Math.sin(t * 2.2); rider.position.y = y0 + .03 * Math.sin(t * 3); }}; },
  question(it) { const g = new T3.Group(), b = MOD.qmark('#ffc83d'); g.add(b); return {g, lift: .4, tick: t => { b.rotation.y = .6 * Math.sin(t); }}; },      // (a question mark you could pick up; it was a grey cube with a ? on it)
  badge(it) { const col = brand(it.brand || it.text), g = new T3.Group(), b = grp(at(MOD.rbox(1.9, 1.9, .34, .08, MOD.PM(S.shade(col, -.25), {roughness: .3, envMapIntensity: .8}), .34), 0, 0, 0), at(label(it.text || '', 1.66, 1.66, '#fff', col), 0, 0, .18)); b.position.y = .95; g.add(b);
    return {g, lift: .45, tick: t => { b.rotation.y = .35 * Math.sin(t * 1.2); }}; },
  gavel(it) { const made = MOD.gavel(), g = made.g, h = made.hammer;
    h.position.set(.35, .2, 0); g.userData.proxy = [-.95, 0, -.5, 1.7, 1.75, .5]; return {g, lift: .4, tick: t => { h.rotation.z = .6 - Math.max(0, Math.sin(t * 4)) * .6; }}; },
};
const FLAT = new Set(['title']);      // (2026-11-24: the hook's claim is on screen from the first second, readable on mute; still only the first two shots carry one)
const FLAT_OFF = new Set([]);      // (the third model reel puts no words on the picture: a script's titles, counters and stamps are not drawn)

// ---------------------------------------------------------------- the sets: a place at real scale, built around its stage (x 0, z 0), GAP wide
function sky(cols) { return canvasTex(8, 512, (x, w, h) => { x.fillStyle = cols[0]; x.fillRect(0, 0, w, h); const g = x.createLinearGradient(0, h * .5, 0, h * .84); cols.forEach((c, i) => g.addColorStop(i / (cols.length - 1), c)); x.fillStyle = g; x.fillRect(0, h * .5, w, h * .5); }); }   // (the camera sees the band just above the horizon)
function disc(r, col, k = 1.6) { return new T3.Mesh(new T3.CircleGeometry(r, 32), new T3.MeshBasicMaterial({color: new T3.Color(col).multiplyScalar(k), fog: false})); }
// (the sky and the ground reach 8 m past the set on each side, so a camera that starts a shot wide and off to one side never sees their edge; neighbours sit at slightly different depths so the two never fight)
function backdrop(g, cols) { const m = new T3.Mesh(new T3.PlaneGeometry(GAP + 16, 80), new T3.MeshBasicMaterial({map: sky(cols), fog: false})); m.position.set(0, 26, -40 - (g.userData.k % 2) * .6); g.add(m); }
function floorTex(kind, a, b) { const t = canvasTex(256, 256, (x, w, h) => { x.fillStyle = a; x.fillRect(0, 0, w, h); x.fillStyle = b;
    if (kind === 'checker') { x.fillRect(0, 0, 128, 128); x.fillRect(128, 128, 128, 128); }
    else if (kind === 'planks') for (let k = 0; k < 4; k++) { x.fillRect(0, k * 64, w, 4); x.fillRect((k * 97) % 256, k * 64, 4, 64); }
    else if (kind === 'tiles') { x.fillRect(0, 0, w, 5); x.fillRect(0, 0, 5, h); }
    else for (let k = 0; k < 70; k++) x.fillRect(hsh(k) * 250, hsh(k + 77) * 250, 6, 6); });          // speckle: grass, sand, asphalt
  t.wrapS = t.wrapT = T3.RepeatWrapping; return t; }
function ground(g, tex, tile = 2, o = {}) { tex.repeat.set((GAP + 16) / tile, 80 / tile); const m = new T3.Mesh(new T3.PlaneGeometry(GAP + 16, 80), new T3.MeshStandardMaterial(Object.assign({map: tex, roughness: .9}, o))); m.rotation.x = -Math.PI / 2; m.position.set(0, -(g.userData.k % 2) * .004, -18); m.receiveShadow = true; g.add(m); }
function wall(g, col, z = -4, h = 12) { const m = box(GAP, h, .4, col, {flatShading: false}); at(m, 0, h / 2, z); g.add(m); return m; }
function pane(w, h, col, k = 1.4) { return new T3.Mesh(new T3.PlaneGeometry(w, h), glowM(col, k)); }
function windows(g, z, y, w, h, n = 3, step = 4.4, col = '#a9dcff') { for (let k = -n; k <= n; k++) { const x = k * step; g.add(at(box(w + .24, h + .24, .1, '#ffffff'), x, y, z + .2)); g.add(at(pane(w, h, col), x, y, z + .27)); g.add(at(box(.08, h, .06, '#fff'), x, y, z + .29)); g.add(at(box(w, .08, .06, '#fff'), x, y, z + .29)); } }
function city(g, night, z0 = -11) { const cols = night ? ['#241c4a', '#2d2259', '#1c1740', '#33285f'] : ['#f09a7c', '#7fbfe8', '#f5d37a', '#b79ae8', '#7fd3a8'];
  const texs = cols.map((col, i) => canvasTex(128, 256, (x, w, h) => { x.fillStyle = col; x.fillRect(0, 0, w, h); for (let r = 0; r < 9; r++) for (let k = 0; k < 4; k++) { const on = hsh(i * 31 + r * 7 + k) > (night ? .45 : .25);
    x.fillStyle = night ? (on ? '#ffd27a' : '#15112c') : (on ? '#e3f3ff' : S.shade(col, -.3)); x.fillRect(12 + k * 29, 12 + r * 27, 18, 17); } }));
  for (let k = 0; k < 17; k++) { const w = 2.8 + hsh(k) * 2, h = 7 + hsh(k + 3) * 12, x = -15 + k * 1.9 + hsh(k + 5), z = z0 - (k % 3) * 4, i = k % cols.length, side = M(S.shade(cols[i], -.12));
    const m = new T3.Mesh(new T3.BoxGeometry(w, h, 3), [side, side, side, side, night ? lit(texs[i], 1.3) : new T3.MeshStandardMaterial({map: texs[i], roughness: .8}), side]); m.position.set(x, h / 2, z); m.castShadow = !night; g.add(m); } }
const LIVE = [];      // what moves in a set by itself: [shot, t => {}]
function rug(g, w, d, col, edge = '#ffc83d', round = false) {      // a patterned carpet under the stage (the second model's floors are never bare)
  const t = canvasTex(256, 256, (x, cw, ch) => { x.fillStyle = edge; x.fillRect(0, 0, cw, ch); x.fillStyle = col; x.fillRect(14, 14, cw - 28, ch - 28); x.strokeStyle = S.shade(col, .25); x.lineWidth = 5; x.strokeRect(30, 30, cw - 60, ch - 60);
    x.fillStyle = S.shade(col, -.22); for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { x.save(); x.translate(64 + i * 43, 64 + j * 43); x.rotate(Math.PI / 4); x.fillRect(-11, -11, 22, 22); x.restore(); } });
  const m = new T3.Mesh(round ? new T3.CircleGeometry(w / 2, 40) : new T3.PlaneGeometry(w, d), new T3.MeshStandardMaterial({map: t, roughness: .95})); m.rotation.x = -Math.PI / 2; m.position.set(0, .012, -.3); m.receiveShadow = true; g.add(m); }
function clouds(g, z = -30) { for (let k = 0; k < 7; k++) { const s = 1.6 + hsh(k) * 1.4, c = grp(ball(.8, '#ffffff', {flatShading: false, emissive: '#ffffff', emissiveIntensity: .3}), at(ball(.6, '#ffffff', {flatShading: false, emissive: '#ffffff', emissiveIntensity: .3}), .75, -.1, 0), at(ball(.55, '#ffffff', {flatShading: false, emissive: '#ffffff', emissiveIntensity: .3}), -.75, -.15, 0)); c.scale.setScalar(s); at(c, -13 + k * 4.3, 6.5 + hsh(k + 9) * 5, z); g.add(c); const x0 = c.position.x; LIVE.push([g.userData.k, t => { c.position.x = ((x0 + 17 + t * .22) % 34) - 17; }]); } }      // (they drift)
function lamps(g, z, y, n = 3, step = 4) { for (let k = -n; k <= n; k++) { g.add(at(cyl(.02, .02, 12 - y, '#333', 5), k * step, y + (12 - y) / 2, z)); g.add(at(cone(.45, .4, '#2c3340', 10), k * step, y, z)); g.add(at(ball(.14, '#fff3c4', {emissive: '#ffe9a8', emissiveIntensity: 3}), k * step, y - .2, z)); } }
function tickerTex(seed) { return canvasTex(256, 160, (x, w, h) => { x.fillStyle = '#0b1026'; x.fillRect(0, 0, w, h); const up = hsh(seed) > .45, col = up ? '#2bd47d' : '#e8394a'; x.strokeStyle = col; x.lineWidth = 6; x.lineJoin = 'round'; x.beginPath(); let y = h * .6;
  for (let i = 0; i <= 12; i++) { y += (hsh(seed * 13 + i) - (up ? .6 : .4)) * 28; y = Math.max(44, Math.min(h - 14, y)); i ? x.lineTo(10 + i * 19.5, y) : x.moveTo(10, y); } x.stroke(); x.fillStyle = col; x.fillRect(10, 10, 76, 18); x.fillStyle = '#dfe6ff'; x.fillRect(96, 10, 44, 18); }); }
// each returns its light: {h: [sky, ground, strength], k: [key colour, strength], rim: colour, fog: colour}
const SETS = {
  async office(g) { backdrop(g, ['#7fc4f5', '#dff1ff']); ground(g, floorTex('planks', '#c59868', '#a97a4c'), 3); wall(g, '#e9eef6'); windows(g, -4, 2.9, 2.4, 2.6); g.add(at(box(GAP, .5, .5, '#c9d2e0'), 0, .25, -3.7)); g.add(at(box(GAP + 16, 1.1, .1, S.shade(brand(), -.1), {flatShading: false}), 0, .55, -3.76)); rug(g, 7.5, 4, '#2f5fb8');
    for (const [n, x, z, h, ry] of [['houseplant', -2.2, -3.2, 1.5, 0], ['houseplant_2', 2.2, -3.2, 1.3, 0], ['bookshelf', 6.6, -3.3, 2.4, 0], ['bookshelf', -6.6, -3.3, 2.4, 0], ['potted_plant', 10.4, -3.2, 1.4, 0], ['potted_plant_2', -10.4, -3.2, 1.4, 0]]) g.add(at(await glb(n, h), x, 0, z, ry));
    return {h: ['#ffffff', '#c9b9a5', .8], k: ['#fff3e0', 1.15], rim: '#bfe3ff', fog: '#dff1ff'}; },
  async home(g) { backdrop(g, ['#ffb27a', '#ffe2c2']); ground(g, floorTex('planks', '#b98558', '#9c6c42'), 3); wall(g, '#f6d9c4'); windows(g, -4, 3, 2, 2.4, 1, 8.8, '#ffe0b0'); g.add(at(box(6, .03, 3.2, '#d9534f', {flatShading: false}), 0, .015, -.9));
    g.add(at(box(GAP, .3, .3, '#fff5ea'), 0, .15, -3.75));
    for (const [n, x, z, h, ry] of [['couch_large', 0, -2.9, 1.15, 0], ['houseplant_3', -3.2, -3.1, 1.7, 0], ['shelf_tall', 4.6, -3.4, 2.2, 0], ['houseplant', -12, -3.2, 1.5, 0], ['bookshelf', 12.6, -3.3, 2.4, 0]]) g.add(at(await glb(n, h), x, 0, z, ry));
    for (const [x, c] of [[-1.3, '#2f7cf6'], [0, '#ffc83d'], [1.3, '#22b573']]) { g.add(at(box(1, 1.3, .06, '#fff'), x, 3.2, -3.76)); g.add(at(box(.84, 1.14, .08, c), x, 3.2, -3.75)); }
    g.add(at(cyl(.04, .04, 1.7, '#444', 6), 3.2, .85, -3)); g.add(at(cone(.42, .5, '#ffe9a8', 12, {emissive: '#ffd27a', emissiveIntensity: 1.2}), 3.2, 1.9, -3));
    return {h: ['#fff1e0', '#c9a58a', .8], k: ['#ffe2c0', 1.1], rim: '#ffb27a', fog: '#ffe2c2'}; },
  async store(g) { backdrop(g, ['#f4d9b0', '#faeed8']); ground(g, floorTex('checker', '#f2e6d0', '#e0c9a4'), 2.4); wall(g, '#f7e8cc'); const cols = ['#e8394a', '#2f7cf6', '#ffc83d', '#22b573', '#9b59d0', '#f28c28'];
    for (let r = 0; r < 4; r++) { g.add(at(box(GAP, .08, .5, '#a07850'), 0, 1.1 + r * 1.05, -3.6)); for (let k = 0; k < 44; k++) { const h = .5 + hsh(k * 7 + r) * .28; g.add(at(box(.44, h, .34, cols[(k * 5 + r * 2 + (k >> 2)) % 6]), -14.5 + k * .66, 1.14 + r * 1.05 + h / 2, -3.6)); } }
    g.add(at(box(GAP, 1, .6, '#c9a27a'), 0, .5, -3.6)); lamps(g, -1.5, 5.6, 3, 4.5);
    return {h: ['#fff6e6', '#d9c3a0', .85], k: ['#fff1dc', 1.1], rim: '#ffd9a0', fog: '#faeed8'}; },
  async factory(g) { backdrop(g, ['#1c3f4a', '#2f6675']); ground(g, floorTex('tiles', '#6a777d', '#56636a'), 2.5); wall(g, '#3f6470');
    for (let k = 0; k < 3; k++) { const p = cyl(.16, .16, GAP, ['#9aa9b1', '#e0b62e', '#9aa9b1'][k], 10); p.rotation.z = Math.PI / 2; g.add(at(p, 0, 4.4 + k * .7, -3.6)); }
    for (let k = -3; k <= 3; k++) { g.add(at(box(.5, 12, .5, '#2f4a55'), k * 4.6 + 2.3, 6, -3.7)); if (!k) continue; const m = box(1.6, 2.2, 1.2, ['#4d6f7c', '#5a7d54', '#7c6a4d'][(k + 3) % 3]); g.add(at(m, k * 4.6, 1.1, -3.1)); g.add(at(pane(.9, .5, ['#7dffb0', '#ffd24a', '#7fd0ff'][(k + 3) % 3], 1.6), k * 4.6, 1.6, -2.49)); g.add(at(cyl(.2, .2, 1.2, '#8892a6', 10), k * 4.6 + .4, 2.8, -3.1)); }
    for (let k = 0; k < 10; k++) g.add(at(box(.7, .7, .7, '#b08a4c'), -13 + k * 2.9 + hsh(k), .35, -2.2 - hsh(k + 4)));
    for (let k = 0; k < 30; k++) { const st = box(.5, .012, .22, k % 2 ? '#1c1c1c' : '#f2c12e', {flatShading: false}); g.add(at(st, -14.5 + k * 1, .006, -1.7)); } lamps(g, -1, 6, 3, 4.6);
    return {h: ['#d6f0ff', '#4a5a60', .7], k: ['#fff0d8', 1.2], rim: '#7fd0ff', fog: '#2f6675'}; },
  city(g) { backdrop(g, ['#3f9ae8', '#bfe6ff']); ground(g, floorTex('speckle', '#8c93a0', '#7d8491'), 3); city(g, false); clouds(g); g.add(at(box(GAP, .16, 3.4, '#c9ced8', {flatShading: false}), 0, .08, -5.4));
    for (const x of [-13.5, -9, -5.2, 5.2, 9, 13.5]) { g.add(at(cyl(.09, .11, 1.2, '#6b4a2e', 6), x, .6, -5.2)); g.add(at(ball(.85, '#4c9a52'), x, 1.8, -5.2)); }       // (none behind the stage: a tree there reads as part of the subject)
    return {h: ['#ffffff', '#9aa3b0', .85], k: ['#fff4e0', 1.25], rim: '#bfe6ff', fog: '#bfe6ff'}; },
  night(g) { backdrop(g, ['#1a1440', '#5a3572', '#e0805a']); ground(g, floorTex('speckle', '#2c2a4a', '#3a3760'), 3, {roughness: .45, metalness: .2}); city(g, true); g.add(at(disc(1.5, '#fff2c9'), 6, 15, -39));
    for (let k = 0; k < 50; k++) g.add(at(disc(.07, '#ffffff', 2), -15 + hsh(k) * 30, 8 + hsh(k + 5) * 20, -39.5));
    for (let k = -3; k <= 3; k++) { g.add(at(cyl(.06, .08, 3.4, '#22203a', 6), k * 4.5 + 2.2, 1.7, -5)); g.add(at(ball(.2, '#ffe9a8', {emissive: '#ffd27a', emissiveIntensity: 3}), k * 4.5 + 2.2, 3.5, -5)); }
    return {h: ['#8c8cff', '#3a2a55', .75], k: ['#ffd9b0', 1.0], rim: '#b08cff', fog: '#5a3572'}; },
  outdoors(g) { backdrop(g, ['#3f9ae8', '#d8f0ff']); ground(g, floorTex('speckle', '#79b860', '#6aa853'), 2.5); clouds(g);
    for (const [x, h, c, z] of [[-11, 13, '#7c95b8', -30], [-3, 18, '#93abcb', -34], [6, 15, '#7c95b8', -31], [13, 12, '#93abcb', -29], [1.5, 9, '#6d87ab', -24], [-7.5, 8, '#6d87ab', -23]]) { g.add(at(cone(h * .7, h, c, 6), x, h / 2, z)); g.add(at(cone(h * .22, h * .3, '#ffffff', 6), x, h * .86, z)); }
    for (let k = 0; k < 16; k++) { const s = 1 + hsh(k) * .8, tr = grp(at(cyl(.1, .14, .8, '#6b4a2e', 6), 0, .4, 0), at(cone(.8, 1.6, '#3f8a4a', 7), 0, 1.5, 0), at(cone(.6, 1.3, '#4c9a52', 7), 0, 2.4, 0)); tr.scale.setScalar(s); g.add(at(tr, -14.5 + k * 1.95 + hsh(k + 1), 0, -6 - hsh(k + 2) * 5)); }
    return {h: ['#ffffff', '#8fb878', .9], k: ['#fff4e0', 1.3], rim: '#d8f0ff', fog: '#d8f0ff'}; },
  sea(g) { backdrop(g, ['#2f8fe6', '#a8dcff']); ground(g, floorTex('speckle', '#1f9fe0', '#3fb4ee'), 2.5, {roughness: .3});      // open water: foam lines, an island, the sun
    for (let k = 0; k < 7; k++) for (let j = 0; j < 9; j++) { const f = box(1.4 + hsh(k * 9 + j) * 1.4, .04, .1, '#ffffff', {flatShading: false}); const x0 = -14 + j * 3.4 + hsh(k + j) * 1.6; g.add(at(f, x0, .03, -1.2 - k * 2.4 - hsh(k * 3 + j) * 1.2)); LIVE.push([g.userData.k, t => { f.position.x = x0 + .5 * Math.sin(t * .8 + k + j); }]); }      // (none in front of the stage: a foam line under the captions reads as a stray bar)
    g.add(at(disc(2.2, '#ffe680', 1.8), -5, 11, -39)); const isl = new T3.Mesh(new T3.SphereGeometry(7, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), M('#f0d9a0')); isl.scale.set(1.5, .16, .6); g.add(at(isl, 6, 0, -22));
    for (const [x, z] of [[3.5, -21.5], [7, -22.5], [9.5, -21.5]]) { const p = grp(at(cyl(.14, .2, 3.4, '#8a6a48', 7), 0, 1.7, 0)); for (let k = 0; k < 6; k++) { const l = box(1.7, .06, .45, '#3f9a52'); l.position.set(Math.cos(k * 1.05) * .8, 3.3, Math.sin(k * 1.05) * .8); l.rotation.y = -k * 1.05; l.rotation.z = -.35; p.add(l); } g.add(at(p, x, .9, z)); } clouds(g);
    return {h: ['#ffffff', '#3fb4ee', .95], k: ['#fff1d0', 1.3], rim: '#a8dcff', fog: '#a8dcff'}; },
  stage(g) { const col = brand(); backdrop(g, ['#1a1236', '#3a2866']); ground(g, floorTex('planks', '#6b4a3a', '#5a3c2e'), 3, {roughness: .4, metalness: .1});      // a keynote: red curtains, a lit screen (no words on it: the header's are in front)
    for (let k = -17; k <= 17; k++) g.add(at(box(.9, 12, .3, k % 2 ? '#8a1f3a' : '#a82a48', {flatShading: false}), k * .88, 6, -4.6 + (k % 2) * .14));
    g.add(at(box(9.4, 5, .2, '#11142a'), 0, 3.4, -4.1)); g.add(at(pane(9, 4.6, S.shade(col, -.2), 1.1), 0, 3.4, -3.98));
    for (let k = 0; k < 5; k++) g.add(at(pane(1.1, .9 + k * .55, '#ffffff', .22 + k * .06), -2.8 + k * 1.4, 1.6 + (.9 + k * .55) / 2, -3.96));      // (a rising chart on the screen)
    g.add(at(box(GAP, .5, 1.2, '#3a2418'), 0, .25, -3.4)); rug(g, 7, 7, '#b0233f', '#ffc83d', true);
    const sp = new T3.SpotLight('#fff3c4', 1.4, 40, .5, .6); sp.position.set(0, 13, 6); sp.target.position.set(0, 1, 0); g.add(sp, sp.target);
    return {h: ['#c9bfff', '#5a3c2e', .75], k: ['#ffe9c4', 1.05], rim: '#ff8ab0', fog: '#3a2866'}; },
  trading(g) { backdrop(g, ['#0c1430', '#1d2b5c']); ground(g, floorTex('tiles', '#1c2548', '#2a3768'), 2.5, {roughness: .3, metalness: .3}); wall(g, '#141c3c');
    for (let k = 0; k < 33; k++) { const x = -14 + (k % 11) * 2.8, y = 1.6 + Math.floor(k / 11) * 1.75; g.add(at(box(2.5, 1.55, .12, '#0b1026'), x, y, -3.78)); g.add(at(new T3.Mesh(new T3.PlaneGeometry(2.36, 1.4), lit(tickerTex(k + 1), 1.2)), x, y, -3.7)); }
    g.add(at(pane(GAP, .3, '#ffc83d', 1.2), 0, 6.75, -3.7)); rug(g, 8, 4.4, '#1b2a6b', '#3fd0ff'); for (let k = -3; k <= 3; k++) { g.add(at(box(2.6, .9, 1, '#26305a'), k * 4.4 + 2.2, .45, -2.6)); g.add(at(box(.9, .6, .06, '#0b1026'), k * 4.4 + 2.2, 1.25, -2.6)); g.add(at(pane(.8, .5, k % 2 ? '#2bd47d' : '#e8394a', 1.1), k * 4.4 + 2.2, 1.25, -2.56)); }
    return {h: ['#9fb4ff', '#1c2548', .75], k: ['#e6ecff', 1.0], rim: '#5a8cff', fog: '#1d2b5c'}; },
  court(g) { backdrop(g, ['#d9c9a8', '#efe4cb']); ground(g, floorTex('checker', '#efe6d2', '#cdbb98'), 2.4, {roughness: .5}); wall(g, '#eadfc6');
    for (let k = -4; k <= 4; k++) { g.add(at(cyl(.38, .44, 7, '#f6eedc', 16, {flatShading: false}), k * 3.3, 3.5, -3)); g.add(at(box(1.1, .3, 1.1, '#e2d4b6'), k * 3.3, 7.1, -3)); g.add(at(box(1.1, .3, 1.1, '#e2d4b6'), k * 3.3, .15, -3)); } g.add(at(box(GAP, .6, 1.3, '#e2d4b6'), 0, 7.5, -3)); rug(g, 4.6, 9, '#a3263c');
    return {h: ['#fff6e6', '#cdbb98', .85], k: ['#fff1dc', 1.15], rim: '#ffe9c4', fog: '#efe4cb'}; },
  studio(g) { const col = brand(); backdrop(g, [S.shade(col, -.55), S.shade(col, -.25)]); ground(g, floorTex('tiles', S.shade(col, -.5), S.shade(col, -.42)), 3, {roughness: .35, metalness: .15}); wall(g, S.shade(col, -.4), -6);
    const halo = new T3.Mesh(new T3.CircleGeometry(4.2, 40), new T3.MeshBasicMaterial({color: new T3.Color(col), transparent: true, opacity: .32, depthWrite: false})); g.add(at(halo, 0, 2.6, -5.75));
    const h2 = new T3.Mesh(new T3.CircleGeometry(2.6, 40), new T3.MeshBasicMaterial({color: new T3.Color('#ffffff'), transparent: true, opacity: .16, depthWrite: false})); g.add(at(h2, 0, 2.6, -5.7));
    return {h: ['#ffffff', S.shade(col, -.5), .75], k: ['#ffffff', 1.15], rim: col, fog: S.shade(col, -.4)}; },
};

// ---------------------------------------------------------------- the camera: fitted to a shot's subjects, pushing in through its sentence, flying between sets
const P = new T3.Vector3();
function place(v) { cam.position.set(v[0], v[1], v[2]); cam.lookAt(v[3], v[4], v[5]); cam.rotateZ(v[6] || 0); cam.updateMatrixWorld(); cam.updateProjectionMatrix(); }
function toPx(v) { P.copy(v).project(cam); return [(P.x + 1) / 2 * W, (1 - P.y) / 2 * H]; }
function camPose(c, u, k) {      // shot k's camera at u (0..1 through its sentence): it starts wide and to one side and pushes in to the fitted frame.
  // Every third shot looks from low down, every third from higher up; the horizon leans a little, more on a blow (the second model's restless camera).
  const e = 1 - (1 - cl(u)) * (1 - cl(u)), far = k ? .24 : .12, d = c.d * (1 + far - far * e), side = (k % 2 ? 1 : -1) * (k ? .16 : .04) * c.d * (1 - e), m = (R.scenes[k] || {}).mood || 0;
  const rise = k % 3 === 1 ? -.25 + .02 * d : k % 3 === 2 ? .45 + .13 * d : .2 + .09 * d, roll = (k % 2 ? 1 : -1) * (m < 0 ? .055 : .024) * (.4 + .6 * e);
  const T = (R.scenes[k] || {}).t0 + u * 3, hx = .035 * c.d * Math.sin(T * .9 + k), hy = .02 * c.d * Math.sin(T * 1.3 + k * 2);      // (a handheld drift: the third model's camera never rests)
  return [c.ax + side + hx, Math.max(.35, c.ay + rise + hy), d, c.ax + hx * .3, c.ay + hy * .3, 0, roll + .008 * Math.sin(T * .7 + k)];
}
function boxOf(obj) {            // an object's box in the world (people: their pose's fixed box, not their skin's rest pose)
  const b = new T3.Box3(), moved = []; obj.traverse(q => { if (q.userData.rest) { moved.push([q, q.position.clone()]); q.position.copy(q.userData.rest); } });      // (a thing falling in counts where it lands)
  obj.updateMatrixWorld(true);
  obj.traverse(q => { if (q.userData.proxy && q.visible) { const l = q.userData.proxy; b.union(new T3.Box3(new T3.Vector3(l[0], l[1], l[2]), new T3.Vector3(l[3], l[4], l[5])).applyMatrix4(q.matrixWorld)); } });
  if (!obj.userData.proxy) obj.traverse(m => { if (m.isMesh && !m.isSkinnedMesh && m.visible && m.geometry && !m.material.transparent) { const a = m.geometry.attributes.position; for (let i = 0; i < a.count; i++) b.expandByPoint(P.fromBufferAttribute(a, i).applyMatrix4(m.matrixWorld)); } });   // (its real corners: a turned thing is no wider than it is)
  moved.forEach(([q, v]) => q.position.copy(v)); if (moved.length) obj.updateMatrixWorld(true);
  return b;
}
function rectOf(b) {             // a world box as the camera sees it now (px)
  if (b.isEmpty()) return null; let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  for (let i = 0; i < 8; i++) { const [x, y] = toPx(new T3.Vector3(i & 1 ? b.max.x : b.min.x, i & 2 ? b.max.y : b.min.y, i & 4 ? b.max.z : b.min.z)); x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  return [x0, y0, x1 - x0, y1 - y0];
}
function envelope(p) {           // the box a subject sweeps through its own motion (so a bob or a swing never leaves the frame)
  const b = new T3.Box3(); window.__measuring = 1; for (let t = 0; t <= 4; t += .2) { if (p.tick) p.tick(t); b.union(boxOf(p.o)); } window.__measuring = 0; return b;      // (a thing that falls in from out of the frame is measured where it lands)
}
function solve(k, subs, zone) {  // stand the subjects side by side on the stage, then find the camera that fills the zone with them
  let x = 0; const gap = .5;
  subs.forEach((p, i) => { const right = subs.length > 1 && i >= subs.length / 2; p.o.position.set(0, p.lift || 0, 0); p.o.rotation.y = subs.length > 1 && p.actor ? (right ? -.4 : .4) : 0;
    if (p.actor) p.actor.mir = right; p.env = envelope(p); const room = (p.it.kind === 'cart' && !p.it.act) ? [.1, .3] : {launch: [0, .25], bounce: [0, .15], drop: [.05, .05, .05], shake: [.06, 0], exit: [1.1, 0], tilt: [.4, .1, .05], spin: [.15, 0]}[p.it.act]; if (room) { p.env.min.x -= room[0]; p.env.max.x += room[0]; p.env.max.y += room[1]; p.env.min.y -= room[2] || 0; }      // (room in the frame for the subject's act)
    p.o.position.x = x - p.env.min.x; p.x0 = p.o.position.x; x += p.env.max.x - p.env.min.x + gap; });
  const sh = k * GAP - (x - gap) / 2; subs.forEach(p => { p.o.position.x += sh; p.env.translate(new T3.Vector3(p.o.position.x, 0, 0)); });
  const c = {ax: k * GAP, ay: 1.1, d: 9}; if (!subs.length) return c;
  const U = new T3.Box3(); subs.forEach(p => U.union(p.env)); const ht = Math.max(.3, U.max.y - U.min.y); c.ax = (U.min.x + U.max.x) / 2; c.ay = (U.min.y + U.max.y) / 2;
  for (let i = 0; i < 24; i++) { place(camPose(c, 1, k)); const r = rectOf(U), s = Math.min(zone[2] / r[2], zone[3] / r[3]), ppm = r[3] / ht;
    c.ax -= (zone[0] + zone[2] / 2 - (r[0] + r[2] / 2)) / ppm; c.ay += (zone[1] + zone[3] / 2 - (r[1] + r[3] / 2)) / ppm; c.d = cl(c.d / s, 2.6, 24); }
  return c;
}

// ---------------------------------------------------------------- build
const SETG = [], ITEMS = [], FOG = [], CAM = [], SEEN = new Set();
async function build() {
  for (let k = 0; k < R.scenes.length; k++) {
    const sc = R.scenes[k], g = new T3.Group(); g.position.x = k * GAP; g.userData.k = k; scene.add(g); SETG.push(g);
    const L = await (SETS[sc.bg] || SETS.studio)(g); FOG[k] = new T3.Fog(new T3.Color(L.fog), 45, 150);
    g.add(new T3.HemisphereLight(L.h[0], L.h[1], L.h[2]));
    const d = new T3.DirectionalLight(L.k[0], L.k[1]); d.position.set(5, 11, 9); d.castShadow = true; d.shadow.mapSize.set(Q >= 1 ? 2048 : 1024, Q >= 1 ? 2048 : 1024); d.shadow.bias = -.0004; d.shadow.normalBias = .03;
    Object.assign(d.shadow.camera, {left: -11, right: 11, top: 12, bottom: -4, near: 1, far: 40}); d.target.position.set(0, 0, 0); g.add(d, d.target);
    const rim = new T3.DirectionalLight(L.rim, .55); rim.position.set(-6, 5, -7); rim.target.position.set(0, 1, 0); g.add(rim, rim.target);
    const subs = [], flats = sc.items.filter(it => FLAT.has(it.kind));
    for (const it of sc.items) {
      if (FLAT.has(it.kind) || !PROPS[it.kind]) continue;
      const made = await PROPS[it.kind](it), o = made.g; scene.add(o); it.dur = sc.t1 - it.t; it._k = k;
      const p = {k, it, o, tick: made.tick, lift: made.lift || 0, actor: made.actor, tag: null};
      if (it.kind === 'person' && (R.cast[it.who] || {}).tag && it.tag !== false && !SEEN.has(it.who)) { SEEN.add(it.who); p.tag = String(R.cast[it.who].tag).toUpperCase(); }   // (a name tag the first time someone appears)
      subs.push(p); ITEMS.push(p);
    }
    for (const it of flats) ITEMS.push({k, it, flat: true});
    const z = ZONE(flats.length > 0); if (subs.some(p => p.tag)) { z[1] += 96; z[3] -= 96; }
    { const m = .045; z[0] += z[2] * m; z[1] += z[3] * m; z[2] *= 1 - 2 * m; z[3] *= 1 - 2 * m; }      // (room for the punch-in on the words that land)
    CAM[k] = solve(k, subs, z);
  }
}

// ---------------------------------------------------------------- the motion layer (2026-11-25): particles drawn over the picture, seeded so every
// frame stands alone (the frame workers draw out of order): a burst is a pure function of the time since its moment
const hs = k => { const x = Math.sin(k * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
function burst(o, kind, at, x, y, w, h) {       // o: the overlay; kind: confetti | dust | sparks | coins | smoke; at: seconds since it fired
  if (at < 0 || at > 1.6) return; const N = {confetti: 46, dust: 18, sparks: 26, coins: 14, smoke: 10}[kind] || 20;
  o.save();
  for (let i = 0; i < N; i++) { const a = hs(i + 1) * Math.PI * 2, sp = .5 + hs(i + 7), g = 1100;
    let px, py, life = 1 - at / 1.6, r;
    if (kind === 'confetti') { const vx = Math.cos(a) * 620 * sp, vy = -Math.abs(Math.sin(a)) * 900 * sp - 200; px = x + vx * at; py = y + vy * at + .5 * g * at * at; r = 9 + hs(i + 3) * 8;
      o.globalAlpha = Math.min(1, life * 1.6); o.fillStyle = ['#ffd23f', '#2bd47d', '#ff5d8f', '#7fc4ff', '#b98cff', '#ffffff'][i % 6]; o.translate(px, py); o.rotate(at * 9 * (hs(i) - .5)); o.fillRect(-r / 2, -r / 4, r, r / 2); o.setTransform(1, 0, 0, 1, 0, 0); }
    else if (kind === 'dust' || kind === 'smoke') { const vx = Math.cos(a) * 260 * sp; px = x + vx * at * (kind === 'smoke' ? .5 : 1); py = y - 40 * at * sp - (kind === 'smoke' ? 160 * at : 0); r = (kind === 'smoke' ? 40 : 18) + 70 * at * sp;
      o.globalAlpha = .45 * life * life; o.fillStyle = kind === 'smoke' ? '#3a3448' : '#e9dcc4'; o.beginPath(); o.arc(px, py, r, 0, 7); o.fill(); }
    else if (kind === 'sparks') { const d = 380 * sp * Math.sqrt(at), ln = 40 * life; px = x + Math.cos(a) * d; py = y + Math.sin(a) * d * .7;
      o.globalAlpha = life; o.strokeStyle = i % 2 ? '#ffd23f' : '#ffffff'; o.lineWidth = 5; o.beginPath(); o.moveTo(px, py); o.lineTo(px - Math.cos(a) * ln, py - Math.sin(a) * ln); o.stroke(); }
    else { const vx = (hs(i) - .5) * 500, vy = -700 * sp; px = x + (hs(i + 2) - .5) * w + vx * at; py = y + vy * at + .5 * g * at * at; r = 16;
      o.globalAlpha = Math.min(1, life * 2); o.fillStyle = '#ffc83d'; o.strokeStyle = '#a3741a'; o.lineWidth = 4; o.beginPath(); o.ellipse(px, py, r * Math.abs(Math.cos(at * 8 + i)) + 3, r, 0, 0, 7); o.fill(); o.stroke(); } }
  o.restore();
}
const FX = {launch: 'sparks', bounce: 'confetti', drop: 'dust', assemble: 'sparks', exit: 'dust', shake: 'smoke', tilt: 'dust', spin: 'sparks'};
function punch(t) {                // the camera punches in a little on every word that lands (a quick push, eased back): a beat the eye feels
  let z = 0; for (const cp of R.caps || []) { if (cp.t0 > t + .05) break; for (const w of cp.words) if (w.hot) { const d = t - w.t0; if (d > -.02 && d < .5) z = Math.max(z, Math.sin(Math.PI * Math.min(1, (d + .02) / .5)) * (d < .12 ? d / .12 : 1)); } }
  return z;
}

// ---------------------------------------------------------------- the acts: a subject acts out its sentence's verb
const ACTS = {
  assemble(p, lt) {          // its parts glide in and click together (made, built, launched)
    const e = ease(cl(lt / .8));
    if (!p.parts) { p.parts = []; p.o.traverse(m => { if (m.isMesh && m !== p.o) { p.parts.push([m, m.position.clone(), m.rotation.z]); if (!m.userData.rest) m.userData.rest = m.position.clone(); } }); }      // (rest: a part flying in is measured where it lands, like the bag's items: on 2026-11-27 two of three nightly tries died on "factory leaves its area" in the half second of the fly-in)
    p.parts.forEach(([m, q, rz], i) => { const a = i * 2.39996, r = (1 - e) * (.7 + (i % 3) * .2);
      m.position.set(q.x + Math.cos(a) * r, q.y + Math.abs(Math.sin(a)) * r * .8, q.z + Math.sin(a * .7) * r * .4); m.rotation.z = rz + (1 - e) * (i % 2 ? .8 : -.8); });
  },
  drop(p, lt, b) { const u = cl(lt / .4); p.o.position.y = b.y + 1 * (1 - u) * (1 - u); const hit = lt - .4;      // it lands with a thump and a small jolt
    if (hit > 0 && hit < .3) { const k = (1 - hit / .3); p.o.scale.y *= 1 - .06 * k * Math.sin(hit * 30); window.__shake = Math.max(window.__shake || 0, .35 * k); } },
  launch(p, lt, b) { const u = ease(cl((lt - .1) / .5)); p.o.position.y = b.y + .22 * u + .03 * Math.sin(lt * 4) * u; },      // (rises and floats)
  shake(p, lt, b) { const k = .025 * Math.max(0, 1 - lt / .9); p.o.position.x = b.x + Math.sin(lt * 40) * k; p.o.rotation.z = Math.sin(lt * 31) * k; },
  spin(p, lt, b) { p.o.rotation.y = b.ry - .9 * (1 - ease(cl(lt / .9))); },      // (turns to face us)
  bounce(p, lt, b) { p.o.position.y = b.y + .12 * Math.abs(Math.sin(lt * 5)) * Math.max(0, 1 - lt / 1.6); },
  pulse(p, lt) { p.o.scale.multiplyScalar(1 + .03 * Math.sin(lt * 5)); },
  exit(p, lt, b) { const out = b.x > p.k * GAP ? 1 : -1, u = cl((lt - .3) / 1.5); p.o.position.x = b.x + out * 1.05 * ease(u); p.o.position.y = b.y + .06 * Math.abs(Math.sin(lt * 9)) * (u > 0 && u < 1 ? 1 : 0); },      // (walks off towards the edge of the shot, away from the other subject; the frame keeps room for the walk)
  tilt(p, lt, b) { const u = cl(lt / 1.3); p.o.rotation.z = -.16 * Math.sin(Math.PI * u) * (1 - .3 * u); },
};
function act(p, lt) {
  const f = ACTS[p.it.act]; if (!f) return;
  if (!p.b) p.b = {x: p.o.position.x, y: p.o.position.y, ry: p.o.rotation.y};
  f(p, Math.max(0, lt), p.b);
}

// ---------------------------------------------------------------- the frame
function sceneAt(t) { const Sc = R.scenes; const k = Sc.findIndex(s => t < s.t1); return k < 0 ? Sc.length - 1 : k; }
function render(t) {
  const Sc = R.scenes, k = sceneAt(t), b = Sc[k].t0, len = Math.max(.6, Sc[k].t1 - b), flying = k > 0 && t < b + FLY;
  let v;
  if (flying) { const e = ease(cl((t - b) / FLY)), A = camPose(CAM[k - 1], 1, k - 1), B = camPose(CAM[k], FLY / len, k); v = A.map((a, i) => lerp(a, B[i], e)); v[1] += .5 * Math.sin(Math.PI * e); }   // the camera lifts and flies to the next set
  else v = camPose(CAM[k], cl((t - b) / len), k);
  { const z = punch(t) * .07; v[0] = v[3] + (v[0] - v[3]) * (1 - z); v[1] = v[4] + (v[1] - v[4]) * (1 - z); v[2] = v[5] + (v[2] - v[5]) * (1 - z); }      // (the punch-in)
  place(v); window.__shake = 0;
  const on = i => i === k || (flying && i === k - 1);      // (only the sets on camera, and only their lights)
  SETG.forEach((g, i) => { g.visible = on(i); });
  scene.fog = FOG[k] || null; scene.background = FOG[k] ? FOG[k].color : null;      // (never black behind a set)
  for (const [i, f] of LIVE) if (on(i)) f(t);
  for (const p of ITEMS) {
    if (p.flat) continue; const vis = on(p.k) && t >= p.it.t; p.o.visible = vis; if (!vis) continue;
    const lt = t - p.it.t, hook = !p.k && p.it.t < 0 && !p.actor; p.o.scale.setScalar(hook ? .9 + .1 * S.ease(t / .5) : S.ease(lt / .35)); const at = t - Math.max(p.it.t, Sc[p.k].t0 + .2); if (p.tick) p.tick(Math.max(0, at));      // (its act and its own motion start when its shot is on screen, never during the shot before)
    if (hook) p.o.rotation.y = -.3 * (1 - S.ease(t / .6));
    act(p, at);         // (it turns to face us as it grows: readable on the very first frame)
  }
  for (const [tx, draw, it] of DYN) { if (!draw || (it && (it._k !== k && !(flying && it._k === k - 1) || t < it.t))) continue; const {x, c} = tx.userData; draw(x, c.width, c.height, Math.max(0, it ? t - it.t : t)); tx.needsUpdate = true; }
  if (window.__shake > .01) { cam.position.y += Math.sin(t * 70) * .025 * window.__shake; cam.updateMatrixWorld(); }      // (a crash shakes the camera)
  bokeh.uniforms.focus.value = Math.hypot(v[0] - v[3], v[1] - v[4], v[2] - v[5]); comp.render();
  window.__whip = flying ? Math.sin(Math.PI * cl((t - b) / FLY)) : 0;      // (the fourth model's whip pan: the cut smears sideways; drawn on the overlay below)
  // the flat layer: the words in their band, name tags, the header with the scene's date, the captions
  S.reset(); ox.clearRect(0, 0, W, H); const old = S.ctx(ox), sc = Sc[k];
  if (flying) { const f = Math.sin(Math.PI * cl((t - b) / FLY)); ox.save(); ox.globalAlpha = .22 * f; ox.fillStyle = '#ffffff'; ox.fillRect(0, 0, W, H); ox.restore(); }      // (a white flash on every cut)
  if (window.__whip > .05) { ox.save(); for (let i = 1; i <= 9; i++) { ox.globalAlpha = .16 * window.__whip; ox.drawImage(cv, (i - 5) * 26 * window.__whip, 0, W, H); } ox.restore(); }
  if (window.__coverOn) { S.cover(); S.ctx(old); window.__flying = flying; return; }      // (the thumbnail: the series badge and the promise, over the picture alone)
  const gr = ox.createLinearGradient(0, 1200, 0, H); gr.addColorStop(0, 'rgba(8,9,20,0)'); gr.addColorStop(.35, 'rgba(8,9,20,.42)'); gr.addColorStop(1, 'rgba(8,9,20,.72)'); ox.fillStyle = gr; ox.fillRect(0, 1200, W, H - 1200);
  if (!flying) {
    const mine = ITEMS.filter(p => p.k === k && !p.flat && t >= p.it.t), rects = mine.map(p => rectOf(boxOf(p.o)));
    mine.forEach((p, i) => { const r = rects[i]; if (!r) return; S.reg(p.it.kind + (p.it.who ? ':' + p.it.who : ''), ...r);
      if (p.tag && t - p.it.t > .25) { const cx = r[0] + r[2] / 2; let half = Math.min(cx - 70, 1010 - cx); rects.forEach((q, j) => { if (j !== i && q) half = Math.min(half, q[0] > cx ? q[0] - 16 - cx : cx - (q[0] + q[2] + 16)); });
        ox.save(); ox.globalAlpha = cl((t - p.it.t - .25) / .3); const rr = S.pill(p.tag, cx, r[1] - 48, 40, '#fff', '#14182b', Math.max(60, 2 * half - 50)); ox.lineWidth = 4; ox.strokeStyle = S.GOLD; S.rr(...rr, rr[3] / 2); ox.stroke(); ox.restore(); S.reg('tag:' + p.it.who, ...rr); } });
    for (const p of ITEMS) if (p.flat && p.k === k && t >= p.it.t) flat(p.it, t, sc);
    mine.forEach((p, i) => { const r = rects[i], fx = FX[p.it.act] || (p.it.kind === 'person' && p.it.pose === 'cheer' ? 'confetti' : p.it.kind === 'money' ? 'coins' : null); if (!r || !fx) return;
      const t0 = Math.max(p.it.t, sc.t0 + .2) + ({drop: .4, launch: .25, assemble: .75, exit: .4}[p.it.act] || .15), cx = r[0] + r[2] / 2, cy = fx === 'dust' ? r[1] + r[3] : r[1] + r[3] * .45;
      burst(ox, fx, t - t0, cx, cy, r[2], r[3]); });
  }
  if (S.endCard(t)) { S.ctx(old); window.__flying = flying; return; }      // (the ending: the choice card, no captions over it)
  S.header(t, flying ? Sc[k - 1].label : sc.label); S.captions(t); S.ctx(old);
  window.__flying = flying;
}
function flat(it, t, sc) {       // the words slammed on a scene, in the band
  const k = S.K[it.kind], lt = t - it.t, a = cl(lt / .3), [x, y, w, h] = BAND, s = Math.min(w / k[0], h / k[1]), dw = k[0] * s, dh = k[1] * s, X = x + (w - dw) / 2, Y = y + (h - dh) / 2; S.reg(it.kind, X, Y, dw, dh);
  ox.save(); const pop = it.kind === 'counter' ? .9 + .1 * S.ease(a) : 1 + 1.1 * (1 - S.ease(lt / .22)); ox.globalAlpha = cl(lt / .1);
  if (it.kind !== 'stamp') { ox.fillStyle = 'rgba(8,9,20,.42)'; S.rr(X + 14, Y - 2, dw - 28, dh + 4, 34); ox.fill(); }      // (a soft dark plate under big words: a busy set behind never fights the letters)
  ox.translate(X + dw / 2, Y + dh / 2); ox.scale(s * pop, s * pop); ox.translate(-k[0] / 2, -k[1] / 2); k[2](it, lt, a, sc.t1 - it.t); ox.restore();
}
window.render = render;
window.__cams = () => CAM.map(c => [+c.d.toFixed(2), +c.ax.toFixed(2), +c.ay.toFixed(2)]);
window.overlaps = t => {         // every pair of drawn boxes that touch (closer than 10 px), and anything outside its area; flights are skipped
  render(t); if (window.__flying) return [];
  const out = [], B = S.boxes().filter(b => b.name !== 'header');
  for (let i = 0; i < B.length; i++) for (let j = i + 1; j < B.length; j++) { const a = B[i], q = B[j];
    const ix = Math.min(a.x + a.w, q.x + q.w) - Math.max(a.x, q.x), iy = Math.min(a.y + a.h, q.y + q.h) - Math.max(a.y, q.y);
    if (ix > -10 && iy > -10) out.push(a.name + ' x ' + q.name); }
  for (const a of B) if (a.y < 250 || a.x < 40 || a.x + a.w > W - 40 || (a.name !== 'caption' && a.y + a.h > 1290)) out.push(a.name + ' leaves its area');
  return out;
};
window.ready = window.ready.then(() => build()).then(() => { render(0); return true; });
})();
