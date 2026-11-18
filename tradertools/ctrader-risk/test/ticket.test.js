// The order request and the one place an order is sent (node --test).
import assert from "node:assert/strict";
import { test } from "node:test";
import { buildOrder, createPlacer } from "../site/js/ticket.js";

const EURUSD = { symbolId: 1, name: "EURUSD", digits: 5, pipPosition: 4, lotSize: 100000, minVolume: 1000, maxVolume: 1e7, volumeStep: 1000 };
const base = { symbol: EURUSD, side: "buy", orderType: "market", entry: 1.1, stop: 1.098, target: 1.104,
               quote: { bid: 1.09998, ask: 1.1 }, balance: 10000, riskMode: "percent", risk: 1, rate: 1, limitReached: false };

test("A market order carries its stop and target as pips, the volume and the planned risk in its label", () => {
  const r = buildOrder(base);
  assert.equal(r.ok, true);
  assert.deepEqual({ ...r.request }, { symbolId: 1, orderType: "market", side: "buy", volume: 50000, label: "ERT r=100.00", stopLossPips: 20, takeProfitPips: 40 });
  assert.equal(r.review.lots, 0.5);
  assert.ok(Object.isFrozen(r.request) && Object.isFrozen(r.review));
});

test("A limit or stop order carries prices, and must sit on the right side of the market", () => {
  const limit = buildOrder({ ...base, orderType: "limit", entry: 1.099, stop: 1.097, target: null });
  assert.equal(limit.ok, true);
  assert.deepEqual({ ...limit.request }, { symbolId: 1, orderType: "limit", side: "buy", volume: 50000, label: "ERT r=100.00", entryPrice: 1.099, stopLoss: 1.097 });
  assert.match(buildOrder({ ...base, orderType: "limit", entry: 1.101, stop: 1.099 }).message, /buy limit order must be below/);
  assert.match(buildOrder({ ...base, orderType: "stop", entry: 1.099, stop: 1.097 }).message, /buy stop order must be above/);
  assert.match(buildOrder({ ...base, side: "sell", orderType: "limit", entry: 1.0995, stop: 1.1015, target: null }).message, /sell limit order must be above/);
});

test("Nothing is built when the limit is reached, without a price, or with a target on the wrong side", () => {
  assert.equal(buildOrder({ ...base, limitReached: true }).code, "limit");
  assert.equal(buildOrder({ ...base, quote: null }).code, "quote");
  assert.match(buildOrder({ ...base, target: 1.099 }).message, /target must be above/);
  assert.equal(buildOrder({ ...base, stop: 1.1 }).code, "stop");
});

test("The placer sends a reviewed order exactly once, refuses a second tap, and never retries", async () => {
  const sent = [];
  let release;
  const placer = createPlacer((req) => { sent.push(req); return new Promise((res) => { release = res; }); });
  const { request } = buildOrder(base);
  const first = placer.place(request);
  const second = await placer.place(request);                   // a double tap while the first is in flight
  assert.equal(second.code, "busy");
  release({ orderId: 42 });
  assert.deepEqual(await first, { ok: true, answer: { orderId: 42 } });
  assert.equal((await placer.place(request)).code, "again");    // the same review cannot be sent twice
  assert.equal(sent.length, 1);
  const other = buildOrder(base).request;                       // a new review can
  release = null;
  const p = placer.place(other);
  release({ orderId: 43 });
  assert.equal((await p).ok, true);
  assert.equal(sent.length, 2);
});

test("A refusal and a silence are reported plainly, and the order is not sent again", async () => {
  const refuse = createPlacer(async () => { throw new Error("NOT_ENOUGH_MONEY"); });
  const r = await refuse.place(buildOrder(base).request);
  assert.equal(r.code, "rejected");
  assert.match(r.message, /NOT_ENOUGH_MONEY/);
  let calls = 0;
  const silent = createPlacer(() => { calls++; return new Promise(() => {}); }, 20);
  const t = await silent.place(buildOrder(base).request);
  assert.equal(t.code, "timeout");
  assert.match(t.message, /Check your positions/);
  assert.equal(calls, 1);
});
