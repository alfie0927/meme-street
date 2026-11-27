/* Meme Street's story reel: the THINGS in a shot, modelled to look like the real object.
   The owner, 2026-11-26: "i want the objects in the reels to look more realistic, like the car could be more REALISTIC, look
   more like a car (have more panels so it can BE a car, rather than just a boring, boxy mess). same with everything else."
   So a thing is no longer a few flat-shaded boxes. It is built from its real parts (a car: a body pressed from its side
   profile with wheel arches, a cabin with glass, alloy wheels with tyres, lamps, bumpers, mirrors, door seams, handles), its
   edges are rounded, its panels are smooth, and its materials reflect a studio sky (paint under a clear coat, glass, chrome,
   rubber). Everything is still made here from nothing: no model file, nothing copied from a real product's design.
   window.Models3D(h) -> {product(kind, col, text), cash(), coin(r), phoneShell(...), tv(w, h), qmark(col), trophy(), bulb(),
   rocket(), gavel()}. A product is about 1 unit wide (a car or van about 2 long), its base at y 0, facing +z;
   userData.late = the parts the factory fits last. */
window.Models3D = function (h) {
'use strict';
const T3 = h.T3, S = h.S, canvasTex = h.canvasTex, PI = Math.PI;
const hsh = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

// ---------------------------------------------------------------- what the shiny parts reflect: a pale sky over a warm floor, with studio lights
const ENV = (() => { const sc = new T3.Scene(), pm = new T3.PMREMGenerator(h.rn);
  const sky = canvasTex(16, 256, (x, w, hh) => { const g = x.createLinearGradient(0, 0, 0, hh); g.addColorStop(0, '#8fbdec'); g.addColorStop(.46, '#f4f7fb'); g.addColorStop(.54, '#b8b0a2'); g.addColorStop(1, '#4c4740'); x.fillStyle = g; x.fillRect(0, 0, w, hh); });
  sc.add(new T3.Mesh(new T3.SphereGeometry(50, 24, 16), new T3.MeshBasicMaterial({map: sky, side: T3.BackSide})));
  for (const [x, y, z, w, hh, k] of [[0, 34, 8, 34, 16, 7], [-32, 14, 18, 10, 26, 4], [34, 16, -4, 8, 22, 3.5], [4, 9, 42, 44, 7, 2.5]]) {
    const m = new T3.Mesh(new T3.PlaneGeometry(w, hh), new T3.MeshBasicMaterial({color: new T3.Color(k, k, k), side: T3.DoubleSide})); m.position.set(x, y, z); m.lookAt(0, 0, 0); sc.add(m); }
  const t = pm.fromScene(sc, .03).texture; pm.dispose(); return t; })();

// ---------------------------------------------------------------- materials
const MC = {};
const PM = (col, o = {}) => { const k = col + JSON.stringify(o); return MC[k] || (MC[k] = new T3.MeshStandardMaterial(Object.assign({color: col, roughness: .5, metalness: 0, envMap: ENV, envMapIntensity: .5}, o))); };
const paint = col => MC['paint' + col] || (MC['paint' + col] = new T3.MeshPhysicalMaterial({color: col, roughness: .36, metalness: .55, clearcoat: 1, clearcoatRoughness: .07, envMap: ENV, envMapIntensity: 1}));
const GLASS = PM('#0e1722', {roughness: .06, metalness: .45, envMapIntensity: 1.3}), CHROME = PM('#e2e6ee', {roughness: .16, metalness: 1, envMapIntensity: 1.25});
const STEEL = PM('#9aa1ae', {roughness: .34, metalness: .92, envMapIntensity: 1}), GOLD = PM('#f2b632', {roughness: .24, metalness: 1, envMapIntensity: 1.2});
const RUBBER = PM('#16171b', {roughness: .92, envMapIntensity: .2}), BLACK = PM('#0d0e11', {roughness: .9, envMapIntensity: .1}), DARK = PM('#24272e', {roughness: .6, envMapIntensity: .35});
const GLOSS = PM('#121318', {roughness: .12, envMapIntensity: 1.1}), LAMP = PM('#f6f8ff', {emissive: '#fff4d2', emissiveIntensity: .9, roughness: .15}), TAIL = PM('#c81e2c', {emissive: '#ff1d2d', emissiveIntensity: .8, roughness: .2});
const WHITE = PM('#f4f4f1', {roughness: .5});

// ---------------------------------------------------------------- shapes
const mk = (geo, mat, shadow = true) => { const m = new T3.Mesh(geo, mat); m.castShadow = shadow; m.receiveShadow = true; return m; };
const at = (m, x, y, z) => { m.position.set(x, y, z); return m; };
const grp = (...a) => { const g = new T3.Group(); a.forEach(m => g.add(m)); return g; };
const cyl = (r1, r2, len, mat, seg = 24, axis = 'y') => { const m = mk(new T3.CylinderGeometry(r1, r2, len, seg), mat); if (axis === 'z') m.rotation.x = PI / 2; else if (axis === 'x') m.rotation.z = PI / 2; return m; };
const ball = (r, mat, sx = 1, sy = 1, sz = 1) => { const m = mk(new T3.SphereGeometry(r, 24, 16), mat); m.scale.set(sx, sy, sz); return m; };
const lathe = (pts, mat, seg = 36) => mk(new T3.LatheGeometry(pts.map(([x, y]) => new T3.Vector2(x, y)), seg), mat);
const lay = m => { m.rotation.x = -PI / 2; return m; };          // something built standing (x, y) laid flat on the floor
const box = (w, hh, d, mat) => mk(new T3.BoxGeometry(w, hh, d), mat);
function smooth(geo, deg = 40) {       // rounds a faceted mesh: a corner's normal is the mean of the faces that meet there within deg of each other (a sharp edge stays sharp)
  const g = geo.index ? geo.toNonIndexed() : geo, p = g.attributes.position, n = p.count, cosT = Math.cos(deg * PI / 180), fn = new Float32Array(n * 3), out = new Float32Array(n * 3);
  const a = new T3.Vector3(), b = new T3.Vector3(), c = new T3.Vector3(), map = new Map();
  for (let i = 0; i < n; i += 3) { a.fromBufferAttribute(p, i); b.fromBufferAttribute(p, i + 1).sub(a); c.fromBufferAttribute(p, i + 2).sub(a); b.cross(c);
    for (let k = 0; k < 3; k++) { const j = i + k; fn[j * 3] = b.x; fn[j * 3 + 1] = b.y; fn[j * 3 + 2] = b.z; const key = Math.round(p.getX(j) * 4e3) + '_' + Math.round(p.getY(j) * 4e3) + '_' + Math.round(p.getZ(j) * 4e3); let L = map.get(key); if (!L) map.set(key, L = []); L.push(j); } }
  for (const L of map.values()) for (const i of L) { const x = fn[i * 3], y = fn[i * 3 + 1], z = fn[i * 3 + 2], l = Math.hypot(x, y, z) || 1; let sx = 0, sy = 0, sz = 0;
    for (const j of L) { const u = fn[j * 3], v = fn[j * 3 + 1], w = fn[j * 3 + 2], m = Math.hypot(u, v, w) || 1; if ((x * u + y * v + z * w) / (l * m) >= cosT) { sx += u; sy += v; sz += w; } }
    const s = Math.hypot(sx, sy, sz) || 1; out[i * 3] = sx / s; out[i * 3 + 1] = sy / s; out[i * 3 + 2] = sz / s; }
  g.setAttribute('normal', new T3.BufferAttribute(out, 3)); return g; }
function rrect(w, hh, r) { const s = new T3.Shape(), x = w / 2, y = hh / 2; r = Math.max(.0005, Math.min(r, x - .0005, y - .0005));
  s.moveTo(-x + r, -y); s.lineTo(x - r, -y); s.absarc(x - r, -y + r, r, -PI / 2, 0, false); s.lineTo(x, y - r); s.absarc(x - r, y - r, r, 0, PI / 2, false);
  s.lineTo(-x + r, y); s.absarc(-x + r, y - r, r, PI / 2, PI, false); s.lineTo(-x, -y + r); s.absarc(-x + r, -y + r, r, PI, PI * 1.5, false); return s; }
function ext(shape, depth, mat, bevel = 0, o = {}) {          // a profile drawn in x, y pushed through z (centred); bevel rounds its edges and grows the profile by as much
  const d = Math.max(.0005, depth - 2 * bevel), geo = new T3.ExtrudeGeometry(shape, Object.assign({depth: d, bevelEnabled: bevel > 0, bevelSize: bevel, bevelThickness: bevel, bevelSegments: 3, curveSegments: 16}, o));
  geo.translate(0, 0, -d / 2); return mk(smooth(geo), mat); }
function rbox(w, hh, d, r, mat, rc) {        // a box w x hh x d with its edges rounded by r; rc: larger round corners as seen from the front
  r = Math.max(.0005, Math.min(r, w / 2 - .001, hh / 2 - .001, d / 2 - .0005)); return ext(rrect(w - 2 * r, hh - 2 * r, Math.max(.0005, (rc == null ? r : rc) - r)), d, mat, r); }
function slab(x0, y0, x1, y1, th, width, mat, off = 0) {      // a flat panel lying on a line of a side profile (its outside is to the left of the line's direction), th thick, width across
  const dx = x1 - x0, dy = y1 - y0, l = Math.hypot(dx, dy), nx = -dy / l, ny = dx / l, s = new T3.Shape(), a = off, b = off + th;
  s.moveTo(x0 + nx * a, y0 + ny * a); s.lineTo(x1 + nx * a, y1 + ny * a); s.lineTo(x1 + nx * b, y1 + ny * b); s.lineTo(x0 + nx * b, y0 + ny * b); s.closePath(); return ext(s, width, mat); }
function decal(w, hh, px, draw, o) {         // something printed on a surface: it is lit like the surface (a screen that shines is h.label)
  const t = canvasTex(Math.round(px * w / hh), px, (x, cw, ch) => { const old = S.ctx(x); draw(x, cw, ch); S.ctx(old); });
  const m = new T3.Mesh(new T3.PlaneGeometry(w, hh), new T3.MeshStandardMaterial(Object.assign({map: t, roughness: .6, envMap: ENV, envMapIntensity: .3}, o))); m.receiveShadow = true; return m; }
const stencil = (text, w, hh, fg, o) => decal(w, hh, 160, (x, cw, ch) => { x.clearRect(0, 0, cw, ch); S.txt(String(text).toUpperCase(), cw / 2, ch / 2 + 4, ch * .66, fg, cw * .96); }, Object.assign({transparent: true, alphaTest: .4}, o));      // letters painted straight onto a panel
const print = (text, w, hh, fg, bg, o) => decal(w, hh, 160, (x, cw, ch) => { x.fillStyle = bg; x.fillRect(0, 0, cw, ch); S.txt(String(text).toUpperCase(), cw / 2, ch / 2 + 4, ch * .62, fg, cw * .9); }, o);

// ---------------------------------------------------------------- vehicles
function wheel(r, w, rim = '#d3d8e0') {      // a tyre on an alloy wheel, its axle along z
  const g = new T3.Group(), t = w / 2, tyre = lathe([[r * .6, -t], [r * .9, -t], [r * .985, -t * .7], [r, -t * .3], [r, t * .3], [r * .985, t * .7], [r * .9, t], [r * .6, t]], RUBBER, 32); tyre.rotation.x = PI / 2; g.add(tyre);
  g.add(cyl(r * .62, r * .62, w * .72, BLACK, 24, 'z')); const RM = PM(rim, {metalness: .95, roughness: .22, envMapIntensity: 1.1});
  for (const s of [-1, 1]) { g.add(at(mk(new T3.TorusGeometry(r * .61, r * .05, 8, 32), RM), 0, 0, s * t * .9));
    for (let k = 0; k < 5; k++) { const a = k * PI * .4 + .3, sp = box(r * .56, r * .14, w * .07, RM); sp.position.set(Math.cos(a) * r * .31, Math.sin(a) * r * .31, s * t * .84); sp.rotation.z = a; g.add(sp); }
    g.add(at(cyl(r * .15, r * .18, w * .1, RM, 16, 'z'), 0, 0, s * t * .88)); g.add(at(cyl(r * .5, r * .5, w * .03, STEEL, 24, 'z'), 0, 0, s * t * .6)); }      // hub, brake disc
  return g; }
const seam = (x, y0, y1, z) => at(box(.006, y1 - y0, .004, BLACK), x, (y0 + y1) / 2, z);
function car(col, text) {
  const g = new T3.Group(), P = paint(col), W = .78, b = .035, ax = .57, ar = .185, wr = .15, s = new T3.Shape();
  // the body, pressed from its side profile: rear bumper, boot, shoulder, bonnet, nose, and the two wheel arches cut out of the sill
  s.moveTo(-.9, .16); s.lineTo(-.915, .3); s.quadraticCurveTo(-.92, .405, -.83, .41); s.lineTo(-.55, .425); s.lineTo(.36, .415); s.quadraticCurveTo(.7, .4, .86, .33); s.quadraticCurveTo(.925, .3, .92, .22); s.lineTo(.9, .16);
  s.lineTo(ax + ar, .16); s.absarc(ax, .16, ar, 0, PI, false); s.lineTo(-ax + ar, .16); s.absarc(-ax, .16, ar, 0, PI, false); s.closePath(); g.add(ext(s, W, P, b));
  for (const x of [ax, -ax]) g.add(at(box(2 * ar - .01, ar + .02, W - .09, BLACK), x, .16 + ar / 2 - .015, 0));        // the dark wheel wells
  // the cabin: roof and pillars in the body's paint, glass let into it
  const cab = new T3.Group(), c = new T3.Shape(), CW = .66; c.moveTo(-.58, .43); c.lineTo(-.31, .615); c.quadraticCurveTo(-.25, .64, -.13, .645); c.lineTo(.02, .645); c.quadraticCurveTo(.11, .64, .15, .615); c.lineTo(.42, .43); c.closePath();
  cab.add(ext(c, CW, P, .03)); cab.add(slab(.17, .601, .405, .44, .012, CW - .1, GLASS, .024)); cab.add(slab(-.565, .44, -.325, .604, .012, CW - .1, GLASS, .024));      // windscreen, rear window
  const sg = new T3.Shape(); sg.moveTo(-.485, .47); sg.lineTo(-.29, .6); sg.lineTo(-.13, .62); sg.lineTo(.02, .62); sg.lineTo(.135, .6); sg.lineTo(.33, .47); sg.closePath();
  for (const z of [-1, 1]) { cab.add(at(ext(sg, .012, GLASS), 0, 0, z * (CW / 2 + .001))); cab.add(at(box(.034, .15, .016, GLOSS), -.085, .545, z * (CW / 2 + .002)));      // side glass, the pillar between the doors
    cab.add(at(rbox(.075, .05, .06, .02, P), .385, .485, z * (CW / 2 + .055))); cab.add(at(box(.03, .012, .05, DARK), .385, .47, z * (CW / 2 + .02))); }               // door mirrors
  cab.add(at(mk(new T3.ConeGeometry(.018, .05, 10), GLOSS), -.27, .69, 0)); g.add(cab);
  for (const z of [-1, 1]) {
    g.add(at(rbox(.1, .05, .17, .02, LAMP), .875, .33, z * .29)); g.add(at(rbox(.05, .055, .2, .018, TAIL), -.935, .355, z * .28));                                  // headlamps, tail lamps
    for (const [x, y0, y1] of [[.33, .2, .41], [-.06, .17, .41], [-.42, .26, .41]]) g.add(seam(x, y0, y1, z * (W / 2 + .001)));                                         // door seams
    for (const x of [.2, -.19]) g.add(at(rbox(.075, .016, .014, .006, CHROME), x, .375, z * (W / 2 + .004)));                                                          // handles
    g.add(at(rbox(.62, .035, .02, .008, DARK), 0, .165, z * (W / 2 + .002))); }                                                                                        // sills
  g.add(at(rbox(.04, .075, .46, .015, GLOSS), .938, .215, 0)); g.add(at(rbox(.03, .032, .32, .01, GLOSS), .925, .305, 0)); g.add(at(rbox(.012, .008, .28, .003, CHROME), .942, .305, 0));      // intake, grille, its bright bar
  g.add(at(rbox(.03, .05, .62, .012, DARK), -.94, .2, 0));
  const plate = print(text || 'MEME ST', .2, .055, '#15162b', '#f4f4f1'); plate.rotation.y = -PI / 2; g.add(at(plate, -.953, .285, 0));
  const wheels = [[ax, 1], [ax, -1], [-ax, 1], [-ax, -1]].map(([x, z]) => at(wheel(wr, .11), x, wr, z * (W / 2 - .045))); wheels.forEach(w => g.add(w));
  g.userData.late = [cab, ...wheels]; return g; }
function van(col, text) {              // a delivery van: a tall load body, a short sloping nose, a sliding side door
  const g = new T3.Group(), P = paint(col), W = .84, b = .04, af = .62, ab = -.56, ar = .2, wr = .16, s = new T3.Shape(), Z = W / 2;
  s.moveTo(-.93, .17); s.lineTo(-.95, .3); s.lineTo(-.95, .93); s.quadraticCurveTo(-.95, 1, -.87, 1); s.lineTo(.3, 1); s.quadraticCurveTo(.41, .995, .46, .93); s.lineTo(.7, .6); s.quadraticCurveTo(.73, .56, .8, .545); s.lineTo(.9, .5); s.quadraticCurveTo(.955, .46, .95, .36); s.lineTo(.93, .17);
  s.lineTo(af + ar, .17); s.absarc(af, .17, ar, 0, PI, false); s.lineTo(ab + ar, .17); s.absarc(ab, .17, ar, 0, PI, false); s.closePath(); g.add(ext(s, W, P, b));
  for (const x of [af, ab]) g.add(at(box(2 * ar - .01, ar + .02, W - .09, BLACK), x, .17 + ar / 2 - .015, 0));
  const glass = grp(slab(.478, .905, .69, .615, .012, W - .17, GLASS, b - .006)), dg = new T3.Shape(); dg.moveTo(.21, .88); dg.lineTo(.425, .88); dg.lineTo(.63, .61); dg.lineTo(.21, .61); dg.closePath();
  const mirrors = new T3.Group();
  for (const z of [-1, 1]) { glass.add(at(ext(dg, .012, GLASS), 0, 0, z * (Z + .001)));
    mirrors.add(at(rbox(.045, .13, .07, .018, GLOSS), .56, .75, z * (Z + .07))); mirrors.add(at(box(.03, .014, .07, DARK), .56, .7, z * (Z + .03)));
    g.add(seam(.16, .22, .93, z * (Z + .001))); g.add(seam(-.38, .34, .93, z * (Z + .001))); g.add(at(box(1.06, .012, .006, GLOSS), -.37, .645, z * (Z + .002)));    // the cab door, the sliding door and its rail
    g.add(at(box(.54, .005, .004, BLACK), -.11, .93, z * (Z + .001))); g.add(at(box(.5, .005, .004, BLACK), .41, .25, z * (Z + .001)));
    for (const x of [.1, -.32]) g.add(at(rbox(.075, .018, .014, .006, CHROME), x, .56, z * (Z + .004)));
    g.add(at(box(1.72, .05, .004, WHITE), -.06, .47, z * (Z + .0015)));                                                                                             // the livery: a white band, the name on the load body
    if (text) { const p = stencil(text, .5, .15, '#ffffff', {roughness: .4}); if (z < 0) p.rotation.y = PI; g.add(at(p, -.66, .8, z * (Z + .002))); }
    g.add(at(cyl(.03, .03, .004, PM(S.shade(col, -.3), {roughness: .4}), 20, 'z'), .82, .47, z * (Z + .001))); g.add(at(ball(.007, PM('#35ff7a', {emissive: '#35ff7a', emissiveIntensity: 2})), .82, .47, z * (Z + .004)));      // the charging flap
    g.add(at(rbox(.07, .075, .16, .02, LAMP), .95, .43, z * .315)); g.add(at(rbox(.03, .28, .05, .012, TAIL), -.985, .64, z * .365)); }
  g.add(at(rbox(.07, .11, W - .03, .028, DARK), .952, .225, 0)); g.add(at(rbox(.02, .03, .42, .01, GLOSS), .988, .33, 0)); g.add(at(rbox(.07, .06, W - .02, .02, DARK), -.962, .2, 0));      // bumpers, the closed grille's slot
  g.add(at(box(.004, .72, .006, BLACK), -.991, .6, 0)); g.add(at(rbox(.014, .07, .02, .005, CHROME), -.994, .56, .04));                                                 // the rear doors
  const plate = print('MEME ST', .2, .055, '#15162b', '#f4f4f1'); plate.rotation.y = -PI / 2; g.add(at(plate, -.9925, .36, 0));
  const wheels = [[af, 1], [af, -1], [ab, 1], [ab, -1]].map(([x, z]) => at(wheel(wr, .12, '#b4bac6'), x, wr, z * (Z - .05))); wheels.forEach(w => g.add(w)); g.add(glass, mirrors);
  g.userData.late = [glass, mirrors, ...wheels]; return g; }

// ---------------------------------------------------------------- things a company makes
function camera(col, text) {           // an action camera on its mount
  const g = new T3.Group(), y = .5, late = [], B = PM('#2b2e35', {roughness: .55, envMapIntensity: .35});
  for (const x of [-.09, 0, .09]) g.add(at(rbox(.05, .16, .17, .015, PM('#1a1c21', {roughness: .5})), x, .08, 0));
  g.add(at(rbox(1, .72, .46, .07, B), 0, y, 0)); g.add(at(rbox(.94, .66, .03, .01, PM('#17191d', {roughness: .25, envMapIntensity: .9}), .05), 0, y, .222));
  const L = new T3.Group(); L.add(cyl(.3, .3, .1, PM('#3d414a', {metalness: .85, roughness: .3, envMapIntensity: 1}), 36, 'z')); L.add(at(cyl(.26, .28, .1, PM('#15161a', {roughness: .4}), 36, 'z'), 0, 0, .07));
  L.add(at(mk(new T3.TorusGeometry(.265, .018, 8, 36), CHROME), 0, 0, .12)); const gl = mk(new T3.SphereGeometry(.34, 32, 12, 0, 2 * PI, 0, .72), PM('#173450', {metalness: .9, roughness: .04, envMapIntensity: 1.9})); gl.rotation.x = PI / 2; gl.position.z = -.135; L.add(gl);
  at(L, .2, y + .02, .25); const scr = grp(at(rbox(.34, .3, .012, .004, GLOSS, .03), 0, 0, 0), at(new T3.Mesh(new T3.PlaneGeometry(.28, .22), h.glowM(col, 1.1)), 0, .01, .008)); at(scr, -.27, y + .1, .24);
  g.add(at(cyl(.075, .075, .03, PM('#d8333f', {roughness: .3}), 24), .3, y + .375, 0)); const ring = mk(new T3.TorusGeometry(.085, .012, 8, 24), CHROME); ring.rotation.x = PI / 2; g.add(at(ring, .3, y + .362, 0));
  g.add(at(rbox(.02, .2, .16, .008, DARK), -.505, y, 0)); g.add(at(ball(.014, PM('#ff3b3b', {emissive: '#ff3b3b', emissiveIntensity: 2})), .42, y + .27, .238));
  late.push(L, scr); if (text) late.push(at(print(text, .38, .1, '#ffffff', '#17191d', {roughness: .3}), -.25, y - .22, .2385)); late.forEach(m => g.add(m)); g.userData.late = late; return g; }
function chip(col, text) {             // a processor: a green board, gold contacts, a metal lid with its name on
  const g = new T3.Group(), c = new T3.Group(), MET = PM('#c9ced7', {metalness: .95, roughness: .3, envMapIntensity: 1.1});
  c.add(at(lay(rbox(1.1, 1.1, .05, .012, PM('#1e6d47', {roughness: .45}), .03)), 0, .025, 0)); c.add(at(lay(rbox(.92, .92, .03, .01, MET, .06)), 0, .065, 0));
  const lid = at(lay(rbox(.8, .8, .1, .03, MET, .09)), 0, .11, 0), name = lay(print(text || '', .6, .2, '#3a3f49', '#c9ced7', {metalness: .9, roughness: .34, envMapIntensity: 1})); at(name, 0, .161, 0);
  for (let i = 0; i < 11; i++) for (const sd of [-1, 1]) { const u = -.45 + i * .09; c.add(at(box(.05, .012, .028, GOLD), u, .052, sd * .508)); c.add(at(box(.028, .012, .05, GOLD), sd * .508, .052, u)); }
  for (const [x, z] of [[-.5, .35], [.5, -.3], [.5, .12]]) c.add(at(box(.035, .03, .06, PM('#c8a877', {roughness: .5})), x, .06, z));
  c.add(lid); if (text) c.add(name); c.rotation.x = 1.1; c.position.y = .62; g.add(c); g.userData.late = text ? [lid, name] : [lid]; return g; }
function phoneShell(w, hh, d, sw, sh) {      // a phone without its picture: a metal frame, a glass front, a rim around the screen (sw x sh, drawn by the caller at z = d * .536)
  const g = new T3.Group(), rc = w * .13, F = PM('#3a3e48', {metalness: .9, roughness: .26, envMapIntensity: 1});
  g.add(rbox(w, hh, d, d * .4, F, rc)); g.add(at(rbox(w - d * .16, hh - d * .16, d * .1, d * .03, GLOSS, rc - d * .08), 0, 0, d * .455));
  const rim = rrect(w - d * .16, hh - d * .16, rc - d * .08); rim.holes.push(rrect(sw - d * .1, sh - d * .1, rc * .62)); g.add(at(ext(rim, d * .03, GLOSS), 0, 0, d * .556));
  g.add(at(cyl(w * .026, w * .026, d * .02, BLACK, 16, 'z'), 0, sh / 2 - w * .075, d * .58));
  g.add(at(rbox(d * .14, hh * .1, d * .3, d * .05, F), w / 2 + d * .03, hh * .16, 0)); for (const y of [.2, .08]) g.add(at(rbox(d * .14, hh * .07, d * .3, d * .05, F), -w / 2 - d * .03, hh * y, 0)); return g; }
function phone(col, text) { const g = new T3.Group(), sh = phoneShell(.55, 1.1, .07, .47, 1.0), s = at(h.label(text || '', .47, 1.0, '#fff', col), 0, .55, .07 * .536 + .0002); g.add(at(sh, 0, .55, 0), s); g.userData.late = [s]; return g; }
function keyboard(w, d, bg, key) {      // rows of keys printed on a deck, lying flat
  return lay(decal(w, d, 256, (x, cw, ch) => { x.fillStyle = bg; x.fillRect(0, 0, cw, ch); x.fillStyle = key; const kw = (cw - 12) / 14, kh = (ch - 12) / 5;
    for (let r = 0; r < 5; r++) for (let k = 0; k < 14; k++) { if (r === 4 && k > 3 && k < 10) continue; x.fillRect(8 + k * kw, 8 + r * kh, kw - 5, kh - 5); } x.fillRect(8 + 4 * kw, 8 + 4 * kh, 6 * kw - 5, kh - 5); }, {roughness: .5})); }
function laptop(col, text) {
  const g = new T3.Group(), AL = PM('#bcc1cb', {metalness: .9, roughness: .32, envMapIntensity: 1}), lid = new T3.Group();
  g.add(at(lay(rbox(1.1, .76, .045, .014, AL, .05)), 0, .0225, 0));
  const keys = keyboard(.98, .36, '#1b1d23', '#31343d'); g.add(at(keys, 0, .0462, -.1));
  g.add(at(lay(new T3.Mesh(new T3.PlaneGeometry(.36, .2), PM('#aab0bb', {metalness: .85, roughness: .22, envMapIntensity: 1}))), 0, .0462, .23)); g.add(at(cyl(.022, .022, .9, DARK, 12, 'x'), 0, .04, -.375));
  lid.add(at(rbox(1.1, .74, .028, .012, AL, .05), 0, .37, 0)); lid.add(at(rbox(1.06, .7, .006, .002, GLOSS, .04), 0, .37, .015)); lid.add(at(h.label(text || '', .98, .6, '#fff', col), 0, .365, .0185)); lid.add(at(cyl(.008, .008, .003, BLACK, 12, 'z'), 0, .7, .019));
  lid.position.set(0, .05, -.375); lid.rotation.x = -.28; g.add(lid); g.userData.late = [lid]; return g; }
function bottle(col, text) {
  const g = new T3.Group(), body = lathe([[0, 0], [.2, 0], [.25, .02], [.27, .08], [.27, .6], [.255, .7], [.2, .82], [.12, .97], [.088, 1.04], [.088, 1.16], [0, 1.16]], PM(col, {roughness: .1, metalness: .15, envMapIntensity: 1.3})); g.add(body);
  const wrap = canvasTex(1024, 200, (x, w, hh) => { const old = S.ctx(x); x.fillStyle = '#f7f5ef'; x.fillRect(0, 0, w, hh); x.fillStyle = S.shade(col, -.25); x.fillRect(0, 0, w, 26); x.fillRect(0, hh - 26, w, 26); if (text) S.txt(String(text).toUpperCase(), w / 2, hh / 2 + 4, hh * .46, S.shade(col, -.4), w * .26); S.ctx(old); });
  const lab = mk(new T3.CylinderGeometry(.274, .274, .34, 40, 1, true), new T3.MeshStandardMaterial({map: wrap, roughness: .55, envMap: ENV, envMapIntensity: .3})); lab.rotation.y = PI; lab.position.y = .36;
  const cap = grp(at(cyl(.1, .1, .1, PM('#f4f4f1', {roughness: .4}), 28), 0, 1.2, 0), at(cyl(.085, .1, .02, PM('#f4f4f1', {roughness: .4}), 28), 0, 1.26, 0)); const ring = mk(new T3.TorusGeometry(.094, .012, 8, 28), PM(col, {roughness: .2})); ring.rotation.x = PI / 2; g.add(at(ring, 0, 1.1, 0));
  g.add(lab, cap); g.userData.late = [cap, lab]; return g; }
function pill(col) {                   // a two-colour capsule leaning on two tablets
  const g = new T3.Group(), p = new T3.Group(), r = .2, len = .42;
  for (const [mat, s, rr] of [[PM('#f7f5ee', {roughness: .1, envMapIntensity: 1.1}), -1, r], [PM(col, {roughness: .1, envMapIntensity: 1.1}), 1, r * 1.035]]) { p.add(at(cyl(rr, rr, len, mat, 36), 0, s * len / 2, 0));
    const cap = mk(new T3.SphereGeometry(rr, 36, 14, 0, 2 * PI, 0, PI / 2), mat); if (s < 0) cap.rotation.x = PI; p.add(at(cap, 0, s * len, 0)); }
  p.rotation.z = .9; p.position.set(0, .6, 0); g.add(p);
  for (const [x, z] of [[-.5, .28], [.52, .3]]) { g.add(at(lathe([[0, 0], [.13, 0], [.155, .02], [.155, .055], [.13, .075], [0, .075]], PM('#f7f5ee', {roughness: .55}), 28), x, 0, z)); g.add(at(box(.24, .006, .012, PM('#d9d6cc', {roughness: .7})), x, .076, z)); }
  g.userData.late = []; return g; }
function shirt(col, text) {            // a T-shirt on a hanger
  const g = new T3.Group(), late = [], sh = new T3.Shape(); sh.moveTo(-.18, .98); sh.lineTo(-.48, .85); sh.lineTo(-.6, .6); sh.lineTo(-.41, .53); sh.lineTo(-.33, .64); sh.lineTo(-.33, .03); sh.lineTo(.33, .03); sh.lineTo(.33, .64); sh.lineTo(.41, .53); sh.lineTo(.6, .6); sh.lineTo(.48, .85); sh.lineTo(.18, .98); sh.quadraticCurveTo(0, .82, -.18, .98);
  const F = PM(col, {roughness: .9, envMapIntensity: .15}), R = PM(S.shade(col, -.28), {roughness: .9, envMapIntensity: .15}); g.add(ext(sh, .1, F, .028));
  const collar = mk(new T3.TorusGeometry(.14, .026, 8, 20, PI), R); collar.rotation.z = PI; g.add(at(collar, 0, 1.0, .05)); g.add(at(rbox(.7, .035, .16, .012, R), 0, .02, 0));
  for (const s of [-1, 1]) { const cuff = rbox(.2, .035, .15, .012, R); cuff.rotation.z = s * .36; g.add(at(cuff, s * .51, .555, 0)); const arm = cyl(.014, .014, .5, PM('#b98a55', {roughness: .5}), 10, 'x'); arm.rotation.z = PI / 2 + s * .4; g.add(at(arm, s * .22, .97, -.02)); }
  const hook = mk(new T3.TorusGeometry(.07, .012, 8, 16, PI * 1.4), CHROME); g.add(at(hook, 0, 1.13, -.02));
  if (text) { const l = at(print(text, .42, .11, '#ffffff', S.shade(col, -.35), {roughness: .9}), 0, .52, .0795); g.add(l); late.push(l); } late.push(collar); g.userData.late = late; return g; }
function shoe(col) {                   // a trainer: a moulded sole, a padded upper with a toe cap and a heel counter, a tongue, laces tied in a bow
  const g = new T3.Group(), up = new T3.Group(), D = .42, F = PM(col, {roughness: .85, envMapIntensity: .2}), F2 = PM(S.shade(col, -.3), {roughness: .8, envMapIntensity: .2}), so = new T3.Shape(), u = new T3.Shape(), toe = new T3.Shape(), heel = new T3.Shape();
  so.moveTo(-.5, .04); so.lineTo(.4, .04); so.quadraticCurveTo(.58, .05, .6, .14); so.quadraticCurveTo(.6, .19, .52, .19); so.lineTo(-.5, .22); so.quadraticCurveTo(-.56, .22, -.56, .15); so.quadraticCurveTo(-.56, .04, -.5, .04);
  g.add(ext(so, D, PM('#f6f6f3', {roughness: .5, envMapIntensity: .4}), .04, {bevelSegments: 5})); g.add(at(rbox(1.06, .035, D - .08, .015, PM('#2c2f37', {roughness: .9})), .01, .0175, 0)); g.add(at(box(1.02, .014, D + .006, F), -.01, .125, 0));
  u.moveTo(-.44, .2); u.lineTo(-.45, .42); u.quadraticCurveTo(-.45, .48, -.39, .47); u.quadraticCurveTo(-.28, .37, -.16, .47); u.quadraticCurveTo(-.1, .52, -.06, .5); u.lineTo(.26, .27); u.quadraticCurveTo(.46, .24, .48, .2); u.closePath();
  toe.moveTo(.24, .2); toe.lineTo(.26, .27); toe.quadraticCurveTo(.46, .24, .48, .2); toe.closePath(); heel.moveTo(-.44, .2); heel.lineTo(-.45, .42); heel.quadraticCurveTo(-.45, .48, -.39, .47); heel.lineTo(-.36, .44); heel.lineTo(-.3, .2); heel.closePath();
  up.add(ext(u, .36, F, .09, {bevelSegments: 6})); up.add(ext(toe, .37, F2, .095, {bevelSegments: 6})); up.add(ext(heel, .37, F2, .095, {bevelSegments: 6}));       // the upper, its toe cap, its heel counter
  const tongue = rbox(.17, .15, .2, .035, F2); tongue.rotation.z = .55; up.add(at(tongue, -.07, .575, 0)); up.add(at(ball(1, BLACK, .13, .03, .1), -.28, .505, 0));
  for (let k = 0; k < 5; k++) { const t = .1 + k * .2; up.add(at(cyl(.016, .016, .2, WHITE, 10, 'z'), -.008 + .32 * t, .58 - .23 * t, 0)); }
  for (const z of [-1, 1]) { const loop = mk(new T3.TorusGeometry(.045, .012, 8, 16), WHITE); loop.rotation.set(.3 * z, z * .9, 0); up.add(at(loop, 0, .63, z * .06)); }
  const band = new T3.Shape(); band.moveTo(-.2, .22); band.lineTo(-.1, .22); band.lineTo(.04, .4); band.lineTo(-.05, .43); band.closePath(); for (const z of [-1, 1]) up.add(at(ext(band, .01, WHITE), 0, 0, z * .182));
  g.add(up); g.userData.late = [up]; return g; }
function gamepad(col) {                // a game controller, tipped up to face us
  const g = new T3.Group(), pad = new T3.Group(), s = new T3.Shape(), late = [], BODY = PM('#2a2d36', {roughness: .42, envMapIntensity: .6}), K = PM('#16171c', {roughness: .5});
  s.moveTo(-.52, .1); s.quadraticCurveTo(-.6, .34, -.38, .34); s.lineTo(.38, .34); s.quadraticCurveTo(.6, .34, .52, .1); s.lineTo(.47, -.2); s.quadraticCurveTo(.42, -.4, .28, -.3); s.lineTo(.17, -.1); s.lineTo(-.17, -.1); s.lineTo(-.28, -.3); s.quadraticCurveTo(-.42, -.4, -.47, -.2); s.closePath();
  pad.add(ext(s, .2, BODY, .07)); for (const x of [-.36, .36]) pad.add(at(rbox(.24, .06, .1, .025, K), x, .4, -.03));
  const dp = grp(rbox(.18, .058, .03, .012, K), rbox(.058, .18, .03, .012, K)); at(dp, -.34, .16, .105); late.push(dp);
  [[.08, 0, col], [-.08, 0, '#ffc83d'], [0, .08, '#2bd47d'], [0, -.08, '#e8394a']].forEach(([dx, dy, c]) => late.push(at(cyl(.04, .04, .03, PM(c, {roughness: .25, envMapIntensity: .9}), 20, 'z'), .34 + dx, .16 + dy, .11)));
  for (const x of [-.14, .14]) late.push(grp(at(cyl(.075, .08, .016, K, 24, 'z'), x, -.02, .104), at(cyl(.032, .032, .05, K, 16, 'z'), x, -.02, .13), at(ball(.062, PM('#3a3e49', {roughness: .7}), 1, 1, .4), x, -.02, .16)));
  late.push(at(cyl(.035, .035, .012, PM(col, {emissive: col, emissiveIntensity: 1.2}), 20, 'z'), 0, .2, .103)); for (const x of [-.1, .1]) pad.add(at(rbox(.05, .022, .012, .006, K), x, .21, .102));
  late.forEach(m => pad.add(m)); pad.rotation.x = -.42; pad.position.y = .5; g.add(pad); g.userData.late = late; return g; }
function burger() {
  const g = new T3.Group(), BUN = PM('#d68f3c', {roughness: .5, envMapIntensity: .4}), top = new T3.Group();
  g.add(lathe([[0, 0], [.46, 0], [.54, .04], [.56, .1], [.54, .16], [0, .16]], BUN)); g.add(lathe([[0, .16], [.56, .16], [.6, .2], [.6, .26], [.56, .3], [0, .3]], PM('#55301c', {roughness: .95, envMapIntensity: .12})));
  const ch = box(.98, .025, .98, PM('#ffc02e', {roughness: .3, envMapIntensity: .6})); ch.rotation.y = PI / 4; g.add(at(ch, 0, .312, 0));
  for (let k = 0; k < 3; k++) g.add(at(cyl(.28, .28, .04, PM('#d8352a', {roughness: .25, envMapIntensity: .8}), 28), Math.cos(k * 2.1 + .4) * .3, .345, Math.sin(k * 2.1 + .4) * .3));
  const lg = new T3.TorusGeometry(.5, .07, 8, 64), lp = lg.attributes.position; for (let i = 0; i < lp.count; i++) { const a = Math.atan2(lp.getY(i), lp.getX(i)), k = 1 + .06 * Math.sin(a * 13); lp.setXYZ(i, lp.getX(i) * k, lp.getY(i) * k, lp.getZ(i) * .45 + .04 * Math.sin(a * 9)); } lg.computeVertexNormals();
  const let_ = mk(lg, PM('#6cab38', {roughness: .6, envMapIntensity: .4})); let_.rotation.x = PI / 2; g.add(at(let_, 0, .385, 0));
  const dome = mk(new T3.SphereGeometry(.57, 40, 16, 0, 2 * PI, 0, PI / 2), PM('#cf8431', {roughness: .32, envMapIntensity: .7})); dome.scale.y = .62; top.add(dome); top.add(at(cyl(.56, .56, .02, BUN, 36), 0, .005, 0));
  for (let k = 0; k < 30; k++) { const th = .12 + hsh(k) * .95, ph = hsh(k + 40) * 2 * PI, sd = ball(.022, PM('#f6e7c4', {roughness: .5}), 1, .45, 1.7); sd.position.set(.572 * Math.sin(th) * Math.cos(ph), .62 * .572 * Math.cos(th), .572 * Math.sin(th) * Math.sin(ph)); sd.rotation.y = hsh(k + 9) * 3; top.add(sd); }
  top.position.y = .41; g.add(top); g.userData.late = [top]; return g; }
function parcel(text) {                // a cardboard box, taped, with its shipping label
  const g = new T3.Group(), K = '#c59b6d', CB = {roughness: .95, envMapIntensity: .12}, TAPE = PM('#dcbd88', {roughness: .22, envMapIntensity: .8});
  g.add(at(rbox(1, .8, .8, .018, PM(K, CB)), 0, .4, 0));
  const face = decal(.94, .74, 384, (x, w, hh) => { x.fillStyle = K; x.fillRect(0, 0, w, hh); x.fillStyle = 'rgba(90,60,30,.10)'; for (let i = 0; i < 60; i++) x.fillRect(0, hsh(i) * hh, w, 1.5);      // the card's ribs
    if (text) S.txt(String(text).toUpperCase(), w * .3, hh * .36, hh * .3, '#4a3320', w * .5);
    x.fillStyle = '#f7f5ef'; x.fillRect(w * .6, hh * .52, w * .33, hh * .36); x.fillStyle = '#22242b'; for (let i = 0; i < 22; i++) x.fillRect(w * .62 + i * w * .0135, hh * .7, hsh(i + 3) > .5 ? w * .008 : w * .004, hh * .14);
    for (let i = 0; i < 3; i++) x.fillRect(w * .62, hh * (.56 + i * .04), w * (.26 - i * .06), hh * .014);
    x.strokeStyle = '#4a3320'; x.lineWidth = hh * .022; x.lineJoin = 'round'; for (const ax of [.12, .26]) { const cx = w * ax, by = hh * .88; x.beginPath(); x.moveTo(cx, by); x.lineTo(cx, by - hh * .2); x.moveTo(cx - w * .04, by - hh * .13); x.lineTo(cx, by - hh * .2); x.lineTo(cx + w * .04, by - hh * .13); x.stroke(); }
    x.beginPath(); x.moveTo(w * .06, hh * .92); x.lineTo(w * .32, hh * .92); x.stroke(); }, CB); g.add(at(face, 0, .4, .4012));
  const tape = grp(at(box(1.006, .004, .15, TAPE), 0, .802, 0), at(box(.004, .24, .15, TAPE), .503, .682, 0), at(box(.004, .24, .15, TAPE), -.503, .682, 0)); g.add(tape);
  g.add(at(box(.002, .56, .004, BLACK), 0, .8, 0)); g.userData.late = [tape]; return g; }
const MAKE = {camera, chip, phone, laptop, car, van, bottle, pill, shirt, shoe, game: gamepad, food: burger};
function product(kind, col, text) { const g = MAKE[kind] ? MAKE[kind](col, text) : parcel(text); if (!g.userData.late) g.userData.late = []; return g; }

// ---------------------------------------------------------------- money: a case of banded notes, gold coins
const NOTE = new T3.MeshStandardMaterial({roughness: .8, envMap: ENV, envMapIntensity: .15, map: canvasTex(512, 224, (x, w, hh) => { const old = S.ctx(x), g = x.createLinearGradient(0, 0, w, 0); g.addColorStop(0, '#6fae7b'); g.addColorStop(.5, '#a8d3a0'); g.addColorStop(1, '#6fae7b'); x.fillStyle = g; x.fillRect(0, 0, w, hh);
  x.strokeStyle = '#2f6b45'; x.lineWidth = 8; x.strokeRect(14, 14, w - 28, hh - 28); x.lineWidth = 2; x.strokeRect(28, 28, w - 56, hh - 56); for (let i = 0; i < 9; i++) { x.beginPath(); x.ellipse(w / 2, hh / 2, 150 - i * 9, 86 - i * 6, 0, 0, 7); x.stroke(); }
  x.fillStyle = '#e4f2df'; x.beginPath(); x.ellipse(w / 2, hh / 2, 62, 78, 0, 0, 7); x.fill(); x.fillStyle = '#2f6b45'; x.beginPath(); x.arc(w / 2, hh / 2 - 18, 24, 0, 7); x.fill(); x.beginPath(); x.ellipse(w / 2, hh / 2 + 52, 44, 34, 0, PI, 0); x.fill();
  for (const [cx, cy] of [[70, 62], [w - 70, 62], [70, hh - 54], [w - 70, hh - 54]]) S.txt('100', cx, cy, 44, '#1f5133'); S.ctx(old); })});
const EDGE = new T3.MeshStandardMaterial({roughness: .9, envMap: ENV, envMapIntensity: .1, map: canvasTex(8, 64, (x, w, hh) => { x.fillStyle = '#e9efe2'; x.fillRect(0, 0, w, hh); x.fillStyle = '#b9c9b4'; for (let i = 0; i < 16; i++) x.fillRect(0, i * 4, w, 1.4); })});
const STRAP = PM('#f3e7c3', {roughness: .7});
function bundle(w = .62, hh = .13, d = .28) { return grp(mk(new T3.BoxGeometry(w, hh, d), [EDGE, EDGE, NOTE, EDGE, EDGE, EDGE]), box(w * .2, hh + .008, d + .008, STRAP)); }
function coin(r) { const m = lathe([[0, 0], [r * .93, 0], [r, r * .06], [r, r * .2], [r * .93, r * .26], [r * .8, r * .2], [0, r * .2]], GOLD, 28); m.geometry.translate(0, -r * .13, 0); return m; }
function cash() {                     // an open metal case tipped towards us, full of banded notes; loose bundles and coins beside it
  const g = new T3.Group(), c = new T3.Group(), AL = PM('#b3b9c4', {metalness: .9, roughness: .34, envMapIntensity: 1}), IN = PM('#191b20', {roughness: .9, envMapIntensity: .1});
  c.add(at(lay(rbox(1.5, .95, .2, .03, AL, .07)), 0, .1, 0)); c.add(at(box(1.42, .02, .87, IN), 0, .195, 0));
  for (let r = 0; r < 3; r++) for (const sx of [-1, 1]) { c.add(at(bundle(), sx * .34, .27, -.29 + r * .29)); if (!(r === 2 && sx > 0)) { const b2 = bundle(); b2.rotation.y = (hsh(r * 2 + sx) - .5) * .16; c.add(at(b2, sx * .34, .4, -.29 + r * .29)); } }
  const top = bundle(); top.rotation.set(0, .5, 0); c.add(at(top, .1, .53, -.05));
  const lid = new T3.Group(); lid.add(at(rbox(1.5, .95, .12, .03, AL, .07), 0, .475, -.06)); lid.add(at(box(1.4, .85, .01, IN), 0, .475, .003)); for (const x of [-.5, 0, .5]) lid.add(at(rbox(.05, .93, .02, .008, AL), x, .475, -.125));
  lid.position.set(0, .2, -.475); lid.rotation.x = -.25; c.add(lid);
  const hd = mk(new T3.TorusGeometry(.13, .02, 8, 20, PI), DARK); hd.rotation.x = PI / 2; c.add(at(hd, 0, .1, .48)); for (const x of [-.48, .48]) c.add(at(rbox(.1, .07, .03, .01, CHROME), x, .15, .478));
  c.rotation.x = .3; c.position.set(0, .16, 0); g.add(c);
  for (const [x, y, z, ry] of [[-.34, .065, -.34, .1], [.34, .065, -.34, -.08], [-.34, .195, -.34, -.05], [.34, .195, -.34, .12]]) { const b = bundle(); b.rotation.y = ry; g.add(at(b, x, y, z)); }      // what the case leans on
  for (const [x, y, z, ry] of [[1.05, .065, .32, .5], [1.02, .195, .3, .2]]) { const b = bundle(); b.rotation.y = ry; g.add(at(b, x, y, z)); }
  for (const [x, z, n] of [[-1.02, .34, 7], [-.8, .52, 4]]) for (let k = 0; k < n; k++) g.add(at(coin(.11), x + (hsh(k + n) - .5) * .014, .015 + k * .03, z + (hsh(k * 3 + n) - .5) * .014));
  return g; }

// ---------------------------------------------------------------- other things on a stage
function tube(x0, y0, z0, x1, y1, z1, r, mat) {      // a rod from one point to another
  const a = new T3.Vector3(x0, y0, z0), b = new T3.Vector3(x1, y1, z1), m = mk(new T3.CylinderGeometry(r, r, a.distanceTo(b), 12), mat); m.position.copy(a).add(b).multiplyScalar(.5); m.quaternion.setFromUnitVectors(new T3.Vector3(0, 1, 0), b.clone().sub(a).normalize()); return m; }
function tower(col) {                  // an office tower: a stone base with glass doors under a canopy, a glass wall in a painted frame, plant and a mast on the roof
  const g = new T3.Group(), Wd = 2.6, Hh = 5.6, Dp = 2.2, FR = PM(col, {roughness: .45, envMapIntensity: .5}), ST = PM('#343a4e', {roughness: .7});
  const win = canvasTex(320, 640, (x, w, hh) => { x.fillStyle = '#27304a'; x.fillRect(0, 0, w, hh); const cw = w / 5, ch = hh / 11; for (let r = 0; r < 11; r++) for (let k = 0; k < 5; k++) { const g2 = x.createLinearGradient(0, r * ch, 0, (r + 1) * ch);
    if (hsh(r * 7 + k) > .74) { g2.addColorStop(0, '#fff0bd'); g2.addColorStop(1, '#f5cf7a'); } else { g2.addColorStop(0, '#a5d2f5'); g2.addColorStop(1, '#4f86bb'); } x.fillStyle = g2; x.fillRect(k * cw + 5, r * ch + 5, cw - 10, ch - 10); } });
  const GL = new T3.MeshStandardMaterial({map: win, roughness: .16, metalness: .3, envMap: ENV, envMapIntensity: .9}); g.add(at(mk(new T3.BoxGeometry(Wd - .1, Hh - 1, Dp - .1), [GL, GL, ST, ST, GL, GL]), 0, 1 + (Hh - 1) / 2, 0));
  for (const x of [-1, 1]) for (const z of [-1, 1]) g.add(at(rbox(.18, Hh, .18, .04, FR), x * (Wd / 2 - .06), Hh / 2, z * (Dp / 2 - .06)));
  g.add(at(rbox(Wd + .16, .26, Dp + .16, .05, FR), 0, Hh + .08, 0)); g.add(at(rbox(Wd + .1, 1, Dp + .1, .04, ST), 0, .5, 0));
  g.add(at(rbox(.9, .42, .7, .04, STEEL), -.5, Hh + .42, -.2)); g.add(at(cyl(.03, .03, 1, DARK, 8), .6, Hh + .7, -.3)); g.add(at(ball(.07, PM('#ff3b3b', {emissive: '#ff3b3b', emissiveIntensity: 2.5})), .6, Hh + 1.22, -.3));
  g.add(at(rbox(1.1, .86, .06, .02, CHROME), 0, .44, Dp / 2 + .05)); for (const x of [-.26, .26]) { g.add(at(rbox(.48, .78, .04, .01, GLASS), x, .43, Dp / 2 + .075)); g.add(at(rbox(.02, .26, .03, .008, CHROME), x - Math.sign(x) * .19, .45, Dp / 2 + .1)); }
  g.add(at(rbox(1.5, .08, .6, .03, FR), 0, .96, Dp / 2 + .32)); return g; }
function tv(w, hh, stand) {            // a flat screen on its foot, the picture (drawn by the caller) at z = .076; its centre at the origin, its foot stand below its bottom edge
  const g = new T3.Group(); g.add(rbox(w, hh, .14, .04, GLOSS, .07)); g.add(at(rbox(.34, stand + .1, .07, .025, DARK), 0, -hh / 2 - stand / 2 + .05, -.03));
  const foot = cyl(.7, .74, .06, DARK, 40); foot.scale.z = .5; g.add(at(foot, 0, -hh / 2 - stand + .03, 0)); g.add(at(ball(.018, PM('#ff3b3b', {emissive: '#ff3b3b', emissiveIntensity: 2})), w / 2 - .12, -hh / 2 + .045, .072)); return g; }
function turntable(r, col) {           // what a product stands on: a dark disc with a bright rim, its top (y .18) lit in the company's colour
  const g = new T3.Group(); g.add(lathe([[0, 0], [r + .1, 0], [r + .1, .04], [r + .03, .15], [r, .165], [0, .165]], PM('#1c2034', {roughness: .3, envMapIntensity: .8}), 56));
  const ring = mk(new T3.TorusGeometry(r + .005, .014, 8, 64), CHROME); ring.rotation.x = PI / 2; g.add(at(ring, 0, .165, 0)); g.add(at(cyl(r - .06, r - .06, .02, PM(S.shade(col, -.1), {emissive: col, emissiveIntensity: .5, roughness: .4}), 56), 0, .17, 0)); return g; }
function qmark(col) {                  // a question mark you could pick up
  const g = new T3.Group(), M2 = PM(col, {roughness: .2, metalness: .15, envMapIntensity: 1}), R = .36, tb = .13, hook = mk(new T3.TorusGeometry(R, tb, 16, 40, PI * 1.5), M2); hook.rotation.z = -PI / 2;
  g.add(at(hook, 0, 1.28, 0)); g.add(at(ball(tb, M2), -R, 1.28, 0)); g.add(at(cyl(tb, tb, .3, M2, 24), 0, .77, 0)); g.add(at(ball(tb, M2), 0, .62, 0)); g.add(at(ball(.16, M2), 0, .2, 0)); return g; }
function trophy() {
  const g = new T3.Group(), cup = lathe([[0, 0], [.3, 0], [.34, .04], [.3, .1], [.1, .16], [.07, .5], [.12, .58], [.4, .86], [.5, 1.2], [.52, 1.5], [.47, 1.5], [.44, 1.22], [.34, .94], [0, .7]], GOLD, 40); g.add(at(cup, 0, .26, 0));
  for (const s of [-1, 1]) { const hd = mk(new T3.TorusGeometry(.2, .035, 10, 24, PI), GOLD); hd.rotation.z = -s * PI / 2; g.add(at(hd, s * .47, 1.42, 0)); }
  g.add(at(rbox(.9, .26, .62, .03, PM('#3b2416', {roughness: .35, envMapIntensity: .6})), 0, .13, 0)); g.add(at(rbox(.46, .12, .01, .004, GOLD), 0, .13, .312)); return g; }
function bulb() {                      // returns {g, glass}: a glass bulb on a threaded cap
  const g = new T3.Group(), glass = lathe([[.15, .52], [.155, .58], [.19, .67], [.26, .77], [.33, .87], [.385, .97], [.41, 1.07], [.405, 1.17], [.37, 1.27], [.31, 1.35], [.23, 1.41], [.12, 1.445], [0, 1.455]], PM('#ffe46b', {emissive: '#ffcc33', emissiveIntensity: 1.2, roughness: .1, envMapIntensity: .9}), 40); g.add(glass);
  g.add(at(cyl(.16, .15, .26, STEEL, 28), 0, .42, 0)); for (let k = 0; k < 4; k++) { const th = mk(new T3.TorusGeometry(.158, .016, 8, 28), CHROME); th.rotation.x = PI / 2; g.add(at(th, 0, .32 + k * .065, 0)); }
  g.add(at(cyl(.07, .13, .08, DARK, 20), 0, .25, 0)); g.add(at(cyl(.05, .05, .03, STEEL, 16), 0, .2, 0)); return {g, glass}; }
function rocket() {                    // returns {r, flame}
  const r = new T3.Group(), body = lathe([[0, 0], [.26, 0], [.36, .2], [.4, .7], [.38, 1.15], [.3, 1.5], [.16, 1.78], [0, 1.92]], PM('#f1f3f8', {roughness: .25, envMapIntensity: .9}), 40); r.add(body);
  r.add(lathe([[.305, 1.48], [.3, 1.5], [.16, 1.78], [0, 1.925], [0, 1.9]].map(([x, y]) => [x * 1.02, y]), PM('#e8394a', {roughness: .25, envMapIntensity: .9}), 40)); const band = mk(new T3.TorusGeometry(.385, .02, 8, 40), PM('#e8394a', {roughness: .3})); band.rotation.x = PI / 2; r.add(at(band, 0, .5, 0));
  r.add(at(cyl(.15, .15, .03, CHROME, 28, 'z'), 0, 1.12, .375)); r.add(at(cyl(.115, .115, .035, PM('#5ab0ff', {emissive: '#2f7cf6', emissiveIntensity: .5, roughness: .08, metalness: .6, envMapIntensity: 1.5}), 28, 'z'), 0, 1.12, .378));
  const fin = new T3.Shape(); fin.moveTo(0, .62); fin.quadraticCurveTo(.3, .4, .36, -.1); fin.lineTo(.14, .02); fin.lineTo(0, .06); fin.closePath();
  for (let k = 0; k < 3; k++) { const f = grp(at(ext(fin, .04, PM('#e8394a', {roughness: .3, envMapIntensity: .8}), .012), .34, 0, 0)); f.rotation.y = k * 2 * PI / 3 + PI / 6; r.add(f); }
  r.add(at(lathe([[.14, 0], [.2, -.16], [.22, -.2], [.17, -.2], [.12, -.02]], STEEL, 28), 0, 0, 0));
  const flame = mk(new T3.ConeGeometry(.2, .8, 16), h.glowM('#ff8a2c', 2), false); flame.rotation.x = PI; flame.position.y = -.56; r.add(flame); return {r, flame}; }
function gavel() {                     // returns {g, hammer}: a judge's hammer over its block
  const g = new T3.Group(), WOOD = PM('#7a4526', {roughness: .32, envMapIntensity: .7}), hammer = new T3.Group();
  g.add(lathe([[0, 0], [.52, 0], [.56, .04], [.56, .14], [.5, .2], [.44, .22], [0, .22]], WOOD, 40));
  const head = lathe([[0, -.46], [.2, -.46], [.24, -.42], [.24, -.3], [.2, -.26], [.2, .26], [.24, .3], [.24, .42], [.2, .46], [0, .46]], WOOD, 32); head.rotation.z = PI / 2; hammer.add(at(head, 0, 1.25, 0));
  for (const x of [-.28, .28]) { const bd = mk(new T3.TorusGeometry(.205, .022, 8, 28), GOLD); bd.rotation.y = PI / 2; hammer.add(at(bd, x, 1.25, 0)); }
  hammer.add(at(lathe([[0, 0], [.05, 0], [.07, .05], [.05, .4], [.06, 1.05], [0, 1.05]], PM('#9a6236', {roughness: .35, envMapIntensity: .6}), 20), 0, .1, 0)); g.add(hammer); return {g, hammer}; }
return {product, cash, coin, bundle, phoneShell, tv, turntable, qmark, trophy, bulb, rocket, gavel, parcel, tower, keyboard, tube, PM, rbox, ext, cyl, ball, box, GOLD, CHROME, STEEL, GLASS, DARK, GLOSS, WHITE, RUBBER, BLACK};
};
