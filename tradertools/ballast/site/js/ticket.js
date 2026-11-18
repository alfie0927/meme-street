// Ballast: from what the trader typed to one order request, or a plain reason why not; and the one place an order
// is sent. Pure apart from `createPlacer`, which only calls the `send` function it is given.
import { makeLabel } from "./journal.js";
import { pipSize, pointsToPips, roundPrice, sizeTrade, toPoints } from "./risk.js";

function fail(code, message, key = code) {
  return { ok: false, code, message, key };
}

/**
 * input: everything sizeTrade takes, plus { symbol: {symbolId, name, digits, pipPosition, isPredictionMarket, ...},
 *        orderType: "market"|"limit"|"stop", target (or null), quote: {bid, ask}, accountType, positionOnSymbol (bool),
 *        limitsKnown (false when the limits could not be read), tradeId }
 * returns { ok: true, request, review } or { ok: false, code, message }
 *
 * A market order carries its stop and target as distances in pips, measured by the platform from the fill, so the
 * risk reviewed holds whatever the fill price. A limit or stop order carries them as prices, rounded to the symbol.
 * Every stop is triggered by the price the position would close at (`stopLossTriggerMethod: "trade"`: a buy's stop
 * on the bid, a sell's on the ask), which is what the loss is computed on.
 */
export function buildOrder(input) {
  const { symbol, side, orderType, entry, stop, target, quote } = input;
  if (input.limitsKnown === false) return fail("limits", "Your loss limits could not be checked (the account's history did not load). Nothing is placed until they can.", "limitsUnknown");
  if (input.accountType === "spreadBetting") return fail("account", "This is a spread-betting account: sizes there are stakes per point, which this panel does not size. Use the platform's own ticket.", "spreadBetting");
  if (!symbol) return fail("symbol", "Open the panel on a symbol first.", "noSymbol");
  if (symbol.isPredictionMarket) return fail("symbol", "This is a prediction-market symbol, which this panel does not size.", "prediction");
  if (input.accountType === "netted" && input.positionOnSymbol) {
    return fail("netted", `This is a netting account and you already hold ${symbol.name}: a new order would change that position instead of opening its own. Close it first, or use the platform's own ticket.`, "netted");
  }
  if (!["market", "limit", "stop"].includes(orderType)) return fail("type", "Choose market, limit or stop.");
  if (!quote || !(quote.bid > 0) || !(quote.ask > 0)) return fail("quote", "No live price for this symbol yet.", "noQuote");
  const pip = pipSize(symbol.pipPosition);
  if (orderType === "market") {
    const gap = side === "buy" ? quote.bid - stop : stop - quote.ask;      // (from the price the stop is triggered by)
    if (stop > 0 && gap < pip - 1e-12) {
      return fail("stop", `The stop is too close: it must be at least 1 pip beyond the ${side === "buy" ? "bid" : "ask"}, or it would be hit as soon as the order fills.`, "stopTooClose");
    }
  } else {
    const now = side === "buy" ? quote.ask : quote.bid;
    const ok = orderType === "limit" ? (side === "buy" ? entry < now : entry > now) : (side === "buy" ? entry > now : entry < now);
    if (!ok) {
      const where = (orderType === "limit") === (side === "buy") ? "below" : "above";
      return fail("entry", `A ${side} ${orderType} order must be ${where} the current price.`, "entrySide");
    }
  }
  const size = sizeTrade(input);
  if (!size.ok) return size;
  if (orderType !== "market") {
    // A pending order fills when the price reaches its entry; the stop is then watched on the other side of today's
    // spread (a buy's on the bid), so it must clear entry minus the spread (plus for a sell) by a pip, or it fires at once.
    const spread = quote.ask - quote.bid;
    const edge = side === "buy" ? entry - spread : entry + spread;
    const gap = side === "buy" ? edge - stop : stop - edge;
    if (gap < pip - 1e-12) {
      const min = roundPrice(side === "buy" ? edge - pip : edge + pip, symbol.digits);
      return { ...fail("stop", `The stop is too close: with today's spread it must be ${side === "buy" ? "at or below" : "at or above"} ${min}, or it would be hit as soon as the order fills.`, "stopTooClosePending"), min };
    }
  }
  if (target != null && target !== "") {
    if (!(target > 0)) return fail("target", "The target price is not valid.", "targetInvalid");
    if (side === "buy" ? !(target > entry) : !(target < entry)) {
      return fail("target", side === "buy" ? "For a buy, the target must be above the entry." : "For a sell, the target must be below the entry.", "targetSide");
    }
  }
  const request = { symbolId: symbol.symbolId, orderType, side, volume: size.volume, stopLossTriggerMethod: "trade",
                    label: makeLabel(size.riskMoney, input.tradeId || "x0000000") };
  if (orderType === "market") {
    request.stopLossPips = size.pips;
    if (target) request.takeProfitPips = pointsToPips(Math.abs(toPoints(target, symbol.digits) - toPoints(entry, symbol.digits)), symbol.digits, symbol.pipPosition);
  } else {
    request.entryPrice = roundPrice(entry, symbol.digits);
    request.stopLoss = roundPrice(stop, symbol.digits);
    if (target) request.takeProfit = roundPrice(target, symbol.digits);
  }
  const review = Object.freeze({
    symbol: symbol.name, side, orderType, entry, stop, target: target || null, lots: size.lots, units: size.units,
    riskMoney: size.riskMoney, priceRisk: size.priceRisk, commissionRisk: size.commissionRisk, budget: size.budget,
    cut: size.cut, pips: size.pips, capped: size.capped, leverage: size.leverage,
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
        // (the platform's own timeout is not a refusal: the order may still have been placed)
        if (e && (e.code === "TIMEOUT" || /timed? ?out/i.test(String(e.message || "")))) {
          return { ok: false, code: "timeout", message: "No answer from cTrader. Check your positions and orders before trying again." };
        }
        return { ok: false, code: "rejected", message: `cTrader refused the order: ${(e && (e.message || e.code)) || "unknown reason"}.` };
      } finally {
        clearTimeout(timer);
        busy = false;
      }
    },
  };
}
