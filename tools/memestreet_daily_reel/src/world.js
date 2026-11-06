// Neon 3D scenes for the reels, in the house style of the PhaseJump reel: glowing teal, purple and amber line work on
// near-black, with depth, bloom and a moving camera. drawWorld(canvas, scene, t) is deterministic in t (every frame is
// computed from the time alone), so render.py can screenshot any frame in any order. It returns the props' labels in
// screen pixels for reel.html to draw as text (so the overlap check sees them).
//
// A world scene: {"layout": "flow|network|hero|grow|risk|compare", "props": [{"p": "<prop>", "color": "teal|...",
// "label": "max 3 words", "t": <time it pops in, from narrate.py>}]}
import * as THREE from 'three';
import {EffectComposer} from './vendor/three/examples/jsm/postprocessing/EffectComposer.js';
import {RenderPass} from './vendor/three/examples/jsm/postprocessing/RenderPass.js';
import {UnrealBloomPass} from './vendor/three/examples/jsm/postprocessing/UnrealBloomPass.js';
import {OutputPass} from './vendor/three/examples/jsm/postprocessing/OutputPass.js';
import {LineSegments2} from './vendor/three/examples/jsm/lines/LineSegments2.js';
import {LineSegmentsGeometry} from './vendor/three/examples/jsm/lines/LineSegmentsGeometry.js';
import {LineMaterial} from './vendor/three/examples/jsm/lines/LineMaterial.js';

const W = 1080, H = 1920, S = .5, BG = 0x080a0b;     // (drawn at half size and scaled up: a glow style stays soft, and it is 4x faster)
export const COL = {teal: 0x4fc6c8, green: 0x3dd68c, amber: 0xe8b14a, red: 0xf0585c, purple: 0x9b7bff, white: 0xe6e9ec, grey: 0x5a636e};
const cl = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x)), seg = (t, a, b) => cl((t - a) / (b - a));
const io = u => u < .5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2, out = u => 1 - Math.pow(1 - u, 3);
const back = u => {const c = 1.7; return 1 + (c + 1) * Math.pow(u - 1, 3) + c * Math.pow(u - 1, 2)};
const rnd = k => {const x = Math.sin(k * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x)};   // (seeded: same every frame)

let R, comp, scene, cam, built = null, parts = {};

function setup(canvas) {
  R = new THREE.WebGLRenderer({canvas, antialias: true, preserveDrawingBuffer: true});
  R.setPixelRatio(1); R.setSize(W * S, H * S, false);
  R.toneMapping = THREE.ACESFilmicToneMapping; R.toneMappingExposure = 1.05;
  scene = new THREE.Scene(); scene.background = new THREE.Color(BG); scene.fog = new THREE.Fog(BG, 13, 32);
  cam = new THREE.PerspectiveCamera(46, W / H, .1, 100); cam.setViewOffset(W, H, 0, H * .07, W, H);   // (the scene sits a little high: the captions get the floor)
  comp = new EffectComposer(R); comp.setSize(W * S, H * S);
  comp.addPass(new RenderPass(scene, cam));
  comp.addPass(new UnrealBloomPass(new THREE.Vector2(W * S / 2, H * S / 2), .75, .5, .28));   // (the glow: the look of the style)
  comp.addPass(new OutputPass());
}

// ---- materials: bright lines that bloom, dark bodies that catch coloured light
const glow = (c, o = 1) => new THREE.MeshBasicMaterial({color: c, transparent: o < 1, opacity: o, toneMapped: false});
const line = (c, o = 1) => new THREE.LineBasicMaterial({color: c, transparent: o < 1, opacity: o, toneMapped: false});
const body = (c = 0x12161b, tint = 0) => new THREE.MeshStandardMaterial({color: c, roughness: .55, metalness: .5, emissive: tint, emissiveIntensity: .07,
  polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1});   // (pushed back a hair: the edge lines never flicker through)
const FAT = {};                                              // (thick neon edges: plain WebGL lines are 1 px and look dashed)
const fat = (c, o = 1, w = 2.6) => FAT[[c, o, w]] ||= Object.assign(new LineMaterial({color: c, linewidth: w, transparent: o < 1, opacity: o, toneMapped: false}),
  {resolution: new THREE.Vector2(W * S, H * S)});
function halo(c, size, o = 1) {                              // a soft additive disc (the glow pool under and inside things)
  const cv = document.createElement('canvas'); cv.width = cv.height = 128; const g = cv.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); const k = new THREE.Color(c);
  gr.addColorStop(0, `rgba(${k.r * 255 | 0},${k.g * 255 | 0},${k.b * 255 | 0},.9)`); gr.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  return new THREE.Mesh(new THREE.PlaneGeometry(size, size), new THREE.MeshBasicMaterial({map: new THREE.CanvasTexture(cv),
    transparent: true, opacity: o, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false}));
}
const edges = (geo, c, o = 1) => new LineSegments2(new LineSegmentsGeometry().fromEdgesGeometry(new THREE.EdgesGeometry(geo, 20)), fat(c, o));
function curveLine(pts, c, w = 3.2) {                       // a thick glowing line along a curve
  const P = new THREE.CatmullRomCurve3(pts.map(p => new THREE.Vector3(...p))).getPoints(40), a = [];
  for (let i = 0; i < P.length - 1; i++) a.push(P[i].x, P[i].y, P[i].z, P[i + 1].x, P[i + 1].y, P[i + 1].z);
  return new LineSegments2(new LineSegmentsGeometry().setPositions(a), fat(c, 1, w));
}
function solid(geo, c, x = 0, y = 0, z = 0, dark = 0x12161b) {  // the house look for any shape: dark body, glowing edges
  const g = new THREE.Group(); g.add(new THREE.Mesh(geo, body(dark, c)), edges(geo, c)); g.position.set(x, y, z); return g;
}
const grp = (...xs) => {const g = new THREE.Group(); xs.forEach(x => g.add(x)); return g};
const at = (o, x, y, z, rx = 0, ry = 0, rz = 0) => {o.position.set(x, y, z); o.rotation.set(rx, ry, rz); return o};
const tube = (pts, r, c) => new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map(p => new THREE.Vector3(...p))), 40, r, 8), glow(c, .9));

// ---- props: each is about 1.5 units tall, standing on y = 0, facing +z
export const PROPS = {
  portal(c) {
    const g = new THREE.Group(); g.userData.portal = true;
    for (let k = 0; k < 4; k++) g.add(new THREE.Mesh(new THREE.TorusGeometry(1 - k * .08, k ? .012 : .04, 12, 96), glow(c, k ? .55 - k * .1 : .9)));
    const h = halo(c, 2.2, .35); h.position.z = -.01; g.add(h);
    g.userData.sparks = [0, 1, 2, 3, 4, 5].map(k => {const s = new THREE.Mesh(new THREE.SphereGeometry(.035, 8, 8), glow(0xffffff)); s.userData.k = k; g.add(s); return s});
    g.scale.set(.8, 1.45, .8); g.position.y = 1.45;
    return grp(g);
  },
  crate(c) {
    const geo = new THREE.BoxGeometry(.75, .75, .75), g = solid(geo, c, 0, .38, 0, 0x1a1712);
    g.add(new THREE.Mesh(new THREE.BoxGeometry(.77, .035, .77), glow(c, .8)));
    return grp(g);
  },
  node(c) { return grp(at(new THREE.Mesh(new THREE.SphereGeometry(.25, 16, 12), glow(c)), 0, .8, 0), at(halo(c, 1.4, .8), 0, .8, 0)) },
  building(c) {                                               // a tower with glowing window rows
    const g = grp(solid(new THREE.BoxGeometry(.9, 2.2, .9), c, 0, 1.1, 0));
    for (let k = 0; k < 6; k++) g.add(at(new THREE.Mesh(new THREE.BoxGeometry(.92, .04, .92), glow(c, .6)), 0, .3 + k * .32, 0));
    return g;
  },
  city(c) {                                                   // a block of towers of different heights
    const g = new THREE.Group();
    [[-.8, 1.2, -.3], [0, 2, 0], [.8, 1.5, -.4], [-.3, .9, .7], [.5, .8, .6]].forEach(([x, h, z]) => g.add(solid(new THREE.BoxGeometry(.6, h, .6), c, x, h / 2, z)));
    return g;
  },
  factory(c) {                                                // a hall with a sawtooth roof and a chimney with smoke rings
    const g = grp(solid(new THREE.BoxGeometry(2, .9, 1.2), c, 0, .45, 0), solid(new THREE.CylinderGeometry(.14, .18, 1.6, 16), c, .7, .8, -.3));
    for (let k = 0; k < 3; k++) g.add(solid(new THREE.BoxGeometry(.6, .3, 1.2), c, -.65 + k * .65, 1.05, 0));
    g.userData.smoke = [0, 1, 2].map(k => {const r = new THREE.Mesh(new THREE.TorusGeometry(.16, .025, 8, 32), glow(COL.grey, .6)); r.rotation.x = Math.PI / 2; g.add(r); return r});
    return grp(g);
  },
  warehouse(c) {
    const roof = solid(new THREE.CylinderGeometry(.7, .7, 2, 24, 1, false, 0, Math.PI), c, 0, 1, 0); roof.rotation.z = Math.PI / 2;
    const g = grp(solid(new THREE.BoxGeometry(2, 1, 1.4), c, 0, .5, 0), roof);
    g.add(at(new THREE.Mesh(new THREE.PlaneGeometry(.7, .6), glow(c, .5)), 0, .32, .71));
    return g;
  },
  truck(c) {
    const g = grp(solid(new THREE.BoxGeometry(1.4, .7, .7), c, -.2, .55, 0), solid(new THREE.BoxGeometry(.5, .55, .7), c, .75, .47, 0));
    [-.6, .2, .75].forEach(x => [-.36, .36].forEach(z => g.add(at(new THREE.Mesh(new THREE.TorusGeometry(.14, .05, 8, 20), glow(c)), x, .17, z))));
    return g;
  },
  ship(c) {
    const hull = new THREE.Shape(); hull.moveTo(-1.2, .4); hull.lineTo(1.3, .4); hull.lineTo(.9, 0); hull.lineTo(-1, 0); hull.lineTo(-1.2, .4);
    const g = grp(solid(new THREE.ExtrudeGeometry(hull, {depth: .7, bevelEnabled: false}), c, 0, 0, -.35));
    [-.5, 0, .5].forEach((x, k) => g.add(solid(new THREE.BoxGeometry(.4, .35, .5), [COL.amber, COL.teal, COL.purple][k], x, .58, 0)));
    g.add(solid(new THREE.BoxGeometry(.3, .6, .4), c, -.95, .7, 0));
    return g;
  },
  plane(c) {
    const f = solid(new THREE.CylinderGeometry(.18, .12, 2, 16), c, 0, 0, 0); f.rotation.z = Math.PI / 2;
    const g = grp(f, solid(new THREE.BoxGeometry(.5, .04, 2.2), c, .1, 0, 0), solid(new THREE.BoxGeometry(.25, .04, .8), c, -.85, .05, 0), solid(new THREE.BoxGeometry(.25, .45, .04), c, -.9, .25, 0));
    g.position.y = 1.2; return grp(g);
  },
  rocket(c) {
    const g = grp(solid(new THREE.CylinderGeometry(.28, .32, 1.6, 20), c, 0, 1.1, 0), solid(new THREE.ConeGeometry(.28, .6, 20), c, 0, 2.2, 0));
    [0, 1, 2].forEach(k => {const f = solid(new THREE.BoxGeometry(.04, .45, .35), c); f.position.set(Math.sin(k * 2.1) * .32, .45, Math.cos(k * 2.1) * .32); f.rotation.y = k * 2.1; g.add(f)});
    const fl = new THREE.Mesh(new THREE.ConeGeometry(.2, .6, 16), glow(COL.amber, .9)); fl.rotation.x = Math.PI; fl.position.y = .05; g.add(fl); g.userData.flame = fl;
    return grp(g);
  },
  drone(c) {
    const g = grp(solid(new THREE.BoxGeometry(.5, .15, .5), c, 0, 0, 0));
    g.userData.rotors = [[-1, -1], [1, -1], [-1, 1], [1, 1]].map(([x, z]) => {
      g.add(at(new THREE.Mesh(new THREE.BoxGeometry(.5, .03, .03), glow(c, .6)), x * .25, 0, z * .25, 0, Math.atan2(z, x)));
      const r = at(new THREE.Mesh(new THREE.TorusGeometry(.18, .015, 6, 24), glow(c)), x * .42, .06, z * .42, Math.PI / 2); g.add(r); return r;
    });
    g.position.y = 1.1; return grp(g);
  },
  train(c) {
    const g = new THREE.Group();
    [0, 1, 2].forEach(k => g.add(solid(new THREE.BoxGeometry(1, .55, .55), c, 1.1 - 1.1 * k, .45, 0)));
    g.add(at(new THREE.Mesh(new THREE.BoxGeometry(4, .03, .7), glow(c, .35)), 0, .12, 0));
    return g;
  },
  coin(c) {
    const d = solid(new THREE.CylinderGeometry(.55, .55, .12, 32), c, 0, 0, 0, 0x1d1808); d.rotation.x = Math.PI / 2;
    const g = grp(d, at(new THREE.Mesh(new THREE.TorusGeometry(.38, .025, 8, 32), glow(c)), 0, 0, .07));
    g.position.y = .8; return grp(g);
  },
  coins(c) {                                                  // a stack of coins
    const g = new THREE.Group();
    for (let k = 0; k < 6; k++) g.add(solid(new THREE.CylinderGeometry(.5, .5, .12, 28), c, (rnd(k) - .5) * .08, .07 + k * .13, 0, 0x1d1808));
    return g;
  },
  bar(c) { return grp(solid(new THREE.BoxGeometry(.5, 1, .5), c, 0, .5, 0), at(new THREE.Mesh(new THREE.BoxGeometry(.52, .04, .52), glow(c)), 0, 1, 0)) },
  arrow(c) {                                                  // pointing up
    const s = new THREE.Shape(); s.moveTo(0, 1); s.lineTo(.55, .4); s.lineTo(.2, .4); s.lineTo(.2, -.6); s.lineTo(-.2, -.6); s.lineTo(-.2, .4); s.lineTo(-.55, .4); s.lineTo(0, 1);
    return grp(solid(new THREE.ExtrudeGeometry(s, {depth: .2, bevelEnabled: false}), c, 0, .9, -.1));
  },
  shield(c) {
    const s = new THREE.Shape(); s.moveTo(0, .9); s.quadraticCurveTo(.55, .85, .7, .7); s.quadraticCurveTo(.7, -.2, 0, -.8); s.quadraticCurveTo(-.7, -.2, -.7, .7); s.quadraticCurveTo(-.55, .85, 0, .9);
    const g = grp(solid(new THREE.ExtrudeGeometry(s, {depth: .15, bevelEnabled: false}), c, 0, 1, -.08));
    g.add(at(halo(c, 2.2, .4), 0, 1, -.2)); return g;
  },
  warning(c) {
    const s = new THREE.Shape(); s.moveTo(0, .8); s.lineTo(.75, -.5); s.lineTo(-.75, -.5); s.lineTo(0, .8);
    const g = grp(solid(new THREE.ExtrudeGeometry(s, {depth: .12, bevelEnabled: false}), c, 0, 1, -.06));
    g.add(at(new THREE.Mesh(new THREE.BoxGeometry(.1, .45, .02), glow(c)), 0, 1.05, .08), at(new THREE.Mesh(new THREE.BoxGeometry(.1, .1, .02), glow(c)), 0, .7, .08));
    return g;
  },
  gear(c) {
    const s = new THREE.Shape(), n = 10;
    for (let k = 0; k <= n * 2; k++) {const a = k / (n * 2) * Math.PI * 2, r = k % 2 ? .62 : .78; k ? s.lineTo(Math.cos(a) * r, Math.sin(a) * r) : s.moveTo(r, 0)}
    const hole = new THREE.Path(); hole.absarc(0, 0, .22, 0, Math.PI * 2, true); s.holes.push(hole);
    const gs = solid(new THREE.ExtrudeGeometry(s, {depth: .18, bevelEnabled: false}), c, 0, 0, -.09);
    const g = grp(gs); g.userData.spin = gs; g.position.y = 1; return grp(g);
  },
  flask(c) {
    const pts = [[0, 0], [.55, 0], [.6, .1], [.2, .9], [.2, 1.4], [.28, 1.45]].map(([x, y]) => new THREE.Vector2(x, y));
    const g = grp(solid(new THREE.LatheGeometry(pts, 20), c, 0, 0, 0));
    g.add(new THREE.Mesh(new THREE.LatheGeometry([[0, .02], [.5, .02], [.38, .4], [0, .4]].map(([x, y]) => new THREE.Vector2(x, y)), 20), glow(COL.green, .7)));
    g.userData.bubbles = [0, 1, 2, 3].map(() => {const b = new THREE.Mesh(new THREE.SphereGeometry(.05, 8, 8), glow(COL.green)); g.add(b); return b});
    return grp(g);
  },
  battery(c) {
    const g = grp(solid(new THREE.CylinderGeometry(.35, .35, 1.3, 24), c, 0, .65, 0), solid(new THREE.CylinderGeometry(.14, .14, .12, 16), c, 0, 1.36, 0));
    g.userData.level = [0, 1, 2, 3].map(k => {const r = at(new THREE.Mesh(new THREE.CylinderGeometry(.3, .3, .22, 24), glow(COL.green, .55)), 0, .2 + k * .28, 0); g.add(r); return r});
    return grp(g);
  },
  chip(c) {
    const g = grp(solid(new THREE.BoxGeometry(1.1, .12, 1.1), c, 0, .5, 0));
    for (let k = 0; k < 5; k++) [-1, 1].forEach(sd => {
      g.add(at(new THREE.Mesh(new THREE.BoxGeometry(.05, .03, .3), glow(c, .8)), -.4 + k * .2, .46, sd * .7));
      g.add(at(new THREE.Mesh(new THREE.BoxGeometry(.3, .03, .05), glow(c, .8)), sd * .7, .46, -.4 + k * .2));
    });
    g.add(at(halo(c, 1.4, .5), 0, .57, 0, -Math.PI / 2)); return g;
  },
  pipe(c) {
    const pts = [[-1.4, .4, 0], [-.6, .4, 0], [-.3, 1, 0], [.3, 1, 0], [.6, .4, 0], [1.4, .4, 0]];
    const g = grp(tube(pts, .09, c));
    g.userData.flow = [0, 1, 2, 3].map(() => {const b = new THREE.Mesh(new THREE.SphereGeometry(.07, 8, 8), glow(0xffffff)); g.add(b); return b});
    g.userData.curve = new THREE.CatmullRomCurve3(pts.map(p => new THREE.Vector3(...p)));
    return grp(g);
  },
  tree(c) {
    const g = grp(solid(new THREE.CylinderGeometry(.08, .1, .6, 8), c, 0, .3, 0));
    [[.55, .9, .9], [.45, .7, 1.35], [.3, .5, 1.7]].forEach(([r, h, y]) => g.add(solid(new THREE.ConeGeometry(r, h, 8), COL.green, 0, y, 0)));
    return g;
  },
  mountain(c) {
    const g = new THREE.Group();
    [[0, 2.2, 1.4], [-1.1, 1.4, 1], [1.1, 1.6, 1.1]].forEach(([x, h, r]) => g.add(solid(new THREE.ConeGeometry(r, h, 5), c, x, h / 2, -.3 * Math.abs(x))));
    return g;
  },
  wave(c) {
    const g = new THREE.Group(); g.userData.lines = [];
    for (let k = 0; k < 6; k++) {
      const geo = new THREE.BufferGeometry().setFromPoints(Array.from({length: 60}, (_, i) => new THREE.Vector3(-2 + i / 59 * 4, 0, 0)));
      const l = new THREE.Line(geo, line(c, .8 - k * .1)); l.position.z = -k * .35; g.add(l); g.userData.lines.push(l);
    }
    return grp(g);
  },
  person(c) {                                                 // the Rookie and Pro look: a glowing capsule figure
    return grp(solid(new THREE.CapsuleGeometry(.22, .6, 6, 12), c, 0, .75, 0), solid(new THREE.SphereGeometry(.2, 16, 12), c, 0, 1.45, 0));
  },
  dragon(c) {                                                 // a neon dragon in profile: horned head, bat wings with glowing spars, spade tail
    const g = new THREE.Group(), b = solid(new THREE.SphereGeometry(.5, 18, 12), c, 0, 0, 0); b.scale.set(1.7, .75, .7);
    const neck = [[.7, .15, 0], [1.15, .55, 0], [1.4, .95, 0]], tail = [[-.75, 0, 0], [-1.4, -.2, 0], [-2.1, 0, 0], [-2.6, .35, 0]];
    const sk = (pts, r) => new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map(p => new THREE.Vector3(...p))), 30, r, 8), body(0x12161b, c));
    const head = solid(new THREE.BoxGeometry(.6, .26, .28), c, 1.68, 1.02, 0); head.rotation.z = -.25;
    const horn = z => {const h = solid(new THREE.ConeGeometry(.05, .32, 6), c, 1.42, 1.25, z); h.rotation.z = .9; return h};
    const spade = solid(new THREE.ConeGeometry(.16, .3, 4), c, -2.72, .45, 0); spade.rotation.z = .9;
    const leg = (x, z) => solid(new THREE.CylinderGeometry(.06, .05, .5, 6), c, x, -.45, z);
    const eye = at(new THREE.Mesh(new THREE.SphereGeometry(.04, 8, 8), glow(COL.amber)), 1.8, 1.1, .15);
    g.add(b, sk(neck, .14), sk(tail, .1), curveLine(neck, c), curveLine(tail, c), head, horn(.09), horn(-.09), spade, eye,
      leg(.45, .2), leg(.45, -.2), leg(-.45, .2), leg(-.45, -.2));
    const wing = sd => {                                      // the membrane between three finger spars, hinged at the shoulder
      const w = new THREE.Group(), tips = [[.7, 2.3], [-.4, 2.1], [-1.3, 1.6]], s = new THREE.Shape();
      s.moveTo(0, 0); tips.forEach(([x, y], k) => {s.lineTo(x, y); if (k < 2) s.lineTo((x + tips[k + 1][0]) / 2 - .05, (y + tips[k + 1][1]) / 2 - .45)}); s.lineTo(-1.1, .1); s.lineTo(0, 0);
      const m = new THREE.Mesh(new THREE.ShapeGeometry(s), new THREE.MeshBasicMaterial({color: c, transparent: true, opacity: .16, side: THREE.DoubleSide, depthWrite: false, toneMapped: false}));
      w.add(m, edges(new THREE.ShapeGeometry(s), c, .8));
      tips.forEach(([x, y]) => w.add(curveLine([[0, 0, 0], [x * .5, y * .55, 0], [x, y, 0]], c, 3)));
      w.rotation.x = -Math.PI / 2 * sd; w.position.set(.25, .3, .25 * sd); return w;
    };
    g.userData.wings = [wing(1), wing(-1)]; g.add(...g.userData.wings);
    return grp(g);
  },
  bird(c) { const d = PROPS.dragon(c); d.children[0].scale.setScalar(.6); return d },   // a griffin or any winged thing
  fish(c) {                                                   // a fish or whale: a long body and a beating tail
    const b = solid(new THREE.SphereGeometry(.5, 16, 12), c, 0, 0, 0); b.scale.set(2, .7, .7);
    const s = new THREE.Shape(); s.moveTo(0, 0); s.lineTo(-.6, .5); s.lineTo(-.45, 0); s.lineTo(-.6, -.5); s.lineTo(0, 0);
    const tail = solid(new THREE.ShapeGeometry(s), c, -.95, 0, 0); const g = grp(b, tail); g.userData.tail = tail;
    g.position.y = 1.2; return grp(g);
  },
};
export const PROP_NAMES = Object.keys(PROPS);

function floor() {
  const g = new THREE.Group();
  const grid = new THREE.GridHelper(40, 40, COL.teal, COL.teal);
  grid.material.transparent = true; grid.material.opacity = .13; grid.material.toneMapped = false; g.add(grid);
  const p = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshStandardMaterial({color: 0x07090a, roughness: .95, metalness: .1}));
  p.rotation.x = -Math.PI / 2; p.position.y = -.002; g.add(p);
  const dust = new THREE.Group();                             // (drifting motes: the air has depth)
  for (let k = 0; k < 60; k++) {const m = new THREE.Mesh(new THREE.SphereGeometry(.025, 6, 6), glow(k % 3 ? COL.teal : COL.purple, .5)); m.userData.k = k; dust.add(m)}
  g.add(dust); g.userData.dust = dust;
  return g;
}

const C = p => COL[(p || {}).color] || COL.teal;
function make(p, fit = 2) {                                 // a prop, scaled so its biggest side is `fit` units (nothing giant, nothing lost)
  const f = PROPS[(p || {}).p] || PROPS.crate, o = f(C(p)), b = new THREE.Box3().setFromObject(o), z = b.getSize(new THREE.Vector3());
  const k = fit / Math.max(z.x, z.y, z.z, .01), g = grp(o); o.scale.setScalar(k); o.position.y -= b.min.y * k; g.userData.prop = p; return g;
}
function pop(o, u0, u) {                                     // pops in on its word (scale with a little overshoot)
  const a = u0 == null ? 1 : back(seg(u, u0 - .05, u0 + .45)); o.scale.setScalar(Math.max(.0001, a)); return a;
}
function idle(o, u, k) {                                     // what each prop does while it stands there
  const D = o.children[0]?.children[0]?.userData || o.children[0]?.userData || {};
  if (D.sparks) D.sparks.forEach(s => {const an = s.userData.k / 6 * Math.PI * 2 + u * 1.4; s.position.set(Math.cos(an), Math.sin(an), 0)});
  if (D.wings) D.wings.forEach((w, j) => {w.rotation.x = (j ? 1 : -1) * (Math.PI / 2 - .5 - .7 * Math.sin(u * 4.5 + k))});
  if (D.spin) D.spin.rotation.z = u * .8;
  if (D.rotors) D.rotors.forEach(r => r.rotation.z = u * 20);
  if (D.flame) D.flame.scale.y = 1 + .25 * Math.sin(u * 30);
  if (D.tail) D.tail.rotation.y = .4 * Math.sin(u * 4);
  if (D.smoke) D.smoke.forEach((r, j) => {const q = (u * .5 + j / 3) % 1; r.position.set(.7, 1.7 + q * 1.4, -.3); r.scale.setScalar(.6 + q * 1.6); r.material.opacity = .6 * (1 - q)});
  if (D.bubbles) D.bubbles.forEach((b, j) => {const q = (u * .6 + j / 4) % 1; b.position.set(Math.sin(j * 2) * .15, .1 + q * 1.3, Math.cos(j * 2) * .15)});
  if (D.level) D.level.forEach((r, j) => r.visible = j <= Math.floor((u * 1.5) % 5) - 1);
  if (D.flow) D.flow.forEach((b, j) => b.position.copy(D.curve.getPointAt((u * .35 + j / 4) % 1)));
  if (D.lines) D.lines.forEach((l, j) => {const p = l.geometry.attributes.position; for (let i = 0; i < p.count; i++) p.setY(i, .25 * Math.sin(p.getX(i) * 2.2 + u * 2 + j * .6) + .3); p.needsUpdate = true});
}
function lights(G, a = COL.teal, b = COL.purple) {
  const L1 = new THREE.PointLight(a, 5, 9); L1.position.set(-2, 2.5, 2);
  const L2 = new THREE.PointLight(b, 5, 9); L2.position.set(2, 2.5, -1);
  G.add(L1, L2, new THREE.AmbientLight(0x223040, .7), new THREE.HemisphereLight(0x4fc6c8, 0x080a0b, .35));
}
const orbitCam = (u, d, r0, r1, an0, an1, y, ty) => {const q = io(seg(u, 0, d)), an = an0 + (an1 - an0) * seg(u, 0, d), r = r0 + (r1 - r0) * q;
  cam.position.set(Math.sin(an) * r, y + .3 * seg(u, 0, d), Math.cos(an) * r); cam.lookAt(0, ty, 0)};
const when = (p, s) => p && p.t != null ? p.t - Math.max(0, s.t0) : null;

// ---- layouts: build once, then pose for u (seconds into the scene); the props come from the writer
const SLOTS = [[-2, -.8], [2, -.8], [-1.3, -2.4], [1.3, -2.4], [0, -3.2]];
const FLIERS = ['dragon', 'bird', 'fish', 'plane', 'drone', 'rocket'];
const LAYOUTS = {
  flow(s) {   // props: the stations left to right (2 or 3), then the thing that travels (repeats along the route)
    const P = s.props || [], st = P.slice(0, Math.max(1, P.length - 1)).slice(0, 3), mover = P.length > 1 ? P[P.length - 1] : {p: 'crate', color: 'amber'};
    const G = new THREE.Group(); G.add(floor()); lights(G, C(st[0]), C(st[st.length - 1]));
    const n = st.length, xs = st.map((_, k) => n === 1 ? 0 : -1.5 + 3 * k / (n - 1)), zs = st.map((_, k) => -k * .6);
    const S0 = st.map((p, k) => {const o = make(p, p.p === 'portal' ? 3 : 2.2); o.position.set(xs[k], 0, zs[k]); if (p.p === 'portal') o.rotation.y = Math.PI / 2 - .55; G.add(o);
      const h = halo(C(p), 2.4, .45); h.rotation.x = -Math.PI / 2; h.position.set(xs[k], .01, zs[k]); G.add(h); return o});
    const portals = n > 1 && st.every(p => p.p === 'portal');
    const M = [0, 1, 2, 3].map(() => {const o = make(mover, .8); G.add(o); return o});
    return {G, labels: () => S0.map((o, k) => ({o, y: 3.3, p: st[k]})).concat([{o: M.find(m => m.visible) || M[0], y: 1.4, p: mover}]), pose(u) {
      S0.forEach((o, k) => {pop(o, when(st[k], s), u); idle(o, u, k)});
      const a = when(mover, s) ?? 0, L = 4.2;
      M.forEach((o, k) => {
        const q = ((Math.max(0, u - a) * .38 + k / M.length)) % 1, x = -L + 2 * L * q;
        let z = 0; for (let j = 0; j < n; j++) if (x > xs[j]) z = zs[j];
        const near = Math.min(...xs.map(v => Math.abs(x - v)));
        o.visible = u >= a && !(portals && x > xs[0] && x < xs[n - 1]); o.position.set(x, .05 * Math.sin(u * 3 + k), z);
        o.scale.setScalar(portals ? cl(near / .5, .05, 1) : 1); o.rotation.y = portals ? u * .6 + k : 0; idle(o, u, k);
      });
    }, cam(u, d) { orbitCam(u, d, 11.5, 10, -.22, -.06, 2.6, 1.05) }};
  },
  network(s) {   // a globe of nodes: each prop lights a node (with its label) on its word, and links fill in between
    const P = s.props || [], G = new THREE.Group(); lights(G);
    const globe = new THREE.Group(); G.add(globe);
    globe.add(new THREE.LineSegments(new THREE.WireframeGeometry(new THREE.SphereGeometry(2.1, 18, 12)), line(COL.teal, .08)));
    globe.add(halo(COL.teal, 6, .18));
    const N = Math.max(P.length, 8), nodes = [];
    for (let k = 0; k < N; k++) {                              // (evenly spread on the sphere: a Fibonacci lattice)
      const y = 1 - 2 * (k + .5) / N, r = Math.sqrt(1 - y * y), a = k * 2.39996, p = P[k];
      const m = new THREE.Group(); m.position.set(Math.cos(a) * r * 2.1, y * 2.1, Math.sin(a) * r * 2.1);
      m.add(new THREE.Mesh(new THREE.SphereGeometry(.09, 12, 12), glow(C(p))), halo(C(p), .7, .8));
      globe.add(m); nodes.push(m);
    }
    const links = []; for (let i = 0; i < N; i++) for (let j = i + 1; j < N; j++) {
      const l = new THREE.Line(new THREE.BufferGeometry().setFromPoints([nodes[i].position, nodes[j].position]), line(COL.purple, 0));
      l.userData = {i, j}; globe.add(l); links.push(l);
    }
    globe.position.y = 2.4;
    const on = k => when(P[k], s) ?? .3 + k * .35;
    return {G, labels: () => P.map((p, k) => ({o: nodes[k], y: .35, p, front: globe})), pose(u) {
      globe.rotation.y = u * .25;
      nodes.forEach((m, k) => {const a = seg(u, on(k) - .05, on(k) + .35); m.scale.setScalar(Math.max(.0001, k < P.length ? back(a) : .55 * a))});
      links.forEach(l => {const t = Math.max(on(l.userData.i), on(l.userData.j)); l.material.opacity = .45 * seg(u, t + .1, t + .6)});
    }, cam(u, d) { orbitCam(u, d, 12.5, 11, .1, -.1, 2.9, 2.4) }};
  },
  hero(s) {   // one big prop on a lit plinth, the rest orbit it, each popping in on its word
    const P = s.props || [], G = new THREE.Group(); G.add(floor()); lights(G, C(P[0]), COL.purple);
    const h = make(P[0] || {p: 'crate'}, 3.2); G.add(h);
    G.add(solid(new THREE.CylinderGeometry(1.5, 1.6, .2, 48), C(P[0]), 0, .1, 0));
    const ring = new THREE.Mesh(new THREE.TorusGeometry(2.4, .02, 8, 96), glow(C(P[0]), .6)); ring.rotation.x = Math.PI / 2; ring.position.y = .05; G.add(ring);
    const sat = P.slice(1, 6).map(p => {const o = make(p, 1.3); G.add(o); return o});
    return {G, labels: () => [{o: h, y: 3.6, p: P[0]}].concat(sat.map((o, k) => ({o, y: 1.6, p: P[k + 1]}))), pose(u) {
      pop(h, when(P[0], s), u); idle(h, u, 0);
      if (FLIERS.includes((P[0] || {}).p)) {const an = u * .55;   // (a flier circles above the plinth, side-on, banking into the turn)
        h.position.set(Math.cos(an) * 1.6, 1.3 + .2 * Math.sin(u * 2), Math.sin(an) * 1.6); h.rotation.set(0, -an - Math.PI, -.25)}
      else {h.position.y = .2; h.rotation.y = u * .35}
      sat.forEach((o, k) => {const [x, z] = SLOTS[k]; pop(o, when(P[k + 1], s), u);   // (beside and behind the hero: never in front of it)
        o.position.set(x, .25 + .15 * Math.sin(u * 2 + k), z); o.rotation.y = u * .5 + k; idle(o, u, k + 1)});
    }, cam(u, d) { orbitCam(u, d, 12, 10.5, -.3, -.1, 3.6, 1.7) }};
  },
  grow(s) {   // good news: columns rise one by one on their words, coins rain, an arrow climbs
    const P = s.props || [], G = new THREE.Group(); G.add(floor()); lights(G, COL.green, COL.teal);
    const n = Math.max(3, Math.min(5, P.length || 4)), bars = [];
    for (let k = 0; k < n; k++) {const b = PROPS.bar(COL.green); b.position.set(-1.6 + 3.2 * k / (n - 1), 0, 0); G.add(b); bars.push(b)}
    const up = PROPS.arrow(COL.green); up.position.set(2.6, 0, .4); G.add(up);
    const coins = [0, 1, 2, 3, 4, 5].map(() => {const c = PROPS.coin(COL.amber); c.scale.setScalar(.35); G.add(c); return c});
    const on = k => when(P[k], s) ?? .4 + k * .5;
    return {G, labels: () => P.slice(0, n).map((p, k) => ({o: bars[k], y: .3, top: true, p})), pose(u) {
      bars.forEach((b, k) => {const a = out(seg(u, on(k), on(k) + .8)); b.scale.set(1, Math.max(.001, a * (1 + k * .55)), 1)});
      up.position.y = .3 + .4 * out(seg(u, on(n - 1), on(n - 1) + 1)); up.rotation.y = u * .8;
      coins.forEach((c, k) => {const q = ((u * .5 + rnd(k)) % 1); c.position.set(-1.8 + rnd(k + 9) * 3.6, 4.2 - q * 4.2, (rnd(k + 3) - .5) * 1.5); c.rotation.y = u * 3 + k});
    }, cam(u, d) { orbitCam(u, d, 10.5, 9.2, .25, .05, 2.8, 1.5) }};
  },
  risk(s) {   // bad news: the company (props[0]) stands lit red, warnings fly in and hit it on their words
    const P = s.props || [], G = new THREE.Group(); G.add(floor()); lights(G, COL.red, COL.amber);
    const h = make(P[0] || {p: 'building', color: 'teal'}, 3); G.add(h);
    const hits = P.slice(1, 4).map(p => {const o = make(p.p ? p : Object.assign({p: 'warning', color: 'red'}, p), 1.5); o.add(at(halo(C(p), 2.2, .5), 0, .8, -.2)); G.add(o); return o});
    const flash = halo(COL.red, 7, 0); flash.position.set(0, 1.5, .5); G.add(flash);
    const on = k => when(P[k + 1], s) ?? .6 + k * .9;
    return {G, labels: () => [{o: h, y: 3.6, p: P[0]}].concat(hits.map((o, k) => ({o, y: 2.4, p: P[k + 1]}))), pose(u) {
      idle(h, u, 0); let shake = 0, f = 0;
      hits.forEach((o, k) => {const q = seg(u, on(k) - .5, on(k)), tx = [-2.2, 2.2, 0][k], tz = [1.2, 1, 1.8][k];
        o.visible = u >= on(k) - .5; o.position.set(tx * (1 + 2 * (1 - out(q))), (1 - out(q)) * 3, tz); o.rotation.y = (1 - q) * 3; idle(o, u, k);
        const hit = seg(u, on(k), on(k) + .5), live = u >= on(k) ? 1 - hit : 0; shake += live; f = Math.max(f, live)});
      h.rotation.z = .05 * Math.sin(u * 40) * shake + .06 * seg(u, on(0), on(0) + 2);
      flash.material.opacity = .5 * f;
    }, cam(u, d) { orbitCam(u, d, 10, 8.5, -.15, .12, 2.9, 1.5) }};
  },
  compare(s) {   // the old way (grey, slow, winding) beside the new way (neon, fast): props[0] old, props[1] new, props[2] what moves
    const P = s.props || [], G = new THREE.Group(); G.add(floor()); lights(G, COL.grey, C(P[1] || {color: 'teal'}));
    const mover = P[2] || {p: 'crate', color: 'amber'};
    const L = make(Object.assign({}, P[0] || {p: 'truck'}, {color: 'grey'}), 2), Rr = make(P[1] || {p: 'portal', color: 'teal'}, 2.6);
    L.position.set(-1.8, 0, 0); Rr.position.set(1.8, 0, 0); if ((P[1] || {}).p === 'portal') Rr.rotation.y = .5; G.add(L, Rr);
    const slow = make(Object.assign({}, mover, {color: 'grey'}), .6), fast = make(mover, .6); G.add(slow, fast);
    const path = new THREE.CatmullRomCurve3([[-3, 0, 2], [-1.4, 0, 1.2], [-2.4, 0, .2], [-1, 0, -.8], [-2.2, 0, -2]].map(p => new THREE.Vector3(...p)));
    G.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(path.getPoints(80)), line(COL.grey, .6)));
    const div = new THREE.Mesh(new THREE.PlaneGeometry(.03, 3), glow(COL.white, .12)); div.position.set(0, 1.5, 0); G.add(div);
    return {G, labels: () => [{o: L, y: 2.6, p: P[0]}, {o: Rr, y: 3.4, p: P[1]}], pose(u) {
      pop(L, when(P[0], s), u); pop(Rr, when(P[1], s), u); idle(L, u, 0); idle(Rr, u, 1);
      slow.position.copy(path.getPointAt((u * .08) % 1)); slow.position.y = .05;
      const q = (u * .6) % 1; fast.position.set(1.8 + (q - .5) * 3, .05, 1.2); fast.visible = Math.abs(q - .5) > .08;
    }, cam(u, d) { orbitCam(u, d, 14, 12.5, -.05, .05, 3.6, 1.2) }};
  },
};
export const LAYOUT_NAMES = Object.keys(LAYOUTS);

export async function drawWorld(canvas, s, t) {
  if (!R) setup(canvas);
  if (built !== s) {
    if (parts.G) scene.remove(parts.G);
    parts = (LAYOUTS[s.layout] || LAYOUTS.hero)(s); scene.add(parts.G); built = s;
  }
  const u = t - Math.max(0, s.t0), d = Math.max(1, s.t1 - Math.max(0, s.t0));
  const fl = parts.G.children[0]?.userData?.dust;
  if (fl) fl.children.forEach(m => {const k = m.userData.k; m.position.set((rnd(k) - .5) * 14, (rnd(k + 50) * 5 + u * .15 * (1 + rnd(k + 9))) % 5, (rnd(k + 99) - .5) * 10)});
  parts.pose(u); parts.cam(u, d); parts.G.updateMatrixWorld(true); cam.updateMatrixWorld();
  comp.render();
  const v = new THREE.Vector3(), box = new THREE.Box3();     // the labels, in screen pixels (reel.html draws them as text)
  const c0 = new THREE.Vector3(), n0 = new THREE.Vector3();
  const facing = x => {if (!x.front) return true; x.front.getWorldPosition(c0); x.o.getWorldPosition(n0); return n0.sub(c0).dot(cam.position.clone().sub(c0)) > 0};
  return (parts.labels ? parts.labels() : []).filter(x => x.p && x.p.label && x.o.visible !== false && x.o.scale.x > .3 && facing(x)).map(x => {
    if (x.top) {box.setFromObject(x.o); v.set((box.min.x + box.max.x) / 2, box.max.y + x.y, (box.min.z + box.max.z) / 2)}
    else {x.o.getWorldPosition(v); v.y += x.y}
    v.project(cam);
    return {text: x.p.label, x: (v.x + 1) / 2 * W, y: (1 - v.y) / 2 * H, color: '#' + C(x.p).toString(16).padStart(6, '0')};
  });
}
