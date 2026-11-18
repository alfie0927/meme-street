// Ballast: the sizing maths. Pure functions, no cTrader; everything here is tested by `node --test`.
//
// The promise: the money lost if the stop is hit, commission included, is never more than the trader chose, before
// slippage and gaps (which no tool can bound). Every number below is chosen to keep that promise:
//   - the size is always rounded DOWN to the symbol's volume step, and refused (never rounded up) below the minimum;
//   - every exchange rate is taken on the side that makes the loss LARGER (ask when multiplying, 1/bid when dividing),
//     and, when the traded symbol is itself a leg of the conversion, the rate is also taken at the stop price and the
//     worse of the two is used (a loss is converted when the stop is hit, not now);
//   - commission is charged twice (open and close), and the platform's conversion fee is added on top;
//   - the budget is cut to the room left under the trader's own loss limits.
//
// Units. A symbol's lotSize, minVolume, maxVolume and volumeStep are in the platform's volume unit, and an order's
// volume is in the same unit. `unitsPerVolume` is how many units of the base asset one volume unit is (1 if volume
// is counted in units). The demo-account probe settles it (README, "Probe").

const EPS = 1e-9;

export function finitePositive(x) {
  return typeof x === "number" && Number.isFinite(x) && x > 0;
}

/** A price as a whole number of the symbol's smallest price steps (points). */
export function toPoints(price, digits) {
  return Math.round(price * 10 ** digits);
}

/** A price rounded to the symbol's digits. */
export function roundPrice(price, digits) {
  return Math.round(price * 10 ** digits) / 10 ** digits;
}

/** The pip size of a symbol, as a price: 10^-pipPosition. */
export function pipSize(pipPosition) {
  return 10 ** -pipPosition;
}

/** A distance in points, as pips, rounded to the finest step the symbol's digits allow. */
export function pointsToPips(points, digits, pipPosition) {
  const k = Math.max(0, digits - pipPosition);
  return Math.round((points / 10 ** (digits - pipPosition)) * 10 ** k) / 10 ** k;
}

/** How many decimals a lot count needs for this symbol (a 0.01-lot step needs 2, a 0.001-lot step 3). */
export function lotDecimals(symbol) {
  if (!symbol || !finitePositive(symbol.volumeStep) || !finitePositive(symbol.lotSize)) return 2;
  const step = symbol.volumeStep / symbol.lotSize;
  for (let d = 0; d <= 8; d++) if (Math.abs(Math.round(step * 10 ** d) - step * 10 ** d) < 1e-7) return Math.max(2, d);
  return 8;
}

function roundClean(x) {
  return Math.round(x * 1e10) / 1e10;
}

function fail(code, message, extra = {}) {
  return { ok: false, code, message, ...extra };
}

/** Plain money for messages: two decimals, no currency (the page adds it). */
export function money(x) {
  return (Math.round(x * 100) / 100).toFixed(2);
}

/**
 * A number typed by a person: "1,000.50", "1 000,50", "1000.5", "0,5". Returns NaN for anything ambiguous or empty,
 * never a wrong number ("100,000" is 100000, not 100).
 */
export function parseNumber(v, decimalMark = ".") {
  let s = String(v ?? "").trim().replace(/[\s  ']/g, "");
  if (!s) return NaN;
  if (!/^[+-]?[\d.,]+$/.test(s)) return NaN;
  const dots = (s.match(/\./g) || []).length;
  const commas = (s.match(/,/g) || []).length;
  if (dots && commas) {                                           // the last one is the decimal mark
    const dec = s.lastIndexOf(".") > s.lastIndexOf(",") ? "." : ",";
    const grp = dec === "." ? "," : ".";
    if ((s.split(dec).length - 1) > 1) return NaN;
    s = s.split(grp).join("").replace(dec, ".");
  } else if (commas > 1 || dots > 1) {                            // "1,000,000" or "1.000.000": thousands
    const sep = commas > 1 ? "," : ".";
    const parts = s.replace(/^[+-]/, "").split(sep);
    if (parts.slice(1).some((p) => p.length !== 3)) return NaN;
    s = s.split(sep).join("");
  } else if (commas + dots === 1) {
    const sep = commas ? "," : ".";
    const [a, b] = s.replace(/^[+-]/, "").split(sep);
    // "1,25" and "0.005" are decimals whatever the reader; "1,250" or "1.250" is a thousand only to a reader whose
    // decimal mark is the other one (the browser's locale decides; this is the one ambiguous shape)
    const thousands = b.length === 3 && a.length >= 1 && a.length <= 3 && a !== "0" && !/^0/.test(a) && sep !== decimalMark;
    s = thousands ? s.replace(sep, "") : s.replace(sep, ".");
  }
  const x = Number(s);
  return Number.isFinite(x) ? x : NaN;
}

// ---- currency conversion -------------------------------------------------------------------------------------------

/**
 * How to turn one unit of asset `from` into asset `to`, through at most two symbols.
 * symbols: [{ id, name, baseAssetId, quoteAssetId }]. Returns [] when from == to, a list of { symbolId, invert }
 * steps, or null. invert false: the symbol is quoted from/to (multiply by its price); true: quoted to/from (divide).
 * `prefer` (an asset id, normally USD) is tried first as the middle of a two-step path; a direct pair always wins.
 */
export function conversionPath(symbols, from, to, prefer = null) {
  if (from == null || to == null) return null;
  if (from === to) return [];
  const edges = [];
  for (const s of symbols || []) {
    if (s.baseAssetId == null || s.quoteAssetId == null || s.baseAssetId === s.quoteAssetId) continue;
    const pair = { base: s.baseAssetId, quote: s.quoteAssetId };
    edges.push({ a: s.baseAssetId, b: s.quoteAssetId, step: { symbolId: s.id, invert: false, ...pair } });
    edges.push({ a: s.quoteAssetId, b: s.baseAssetId, step: { symbolId: s.id, invert: true, ...pair } });
  }
  const direct = edges.find((e) => e.a === from && e.b === to);
  if (direct) return [direct.step];
  const firsts = edges.filter((e) => e.a === from).sort((x, y) => (y.b === prefer) - (x.b === prefer));
  for (const e1 of firsts) {
    const e2 = edges.find((e) => e.a === e1.b && e.b === to);
    if (e2) return [e1.step, e2.step];
  }
  return null;
}

/**
 * The rate along a path, on the conservative side: ask when multiplying, 1/bid when dividing.
 * quotes: { [symbolId]: { bid, ask } }. `at`: { symbolId, base, quote, price } for the traded symbol at the stop: a leg
 * on that symbol, or on another listing of the same pair, is also valued at the stop price and the worse value is used.
 * Returns { ok: true, rate } or { ok: false, missing: [symbolId...] }.
 */
export function conversionRate(path, quotes, at = null) {
  if (!path) return { ok: false, missing: [] };
  let rate = 1;
  const missing = [];
  for (const step of path) {
    const q = quotes && quotes[step.symbolId];
    let price = q && (step.invert ? q.bid : q.ask);
    if (!finitePositive(price)) {
      missing.push(step.symbolId);
      continue;
    }
    const same = at && (at.symbolId === step.symbolId || (at.base != null && at.base === step.base && at.quote === step.quote));
    if (same && finitePositive(at.price)) {                   // (also a second listing of the same pair, e.g. EURUSD.raw)
      price = step.invert ? Math.min(price, at.price) : Math.max(price, at.price);
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

// ---- commission ----------------------------------------------------------------------------------------------------

/**
 * Commission per unit per side, in the account's money.
 * c: { mode: "none" | "lot" (money per lot per side) | "million" (USD per million USD traded per side) |
 *       "percent" (percent of the trade's value per side), value }
 * For "million": usdPerUnit is one unit's value in USD now (price x quote-to-USD rate) and usdToDeposit the rate
 * from USD to the account's money (both conservative). For "percent": depositPerUnit is one unit's value in the
 * account's money (price x quote-to-deposit rate).
 */
export function commissionPerUnit(c, { lotUnits, usdPerUnit, usdToDeposit, depositPerUnit } = {}) {
  if (!c || c.mode === "none" || !(c.value > 0)) return 0;
  if (c.mode === "lot") return finitePositive(lotUnits) ? c.value / lotUnits : NaN;
  if (c.mode === "percent") return finitePositive(depositPerUnit) ? (depositPerUnit * c.value) / 100 : NaN;
  if (c.mode === "million") return finitePositive(usdPerUnit) && finitePositive(usdToDeposit) ? (usdPerUnit * c.value * usdToDeposit) / 1e6 : NaN;
  return NaN;
}

// ---- sizing --------------------------------------------------------------------------------------------------------

/**
 * The size of a trade for the risk chosen.
 *
 * input: { balance, riskMode: "percent"|"money", risk, side: "buy"|"sell", entry, stop, rate,
 *          commission (money per unit per side, default 0), feeRate (the platform's conversion fee, a fraction:
 *          applied when the quote currency is not the account's), room (the most the limits allow, default none),
 *          symbol: { digits, pipPosition, lotSize, minVolume, maxVolume, volumeStep, unitsPerVolume } }
 * returns { ok: true, volume, lots, units, riskMoney, priceRisk, commissionRisk, budget, cut, points, pips, capped,
 *           leverage (position value / balance) }
 *      or { ok: false, code, message, minRisk? }
 */
export function sizeTrade(input) {
  const { balance, riskMode, risk, side, entry, stop, rate, symbol } = input;
  const commission = input.commission ?? 0;
  const feeRate = input.feeRate ?? 0;
  if (!symbol || !finitePositive(symbol.volumeStep) || !finitePositive(symbol.lotSize)) {
    return fail("symbol", "This symbol's trading details are missing. Reopen the panel on the symbol.", { key: "symbolDetails" });
  }
  if (!finitePositive(balance)) return fail("balance", "The account balance is not available.", { key: "balance" });
  if (!finitePositive(risk)) return fail("risk", "Enter the risk: a percent of the balance, or an amount of money.", { key: "riskEmpty" });
  if (riskMode === "percent" && risk > 100) return fail("risk", "A risk above 100% of the balance is not possible.", { key: "riskTooBig" });
  if (!finitePositive(entry)) return fail("entry", "Enter the entry price.", { key: "entryEmpty" });
  if (!finitePositive(stop)) return fail("stop", "Enter the stop.", { key: "stopEmpty" });
  if (!finitePositive(rate)) return fail("rate", "No exchange rate into the account's currency is available yet, so the risk cannot be sized.", { key: "noRate" });
  if (!(commission >= 0) || !Number.isFinite(commission)) return fail("commission", "The commission cannot be worked out for this symbol. Check the commission setting.", { key: "commission" });
  if (!(feeRate >= 0) || feeRate >= 1) return fail("fee", "The platform's conversion fee for this symbol is not valid.", { key: "fee" });
  if (side !== "buy" && side !== "sell") return fail("side", "Choose Buy or Sell.", { key: "side" });

  const points = Math.abs(toPoints(entry, symbol.digits) - toPoints(stop, symbol.digits));
  if (points === 0) return fail("stop", "The stop is at the entry price: there is no distance to size from.", { key: "stopAtEntry" });
  if (side === "buy" && stop > entry) return fail("stop", "For a buy, the stop must be below the entry.", { key: "stopSideBuy" });
  if (side === "sell" && stop < entry) return fail("stop", "For a sell, the stop must be above the entry.", { key: "stopSideSell" });

  let budget = riskMode === "percent" ? (balance * risk) / 100 : risk;
  let cut = false;
  if (input.room != null) {
    if (!(input.room > 0)) return fail("limit", "Your loss limit has no room left. This panel will not place orders until it resets.", { key: "noRoom" });
    if (input.room < budget) {
      budget = input.room;
      cut = true;
    }
  }
  const distance = points / 10 ** symbol.digits;
  const unitsPerVolume = finitePositive(symbol.unitsPerVolume) ? symbol.unitsPerVolume : 1;
  const pricePerUnit = distance * rate * (1 + feeRate);
  const lossPerUnit = pricePerUnit + 2 * commission;
  const riskPerVolume = lossPerUnit * unitsPerVolume;
  const step = symbol.volumeStep;
  const minVolume = finitePositive(symbol.minVolume) ? symbol.minVolume : step;
  const maxVolume = finitePositive(symbol.maxVolume) ? symbol.maxVolume : Infinity;

  let steps = Math.floor(budget / riskPerVolume / step + EPS);      // (EPS: 49.9999999 steps from float noise is 50)
  let capped = false;
  if (steps * step > maxVolume + EPS) {
    steps = Math.floor(maxVolume / step + EPS);
    capped = true;
  }
  let volume = roundClean(steps * step);
  while (volume > 0 && volume * riskPerVolume > budget * (1 + EPS)) {   // (never past the budget)
    steps -= 1;
    volume = roundClean(steps * step);
  }
  if (volume < minVolume - EPS) {
    const minRisk = minVolume * riskPerVolume;
    return fail("min", `The smallest size this symbol allows would risk ${money(minRisk)}, more than the ${money(budget)} ${cut ? "your limits leave" : "chosen"}. Nothing is placed.`, { minRisk, budget, cut, key: "minSize" });
  }
  const units = roundClean(volume * unitsPerVolume);
  return {
    ok: true, volume, lots: roundClean(volume / symbol.lotSize), units,
    riskMoney: volume * riskPerVolume, priceRisk: units * pricePerUnit, commissionRisk: units * 2 * commission,
    budget, cut, points, pips: pointsToPips(points, symbol.digits, symbol.pipPosition), capped,
    leverage: (units * entry * rate) / balance,
  };
}

/** The target from a multiple of the risk distance. */
export function targetFromR(side, entry, stop, r, digits) {
  const d = Math.abs(entry - stop) * r;
  return roundPrice(side === "buy" ? entry + d : entry - d, digits);
}

/** Reward to risk of a planned trade, and the win rate at which it breaks even (before costs). */
export function rewardRisk(entry, stop, target) {
  const risk = Math.abs(entry - stop);
  const reward = Math.abs(target - entry);
  if (!(risk > 0) || !(reward > 0)) return null;
  const rr = reward / risk;
  return { rr, breakEvenWinRate: 1 / (1 + rr) };
}

/** The loss at the stop of an open position, in the account's money, with the closing commission; null without a stop. */
export function positionRisk(p, rate, unitsPerVolume = 1) {
  if (!finitePositive(p.stopLoss)) return null;
  const units = p.volume * unitsPerVolume;
  const loss = (p.side === "buy" ? p.entryPrice - p.stopLoss : p.stopLoss - p.entryPrice) * units * rate;
  // (a stop past the entry locks in a profit: no price risk left. The closing side's commission is still to pay:
  //  `commission` is what the position has been charged so far, in account money, counted once more.)
  return Math.max(0, loss) + Math.abs(Number.isFinite(p.commission) ? p.commission : 0);
}

/** Average true range of bars [{ high, low, close }] over `n` bars (Wilder's smoothing), or null. */
export function atr(bars, n = 14) {
  if (!bars || bars.length < n + 1) return null;
  const tr = [];
  for (let i = 1; i < bars.length; i++) {
    const b = bars[i];
    const pc = bars[i - 1].close;
    tr.push(Math.max(b.high - b.low, Math.abs(b.high - pc), Math.abs(b.low - pc)));
  }
  let a = tr.slice(0, n).reduce((s, x) => s + x, 0) / n;
  for (let i = n; i < tr.length; i++) a = (a * (n - 1) + tr[i]) / n;
  return a;
}
