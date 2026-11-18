// Reading the history in full, or saying it is not (node --test; audit 6).
import assert from "node:assert/strict";
import { test } from "node:test";
import { readDeals } from "../site/js/history.js";

const DAY = 86400000;
const now = Date.parse("2026-11-18T12:00:00Z");
const all = Array.from({ length: 30 }, (_, i) => ({ dealId: i, closingTime: new Date(now - i * DAY).toISOString() }));

function fake({ cap = 1000, fail = () => false } = {}) {
  const calls = [];
  const fn = async (a, b) => {
    calls.push([a, b]);
    if (fail(a, b)) throw new Error("down");
    const inside = all.filter((d) => { const t = Date.parse(d.closingTime); return t >= a && t <= b; });
    return { deals: inside.slice(0, cap), hasMore: inside.length > cap };
  };
  return { fn, calls };
}

test("Five weeks are read one week at a time, every deal once", async () => {
  const f = fake();
  const r = await readDeals(f.fn, now - 35 * DAY, now);
  assert.equal(r.complete, true);
  assert.equal(r.deals.length, 30);
  assert.equal(f.calls.length, 5);
  assert.ok(f.calls.every(([a, b]) => b - a <= 7 * DAY));
});

test("A window with more than the platform returns is split until it fits", async () => {
  const f = fake({ cap: 2 });
  const r = await readDeals(f.fn, now - 7 * DAY, now);
  assert.equal(r.complete, true);
  assert.equal(r.deals.length, 8);                       // days 0 to 7 inclusive
});

test("A failure, or a window that never fits, makes the read incomplete (and the limits then fail closed)", async () => {
  const failed = await readDeals(fake({ fail: (a) => a < now - 20 * DAY }).fn, now - 35 * DAY, now);
  assert.equal(failed.complete, false);
  assert.ok(failed.deals.length > 0);
  const tight = await readDeals(fake({ cap: 0 }).fn, now - DAY, now, { depth: 2 });
  assert.equal(tight.complete, false);
});
