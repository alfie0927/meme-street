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
 * input: { balance, equity, deals (closed deals covering at least the day), dayFrom (ms), dealsOk (the deals could
 *          be read in full), rule: "balance"|"higher", sodEquity (equity seen at the day's start, if any),
 *          dayLimit (money), totalLimit (money), initial (the account's starting balance), totalMode: "static"|"trailing",
 *          peak (the highest balance or equity seen, for trailing) }
 * returns { day: {loss, limit, used, light, ref, refNote}, total: {...}, room, known, worstIfStopsHit? }
 */
export function limitState(input) {
  const { balance, equity: eq, deals, dayFrom, dealsOk, rule, sodEquity, dayLimit, totalLimit, initial, totalMode, peak } = input;
  const equity = Number.isFinite(eq) ? eq : balance;
  const out = { day: null, total: null, room: null, known: true };
  if (finitePositive(dayLimit)) {
    const { net } = closedSince(deals, dayFrom);
    const sodBalance = balance - net;                          // (deposits and withdrawals during the day are not seen)
    let ref = sodBalance;
    let refNote = "start-of-day balance";
    if (rule === "higher") {
      if (Number.isFinite(sodEquity)) {
        ref = Math.max(sodBalance, sodEquity);
        refNote = "the higher of start-of-day balance and equity";
      } else {
        refNote = "start-of-day balance (the day's opening equity was not seen: open this panel before the day starts)";
      }
    }
    const loss = Math.max(0, ref - equity);
    out.day = { loss, limit: dayLimit, used: loss / dayLimit, light: light(loss, dayLimit), ref, refNote };
    if (!dealsOk) {
      out.known = false;
      out.day.light = "unknown";
    }
  }
  if (finitePositive(totalLimit)) {
    const base = totalMode === "trailing" ? Math.max(finitePositive(peak) ? peak : 0, finitePositive(initial) ? initial : 0) : initial;
    if (!finitePositive(base)) {
      out.known = false;
      out.total = { loss: null, limit: totalLimit, used: null, light: "unknown", ref: null,
                    refNote: "enter the account's starting balance" };
    } else {
      const loss = Math.max(0, base - equity);
      out.total = { loss, limit: totalLimit, used: loss / totalLimit, light: light(loss, totalLimit), ref: base,
                    refNote: totalMode === "trailing" ? "the highest balance or equity seen" : "the starting balance" };
    }
  }
  const rooms = [out.day, out.total].filter((x) => x && x.loss != null).map((x) => x.limit - x.loss);
  if (rooms.length) {
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
