// Ballast: loss limits the way funded-account ("prop") firms count them, and the trading day in a firm's own time
// zone. Pure functions; tested by `node --test`.
//
// The firms' rules differ and change: the trader picks the rule and reads their firm's page. What is computed:
//   daily loss  = how far equity is below the day's reference (start-of-day balance, or the higher of start-of-day
//                 balance and equity), open trades included
//   total loss  = how far equity is below the starting balance (static) or the highest balance or equity seen
//                 (trailing)
//   room        = the smallest of (limit - loss) over the limits set: a trade may not risk more than that.

const DAY = 86400000;

function finitePositive(x) {
  return typeof x === "number" && Number.isFinite(x) && x > 0;
}

/** The offset of `timeZone` from UTC at `ms`, in milliseconds (east positive). */
export function tzOffset(ms, timeZone) {
  const f = new Intl.DateTimeFormat("en-US", { timeZone, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit",
                                               hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const p = Object.fromEntries(f.formatToParts(new Date(ms)).map((x) => [x.type, x.value]));
  const asUtc = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour % 24, +p.minute, +p.second);
  return asUtc - Math.floor(ms / 1000) * 1000;
}

/** The UTC instant of a local wall-clock time in `timeZone`. */
export function zonedTime(y, m, d, hour, timeZone) {
  const guess = Date.UTC(y, m, d, hour);
  let t = guess - tzOffset(guess, timeZone);
  t = guess - tzOffset(t, timeZone);                          // (once more: right across a daylight-saving change)
  return t;
}

/** The start of the trading day: the latest `hour`:00 in `timeZone` that is not later than `nowMs`. */
export function dayStart(nowMs, hour, timeZone) {
  const local = new Date(nowMs + tzOffset(nowMs, timeZone));
  let t = zonedTime(local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate(), hour, timeZone);
  if (t > nowMs) {
    const prev = new Date(nowMs + tzOffset(nowMs, timeZone) - DAY);
    t = zonedTime(prev.getUTCFullYear(), prev.getUTCMonth(), prev.getUTCDate(), hour, timeZone);
  }
  return t;
}

/** The net result of deals closed since `fromMs` (wins and losses netted), and how many. */
export function closedSince(deals, fromMs) {
  let net = 0;
  let n = 0;
  for (const d of deals || []) {
    if (!d.closingTime || !Number.isFinite(d.netProfit)) continue;
    if (Date.parse(d.closingTime) >= fromMs) {
      net += d.netProfit;
      n += 1;
    }
  }
  return { net, n };
}

/**
 * The limits' state.
 * input: {
 *   balance, equity, worstEquity (equity if every open stop were hit; optional, never above equity),
 *   deals (closed deals covering at least the day), dayFrom (ms), dealsOk (the deals could be read in full),
 *   dayLimit, totalLimit: money, or null when not set, or NaN when set but not computable (a % with no starting balance),
 *   rule: "balance" | "higher" (of the day's opening balance and equity), sodEquity (the day's opening equity, if seen
 *   or entered), dayFloor (the lowest equity the firm allows today, from its dashboard, if entered: exact),
 *   initial (the starting balance), totalMode: "static" | "trailing", peak (the highest balance or equity this device
 *   has seen), totalFloor (the lowest equity the firm allows overall, from its dashboard, if entered) }
 * returns { day, total, room, known } where day and total are null (not set) or
 *   { loss (now), worst (if every stop is hit), limit, used, light, ref, refCode, uncertain, error }
 *   refCode: "sodBalance" | "higher" | "floor" | "initial" | "trailing"; error (blocks orders): "needStart" |
 *   "history" | "needSodEquity"; uncertain (shown, does not block): "devicePeak".
 *   room: the most a new trade may lose (from the worst case), or null when no limit is set.
 */
export function limitState(input) {
  const { balance, deals, dayFrom, dealsOk, rule, sodEquity, dayLimit, totalLimit, initial, totalMode, peak } = input;
  const equity = Number.isFinite(input.equity) ? input.equity : balance;
  const worstEq = Number.isFinite(input.worstEquity) ? Math.min(equity, input.worstEquity) : equity;
  const out = { day: null, total: null, room: null, known: true };
  const make = (limit, ref, refCode, extra = {}) => {
    const loss = Math.max(0, ref - equity);
    const worst = Math.max(0, ref - worstEq);
    return { loss, worst, limit, used: loss / limit, light: light(loss, limit), ref, refCode, uncertain: null, error: null, ...extra };
  };
  const bad = (limit, error) => ({ loss: null, worst: null, limit, used: null, light: "unknown", ref: null, refCode: null, uncertain: null, error });

  if (dayLimit != null) {
    if (!finitePositive(dayLimit)) out.day = bad(dayLimit, "needStart");
    else if (Number.isFinite(input.dayFloor)) out.day = make(dayLimit, input.dayFloor + dayLimit, "floor");
    else if (!dealsOk) out.day = bad(dayLimit, "history");
    else {
      const sodBalance = balance - closedSince(deals, dayFrom).net;   // (deposits and withdrawals during the day are not seen)
      if (rule === "higher") {
        out.day = Number.isFinite(sodEquity) ? make(dayLimit, Math.max(sodBalance, sodEquity), "higher") : bad(dayLimit, "needSodEquity");
      } else {
        out.day = make(dayLimit, sodBalance, "sodBalance");
      }
    }
  }
  if (totalLimit != null) {
    if (!finitePositive(totalLimit)) out.total = bad(totalLimit, "needStart");
    else {
      const floors = [];
      if (Number.isFinite(input.totalFloor)) floors.push(input.totalFloor);
      if (finitePositive(initial)) floors.push(initial - totalLimit);
      if (totalMode === "trailing" && finitePositive(peak)) floors.push(peak - totalLimit);
      if (!floors.length) out.total = bad(totalLimit, "needStart");
      else {
        const floor = Math.max(...floors);                        // (every one is a floor the firm enforces: the highest binds)
        const code = Number.isFinite(input.totalFloor) && floor === input.totalFloor ? "floor" : totalMode === "trailing" ? "trailing" : "initial";
        out.total = make(totalLimit, floor + totalLimit, code,
                         { uncertain: totalMode === "trailing" && !Number.isFinite(input.totalFloor) ? "devicePeak" : null });
      }
    }
  }
  const parts = [out.day, out.total].filter(Boolean);
  if (parts.some((x) => x.error)) out.known = false;
  const rooms = parts.filter((x) => !x.error).map((x) => x.limit - x.worst);
  if (parts.length && out.known) {
    const r = Math.min(...rooms);
    out.room = r < 0.005 ? 0 : r;                              // (under half a cent is no room: float noise must not leave a sliver)
  }
  return out;
}

/** "green", "amber" (80% used) or "red" (reached). */
export function light(loss, limit) {
  const used = loss / limit;
  return used >= 1 - 1e-9 ? "red" : used >= 0.8 - 1e-9 ? "amber" : "green";
}
