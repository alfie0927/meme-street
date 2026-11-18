// DEVICE: a game show. The hook is a big red buzzer slammed on "Can you"; three lamps above the title count the
// questions (dark, then the live one pulses amber during the countdown, then green with a burst at the answer). The
// question and answer scenes themselves are the template's (chart, option cards, countdown): this function only adds
// the lamps strip and the buzzer, and stays out of the title row. Palette: the house teal and amber, a red buzzer.
({t, T, s, i, R, api}) => {
  const {seg, cl, io, out, back, esc, punch, at, boomFx, G, AM, RD, TE} = api;
  if (s.kind === 'big' || s.kind === 'outro') return '';
  const S = R.scenes, qs = S.map((q, k) => k).filter(k => S[k].kind === 'question');   // the question scenes, in order
  let g = '';
  // the lamps strip (y 352, between the progress line and the title): one per question (not in scene 0: the hook has the top of the frame)
  if (i > 0) qs.forEach((k, n) => {
    const Q = S[k], A = S[k + 1] && S[k + 1].kind === 'answer' ? S[k + 1] : null, x = 540 + (n - (qs.length - 1) / 2) * 70;
    const live = i === k, done = A && t >= A.t0 + .1, lit = done ? G : live ? AM : '#2a2f35';
    const pul = live && Q.think_t && t >= Q.think_t[0] ? .75 + .25 * Math.sin((t - Q.think_t[0]) * 10) : 1;
    if (A && seg(t, A.t0 + .1, A.t0 + .6) < 1 && t >= A.t0 + .1) g += boomFx(x, 352, seg(t, A.t0 + .1, A.t0 + .6), 46, G);
    g += `<circle cx="${x.toFixed(1)}" cy="352" r="${(16 * pul).toFixed(1)}" fill="${lit}" stroke="${done || live ? lit : '#3a4048'}" stroke-width="3"/>`;
    if (done || live) g += `<circle cx="${x.toFixed(1)}" cy="352" r="26" fill="none" stroke="${lit}" stroke-width="2" opacity="${(.5 * pul).toFixed(2)}"/>`;
  });
  // the hook: the buzzer, slammed on "Can you"; it springs back and rings
  if (i === 0) {
    const tHit = at(s, 'Can you'), a = back(seg(t, s.t0, s.t0 + .6)), p = seg(t, tHit, tHit + .12), r = seg(t, tHit + .12, tHit + .5), press = p < 1 ? p : 1 - r;
    const cy = 980, sq = 1 - .28 * press;
    g += `<g transform="translate(540 ${cy}) scale(${a.toFixed(3)})">`;
    g += `<ellipse cx="0" cy="150" rx="300" ry="54" fill="#1b2027" stroke="#3a4048" stroke-width="6"/>`;
    g += `<g transform="translate(0 ${(60 * press).toFixed(1)}) scale(1 ${sq.toFixed(3)})"><ellipse cx="0" cy="110" rx="230" ry="60" fill="#8f1f2a"/><rect x="-230" y="-40" width="460" height="150" fill="#8f1f2a"/><ellipse cx="0" cy="-40" rx="230" ry="60" fill="${RD}"/><ellipse cx="-60" cy="-58" rx="80" ry="22" fill="#ff9aa2" opacity=".55"/></g>`;
    if (t >= tHit) { const u = seg(t, tHit, tHit + .9); g += `<ellipse cx="0" cy="110" rx="${(240 + 320 * u).toFixed(0)}" ry="${(60 + 80 * u).toFixed(0)}" fill="none" stroke="${AM}" stroke-width="${(10 * (1 - u)).toFixed(1)}" opacity="${(1 - u).toFixed(2)}"/>`; }
    g += `</g>`;
    // three dark chart cards waiting behind it, popping in on "Three charts"
    const tC = at(s, 'Three charts');
    for (let k = 0; k < 3; k++) { const b = back(seg(t, tC + k * .15, tC + k * .15 + .4)); if (b <= 0) continue;
      g += `<g transform="translate(${260 + k * 280} 640) scale(${b.toFixed(3)})"><rect x="-100" y="-70" width="200" height="140" rx="18" fill="#0d1116" stroke="${TE}" stroke-width="4"/><polyline points="-70,40 -35,10 -5,30 30,-20 70,-40" fill="none" stroke="${k === 1 ? RD : G}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/><text x="0" y="-85" text-anchor="middle" font-size="28" font-weight="800" fill="${TE}">${k + 1}</text></g>`; }
  }
  return `<svg style="position:absolute;left:0;top:0" width="1080" height="1920">${g}</svg>` + punch(s, t);
}
