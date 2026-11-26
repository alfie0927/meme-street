// POV: a real stock chart as a rollercoaster. The track is the price line (smoothed, the peak and the low kept); the ride is
// physics (a chain lift up the climb, gravity down the drops); a price HUD rides along. window.__R = {T, prices, ride: [t0, t1],
// caps: [{t0, t1, text, hot}], end: {t, name, lines}, cover}
const T3 = THREE, R = window.__R, W = 1080, H = 1920, Q = window.__Q || 2 / 3, F = 'Montserrat, sans-serif';
const cl = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x)), ease = x => 1 - Math.pow(1 - cl(x), 3), back = x => { x = cl(x); const k = 1.7; return 1 + (k + 1) * Math.pow(x - 1, 3) + k * Math.pow(x - 1, 2); };
const hs = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const rn = new T3.WebGLRenderer({canvas: document.getElementById('gl'), antialias: Q >= 1, preserveDrawingBuffer: true}); rn.setSize(Math.round(W * Q), Math.round(H * Q), false); rn.setPixelRatio(1);
rn.shadowMap.enabled = true; T3.ColorManagement.legacyMode = false; rn.outputEncoding = T3.sRGBEncoding; rn.toneMapping = T3.ACESFilmicToneMapping; rn.toneMappingExposure = 1.05;
const scene = new T3.Scene(), cam = new T3.PerspectiveCamera(62, W / H, .1, 2500), ox = document.getElementById('c').getContext('2d');
const M = (col, o = {}) => new T3.MeshStandardMaterial(Object.assign({color: col, roughness: .7}, o));

// the sky: a gradient dome, a low sun, soft clouds
const skyT = (() => { const c = document.createElement('canvas'); c.width = 8; c.height = 512; const x = c.getContext('2d'), g = x.createLinearGradient(0, 0, 0, 512);
  g.addColorStop(0, '#2a5bd7'); g.addColorStop(.45, '#7fb6ff'); g.addColorStop(.62, '#ffd7a8'); g.addColorStop(1, '#ffb27a'); x.fillStyle = g; x.fillRect(0, 0, 8, 512); const t = new T3.CanvasTexture(c); t.encoding = T3.sRGBEncoding; return t; })();
const skyM = new T3.Mesh(new T3.SphereGeometry(1800, 32, 16), new T3.MeshBasicMaterial({map: skyT, side: T3.BackSide, fog: false})); scene.add(skyM);
scene.fog = new T3.Fog('#ffd2b0', 300, 1600);
scene.add(new T3.HemisphereLight('#cfe6ff', '#6a8a4a', .9)); const sun = new T3.DirectionalLight('#fff1d6', 2.2); sun.position.set(-300, 400, -200); sun.castShadow = true;
Object.assign(sun.shadow.camera, {left: -400, right: 400, top: 400, bottom: -400, far: 1500}); sun.shadow.mapSize.set(2048, 2048); scene.add(sun);
const sunDisc = new T3.Mesh(new T3.CircleGeometry(60, 32), new T3.MeshBasicMaterial({color: '#fff3c4', fog: false})); sunDisc.position.set(-500, 260, -1500); sunDisc.lookAt(0, 0, 0); scene.add(sunDisc);
const ground = new T3.Mesh(new T3.PlaneGeometry(6000, 6000), M('#6fbf5a')); ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);
for (let i = 0; i < 26; i++) { const c = new T3.Group(); for (let k = 0; k < 4; k++) { const b = new T3.Mesh(new T3.SphereGeometry(20 + hs(i * 7 + k) * 16, 12, 8), new T3.MeshBasicMaterial({color: '#ffffff', fog: false, transparent: true, opacity: .9})); b.position.set(k * 26 - 40, hs(i + k) * 10, 0); c.add(b); }
  c.position.set((hs(i) - .5) * 2400, 230 + hs(i + 3) * 160, -300 - hs(i + 9) * 1200); scene.add(c); }

// the track: the price line, smoothed, as a long rising and falling coaster, a gentle S in plan
const P0 = R.prices, n = P0.length - 1, hiI = P0.indexOf(Math.max(...P0)), loI = P0.indexOf(Math.min(...P0)), keep = new Set([0, n, hiI, loI]); for (let k = 1; k < 14; k++) keep.add(Math.round(k / 14 * n));
const idx = [...keep].sort((a, b) => a - b), lo = Math.min(...P0), hi = Math.max(...P0), LEN = 2000, HGT = 130;
const pts = []; idx.forEach(i => { const u = i / n, pt = u2 => new T3.Vector3(Math.sin(u2 * Math.PI * 2.2) * 120, 6 + (P0[i] - lo) / (hi - lo) * HGT, -u2 * LEN);
  if (i === hiI) { const d = 1.6 / n; pts.push(pt(u - d).add(new T3.Vector3(0, -6, 0)), pt(u), pt(u + d).add(new T3.Vector3(0, -6, 0))); } else pts.push(pt(u)); });      // (a rounded crest, never a spike)
pts.unshift(new T3.Vector3(pts[0].x - 2, pts[0].y, 60)); pts.push(new T3.Vector3(pts[pts.length - 1].x, pts[pts.length - 1].y, -LEN - 120));
const curve = new T3.CatmullRomCurve3(pts, false, 'centripetal'), N = 2400, SP = curve.getSpacedPoints(N), FR = curve.computeFrenetFrames(N, false);
const red = '#e8394a', green = '#2bd47d';
function rail(off) { const p = SP.map((q, i) => { const t = curve.getTangentAt(i / N), side = new T3.Vector3().crossVectors(t, new T3.Vector3(0, 1, 0)).normalize(); return q.clone().addScaledVector(side, off); });
  return new T3.Mesh(new T3.TubeGeometry(new T3.CatmullRomCurve3(p), 1600, .35, 8), M('#d9dde6', {metalness: .6, roughness: .35})); }
[-1.6, 1.6].forEach(o => { const r = rail(o); r.castShadow = true; scene.add(r); });
const spine = (() => { const p = SP.map(q => q.clone().add(new T3.Vector3(0, -1.3, 0))); const m = new T3.Mesh(new T3.TubeGeometry(new T3.CatmullRomCurve3(p), 1600, .4, 8), M(red, {roughness: .4})); m.castShadow = true; return m; })(); scene.add(spine);
for (let i = 0; i < N; i += 6) { const q = SP[i], t = curve.getTangentAt(i / N), b = new T3.Mesh(new T3.BoxGeometry(3.8, .3, .6), M('#5a3a2a')); b.position.copy(q).add(new T3.Vector3(0, -.4, 0)); b.lookAt(q.clone().add(t)); scene.add(b);
  if (i % 36 === 0 && q.y > 4) { const s = new T3.Mesh(new T3.CylinderGeometry(.9, 1.2, q.y, 8), M('#f4f2ee')); s.position.set(q.x, q.y / 2 - .8, q.z); s.castShadow = true; scene.add(s); } }
// a peak flag and price signs along the way
function sign(text, col, at, h = 14) { const c = document.createElement('canvas'); c.width = 512; c.height = 200; const x = c.getContext('2d'); x.fillStyle = col; x.fillRect(0, 0, 512, 200); x.fillStyle = '#fff'; x.font = `900 110px ${F}`; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(text, 256, 104);
  const t = new T3.CanvasTexture(c); t.encoding = T3.sRGBEncoding; const m = new T3.Mesh(new T3.PlaneGeometry(26, 10), new T3.MeshBasicMaterial({map: t, side: T3.DoubleSide})); const q = curve.getPointAt(at); m.position.set(q.x + 14, q.y + h, q.z); m.lookAt(q.x + 14, q.y + h, q.z + 100); scene.add(m);
  const p = new T3.Mesh(new T3.CylinderGeometry(.4, .4, q.y + h), M('#333')); p.position.set(q.x + 14, (q.y + h) / 2, q.z - .2); scene.add(p); }
const uOfI = i => { const z = -i / n * LEN, zs = SP.map(q => q.z); let k = 0; while (k < N && zs[k] > z) k++; return k / N; };
sign('$' + P0[0].toFixed(2), '#2f7cf6', uOfI(0) + .01, 10); sign('$' + P0[hiI].toFixed(2), green, uOfI(hiI), 16); sign('$' + P0[n].toFixed(2), red, Math.min(.97, uOfI(n) - .02), 10);
// a town under it: pines and small houses
for (let i = 0; i < 260; i++) { const x = (hs(i) - .5) * 900, z = -hs(i + 1) * (LEN + 400) + 100; if (Math.abs(x - Math.sin(-z / LEN * Math.PI * 2.2) * 120) < 40) continue;
  if (i % 5) { const tr = new T3.Group(); tr.add(new T3.Mesh(new T3.CylinderGeometry(.6, .8, 4, 6), M('#6b4a2e'))); const c1 = new T3.Mesh(new T3.ConeGeometry(4.5, 11, 7), M(i % 3 ? '#2f7a45' : '#3d9152')); c1.position.y = 7; tr.add(c1); tr.position.set(x, 2, z); tr.scale.setScalar(.8 + hs(i + 4) * .9); tr.children.forEach(m => m.castShadow = true); scene.add(tr); }
  else { const hh = new T3.Group(), col = ['#f2d6a2', '#cfe6f5', '#f5c6d0', '#fff0c2'][i % 4]; const b = new T3.Mesh(new T3.BoxGeometry(14, 10, 12), M(col)); b.position.y = 5; hh.add(b); const r = new T3.Mesh(new T3.ConeGeometry(11, 7, 4), M(['#c0392b', '#2e6fa8', '#8a3a8a'][i % 3])); r.rotation.y = Math.PI / 4; r.position.y = 13.5; hh.add(r); hh.position.set(x, 0, z); hh.children.forEach(m => m.castShadow = true); scene.add(hh); } }
// the car in front of us: its nose and the lap bar
const car = new T3.Group(); const body = new T3.Mesh(new T3.BoxGeometry(3.4, .8, 3.2), M('#ffd23f', {roughness: .35})); body.position.set(0, -2.3, -4.6); car.add(body);
const nose = new T3.Mesh(new T3.CylinderGeometry(0, 1.7, 2.2, 4), M('#ffd23f', {roughness: .35})); nose.rotation.x = -Math.PI / 2; nose.rotation.y = Math.PI / 4; nose.position.set(0, -2.3, -7); nose.scale.setScalar(.8); car.add(nose);
const bar = new T3.Mesh(new T3.TorusGeometry(1.1, .12, 8, 24, Math.PI), M('#222')); bar.rotation.z = Math.PI; bar.position.set(0, -1.75, -2.2); car.add(bar);
[-1, 1].forEach(s => { const h = new T3.Mesh(new T3.BoxGeometry(.32, .9, .5), M('#f2c9a0')); h.position.set(s * .9, -1.45, -2.4); h.rotation.x = -.4; car.add(h); });
cam.add(car); scene.add(cam);

// the ride: u(t) from physics, precomputed (a chain lift on the climbs, gravity on the drops), mapped onto R.ride
const U = (() => { const out = [0]; let u = 0, v = 1.2, dt = 1 / 120; const hAt = x => curve.getPointAt(cl(x)).y, peakU = uOfI(hiI);
  while (u < 1 && out.length < 120 * 200) { const h = hAt(u), h2 = hAt(u + .0005), slope = (h2 - h) / (.0005 * LEN);
    if (slope > .02 && u < peakU + .01) v = Math.max(v, 6.5); else v = Math.max(5, v - 9.8 * slope * dt * 1.6 - .02 * v * dt);
    u += v * dt / LEN * 1.0; out.push(u); }
  return out; })();
const KP = U.findIndex(x => x >= uOfI(hiI));      // (the climb takes R.ride[0]..[1], the rest [1]..[2]: the lift is slow but never boring)
const uAt = t => { const [a, m, b] = R.ride, k = t < m ? cl((t - a) / (m - a)) * KP : KP + cl((t - m) / (b - m)) * (U.length - 1 - KP), i = Math.floor(k), f = k - i; return cl(U[i] + ((U[Math.min(U.length - 1, i + 1)] || 1) - U[i]) * f, 0, .985); };
const priceAt = u => { const z = -curve.getPointAt(u).z / LEN * n; return P0[cl(Math.round(z), 0, n)]; };

function big(s, x, y, size, fill, stroke = '#000', rot = 0) { ox.save(); ox.translate(x, y); ox.rotate(rot); ox.font = `900 ${size}px ${F}`; ox.textAlign = 'center'; ox.textBaseline = 'middle'; ox.lineJoin = 'round';
  ox.lineWidth = size * .2; ox.strokeStyle = stroke; ox.strokeText(s, 0, 0); ox.fillStyle = fill; ox.fillText(s, 0, 0); ox.restore(); }
function frame(t) {
  const u = uAt(t), p = curve.getPointAt(u), ah = curve.getPointAt(Math.min(1, u + .022)), tan = curve.getTangentAt(u);
  const upOf = v => { const w = new T3.Vector3(0, 1, 0); return w.sub(v.clone().multiplyScalar(v.y)).normalize(); }, nu = upOf(tan), au = upOf(curve.getTangentAt(Math.min(1, u + .022)));      // (the seat sits above the track's own surface: on a near-vertical climb 'up' leans with it)
  const pov = p.clone().addScaledVector(nu, 2.4), look = ah.clone().addScaledVector(au, 2.2), D0 = R.drone || 0; cam.up.copy(nu.clone().lerp(new T3.Vector3(0, 1, 0), .5).normalize());
  { const d = look.clone().sub(pov), hz = Math.hypot(d.x, d.z), mn = -Math.tan(.55) * hz; if (d.y < mn) look.y = pov.y + mn; }      // (over a crest the eye looks down the drop, never straight at the rails)      // (frame 0: a drone shot of the whole chart-shaped coaster, swooping into the seat)
  if (t < D0) { const k = ease(cl(t / D0)), top = curve.getPointAt(uOfI(hiI)), dp = new T3.Vector3(top.x + 380, top.y + 120, top.z + 420), dl = top.clone().add(new T3.Vector3(0, -40, 0));
    cam.position.copy(dp.lerp(pov, k * k)); cam.lookAt(dl.lerp(look, k * k)); car.visible = k > .85; } else { cam.position.copy(pov); cam.lookAt(look); car.visible = true; }
  const side = curve.getTangentAt(Math.min(1, u + .01)).x - tan.x; cam.rotateZ(cl(-side * 4, -.25, .25));
  const sp = (uAt(t + .05) - u) * LEN / .05; if (sp > 25) { cam.position.x += Math.sin(t * 70) * .05; cam.position.y += Math.sin(t * 53) * .05; }
  skyM.position.copy(cam.position);      // (the sky goes with us: past the far end it would be black)
  cam.fov = 62 + cl((sp - 20) / 40) * 16; cam.updateProjectionMatrix(); rn.render(scene, cam);
  ox.clearRect(0, 0, W, H);
  if (sp > 30) { ox.save(); ox.globalAlpha = cl((sp - 30) / 30) * .55; ox.strokeStyle = '#fff'; ox.lineWidth = 4; for (let i = 0; i < 40; i++) { const a = hs(i) * Math.PI * 2, r0 = 380 + hs(i + 2) * 200, r1 = r0 + 140 + hs(i + 5) * 200, s = (t * 6 + hs(i + 9)) % 1;
    ox.beginPath(); ox.moveTo(540 + Math.cos(a) * (r0 + s * 300), 1000 + Math.sin(a) * (r0 + s * 300) * 1.4); ox.lineTo(540 + Math.cos(a) * (r1 + s * 300), 1000 + Math.sin(a) * (r1 + s * 300) * 1.4); ox.stroke(); } ox.restore(); }
  // the HUD: the price as you ride it, and the change from the start
  const pr = priceAt(u), ch = (pr / P0[0] - 1) * 100, up = ch >= 0; ox.save(); ox.fillStyle = 'rgba(8,8,14,.72)'; ox.beginPath(); ox.roundRect(250, 120, 580, 190, 30); ox.fill(); ox.lineWidth = 6; ox.strokeStyle = up ? green : red; ox.stroke();
  ox.font = `800 34px ${F}`; ox.fillStyle = '#ffd23f'; ox.textAlign = 'center'; ox.fillText('MYSTERY STOCK', 540, 170); ox.font = `900 84px ${F}`; ox.fillStyle = '#fff'; ox.fillText('$' + pr.toFixed(2), 540, 250);
  ox.font = `900 44px ${F}`; ox.fillStyle = up ? green : red; ox.fillText((up ? '+' : '') + Math.round(ch) + '%', 540, 296); ox.restore();
  const cap = (R.caps || []).find(q => t >= q.t0 && t < q.t1); if (cap) { const pp = back(cl((t - cap.t0) / .18)); ox.save(); ox.translate(540, 1500); ox.scale(pp, pp); big(cap.text, 0, 0, cap.size || 96, cap.hot ? '#ffd23f' : '#fff'); ox.restore(); }
  if (t < 3.2) { big('POV:', 540, 440, 84, '#fff'); big('THIS STOCK IS A', 540, 545, 74, '#fff'); big('ROLLERCOASTER', 540, 655, 108, '#ffd23f'); }
  const E = R.end; if (E && t >= E.t) { const a = cl((t - E.t) / .3); ox.fillStyle = `rgba(6,6,14,${.9 * a})`; ox.fillRect(0, 0, W, H); ox.globalAlpha = a; big('IT WAS', 540, 640, 76, '#fff'); big(E.name, 540, 770, 120 * back(cl((t - E.t - .15) / .3)), '#ffd23f');
    E.lines.forEach((l, i) => big(l, 540, 960 + i * 90, 50, '#fff')); ox.fillStyle = '#4cc3cc'; ox.beginPath(); ox.roundRect(190, 1260, 700, 130, 65); ox.fill(); big('memestreet.net', 540, 1327, 68, '#04161a', 'rgba(0,0,0,0)'); ox.globalAlpha = 1; }
}
function cover() { const C = R.cover || {}; frame(C.t || 9); ox.clearRect(0, 330, W, 1590); ox.fillStyle = 'rgba(0,0,0,.18)'; ox.fillRect(0, 0, W, H); big('YOU BOUGHT', 540, 1380, 120, '#fff', '#000', -.04); big('AT THE TOP', 540, 1530, 130, '#ff4d5e', '#000', -.04); }
window.render = t => window.__coverOn ? cover() : frame(t);
window.overlaps = () => [];
window.ready = document.fonts.load(`900 40px ${F}`).then(() => document.fonts.load(`800 40px ${F}`)).then(() => { frame(0); return true; });
window.__dbg = () => ({U: U.length, end: U[U.length - 1], peakU: uOfI(hiI)});
