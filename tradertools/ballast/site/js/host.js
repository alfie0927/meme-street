// Ballast: the only file that talks to cTrader (Plugin API v2, through the vendored SDK). Everything the panel needs
// from the platform goes through these functions, so a change in the SDK is a change here only. host-mock.js offers
// the same functions over fixed data for local work and the browser test.
import {
  accountInfo, asset, availablePeriods, cancelOrder, createClientAdapter, dealHistory, firstValueFrom, handshake,
  newOrder, pendingOrders as pendingOrdersReq, positions as positionsReq, subscribeExecutions, subscribeQuotes, symbolById, symbolByName, symbols,
  trendbars,
} from "../vendor/ctrader-sdk.js";
import { readDeals } from "./history.js";

let adapter = null;
const call = (fn, payload) => firstValueFrom(fn(adapter, payload, { timeoutMs: 10000 }));

export const kind = "ctrader";
// Set from the demo-account probe (README "Probe"): 1 if the API counts volume in units of the base asset. Until
// VOLUME_CHECKED is true the panel sizes trades but does not place them: a wrong unit would scale every order.
export const UNITS_PER_VOLUME = 1;
export const VOLUME_CHECKED = false;

/** Connects to the cTrader window this page runs in. Returns what the host says about itself. */
export async function connect() {
  adapter = createClientAdapter();
  return firstValueFrom(handshake(adapter));
}

/** { login, balance, equity, currency, environment: "demo"|"live", accountType, isLimitedRisk } */
export async function account() {
  const a = await call(accountInfo, null);
  const equity = Number.isFinite(a.equity) ? a.equity : Number.isFinite(a.unrealizedNetPnl) ? a.balance + a.unrealizedNetPnl : null;
  return { login: a.login, balance: a.balance, equity, currency: a.depositCurrency || "", environment: a.environmentType,
           accountType: a.accountType, isLimitedRisk: a.isLimitedRisk };
}

function details(s) {
  return { symbolId: s.symbolId, name: s.name, digits: s.digits, pipPosition: s.pipPosition, lotSize: s.lotSize,
           minVolume: s.minVolume, maxVolume: s.maxVolume, volumeStep: s.volumeStep, baseAssetId: s.baseAssetId,
           quoteAssetId: s.quoteAssetId, isMarketOpen: s.isMarketOpen, isPredictionMarket: !!s.isPredictionMarket,
           feeRate: s.pnlConversionFeeRate || 0, unitsPerVolume: UNITS_PER_VOLUME };
}

/** One symbol's trading details by name, or null. */
export async function symbol(name) {
  const s = ((await call(symbolByName, { name })).symbols || [])[0];
  return s ? details(s) : null;
}

/** Several symbols' details by id. */
export async function symbolsById(ids) {
  if (!ids.length) return [];
  return ((await call(symbolById, { symbolId: ids })).symbols || []).map(details);
}

/** Every symbol, light: { id, name, baseAssetId, quoteAssetId } (for conversions into the account's money). */
export async function symbolList() {
  return (await call(symbols, null)).symbols || [];
}

/** [{ assetId, name }] for the ids asked. */
export async function assets(ids) {
  if (!ids.length) return [];
  return (await call(asset, { assetId: ids })).assets || [];
}

/** Live quotes: calls onQuote({ symbolId, bid, ask }); either side may be missing from one event; onError if the stream
 *  fails. Returns a stop function. */
export function quotes(symbolIds, onQuote, onError = () => {}) {
  if (!symbolIds.length) return () => {};
  const sub = subscribeQuotes(adapter, { symbolIds }).subscribe({ next: onQuote, error: onError, complete: onError });
  return () => sub.unsubscribe();
}

/** Calls cb on every execution event (a fill, a close, a cancel). Returns a stop function. */
export function onExecution(cb) {
  const sub = subscribeExecutions(adapter, null).subscribe({ next: cb, error: () => {} });
  return () => sub.unsubscribe();
}

/** Open positions: [{ positionId, symbolId, symbolName, side, volume, entryPrice, stopLoss, takeProfit, netPnl }]. */
export async function positions() {
  return (await call(positionsReq, null)).positions || [];
}

/** Pending orders: [{ orderId, symbolId, symbolName, side, type, volume, entryPrice, stopLoss, takeProfit }]. */
export async function pendingOrders() {
  return (await call(pendingOrdersReq, null)).pendingOrders || [];
}

/** Closed deals between two times (ms), read in full: { deals, complete }. */
export function deals(fromMs, toMs) {
  return readDeals(async (a, b) => {
    const r = await call(dealHistory, { fromTimestamp: new Date(a).toISOString(), toTimestamp: new Date(b).toISOString() });
    return { deals: r.deals || [], hasMore: !!r.hasMore };
  }, fromMs, toMs);
}

/** The chart periods the platform offers: [{ code, name }]. */
export async function periods() {
  return (await call(availablePeriods, null)).periods || [];
}

/** The last `count` bars of a symbol: [{ timestamp, open, high, low, close }], oldest first. */
export async function bars(symbolId, period, count) {
  const r = await call(trendbars, { symbolId, period, count });
  return (r.bars || []).slice().sort((a, b) => (a.timestamp < b.timestamp ? -1 : 1));
}

/** Sends one order (ticket.js createPlacer is the only caller). Resolves { orderId } or rejects with the reason. */
export function placeOrder(request) {
  // (a longer wait than createPlacer's 10 s, so the placer's own timeout, which holds the order's risk, comes first)
  return firstValueFrom(newOrder(adapter, { ...request }, { timeoutMs: 60000 }));
}

/** Cancels a pending order (the probe's limit-order test). */
export function cancel(orderId) {
  return call(cancelOrder, { orderId });
}
