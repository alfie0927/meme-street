// Worked examples for the sizing maths (node --test). Volumes here are in units (unitsPerVolume 1); one case checks
// that a platform counting in hundredths gives the same trade.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  conversionPath, conversionRate, dayStart, lossLight, makeLabel, parseLabel, pointsToPips, realisedLossSince,
  rewardRisk, sizeTrade, summary, targetFromR, tradeLog,
} from "../site/js/risk.js";

const FX = { digits: 5, pipPosition: 4, lotSize: 100000, minVolume: 1000, maxVolume: 10000000, volumeStep: 1000 };
const JPY = { digits: 3, pipPosition: 2, lotSize: 100000, minVolume: 1000, maxVolume: 10000000, volumeStep: 1000 };
const INDEX = { digits: 1, pipPosition: 0, lotSize: 1, minVolume: 0.1, maxVolume: 1000, volumeStep: 0.1 };
const GOLD = { digits: 2, pipPosition: 1, lotSize: 100, minVolume: 1, maxVolume: 10000, volumeStep: 1 };
const BTC = { digits: 2, pipPosition: 0, lotSize: 1, minVolume: 0.01, maxVolume: 100, volumeStep: 0.01 };
const near = (a, b, tol = 1e-6) => assert.ok(Math.abs(a - b) <= tol, `${a} is not ${b}`);

test("EURUSD in a USD account: 1% of 10,000 over 20 pips is 0.50 lots, exactly on the boundary", () => {
  const r = sizeTrade({ balance: 10000, riskMode: "percent", risk: 1, side: "buy", entry: 1.1, stop: 1.098, rate: 1, symbol: FX });
  assert.equal(r.ok, true);
  assert.equal(r.volume, 50000);
  assert.equal(r.lots, 0.5);
  near(r.riskMoney, 100);
  assert.equal(r.pips, 20);
});

test("EURUSD in a GBP account: 1% of 5,000 over 25 pips with GBPUSD bid 1.2500 is 0.25 lots", () => {
  const path = conversionPath([{ id: 7, baseAssetId: 2, quoteAssetId: 1 }], 1, 2);   // USD (1) -> GBP (2) through GBPUSD
  assert.deepEqual(path, [{ symbolId: 7, invert: true }]);
  const { rate } = conversionRate(path, { 7: { bid: 1.25, ask: 1.2502 } });
  near(rate, 0.8);
  const r = sizeTrade({ balance: 5000, riskMode: "percent", risk: 1, side: "buy", entry: 1.1, stop: 1.0975, rate, symbol: FX });
  assert.equal(r.lots, 0.25);
  near(r.riskMoney, 50);
});

test("USDJPY short in a USD account: 0.5% of 10,000 over 30 pips is 0.25 lots", () => {
  const rate = 1 / 150.3;                                                              // JPY -> USD at the ask side of USDJPY
  const r = sizeTrade({ balance: 10000, riskMode: "percent", risk: 0.5, side: "sell", entry: 150.0, stop: 150.3, rate, symbol: JPY });
  assert.equal(r.ok, true);
  assert.equal(r.pips, 30);
  assert.equal(r.lots, 0.25);
  assert.ok(r.riskMoney <= 50 + 1e-9);
});

test("EURJPY in a GBP account: 1% of 20,000 over 80 pips with GBPJPY bid 190 rounds down to 0.47 lots", () => {
  const path = conversionPath([{ id: 9, baseAssetId: 2, quoteAssetId: 4 }], 4, 2);   // JPY (4) -> GBP through GBPJPY
  const { rate } = conversionRate(path, { 9: { bid: 190, ask: 190.02 } });
  const r = sizeTrade({ balance: 20000, riskMode: "percent", risk: 1, side: "buy", entry: 160, stop: 159.2, rate, symbol: JPY });
  assert.equal(r.volume, 47000);
  assert.equal(r.lots, 0.47);
  near(r.riskMoney, 197.894736, 1e-5);
});

test("An index with a 0.1 step: 1% of 10,000 over 30 points is 3.3", () => {
  const r = sizeTrade({ balance: 10000, riskMode: "percent", risk: 1, side: "buy", entry: 5000, stop: 4970, rate: 1, symbol: INDEX });
  assert.equal(r.volume, 3.3);
  near(r.riskMoney, 99);
});

test("Gold in a EUR account: 1% of 10,000 over 8.00 with EURUSD bid 1.1000 is 0.13 lots", () => {
  const rate = conversionRate([{ symbolId: 3, invert: true }], { 3: { bid: 1.1, ask: 1.1001 } }).rate;
  const r = sizeTrade({ balance: 10000, riskMode: "percent", risk: 1, side: "buy", entry: 2400, stop: 2392, rate, symbol: GOLD });
  assert.equal(r.volume, 13);
  assert.equal(r.lots, 0.13);
  near(r.riskMoney, 94.545454, 1e-5);
});

test("Bitcoin: 2% of 2,000 over 1,200 is 0.03; at 0.5% the smallest size is too big and nothing is sized", () => {
  const ok = sizeTrade({ balance: 2000, riskMode: "percent", risk: 2, side: "buy", entry: 60000, stop: 58800, rate: 1, symbol: BTC });
  assert.equal(ok.volume, 0.03);
  near(ok.riskMoney, 36);
  const no = sizeTrade({ balance: 2000, riskMode: "percent", risk: 0.5, side: "buy", entry: 60000, stop: 58800, rate: 1, symbol: BTC });
  assert.equal(no.ok, false);
  assert.equal(no.code, "min");
  near(no.minRisk, 12);
  assert.match(no.message, /12\.00, more than the 10\.00 chosen\. Nothing is placed\./);
});

test("A fixed amount of money is used as it is", () => {
  const r = sizeTrade({ balance: 10000, riskMode: "money", risk: 75, side: "sell", entry: 1.1, stop: 1.1025, rate: 1, symbol: FX });
  assert.equal(r.volume, 30000);
  near(r.riskMoney, 75);
});

test("A platform that counts volume in hundredths sizes the same trade", () => {
  const cents = { ...FX, lotSize: 10000000, minVolume: 100000, maxVolume: 1000000000, volumeStep: 100000, unitsPerVolume: 0.01 };
  const r = sizeTrade({ balance: 10000, riskMode: "percent", risk: 1, side: "buy", entry: 1.1, stop: 1.098, rate: 1, symbol: cents });
  assert.equal(r.volume, 5000000);
  assert.equal(r.lots, 0.5);
  assert.equal(r.units, 50000);
});

test("The maximum volume caps the size and says so", () => {
  const r = sizeTrade({ balance: 1e9, riskMode: "percent", risk: 1, side: "buy", entry: 1.1, stop: 1.098, rate: 1, symbol: FX });
  assert.equal(r.volume, 10000000);
  assert.equal(r.capped, true);
});

test("The risk is never larger than the budget, whatever the numbers", () => {
  for (let i = 0; i < 2000; i++) {
    const entry = 0.5 + Math.random() * 2;
    const stop = entry - (1 + Math.floor(Math.random() * 500)) / 1e5;
    const rate = 0.3 + Math.random() * 2;
    const r = sizeTrade({ balance: 1000 + Math.random() * 1e5, riskMode: "percent", risk: 0.1 + Math.random() * 3, side: "buy", entry, stop, rate, symbol: FX });
    if (r.ok) assert.ok(r.riskMoney <= r.budget * (1 + 1e-9), `${r.riskMoney} > ${r.budget}`);
  }
});

test("Bad input is refused with a plain reason, never sized", () => {
  const base = { balance: 10000, riskMode: "percent", risk: 1, side: "buy", entry: 1.1, stop: 1.098, rate: 1, symbol: FX };
  const cases = [
    [{ stop: 1.1 }, "stop", /no distance/],
    [{ stop: 1.102 }, "stop", /below the entry/],
    [{ side: "sell" }, "stop", /above the entry/],
    [{ risk: 0 }, "risk", /Enter the risk/],
    [{ risk: -1 }, "risk", /Enter the risk/],
    [{ risk: 150 }, "risk", /above 100%/],
    [{ balance: 0 }, "balance", /balance/],
    [{ entry: NaN }, "entry", /entry/],
    [{ rate: 0 }, "rate", /exchange rate/],
    [{ symbol: null }, "symbol", /trading details/],
  ];
  for (const [change, code, message] of cases) {
    const r = sizeTrade({ ...base, ...change });
    assert.equal(r.ok, false, JSON.stringify(change));
    assert.equal(r.code, code, JSON.stringify(change));
    assert.match(r.message, message);
  }
});

test("Conversion paths: none needed, direct, inverse, two steps, none found; missing quotes are reported", () => {
  const syms = [{ id: 1, baseAssetId: 10, quoteAssetId: 20 }, { id: 2, baseAssetId: 30, quoteAssetId: 20 }];
  assert.deepEqual(conversionPath(syms, 10, 10), []);
  assert.deepEqual(conversionPath(syms, 10, 20), [{ symbolId: 1, invert: false }]);
  assert.deepEqual(conversionPath(syms, 20, 10), [{ symbolId: 1, invert: true }]);
  assert.deepEqual(conversionPath(syms, 10, 30), [{ symbolId: 1, invert: false }, { symbolId: 2, invert: true }]);
  assert.equal(conversionPath(syms, 10, 99), null);
  assert.deepEqual(conversionRate([], {}), { ok: true, rate: 1 });
  const two = conversionRate(conversionPath(syms, 10, 30), { 1: { bid: 1.99, ask: 2 }, 2: { bid: 4, ask: 4.01 } });
  near(two.rate, 0.5);                                         // ask going in, 1/bid coming out: the larger risk
  assert.deepEqual(conversionRate([{ symbolId: 1, invert: false }], {}), { ok: false, missing: [1] });
});

test("Pips, targets by R and reward to risk", () => {
  assert.equal(pointsToPips(205, 5, 4), 20.5);
  assert.equal(pointsToPips(300, 3, 2), 30);
  assert.equal(targetFromR("buy", 1.1, 1.098, 2, 5), 1.104);
  assert.equal(targetFromR("sell", 150, 150.3, 1.5, 3), 149.55);
  const rr = rewardRisk(1.1, 1.098, 1.104);
  near(rr.rr, 2);
  near(rr.breakEvenWinRate, 1 / 3);
  assert.equal(rewardRisk(1.1, 1.1, 1.2), null);
});

test("The log keeps only this panel's closed trades, with R, newest first; and its summary", () => {
  assert.equal(makeLabel(100), "ERT r=100.00");
  assert.deepEqual(parseLabel("ERT r=82.50"), { risk: 82.5 });
  assert.equal(parseLabel("someone else's label"), null);
  const deals = [
    { dealId: 1, symbolName: "EURUSD", openingDirection: "buy", closingTime: "2026-11-18T10:00:00Z", netProfit: 200, label: "ERT r=100.00" },
    { dealId: 2, symbolName: "EURUSD", openingDirection: "sell", closingTime: "2026-11-18T12:00:00Z", netProfit: -100, label: "ERT r=100.00" },
    { dealId: 3, symbolName: "GBPUSD", openingDirection: "buy", closingTime: "2026-11-18T13:00:00Z", netProfit: 50, label: "manual" },
    { dealId: 4, symbolName: "GBPUSD", openingDirection: "buy", closingTime: null, netProfit: null, label: "ERT r=10.00" },
  ];
  const log = tradeLog(deals);
  assert.deepEqual(log.map((t) => [t.id, t.r]), [[2, -1], [1, 2]]);
  const s = summary(log);
  assert.equal(s.count, 2);
  assert.equal(s.winRate, 0.5);
  assert.equal(s.avgR, 0.5);
  assert.equal(s.profitFactor, 2);
  assert.deepEqual(summary([]), { count: 0, winRate: null, avgR: null, profitFactor: null });
});

test("The loss light: the day starts at the chosen hour, every closed trade counts, amber at 80%, red at 100%", () => {
  const now = Date.parse("2026-11-18T09:30:00Z");
  assert.equal(new Date(dayStart(now, 8, 0)).toISOString(), "2026-11-18T08:00:00.000Z");
  assert.equal(new Date(dayStart(now, 22, 0)).toISOString(), "2026-11-17T22:00:00.000Z");
  assert.equal(new Date(dayStart(now, 0, 60)).toISOString(), "2026-11-17T23:00:00.000Z");   // midnight in UTC+1
  const deals = [
    { closingTime: "2026-11-18T08:30:00Z", netProfit: -120 },
    { closingTime: "2026-11-18T09:00:00Z", netProfit: 40 },
    { closingTime: "2026-11-17T20:00:00Z", netProfit: -500 },
  ];
  assert.equal(realisedLossSince(deals, dayStart(now, 8, 0)), 80);
  assert.equal(realisedLossSince([{ closingTime: "2026-11-18T08:30:00Z", netProfit: 10 }], 0), 0);
  assert.equal(lossLight(80, 0), "off");
  assert.equal(lossLight(79, 100), "green");
  assert.equal(lossLight(80, 100), "amber");
  assert.equal(lossLight(100, 100), "red");
});
