// Ballast: the trade journal. Each order this panel places carries a label "BLST r=<planned risk> id=<trade id>";
// closed deals with the same id are one trade (a position closed in parts is still one trade). Pure; tested.
import { money } from "./risk.js";

const LABEL = /^(?:BLST|ERT) r=(\d+(?:\.\d+)?)(?: id=([a-z0-9]{4,12}))?$/;

export function makeLabel(riskMoney, id) {
  return `BLST r=${money(riskMoney)} id=${id}`;
}

/** A short random id for one trade (base 36). `rnd` is injectable for tests. */
export function newTradeId(rnd = Math.random) {
  let s = "";
  for (let i = 0; i < 8; i++) s += "abcdefghijklmnopqrstuvwxyz0123456789"[Math.floor(rnd() * 36)];
  return s;
}

export function parseLabel(label) {
  const m = LABEL.exec(label || "");
  return m ? { risk: Number(m[1]), id: m[2] || null } : null;
}

/**
 * Closed trades placed by this panel, newest first.
 * deals: Plugin API v2 DealSummary [{ dealId, symbolName, openingDirection, closingTime, netProfit, label }].
 * returns [{ id, symbol, side, closed, net, risk, r, parts }]
 */
export function tradeLog(deals) {
  const by = new Map();
  for (const d of deals || []) {
    if (!d.closingTime || !Number.isFinite(d.netProfit)) continue;
    const lab = parseLabel(d.label);
    if (!lab) continue;
    const key = lab.id || "deal:" + d.dealId;
    const t = by.get(key) || { id: key, symbol: d.symbolName, side: d.openingDirection, closed: d.closingTime, net: 0, risk: lab.risk, parts: 0 };
    t.net += d.netProfit;
    t.parts += 1;
    if (d.closingTime > t.closed) t.closed = d.closingTime;
    by.set(key, t);
  }
  const out = [...by.values()].map((t) => ({ ...t, net: Math.round(t.net * 100) / 100, r: t.risk > 0 ? t.net / t.risk : null }));
  return out.sort((a, b) => (a.closed < b.closed ? 1 : a.closed > b.closed ? -1 : 0));
}

/** Statistics over trades: the numbers that say whether a way of trading is working. */
export function stats(trades) {
  const n = trades.length;
  const empty = { count: 0, wins: 0, losses: 0, winRate: null, avgR: null, avgWinR: null, avgLossR: null, profitFactor: null,
                  net: 0, bestR: null, worstR: null, maxLosingStreak: 0 };
  if (!n) return empty;
  const wins = trades.filter((t) => t.net > 0);
  const losses = trades.filter((t) => t.net < 0);
  const gains = wins.reduce((s, t) => s + t.net, 0);
  const lost = -losses.reduce((s, t) => s + t.net, 0);
  const rs = trades.map((t) => t.r).filter((r) => r !== null);
  const mean = (xs) => (xs.length ? xs.reduce((s, x) => s + x, 0) / xs.length : null);
  let streak = 0;
  let worst = 0;
  for (const t of [...trades].reverse()) {                     // (oldest first)
    streak = t.net < 0 ? streak + 1 : 0;
    worst = Math.max(worst, streak);
  }
  return {
    count: n, wins: wins.length, losses: losses.length, winRate: wins.length / n,
    avgR: mean(rs), avgWinR: mean(wins.map((t) => t.r).filter((r) => r !== null)), avgLossR: mean(losses.map((t) => t.r).filter((r) => r !== null)),
    profitFactor: lost > 0 ? gains / lost : null, net: Math.round((gains - lost) * 100) / 100,
    bestR: rs.length ? Math.max(...rs) : null, worstR: rs.length ? Math.min(...rs) : null, maxLosingStreak: worst,
  };
}

/** The same statistics for each symbol, most traded first. */
export function bySymbol(trades) {
  const g = new Map();
  for (const t of trades) g.set(t.symbol, [...(g.get(t.symbol) || []), t]);
  return [...g.entries()].map(([symbol, ts]) => ({ symbol, ...stats(ts) })).sort((a, b) => b.count - a.count);
}

/** The journal as CSV text (one row a trade), for a spreadsheet. */
export function toCSV(trades) {
  const q = (v) => (/[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
  const rows = [["closed", "symbol", "side", "net", "planned_risk", "r", "parts"]];
  for (const t of trades) rows.push([t.closed, t.symbol, t.side, money(t.net), money(t.risk), t.r === null ? "" : t.r.toFixed(3), t.parts]);
  return rows.map((r) => r.map(q).join(",")).join("\n") + "\n";
}
