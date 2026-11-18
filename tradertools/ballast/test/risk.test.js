// The sizing maths (node --test). Volumes are in units (unitsPerVolume 1) unless a case says otherwise. Every number
// was worked out by hand first; the audit of 18 November 2026 supplied the commission, stop-rate and room cases.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  atr, commissionPerUnit, conversionPath, conversionRate, lotDecimals, parseNumber, pointsToPips, positionRisk,
  rewardRisk, sizeTrade, targetFromR,
} from "../site/js/risk.js";

const FX = { digits: 5, pipPosition: 4, lotSize: 100000, minVolume: 1000, maxVolume: 10000000, volumeStep: 1000 };
const JPY = { digits: 3, pipPosition: 2, lotSize: 100000, minVolume: 1000, maxVolume: 10000000, volumeStep: 1000 };
const INDEX = { digits: 1, pipPosition: 0, lotSize: 1, minVolume: 0.1, maxVolume: 1000, volumeStep: 0.1 };
const GOLD = { digits: 2, pipPosition: 1, lotSize: 100, minVolume: 1, maxVolume: 10000, volumeStep: 1 };
const BTC = { digits: 2, pipPosition: 0, lotSize: 1, minVolume: 0.01, maxVolume: 100, volumeStep: 0.01 };
const near = (a, b, tol = 1e-6) => assert.ok(Math.abs(a - b) <= tol, `${a} is not ${b}`);
const base = { balance: 10000, riskMode: "percent", risk: 1, side: "buy", entry: 1.1, stop: 1.098, rate: 1, symbol: FX };

test("EURUSD in a USD account: 1% of 10,000 over 20 pips is 0.50 lots, exactly on the boundary", () => {
  const r = sizeTrade(base);
  assert.equal(r.volume, 50000);
  assert.equal(r.lots, 0.5);
  near(r.riskMoney, 100);
  assert.equal(r.pips, 20);
  near(r.leverage, 5.5);                                   // 50,000 x 1.10 / 10,000
});

test("EURUSD in a GBP account: 25 pips with GBPUSD bid 1.2500 is 0.25 lots", () => {
  const path = conversionPath([{ id: 7, baseAssetId: 2, quoteAssetId: 1 }], 1, 2);
  assert.deepEqual(path, [{ symbolId: 7, invert: true }]);
  const { rate } = conversionRate(path, { 7: { bid: 1.25, ask: 1.2502 } });
  const r = sizeTrade({ ...base, balance: 5000, stop: 1.0975, rate });
  assert.equal(r.lots, 0.25);
  near(r.riskMoney, 50);
});

test("USDJPY long in a USD account is converted at the stop, not now (audit 2)", () => {
  // 1% of 1,000,000 over 3.000 yen; the loss is in yen and turned into dollars when the stop is hit, at 147
  const path = [{ symbolId: 3, invert: true }];
  const quotes = { 3: { bid: 149.998, ask: 150 } };
  const now = conversionRate(path, quotes).rate;
  const atStop = conversionRate(path, quotes, { symbolId: 3, price: 147 }).rate;
  near(atStop, 1 / 147);
  assert.ok(atStop > now);
  const r = sizeTrade({ ...base, balance: 1000000, entry: 150, stop: 147, rate: atStop, symbol: JPY });
  assert.equal(r.volume, 490000);
  near(r.riskMoney, 10000, 1e-6);
  const old = sizeTrade({ ...base, balance: 1000000, entry: 150, stop: 147, rate: now, symbol: JPY });
  assert.equal(old.volume, 499000);                        // (what converting at today's rate would have done)
  assert.ok(old.volume * 3 / 147 > 10000);
});

test("EURUSD long in a EUR account: 1,000.02 of risk converted at the stop is 109,000 units (audit 2)", () => {
  const rate = conversionRate([{ symbolId: 1, invert: true }], { 1: { bid: 1.09998, ask: 1.1 } }, { symbolId: 1, price: 1.09 }).rate;
  const r = sizeTrade({ ...base, riskMode: "money", risk: 1000.02, stop: 1.09, rate });
  assert.equal(r.volume, 109000);
  near(r.riskMoney, 1000, 1e-6);
});

test("USDJPY short in a USD account: 0.5% of 10,000 over 30 pips is 0.24 lots (0.2499... at 1/bid, rounded down)", () => {
  const rate = conversionRate([{ symbolId: 3, invert: true }], { 3: { bid: 149.998, ask: 150 } }, { symbolId: 3, price: 150.3 }).rate;
  const r = sizeTrade({ ...base, risk: 0.5, side: "sell", entry: 150, stop: 150.3, rate, symbol: JPY });
  assert.equal(r.pips, 30);
  assert.equal(r.lots, 0.24);
  assert.ok(r.riskMoney <= 50);
});

test("EURJPY in a GBP account through GBPJPY rounds down to 0.47 lots", () => {
  const { rate } = conversionRate(conversionPath([{ id: 9, baseAssetId: 2, quoteAssetId: 4 }], 4, 2), { 9: { bid: 190, ask: 190.02 } });
  const r = sizeTrade({ ...base, balance: 20000, entry: 160, stop: 159.2, rate, symbol: JPY });
  assert.equal(r.volume, 47000);
  near(r.riskMoney, 197.894736, 1e-5);
});

test("An index, gold and bitcoin", () => {
  near(sizeTrade({ ...base, entry: 5000, stop: 4970, symbol: INDEX }).volume, 3.3);
  const gold = sizeTrade({ ...base, entry: 2400, stop: 2392, rate: 1 / 1.1, symbol: GOLD });
  assert.equal(gold.lots, 0.13);
  near(gold.riskMoney, 94.545454, 1e-5);
  const btc = sizeTrade({ ...base, balance: 2000, risk: 2, entry: 60000, stop: 58800, symbol: BTC });
  assert.equal(btc.volume, 0.03);
  const small = sizeTrade({ ...base, balance: 2000, risk: 0.5, entry: 60000, stop: 58800, symbol: BTC });
  assert.equal(small.code, "min");
  near(small.minRisk, 12);
  assert.match(small.message, /12\.00, more than the 10\.00 chosen\. Nothing is placed\./);
});

test("Commission per lot is in the risk, both sides (audit 1)", () => {
  const c = commissionPerUnit({ mode: "lot", value: 3.5 }, { lotUnits: 100000 });
  near(c, 0.000035);
  const five = sizeTrade({ ...base, stop: 1.0995, commission: c });
  assert.equal(five.volume, 175000);
  near(five.riskMoney, 99.75);
  near(five.priceRisk, 87.5);
  near(five.commissionRisk, 12.25);
  const two = sizeTrade({ ...base, stop: 1.0998, commission: c });
  assert.equal(two.volume, 370000);
  near(two.riskMoney, 99.9);
  const none = sizeTrade({ ...base, stop: 1.0995 });
  assert.equal(none.volume, 200000);                       // (without it: 200,000 units, a real loss of 114)
});

test("Commission per million USD traded (audit 1)", () => {
  const c = commissionPerUnit({ mode: "million", value: 30 }, { usdPerUnit: 1.1, usdToDeposit: 1 });
  near(c, 0.000033);
  const r = sizeTrade({ ...base, stop: 1.0995, commission: c });
  assert.equal(r.volume, 176000);
  near(r.riskMoney, 99.616);
  assert.ok(Number.isNaN(commissionPerUnit({ mode: "million", value: 30 }, {})));
  assert.equal(sizeTrade({ ...base, commission: NaN }).code, "commission");
  assert.equal(commissionPerUnit({ mode: "none", value: 9 }), 0);
});

test("The platform's conversion fee is added (audit 9)", () => {
  const r = sizeTrade({ ...base, balance: 5000, stop: 1.0975, rate: 0.8, feeRate: 0.001 });
  assert.equal(r.volume, 24000);
  near(r.riskMoney, 48.048);
  assert.equal(sizeTrade({ ...base, feeRate: 1 }).code, "fee");
});

test("The room left under the limits cuts the budget, and none left refuses (audit 4)", () => {
  const r = sizeTrade({ ...base, room: 50 });
  assert.equal(r.volume, 25000);
  assert.equal(r.cut, true);
  assert.equal(r.budget, 50);
  assert.equal(sizeTrade({ ...base, room: 500 }).cut, false);
  assert.equal(sizeTrade({ ...base, room: 0 }).code, "limit");
  assert.match(sizeTrade({ ...base, room: 1, symbol: { ...FX, minVolume: 10000 } }).message, /your limits leave/);
});

test("Steps that are not a power of ten, and a minimum that is not a step", () => {
  const odd = { digits: 0, pipPosition: 0, lotSize: 1, minVolume: 0.3, maxVolume: 100, volumeStep: 0.3 };
  const a = sizeTrade({ ...base, riskMode: "money", risk: 27, entry: 100, stop: 90, symbol: odd });
  near(a.volume, 2.7);
  near(a.riskMoney, 27);
  const b = sizeTrade({ ...base, riskMode: "money", risk: 6, entry: 100, stop: 90, symbol: { ...odd, minVolume: 0.5 } });
  near(b.volume, 0.6);
});

test("Volume counted in hundredths sizes the same trade", () => {
  const cents = { ...FX, lotSize: 10000000, minVolume: 100000, maxVolume: 1000000000, volumeStep: 100000, unitsPerVolume: 0.01 };
  const r = sizeTrade({ ...base, symbol: cents });
  assert.equal(r.volume, 5000000);
  assert.equal(r.units, 50000);
  assert.equal(r.lots, 0.5);
});

test("The maximum volume caps the size and says so", () => {
  const r = sizeTrade({ ...base, balance: 1e9 });
  assert.equal(r.volume, 10000000);
  assert.equal(r.capped, true);
});

test("The loss is never larger than the budget, with commission and fees, whatever the numbers", () => {
  for (let i = 0; i < 3000; i++) {
    const entry = 0.5 + Math.random() * 2;
    const stop = entry - (1 + Math.floor(Math.random() * 500)) / 1e5;
    const r = sizeTrade({ ...base, balance: 1000 + Math.random() * 1e5, risk: 0.1 + Math.random() * 3, entry, stop,
                          rate: 0.3 + Math.random() * 2, commission: Math.random() * 0.0001, feeRate: Math.random() * 0.01 });
    if (r.ok) assert.ok(r.riskMoney <= r.budget * (1 + 1e-9), `${r.riskMoney} > ${r.budget}`);
  }
});

test("Bad input is refused with a plain reason", () => {
  const cases = [
    [{ stop: 1.1 }, "stop", /no distance/], [{ stop: 1.102 }, "stop", /below the entry/], [{ side: "sell" }, "stop", /above the entry/],
    [{ risk: 0 }, "risk", /Enter the risk/], [{ risk: 150 }, "risk", /above 100%/], [{ balance: 0 }, "balance", /balance/],
    [{ entry: NaN }, "entry", /entry/], [{ rate: 0 }, "rate", /exchange rate/], [{ symbol: null }, "symbol", /trading details/],
  ];
  for (const [change, code, message] of cases) {
    const r = sizeTrade({ ...base, ...change });
    assert.equal(r.code, code, JSON.stringify(change));
    assert.match(r.message, message);
  }
});

test("Conversion paths: direct first, USD preferred in the middle, the worse price at the stop", () => {
  const syms = [{ id: 1, baseAssetId: 10, quoteAssetId: 20 }, { id: 2, baseAssetId: 30, quoteAssetId: 20 },
                { id: 3, baseAssetId: 10, quoteAssetId: 40 }, { id: 4, baseAssetId: 30, quoteAssetId: 40 }];
  assert.deepEqual(conversionPath(syms, 10, 10), []);
  assert.deepEqual(conversionPath(syms, 20, 10), [{ symbolId: 1, invert: true }]);
  assert.deepEqual(conversionPath(syms, 10, 30, 40), [{ symbolId: 3, invert: false }, { symbolId: 4, invert: true }]);
  assert.deepEqual(conversionPath(syms, 10, 30, 20), [{ symbolId: 1, invert: false }, { symbolId: 2, invert: true }]);
  assert.equal(conversionPath(syms, 10, 99), null);
  const q = { 1: { bid: 1.99, ask: 2 }, 2: { bid: 4, ask: 4.01 } };
  near(conversionRate(conversionPath(syms, 10, 30, 20), q).rate, 0.5);
  near(conversionRate([{ symbolId: 1, invert: false }], q, { symbolId: 1, price: 2.5 }).rate, 2.5);   // the stop is worse
  near(conversionRate([{ symbolId: 1, invert: false }], q, { symbolId: 1, price: 1.5 }).rate, 2);     // now is worse
  assert.deepEqual(conversionRate([{ symbolId: 1, invert: false }], {}), { ok: false, missing: [1] });
});

test("Numbers as people type them, never a wrong number (audit 12)", () => {
  assert.equal(parseNumber("100,000"), 100000);
  assert.equal(parseNumber("100,000", ","), 100);           // (to a reader whose decimal mark is the comma)
  assert.equal(parseNumber("1,000,000"), 1000000);
  assert.equal(parseNumber("1.000.000"), 1000000);
  assert.equal(parseNumber("1,000.50"), 1000.5);
  assert.equal(parseNumber("1.000,50"), 1000.5);
  assert.equal(parseNumber("1 000,50"), 1000.5);
  assert.equal(parseNumber("1,5"), 1.5);
  assert.equal(parseNumber("0,005"), 0.005);
  assert.equal(parseNumber("1.0850"), 1.085);
  assert.equal(parseNumber("1.250", ","), 1250);
  assert.equal(parseNumber("1.250"), 1.25);
  for (const bad of ["", "abc", "1,2,3", "1.2.3", "1,000.5.5", "--1"]) assert.ok(Number.isNaN(parseNumber(bad)), bad);
});

test("Pips, lot decimals, targets by R, reward to risk", () => {
  assert.equal(pointsToPips(205, 5, 4), 20.5);
  assert.equal(pointsToPips(300, 3, 2), 30);
  assert.equal(lotDecimals(FX), 2);
  assert.equal(lotDecimals({ ...FX, volumeStep: 100 }), 3);
  assert.equal(lotDecimals(BTC), 2);
  assert.equal(targetFromR("buy", 1.1, 1.098, 2, 5), 1.104);
  assert.equal(targetFromR("sell", 150, 150.3, 1.5, 3), 149.55);
  near(rewardRisk(1.1, 1.098, 1.104).breakEvenWinRate, 1 / 3);
  assert.equal(rewardRisk(1.1, 1.1, 1.2), null);
});

test("An open position's risk at its stop; none without a stop; none once the stop is past the entry", () => {
  near(positionRisk({ side: "buy", entryPrice: 1.1, stopLoss: 1.098, volume: 50000 }, 1), 100);
  near(positionRisk({ side: "sell", entryPrice: 150, stopLoss: 150.3, volume: 100000 }, 1 / 150), 200);
  assert.equal(positionRisk({ side: "buy", entryPrice: 1.1, stopLoss: null, volume: 1 }, 1), null);
  assert.equal(positionRisk({ side: "buy", entryPrice: 1.1, stopLoss: 1.105, volume: 1000 }, 1), 0);
});

test("ATR, Wilder's smoothing", () => {
  const bars = [{ high: 11, low: 9, close: 10 }];
  for (let i = 0; i < 20; i++) bars.push({ high: 12, low: 10, close: 11 });   // true range 2 every bar after the first
  near(atr(bars, 14), 2);
  assert.equal(atr(bars.slice(0, 10), 14), null);
  const gap = [{ high: 10, low: 9, close: 10 }, { high: 15, low: 14, close: 14.5 }];
  near(atr(gap, 1), 5);                                    // the gap from 10 to 15 counts
});
