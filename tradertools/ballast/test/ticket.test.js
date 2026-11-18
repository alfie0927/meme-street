// The order request and the one place an order is sent (node --test).
import assert from "node:assert/strict";
import { test } from "node:test";
import { buildOrder, createPlacer } from "../site/js/ticket.js";

const EURUSD = { symbolId: 1, name: "EURUSD", digits: 5, pipPosition: 4, lotSize: 100000, minVolume: 1000, maxVolume: 1e7, volumeStep: 1000 };
const base = { symbol: EURUSD, side: "buy", orderType: "market", entry: 1.1, stop: 1.098, target: 1.104, quote: { bid: 1.09998, ask: 1.1 },
               balance: 10000, riskMode: "percent", risk: 1, rate: 1, accountType: "hedged", tradeId: "abcd1234" };

test("A market order: stop and target in pips, the stop triggered on the closing price, risk and id in the label", () => {
  const r = buildOrder(base);
  assert.equal(r.ok, true);
  assert.deepEqual({ ...r.request }, { symbolId: 1, orderType: "market", side: "buy", volume: 50000, stopLossTriggerMethod: "trade",
                                       label: "BLST r=100.00 id=abcd1234", stopLossPips: 20, takeProfitPips: 40 });
  assert.ok(Object.isFrozen(r.request) && Object.isFrozen(r.review));
});

test("A stop inside the spread, or less than a pip beyond the closing price, is refused (audit 3)", () => {
  assert.match(buildOrder({ ...base, stop: 1.09999 }).message, /at least 1 pip beyond the bid/);
  assert.match(buildOrder({ ...base, stop: 1.09991 }).message, /too close/);                 // 0.7 pip beyond the bid
  assert.equal(buildOrder({ ...base, stop: 1.09988 }).ok, true);                             // 1.0 pip beyond the bid
  assert.match(buildOrder({ ...base, side: "sell", stop: 1.09999, target: null }).message, /beyond the ask/);
  assert.match(buildOrder({ ...base, side: "sell", stop: 1.10005, target: null }).message, /too close/);
});

test("Limit and stop orders carry prices rounded to the symbol, on the right side of the market (audit 12)", () => {
  const r = buildOrder({ ...base, orderType: "limit", entry: 1.099004, stop: 1.097001, target: 1.103003 });
  assert.deepEqual([r.request.entryPrice, r.request.stopLoss, r.request.takeProfit], [1.099, 1.097, 1.103]);
  assert.equal(r.request.stopLossTriggerMethod, "trade");
  assert.match(buildOrder({ ...base, orderType: "limit", entry: 1.101, stop: 1.099 }).message, /buy limit order must be below/);
  assert.match(buildOrder({ ...base, orderType: "stop", entry: 1.099, stop: 1.097 }).message, /buy stop order must be above/);
});

test("Spread betting, netting with a position open, prediction markets and unknown limits are refused (audit 6, 10)", () => {
  assert.equal(buildOrder({ ...base, accountType: "spreadBetting" }).code, "account");
  assert.equal(buildOrder({ ...base, accountType: "netted", positionOnSymbol: true }).code, "netted");
  assert.equal(buildOrder({ ...base, accountType: "netted", positionOnSymbol: false }).ok, true);
  assert.equal(buildOrder({ ...base, symbol: { ...EURUSD, isPredictionMarket: true } }).code, "symbol");
  assert.equal(buildOrder({ ...base, limitsKnown: false }).code, "limits");
});

test("The limits' room cuts the size; no room refuses; the review shows the cut", () => {
  const r = buildOrder({ ...base, room: 50 });
  assert.equal(r.request.volume, 25000);
  assert.equal(r.review.cut, true);
  assert.equal(buildOrder({ ...base, room: 0 }).code, "limit");
});

test("No price, or a target on the wrong side, builds nothing", () => {
  assert.equal(buildOrder({ ...base, quote: null }).code, "quote");
  assert.match(buildOrder({ ...base, target: 1.099 }).message, /target must be above/);
});

test("The placer sends a reviewed order exactly once, refuses a second tap, and never retries", async () => {
  const sent = [];
  let release;
  const placer = createPlacer((req) => { sent.push(req); return new Promise((res) => { release = res; }); });
  const { request } = buildOrder(base);
  const first = placer.place(request);
  assert.equal((await placer.place(request)).code, "busy");
  release({ orderId: 42 });
  assert.deepEqual(await first, { ok: true, answer: { orderId: 42 } });
  assert.equal((await placer.place(request)).code, "again");
  assert.equal(sent.length, 1);
});

test("A refusal and a silence are reported plainly, and the order is not sent again", async () => {
  const r = await createPlacer(async () => { throw new Error("NOT_ENOUGH_MONEY"); }).place(buildOrder(base).request);
  assert.match(r.message, /NOT_ENOUGH_MONEY/);
  let calls = 0;
  const t = await createPlacer(() => { calls++; return new Promise(() => {}); }, 20).place(buildOrder(base).request);
  assert.match(t.message, /Check your positions/);
  assert.equal(calls, 1);
});

test("A pending order's stop must clear the spread at the fill, or it fires at once (second audit C1)", () => {
  // quote 1.09998 / 1.10000: a buy limit at 1.09900 fills when the ask is there, with the bid at 1.09898
  const lim = { ...base, orderType: "limit", entry: 1.099, target: null };
  assert.equal(buildOrder({ ...lim, stop: 1.09899 }).key, "stopTooClosePending");
  assert.equal(buildOrder({ ...lim, stop: 1.09889 }).key, "stopTooClosePending");
  const ok = buildOrder({ ...lim, stop: 1.09888 });
  assert.equal(ok.ok, true);                                   // exactly 1 pip below 1.09898
  assert.equal(buildOrder({ ...lim, stop: 1.09899 }).min, 1.09888);
  // a sell stop at 1.09900 fills on the bid, with the ask at 1.09902: the stop must be at 1.09912 or above
  const sst = { ...base, side: "sell", orderType: "stop", entry: 1.099, target: null };
  assert.equal(buildOrder({ ...sst, stop: 1.09911 }).key, "stopTooClosePending");
  assert.equal(buildOrder({ ...sst, stop: 1.09912 }).ok, true);
});
