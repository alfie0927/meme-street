// The sessions clock (node --test): each session in its own city's time, the forex week, daylight saving.
import assert from "node:assert/strict";
import { test } from "node:test";
import { fxWeekOpen, sessionState, span } from "../site/js/sessions.js";

const at = (t) => Object.fromEntries(sessionState(Date.parse(t)).map((s) => [s.name, [s.open, new Date(s.next).toISOString().slice(0, 16)]]));

test("A Wednesday morning in London: London open, the others closed, each with its next edge", () => {
  assert.deepEqual(at("2026-11-18T09:00:00Z"), {
    Sydney: [false, "2026-11-18T20:00"], Tokyo: [false, "2026-11-19T00:00"], London: [true, "2026-11-18T17:00"], "New York": [false, "2026-11-18T13:00"],
  });
});

test("The weekend: everything shut; Sydney opens with the forex week at 17:00 New York time on Sunday", () => {
  assert.equal(fxWeekOpen(Date.parse("2026-11-21T12:00:00Z")), false);
  assert.deepEqual(at("2026-11-21T12:00:00Z").Sydney, [false, "2026-11-22T22:00"]);
  assert.equal(fxWeekOpen(Date.parse("2026-11-22T22:30:00Z")), true);
  assert.deepEqual(at("2026-11-22T22:30:00Z").Sydney, [true, "2026-11-23T05:00"]);
  assert.equal(fxWeekOpen(Date.parse("2026-11-20T21:59:00Z")), true);       // Friday 16:59 in New York
  assert.equal(fxWeekOpen(Date.parse("2026-11-20T22:01:00Z")), false);
});

test("Daylight saving: London and New York open an hour earlier in UTC in summer", () => {
  assert.deepEqual(at("2026-03-29T12:00:00Z").London, [false, "2026-03-30T07:00"]);
  assert.deepEqual(at("2026-03-29T12:00:00Z")["New York"], [false, "2026-03-30T12:00"]);
  assert.deepEqual(at("2026-03-29T12:00:00Z").Sydney, [false, "2026-03-29T21:00"]);
});

test("Spans read plainly", () => {
  assert.equal(span(125 * 60000), "2 h 05 min");
  assert.equal(span(59 * 60000), "59 min");
});
