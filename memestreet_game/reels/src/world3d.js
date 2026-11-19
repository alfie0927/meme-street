/* The story serial's 3D town (the owner, 2026-11-14: "a proper 3D world, where the people are walking around").
   reel.html loads it (after vendor/three.min.js) for a reel of type "Blocky story"; the reel's scene function is
   ({t, api}) => api.world(t). Every scene carries "shots": a place, a camera, actors, props (story_reel.py WHAT is the
   writer's guide, world.py the checker). Everything on screen is a pure function of t: no state is carried from frame to
   frame, so any frame can be drawn alone. The look is our own toy-block town: no game's name, logo, avatars or music. */
(function () {
'use strict';
const VOC={"places":["street","home","doorway","shop","bank","park","square","airport","room"],"cams":["close","mid","low","wide","high","two","over"],"moves":["in","out","orbit","rise","still"],"poses":["idle","walk","run","wave","beg","cheer","shrug","sad","shock","point","sit","type","hold","show","talk","laugh","cry","think","dance","whisper","shake","fall","carry","angry","nod","present"],"faces":["smile","grin","sad","cry","shock","angry","flat","laugh","smug"],"items":["notebook","phone","paper","coin","money","briefcase","padlock","megaphone","photo","chart","key","trophy","parcel"],"skies":["day","sunset","night","red","gold"],"fx":["shake","flash","redflash","confetti","coins","zoom"],"planes":["parked","takeoff","land","fly","away"],"forms":["line","row","cluster","scatter"],"charts":["up","crash","rocket","wobble","flat","down","candles","bounce","rebound"],"emotes":["!","?","$","...","#1","zzz"],"cars":["gold","red","blue","white"]};
const T3 = THREE, R = window.__R, CW = 864, CH = 1536, PI = Math.PI;   // (drawn at 864x1536 and scaled up: software WebGL on the reel server takes about 0.65 s a frame at this size)
const hsh = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const free = document.getElementById('free'); document.body.classList.add('oneword');
const cv = document.createElement('canvas'); cv.id = 'w3d'; cv.style.cssText = 'position:absolute;left:0;top:0;width:1080px;height:1920px'; free.before(cv);
const ov = document.createElement('div'); ov.id = 'w3o'; ov.style.cssText = 'position:absolute;left:0;top:0;width:1080px;height:1920px;box-sizing:border-box'; free.before(ov);
const rn = new T3.WebGLRenderer({ canvas: cv, antialias: true, preserveDrawingBuffer: true });
rn.setSize(CW, CH, false); rn.shadowMap.enabled = true; rn.shadowMap.type = T3.PCFSoftShadowMap;
const scene = new T3.Scene(), cam = new T3.PerspectiveCamera(36, CW / CH, .1, 900);
scene.fog = new T3.Fog(0xcfeaff, 70, 380);
const hemi = new T3.HemisphereLight(0xffffff, 0x8fb87a, .8), sun = new T3.DirectionalLight(0xfff3d6, .75);
sun.castShadow = true; sun.shadow.mapSize.set(1536, 1536); sun.shadow.bias = -.0005; sun.shadow.normalBias = .04;
{ const s = sun.shadow.camera; s.left = -24; s.right = 24; s.top = 24; s.bottom = -24; s.near = 1; s.far = 160; }
scene.add(hemi, sun, sun.target);

// ---------- helpers: merged coloured boxes, canvas textures
const UB = new T3.BoxGeometry(1, 1, 1), VM = new T3.MeshLambertMaterial({ vertexColors: true }), mats = {};
const mat = c => mats[c] || (mats[c] = new T3.MeshLambertMaterial({ color: c }));
const part = (w, h, d, x, y, z, c, ry) => ({ g: new T3.BoxGeometry(w, h, d), m: new T3.Matrix4().makeRotationY(ry || 0).setPosition(x, y, z), c });   // (x, y, z: the centre)
function geoOf(parts) {
  const p = [], n = [], c = [], k = new T3.Color();
  for (const q of parts) {
    const g = q.g.index ? q.g.toNonIndexed() : q.g; g.applyMatrix4(q.m); const P = g.attributes.position.array, N = g.attributes.normal.array; k.set(q.c);
    for (let i = 0; i < P.length; i += 3) { p.push(P[i], P[i + 1], P[i + 2]); n.push(N[i], N[i + 1], N[i + 2]); c.push(k.r, k.g, k.b); }
  }
  const g = new T3.BufferGeometry();
  g.setAttribute('position', new T3.Float32BufferAttribute(p, 3)); g.setAttribute('normal', new T3.Float32BufferAttribute(n, 3)); g.setAttribute('color', new T3.Float32BufferAttribute(c, 3));
  return g;
}
function solid(parts, parent, noShadow) { const m = new T3.Mesh(geoOf(parts), VM); m.castShadow = !noShadow; m.receiveShadow = true; (parent || scene).add(m); return m; }
function tex(w, h) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; const t = new T3.CanvasTexture(c), x = c.getContext('2d'); t.k = null;
  t.paint = (key, fn) => { if (t.k === key) return; t.k = key; fn(x, w, h); t.needsUpdate = true; }; return t;
}
const FONT = px => `900 ${px}px "Arial Black","DejaVu Sans",sans-serif`;
function fitText(x, s, maxW, px) { x.font = FONT(px); while (px > 14 && x.measureText(s).width > maxW) { px -= 2; x.font = FONT(px); } return px; }
function rr(x, a, b, w, h, r) { x.beginPath(); x.moveTo(a + r, b); x.arcTo(a + w, b, a + w, b + h, r); x.arcTo(a + w, b + h, a, b + h, r); x.arcTo(a, b + h, a, b, r); x.arcTo(a, b, a + w, b, r); x.closePath(); }
const fmt = v => (v < 0 ? '-' : '') + Math.abs(Math.round(v)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
function plane(w, h, map, x, y, z, ry, lit) {
  const m = new T3.Mesh(new T3.PlaneGeometry(w, h), new (lit ? T3.MeshLambertMaterial : T3.MeshBasicMaterial)(typeof map === 'string' ? { color: map } : { map }));
  m.position.set(x, y, z); m.rotation.y = ry || 0; scene.add(m); return m;
}
function sign(text, w, h, x, y, z, bg, fg, ry) {
  const t = tex(512, Math.round(512 * h / w));
  t.paint(text, (c, W, H) => { c.fillStyle = bg; c.fillRect(0, 0, W, H); c.fillStyle = fg; c.textAlign = 'center'; c.textBaseline = 'middle'; fitText(c, text, W - 40, H * .7); c.fillText(text, W / 2, H / 2 + 3); });
  return plane(w, h, t, x, y, z, ry);
}

// ---------- the town (static: one merged mesh)
const ST = [], WALLS = [];
const box = (x, y, z, w, h, d, c, ry) => (h > 13 ? WALLS : ST).push(part(w, h, d, x, y + h / 2, z, c, ry));   // (y: the bottom)
const pyr = (x, y, z, w, h, d, c) => { const g = new T3.CylinderGeometry(0, Math.SQRT1_2, 1, 4, 1).toNonIndexed(); g.rotateY(PI / 4); g.scale(w, h, d); g.computeVertexNormals(); ST.push({ g, m: new T3.Matrix4().setPosition(x, y + h / 2, z), c }); };
function house(x, z, w, h, d, wall, roof, door, dir, nodoor) {
  const f = z + dir * d / 2;
  box(x, 0, z, w, h, d, wall); pyr(x, h, z, w + 1.2, h * .6, d + 1.2, roof); box(x + w * .28, h + .2, z - dir * d * .18, .8, h * .5, .8, '#8a5a44');
  if (!nodoor) { box(x, 0, f + dir * .06, 1.3, 2.5, .12, door); box(x + .42, 1.15, f + dir * .14, .14, .14, .08, '#f2c94c'); }
  for (const s of [-1, 1]) { const wx = x + s * w * .31; box(wx, 1.35, f + dir * .04, 1.6, 1.5, .1, '#ffffff'); box(wx, 1.47, f + dir * .08, 1.3, 1.26, .08, '#9fd6ff'); box(wx, 1.47, f + dir * .11, .09, 1.26, .06, '#ffffff'); box(wx, 2.06, f + dir * .11, 1.3, .09, .06, '#ffffff'); }
  box(x, 0, f + dir * 1.75, 1.5, .06, 3.5, '#dccfae');
  for (const s of [-1, 1]) { box(x + s * 2.4, 0, f + dir * 3.1, 1.4, .8, .9, '#4aa85a'); box(x + s * 3.5, 0, f + dir * 3.1, .9, .6, .8, '#57b560'); }
  box(x + 1.15, 0, f + dir * 3.2, .12, 1, .12, '#6b7078'); box(x + 1.15, 1, f + dir * 3.2, .5, .3, .34, '#c2493a');
}
const tree = (x, z, s) => { s = s || 1; box(x, 0, z, .5 * s, 1.9 * s, .5 * s, '#7a4f2a'); box(x, 1.5 * s, z, 2.5 * s, 2 * s, 2.5 * s, '#3f9e4d'); box(x, 3.2 * s, z, 1.7 * s, 1.5 * s, 1.7 * s, '#57b560'); };
const lamp = (x, z, dz) => { box(x, 0, z, .16, 3.6, .16, '#3a3f48'); box(x, 3.5, z + dz * .4, .16, .14, .9, '#3a3f48'); box(x, 3.2, z + dz * .8, .4, .3, .4, '#ffe9a8'); };
(function town() {
  box(0, 0, 0, 260, .06, 7, '#4b4f58'); for (let x = -128; x < 128; x += 4) box(x, .06, 0, 2, .02, .24, '#f2c94c');
  for (const z of [-4.75, 4.75]) box(0, 0, z, 260, .2, 2.5, '#cfd2d7');
  for (const z of [-3.56, 3.56]) box(0, 0, z, 260, .22, .14, '#9aa0a8');
  for (const x of [-36, -24, -12, 0, 12.5, 26]) lamp(x, -3.9, 1);
  // the north row: the old neighbour's, the narrator's (its door is a moving part), Maya's, the shop, the bank
  house(-30, -13, 8, 4.4, 7, '#9ad0d6', '#3d6f8f', '#7a4a2a', 1);
  house(-18, -13, 8, 4.6, 7, '#f5e6c4', '#c2493a', '#5b3a22', 1, true);
  house(-6, -13, 8, 4.2, 7, '#f3b6cb', '#8a4f7d', '#fdfdfd', 1);
  for (const x of [-24, -12, 0]) tree(x, -12.5, .9); for (let x = -40; x <= 24; x += 7) tree(x + 2 * hsh(x), -22 - 3 * hsh(x + 3), 1 + .3 * hsh(x + 5));
  // (inside the narrator's house, for the doorway shots: a dark wall with the door's opening, and a floor)
  box(-20.375, 0, -9.9, 3.05, 4.4, .1, '#17131c'); box(-15.625, 0, -9.9, 3.05, 4.4, .1, '#17131c'); box(-18, 2.5, -9.9, 1.7, 1.9, .1, '#17131c'); box(-18, 0, -13, 7.6, .05, 6.6, '#5a4632');
  // the shop
  box(6, 0, -13, 9, 4.6, 7, '#f7e7c6'); box(6, 4.6, -13, 9.6, .4, 7.6, '#d9b98a'); box(4.6, .9, -9.46, 3.8, 2.1, .1, '#ffffff'); box(4.6, 1, -9.42, 3.5, 1.9, .1, '#9fd6ff'); box(8.6, 0, -9.44, 1.3, 2.5, .12, '#2f6f57');
  for (let i = 0; i < 9; i++) box(2 + i, 2.95, -8.6, 1, .14, 1.9, i % 2 ? '#ffffff' : '#e2504a');
  box(3.1, 0, -8.6, 1.1, .6, .8, '#a8703f'); for (let i = 0; i < 3; i++) box(2.8 + i * .32, .6, -8.6, .26, .24, .26, ['#f2a23a', '#e2504a', '#7ac74f'][i]);
  // the bank
  box(19, 0, -14, 11, 6.6, 8, '#ece7db'); box(19, 0, -9.5, 9.4, .22, 1.3, '#d6d0c2'); box(19, .22, -9.75, 9.4, .22, .7, '#d6d0c2');
  for (const dx of [-4.2, -1.6, 1.6, 4.2]) box(19 + dx, .44, -9.75, .7, 5.2, .7, '#ffffff');
  box(19, 5.64, -9.75, 10.6, .9, 1.2, '#d6d0c2'); pyr(19, 6.6, -14, 11.8, 2, 8.8, '#b8b09c'); box(19, .44, -9.98, 2, 3.2, .12, '#3a2d1e');
  // the park
  box(38, 0, -17, 22, .05, 19, '#62c06a'); box(38, .05, -9.2, 22, .03, 1.6, '#e3d6b4'); box(38, .05, -13, 1.6, .03, 6, '#e3d6b4');
  box(38, .36, -14.6, 2.6, .14, .7, '#a8703f'); box(38, .5, -14.98, 2.6, .75, .12, '#a8703f'); for (const dx of [-1.1, 1.1]) box(38 + dx, 0, -14.6, .14, .36, .6, '#6b4426');
  for (const [x, z, s] of [[30, -20, 1.1], [34, -23.5, 1.3], [42.5, -22, 1.2], [47, -18, 1], [29, -12.5, .9], [47.5, -11.5, 1], [44, -25, 1.2], [35.2, -18.6, 1], [41, -19, 1.15], [31, -16, .8]]) tree(x, z, s);
  box(45.4, .05, -14.6, 5, .06, 3.6, '#5db7ee'); box(45.4, .02, -14.6, 5.5, .06, 4.1, '#e3d6b4');
  for (let i = 0; i < 14; i++) box(29 + 19 * hsh(i), .05, -10.6 - 1.6 * hsh(i + 20), .22, .3, .22, ['#e2504a', '#f2c94c', '#e86aa6', '#ffffff'][i % 4]);
  // the square: paving, a stage, the big screen on two posts, a fountain, flags
  box(-49, 0, -16, 22, .08, 19, '#ddd6c6'); for (let i = 0; i < 5; i++) box(-49, .08, -8.5 - i * 3.6, 22, .01, .12, '#c9c1ae');
  box(-49, 0, -21, 6.4, .7, 2.6, '#8a5a44'); box(-49, .7, -21, 6.6, .06, 2.8, '#a8703f');
  for (const dx of [-3.6, 3.6]) box(-49 + dx, 0, -23.7, .5, 3, .5, '#444a55'); box(-49, 2.9, -23.75, 9.7, 6, .3, '#22262e');
  box(-56.2, 0, -11.5, 3.6, .6, 3.6, '#b9bec7'); box(-56.2, .6, -11.5, 3, .08, 3, '#6cc3f2'); box(-56.2, .6, -11.5, .6, 1.6, .6, '#b9bec7'); box(-56.2, 2.2, -11.5, 1.4, .25, 1.4, '#b9bec7');
  for (const dx of [-9.5, 9.5]) { box(-49 + dx, 0, -24, .16, 7, .16, '#6b7078'); box(-49 + dx + .7, 5.8, -24, 1.3, .9, .06, dx < 0 ? '#e2504a' : '#4f8fe6'); tree(-49 + dx * 1.05, -18, .9); }
  // the airport: apron, runway, tower, hangar, the road to it
  box(72, 0, -31, 64, .05, 22, '#b9bcc2'); box(76, 0, -48, 170, .06, 10, '#3c4048'); for (let x = -4; x < 158; x += 8) box(x, .06, -48, 4, .02, .4, '#ffffff');
  box(94, 0, -36, 3, 10, 3, '#e6e6e6'); box(94, 10, -36, 4.8, 2.2, 4.8, '#7fc4ee'); box(94, 12.2, -36, 5.4, .4, 5.4, '#c2493a');
  box(50, 0, -37, 14, 6.5, 10, '#c9ced6'); box(50, 0, -31.95, 9, 5, .1, '#5b6470'); box(56, 0, -13, 5, .05, 15, '#4b4f58');
  // the far side of the street: a meadow, then a second row of houses; hills all round
  for (let i = 0; i < 11; i++) house(-60 + i * 12, 38, 8, 4.2 + .6 * hsh(i), 7, ['#f5e6c4', '#bfe0b0', '#f3b6cb', '#b9d3f2', '#f7d79a'][i % 5], ['#c2493a', '#3d6f8f', '#8a4f7d', '#5b6470'][i % 4], '#5b3a22', -1);
  for (let i = 0; i < 16; i++) { const x = -90 + i * 12 + 5 * hsh(i + 80); if (x < -26 || x > 10) tree(x, 12 + 14 * hsh(i + 90), .9 + .4 * hsh(i)); }
  for (let i = 0; i < 12; i++) { box(-270 + i * 50, 0, -170 - 30 * hsh(i), 70, 16 + 26 * hsh(i + 9), 40, i % 2 ? '#58a866' : '#4a9a5c'); box(-270 + i * 50, 0, 150 + 30 * hsh(i + 4), 70, 12 + 20 * hsh(i + 5), 40, i % 2 ? '#4a9a5c' : '#58a866'); }
  // the narrator's room, a set far from town: floor, three walls, a rug, a desk with a laptop, a shelf, a plant, a window
  const X = -200, Z = -100;
  box(X, 0, Z + 10, 12, .08, 30, '#c69a66'); for (let i = -4; i <= 4; i++) box(X + i * 1.3, .08, Z + 10, .05, .01, 30, '#a97f52'); box(X - .6, .08, Z + .6, 5.4, .03, 3.6, '#e2504a'); box(X - .6, .1, Z + .6, 4.6, .03, 2.8, '#f3b6a0');
  box(X, 0, Z - 5.1, 12.4, 14, .3, '#f1e6d0'); box(X - 6.1, 0, Z + 10, .3, 14, 30.4, '#e9dcc3'); box(X + 6.1, 0, Z + 10, .3, 14, 30.4, '#e9dcc3');
  box(X - 1.3, 1.2, Z - 4.86, 5.5, 3.6, .2, '#15181d');
  box(X + 4, 1.5, Z - 4.9, 2.3, 2.4, .12, '#ffffff'); box(X + 4, 1.62, Z - 4.86, 2, 2.1, .1, '#9fd6ff'); box(X + 4, 1.62, Z - 4.82, .09, 2.1, .06, '#ffffff');
  box(X + 3.9, .92, Z - 3.1, 2.6, .1, 1.2, '#8a5a3c'); for (const [dx, dz] of [[-1.2, -.5], [1.2, -.5], [-1.2, .5], [1.2, .5]]) box(X + 3.9 + dx, 0, Z - 3.1 + dz, .12, .92, .12, '#6b4426');
  box(X + 3.9, 1.02, Z - 3, .9, .05, .6, '#c9ced6'); box(X + 3.9, 1.05, Z - 3.32, .9, .6, .05, '#22262e');
  box(X - 5.6, 0, Z - 1.5, .6, 3.4, 2.4, '#8a5a3c'); for (let i = 0; i < 12; i++) box(X - 5.5, .5 + Math.floor(i / 4) * 1, Z - 2.4 + (i % 4) * .5, .5, .7, .3, ['#e2504a', '#4f8fe6', '#f2c94c', '#3fb6a8'][(i * 7) % 4]);
  box(X - 4.9, 0, Z - 4.3, .7, .6, .7, '#c96f3a'); box(X - 4.9, .6, Z - 4.3, 1.1, 1.2, 1.1, '#3f9e4d'); box(X - 4.9, 1.6, Z - 4.3, .7, .7, .7, '#57b560');
  solid(ST); solid(WALLS, null, true);
})();
{ // the ground: grass with a soft check, so the camera's moves read
  const t = tex(64, 64); t.paint('g', (x) => { for (let i = 0; i < 4; i++) { x.fillStyle = (i % 3 === 0) ? '#63bf68' : '#5cb962'; x.fillRect((i % 2) * 32, Math.floor(i / 2) * 32, 32, 32); } for (let i = 0; i < 26; i++) { x.fillStyle = i % 2 ? '#6bc66f' : '#55b05b'; x.fillRect(hsh(i) * 60, hsh(i + 30) * 60, 3, 3); } });
  t.wrapS = t.wrapT = T3.RepeatWrapping; t.repeat.set(230, 230);
  const g = new T3.Mesh(new T3.PlaneGeometry(920, 920), new T3.MeshLambertMaterial({ map: t })); g.rotation.x = -PI / 2; g.receiveShadow = true; scene.add(g);
}
sign('MARKET', 6, 1.05, 6, 3.95, -9.42, '#2f6f57', '#ffffff'); sign('BANK', 4.2, .72, 19, 6.08, -9.12, '#3a2d1e', '#ffd23f'); sign('AIRPORT', 7, 1, 50, 5.6, -31.9, '#24345e', '#ffffff');
// moving parts of the town: the narrator's door, the dark behind it, the room's fourth wall, the two screens, the sky, clouds
const DOOR = new T3.Group(); DOOR.position.set(-18.85, 0, -9.5); scene.add(DOOR);
{ const d = new T3.Mesh(UB, mat('#5b3a22')); d.scale.set(1.7, 2.5, .1); d.position.set(.85, 1.25, 0); d.castShadow = true; DOOR.add(d); const k = new T3.Mesh(UB, mat('#f2c94c')); k.scale.set(.14, .14, .22); k.position.set(1.45, 1.15, 0); DOOR.add(k); }
plane(1.7, 2.5, '#120e16', -18, 1.25, -9.485, 0);
{ const w = plane(12.4, 14, '#f1e6d0', -200, 7, -75, PI, true); w.receiveShadow = true; }
const TV = tex(640, 400), BOARD = tex(640, 400), HELD = tex(640, 400);
plane(5.1, 3.2, TV, -201.3, 3, -104.74, 0); plane(9.2, 5.5, BOARD, -49, 5.9, -23.58, 0);
const SKYT = tex(8, 256), SKYM = new T3.Mesh(new T3.SphereGeometry(800, 16, 12), new T3.MeshBasicMaterial({ map: SKYT, side: T3.BackSide, fog: false, depthWrite: false })); scene.add(SKYM);
const CLOUDS = []; for (let i = 0; i < 10; i++) { const s = 1 + hsh(i + 11); const m = solid([part(9 * s, 2.2 * s, 5 * s, 0, 0, 0, '#ffffff'), part(5 * s, 2 * s, 4 * s, 3 * s, 1.6 * s, .5, '#ffffff'), part(4 * s, 1.6 * s, 3.4 * s, -3.4 * s, 1.2 * s, -.4, '#f4f8ff')], null, true); m.receiveShadow = false; CLOUDS.push(m); }
const SKY = { day: ['#2f8de4', '#bfe6ff', '#fff3d6', .75, .8], sunset: ['#4b4aa6', '#ffb37a', '#ffb880', .7, .62], night: ['#070b22', '#27335f', '#9db4ff', .34, .36], red: ['#1d0306', '#a02320', '#ff6a4c', .55, .46], gold: ['#e8962e', '#ffe9a8', '#fff0c0', .8, .78] };

// ---------- places: an origin on the ground, which way the camera side is (ry), how wide a wide shot stands off
const PL = {
  street: { o: [-12, 4.7], wide: 14 }, home: { o: [-18, -8.3], wide: 13 }, doorway: { o: [-18, -9.5], ry: PI, wide: 6.4, wh: 1.9, inside: 1, door: 'open' },
  shop: { o: [6, -7.9], wide: 13 }, bank: { o: [19, -7.6], wide: 15 }, park: { o: [38, -13.6], wide: 13, lane: -9.2 },
  square: { o: [-49, -14], wide: 16, lane: -8.2, h: (x, z) => (Math.abs(x) < 3.2 && z < -5.7 && z > -8.3 ? .76 : .08), screen: BOARD },
  airport: { o: [72, -27], wide: 20, lane: -21 }, room: { o: [-200, -100], wide: 9, wh: 2.7, inside: 1, quiet: 1, screen: TV },
};
for (const k in PL) { const P = PL[k]; P.k = k; P.ry = P.ry || 0; const c = Math.cos(P.ry), s = Math.sin(P.ry); P.w = (x, z) => [P.o[0] + x * c + z * s, P.o[1] - x * s + z * c]; P.h = P.h || (() => (Math.abs(P.o[1]) < 6.2 ? .2 : 0)); }

// ---------- people
const ALIAS = { i: 'narrator', me: 'narrator', 'market sheriff': 'sheriff' };
const nm = s => { s = String(s || '').toLowerCase().replace(/\(.*?\)/g, '').replace(/^the\s+/, '').replace(/[^a-z0-9 ]/g, '').replace(/\s+/g, ' ').trim(); return ALIAS[s] || s; };
const LOOKS = { narrator: { shirt: '#8a96ab', pants: '#2e3a52', hair: '#6b4426', skin: '#f1c27d' }, timmy: { shirt: '#43b05c', pants: '#3a4a6b', hair: '#d6402f', skin: '#f6d0a8', cap: '#d6402f' },
  'mr gold': { shirt: '#f2b632', pants: '#1f2433', hair: '#1b1b1b', skin: '#e8b88a', shades: 1 }, maya: { shirt: '#e0457b', pants: '#3a2f55', hair: '#2b1a10', skin: '#c98b5e', long: 1 },
  'old neighbour': { shirt: '#4fb3c9', pants: '#55452f', hair: '#c9c9c9', skin: '#f3cfa6' }, sheriff: { shirt: '#24345e', pants: '#3b2f22', hair: '#5a3a22', skin: '#e2b48c', hat: '#7a5230', star: 1 } };
for (const k in R.looks || {}) LOOKS[nm(k)] = R.looks[k];   // (a story's own cast: stories.json "looks")
const PAL = { shirt: ['#e2504a', '#4f8fe6', '#f2a23a', '#9b6fe0', '#3fb6a8', '#e86aa6', '#7a8a99', '#d9d04a', '#5aa0d8', '#c96f3a'], pants: ['#2e3a52', '#3b2f22', '#1f2433', '#4a4f5c', '#5b4a6b'], hair: ['#2b1a10', '#6b4426', '#d9a441', '#1b1b1b', '#a55a2a', '#c9c9c9', '#7a3b1d'], skin: ['#f1c27d', '#f6d0a8', '#c98b5e', '#8d5a3b', '#e8b88a', '#f3cfa6'] };
function look(k) {
  if (LOOKS[k]) return LOOKS[k]; let s = 7; for (const ch of k) s = (s * 31 + ch.charCodeAt(0)) % 100003; const pick = (a, j) => a[Math.floor(hsh(s + j) * a.length)];
  return LOOKS[k] = { shirt: pick(PAL.shirt, 1), pants: pick(PAL.pants, 2), hair: pick(PAL.hair, 3), skin: pick(PAL.skin, 4), long: hsh(s + 5) > .62, cap: hsh(s + 6) > .86 ? pick(PAL.shirt, 7) : null };
}
const ACT = {};
function actor(name) {
  const k = nm(name); if (ACT[k]) return ACT[k];
  const L = look(k), a = ACT[k] = { k, L, seed: Object.keys(ACT).length * 1.7 + .3, items: {} }, g = a.g = new T3.Group(), b = a.b = new T3.Group(); g.add(b); scene.add(g);
  solid([part(.86, .85, .44, 0, 1.275, 0, L.shirt)].concat(L.star ? [part(.2, .2, .05, .28, 1.56, .235, '#ffd23f')] : []), b);
  const hd = a.head = new T3.Group(); hd.position.set(0, 1.7, 0); b.add(hd);
  a.ftex = tex(128, 128); const sk = mat(L.skin), hm = new T3.Mesh(UB, [sk, sk, sk, sk, new T3.MeshLambertMaterial({ map: a.ftex }), sk]); hm.scale.set(.74, .68, .68); hm.position.y = .36; hm.castShadow = true; hd.add(hm);
  const hp = [];
  if (!L.bald) { hp.push(part(.8, .2, .74, 0, .76, -.01, L.hair), part(.8, L.long ? 1 : .46, .16, 0, L.long ? .3 : .55, -.33, L.hair)); for (const s of [-1, 1]) hp.push(L.long ? part(.14, .8, .5, s * .4, .36, -.1, L.hair) : part(.1, .3, .5, s * .4, .6, -.1, L.hair)); }
  if (L.cap) hp.push(part(.82, .24, .78, 0, .8, 0, L.cap), part(.66, .07, .36, 0, .7, .5, L.cap));
  if (L.hat) hp.push(part(1.3, .08, 1.2, 0, .76, 0, L.hat), part(.66, .34, .62, 0, .96, 0, L.hat));
  if (L.shades) hp.push(part(.76, .17, .08, 0, .46, .35, '#111111'));
  if (hp.length) solid(hp, hd);
  for (const s of [1, -1]) {   // (+x is the actor's left)
    const ar = new T3.Group(); ar.position.set(s * .57, 1.62, 0); b.add(ar); solid([part(.28, .56, .3, 0, -.2, 0, L.shirt), part(.26, .26, .28, 0, -.61, 0, L.skin)], ar); a[s > 0 ? 'al' : 'ar'] = ar;
    const lg = new T3.Group(); lg.position.set(s * .21, .85, 0); b.add(lg); solid([part(.37, .74, .38, 0, -.37, 0, L.pants), part(.39, .14, .48, 0, -.78, .05, L.shoes || '#2b2b2b')], lg); a[s > 0 ? 'll' : 'lr'] = lg;
  }
  a.ltex = tex(256, 128); a.label = new T3.Mesh(new T3.PlaneGeometry(.72, .36), new T3.MeshBasicMaterial({ map: a.ltex, transparent: true, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 })); a.label.position.set(0, 1.36, .228); b.add(a.label);
  a.etex = tex(128, 128); a.emote = new T3.Sprite(new T3.SpriteMaterial({ map: a.etex })); a.emote.position.set(.56, 2.74, .1); g.add(a.emote);
  a.hand = new T3.Group(); a.hand.position.set(0, -.74, .2); a.ar.add(a.hand);
  return a;
}
function face(a, mood, blink) {
  a.ftex.paint(mood + (blink ? 1 : 0), (x, w, h) => {
    x.fillStyle = a.L.skin; x.fillRect(0, 0, w, h); const E = (cx, cy, rx, ry) => { x.beginPath(); x.ellipse(cx, cy, rx, ry, 0, 0, 7); x.fill(); };
    const sh = mood === 'shock', la = mood === 'laugh', ey = 54; x.fillStyle = x.strokeStyle = '#16181c'; x.lineCap = 'round'; x.lineWidth = 7;
    if (la || blink) for (const cx of [40, 88]) { x.beginPath(); if (la) x.arc(cx, ey + 6, 11, PI * 1.1, PI * 1.9); else { x.moveTo(cx - 10, ey); x.lineTo(cx + 10, ey); } x.stroke(); }
    else { if (sh) { x.fillStyle = '#fff'; E(40, ey, 15, 17); E(88, ey, 15, 17); x.fillStyle = '#16181c'; } E(40, ey, sh ? 7 : 9, sh ? 8 : 12); E(88, ey, sh ? 7 : 9, sh ? 8 : 12); if (!sh) { x.fillStyle = '#fff'; E(43, ey - 4, 3, 3); E(91, ey - 4, 3, 3); x.fillStyle = '#16181c'; } }
    x.lineWidth = 6; const brow = (l, r) => { x.beginPath(); x.moveTo(28, l[0]); x.lineTo(52, l[1]); x.stroke(); x.beginPath(); x.moveTo(76, r[0]); x.lineTo(100, r[1]); x.stroke(); };
    if (mood === 'angry') brow([28, 40], [40, 28]); else if (mood === 'sad' || mood === 'cry') brow([38, 30], [30, 38]); else if (sh) brow([24, 24], [24, 24]); else if (mood === 'smug') brow([34, 34], [26, 30]);
    x.lineWidth = 7; const my = 92;
    if (mood === 'smile' || mood === 'smug') { x.beginPath(); x.arc(64, my - 14, 24, PI * .15, PI * .85); x.stroke(); }
    else if (mood === 'grin' || la) { x.beginPath(); x.moveTo(36, my - 10); x.quadraticCurveTo(64, my + 32, 92, my - 10); x.closePath(); x.fillStyle = '#7a2020'; x.fill(); x.stroke(); x.fillStyle = '#fff'; x.fillRect(47, my - 8, 34, 8); }
    else if (mood === 'sad' || mood === 'cry') { x.beginPath(); x.arc(64, my + 16, 22, PI * 1.2, PI * 1.8); x.stroke(); }
    else if (sh) { x.fillStyle = '#5a1515'; E(64, my + 2, 13, 17); }
    else if (mood === 'angry') { x.beginPath(); x.arc(64, my + 18, 24, PI * 1.25, PI * 1.75); x.stroke(); }
    else { x.beginPath(); x.moveTo(48, my); x.lineTo(80, my); x.stroke(); }
    if (mood === 'cry') { x.fillStyle = '#4fb3ff'; x.fillRect(35, ey + 13, 10, 46); x.fillRect(83, ey + 13, 10, 46); }
  });
}
function chest(a, txt, col, pop) {
  a.label.visible = txt != null && txt !== ''; if (!a.label.visible) return; txt = String(txt); const gold = txt[0] === '#';
  a.ltex.paint(txt + col, (x, w, h) => { x.clearRect(0, 0, w, h); rr(x, 5, 5, w - 10, h - 10, 30); x.fillStyle = gold ? '#ffd23f' : '#fff'; x.fill(); x.lineWidth = 8; x.strokeStyle = '#15171a'; x.stroke(); x.fillStyle = col; x.textAlign = 'center'; x.textBaseline = 'middle'; fitText(x, txt, w - 40, 82); x.fillText(txt, w / 2, h / 2 + 5); });
  const s = 1 + .22 * (pop || 0); a.label.scale.set(s, s, 1);
}
function emote(a, g, k) {
  a.emote.visible = !!g && k > 0; if (!a.emote.visible) return;
  a.etex.paint(g, (x) => { x.clearRect(0, 0, 128, 128); x.fillStyle = '#fff'; x.strokeStyle = '#15171a'; x.lineWidth = 7; x.beginPath(); x.moveTo(48, 98); x.lineTo(64, 126); x.lineTo(80, 98); x.fill(); x.stroke(); x.beginPath(); x.arc(64, 56, 50, 0, 7); x.fill(); x.stroke(); x.fillStyle = g === '!' ? '#e2372f' : g === '$' ? '#1f9d55' : '#15171a'; x.textAlign = 'center'; x.textBaseline = 'middle'; fitText(x, g, 76, 74); x.fillText(g, 64, 60); });
  const s = .72 * back(cl(k)); a.emote.scale.set(s, s, 1);
}
// what a hand can hold (drawn upright whatever the arm does)
const ITEMS = {
  notebook: () => [part(.36, .46, .08, 0, 0, 0, '#7a4a2a'), part(.3, .4, .03, 0, 0, .04, '#f3ead6'), part(.04, .46, .1, -.18, 0, 0, '#3b2414')],
  phone: () => [part(.22, .4, .04, 0, 0, 0, '#15181d'), part(.18, .33, .02, 0, 0, .025, '#6cc3f2')], paper: () => [part(.4, .52, .02, 0, 0, 0, '#ffffff'), part(.3, .04, .01, 0, .14, .012, '#9aa0a8'), part(.3, .04, .01, 0, .04, .012, '#9aa0a8'), part(.3, .04, .01, 0, -.06, .012, '#9aa0a8')],
  coin: () => [part(.26, .26, .05, 0, 0, 0, '#ffd23f'), part(.14, .14, .02, 0, 0, .03, '#c78e1f')], money: () => [part(.44, .22, .14, 0, 0, 0, '#3fae5c'), part(.12, .22, .15, 0, 0, 0, '#f3ead6')],
  briefcase: () => [part(.6, .42, .16, 0, -.2, 0, '#5b3a22'), part(.2, .08, .05, 0, .04, 0, '#2b1a10')], padlock: () => [part(.34, .28, .12, 0, -.06, 0, '#9aa0a8'), part(.05, .2, .05, -.1, .16, 0, '#6b7078'), part(.05, .2, .05, .1, .16, 0, '#6b7078'), part(.25, .05, .05, 0, .26, 0, '#6b7078')],
  megaphone: () => [part(.2, .2, .3, 0, 0, 0, '#e2504a'), part(.34, .34, .16, 0, 0, .22, '#ffffff'), part(.44, .44, .08, 0, 0, .34, '#e2504a')], key: () => [part(.1, .34, .04, 0, 0, 0, '#ffd23f'), part(.22, .16, .04, 0, .22, 0, '#ffd23f')],
  trophy: () => [part(.3, .3, .3, 0, .12, 0, '#ffd23f'), part(.08, .16, .08, 0, -.1, 0, '#c78e1f'), part(.26, .07, .26, 0, -.2, 0, '#5b3a22')],
  photo: () => [part(.5, .42, .02, 0, 0, 0, '#f6f1e5'), part(.42, .3, .01, 0, .03, .012, '#c9a66b'), part(.08, .14, .01, -.07, 0, .02, '#f2b632'), part(.08, .14, .01, .07, 0, .02, '#f2b632')],
  chart: () => [part(1.36, .88, .04, 0, .2, -.03, '#22262e')],
  parcel: () => [part(.5, .4, .4, 0, 0, 0, '#f6f1e5'), part(.52, .08, .42, 0, 0, 0, '#e2372f'), part(.08, .42, .42, 0, 0, 0, '#e2372f'), part(.2, .1, .1, 0, .24, 0, '#e2372f')],
};
function hold(a, name) {
  for (const k in a.items) a.items[k].visible = k === name; if (!name || !ITEMS[name]) return;
  if (!a.items[name]) { const m = a.items[name] = solid(ITEMS[name](), a.hand); if (name === 'chart') { const p = new T3.Mesh(new T3.PlaneGeometry(1.28, .8), new T3.MeshBasicMaterial({ map: HELD })); p.position.set(0, .2, 0); m.add(p); } }
  a.hand.quaternion.copy(a.ar.quaternion).invert();
}
// poses: joint angles as [swing, raise] for an arm (swing < 0 is forward; the left arm raises with +, the right with -)
const POSES = {
  idle: (t, k) => ({ al: [.04 * Math.sin(t * 1.7), .06], ar: [-.04 * Math.sin(t * 1.7), -.06], hy: .1 * Math.sin(t * .6 + k) }),
  wave: t => ({ ar: [0, -(2.55 + .32 * Math.sin(t * 9))], al: [0, .08], hz: .05 * Math.sin(t * 9) }),
  beg: t => ({ al: [-1.2 + .07 * Math.sin(t * 3), -.12], ar: [-1.2 + .07 * Math.sin(t * 3), .12], hx: -.12, lean: .1 }),
  cheer: (t, k) => ({ al: [0, 2.7 + .15 * Math.sin(t * 10)], ar: [0, -2.7 - .15 * Math.sin(t * 10)], y: .22 * Math.abs(Math.sin(t * 5.5 + k)), hx: -.1 }),
  shrug: t => { const s = .5 + .5 * Math.sin(t * 3.2); return { al: [-.35 * s, .55 * s], ar: [-.35 * s, -.55 * s], hz: .14 * s, y: .04 * s }; },
  sad: t => ({ hx: .38, lean: .1, al: [.05, .03], ar: [.05, -.03], hy: .05 * Math.sin(t) }),
  shock: (t, k, u) => ({ al: [.35, 1.05], ar: [.35, -1.05], lean: -.13, hx: -.08, y: .3 * Math.max(0, Math.sin(Math.min(u, .45) / .45 * PI)) }),
  point: () => ({ ar: [-1.5, -.05], al: [0, .08] }),
  sit: () => ({ ll: -1.5, lr: -1.5, y: -.36, al: [-.5, .05], ar: [-.5, -.05] }),
  type: t => ({ ll: -1.5, lr: -1.5, y: -.36, al: [-1.15 + .08 * Math.sin(t * 14), -.1], ar: [-1.15 + .08 * Math.cos(t * 14), .1], hx: .12 }),
  hold: () => ({ ar: [-1.05, -.42], al: [0, .08] }),
  show: t => ({ ar: [-2.7, -.12], al: [0, .08], y: .03 * Math.sin(t * 4) }),
  talk: t => ({ ar: [-.75 + .3 * Math.sin(t * 5), -.2], al: [-.2, .12], hx: .05 * Math.sin(t * 6) }),
  laugh: t => ({ al: [-.55, -.35], ar: [-.55, .35], hx: -.22, y: .07 * Math.abs(Math.sin(t * 11)), lean: -.06 }),
  cry: t => ({ al: [-1.8, -.42], ar: [-1.8, .42], hx: .22, lean: .1, y: .02 * Math.sin(t * 16) }),
  think: () => ({ ar: [-2.3, .42], al: [-.3, -.55], hz: .12, hy: .15 }),
  dance: t => ({ al: [0, 1.4 + 1.1 * Math.sin(t * 7)], ar: [0, -1.4 + 1.1 * Math.sin(t * 7)], roll: .14 * Math.sin(t * 7), y: .12 * Math.abs(Math.sin(t * 7)), ll: .2 * Math.sin(t * 7), lr: -.2 * Math.sin(t * 7) }),
  whisper: () => ({ ar: [-2.2, .5], lean: .16, hy: .3 }),
  shake: t => ({ ar: [-1.25 + .12 * Math.sin(t * 10), .05], al: [0, .08] }),
  fall: (t, k, u) => ({ fall: out(cl(u / .45)), al: [0, 1.2], ar: [0, -1.2] }),
  carry: () => ({ al: [-1.2, -.2], ar: [-1.2, .2] }),
  angry: t => ({ al: [-.2, .9], ar: [-.2, -.9], lean: .1, y: .03 * Math.sin(t * 14) }),
  present: t => ({ ar: [0, -(1.45 + .06 * Math.sin(t * 3))], al: [0, .08], hy: -.42 }),
  nod: t => ({ hx: .18 * Math.sin(t * 7), al: [0, .06], ar: [0, -.06] }),
};
POSES.walk = POSES.run = POSES.idle;
const MOOD = { cheer: 'grin', sad: 'sad', cry: 'cry', shock: 'shock', laugh: 'laugh', angry: 'angry', beg: 'sad', dance: 'grin', fall: 'shock' };
const PK = ['alx', 'alz', 'arx', 'arz', 'll', 'lr', 'hx', 'hy', 'hz', 'lean', 'roll', 'y', 'fall'];
const flat = P => ({ alx: P.al ? P.al[0] : 0, alz: P.al ? P.al[1] : .05, arx: P.ar ? P.ar[0] : 0, arz: P.ar ? P.ar[1] : -.05, ll: P.ll || 0, lr: P.lr || 0, hx: P.hx || 0, hy: P.hy || 0, hz: P.hz || 0, lean: P.lean || 0, roll: P.roll || 0, y: P.y || 0, fall: P.fall || 0 });
const mix = (A, B, k) => { const o = {}; for (const q of PK) o[q] = A[q] + (B[q] - A[q]) * k; return o; };
function setPose(a, F) { a.al.rotation.set(F.alx, 0, F.alz); a.ar.rotation.set(F.arx, 0, F.arz); a.ll.rotation.x = F.ll; a.lr.rotation.x = F.lr; a.head.rotation.set(F.hx, F.hy, F.hz); a.b.rotation.set(F.lean - F.fall * 1.5, 0, F.roll); a.b.position.y = F.y; }

// ---------- the gold plane, the sports car, traffic
const PLN = new T3.Group(); scene.add(PLN);
{ const G = '#f2b632', D = '#c78e1f', W = '#27324d';
  solid([part(10, 1.9, 1.9, 0, 2, 0, G), part(1.5, 1.4, 1.5, 5.6, 1.9, 0, G), part(.9, .7, 1.2, 5.2, 2.75, 0, W), part(.3, 2.3, 1.7, -4.6, 3.6, 0, D), part(1.7, .2, 4.6, -4.5, 2.6, 0, D), part(2.7, .22, 11.5, .2, 1.5, 0, D),
    part(1.5, .7, .7, .6, 1.05, 3.2, W), part(1.5, .7, .7, .6, 1.05, -3.2, W), part(.4, .9, .4, 3.2, .45, 0, '#22262e'), part(.4, .9, .4, -1.2, .45, 1.2, '#22262e'), part(.4, .9, .4, -1.2, .45, -1.2, '#22262e'), part(.8, 1.5, .06, 2.4, 1.95, .96, W)]
    .concat([-3, -2, -1, 0, 1].map(i => part(.55, .5, .06, i * 1.05 - .3, 2.35, .96, W))), PLN);
  PLN.stairs = solid([0, 1, 2, 3].map(i => part(.9, .26, .5, 2.4, 1.0 - i * .3, 1.25 + i * .5, '#d9dce2')), PLN); }
function car(c, sport) {
  const g = new T3.Group(), P = sport ? [part(4.4, .55, 1.9, 0, .6, 0, c), part(1.6, .28, 1.8, 1.2, .98, 0, c), part(.1, .5, 1.7, .5, 1.12, 0, '#bfe6ff'), part(1.5, .5, 1.5, -.6, .7, 0, '#2b2b2b'), part(.3, .3, 1.9, -2, 1.05, 0, c), part(.08, .26, .08, -2, .86, .8, c), part(.08, .26, .08, -2, .86, -.8, c)]
    : [part(4, .7, 1.8, 0, .65, 0, c), part(2.2, .7, 1.7, -.2, 1.35, 0, c), part(2.24, .5, 1.5, -.2, 1.38, 0, '#bfe6ff'), part(.1, .2, 1.4, 2, .7, 0, '#ffe9a8')];
  for (const [x, z] of [[1.35, .9], [1.35, -.9], [-1.35, .9], [-1.35, -.9]]) P.push(part(.7, .7, .3, x, .35, z, '#1d1f24'), part(.3, .3, .32, x, .35, z, '#c9ced6'));
  solid(P, g); scene.add(g); return g;
}
const CARCOL = { gold: '#f2b632', red: '#e2372f', blue: '#3f7fe0', white: '#f4f4f4' }, HERO = {}, TRAFFIC = ['#e2504a', '#4f8fe6', '#f4f4f4', '#3fb6a8'].map(c => car(c));
const CONF = new T3.InstancedMesh(UB, new T3.MeshLambertMaterial(), 90); CONF.instanceMatrix.setUsage(T3.DynamicDrawUsage); CONF.frustumCulled = false; CONF.count = 0; scene.add(CONF);
for (let i = 0; i < 90; i++) CONF.setColorAt(i, new T3.Color('#ffffff'));

// ---------- the timeline of shots
const SH = []; let still = false;
const nkw = w => String(w).toLowerCase().replace(/[^a-z0-9%$.]/g, '');
function atSay(s, phrase) {   // when a phrase of the line is said, found on the written words (narrate.py "vt"), so 'hit zero' is found though the caption shows 0
  if (!s.vt) return API.at(s, phrase);
  const P = String(phrase || '').split(/\s+/).map(nkw).filter(Boolean), W = String(s.vo || '').split(/\s+/).map(nkw);
  for (let k = 0; P.length && k + P.length <= W.length; k++) if (P.every((w, j) => W[k + j] === w || W[k + j].startsWith(w))) return s.vt[Math.min(k, s.vt.length - 1)];
  return s.vs || s.t0;
}
(function shots() {
  const SCN = R.scenes; let last = null;
  SCN.forEach((s, i) => {
    const L = s.shots && s.shots.length ? s.shots : last ? [] : [{ place: 'street', cam: 'wide' }];   // (a scene with no shots, the end card: the last shot plays on under it)
    L.forEach((q, k) => { let t0 = k === 0 ? s.t0 : s.vs + (s.ve - s.vs) * k / L.length; if (k && q.say) { const a = atSay(s, q.say); if (a > s.vs + .05) t0 = a - .05; }   // (words that are not found in the line: the shots share the scene evenly)
      if (SH.length && t0 < SH[SH.length - 1].t0 + .5) t0 = SH[SH.length - 1].t0 + .5; last = { s: q, sc: s, i: SH.length, t0, prevSky: last ? last.sky : 'day' }; last.sky = SKY[q.sky] ? q.sky : last.prevSky; SH.push(last); });
  });
  SH.forEach((S, k) => { S.t1 = k + 1 < SH.length ? SH[k + 1].t0 : S.sc.t1; S.t0 = k ? S.t0 : -1; });
})();
const when = (S, say, d) => { const t = say ? atSay(S.sc, say) : null; return t == null || t <= S.sc.vs + .02 || t < S.t0 - .2 || t > S.t1 ? d : t; };   // (a phrase said in another shot of the scene does not count)
const xz = v => (Array.isArray(v) ? [+v[0] || 0, +v[1] || 0] : [0, 0]);
function prep(S) {
  if (S.A) return S; const q = S.s, P = S.P = PL[q.place] || PL.street, mid = S.t0 + (S.t1 - S.t0) * .5; S.A = []; S.by = {};
  const add = (e, delay) => {
    const th = e.then || null, ts = th ? when(S, e.say, Math.max(S.t0, 0) + (S.t1 - Math.max(S.t0, 0)) * .5) + (delay || 0) : null, E = { who: nm(e.who), ts, s1: e, s2: th ? Object.assign({}, e, th) : e, segs: [], p0: xz(e.at), in: e.in };
    const leg = (ta, from, to, run, end) => { const len = Math.hypot(to[0] - from[0], to[1] - from[1]); if (len < .05) return; E.segs.push({ ta, from, to, len, run, dur: Math.max(.3, Math.min(len / (run ? 3.6 : 1.55), end - ta - .1)) }); };
    if (e.to) leg(Math.max(S.t0, 0) + (delay || 0), E.p0, xz(e.to), e.do === 'run', th ? ts : S.t1 + 9);
    if (th && th.to) leg(ts, e.to ? xz(e.to) : E.p0, xz(th.to), th.do === 'run', S.t1 + 9);
    const tg = e.look; E.f0 = E.segs.length && E.segs[0].ta <= S.t0 + .3 ? Math.atan2(E.segs[0].to[0] - E.segs[0].from[0], E.segs[0].to[1] - E.segs[0].from[1]) : Array.isArray(tg) ? Math.atan2(tg[0] - E.p0[0], tg[1] - E.p0[1]) : null;
    S.A.push(E); S.by[E.who] = E;
  };
  const turn = () => S.A.forEach(E => { const o = typeof E.s1.look === 'string' && S.by[nm(E.s1.look)]; if (E.f0 == null && o) E.f0 = .55 * Math.atan2(o.p0[0] - E.p0[0], o.p0[1] - E.p0[1]); });
  (q.actors || []).forEach(e => add(e, 0));
  (Array.isArray(q.crowd) ? q.crowd : q.crowd ? [q.crowd] : []).forEach((c, ci) => {
    const n = Math.min(14, c.n || 6), at = xz(c.at), gap = c.gap || 1.15;
    for (let k = 0; k < n; k++) {
      const id = ci * 20 + k + 1, r = hsh(id * 3.1), pos = c.form === 'line' ? [at[0] + k * gap, at[1] + .12 * (r - .5)] : c.form === 'row' ? [at[0] + (k - (n - 1) / 2) * gap, at[1] + .3 * (r - .5)]
        : c.form === 'scatter' ? [at[0] + (hsh(id) - .5) * 9, at[1] + (hsh(id + 9) - .5) * 5] : [at[0] + Math.cos(PI * (1.15 + .7 * k / Math.max(1, n - 1))) * (2.3 + 1.3 * (k % 2)), at[1] + Math.sin(PI * (1.15 + .7 * k / Math.max(1, n - 1))) * (2.3 + 1.3 * (k % 2))];
      const base = Math.round((900 + hsh(id + 70) * 62000) / 10) * 10, cv2 = v => (v === 'rand' ? base : v === 'x2' ? base * 2 : v === 'x10' ? base * 10 : v === 'half' ? base / 2 : v === 'zero' ? 0 : v === 'neg' ? -Math.round(base / 3) : v);
      const e = Object.assign({}, c, { who: 'townie ' + id, at: pos, chest: cv2(c.chest == null ? 'rand' : c.chest), look: c.look || (c.form === 'line' ? [at[0] - 4, at[1]] : c.form === 'cluster' ? at : undefined) });
      if (c.then) e.then = Object.assign({}, c.then, c.then.chest != null ? { chest: cv2(c.then.chest) } : {});
      if (c.to) e.to = [pos[0] + (c.to[0] - at[0]), pos[1] + (c.to[1] - at[1])];
      add(e, k * .07);
    }
  });
  turn(); const C = String(q.cam || 'wide').split(':'); S.ck = CAMS[C[0]] ? C[0] : 'wide'; S.tg = (CAMS[C[0]] ? C[1] || '' : C[0]).split(/[,>]/).map(x => x.trim()).filter(Boolean);
  S.fx = (q.fx || []).map(f => (typeof f === 'string' ? { do: f } : f)).map(f => ({ do: f.do, t: when(S, f.say, Math.max(S.t0, 0)) }));
  S.skyT = q.sky_say ? when(S, q.sky_say, null) : null;
  if (q.plane) { const p = typeof q.plane === 'string' ? { mode: q.plane } : q.plane; S.plane = { mode: p.mode || 'parked', at: p.at ? xz(p.at) : [0, -8], t: when(S, p.say, Math.max(S.t0, 0)) }; }
  if (q.car) { const c = q.car; S.car = { c: CARCOL[c.color] ? c.color : 'gold', from: xz(c.from || [-9, -3]), to: xz(c.to || c.from || [9, -3]), t: when(S, c.say, Math.max(S.t0, 0)), who: c.who ? nm(c.who) : null }; if (S.car.who && S.by[S.car.who]) S.by[S.car.who].in = 'car'; }
  S.doorT = q.door === 'burst' ? when(S, q.door_say, mid) : null;
  // people and traffic that are simply there: hidden for the whole shot if they would cross between the camera and the actors
  S.amb = [];
  if (!P.quiet) {
    const lanes = [-5.3, -4.3, 4.2, 5.3].concat(P.lane ? [P.lane, P.lane - .9] : []), c0 = camAt(S, Math.max(S.t0, 0)), fx = c0.g.x, samples = []; for (let k = 0; k <= 12; k++) { const t = Math.max(S.t0, 0) + (S.t1 - Math.max(S.t0, 0)) * k / 12; samples.push([t, camAt(S, t)]); }
    const clear = (pos, r) => samples.every(([t, c]) => { const p = pos(t), ax = c.p.x, az = c.p.z, bx = c.g.x, bz = c.g.z, dx = bx - ax, dz = bz - az, u = cl(((p[0] - ax) * dx + (p[1] - az) * dz) / (dx * dx + dz * dz || 1)); if (Math.hypot(p[0] - ax - dx * u, p[1] - az - dz * u) < r) return false; return S.A.every(E => { const l = where(S, E, t), w = P.w(l[0], l[1]); return Math.hypot(p[0] - w[0], p[1] - w[1]) > r + .4; }); });
    for (let k = 0; k < 10; k++) { const z = lanes[k % lanes.length], v = (hsh(k + 40 + S.i) > .5 ? 1 : -1) * (1.15 + .5 * hsh(k + 50)), off = hsh(k * 7 + S.i * 3 + 60) * 44, pos = t => [fx + ((((off + v * t) % 44) + 44) % 44) - 22, z]; if (clear(pos, 1.5)) S.amb.push({ who: 'walker ' + k, pos, v, chest: Math.round((900 + hsh(k + 70) * 88000) / 10) * 10 }); }
    S.cars = []; TRAFFIC.forEach((m, k) => { const v = k % 2 ? -8.5 : 9.5, z = k % 2 ? -1.75 : 1.75, off = hsh(k * 5 + S.i + 3) * 90, pos = t => [fx + ((((off + v * t) % 90) + 90) % 90) - 45, z]; if (clear(pos, 3.2) && !(S.car && Math.abs(P.w(0, S.car.from[1])[1]) < 3.6)) S.cars.push({ m, pos, v }); });
  }
  return S;
}
// where an actor stands at t (place coordinates), and which way they face
function where(S, E, t) {
  let p = E.p0, mv = null, done = null;
  for (const g of E.segs) if (t >= g.ta) { const k = cl((t - g.ta) / g.dur); p = [lerp(g.from[0], g.to[0], k), lerp(g.from[1], g.to[1], k)]; mv = k < 1 ? { g, k } : null; done = g; }
  p.mv = mv; p.done = done; return p;
}
function spot(S, name, t) {   // a camera target: an actor, or a thing
  const P = S.P, E = S.by[nm(name)];
  if (E) { if (E.in === 'car' && S.car) { const c = carAt(S, t); return { x: c.x, y: .25, z: c.z, f: c.ry - P.ry + PI / 2, E, wheel: 1 }; } const p = where(S, E, t), w = P.w(p[0], p[1]); return { x: w[0], y: P.h(p[0], p[1]), z: w[1], f: E.f0, E }; }
  if (name === 'plane' && S.plane && S.plane.mode !== 'away') { const m = planeAt(S, t); return { x: m.x, y: m.y + .6, z: m.z, plane: 1 }; }
  if (name === 'car' && S.car) { const c = carAt(S, t); return { x: c.x, y: 0, z: c.z }; }
  if (name === 'screen' && P.screen) { const rm = P.k === 'room', w = rm ? P.w(-1.3, -4.7) : P.w(0, -9.5); const w3 = rm ? P.w(-.2, -4.7) : w; return { x: w3[0], y: rm ? 3 : 5.9, z: w3[1], w: rm ? 7.4 : 9.2, thing: 'screen' }; }
  if (name === 'door') return { x: -18, y: 0, z: -9.5, thing: 1 };
  return null;
}
const CAMS = { close: { d: 4.7, h: 1.8, y: 1.5, f: 34, a: 13 }, mid: { d: 7.6, h: 1.9, y: 1, f: 36, a: 17 }, low: { d: 4.4, h: .5, y: 1.5, f: 42, a: 22 }, wide: { f: 50, a: 9 }, high: { f: 46, a: 24 }, two: { f: 36, a: 8 }, over: { f: 40, a: 0 } };
function camAt(S, t) {
  const P = S.P, q = S.s, C = CAMS[S.ck], u = cl((t - Math.max(S.t0, 0)) / (S.t1 - Math.max(S.t0, 0))), mv = q.move || 'in', side = S.i % 2 ? 1 : -1;
  let zoom = mv === 'in' ? 1 - .09 * u : mv === 'out' ? 1 + .12 * u : 1; const a0 = (q.angle != null ? q.angle : P.inside && P.k !== 'room' ? 0 : side * C.a) * PI / 180 + (mv === 'orbit' ? .4 * (u - .5) : 0), dh = mv === 'rise' ? 2.4 * u : 0;
  for (const f of S.fx || []) if (f.do === 'zoom') zoom *= 1 - .17 * out(seg(t, f.t, f.t + .25));
  const T = S.tg.map(n => spot(S, n, t)).filter(Boolean), o = P.w(0, 0), pts = S.A.map(E => where(S, E, Math.max(S.t0, 0)));
  let g, d, h, y, phi = P.ry, a = a0;
  if (T[0] && T[0].thing === 'screen') { g = T[0]; d = g.w / .34 * 1.12; y = g.y - .11 * d; h = y + 1; a = q.angle != null ? a0 : 0; }   // (the screen fills the frame's width, the room or the square under it)
  else if ((S.ck === 'close' || S.ck === 'mid' || S.ck === 'low') && T[0]) { const s = T[0], seat = s.E && (s.E.in === 'car' || /^(sit|type)$/.test(s.E.s1.do || '')) ? -.36 : 0; g = s; d = C.d * (s.thing ? 1.8 : S.ck !== 'mid' && s.E && (s.E.s1.emote || s.E.s2.emote) ? 1.3 : 1);   /* (a bubble by the head needs the room: it was cut off at the frame's edge) */ h = s.y + C.h + seat + (s.thing ? 1.4 : 0); y = s.y + C.y + seat + (s.thing ? 1 : 0); if (s.f != null) phi += s.f; if (s.wheel && q.angle == null) a = side * 34 * PI / 180; }
  else if (S.ck === 'two' && T[1]) { g = { x: (T[0].x + T[1].x) / 2, z: (T[0].z + T[1].z) / 2 }; const sep = Math.hypot(T[0].x - T[1].x, T[0].z - T[1].z), by = Math.max(T[0].y, T[1].y); d = Math.max(5.4, (sep + 1.7) / .36); h = by + 1.75; y = by + 1.15; }
  else if (S.ck === 'over' && T[1]) { const A = T[0], B = T[1], dx = A.x - B.x, dz = A.z - B.z, L = Math.hypot(dx, dz) || 1; return { p: new T3.Vector3(A.x + dx / L * 2.1 * zoom - dz / L * .8, A.y + 2.25 + dh, A.z + dz / L * 2.1 * zoom + dx / L * .8), g: new T3.Vector3(B.x, B.y + 1.5, B.z), f: C.f }; }
  else {
    let cx = 0, cz = 0, ex = 0, far = 0; if (T[0]) { g = T[0]; far = g.plane ? 34 : 0; } else { if (pts.length) { cx = pts.reduce((s, p) => s + p[0], 0) / pts.length; cz = pts.reduce((s, p) => s + p[1], 0) / pts.length; ex = Math.max(...pts.map(p => Math.abs(p[0] - cx))); } const w = P.w(cx, cz); g = { x: w[0], z: w[1], y: P.h(cx, cz) }; }
    const hi = S.ck === 'high'; d = far || Math.max(P.wide * (hi ? .9 : .8), Math.min(40, (2 * ex + 3.2) / .5)); h = (g.y || 0) + (hi ? d * .95 : (P.wh || 4.4) * Math.sqrt(d / P.wide)); y = (g.y || 0) + (hi ? 0 : P.inside ? 1.3 : 1);
  }
  d *= zoom; let px = g.x + Math.sin(phi + a) * d, pz = g.z + Math.cos(phi + a) * d, sx = 0, sy = 0;
  for (const f of S.fx || []) if (f.do === 'shake' && t >= f.t) { const k = Math.exp(-4.5 * (t - f.t)); sx += .16 * k * Math.sin(t * 61); sy += .12 * k * Math.sin(t * 47 + 1); }
  return { p: new T3.Vector3(px + sx, h + dh + sy, pz), g: new T3.Vector3(g.x + sx, y + sy, g.z), f: T[0] && T[0].thing === 'screen' ? 34 : C.f };
}
function planeAt(S, t) {
  const p = S.plane, P = S.P, w = P.w(p.at[0], p.at[1]), k = cl((t - p.t) / Math.max(.6, S.t1 - p.t)), m = { x: w[0], y: 0, z: w[1], pitch: 0, sc: 1, stairs: p.mode === 'parked' };
  const go = (k2) => { m.x += 95 * k2 * k2 * Math.cos(P.ry); m.z -= 95 * k2 * k2 * Math.sin(P.ry); const up = Math.max(0, k2 - .42); m.y = 46 * up * up * 3; m.pitch = .3 * io(cl(up * 4)); };
  if (p.mode === 'takeoff') go(k); else if (p.mode === 'land') { go(1 - out(k)); m.x = 2 * w[0] - m.x; m.z = 2 * w[1] - m.z; m.pitch *= -.6; m.stairs = k > .97; }
  else if (p.mode === 'fly') { m.x += (k - .5) * 70 * Math.cos(P.ry); m.z -= (k - .5) * 70 * Math.sin(P.ry) + 26; m.y = 21; }
  else if (p.mode === 'away') { const w2 = P.w(p.at[0] + 6 + 14 * k, p.at[1] - 150); m.x = w2[0]; m.z = w2[1]; m.y = 58 + 10 * k; m.pitch = .2; m.sc = .5; }
  return m;
}
function carAt(S, t) { const c = S.car, P = S.P, k = io(cl((t - c.t) / Math.max(.5, S.t1 - c.t - .1))), p = [lerp(c.from[0], c.to[0], k), lerp(c.from[1], c.to[1], k)], w = P.w(p[0], p[1]), dx = c.to[0] - c.from[0], dz = c.to[1] - c.from[1]; return { x: w[0], z: w[1], ry: P.ry + (Math.hypot(dx, dz) > .1 ? Math.atan2(-dz, dx) : 0), roll: k * Math.hypot(dx, dz) / .35 }; }
function screenPaint(tx, c, u, big) {
  const st = Math.round(cl(u) * 28); tx.paint(JSON.stringify(c) + st, (x, w, h) => {
    const p = st / 28, mode = c.lines ? 'plan' : c.chart ? 'chart' : 'text'; x.textBaseline = 'middle';
    if (mode === 'plan') { x.fillStyle = '#7a4a2a'; x.fillRect(0, 0, w, h); x.fillStyle = '#2f6b4f'; x.fillRect(14, 14, w - 28, h - 28); x.fillStyle = '#fff'; x.textAlign = 'center'; fitText(x, String(c.title || 'MY PLAN').toUpperCase(), w - 80, 58); x.fillText(String(c.title || 'MY PLAN').toUpperCase(), w / 2, 62);
      const L = c.lines.slice(0, 3); L.forEach((s, k) => { const y = 142 + k * 84, on = p > (k + 1) / (L.length + 1); x.strokeStyle = '#fff'; x.lineWidth = 6; x.strokeRect(46, y - 24, 48, 48); if (on) { x.strokeStyle = '#7dffa8'; x.lineWidth = 9; x.beginPath(); x.moveTo(54, y); x.lineTo(68, y + 16); x.lineTo(92, y - 20); x.stroke(); } x.fillStyle = '#fff'; x.textAlign = 'left'; fitText(x, String(s), w - 170, 40); x.fillText(String(s), 122, y + 2); }); return; }
    x.fillStyle = '#0b0f13'; x.fillRect(0, 0, w, h);
    if (mode === 'text') { const L = String(c.text || c.title || '').split('|').slice(0, 3); x.textAlign = 'center'; L.forEach((s, k) => { x.fillStyle = k ? '#e6e9ec' : ({ red: '#f0585c', green: '#3dd68c', gold: '#ffd23f' }[c.tone] || '#ffd23f'); fitText(x, s.trim(), w - 70, L.length > 1 ? 86 : 120); x.fillText(s.trim(), w / 2, h / 2 + (k - (L.length - 1) / 2) * 104); }); return; }
    x.strokeStyle = '#1b222b'; x.lineWidth = 2; for (let k = 1; k < 5; k++) { x.beginPath(); x.moveTo(0, 90 + k * 52); x.lineTo(w, 90 + k * 52); x.stroke(); }
    const F = { up: q => .18 + .62 * q, crash: q => (q < .62 ? .22 + .95 * q : Math.max(.03, .81 - (q - .62) * 3.4)), rocket: q => .07 + .9 * q * q * q, wobble: q => .5 + .22 * Math.sin(q * 9) + .16 * Math.sin(q * 23), flat: () => .5, down: q => .86 - .72 * q, candles: q => .38 + .2 * Math.sin(q * 7) + .22 * q,
      bounce: q => .24 + .5 * Math.abs(Math.sin(q * 7.5 + .6)) * (.75 + .25 * Math.sin(q * 3)), rebound: q => (q < .45 ? .7 - .46 * q / .45 + .05 * Math.sin(q * 30) : .24 + .68 * Math.pow((q - .45) / .55, 1.3)) }[c.chart] || (q => .4 + .3 * q);
    const N = 24, n = Math.ceil(N * cl(p * 1.3)), Y = v => h - 84 - cl(v, 0, 1) * (h - 190), f = k => F(k / N) + .05 * (hsh(k * 3.3) - .5);
    for (let k = 0; k < n; k++) { const o = f(k), cl2 = f(k + 1), up = cl2 >= o, cx = 34 + k * (w - 68) / N + 9; x.strokeStyle = x.fillStyle = up ? '#3dd68c' : '#f0585c'; x.lineWidth = 3; x.beginPath(); x.moveTo(cx, Y(Math.max(o, cl2) + .04 * hsh(k))); x.lineTo(cx, Y(Math.min(o, cl2) - .04 * hsh(k + 5))); x.stroke(); x.fillRect(cx - 8, Math.min(Y(o), Y(cl2)), 16, Math.max(4, Math.abs(Y(o) - Y(cl2)))); }
    if (c.level != null) {   // (a level drawn on the board: "level": 0..1 of the chart's height, "buy": true for the buy mark, "stop": the stop under it)
      const ly = Y(c.level); x.setLineDash([22, 12]); x.strokeStyle = '#ffd23f'; x.lineWidth = 7; x.beginPath(); x.moveTo(18, ly); x.lineTo(w - 18, ly); x.stroke(); x.setLineDash([]);
      // (every tag in the clear band under the line, never on a candle: the critic, 2026-11-19)
      x.textAlign = 'right'; x.fillStyle = '#ffd23f'; fitText(x, 'LEVEL', 160, 26); x.fillText('LEVEL', w - 24, ly + 32);
      if (c.buy && p > .15) { const bx = w * .3; x.fillStyle = '#3dd68c'; x.beginPath(); x.moveTo(bx, ly + 18); x.lineTo(bx - 20, ly + 40); x.lineTo(bx + 20, ly + 40); x.fill(); x.textAlign = 'center'; fitText(x, 'BUY HERE', 240, 32); x.fillText('BUY HERE', bx, ly + 66); }
      if (c.stop != null && p > .55) { const sy = Math.max(Y(c.stop), ly + 50); x.strokeStyle = '#f0585c'; x.lineWidth = 6; x.beginPath(); x.moveTo(w * .55, sy); x.lineTo(w - 18, sy); x.stroke(); x.fillStyle = '#f0585c'; x.textAlign = 'right'; fitText(x, 'STOP', 160, 30); x.fillText('STOP', w - 24, sy + 28); }
    }
    x.textAlign = 'left'; x.fillStyle = '#fff'; const ti = String(c.title || '').toUpperCase(); fitText(x, ti, w - (c.pct ? 250 : 40), big ? 80 : 44); x.fillText(ti, 24, big ? 56 : 46);
    if (c.pct && (p > .72 || !c.chart)) { x.textAlign = 'right';   // (the percentage lands once the chart has drawn what it says: the critic, 2026-11-14)
      x.fillStyle = /^-|^−/.test(c.pct) ? '#f0585c' : '#3dd68c'; fitText(x, String(c.pct), 210, 50); x.fillText(String(c.pct), w - 22, 46); }
    if (c.news && p > .22) { x.fillStyle = '#ffd23f'; x.fillRect(0, h - 66, w, 66); x.fillStyle = '#15171a'; x.textAlign = 'center'; fitText(x, String(c.news), w - 40, 40); x.fillText(String(c.news), w / 2, h - 32); }
  });
}
const COL = { a: new T3.Color(), b: new T3.Color(), c: new T3.Color() }, hex = c => '#' + c.getHexString();
function sky(S, t) {
  const cur = S.sky, k = S.skyT == null ? 1 : io(seg(t, S.skyT, S.skyT + .6)), A = SKY[S.skyT == null ? cur : S.prevSky], B = SKY[cur], kq = Math.round(k * 20) / 20, L = (i) => COL.a.set(A[i]).lerp(COL.b.set(B[i]), kq);
  const top = hex(L(0)), bot = hex(L(1));
  SKYT.paint(top + bot, (x, w, h) => { const g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, top); g.addColorStop(.5, bot); g.addColorStop(1, bot); x.fillStyle = g; x.fillRect(0, 0, w, h); });
  scene.fog.color.set(bot); sun.color.copy(L(2)); sun.intensity = lerp(A[3], B[3], kq); hemi.intensity = lerp(A[4], B[4], kq);
  COL.c.set('#ffffff').lerp(COL.a.set(bot), .35); CLOUDS.forEach((m, i) => { m.position.set((((i * 67 + t * 1.3) % 420) + 420) % 420 - 210, 34 + 14 * hsh(i), -150 + 26 * i); m.visible = !S.P.inside || S.P.k === 'doorway'; });
}
function person(S, E, t, P) {
  const a = actor(E.who), two = E.ts != null && t >= E.ts, st = two ? E.s2 : E.s1, u = two ? t - E.ts : t - Math.max(S.t0, 0), p = where(S, E, t), mv = p.mv, tt = t + a.seed;
  a.g.visible = !st.hide; if (st.hide) return a;
  let ang = 0, hturn = 0; const tg = st.look;
  if (mv) ang = Math.atan2(mv.g.to[0] - mv.g.from[0], mv.g.to[1] - mv.g.from[1]);
  else { if (Array.isArray(tg)) ang = Math.atan2(tg[0] - p[0], tg[1] - p[1]); else if (tg && S.by[nm(tg)]) { const o = where(S, S.by[nm(tg)], t), full = Math.atan2(o[0] - p[0], o[1] - p[1]); ang = cl(full, -.7, .7); hturn = cl(full - ang, -.3, .3);   /* (cheated to the camera: turned further, the face of the one nearer the camera was gone in a two shot: part 2's review) */ } else if (tg === 'screen') { const sx = P.k === 'room' ? -1.3 : 0, sz = P.k === 'room' ? -4.7 : -9.5; ang = Math.atan2(sx - p[0], sz - p[1]); }
    if (p.done) { const from = Math.atan2(p.done.to[0] - p.done.from[0], p.done.to[1] - p.done.from[1]), k = io(cl((t - p.done.ta - p.done.dur) / .3)); let dd = ang - from; dd = Math.atan2(Math.sin(dd), Math.cos(dd)); ang = from + dd * k; } }
  const w = P.w(p[0], p[1]); a.g.position.set(w[0], P.h(p[0], p[1]), w[1]); a.g.rotation.y = P.ry + ang;
  const pose = d => flat((POSES[d] || POSES.idle)(tt, a.seed, u)); let F = pose(st.do);
  if (two && u < .25 && E.s1.do !== st.do) F = mix(pose(E.s1.do), F, io(u / .25));
  const carry = st.hold && !/^(show|point|wave|shake|carry|beg|cheer|cry)$/.test(st.do || '');
  if (carry) { F.arx = -1.05; F.arz = -.42; }
  if (mv) { const A = mv.g.run ? 1 : .62, s = Math.sin(mv.k * mv.g.len * 2.9); F.ll = -A * s; F.lr = A * s; F.alx = A * .8 * s; F.alz = .06; if (!carry) { F.arx = -A * .8 * s; F.arz = -.06; } F.y = (mv.g.run ? .1 : .05) * Math.abs(Math.cos(mv.k * mv.g.len * 2.9)); F.lean = mv.g.run ? .24 : .06; F.hx = 0; F.fall = 0; F.roll = 0; }
  if (E.in === 'car' && S.car) { const c = carAt(S, t); a.g.position.set(c.x - .6 * Math.cos(c.ry), .28, c.z + .6 * Math.sin(c.ry)); a.g.rotation.y = c.ry + PI / 2; F.ll = F.lr = -1.5; F.y = -.36; }
  F.hy += hturn; setPose(a, F); face(a, st.face || MOOD[st.do] || 'smile', ((t * .9 + a.seed) % 3.1) < .12);
  // the number on the chest: it counts when it changes, green up and red down, and stays red at zero or below
  const c1 = E.s1.chest, c2 = E.s2.chest, end1 = Array.isArray(c1) ? c1[1] : c1; let txt, col = '#15171a', pop = 0;
  const count = (from, to, k) => { if (typeof from !== 'number' || typeof to !== 'number') { const v = k < .5 ? from : to; return [typeof v === 'number' ? fmt(v) : v, 0]; } pop = k > 0 && k < 1 ? Math.sin(PI * k) : 0; col = k < 1 ? (to > from ? '#1f9d55' : '#e2372f') : to <= 0 ? '#e2372f' : '#15171a'; return fmt(from + (to - from) * out(k)); };
  if (two && c2 !== undefined && c2 !== end1) { const r = count(end1 == null ? 0 : end1, Array.isArray(c2) ? c2[1] : c2, seg(t, E.ts, E.ts + .7)); txt = Array.isArray(r) ? r[0] : r; }
  else if (Array.isArray(c1)) { const t0 = Math.max(S.t0, 0) + .12, r = count(c1[0], c1[1], seg(t, t0, t0 + Math.min(1.1, (S.t1 - t0) * .6))); txt = Array.isArray(r) ? r[0] : r; }
  else { txt = typeof end1 === 'number' ? fmt(end1) : end1; if (typeof end1 === 'number' && end1 <= 0) col = '#e2372f'; }
  chest(a, txt, col, pop); emote(a, st.emote, u / .22); hold(a, st.hold);
  return a;
}
function draw(t) {
  const S = prep(SH.reduce((b, q) => (t >= q.t0 ? q : b), SH[0])), P = S.P, q = S.s, u = cl((t - Math.max(S.t0, 0)) / (S.t1 - Math.max(S.t0, 0))), seen = {};
  sky(S, t);
  for (const E of S.A) seen[person(S, E, t, P).k] = 1;
  for (const m of S.amb) { const p = m.pos(t), a = actor(m.who); seen[a.k] = 1; a.g.visible = true; a.g.position.set(p[0], Math.abs(p[1]) < 6.2 ? .2 : .06, p[1]); a.g.rotation.y = m.v > 0 ? PI / 2 : -PI / 2; const ph = (t * Math.abs(m.v) + a.seed) * 2.9, s = Math.sin(ph); setPose(a, flat({ ll: -.62 * s, lr: .62 * s, al: [.5 * s, .06], ar: [-.5 * s, -.06], y: .05 * Math.abs(Math.cos(ph)), lean: .06 })); face(a, 'smile', false); chest(a, fmt(m.chest), '#15171a', 0); emote(a, null, 0); hold(a, null); }
  for (const k in ACT) if (!seen[k]) ACT[k].g.visible = false;
  TRAFFIC.forEach(m => { m.visible = false; }); for (const c of S.cars || []) { const p = c.pos(t); c.m.visible = true; c.m.position.set(p[0], .06, p[1]); c.m.rotation.y = c.v > 0 ? 0 : PI; }
  for (const k in HERO) HERO[k].visible = false;
  if (S.car) { const m = HERO[S.car.c] || (HERO[S.car.c] = car(CARCOL[S.car.c], true)), c = carAt(S, t); m.visible = true; m.position.set(c.x, .06, c.z); m.rotation.y = c.ry; }
  PLN.visible = !!S.plane; if (S.plane) { const m = planeAt(S, t); PLN.position.set(m.x, m.y, m.z); PLN.rotation.set(0, P.ry, m.pitch); PLN.scale.setScalar(m.sc); PLN.stairs.visible = m.stairs; }
  { const d = q.door || P.door || 'closed'; DOOR.rotation.y = 1.85 * (d === 'open' ? 1 : d === 'burst' ? back(seg(t, S.doorT, S.doorT + .28)) : 0); }
  if (q.screen) { if (P.screen) screenPaint(P.screen, q.screen, u); screenPaint(HELD, q.screen, u, 1); } else if (P.screen) screenPaint(P.screen, { text: P.k === 'room' ? 'MEME STREET' : 'TOWN NEWS' }, 1);
  // confetti and coins, a flash, the old-photo look
  let fl = 0, flc = '255,255,255'; CONF.count = 0;
  for (const f of S.fx) {
    const k = t - f.t; if (k < 0 || still) continue;   // (the cover: no coins across the number, no flash)
    if (f.do === 'flash' || f.do === 'redflash') { const v = .85 * (1 - cl(k / .4)); if (v > fl) { fl = v; flc = f.do === 'flash' ? '255,255,255' : '230,40,30'; } }
    if ((f.do === 'confetti' || f.do === 'coins') && k < 3) {
      const c = camAt(S, t).g, M = new T3.Matrix4(), Q = new T3.Quaternion(), E3 = new T3.Euler(), V3 = new T3.Vector3(), SC3 = new T3.Vector3(), coin = f.do === 'coins';
      for (let i = 0; i < 90; i++) { const kk = k - hsh(i) * .25; if (kk < 0) { M.makeScale(0, 0, 0); CONF.setMatrixAt(i, M); continue; }
        const vx = (hsh(i + 9) - .5) * 5.5, vz = (hsh(i + 19) - .5) * 3, vy = coin ? 0 : 3.5 + 4.5 * hsh(i + 29), y0 = coin ? 5.2 + 2 * hsh(i + 39) : 1.2;
        V3.set(c.x + vx * kk * (coin ? .35 : 1), Math.max(.08, c.y - 1 + y0 + vy * kk - 4.9 * kk * kk * (coin ? 1.2 : 1)), c.z + vz * kk * (coin ? .35 : 1)); E3.set(kk * 7 + i, kk * 5 + i * 2, 0); Q.setFromEuler(E3); const s = coin ? .2 : .13; SC3.set(s, coin ? s : s * .5, coin ? .05 : s);
        M.compose(V3, Q, SC3); CONF.setMatrixAt(i, M); CONF.setColorAt(i, COL.c.set(coin ? '#ffd23f' : ['#e2504a', '#4f8fe6', '#ffd23f', '#3dd68c', '#e86aa6'][i % 5])); }
      CONF.count = 90; CONF.instanceMatrix.needsUpdate = true; if (CONF.instanceColor) CONF.instanceColor.needsUpdate = true;
    }
  }
  const photo = q.look === 'photo'; cv.style.filter = photo ? 'sepia(.85) saturate(.85) contrast(1.05)' : ''; ov.style.border = photo ? '44px solid #f6f1e5' : ''; ov.style.borderBottomWidth = photo ? '110px' : ''; ov.style.background = fl > 0 ? `rgba(${flc},${fl.toFixed(3)})` : '';
  const c = camAt(S, t); cam.fov = c.f; cam.position.copy(c.p); cam.lookAt(c.g); cam.updateProjectionMatrix();
  if (S.plane && S.plane.mode === 'away') {   // (the plane as a dot in the sky: always in the upper part of this shot's frame, flying away)
    const d = new T3.Vector3().subVectors(c.g, c.p).normalize(), e = Math.asin(d.y) + .66 * c.f / 2 * PI / 180, hl = Math.hypot(d.x, d.z) || 1, k = cl((t - S.plane.t) / Math.max(.6, S.t1 - S.plane.t)), sd = 170 * Math.tan(.64 * Math.atan(Math.tan(c.f / 2 * PI / 180) * .5625)) * (1 + .1 * k);   // (to the right of whoever fills the middle of the frame)
    PLN.position.set(c.p.x + (d.x / hl * Math.cos(e)) * 170 - d.z / hl * sd, c.p.y + Math.sin(e) * 170 + 5 * k, c.p.z + (d.z / hl * Math.cos(e)) * 170 + d.x / hl * sd); PLN.rotation.set(0, Math.atan2(-d.z, d.x) + .5, .2); PLN.scale.setScalar(.5 - .12 * k); PLN.stairs.visible = false;
  }
  SKYM.position.copy(c.p); sun.target.position.copy(c.g); sun.position.set(c.g.x + 16, c.g.y + 30, c.g.z + 13); sun.target.updateMatrixWorld();
  rn.render(scene, cam); return '';
}
// the list above is what world.py checks a script against: it must name exactly what this file can draw
for (const [k, o] of [['places', PL], ['cams', CAMS], ['poses', POSES], ['items', ITEMS], ['skies', SKY], ['cars', CARCOL]]) if (VOC[k].slice().sort().join() !== Object.keys(o).sort().join()) throw new Error('world3d.js: VOC.' + k + ' does not match what the file draws');
API.world = draw;
window.W3D = { draw, VOC, shots: SH,
  cover: async () => {   // the thumbnail (the owner, 2026-11-14: "on the thumbnail put 'PART 1'"): the opening shot once its number has landed, PART N and the story's title over the legs
    still = true; await render(Math.max(0, SH[0].t0) + .93 * (SH[0].t1 - Math.max(0, SH[0].t0)));   // (late in the shot: its number has finished counting)
    for (const id of ['caps', 'opts', 'hook0']) document.getElementById(id).innerHTML = ''; document.querySelector('.prog').style.display = 'none';
    const d = document.createElement('div'); d.style.cssText = 'position:absolute;left:40px;right:40px;top:1215px;text-align:center;z-index:5;font:900 164px/1 "Arial Black","DejaVu Sans",sans-serif;color:#ffd23f;-webkit-text-stroke:22px #000;paint-order:stroke fill;text-shadow:0 10px 0 #000';
    d.innerHTML = (R.part ? 'PART ' + R.part : '') + `<div style="margin-top:22px;font-size:66px;line-height:1.05;color:#fff;-webkit-text-stroke:14px #000;text-shadow:0 6px 0 #000;text-transform:uppercase">${esc(R.series || R.title || '')}</div>`; document.body.appendChild(d);
    return new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  } };
})();
