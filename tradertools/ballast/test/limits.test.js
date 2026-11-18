// Loss limits as funded-account firms count them, and the day in a firm's own time zone (node --test).
import assert from "node:assert/strict";
import { test } from "node:test";
import { closedSince, dayStart, light, limitState, tzOffset } from "../site/js/limits.js";

const iso = (ms) => new Date(ms).toISOString();

test("The day starts at midnight in the firm's time zone, right across daylight saving (audit 12)", () => {
  assert.equal(iso(dayStart(Date.parse("2026-10-25T12:00:00Z"), 0, "Europe/Prague")), "2026-10-24T22:00:00.000Z");
  assert.equal(iso(dayStart(Date.parse("2026-03-29T12:00:00Z"), 0, "Europe/Prague")), "2026-03-28T23:00:00.000Z");
  assert.equal(iso(dayStart(Date.parse("2026-11-18T09:30:00Z"), 8, "UTC")), "2026-11-18T08:00:00.000Z");
  assert.equal(iso(dayStart(Date.parse("2026-11-18T07:30:00Z"), 8, "UTC")), "2026-11-17T08:00:00.000Z");
  assert.equal(iso(dayStart(Date.parse("2026-11-18T23:30:00Z"), 0, "Europe/Prague")), "2026-11-18T23:00:00.000Z");
  assert.equal(tzOffset(Date.parse("2026-07-01T00:00:00Z"), "America/New_York"), -4 * 3600000);
  assert.equal(tzOffset(Date.parse("2026-12-01T00:00:00Z"), "America/New_York"), -5 * 3600000);
});

test("Closed deals since the day's start are netted, wins against losses", () => {
  const from = Date.parse("2026-11-18T00:00:00Z");
  const deals = [{ closingTime: "2026-11-18T08:30:00Z", netProfit: -120 }, { closingTime: "2026-11-18T09:00:00Z", netProfit: 40 },
                 { closingTime: "2026-11-17T20:00:00Z", netProfit: -500 }, { closingTime: null, netProfit: null }];
  assert.deepEqual(closedSince(deals, from), { net: -80, n: 2 });
});

const day = Date.parse("2026-11-18T00:00:00Z");

test("FTMO's way: equity against the start-of-day balance, open trades included (audit 5)", () => {
  // initial 100,000; 2,000 won before today; today nothing closed; open trades 4,500 down; daily limit 5% of initial
  const s = limitState({ balance: 102000, equity: 97500, deals: [], dayFrom: day, dealsOk: true, rule: "balance",
                         dayLimit: 5000, totalLimit: 10000, initial: 100000, totalMode: "static" });
  assert.equal(s.day.loss, 4500);
  assert.equal(s.day.light, "amber");
  assert.equal(s.total.loss, 2500);
  assert.equal(s.room, 500);
  assert.equal(limitState({ balance: 102000, equity: 97000, deals: [], dayFrom: day, dealsOk: true, rule: "balance", dayLimit: 5000 }).day.light, "red");
});

test("The higher of start-of-day balance and equity, when the day's opening equity was seen (audit 5)", () => {
  const s = limitState({ balance: 100000, equity: 96500, deals: [], dayFrom: day, dealsOk: true, rule: "higher", sodEquity: 101000, dayLimit: 5000 });
  assert.equal(s.day.ref, 101000);
  assert.equal(s.day.loss, 4500);
  assert.equal(s.day.light, "amber");
  const unseen = limitState({ balance: 100000, equity: 96500, deals: [], dayFrom: day, dealsOk: true, rule: "higher", dayLimit: 5000 });
  assert.equal(unseen.day.loss, 3500);
  assert.match(unseen.day.refNote, /was not seen/);
});

test("Today's closed losses and open losses add up; the room is what is left (audit 4)", () => {
  // realised -400 today, floating -50: the day is 450 down of 500, so a trade may risk 50 at most
  const deals = [{ closingTime: "2026-11-18T10:00:00Z", netProfit: -400 }];
  const s = limitState({ balance: 9600, equity: 9550, deals, dayFrom: day, dealsOk: true, rule: "balance", dayLimit: 500 });
  assert.equal(s.day.ref, 10000);
  assert.equal(s.day.loss, 450);
  assert.equal(s.room, 50);
  const full = limitState({ balance: 9930, equity: 9880.000000000002 - 1e-12, deals: [{ closingTime: "2026-11-18T10:00:00Z", netProfit: -70 }], dayFrom: day, dealsOk: true, rule: "balance", dayLimit: 120 });
  assert.equal(full.room, 0);                              // (120 - 119.9999999999 is no room)
});

test("The total limit counts equity, static or trailing; no starting balance means unknown (audit 7, 10)", () => {
  const st = limitState({ balance: 95000, equity: 93500, deals: [], dayFrom: day, dealsOk: true, totalLimit: 10000, initial: 100000, totalMode: "static" });
  assert.equal(st.total.loss, 6500);
  assert.equal(st.room, 3500);
  const tr = limitState({ balance: 104000, equity: 103000, deals: [], dayFrom: day, dealsOk: true, totalLimit: 5000, initial: 100000, totalMode: "trailing", peak: 106000 });
  assert.equal(tr.total.loss, 3000);
  const none = limitState({ balance: 95000, equity: 95000, deals: [], dayFrom: day, dealsOk: true, totalLimit: 10000 });
  assert.equal(none.total.light, "unknown");
  assert.equal(none.known, false);
});

test("If the history could not be read, the limits are unknown, and the panel fails closed (audit 6)", () => {
  const s = limitState({ balance: 10000, equity: 10000, deals: [], dayFrom: day, dealsOk: false, rule: "balance", dayLimit: 500 });
  assert.equal(s.known, false);
  assert.equal(s.day.light, "unknown");
  const off = limitState({ balance: 10000, equity: 10000, deals: [], dayFrom: day, dealsOk: false });
  assert.equal(off.known, true);                          // (no limit set: nothing to know)
  assert.equal(off.room, null);
});

test("Lights", () => {
  assert.equal(light(79, 100), "green");
  assert.equal(light(80, 100), "amber");
  assert.equal(light(100, 100), "red");
});
