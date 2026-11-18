// The same functions as host.js over fixed data: a 10,000 USD demo account and a few symbols of every kind. Used
// with ?mock=1 for local work and by tests/test_tradertools.py, which drives it through window.__mock. It never
// talks to cTrader and can place nothing real.
export const kind = "mock";
export const UNITS_PER_VOLUME = 1;

const ASSETS = { 1: "USD", 2: "EUR", 3: "GBP", 4: "JPY", 5: "XAU", 6: "BTC", 7: "US500" };
const SYMBOLS = [
  { symbolId: 1, name: "EURUSD", digits: 5, pipPosition: 4, lotSize: 100000, minVolume: 1000, maxVolume: 10000000, volumeStep: 1000, baseAssetId: 2, quoteAssetId: 1 },
  { symbolId: 2, name: "GBPUSD", digits: 5, pipPosition: 4, lotSize: 100000, minVolume: 1000, maxVolume: 10000000, volumeStep: 1000, baseAssetId: 3, quoteAssetId: 1 },
  { symbolId: 3, name: "USDJPY", digits: 3, pipPosition: 2, lotSize: 100000, minVolume: 1000, maxVolume: 10000000, volumeStep: 1000, baseAssetId: 1, quoteAssetId: 4 },
  { symbolId: 4, name: "EURJPY", digits: 3, pipPosition: 2, lotSize: 100000, minVolume: 1000, maxVolume: 10000000, volumeStep: 1000, baseAssetId: 2, quoteAssetId: 4 },
  { symbolId: 5, name: "XAUUSD", digits: 2, pipPosition: 1, lotSize: 100, minVolume: 1, maxVolume: 10000, volumeStep: 1, baseAssetId: 5, quoteAssetId: 1 },
  { symbolId: 6, name: "US500", digits: 1, pipPosition: 0, lotSize: 1, minVolume: 0.1, maxVolume: 1000, volumeStep: 0.1, baseAssetId: 7, quoteAssetId: 1 },
  { symbolId: 7, name: "BTCUSD", digits: 2, pipPosition: 0, lotSize: 1, minVolume: 0.01, maxVolume: 100, volumeStep: 0.01, baseAssetId: 6, quoteAssetId: 1 },
];
const QUOTES = { 1: [1.09998, 1.1], 2: [1.24998, 1.25], 3: [149.998, 150], 4: [159.998, 160], 5: [2399.8, 2400], 6: [4999.5, 5000], 7: [59990, 60000] };

const state = { balance: 10000, currency: "USD", sent: [], deals: [], listeners: [], execs: [], answer: null };
window.__mock = state;                       // (the browser test reads what was sent and adds closed deals)

export async function connect() {
  return { hostKind: "web", hostVersion: "mock", requestTypes: [], subscriptionTypes: [] };
}

export async function account() {
  return { balance: state.balance, equity: state.balance, currency: state.currency, environment: "demo", accountType: "hedged" };
}

export async function symbol(name) {
  const s = SYMBOLS.find((x) => x.name === name);
  return s ? { ...s, isMarketOpen: true, unitsPerVolume: UNITS_PER_VOLUME } : null;
}

export async function symbolList() {
  return SYMBOLS.map((s) => ({ id: s.symbolId, name: s.name, baseAssetId: s.baseAssetId, quoteAssetId: s.quoteAssetId }));
}

export async function assets(ids) {
  return ids.filter((id) => ASSETS[id]).map((id) => ({ assetId: id, name: ASSETS[id] }));
}

export function quotes(symbolIds, onQuote) {
  const t = setTimeout(() => symbolIds.forEach((id) => QUOTES[id] && onQuote({ symbolId: id, bid: QUOTES[id][0], ask: QUOTES[id][1] })), 0);
  return () => clearTimeout(t);
}

export function onExecution(cb) {
  state.execs.push(cb);
  return () => { state.execs = state.execs.filter((f) => f !== cb); };
}

export async function deals(fromMs, toMs) {
  return state.deals.filter((d) => {
    const t = Date.parse(d.closingTime || d.openingTime);
    return t >= fromMs && t <= toMs;
  });
}

/** Records the order. `state.answer` set to "hang" makes the next one never answer; "refuse" makes it fail. */
export function placeOrder(request) {
  state.sent.push(request);
  if (state.answer === "hang") return new Promise(() => {});
  if (state.answer === "refuse") return Promise.reject(new Error("MOCK_REFUSED"));
  return new Promise((resolve) => setTimeout(() => resolve({ orderId: 1000 + state.sent.length }), 150));
}

export async function cancel() {
  return {};
}
