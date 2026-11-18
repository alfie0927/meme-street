// The only file that talks to cTrader (Plugin API v2 through the vendored SDK). Everything the panel needs from the
// platform goes through these few functions, so a change in the SDK is a change here only. host-mock.js offers the
// same functions over fixed data for local work and the browser test.
import {
  accountInfo, asset, cancelOrder, createClientAdapter, dealHistory, firstValueFrom, handshake, newOrder,
  subscribeExecutions, subscribeQuotes, symbolByName, symbols,
} from "../vendor/ctrader-sdk.js";

const call = (fn, payload) => firstValueFrom(fn(adapter, payload, { timeoutMs: 10000 }));
let adapter = null;

export const kind = "ctrader";

/** Connects to the cTrader window this page runs in. Returns what the host says about itself. */
export async function connect() {
  adapter = createClientAdapter();
  return firstValueFrom(handshake(adapter));
}

/** { balance, equity, currency, environment: "demo"|"live", accountType } */
export async function account() {
  const a = await call(accountInfo, null);
  return { balance: a.balance, equity: a.equity ?? null, currency: a.depositCurrency || "", environment: a.environmentType,
           accountType: a.accountType, raw: a };
}

/** One symbol's trading details, or null. `unitsPerVolume`: see risk.js and the README's probe. */
export async function symbol(name) {
  const r = await call(symbolByName, { name });
  const s = r.symbols && r.symbols[0];
  if (!s) return null;
  return { symbolId: s.symbolId, name: s.name, digits: s.digits, pipPosition: s.pipPosition, lotSize: s.lotSize,
           minVolume: s.minVolume, maxVolume: s.maxVolume, volumeStep: s.volumeStep, baseAssetId: s.baseAssetId,
           quoteAssetId: s.quoteAssetId, isMarketOpen: s.isMarketOpen, unitsPerVolume: UNITS_PER_VOLUME, raw: s };
}

// ponytail: set from the probe of 25 November 2026 (README "Probe"); 1 if the API counts volume in units.
export const UNITS_PER_VOLUME = 1;

/** Every symbol, light: { id, name, baseAssetId, quoteAssetId } (for the conversion into the account's currency). */
export async function symbolList() {
  return (await call(symbols, null)).symbols || [];
}

/** [{ assetId, name }] for the ids asked. */
export async function assets(ids) {
  if (!ids.length) return [];
  return (await call(asset, { assetId: ids })).assets || [];
}

/** Live quotes for these symbols: calls onQuote({ symbolId, bid, ask }). Returns a function that stops them. */
export function quotes(symbolIds, onQuote) {
  const sub = subscribeQuotes(adapter, { symbolIds }).subscribe({ next: onQuote, error: () => {} });
  return () => sub.unsubscribe();
}

/** Calls cb on every execution event (a fill, a close, a cancel). Returns a function that stops it. */
export function onExecution(cb) {
  const sub = subscribeExecutions(adapter, null).subscribe({ next: cb, error: () => {} });
  return () => sub.unsubscribe();
}

/** Closed deals between two times (ms). Plugin API v2 DealSummary objects. */
export async function deals(fromMs, toMs) {
  const r = await call(dealHistory, { fromTimestamp: new Date(fromMs).toISOString(), toTimestamp: new Date(toMs).toISOString() });
  return r.deals || [];
}

/** Sends one order (ticket.js createPlacer is the only caller). Resolves { orderId } or rejects with the reason. */
export function placeOrder(request) {
  return call(newOrder, { ...request });
}

/** Cancels a pending order (the probe's limit-order test). */
export function cancel(orderId) {
  return call(cancelOrder, { orderId });
}
