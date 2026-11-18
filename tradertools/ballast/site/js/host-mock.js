// Ballast: the same functions as host.js over fixed data: a 10,000 USD demo account, symbols of every kind, two open
// positions (one without a stop) and a few closed trades. Used with ?mock=1 for local work, screenshots and
// tests/test_tradertools.py, which drives it through window.__mock. It never talks to cTrader and places nothing real.
export const kind = "mock";
export const UNITS_PER_VOLUME = 1;
export const VOLUME_CHECKED = true;

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
const now = Date.now();
const iso = (ms) => new Date(ms).toISOString();

const state = {
  login: 5550123, balance: 10000, equity: 9960, currency: "USD", accountType: "hedged", sent: [], listeners: [], execs: [],
  answer: null, failDeals: false, failPositions: false, orders: [],
  positions: [
    { positionId: 11, symbolId: 1, symbolName: "EURUSD", side: "buy", volume: 20000, entryPrice: 1.1015, stopLoss: 1.0990, takeProfit: 1.1065, netPnl: -34, openTimestamp: iso(now - 2 * 3600000) },
    { positionId: 12, symbolId: 5, symbolName: "XAUUSD", side: "sell", volume: 2, entryPrice: 2397, stopLoss: null, takeProfit: null, netPnl: -6, openTimestamp: iso(now - 3600000) },
  ],
  deals: [
    { dealId: 101, symbolName: "EURUSD", openingDirection: "buy", openingTime: iso(now - 3 * 86400000), closingTime: iso(now - 3 * 86400000 + 3600000), netProfit: 152, label: "BLST r=75.00 id=mock0001" },
    { dealId: 102, symbolName: "XAUUSD", openingDirection: "sell", openingTime: iso(now - 2 * 86400000), closingTime: iso(now - 2 * 86400000 + 7200000), netProfit: -75, label: "BLST r=75.00 id=mock0002" },
    { dealId: 103, symbolName: "GBPUSD", openingDirection: "buy", openingTime: iso(now - 26 * 3600000), closingTime: iso(now - 25 * 3600000), netProfit: 40, label: "BLST r=80.00 id=mock0003" },
    { dealId: 104, symbolName: "GBPUSD", openingDirection: "buy", openingTime: iso(now - 26 * 3600000), closingTime: iso(now - 24.5 * 3600000), netProfit: 80, label: "BLST r=80.00 id=mock0003" },
  ],
};
window.__mock = state;

export async function connect() {
  return { hostKind: "web", hostVersion: "mock", requestTypes: [], subscriptionTypes: [] };
}

export async function account() {
  return { login: state.login, balance: state.balance, equity: state.equity, currency: state.currency, environment: "demo",
           accountType: state.accountType, isLimitedRisk: false };
}

const details = (s) => ({ ...s, isMarketOpen: true, isPredictionMarket: false, feeRate: 0, unitsPerVolume: UNITS_PER_VOLUME });

export async function symbol(name) {
  const s = SYMBOLS.find((x) => x.name === name);
  return s ? details(s) : null;
}

export async function symbolsById(ids) {
  return SYMBOLS.filter((s) => ids.includes(s.symbolId)).map(details);
}

export async function symbolList() {
  return SYMBOLS.map((s) => ({ id: s.symbolId, name: s.name, baseAssetId: s.baseAssetId, quoteAssetId: s.quoteAssetId }));
}

export async function assets(ids) {
  return ids.filter((id) => ASSETS[id]).map((id) => ({ assetId: id, name: ASSETS[id] }));
}

export function quotes(symbolIds, onQuote) {
  const send = () => symbolIds.forEach((id) => QUOTES[id] && onQuote({ symbolId: id, bid: QUOTES[id][0], ask: QUOTES[id][1] }));
  const t = setTimeout(send, 0);
  const every = setInterval(send, 5000);                       // (a live feed ticks: the panel distrusts a silent one)
  return () => { clearTimeout(t); clearInterval(every); };
}

export function onExecution(cb) {
  state.execs.push(cb);
  return () => { state.execs = state.execs.filter((f) => f !== cb); };
}

export async function positions() {
  if (state.failPositions) throw new Error("MOCK_POSITIONS");
  return state.positions.map((p) => ({ ...p }));
}

export async function pendingOrders() {
  return state.orders.map((o) => ({ ...o }));
}

export async function deals(fromMs, toMs) {
  if (state.failDeals) return { deals: [], complete: false };
  return { deals: state.deals.filter((d) => { const t = Date.parse(d.closingTime); return t >= fromMs && t <= toMs; }), complete: true };
}

export async function periods() {
  return [{ code: "m15", name: "15 Minutes" }, { code: "h1", name: "1 Hour" }, { code: "h4", name: "4 Hours" }, { code: "d1", name: "Daily" }];
}

/** Bars with a true range of exactly 0.0012 (12 pips) on EURUSD, so the ATR is 0.0012; other symbols scale. */
export async function bars(symbolId, period, count) {
  const q = QUOTES[symbolId];
  const mid = (q[0] + q[1]) / 2;
  const r = mid * 0.0012 / 1.1;
  return Array.from({ length: count }, (_, i) => ({ timestamp: iso(now - (count - i) * 3600000), open: mid, high: mid + r / 2, low: mid - r / 2, close: mid }));
}

/** Records the order. `state.answer` "hang": never answers; "refuse": fails. */
export function placeOrder(request) {
  state.sent.push(request);
  if (state.answer === "hang") return new Promise(() => {});
  if (state.answer === "refuse") return Promise.reject(new Error("MOCK_REFUSED"));
  return new Promise((resolve) => setTimeout(() => resolve({ orderId: 1000 + state.sent.length }), 150));
}

export async function cancel() {
  return {};
}
