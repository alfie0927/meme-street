// From what the trader typed to one order request, or a plain reason why not; and the one place an order is sent.
// Pure apart from `createPlacer`, which only calls the `send` function it is given.
import { makeLabel, pointsToPips, sizeTrade, toPoints } from "./risk.js";

function fail(code, message) {
  return { ok: false, code, message };
}

/**
 * input: { symbol: {symbolId, name, digits, pipPosition, ...}, side, orderType: "market"|"limit"|"stop",
 *          entry, stop, target (or null), quote: {bid, ask}, balance, riskMode, risk, rate, limitReached }
 * returns { ok: true, request, review } or { ok: false, code, message }
 *
 * A market order carries its stop and target as distances in pips (the platform measures them from the fill), so
 * the risk stays the one reviewed even if the price moves before it fills. A limit or stop order carries them as
 * prices.
 */
export function buildOrder(input) {
  const { symbol, side, orderType, entry, stop, target, quote, limitReached } = input;
  if (limitReached) return fail("limit", "Your loss limit for today is reached. This panel will not place orders until it resets.");
  if (!symbol) return fail("symbol", "Open the panel on a symbol first.");
  if (!["market", "limit", "stop"].includes(orderType)) return fail("type", "Choose market, limit or stop.");
  if (!quote || !(quote.bid > 0) || !(quote.ask > 0)) return fail("quote", "No live price for this symbol yet.");
  if (orderType !== "market") {
    const now = side === "buy" ? quote.ask : quote.bid;
    const ok = orderType === "limit" ? (side === "buy" ? entry < now : entry > now) : (side === "buy" ? entry > now : entry < now);
    if (!ok) {
      const where = (orderType === "limit") === (side === "buy") ? "below" : "above";
      return fail("entry", `A ${side} ${orderType} order must be ${where} the current price.`);
    }
  }
  const size = sizeTrade(input);
  if (!size.ok) return size;
  if (target != null && target !== "") {
    if (!(target > 0)) return fail("target", "The target price is not valid.");
    if (side === "buy" ? !(target > entry) : !(target < entry)) {
      return fail("target", side === "buy" ? "For a buy, the target must be above the entry." : "For a sell, the target must be below the entry.");
    }
  }
  const request = { symbolId: symbol.symbolId, orderType, side, volume: size.volume, label: makeLabel(size.riskMoney) };
  if (orderType === "market") {
    request.stopLossPips = size.pips;
    if (target) request.takeProfitPips = pointsToPips(Math.abs(toPoints(target, symbol.digits) - toPoints(entry, symbol.digits)), symbol.digits, symbol.pipPosition);
  } else {
    request.entryPrice = entry;
    request.stopLoss = stop;
    if (target) request.takeProfit = target;
  }
  const review = Object.freeze({
    symbol: symbol.name, side, orderType, entry, stop, target: target || null,
    lots: size.lots, units: size.units, riskMoney: size.riskMoney, budget: size.budget, pips: size.pips, capped: size.capped,
  });
  return { ok: true, request: Object.freeze(request), review };
}

/**
 * The only way an order leaves this panel. `place(request)` sends it once: a second call while one is in flight,
 * or for the same reviewed request again, does nothing. There are no retries: if the platform does not answer
 * within `timeoutMs`, the result says to check the positions, because the order may still have been placed.
 */
export function createPlacer(send, timeoutMs = 10000) {
  let busy = false;
  const sent = new WeakSet();
  return {
    get busy() {
      return busy;
    },
    async place(request) {
      if (busy) return { ok: false, code: "busy", message: "An order is already being sent." };
      if (sent.has(request)) return { ok: false, code: "again", message: "This order was already sent. Review it again to send another." };
      busy = true;
      sent.add(request);
      let timer;
      try {
        const answer = await Promise.race([
          send(request),
          new Promise((resolve) => {
            timer = setTimeout(() => resolve({ timeout: true }), timeoutMs);
          }),
        ]);
        if (answer && answer.timeout) {
          return { ok: false, code: "timeout", message: "No answer from cTrader. Check your positions and orders before trying again." };
        }
        return { ok: true, answer };
      } catch (e) {
        return { ok: false, code: "rejected", message: `cTrader refused the order: ${(e && (e.message || e.code)) || "unknown reason"}.` };
      } finally {
        clearTimeout(timer);
        busy = false;
      }
    },
  };
}
