// Writes this folder's reel.json from the game's charts. Every figure on screen is worked out here from the arrays (and
// asserted), never typed in.   node make_reel.mjs [charts.json]
import fs from 'node:fs'; import path from 'node:path'; import assert from 'node:assert'; import {fileURLToPath} from 'node:url';
import {build, money} from '../../engines/remotion/src/raceMath.mjs';
const HERE = path.dirname(fileURLToPath(import.meta.url)), C = JSON.parse(fs.readFileSync(process.argv[2] || 'D:/reel-tmp/studio_data/charts.json', 'utf8'));

// ---- the look: one signal colour a stock (none of them a company's own colour), paper, ink
const COLOR = {MARA: '#e3120b', EXPR: '#1f3fd1', ETSY: '#00965e', DAL: '#f5a300', TSM: '#7b2fbe', NOK: '#e6007e', WKHS: '#00a5b5'};
const stake = 1000, T = 25, days = C[0].chart.length - 1;
const years = c => { const a = c.start.slice(0, 4), b = c.end.slice(0, 4); return a === b ? a : a + '\u2013' + b.slice(2); };
const series = C.map(c => ({ticker: c.ticker, name: c.name, years: years(c), color: COLOR[c.ticker], chart: c.chart}));   // (in the order the game showed them)

// ---- the facts, from the daily closes
const V = series.map(s => s.chart.map(x => stake * x / s.chart[0])), n = series.length, idx = [...Array(n).keys()];
const order = d => idx.slice().sort((a, b) => V[b][d] - V[a][d]), leader = d => order(d)[0];
let pk = {v: 0}; V.forEach((v, i) => v.forEach((x, d) => { if (x > pk.v) pk = {i, d, v: x}; }));
const R = series[pk.i], rv = V[pk.i], fin = order(days), W = series[fin[0]], gap = V[fin[0]][days] - V[fin[1]][days];
let jump = 1; for (let d = 2; d <= days; d++) if (rv[d] / rv[d - 1] > rv[jump] / rv[jump - 1]) jump = d;       // the rocket's biggest single day
let from = 1; while (leader(from) !== pk.i) from++;                                                           // the day it took the lead
let lost = pk.d; while (leader(lost) === pk.i) lost++;                                                        // the first day after the peak it was not in front
const drop = Math.round((1 - rv[lost] / pk.v) * 100), times = Math.floor(pk.v / stake), jx = Math.floor(rv[jump] / rv[jump - 1]);
for (let d = from; d < lost; d++) assert(leader(d) === pk.i, 'the rocket led from day ' + from + ' to its fall');
assert(fin[1] === pk.i && gap > 0 && gap < 50, 'the rocket finishes second, by a hair');
assert(Math.round(V[fin[0]][days]) - Math.round(V[fin[1]][days]) === Math.round(gap), 'the gap is the difference of the two figures shown');
assert(jump < pk.d && pk.d < lost && lost < days);

// ---- the time: [second, day]. Quiet stretches pass fast, the big moves slowly.
const t0 = 1.2, tJ = 7.3, tP = 10.0, tF = 11.0, tL = 14.4, tZ = 18.6, tC = 20.8;
const keys = [[t0, 0], [2.0, 1], [3.2, 2], [3.9, 6], [tJ, jump - 1], [8.2, jump], [tP - .1, pk.d], [tF + .1, pk.d], [tL, lost], [16.4, 112], [17.6, days - 1], [tZ, days]];
keys.forEach((k, i) => assert(!i || (k[0] > keys[i - 1][0] && k[1] >= keys[i - 1][1]), 'the days only go forward'));

// ---- the words: [from, to, small line, big line, its size, the stock whose colour it takes (or null), a tag that lands 0.45 s later]
const UP = s => s.toUpperCase();
const captions = [
  [-1, 1.25, `${n} REAL STOCKS.`, `${money(stake)} ON EACH.`, 94, null, ''],
  [1.3, 2.75, 'ONE TURNED INTO', money(pk.v), 150, pk.i, ''],
  [2.8, 4.3, 'AND IT STILL', "DIDN'T WIN.", 124, null, ''],
  [4.5, 7.0, `IN FRONT SINCE DAY ${from}`, UP(R.name), 124, pk.i, ''],
  [tJ, 9.8, `DAY ${jump}`, `${jx}\u00d7 IN ONE DAY`, 104, pk.i, ''],
  [tP - .05, tF + .2, `DAY ${pk.d} \u00b7 THE PEAK`, money(pk.v), 150, pk.i, `${times}\u00d7 THE MONEY`],
  [tF + .4, tL, 'SINCE THE PEAK', '\u2212{fall}%', 150, pk.i, ''],                        // ({fall}: the composition counts it, frame by frame)
  [tL + .1, 17.4, 'TWO STOCKS, ONE LEAD', 'NECK AND NECK', 96, null, ''],
  [17.6, tZ - .05, `DAY ${days}`, 'THE LAST DAY', 108, null, ''],
  [tZ + .1, tC - .05, `${UP(W.name)} WINS BY`, money(gap), 150, fin[0], 'PHOTO FINISH'],
];
const card = [`DAY ${pk.d} OF ${days}`, `YOUR ${money(stake)} IS ${money(pk.v)}.`, 'WHAT DO YOU DO?'];
const props = {T, stake, series, keys, captions, zooms: [[tP - .1, tF], [tZ + .05, tC - .3]], finish: tZ, card: {t: tC, lines: card, foot: 'COMMENT A, B OR C', site: 'MEMESTREET.NET'},
  kicker: [`THE ${money(stake)} RACE`, `${days} TRADING DAYS`], note: ['EACH OVER ITS OWN', `${days} TRADING DAYS,`, 'IN DIFFERENT YEARS'], ticks: [1000, 2000, 5000, 10000],
  paper: '#f3f0e8', ink: '#111111', grey: '#85827a', track: '#dcd8ce'};

// ---- what the picture does with them (the same code the composition runs), and what is heard
const B = build(props), end = B.F[B.F.length - 1];
assert(B.peak.i === pk.i && Math.abs(B.peak.v - pk.v) < .01 && Math.round(B.peak.d) === pk.d, 'the picture reaches the true peak');
assert(idx.every(i => end.rank[i] === fin.indexOf(i)) && end.lead === fin[0], 'the picture ends in the true order');
const held = B.F[Math.round((tP + .5) * 30)]; assert(idx.every(i => held.rank[i] === order(pk.d).indexOf(i)), 'the picture holds the peak in the true order');
assert(idx.every(i => Math.abs(end.v[i] - V[i][days]) < .01), 'the picture ends on the true figures');
const ev = [[0, 'rise'], [t0, 'whoosh'], [tJ, 'riser'], [8.2, 'boom'], [tP, 'ding'], [tP + .4, 'coin'], [tF, 'drop'], [tF + .4, 'crumble'], [17.6, 'riser'],          // the start, the rocket, the peak and its tag, the fall, the last day,
  [tZ, 'snap'], [tZ + .45, 'ding'], [tZ + .7, 'click'], [tZ + 1.3, 'pop'], [tC, 'whoosh'], [tC + .6, 'pop'], [tC + .75, 'pop'], [tC + .9, 'pop'], [tC + 1.2, 'sparkle']];   // the line, the winner's stamp, its mark, the peak note, the card and its answers
for (let t = tC + 1.7; t < T - .2; t += .5) ev.push([t, 'tick']);                                        // the answers lighting up in turn
const clear = (t, gap) => ev.every(e => Math.abs(e[0] - t) >= gap);
for (const [t, k] of B.heard) if (k === 'lead') ev.push([t, 'swish']);                                   // every change of leader, always
for (const t of [1.3, 2.8, 4.5, tL + .1]) if (clear(t, .12)) ev.push([t, t === 2.8 ? 'thud' : 'pop']);  // a caption landing, where nothing else is sounding
for (const [t, k] of B.heard) if (k === 'pass' && clear(t, .25)) ev.push([t, 'tick']);                   // the pack's passes, at most four a second
const events = ev.map(([t, k]) => [Math.round(t * 100) / 100, k]).sort((a, b) => a[0] - b[0]);

const reel = {
  name: 'race-1600', slot: '1600', engine: 'remotion', style: 'swiss data', entry: 'Race', title: `The ${money(stake)} race`,
  hook: {context: `${n} real stocks. ${money(stake)} on each.`, lean: `One turned into ${money(pk.v)}.`, snapback: "And it still didn't win.",
    text: `${n} real stocks. ${money(stake)} on each.`, visual: 'seven coloured bars already growing from nothing to $1,000 each, their figures counting up'},
  say: [], choice: {q: `Day ${pk.d}: your ${money(stake)} is ${money(pk.v)}. What do you do?`, a: 'Sell it all', b: 'Take half out', c: 'Hold on'},
  props, events, music: 'Fun and Games',
  caption: `${money(stake)} on each of ${n} real mystery stocks from the game, each followed over its own ${days} trading days (they are from different years). ` +
    `${R.name} turned it into ${money(pk.v)} by day ${pk.d}, then gave most of it back and finished second, ${money(gap)} behind ${W.name}.`,
  cover: {t: tP + .8},
};
fs.writeFileSync(path.join(HERE, 'reel.json'), JSON.stringify(reel));
console.log(`peak ${R.name} ${pk.v.toFixed(2)} on day ${pk.d} (${times}x); biggest day ${jump}: x${(rv[jump] / rv[jump - 1]).toFixed(2)}; led from day ${from}, lost the lead on day ${lost} (-${drop}%)`);
console.log('final  ' + fin.map(i => `${series[i].name} ${V[i][days].toFixed(2)}`).join(' | ') + `  gap ${gap.toFixed(2)}`);
console.log('leader on screen: ' + B.heard.filter(h => h[1] === 'lead').map(h => `${h[0].toFixed(2)}s`).join(' ') + `; passes ${B.heard.filter(h => h[1] === 'pass').length}; events ${events.length}`);
