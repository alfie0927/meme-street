// The maths of Exact Risk Ticket. Pure functions, no cTrader: everything here is tested by `node --test`.
//
// Units. A symbol's `lotSize`, `minVolume`, `maxVolume` and `volumeStep` are in the platform's volume unit, and an
// order's `volume` is in the same unit. `unitsPerVolume` says how many units of the base asset one volume unit is
// (1 if volume is counted in units, 0.01 if it is counted in hundredths). The probe on a demo account settles which
// one cTrader's Plugin API v2 uses (README, "Probe"); nothing below depends on the answer except through that number.
//
// Money. `rate` is how much of the account's currency one unit of the symbol's quote currency is worth. Every rate
// is taken on the side that makes the risk look LARGER (conservative), so a size computed here never risks more than
// was asked for. The result is always rounded DOWN to the volume step.

const EPS = 1e-9;

/** A price as a whole number of the symbol's smallest price steps (points). */
export function toPoints(price, digits) {
  return Math.round(price * 10 ** digits);
}

/** The pip size of a symbol, as a price: 10^-pipPosition. */
export function pipSize(pipPosition) {
  return 10 ** -pipPosition;
}

/** A distance in points, as pips, rounded to the finest step the symbol's digits allow. */
export function pointsToPips(points, digits, pipPosition) {
  const per = 10 ** (digits - pipPosition);
  return Math.round((points / per) * 10 ** Math.max(0, digits - pipPosition)) / 10 ** Math.max(0, digits - pipPosition);
}

function finitePositive(x) {
  return typeof x === "number" && Number.isFinite(x) && x > 0;
}

function roundClean(x) {
  return Math.round(x * 1e10) / 1e10;
}

function fail(code, message, extra = {}) {
  return { ok: false, code, message, ...extra };
}

/**
 * The size of a trade for the risk chosen.
 *
 * input: { balance, riskMode: "percent"|"money", risk, side: "buy"|"sell", entry, stop, rate,
 *          symbol: { digits, pipPosition, lotSize, minVolume, maxVolume, volumeStep, unitsPerVolume } }
 * returns { ok: true, volume, lots, units, riskMoney, budget, points, pips, capped }
 *      or { ok: false, code, message, minRisk? }
 */
export function sizeTrade(input) {
  const { balance, riskMode, risk, side, entry, stop, rate, symbol } = input;
  if (!symbol || !finitePositive(symbol.volumeStep) || !finitePositive(symbol.lotSize)) {
    return fail("symbol", "This symbol's trading details are missing. Reopen the panel on the symbol.");
  }
  if (!finitePositive(balance)) return fail("balance", "The account balance is not available.");
  if (!finitePositive(risk)) return fail("risk", "Enter the risk: a percent of the balance, or an amount of money.");
  if (riskMode === "percent" && risk > 100) return fail("risk", "A risk above 100% of the balance is not possible.");
  if (!finitePositive(entry)) return fail("entry", "Enter the entry price.");
  if (!finitePositive(stop)) return fail("stop", "Enter the stop price.");
  if (!finitePositive(rate)) return fail("rate", "No exchange rate into the account's currency is available yet, so the risk cannot be sized.");
  if (side !== "buy" && side !== "sell") return fail("side", "Choose Buy or Sell.");

  const points = Math.abs(toPoints(entry, symbol.digits) - toPoints(stop, symbol.digits));
  if (points === 0) return fail("stop", "The stop is at the entry price: there is no distance to size from.");
  if (side === "buy" && stop > entry) return fail("stop", "For a buy, the stop must be below the entry.");
  if (side === "sell" && stop < entry) return fail("stop", "For a sell, the stop must be above the entry.");

  const distance = points / 10 ** symbol.digits;
  const unitsPerVolume = finitePositive(symbol.unitsPerVolume) ? symbol.unitsPerVolume : 1;
  const budget = riskMode === "percent" ? (balance * risk) / 100 : risk;
  const riskPerVolume = distance * rate * unitsPerVolume;
  const step = symbol.volumeStep;
  const minVolume = finitePositive(symbol.minVolume) ? symbol.minVolume : step;
  const maxVolume = finitePositive(symbol.maxVolume) ? symbol.maxVolume : Infinity;

  let steps = Math.floor(budget / riskPerVolume / step + EPS);      // (EPS: 49.9999999 steps from float noise is 50)
  let capped = false;
  if (steps * step > maxVolume) {
    steps = Math.floor(maxVolume / step + EPS);
    capped = true;
  }
  let volume = roundClean(steps * step);
  while (volume > 0 && volume * riskPerVolume > budget * (1 + EPS)) {   // (never round up past the budget)
    steps -= 1;
    volume = roundClean(steps * step);
  }
  if (volume < minVolume - EPS) {
    const minRisk = minVolume * riskPerVolume;
    return fail("min", `The smallest size this symbol allows would risk ${money(minRisk)}, more than the ${money(budget)} chosen. Nothing is placed.`, { minRisk, budget });
  }
  const riskMoney = volume * riskPerVolume;
  return {
    ok: true, volume, lots: roundClean(volume / symbol.lotSize), units: roundClean(volume * unitsPerVolume),
    riskMoney, budget, points, pips: pointsToPips(points, symbol.digits, symbol.pipPosition), capped,
  };
}

/** Plain money for messages: two decimals, no currency (the page adds it). */
export function money(x) {
  return (Math.round(x * 100) / 100).toFixed(2);
}

/**
 * How to turn one unit of asset `from` into asset `to`, through at most two symbols.
 * symbols: [{ id, baseAssetId, quoteAssetId }]. Returns [] when from == to, a list of { symbolId, invert } steps,
 * or null when no path exists. A step with invert false is a symbol quoted from/to (multiply by its price); invert
 * true is a symbol quoted to/from (divide).
 */
export function conversionPath(symbols, from, to) {
  if (from === to) return [];
  const edges = [];
  for (const s of symbols || []) {
    if (s.baseAssetId == null || s.quoteAssetId == null || s.baseAssetId === s.quoteAssetId) continue;
    edges.push({ a: s.baseAssetId, b: s.quoteAssetId, symbolId: s.id, invert: false });
    edges.push({ a: s.quoteAssetId, b: s.baseAssetId, symbolId: s.id, invert: true });
  }
  const direct = edges.find((e) => e.a === from && e.b === to);
  if (direct) return [{ symbolId: direct.symbolId, invert: direct.invert }];
  for (const e1 of edges) {
    if (e1.a !== from) continue;
    const e2 = edges.find((e) => e.a === e1.b && e.b === to);
    if (e2) return [{ symbolId: e1.symbolId, invert: e1.invert }, { symbolId: e2.symbolId, invert: e2.invert }];
  }
  return null;
}

/**
 * The rate along a path, on the conservative side: ask when multiplying, 1/bid when dividing.
 * quotes: { [symbolId]: { bid, ask } }. Returns { ok: true, rate } or { ok: false, missing: [symbolId...] }.
 */
export function conversionRate(path, quotes) {
  if (!path) return { ok: false, missing: [] };
  let rate = 1;
  const missing = [];
  for (const step of path) {
    const q = quotes && quotes[step.symbolId];
    const price = q && (step.invert ? q.bid : q.ask);
    if (!finitePositive(price)) {
      missing.push(step.symbolId);
      continue;
    }
    rate = step.invert ? rate / price : rate * price;
  }
  return missing.length ? { ok: false, missing } : { ok: true, rate };
}

/** The price a market order would get now: the ask for a buy, the bid for a sell. */
export function marketEntry(side, quote) {
  if (!quote) return NaN;
  return side === "buy" ? quote.ask : quote.bid;
}

/** The target from a multiple of the risk distance. */
export function targetFromR(side, entry, stop, r, digits) {
  const d = Math.abs(entry - stop) * r;
  const t = side === "buy" ? entry + d : entry - d;
  return Math.round(t * 10 ** digits) / 10 ** digits;
}

/** Reward to risk of a planned trade, and the win rate at which it breaks even (ignoring costs). */
export function rewardRisk(entry, stop, target) {
  const risk = Math.abs(entry - stop);
  const reward = Math.abs(target - entry);
  if (!(risk > 0) || !(reward > 0)) return null;
  const rr = reward / risk;
  return { rr, breakEvenWinRate: 1 / (1 + rr) };
}

// ---- the label an order carries, so the log can show R: "ERT r=123.45" (the planned risk in account money)
const LABEL = /^ERT r=(\d+(?:\.\d+)?)$/;

export function makeLabel(riskMoney) {
  return `ERT r=${money(riskMoney)}`;
}

export function parseLabel(label) {
  const m = LABEL.exec(label || "");
  return m ? { risk: Number(m[1]) } : null;
}

export function rMultiple(netProfit, plannedRisk) {
  return finitePositive(plannedRisk) && Number.isFinite(netProfit) ? netProfit / plannedRisk : null;
}

/**
 * Closed trades placed by this panel, newest first, with their R.
 * deals: [{ dealId, symbolName, openingDirection, closingTime, netProfit, label }] (Plugin API v2 DealSummary).
 */
export function tradeLog(deals) {
  const out = [];
  for (const d of deals || []) {
    if (!d.closingTime || !Number.isFinite(d.netProfit)) continue;
    const planned = parseLabel(d.label);
    if (!planned) continue;
    out.push({ id: d.dealId, symbol: d.symbolName, side: d.openingDirection, closed: d.closingTime,
               net: d.netProfit, r: rMultiple(d.netProfit, planned.risk) });
  }
  return out.sort((a, b) => (a.closed < b.closed ? 1 : a.closed > b.closed ? -1 : 0));
}

/** One line of statistics over a log: trades, win rate, average R and profit factor. */
export function summary(log) {
  const n = log.length;
  if (!n) return { count: 0, winRate: null, avgR: null, profitFactor: null };
  const wins = log.filter((t) => t.net > 0);
  const gains = wins.reduce((s, t) => s + t.net, 0);
  const losses = -log.filter((t) => t.net < 0).reduce((s, t) => s + t.net, 0);
  const rs = log.map((t) => t.r).filter((r) => r !== null);
  return {
    count: n,
    winRate: wins.length / n,
    avgR: rs.length ? rs.reduce((s, r) => s + r, 0) / rs.length : null,
    profitFactor: losses > 0 ? gains / losses : null,
  };
}

/** The start of the trading day for the loss light: the latest moment at `resetHour` local time that is not later
 * than `nowMs`. `offsetMinutes` is the local time's offset from UTC (east positive), so the result is testable. */
export function dayStart(nowMs, resetHour, offsetMinutes) {
  const local = nowMs + offsetMinutes * 60000;
  const d = new Date(local);
  let start = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), resetHour) - offsetMinutes * 60000;
  if (start > nowMs) start -= 86400000;
  return start;
}

/** The money lost on trades closed since `fromMs` (all deals, not only this panel's): a positive number, or 0. */
export function realisedLossSince(deals, fromMs) {
  let net = 0;
  for (const d of deals || []) {
    if (!d.closingTime || !Number.isFinite(d.netProfit)) continue;
    if (Date.parse(d.closingTime) >= fromMs) net += d.netProfit;
  }
  return net < 0 ? -net : 0;
}

/** "off" (no limit set), "green", "amber" (80% of the limit used) or "red" (the limit reached). */
export function lossLight(loss, limit) {
  if (!finitePositive(limit)) return "off";
  const used = loss / limit;
  return used >= 1 - EPS ? "red" : used >= 0.8 - EPS ? "amber" : "green";
}
