// DEVICE: a cut-away building. Gains take the stairs: the trader climbs one floor per winning day while the account
// counts up. Losses take the lift: one trade with no stop and the lift car drops seven floors in a second, with a shake.
// The payoff: a stop loss is a gate across the shaft; the car falls one floor and stops on it. Palette: warm amber and
// cream on dark brown, red for the fall.
({t, T, s, i, R, api}) => {
  const {seg, cl, io, out, back, esc, punch, at, fig, boomFx} = api;
  if (s.kind === 'big' || s.kind === 'outro') return '';
  const S = R.scenes, S1 = S[1] || s, S2 = S[2] || s, S3 = S[3] || s, S4 = S[4] || s;
  const CR = '#f3e3c0', AM = '#f0b24a', RD = '#ff5a5a', BR = '#2a1d12', LN = '#5a4330';
  const FH = 92, fy = f => 1240 - f * FH;                          // floor f's ground line (0..7)
  const stairX = 440, liftX = 740;
  // where the trader is: floor (float), x, and what the lift is doing
  let floor = 0, x = stairX, inLift = false, shake = 0, dust = 0, acct = 10000, col = CR, gate = null, replay = i >= 4;
  const tUp0 = at(S1, 'Seven winning'), tUp1 = at(S1, 'one careful step') || tUp0 + 3;
  if (i >= 1) floor = 7 * cl(seg(t, tUp0, tUp1));
  let carWait = 7;                                                  // where the empty lift waits
  if (i === 0) { const w = io(seg(t, s.t0, s.t0 + 1.4)); x = 280 + (stairX - 280) * w; carWait = 7 * io(seg(t, at(s, 'Losses take'), at(s, 'Losses take') + 1.6)); }   // the trader walks in; the lift rides up to wait at the top
  const tWalk = at(S2, 'Then one trade'), tDrop = at(S2, 'opens under');
  if (i === 2) { const w = io(seg(t, tWalk, tWalk + .9)); x = stairX + (liftX - stairX) * w; inLift = w > .5;
    if (t >= tDrop) { const u = cl((t - tDrop) / .32); floor = 7 * (1 - u * u); const d = t - tDrop - .32; if (d >= 0) { shake = 7 * Math.sin(d * 50) * Math.max(0, 1 - d / .45); dust = cl(d / .6); } } }
  if (i === 3) { floor = 0; const w = io(seg(t, at(S3, 'gone in two'), at(S3, 'gone in two') + 2.2)); x = liftX - 200 * w; inLift = w < .15; }   // the trader trudges out of the lift
  if (replay) { floor = 7; x = liftX; inLift = true; const tGate = at(S4, 'gate across'), tFall = at(S4, 'lift can only fall');
    gate = {f: 6, a: back(seg(t, tGate, tGate + .4))};
    if (t >= tFall) { const u = cl((t - tFall) / .22); floor = 7 - u * u; const d = t - tFall - .22; if (d >= 0) shake = 4 * Math.sin(d * 50) * Math.max(0, 1 - d / .3); } }
  // the account: +1% a floor on the way up; the drop takes it to 9,600; the gate keeps it at 10,600
  if (i === 1 || (i === 2 && t < tDrop)) acct = 10000 + Math.round(700 * cl(floor / 7));
  else if (i === 2) { acct = Math.round(10700 - 1100 * cl((t - tDrop) / .32)); col = RD; }
  else if (i === 3) { acct = 9600; col = RD; }
  else if (replay) { acct = Math.round(10700 - 100 * cl(floor >= 7 ? 0 : (7 - floor))); col = gate && gate.a > 0 ? AM : CR; }
  let g = `<g transform="translate(${shake.toFixed(1)} 0)">`;
  // the building: a cut-away, eight floors; the stairs on the left, the lift shaft on the right
  g += `<rect x="240" y="${fy(7) - 70}" width="600" height="${1270 - fy(7) + 80}" rx="6" fill="${BR}" stroke="${LN}" stroke-width="5"/>`;
  for (let f = 0; f <= 7; f++) {
    g += `<line x1="246" x2="650" y1="${fy(f)}" y2="${fy(f)}" stroke="${LN}" stroke-width="3"/>`;
    g += `<text x="268" y="${fy(f) - 54}" font-size="28" font-weight="700" fill="${LN}">${f}</text>`;
    const gone = i === 3 ? seg(t, at(S3, 'Seven weeks') + f * .25, at(S3, 'Seven weeks') + f * .25 + .5) : 0;   // in scene 3 the flights break off and fall, bottom up
    if (f < 7) for (let k = 0; k < 8; k++) { const ty = fy(f) - (k + 1) * FH / 8 + 900 * gone * gone; if (ty > 1238) continue;
      g += `<rect x="${456 + k * 22}" y="${ty.toFixed(1)}" width="22" height="5" fill="${AM}" opacity="${(.95 - .6 * gone).toFixed(2)}" transform="rotate(${(gone * 40 * (k % 2 ? 1 : -1)).toFixed(1)} ${467 + k * 22} ${ty.toFixed(1)})"/>`; }   // the flight to the next floor
  }
  g += `<rect x="660" y="${fy(7) - 70}" width="160" height="${1270 - fy(7) + 72}" fill="#17100a" stroke="${LN}" stroke-width="3"/>`;   // the shaft
  for (let f = 0; f <= 7; f++) g += `<line x1="660" x2="820" y1="${fy(f)}" y2="${fy(f)}" stroke="${LN}" stroke-width="2" stroke-dasharray="6 8"/>`;
  // the gate (a stop loss): an amber bar across the shaft on floor 6
  if (gate && gate.a > 0) g += `<g transform="translate(740 ${fy(gate.f)}) scale(${gate.a.toFixed(3)} 1)"><rect x="-84" y="-10" width="168" height="14" rx="4" fill="${AM}"/><text x="0" y="-22" text-anchor="middle" font-size="28" font-weight="800" fill="${AM}">STOP</text></g>`;
  // the lift car: on the trader's floor when they are in it, else waiting at floor 7; a cable above it
  const carF = inLift ? floor : carWait, cy = fy(carF);
  g += `<line x1="740" x2="740" y1="${fy(7) - 70}" y2="${(cy - FH + 8).toFixed(1)}" stroke="${LN}" stroke-width="3"/>`;
  g += `<rect x="676" y="${(cy - FH + 8).toFixed(1)}" width="128" height="${FH - 8}" rx="4" fill="#3a2a1a" stroke="${CR}" stroke-width="3"/>`;
  if (dust > 0) g += boomFx(740, 1240, dust, 180, '#8a7a66');
  // the trader
  const cues = [{do: 'pose', fig: 0, pose: 'walk', t: tUp0}, {do: 'pose', fig: 0, pose: 'stand', t: tUp1}, {do: 'pose', fig: 0, pose: 'walk', t: tWalk},
                {do: 'pose', fig: 0, pose: 'stand', t: tWalk + .9}, {do: 'pose', fig: 0, pose: 'panic', t: tDrop}, {do: 'pose', fig: 0, pose: 'sad', t: tDrop + .6}];
  const pose = i === 0 ? 'walk' : i === 3 ? (t < at(S3, 'gone in two') + 2.2 ? 'walk' : 'sad') : replay ? (t >= at(S4, 'lift can only fall') + .25 ? 'happy' : 'stand') : 'stand';
  const cues0 = [{do: 'pose', fig: 0, pose: 'stand', t: s.t0 + 1.4}];
  g += fig({pose, color: CR, x, y: fy(floor), sc: .9, s: {cues: i === 0 ? cues0 : i <= 2 ? cues : i === 3 ? [{do: 'pose', fig: 0, pose: 'sad', t: at(S3, 'gone in two') + 2.2}] : [], t0: -9}}, t);
  g += `</g>`;
  // HUD (y 380..500): the account and the floor
  g += `<text x="90" y="420" font-size="28" font-weight="700" fill="${AM}" letter-spacing="2">ACCOUNT</text><text x="90" y="486" font-size="60" font-weight="800" fill="${col}">£${acct.toLocaleString('en-GB')}</text>`;
  g += `<text x="990" y="420" text-anchor="end" font-size="28" font-weight="700" fill="${AM}" letter-spacing="2">FLOOR</text><text x="990" y="486" text-anchor="end" font-size="60" font-weight="800" fill="${col}">${Math.round(floor)}</text>`;
  return `<svg style="position:absolute;left:0;top:0" width="1080" height="1920">${g}</svg>` + punch(s, t);
}
