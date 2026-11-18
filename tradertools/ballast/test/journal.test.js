// The journal: one trade per label id, R from the planned risk, the statistics, CSV (node --test).
import assert from "node:assert/strict";
import { test } from "node:test";
import { bySymbol, makeLabel, newTradeId, parseLabel, stats, toCSV, tradeLog } from "../site/js/journal.js";

test("Labels carry the planned risk and a trade id; old probe labels still read", () => {
  assert.equal(makeLabel(100, "abc12345"), "BLST r=100.00 id=abc12345");
  assert.deepEqual(parseLabel("BLST r=82.50 id=k3f9a2b1"), { risk: 82.5, id: "k3f9a2b1" });
  assert.deepEqual(parseLabel("ERT r=1.00"), { risk: 1, id: null });
  assert.equal(parseLabel("manual"), null);
  assert.equal(parseLabel("BLST r=1 id=BAD!"), null);
  let i = 0;
  assert.equal(newTradeId(() => (i++ % 36) / 36), "abcdefgh");
  assert.ok(makeLabel(123456789.123, newTradeId()).length <= 100);
});

const D = (dealId, t, net, label, symbol = "EURUSD", side = "buy") => ({ dealId, symbolName: symbol, openingDirection: side, closingTime: t, netProfit: net, label });

test("A position closed in two parts is one trade (audit 8)", () => {
  const deals = [D(1, "2026-11-18T10:00:00Z", -50, "BLST r=100.00 id=aaaa1111"), D(2, "2026-11-18T10:05:00Z", -50, "BLST r=100.00 id=aaaa1111"),
                 D(3, "2026-11-18T12:00:00Z", 200, "BLST r=100.00 id=bbbb2222"), D(4, "2026-11-18T13:00:00Z", 999, "someone else's")];
  const log = tradeLog(deals);
  assert.deepEqual(log.map((t) => [t.id, t.net, t.r, t.parts]), [["bbbb2222", 200, 2, 1], ["aaaa1111", -100, -1, 2]]);
  const s = stats(log);
  assert.equal(s.count, 2);
  assert.equal(s.winRate, 0.5);
  assert.equal(s.avgR, 0.5);
  assert.equal(s.profitFactor, 2);
  assert.equal(s.net, 100);
  assert.equal(s.maxLosingStreak, 1);
});

test("Statistics: average win and loss in R, best and worst, the longest losing run", () => {
  const t = (closed, net) => ({ symbol: "X", closed, net, r: net / 100 });
  const log = [t("05", 300), t("04", -100), t("03", -100), t("02", -100), t("01", 150)];   // newest first
  const s = stats(log);
  assert.equal(s.maxLosingStreak, 3);
  assert.equal(s.avgWinR, 2.25);
  assert.equal(s.avgLossR, -1);
  assert.equal(s.bestR, 3);
  assert.equal(s.worstR, -1);
  assert.equal(stats([]).count, 0);
});

test("By symbol, and as CSV", () => {
  const log = tradeLog([D(1, "2026-11-18T10:00:00Z", 100, "BLST r=50.00 id=aaaa1111"),
                        D(2, "2026-11-18T11:00:00Z", -50, "BLST r=50.00 id=bbbb2222", "XAUUSD", "sell"),
                        D(3, "2026-11-18T12:00:00Z", -25, "BLST r=50.00 id=cccc3333")]);
  assert.deepEqual(bySymbol(log).map((x) => [x.symbol, x.count]), [["EURUSD", 2], ["XAUUSD", 1]]);
  const csv = toCSV(log);
  assert.equal(csv.split("\n")[0], "closed,symbol,side,net,planned_risk,r,parts");
  assert.ok(csv.includes("2026-11-18T11:00:00Z,XAUUSD,sell,-50.00,50.00,-1.000,1"));
});
