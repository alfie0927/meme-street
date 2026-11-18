// DEVICE: a rowing boat on water with a stick trader standing in it. Every trade drills a hole; water jets in and the
// level rises while the HUD counts trades and fees; the trader bails, then panics as the boat tilts; corks plug the holes
// one by one and the water drains. Palette: cold white and ice blue on a blue-black night, red for the holes.
({t, T, s, i, R, api}) => {
  const {seg, cl, io, out, back, esc, punch, at, fig, boomFx} = api;
  if (s.kind === 'big' || s.kind === 'outro') return '';           // the big line and the end card stand alone
  const S = R.scenes, W = '#eef3ff', B = '#6fa8ff', RD = '#ff5c6c', DK = '#0a0c14';
  const t1 = S[1] || s, t2 = S[2] || s, t3 = S[3] || s;
  const nHoles = 20, hx = q => 300 + q * 27, hy = q => 1118 - 10 * Math.sin(Math.PI * (q + .5) / nHoles);   // along the hull's belly
  // how many holes so far: one on 'drills' in scene 0, the rest one by one through 'Twenty trades a day'
  const tDrill = at(S[0], 'drills'), tTw0 = at(t1, 'Twenty'), tTw1 = at(t1, 'but every') || tTw0 + 2.5;
  const holeAt = q => q === 0 ? tDrill : tTw0 + (q - 1) * ((tTw1 - tTw0) / (nHoles - 1));
  let holes = 0; for (let q = 0; q < nHoles; q++) if (t >= holeAt(q)) holes = q + 1;
  // corks: from 'plug the holes' in scene 3, one every 0.12 s
  const tPlug = at(t3, 'plug the holes'), corkAt = q => tPlug + q * .12;
  let corks = 0; if (i >= 3) for (let q = 0; q < nHoles; q++) if (t >= corkAt(q)) corks = q + 1;
  const open = Math.max(0, holes - corks);
  // the water inside: rises with open holes over time (scene 1 and 2), drains in scene 3
  let level = 0;                                                  // 0 dry .. 1 at the gunwale
  if (i >= 1) level = cl(seg(t, tTw0, t2.t1 - .3)) * (.35 + .65 * cl(holes / nHoles));
  if (i >= 3) level *= 1 - io(seg(t, tPlug + .6, tPlug + 2.4));
  const tilt = -7 * io(seg(t, t2.t0 + .2, t2.t0 + 1.2)) * (1 - io(seg(t, tPlug + .4, tPlug + 1.6)));
  const bob = 3 * Math.sin(t * 1.4), deck = 1010 + bob + 18 * level;   // the boat sits lower as it fills
  let g = '';
  // sky and the moon
  g += `<rect x="0" y="520" width="1080" height="770" fill="${DK}"/>`;
  for (let k = 0; k < 18; k++) g += `<circle cx="${(k * 173) % 1040 + 20}" cy="${540 + (k * 97) % 380}" r="${k % 3 ? 2 : 3}" fill="${W}" opacity="${(.25 + .3 * (.5 + .5 * Math.sin(t * 1.1 + k))).toFixed(2)}"/>`;
  g += `<circle cx="860" cy="640" r="54" fill="${W}" opacity=".9"/>`;
  // the open water, three wave bands
  for (let b = 0; b < 3; b++) { let d = `M-40 ${1090 + b * 60}`; for (let x = -40; x <= 1120; x += 40) d += ` Q${x + 20} ${1090 + b * 60 - 14 * Math.sin(t * 1.6 + x / 90 + b)} ${x + 40} ${1090 + b * 60}`;
    g += `<path d="${d} L1120 1300 L-40 1300 Z" fill="${B}" opacity="${(.22 + .16 * b).toFixed(2)}"/>`; }
  // the boat (tilted group): hull, the water inside it, the holes with their jets, the corks, the trader
  const hull = `M250 ${1000} Q300 1150 540 1150 Q780 1150 830 1000 Z`;
  g += `<g transform="translate(540 ${deck.toFixed(1)}) rotate(${tilt.toFixed(2)}) translate(-540 -1010)">`;
  g += `<defs><clipPath id="hullc"><path d="${hull}"/></clipPath></defs>`;
  g += `<path d="${hull}" fill="#141a26" stroke="${W}" stroke-width="8" stroke-linejoin="round"/>`;
  g += `<rect x="240" y="${(1150 - 150 * level).toFixed(1)}" width="600" height="${(150 * level + 10).toFixed(1)}" fill="${B}" opacity=".55" clip-path="url(#hullc)"/>`;
  for (let q = 0; q < holes; q++) {
    const x = hx(q), y = hy(q), a = back(seg(t, holeAt(q), holeAt(q) + .3)), plugged = q < corks;
    if (a <= 0) continue;
    if (seg(t, holeAt(q), holeAt(q) + .4) < 1) g += boomFx(x, y, seg(t, holeAt(q), holeAt(q) + .4), 70, RD);
    g += `<circle cx="${x}" cy="${y.toFixed(1)}" r="${(9 * a).toFixed(1)}" fill="${plugged ? '#c9a16b' : RD}" stroke="${plugged ? W : DK}" stroke-width="3"/>`;
    if (!plugged && t < tPlug + 3) for (let j = 0; j < 3; j++) { const f = ((t * 1.3 + j * .33 + q * .17) % 1);   // the jet: droplets up into the boat
      g += `<circle cx="${(x + 6 * Math.sin(f * 6 + q)).toFixed(1)}" cy="${(y - 10 - f * 70).toFixed(1)}" r="${(5 - 3 * f).toFixed(1)}" fill="${B}" opacity="${(.9 * (1 - f)).toFixed(2)}"/>`; }
    if (plugged) { const c = back(seg(t, corkAt(q), corkAt(q) + .3)); g += `<circle cx="${x}" cy="${y.toFixed(1)}" r="${(14 * c).toFixed(1)}" fill="none" stroke="#c9a16b" stroke-width="4" opacity="${(1 - seg(t, corkAt(q) + .3, corkAt(q) + .8)).toFixed(2)}"/>`; }
  }
  // the trader: stands, bails (arms swing left-right from 'Twenty'), panics as it tilts, happy once the corks are in
  const cues = [];
  for (let q = 0; q < 40; q++) cues.push({do: 'pose', fig: 0, pose: q % 2 ? 'pointl' : 'point', t: tTw0 + q * .55});
  cues.push({do: 'pose', fig: 0, pose: 'panic', t: t2.t0 + .3}, {do: 'pose', fig: 0, pose: 'happy', t: tPlug + 1.2});
  g += fig({pose: 'stand', color: W, label: 'You', x: 540, y: 1000, sc: 1.9, s: {cues: cues.filter(c => c.t <= t + 1 && (i >= 1 || c.pose === 'stand')), t0: -9}}, t);
  g += `</g>`;
  // HUD (y 380..500): trades today and fees paid, counting with the holes; green when the plan is back
  const fee = 9.2, tr = i >= 3 && t >= at(t3, 'Three good trades') ? 3 : holes, col = i >= 3 && t >= at(t3, 'Three good trades') ? '#5be39a' : (open ? RD : W);
  g += `<text x="90" y="420" font-size="28" font-weight="700" fill="${B}" letter-spacing="2">TRADES TODAY</text><text x="90" y="486" font-size="60" font-weight="800" fill="${col}">${tr}</text>`;
  g += `<text x="990" y="420" text-anchor="end" font-size="28" font-weight="700" fill="${B}" letter-spacing="2">FEES PAID</text><text x="990" y="486" text-anchor="end" font-size="60" font-weight="800" fill="${col}">£${Math.round(tr * fee * (tr === 3 ? 1 : Math.max(1, cl(seg(t, tTw0, t2.t1)) * 1.4)))}</text>`;
  return `<svg style="position:absolute;left:0;top:0" width="1080" height="1920">${g}</svg>` + punch(s, t);
}
