// Loss limits as funded-account firms count them, and the day in a firm's own time zone (node --test).
import assert from "node:assert/strict";
import { test } from "node:test";
import { closedSince, dayStart, light, limitState, tzOffset } from "../site/js/limits.js";

const iso = (ms) => new Date(ms).toISOString();
const day = Date.parse("2026-11-18T00:00:00Z");
const base = { balance: 10000, equity: 10000, deals: [], dayFrom: day, dealsOk: true, rule: "balance", dayLimit: null, totalLimit: null };

test("The day starts at midnight in the firm's time zone, right across daylight saving", () => {
  assert.equal(iso(dayStart(Date.parse("2026-10-25T12:00:00Z"), 0, "Europe/Prague")), "2026-10-24T22:00:00.000Z");
  assert.equal(iso(dayStart(Date.parse("2026-03-29T12:00:00Z"), 0, "Europe/Prague")), "2026-03-28T23:00:00.000Z");
  assert.equal(iso(dayStart(Date.parse("2026-11-18T09:30:00Z"), 8, "UTC")), "2026-11-18T08:00:00.000Z");
  assert.equal(iso(dayStart(Date.parse("2026-11-18T07:30:00Z"), 8, "UTC")), "2026-11-17T08:00:00.000Z");
  assert.equal(iso(dayStart(Date.parse("2026-11-18T23:30:00Z"), 0, "Europe/Prague")), "2026-11-18T23:00:00.000Z");
  assert.equal(tzOffset(Date.parse("2026-07-01T00:00:00Z"), "America/New_York"), -4 * 3600000);
  assert.equal(tzOffset(Date.parse("2026-12-01T00:00:00Z"), "America/New_York"), -5 * 3600000);
});

test("Closed deals since the day's start are netted, wins against losses", () => {
  const deals = [{ closingTime: "2026-11-18T08:30:00Z", netProfit: -120 }, { closingTime: "2026-11-18T09:00:00Z", netProfit: 40 },
                 { closingTime: "2026-11-17T20:00:00Z", netProfit: -500 }, { closingTime: null, netProfit: null }];
  assert.deepEqual(closedSince(deals, day), { net: -80, n: 2 });
});

test("FTMO's way: equity against the day's opening balance, open trades included", () => {
  const s = limitState({ ...base, balance: 102000, equity: 97500, dayLimit: 5000, totalLimit: 10000, initial: 100000, totalMode: "static" });
  assert.deepEqual([s.day.loss, s.day.light, s.day.refCode, s.total.loss, s.room], [4500, "amber", "sodBalance", 2500, 500]);
  assert.equal(limitState({ ...base, balance: 102000, equity: 97000, dayLimit: 5000 }).day.light, "red");
});

test("Real loss and the worst case are kept apart; the room comes from the worst case", () => {
  // the day: lost 40 for real; the open trades' stops would take it to 50 against a 40 limit
  const s = limitState({ ...base, equity: 9960, worstEquity: 9950, dayLimit: 40 });
  assert.equal(s.day.loss, 40);
  assert.equal(s.day.worst, 50);
  assert.equal(s.day.light, "red");
  assert.equal(s.room, 0);
  const t = limitState({ ...base, equity: 9990, worstEquity: 9950, dayLimit: 100 });
  assert.deepEqual([t.day.loss, t.day.worst, t.day.light, t.room], [10, 50, "green", 50]);
  const u = limitState({ ...base, equity: 9990, worstEquity: 10050, dayLimit: 100 });
  assert.equal(u.day.worst, 10);                           // (a worst case is never better than now)
});

test("Today's closed losses and open losses add up", () => {
  const deals = [{ closingTime: "2026-11-18T10:00:00Z", netProfit: -400 }];
  const s = limitState({ ...base, balance: 9600, equity: 9550, deals, dayLimit: 500 });
  assert.deepEqual([s.day.ref, s.day.loss, s.room], [10000, 450, 50]);
  const full = limitState({ ...base, balance: 9930, equity: 9880.000000000002 - 1e-12, deals: [{ closingTime: "2026-11-18T10:00:00Z", netProfit: -70 }], dayLimit: 120 });
  assert.equal(full.room, 0);                              // (120 - 119.9999999999 is no room)
});

test("The higher of opening balance and equity: exact when the opening equity is known, blocked when it is not", () => {
  const s = limitState({ ...base, balance: 100000, equity: 96500, rule: "higher", sodEquity: 101000, dayLimit: 5000 });
  assert.deepEqual([s.day.ref, s.day.loss, s.day.light, s.day.refCode], [101000, 4500, "amber", "higher"]);
  const unseen = limitState({ ...base, balance: 100000, equity: 96500, rule: "higher", dayLimit: 5000 });
  assert.equal(unseen.day.error, "needSodEquity");
  assert.equal(unseen.known, false);
  assert.equal(unseen.room, null);
});

test("The firm's own floor for the day, from its dashboard, is exact and wins", () => {
  // the firm says equity may not go below 96,000 today; the limit is 5,000; equity is 97,000
  const s = limitState({ ...base, balance: 100000, equity: 97000, rule: "higher", dayFloor: 96000, dayLimit: 5000 });
  assert.deepEqual([s.day.ref, s.day.loss, s.room, s.day.refCode, s.known], [101000, 4000, 1000, "floor", true]);
});

test("A percentage limit with no starting balance blocks, never falls back to no limit (review bug 1)", () => {
  const s = limitState({ ...base, dayLimit: NaN, totalLimit: NaN });
  assert.equal(s.day.error, "needStart");
  assert.equal(s.total.error, "needStart");
  assert.equal(s.known, false);
});

test("The total limit counts equity; trailing uses the highest of every floor it knows", () => {
  const st = limitState({ ...base, balance: 95000, equity: 93500, totalLimit: 10000, initial: 100000, totalMode: "static" });
  assert.deepEqual([st.total.loss, st.room, st.total.refCode, st.total.uncertain], [6500, 3500, "initial", null]);
  // trailing with no floor from the firm: this device may have missed the peak, so orders wait for the firm's figure
  const tr = limitState({ ...base, balance: 104000, equity: 103000, totalLimit: 5000, initial: 100000, totalMode: "trailing", peak: 106000 });
  assert.deepEqual([tr.total.error, tr.known], ["needFloor", false]);
  // the floor typed (100,500) is below what this device saw (106,000 - 5,000): the device's peak binds, flagged as unsure
  const dp = limitState({ ...base, balance: 104000, equity: 103000, totalLimit: 5000, initial: 100000, totalMode: "trailing", peak: 106000, totalFloor: 100500 });
  assert.deepEqual([dp.total.loss, dp.total.refCode, dp.total.uncertain, dp.known], [3000, "trailing", "devicePeak", true]);
  // the firm's dashboard says the floor is 102,000 (its peak was 107,000, higher than this device saw)
  const fl = limitState({ ...base, balance: 104000, equity: 103000, totalLimit: 5000, initial: 100000, totalMode: "trailing", peak: 106000, totalFloor: 102000 });
  assert.deepEqual([fl.total.loss, fl.room, fl.total.refCode, fl.total.uncertain], [4000, 1000, "floor", null]);
  assert.equal(limitState({ ...base, totalLimit: 10000 }).total.error, "needStart");
});

test("If the history could not be read, the day is unknown and orders are blocked (fail closed)", () => {
  const s = limitState({ ...base, dealsOk: false, dayLimit: 500 });
  assert.deepEqual([s.known, s.day.error, s.day.light, s.room], [false, "history", "unknown", null]);
  const floor = limitState({ ...base, dealsOk: false, dayLimit: 500, dayFloor: 9600 });
  assert.equal(floor.known, true);                         // (the firm's floor needs no history)
  const off = limitState({ ...base, dealsOk: false });
  assert.deepEqual([off.known, off.room], [true, null]);
});

test("Lights", () => {
  assert.equal(light(79, 100), "green");
  assert.equal(light(80, 100), "amber");
  assert.equal(light(100, 100), "red");
});

test("Daylight saving: the day starts at the first of a repeated hour, or when the clocks jump past a missing one", () => {
  const at = (iso) => Date.parse(iso);
  assert.equal(dayStart(at("2025-10-26T00:30:00Z"), 2, "Europe/Prague"), at("2025-10-26T00:00:00Z"));
  assert.equal(dayStart(at("2025-10-26T00:30:00Z"), 1, "Europe/London"), at("2025-10-26T00:00:00Z"));
  assert.equal(dayStart(at("2025-03-09T06:30:00Z"), 2, "America/New_York"), at("2025-03-08T07:00:00Z"));
  assert.equal(dayStart(at("2025-03-09T07:30:00Z"), 2, "America/New_York"), at("2025-03-09T07:00:00Z"));
});

test("Higher-of rule: with nothing open as the day began, the opening equity is the opening balance", () => {
  const s = limitState({ ...base, rule: "higher", dayLimit: 500, openAtDayStart: false });
  assert.deepEqual([s.known, s.day.refCode, s.day.ref], [true, "higher", s.day.ref]);
  assert.equal(limitState({ ...base, rule: "higher", dayLimit: 500 }).day.error, "needSodEquity");
  assert.equal(limitState({ ...base, rule: "higher", dayLimit: 500, openAtDayStart: true }).day.error, "needSodEquity");
});

test("A limit typed but unreadable, and open risk that cannot be counted, block orders", () => {
  assert.deepEqual([limitState({ ...base, dayLimit: NaN, dayError: "badNumber" }).day.error], ["badNumber"]);
  const b = limitState({ ...base, dayLimit: 500, blockers: ["positions"] });
  assert.deepEqual([b.known, b.room, b.blockers], [false, null, ["positions"]]);
  assert.equal(limitState({ ...base, blockers: ["positions"] }).known, true);   // (no limit set: nothing to protect)
});
