// "I put $1,000 in this stock": a 3D stack of $100 bills on a table under a lamp. As the real price line draws, bills drop onto
// the stack (it rises) or lift off and burn away (it falls); a counter rolls. Every frame is a pure function of t.
// window.__R = {T, prices, run: [t0, t1], name, end: {t, lines}, caps, cover}
const T3 = THREE, R = window.__R, W = 1080, H = 1920, Q = window.__Q || 2 / 3, F = 'Montserrat, sans-serif';
const cl = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x)), ease = x => 1 - Math.pow(1 - cl(x), 3), back = x => { x = cl(x); const k = 1.7; return 1 + (k + 1) * Math.pow(x - 1, 3) + k * Math.pow(x - 1, 2); };
const hs = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const rn = new T3.WebGLRenderer({canvas: document.getElementById('gl'), antialias: Q >= 1, preserveDrawingBuffer: true}); rn.setSize(Math.round(W * Q), Math.round(H * Q), false); rn.setPixelRatio(1);
rn.shadowMap.enabled = true; rn.shadowMap.type = T3.PCFSoftShadowMap; T3.ColorManagement.legacyMode = false; rn.outputEncoding = T3.sRGBEncoding; rn.toneMapping = T3.ACESFilmicToneMapping;
const scene = new T3.Scene(), cam = new T3.PerspectiveCamera(34, W / H, .05, 100), ox = document.getElementById('c').getContext('2d');
scene.background = new T3.Color('#120d0a');
const M = (col, o = {}) => new T3.MeshStandardMaterial(Object.assign({color: col, roughness: .7}, o));
// the room: a dark wood table, a warm lamp from above, a dim back wall
const wood = (() => { const c = document.createElement('canvas'); c.width = 512; c.height = 512; const x = c.getContext('2d'); x.fillStyle = '#3a2414'; x.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 70; i++) { x.strokeStyle = `rgba(${30 + hs(i) * 40},${15 + hs(i + 1) * 20},8,.5)`; x.lineWidth = 1 + hs(i + 2) * 3; x.beginPath(); x.moveTo(0, hs(i + 3) * 512); x.bezierCurveTo(170, hs(i + 4) * 512, 340, hs(i + 5) * 512, 512, hs(i + 6) * 512); x.stroke(); }
  const t = new T3.CanvasTexture(c); t.encoding = T3.sRGBEncoding; t.wrapS = t.wrapT = T3.RepeatWrapping; t.repeat.set(5, 5); return t; })();
const table = new T3.Mesh(new T3.PlaneGeometry(20, 20), new T3.MeshStandardMaterial({map: wood, roughness: .55})); table.rotation.x = -Math.PI / 2; table.receiveShadow = true; scene.add(table);
const wall = new T3.Mesh(new T3.PlaneGeometry(30, 20), M("#1c1410")); wall.position.set(0, 6, -6); scene.add(wall);
scene.add(new T3.HemisphereLight('#ffe2b8', '#1a120c', .35));
const lamp = new T3.SpotLight('#ffd9a0', 3.2, 20, .55, .5, 1.2); lamp.position.set(.8, 7, 2.5); lamp.target.position.set(0, 0, 0); lamp.castShadow = true; lamp.shadow.mapSize.set(2048, 2048); lamp.shadow.bias = -.0003; scene.add(lamp, lamp.target);
const fireL = new T3.PointLight('#ff7a2a', 0, 6, 2); fireL.position.set(0, 2, 1); scene.add(fireL);
// a bill: a thin box with a drawn face
const billT = (() => { const c = document.createElement('canvas'); c.width = 1024; c.height = 440; const x = c.getContext('2d'); x.fillStyle = '#d9e6cf'; x.fillRect(0, 0, 1024, 440);
  x.strokeStyle = '#4c6b45'; x.lineWidth = 14; x.strokeRect(20, 20, 984, 400); x.lineWidth = 3; x.strokeRect(48, 48, 928, 344);
  x.fillStyle = '#c9d9bd'; x.beginPath(); x.ellipse(512, 220, 150, 170, 0, 0, 7); x.fill(); x.strokeStyle = '#6f8f66'; x.lineWidth = 5; x.stroke();
  x.fillStyle = '#4c6b45'; x.font = '900 150px Montserrat, sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText('100', 170, 120); x.fillText('100', 860, 330); x.font = '900 190px Montserrat, sans-serif'; x.fillText('$', 512, 230);
  x.font = '800 34px Montserrat, sans-serif'; x.fillText('MEME STREET RESERVE NOTE', 512, 400); const t = new T3.CanvasTexture(c); t.encoding = T3.sRGBEncoding; t.anisotropy = 8; return t; })();
const bG = new T3.BoxGeometry(2.6, .018, 1.12), bMats = [M('#c9d9bd'), M('#c9d9bd'), new T3.MeshStandardMaterial({map: billT, roughness: .8}), M('#b9caa9'), M('#c9d9bd'), M('#c9d9bd')];
// the stack: 60 bills max (each = $100 of a $1,000 start: 10 bills at start), placed with a little scatter
const MAXB = 150, UNIT = 10, bills = [];      // (each bill is $10 of the $1,000: a real tower that grows and shrinks)
 for (let i = 0; i < MAXB; i++) { const b = new T3.Mesh(bG, bMats); b.castShadow = b.receiveShadow = true; b.userData.rest = [(hs(i) - .5) * .06, .01 + i * .021, (hs(i + 9) - .5) * .05, (hs(i + 3) - .5) * .08]; scene.add(b); bills.push(b); }
// the value along the run
const P = R.prices, n = P.length - 1, valAt = t => { const k = cl((t - R.run[0]) / (R.run[1] - R.run[0])) * n, i = Math.floor(k), f = k - i; return 1000 * (P[i] + ((P[Math.min(n, i + 1)] || P[i]) - P[i]) * f) / P[0]; };
const countAt = t => Math.max(1, Math.min(MAXB, Math.round(valAt(t) / UNIT)));
// when did each bill arrive and when did it go (from the count over time): a bill i is present while count > i
const STEP = 1 / 30, events = []; { let prev = countAt(0); for (let t = 0; t <= R.T; t += STEP) { const c = countAt(t); if (c !== prev) { if (c > prev) for (let i = prev; i < c; i++) events.push([i, t, 'in']); else for (let i = prev - 1; i >= c; i--) events.push([i, t, 'out']); prev = c; } } }
function billState(i, t) { let st = i < countAt(0) ? ['here', -9] : ['gone', -9]; for (const [j, et, k] of events) { if (et > t) break; if (j === i) st = [k === 'in' ? 'here' : 'gone', et, k]; } return st; }
// embers: a pure function of the time since a bill went
function frame(t) {
  let burning = 0;
  bills.forEach((b, i) => { const [st, et, kind] = billState(i, t), [rx, ry, rz, rr] = b.userData.rest, d = t - et;
    if (st === 'here') { b.visible = true; const drop = kind === 'in' ? cl(d / .35) : 1; b.position.set(rx + (1 - drop) * (hs(i + 2) - .5) * 2, ry + (1 - ease(drop)) * 4, rz); b.rotation.set(0, rr + (1 - drop) * 2, (1 - drop) * .6); b.scale.setScalar(1); }
    else if (kind === 'out' && d < 1.4) { b.visible = true; const u = cl(d / 1.4); b.position.set(rx + Math.sin(i + d * 3) * 1.2 * u, ry + 1.6 * ease(u) + .1, rz + 1.2 * u); b.rotation.set(Math.sin(d * 4 + i) * 1.2 * u, rr + d * 3, Math.cos(d * 3 + i) * .9 * u); b.scale.setScalar(1 - .85 * u * u);
      burning = Math.max(burning, 1 - u); }
    else b.visible = false; });
  fireL.intensity = 6 * burning * (.8 + .2 * Math.sin(t * 40));
  const top = .01 + countAt(t) * .021, a = .5 + t * .1; cam.position.set(Math.sin(t * .09) * 2.2, 4.2, 12.5); cam.lookAt(0, 1.9, 0); rn.render(scene, cam);      // (the whole tower, framed between the chart above and the words below)
  ox.clearRect(0, 0, W, H);
  // embers over the picture where bills burn
  for (const [j, et, k] of events) { if (k !== 'out') continue; const d = t - et; if (d < 0 || d > 1.6) continue; if (j % 3) continue; for (let e = 0; e < 10; e++) { const s = hs(j * 31 + e), x = 540 + (s - .5) * 420 + Math.sin(d * 5 + e) * 40, y = 1050 - d * (250 + hs(e + j) * 300), r = (1 - d / 1.6) * (6 + hs(e + 2) * 10);
    ox.fillStyle = `rgba(255,${120 + hs(e) * 100},40,${1 - d / 1.6})`; ox.beginPath(); ox.arc(x, y, r, 0, 7); ox.fill(); } }
  // the chart, small, top, drawing as it goes
  const k = cl((t - R.run[0]) / (R.run[1] - R.run[0])) * n, lo = Math.min(...P), hi = Math.max(...P), cx = 120, cy = 430, cw = 840, ch = 300;
  ox.fillStyle = 'rgba(10,8,6,.72)'; ox.beginPath(); ox.roundRect(cx - 30, cy - 30, cw + 60, ch + 60, 28); ox.fill();
  ox.lineWidth = 7; ox.lineJoin = 'round'; ox.strokeStyle = valAt(t) >= 1000 ? '#2bd47d' : '#ff4d5e'; ox.beginPath(); for (let i = 0; i <= Math.floor(k); i++) { const x = cx + i / n * cw, y = cy + ch - (P[i] - lo) / (hi - lo) * ch; i ? ox.lineTo(x, y) : ox.moveTo(x, y); } ox.stroke();
  ox.fillStyle = '#ffd23f'; ox.font = `800 34px ${F}`; ox.textAlign = 'left'; ox.fillText('MYSTERY STOCK', cx, cy - 2);
  // the counter
  const v = valAt(t), up = v >= 1000; ox.textAlign = 'center'; ox.textBaseline = 'middle'; ox.lineJoin = 'round';
  const s = '$' + Math.round(v).toLocaleString('en-US'); ox.font = `900 150px ${F}`; ox.lineWidth = 26; ox.strokeStyle = '#000'; ox.strokeText(s, 540, 230); ox.fillStyle = up ? '#2bd47d' : '#ff4d5e'; ox.fillText(s, 540, 230);
  // the hook and captions
  if (t < 2.6) { const p = back(cl(t / .25)); ox.save(); ox.translate(540, 1500); ox.scale(p, p); ox.font = `900 88px ${F}`; ox.lineWidth = 18; ox.strokeStyle = '#000'; ['I PUT $1,000', 'IN THIS STOCK'].forEach((l, i) => { ox.strokeText(l, 0, i * 104); ox.fillStyle = i ? '#ffd23f' : '#fff'; ox.fillText(l, 0, i * 104); }); ox.restore(); }
  const cap = (R.caps || []).find(q => t >= q.t0 && t < q.t1); if (cap) { const p = back(cl((t - cap.t0) / .2)); ox.save(); ox.translate(540, 1540); ox.scale(p, p); ox.font = `900 ${cap.size || 92}px ${F}`; ox.lineWidth = 18; ox.strokeStyle = '#000'; ox.strokeText(cap.text, 0, 0); ox.fillStyle = cap.hot ? '#ffd23f' : '#fff'; ox.fillText(cap.text, 0, 0); ox.restore(); }
  const E = R.end; if (E && t >= E.t) { const a = cl((t - E.t) / .3); ox.fillStyle = `rgba(8,6,4,${.9 * a})`; ox.fillRect(0, 0, W, H); ox.globalAlpha = a; ox.font = `900 76px ${F}`; ox.fillStyle = '#fff'; ox.fillText('IT WAS', 540, 640);
    ox.font = `900 ${Math.round(124 * back(cl((t - E.t - .15) / .3)))}px ${F}`; ox.lineWidth = 20; ox.strokeStyle = '#000'; ox.strokeText(R.name, 540, 780); ox.fillStyle = '#ffd23f'; ox.fillText(R.name, 540, 780);
    ox.font = `800 50px ${F}`; ox.fillStyle = '#fff'; E.lines.forEach((l, i) => ox.fillText(l, 540, 960 + i * 80)); ox.fillStyle = '#4cc3cc'; ox.beginPath(); ox.roundRect(190, 1260, 700, 130, 65); ox.fill(); ox.fillStyle = '#04161a'; ox.font = `900 64px ${F}`; ox.fillText('memestreet.net', 540, 1328); ox.globalAlpha = 1; }
}
function cover() { const C = R.cover || {}; frame(C.t || 8); ox.clearRect(0, 1350, W, 570); ox.textAlign = 'center'; ox.textBaseline = 'middle'; ox.lineJoin = 'round'; ox.font = `900 120px ${F}`; ox.lineWidth = 24; ox.strokeStyle = '#000';
  ox.save(); ox.translate(540, 1520); ox.rotate(-.04); ox.strokeText('WATCH MY', 0, 0); ox.fillStyle = '#fff'; ox.fillText('WATCH MY', 0, 0); ox.strokeText('$1,000 BURN', 0, 140); ox.fillStyle = '#ff4d5e'; ox.fillText('$1,000 BURN', 0, 140); ox.restore(); }
window.render = t => window.__coverOn ? cover() : frame(t);
window.overlaps = () => [];
window.ready = document.fonts.load(`900 40px ${F}`).then(() => document.fonts.load(`800 40px ${F}`)).then(() => { billT.needsUpdate = true; frame(0); return true; });
