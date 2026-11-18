// Ballast: the panel. Five tools over one account: Ticket (size, review, place), Limits (daily and total loss, the way
// funded-account firms count them), Exposure (open risk at the stops), Journal (trades in R) and Sessions (the
// market's clock). The maths is in risk.js, limits.js, journal.js and sessions.js; ticket.js builds the order and is
// the only way one is sent; host.js (cTrader) or host-mock.js (?mock=1) supplies the account and prices.
import { bySymbol, newTradeId, stats, toCSV, tradeLog } from "./journal.js";
import { dayStart, limitState } from "./limits.js";
import {
  atr, commissionPerUnit, conversionPath, conversionRate, lotDecimals, marketEntry, money, parseNumber, pipSize,
  positionRisk, rewardRisk, roundPrice, targetFromR,
} from "./risk.js";
import { fxWeekOpen, sessionState, span } from "./sessions.js";
import { buildOrder, createPlacer } from "./ticket.js";

const VERSION = "1.0.0";
// The paid plugin's id in the cTrader Store (the `id` query parameter). Empty until the Store gives one; then only
// that id may place orders from this page. ponytail: a determined copier can get round it; there is no server.
const PAID_IDS = [];
const KEY = "ballast.v1";

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const edition = document.body.dataset.edition === "trial" ? "trial" : "full";
const canPlace = edition === "full" && (PAID_IDS.length === 0 || PAID_IDS.includes(params.get("id")));
document.documentElement.dataset.theme = params.get("theme") === "light" ? "light" : "dark";
const DEC = (1.5).toLocaleString().includes(",") ? "," : ".";
const num = (v) => parseNumber(v, DEC);
const browserTz = (() => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"; } catch { return "UTC"; } })();
const TZS = [[browserTz, `Your time zone (${browserTz})`], ["UTC", "UTC"], ["Europe/Prague", "Prague (FTMO and others)"],
             ["Europe/Athens", "Athens: many brokers' server time"], ["America/New_York", "New York (the forex day ends at 17:00)"],
             ["Europe/London", "London"], ["Asia/Dubai", "Dubai"], ["Asia/Singapore", "Singapore"], ["Australia/Sydney", "Sydney"]]
  .filter((x, i, a) => a.findIndex((y) => y[0] === x[0]) === i);

$("version").textContent = "v" + VERSION;
$("edition").textContent = edition === "trial" ? "Trial: sizes and checks; does not place orders" : "Risk toolkit";

// ---- storage: one record per account, in this browser only ----------------------------------------------------------
let cfg = {};
let cfgKey = KEY;
function load(key) {
  try { return JSON.parse(localStorage.getItem(key)) || {}; } catch { return {}; }
}
function save() {
  try { localStorage.setItem(cfgKey, JSON.stringify(cfg)); } catch { /* storage may be off: settings last for this visit */ }
}

const st = { host: null, acct: null, sym: null, list: [], assetId: {}, depositAsset: null, usdAsset: null, quotes: {},
             quoteKey: "", stopQuotes: () => {}, details: {}, positions: [], deals: [], dealsComplete: false, built: null,
             frozen: null, limits: null, atr: null, tradeId: newTradeId(), side: "buy", painting: false };

const fmt = (x, d) => (Number.isFinite(x) ? x.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }) : "-");
const cur = () => (st.acct ? st.acct.currency : "");
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}
function banner(text) {
  $("banner").hidden = !text;
  $("banner").textContent = text || "";
}

// ---- start-up --------------------------------------------------------------------------------------------------------
const FIELDS = ["risk", "risk-mode", "stop-unit", "target-unit", "comm-mode", "comm", "atr-period", "lim-day", "lim-day-mode",
                "lim-total", "lim-total-mode", "lim-start", "lim-rule", "lim-trail", "lim-hour", "lim-tz", "lim-open"];
const DEFAULTS = { risk: "1", "risk-mode": "percent", "stop-unit": "pips", "target-unit": "r", "comm-mode": "none",
                   "lim-day-mode": "money", "lim-total-mode": "money", "lim-rule": "balance", "lim-trail": "static",
                   "lim-hour": "0", "lim-tz": "Europe/Prague", "lim-open": "stops" };

async function start() {
  for (let h = 0; h < 24; h++) $("lim-hour").add(new Option(String(h).padStart(2, "0") + ":00", String(h)));
  for (const [v, t] of TZS) $("lim-tz").add(new Option(t, v));
  showTab(load(KEY).tab || "ticket");
  if (!canPlace) {
    $("place").hidden = true;
    $("review-note").hidden = false;
    $("review-note").textContent = edition === "trial"
      ? "The trial sizes the trade and checks your limits. Placing it from here is in the full version."
      : "This copy is not the Store's paid plugin, so it does not place orders.";
  }
  try {
    st.host = params.has("mock") ? await import("./host-mock.js") : await import("./host.js");
    await st.host.connect();
    st.acct = await st.host.account();
  } catch (e) {
    $("acct").textContent = "Not connected";
    banner("Ballast runs inside cTrader. It could not reach cTrader here" + (e && e.message ? ` (${e.message})` : "") + ".");
    return;
  }
  cfgKey = `${KEY}.${st.acct.login}`;
  cfg = load(cfgKey);
  for (const f of FIELDS) if (cfg[f] != null || DEFAULTS[f] != null) $(f).value = cfg[f] ?? DEFAULTS[f];
  showAccount();
  try {
    st.list = await st.host.symbolList();
    const ids = [...new Set(st.list.flatMap((s) => [s.baseAssetId, s.quoteAssetId]).filter((x) => x != null))];
    for (const a of await st.host.assets(ids)) st.assetId[a.name] = a.assetId;
  } catch { /* without the list, only same-currency symbols can be sized; the banner says so */ }
  st.depositAsset = st.assetId[st.acct.currency] ?? null;
  st.usdAsset = st.assetId.USD ?? null;
  try {
    const ps = await st.host.periods();
    for (const p of ps) $("atr-period").add(new Option(p.name, p.code));
    $("atr-period").value = cfg["atr-period"] && ps.some((p) => p.code === cfg["atr-period"]) ? cfg["atr-period"] : (ps.find((p) => /hour/i.test(p.name)) || ps[0] || {}).code || "";
  } catch { /* no periods: the ATR stop is not offered */ }
  await loadSymbol(params.get("symbol") || cfg.symbol || "EURUSD");
  await refreshAll();
  let pending = null;
  st.host.onExecution(() => { clearTimeout(pending); pending = setTimeout(refreshAll, 800); });
  setInterval(refreshAll, 30000);                          // (reading only: nothing is ever sent on a timer)
  setInterval(renderSessions, 30000);
}

function showAccount() {
  const a = st.acct;
  $("acct").textContent = `${a.environment === "demo" ? "Demo" : "Live"} · ${fmt(a.balance, 2)} ${a.currency}`;
}

async function refreshAll() {
  if (!st.host) return;
  try { st.acct = await st.host.account(); showAccount(); } catch { /* keep the last figures */ }
  try { st.positions = await st.host.positions(); } catch { /* keep */ }
  const now = Date.now();
  try {
    const r = await st.host.deals(now - 35 * 86400000, now);
    st.deals = r.deals;
    st.dealsComplete = r.complete;
  } catch {
    st.dealsComplete = false;
  }
  const missing = [...new Set(st.positions.map((p) => p.symbolId))].filter((id) => !st.details[id]);
  if (missing.length) {
    try { for (const d of await st.host.symbolsById(missing)) st.details[d.symbolId] = d; } catch { /* exposure shows "unknown" */ }
  }
  subscribe();
  paint();
}

// ---- prices -----------------------------------------------------------------------------------------------------------
const pathOf = (quoteAsset, to = st.depositAsset) => conversionPath(st.list, quoteAsset, to, st.usdAsset);

function subscribe() {
  const ids = new Set();
  const add = (d) => {
    if (!d) return;
    ids.add(d.symbolId);
    for (const p of pathOf(d.quoteAssetId) || []) ids.add(p.symbolId);
    if ($("comm-mode").value === "million") for (const p of [...(pathOf(d.quoteAssetId, st.usdAsset) || []), ...(pathOf(st.usdAsset) || [])]) ids.add(p.symbolId);
  };
  add(st.sym);
  for (const p of st.positions) add(st.details[p.symbolId]);
  const key = [...ids].sort((a, b) => a - b).join(",");
  if (key === st.quoteKey) return;
  st.quoteKey = key;
  st.stopQuotes();
  st.stopQuotes = st.host.quotes([...ids], (q) => {
    const o = st.quotes[q.symbolId] || (st.quotes[q.symbolId] = {});
    if (q.bid != null) o.bid = q.bid;                        // (an event may carry one side only)
    if (q.ask != null) o.ask = q.ask;
    if (st.sym && q.symbolId === st.sym.symbolId) $("px").textContent = `${fmt(o.bid, st.sym.digits)} / ${fmt(o.ask, st.sym.digits)}`;
    if (!st.painting) {
      st.painting = true;
      requestAnimationFrame(() => { st.painting = false; paint(); });
    }
  });
}

/** Quote currency -> account money for symbol `d`, conservative, valued at `stop` too when the symbol is a leg. */
function rateFor(d, stop) {
  const path = pathOf(d.quoteAssetId);
  if (!path) return NaN;
  const r = conversionRate(path, st.quotes, Number.isFinite(stop) ? { symbolId: d.symbolId, price: stop } : null);
  return r.ok ? r.rate : NaN;
}

async function loadSymbol(name) {
  name = String(name || "").trim().toUpperCase();
  $("sym").value = name;
  st.sym = name ? await st.host.symbol(name).catch(() => null) : null;
  st.atr = null;
  if (!st.sym) {
    banner(`No symbol called ${name || "(empty)"} on this account.`);
  } else {
    st.details[st.sym.symbolId] = st.sym;
    banner(pathOf(st.sym.quoteAssetId) ? "" : `There is no price to turn ${name}'s currency into ${cur()}, so its risk cannot be sized.`);
    cfg.symbol = name;
    save();
    loadAtr();
  }
  subscribe();
  paint();
}

async function loadAtr() {
  const s = st.sym;
  const period = $("atr-period").value;
  if (!s || !period) return;
  try {
    const bars = await st.host.bars(s.symbolId, period, 60);
    if (st.sym === s) st.atr = atr(bars, 14);
  } catch { st.atr = null; }
  paint();
}

// ---- the ticket -------------------------------------------------------------------------------------------------------
function ticketInputs() {
  const s = st.sym;
  const orderType = $("otype").value;
  const quote = s ? st.quotes[s.symbolId] : null;
  const entry = orderType === "market" ? marketEntry(st.side, quote) : num($("entry").value);
  let stop = num($("stop").value);
  const unit = $("stop-unit").value;
  if (s && Number.isFinite(stop) && Number.isFinite(entry) && unit !== "price") {
    const d = unit === "pips" ? stop * pipSize(s.pipPosition) : stop * (st.atr || NaN);
    stop = roundPrice(st.side === "buy" ? entry - d : entry + d, s.digits);
  }
  let target = num($("target").value);
  if (!Number.isFinite(target)) target = null;
  else if ($("target-unit").value === "r" && s && Number.isFinite(stop)) target = targetFromR(st.side, entry, stop, target, s.digits);
  const rate = s ? rateFor(s, stop) : NaN;
  let commission = 0;
  const cm = $("comm-mode").value;
  if (s && cm !== "none") {
    const value = num($("comm").value);
    const lotUnits = s.lotSize * (s.unitsPerVolume || 1);
    const toUsd = s.quoteAssetId === st.usdAsset ? 1 : (() => { const r = conversionRate(pathOf(s.quoteAssetId, st.usdAsset), st.quotes); return r.ok ? r.rate : NaN; })();
    const usdToDep = st.usdAsset === st.depositAsset ? 1 : (() => { const r = conversionRate(pathOf(st.usdAsset), st.quotes); return r.ok ? r.rate : NaN; })();
    commission = Number.isFinite(value) ? commissionPerUnit({ mode: cm, value }, { lotUnits, usdPerUnit: entry * toUsd, usdToDeposit: usdToDep }) : NaN;
  }
  const L = st.limits;
  return {
    symbol: s, side: st.side, orderType, entry, stop, target, quote, balance: st.acct ? st.acct.balance : NaN,
    riskMode: $("risk-mode").value, risk: num($("risk").value), rate, commission,
    feeRate: s && s.quoteAssetId !== st.depositAsset ? s.feeRate || 0 : 0,
    room: L && L.room != null ? L.room : null, limitsKnown: L ? L.known : true, accountType: st.acct && st.acct.accountType,
    positionOnSymbol: !!(s && st.positions.some((p) => p.symbolId === s.symbolId)), tradeId: st.tradeId,
  };
}

function renderTicket() {
  const inp = ticketInputs();
  st.built = buildOrder(inp);
  const out = $("result");
  out.textContent = "";
  const d = st.sym ? lotDecimals(st.sym) : 2;
  if (!st.built.ok) {
    out.append(el("p", "warn", st.built.message));
  } else {
    const r = st.built.review;
    out.append(el("div", "big", `${fmt(r.lots, d)} lots`));
    out.append(el("div", null, `Loses ${money(r.riskMoney)} ${cur()} at the stop${r.commissionRisk > 0 ? ` (${money(r.priceRisk)} price, ${money(r.commissionRisk)} commission)` : ""} · stop ${fmt(r.pips, 1)} pips`));
    out.append(el("div", "mut small", `${fmt(r.units, 2)} units · budget ${money(r.budget)} ${cur()}`));
    const rr = inp.target ? rewardRisk(inp.entry, inp.stop, inp.target) : null;
    if (rr) out.append(el("div", "mut small", `Target ${fmt(inp.target, st.sym.digits)}: ${fmt(rr.rr, 2)} times the risk; it breaks even at ${fmt(rr.breakEvenWinRate * 100, 0)}% wins, before costs.`));
    if (r.cut) out.append(el("div", "warn", "Cut to fit your loss limits: this is the most they leave room for."));
    if (r.capped) out.append(el("div", "warn", "Capped at the largest size this symbol allows."));
    if (r.leverage > 20) out.append(el("div", "warn", `This position is worth ${fmt(r.leverage, 0)} times your balance: a tight stop makes a big position. Check the margin it needs.`));
    if ($("comm-mode").value === "none") out.append(el("div", "mut small", "Commission is set to none: if your account pays commission, set it under Costs."));
  }
  const atrOn = $("stop-unit").value === "atr";
  $("atr-line").hidden = !(st.atr && st.sym);
  if (st.atr && st.sym) {
    const pips = st.atr / pipSize(st.sym.pipPosition);
    const k = atrOn ? num($("stop").value) : NaN;
    $("atr-line").textContent = `Volatility: ATR(14) on the ${$("atr-period").selectedOptions[0]?.text || "chart"} is ${fmt(st.atr, st.sym.digits)} (${fmt(pips, 1)} pips)` +
      (Number.isFinite(k) ? `; ${fmt(k, 2)} x ATR is ${fmt(pips * k, 1)} pips.` : ". Choose \"x ATR\" to set the stop as a multiple of it.");
  }
  const cm = $("comm-mode").value;
  document.querySelectorAll(".comm-row").forEach((e) => { e.hidden = cm === "none"; });
  $("costs-sum").textContent = cm === "none" ? "· no commission" : `· ${$("comm").value || "?"} ${cm === "lot" ? cur() + " per lot" : "USD per million"}, each side`;
  $("review").disabled = !st.built.ok;
}

// ---- limits -------------------------------------------------------------------------------------------------------------
function openRisk() {
  let total = 0;
  let noStop = 0;
  let unknown = 0;
  const rows = st.positions.map((p) => {
    const d = st.details[p.symbolId];
    const rate = d ? rateFor(d, p.stopLoss) : NaN;
    const risk = d && Number.isFinite(rate) ? positionRisk(p, rate, d.unitsPerVolume || 1) : undefined;
    if (risk === null) noStop += 1;
    else if (risk === undefined) unknown += 1;
    else total += risk;
    return { p, d, risk };
  });
  return { rows, total, noStop, unknown };
}

function computeLimits() {
  const a = st.acct;
  if (!a) return null;
  const startBal = num($("lim-start").value);
  const asMoney = (v, mode) => (mode === "pct" ? (Number.isFinite(startBal) ? (startBal * v) / 100 : NaN) : v);
  const dayLimit = asMoney(num($("lim-day").value), $("lim-day-mode").value);
  const totalLimit = asMoney(num($("lim-total").value), $("lim-total-mode").value);
  const now = Date.now();
  const dayFrom = dayStart(now, Number($("lim-hour").value) || 0, $("lim-tz").value || "UTC");
  const equity = Number.isFinite(a.equity) ? a.equity : a.balance;
  if (!cfg.sod || cfg.sod.day !== dayFrom) {                 // (the day's opening equity, if this panel sees the day begin)
    cfg.sod = { day: dayFrom, equity: now - dayFrom < 15 * 60000 ? equity : null };
    save();
  }
  const peak = Math.max(cfg.peak || 0, a.balance, equity);
  if (peak !== cfg.peak) { cfg.peak = peak; save(); }
  const exp = openRisk();
  let eff = equity;
  let openNote = "";
  if ($("lim-open").value === "stops") {
    if (exp.noStop || exp.unknown) openNote = `${exp.noStop + exp.unknown} open trade${exp.noStop + exp.unknown === 1 ? " has" : "s have"} no stop (or no price yet), so ${exp.noStop + exp.unknown === 1 ? "it is" : "they are"} counted at today's price only.`;
    eff = Math.min(equity, a.balance - exp.total);
  }
  const s = limitState({ balance: a.balance, equity: eff, deals: st.deals, dayFrom, dealsOk: st.dealsComplete,
                         rule: $("lim-rule").value, sodEquity: cfg.sod.equity, dayLimit, totalLimit, initial: startBal,
                         totalMode: $("lim-trail").value, peak });
  s.openNote = openNote;
  s.dayFrom = dayFrom;
  return s;
}

function renderLimits() {
  const s = (st.limits = computeLimits());
  const box = $("limits-out");
  box.textContent = "";
  if (!s || (!s.day && !s.total)) {
    box.append(el("p", "mut", "No limits set. If a firm funds your account, enter its daily and total loss limits below; Ballast then sizes every trade so a stop-out cannot break them."));
    $("light-tab").hidden = true;
    return;
  }
  const worst = [s.day, s.total].filter(Boolean).map((x) => x.light);
  const lightAll = worst.includes("unknown") ? "unknown" : worst.includes("red") ? "red" : worst.includes("amber") ? "amber" : "green";
  $("light-tab").hidden = false;
  $("light-tab").className = "dot " + lightAll;
  for (const [name, x] of [["Today", s.day], ["In total", s.total]]) {
    if (!x) continue;
    box.append(el("h3", null, name));
    if (x.loss == null || x.light === "unknown") {
      box.append(el("p", "bad", name === "Today" ? "Unknown: the account's history did not load, so today's loss cannot be checked. Orders are blocked until it loads." : `Unknown: ${x.refNote}.`));
      continue;
    }
    const meter = el("div", "meter");
    const bar = el("i", x.light);
    bar.style.width = Math.min(100, x.used * 100).toFixed(1) + "%";
    meter.append(bar);
    box.append(el("div", null, `${money(x.loss)} of ${money(x.limit)} ${cur()} used (${fmt(x.used * 100, 0)}%)`), meter,
               el("div", "mut small", `Counted from ${x.refNote}: ${money(x.ref)} ${cur()}.`));
  }
  if (s.room != null) box.append(el("p", s.room > 0 ? null : "bad", s.room > 0 ? `A new trade may lose at most ${money(s.room)} ${cur()}: Ticket cuts the size to fit.` : "A limit is reached: this panel will not place orders until it resets."));
  if (s.day) box.append(el("p", "mut small", `The day began ${new Date(s.dayFrom).toLocaleString()} (${$("lim-tz").value}).`));
  if (s.openNote) box.append(el("p", "warn", s.openNote));
  if (!st.dealsComplete && s.day) box.append(el("p", "bad", "The history is incomplete."));
}

// ---- exposure -----------------------------------------------------------------------------------------------------------
function renderExposure() {
  const box = $("exposure-out");
  box.textContent = "";
  const exp = openRisk();
  if (!st.positions.length) {
    box.append(el("p", "mut", "No open positions."));
    return;
  }
  for (const { p, d, risk } of exp.rows) {
    const row = el("div", "row");
    const left = el("div");
    const lots = d ? `${fmt(p.volume / d.lotSize, lotDecimals(d))} lots` : `${p.volume} units`;
    left.append(el("b", null, `${p.symbolName} ${p.side === "buy" ? "buy" : "sell"}`), el("div", "mut small", `${lots} at ${fmt(p.entryPrice, d ? d.digits : 5)} · stop ${p.stopLoss ? fmt(p.stopLoss, d ? d.digits : 5) : "none"}`));
    const right = el("div", "num");
    if (risk === null) right.append(el("span", "bad", "no stop: no limit"));
    else if (risk === undefined) right.append(el("span", "mut", "price not known yet"));
    else right.append(el("b", null, `${money(risk)} ${cur()}`), el("div", "mut small", `${fmt((risk / st.acct.balance) * 100, 2)}% of balance`));
    row.append(left, right);
    box.append(row);
  }
  box.append(el("h3", null, "Total"));
  box.append(el("div", null, `At risk at the stops: ${money(exp.total)} ${cur()} (${fmt((exp.total / st.acct.balance) * 100, 2)}% of balance)`));
  if (exp.noStop) box.append(el("p", "bad", `${exp.noStop} position${exp.noStop === 1 ? " has" : "s have"} no stop: ${exp.noStop === 1 ? "its" : "their"} loss has no limit.`));
  else box.append(el("div", "mut small", `If every stop is hit: balance ${money(st.acct.balance - exp.total)} ${cur()}, before commission and slippage.`));
}

// ---- journal ------------------------------------------------------------------------------------------------------------
function renderJournal() {
  const trades = tradeLog(st.deals);
  const s = stats(trades);
  const box = $("journal-sum");
  box.textContent = "";
  if (!s.count) {
    box.append(el("p", "mut", "Trades placed from Ballast show here once they close, each in R (its result divided by the money it risked)."));
  } else {
    const dl = el("dl");
    const add = (k, v) => dl.append(el("dt", null, k), el("dd", null, v));
    add("Trades (35 days)", String(s.count));
    add("Won", `${s.wins} (${fmt(s.winRate * 100, 0)}%)`);
    add("Average", s.avgR === null ? "-" : `${fmt(s.avgR, 2)} R per trade`);
    add("Average win / loss", `${s.avgWinR === null ? "-" : fmt(s.avgWinR, 2) + " R"} / ${s.avgLossR === null ? "-" : fmt(s.avgLossR, 2) + " R"}`);
    add("Profit factor", s.profitFactor === null ? "-" : fmt(s.profitFactor, 2));
    add("Net", `${money(s.net)} ${cur()}`);
    add("Longest losing run", String(s.maxLosingStreak));
    box.append(dl);
    if (s.count < 30) box.append(el("p", "mut small", `${s.count} trades is a small sample: these numbers swing a lot until there are 30 or more.`));
  }
  if (!st.dealsComplete) box.append(el("p", "warn", "Part of the history did not load, so some trades may be missing."));
  const sym = $("journal-sym").tBodies[0];
  sym.textContent = "";
  for (const x of bySymbol(trades)) {
    const r = sym.insertRow();
    [x.symbol, x.count, fmt(x.winRate * 100, 0) + "%", x.avgR === null ? "-" : fmt(x.avgR, 2), money(x.net)].forEach((v, i) => {
      const c = r.insertCell();
      c.textContent = v;
      if (i) c.className = "num" + (i === 4 ? (x.net >= 0 ? " pos" : " neg") : "");
    });
  }
  const log = $("journal-log").tBodies[0];
  log.textContent = "";
  for (const t of trades.slice(0, 50)) {
    const r = log.insertRow();
    [new Date(t.closed).toLocaleDateString(), t.symbol, t.side, money(t.net), t.r === null ? "-" : fmt(t.r, 2)].forEach((v, i) => {
      const c = r.insertCell();
      c.textContent = v;
      if (i >= 3) c.className = "num " + (t.net >= 0 ? "pos" : "neg");
    });
  }
  $("csv").disabled = !trades.length;
}

// ---- sessions -----------------------------------------------------------------------------------------------------------
function renderSessions() {
  const box = $("sessions-out");
  box.textContent = "";
  const now = Date.now();
  const ss = sessionState(now);
  for (const s of ss) {
    const row = el("div", "row");
    const left = el("div");
    left.append(el("b", null, s.name), el("div", "mut small", `${s.local} there`));
    const right = el("div", "num");
    right.append(s.open ? el("span", "open-badge", "Open") : el("span", "mut", "Closed"),
                 el("div", "mut small", s.next ? `${s.open ? "closes" : "opens"} in ${span(s.next - now)}` : ""));
    row.append(left, right);
    box.append(row);
  }
  const open = ss.filter((s) => s.open).map((s) => s.name);
  box.append(el("p", "small", !fxWeekOpen(now) ? "The forex market is shut for the weekend: it reopens on Sunday at 17:00 New York time."
    : open.includes("London") && open.includes("New York") ? "London and New York overlap now: usually the busiest hours." : open.length ? `Open now: ${open.join(", ")}.` : "Between sessions."));
}

// ---- painting ---------------------------------------------------------------------------------------------------------
function paint() {
  renderLimits();                                         // (first: the ticket sizes against the limits' room)
  renderTicket();
  renderExposure();
  renderJournal();
  renderSessions();
}

// ---- review and place: the only path to an order ----------------------------------------------------------------------
const placer = createPlacer((request) => st.host.placeOrder(request));

function openReview() {
  if (!st.built || !st.built.ok) return;
  st.frozen = st.built;
  const r = st.frozen.review;
  const d = st.sym.digits;
  const rows = [["Symbol", r.symbol], ["Side", r.side === "buy" ? "Buy" : "Sell"], ["Order", r.orderType],
                ["Entry", r.orderType === "market" ? `at the market (now ${fmt(r.entry, d)})` : fmt(r.entry, d)],
                ["Stop", `${fmt(r.stop, d)}, ${fmt(r.pips, 1)} pips${r.orderType === "market" ? " from the fill" : ""}`],
                ["Target", r.target ? fmt(r.target, d) : "none"], ["Size", `${fmt(r.lots, lotDecimals(st.sym))} lots`],
                ["Loss at the stop", `${money(r.riskMoney)} ${cur()}${r.commissionRisk > 0 ? ", commission included" : ""}`]];
  const dl = $("review-list");
  dl.textContent = "";
  for (const [k, v] of rows) dl.append(el("dt", null, k), el("dd", null, v));
  $("place-msg").textContent = "";
  $("place").disabled = false;
  $("reviewbox").hidden = false;
  $("review").hidden = true;
}

function closeReview() {
  st.frozen = null;
  $("reviewbox").hidden = true;
  $("review").hidden = false;
}

async function place(ev) {
  if (!ev.isTrusted || !canPlace || !st.frozen) return;          // (a real click only)
  const now = buildOrder(ticketInputs());                        // (the limits and the account, checked again now)
  const blocking = ["limit", "limits", "netted", "account", "quote", "symbol"];
  if (!now.ok && blocking.includes(now.code)) {
    $("place-msg").textContent = now.message;
    return;
  }
  if (st.limits && st.limits.room != null && st.frozen.review.riskMoney > st.limits.room + 1e-9) {
    $("place-msg").textContent = "Your loss limits leave less room than when you reviewed: review again.";
    return;
  }
  $("place").disabled = true;
  $("place-msg").textContent = "Sending...";
  const res = await placer.place(st.frozen.request);
  $("place-msg").textContent = res.ok ? `Sent. cTrader order ${res.answer && res.answer.orderId != null ? "#" + res.answer.orderId : "accepted"}.` : res.message;
  if (res.ok) {
    st.tradeId = newTradeId();                                   // (the next trade gets its own id)
    setTimeout(refreshAll, 1500);
  }
}

// ---- events -------------------------------------------------------------------------------------------------------------
function showTab(name) {
  document.querySelectorAll("[data-tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === name)));
  document.querySelectorAll(".tab").forEach((t) => { t.hidden = t.id !== "tab-" + name; });
  try { const g = load(KEY); g.tab = name; localStorage.setItem(KEY, JSON.stringify(g)); } catch { /* fine */ }
}
document.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
document.querySelectorAll("[data-side]").forEach((b) => b.addEventListener("click", () => {
  st.side = b.dataset.side;
  document.querySelectorAll("[data-side]").forEach((x) => x.classList.toggle("on", x === b));
  edited();
}));
$("otype").addEventListener("change", () => {
  document.querySelectorAll(".entry-row").forEach((e) => { e.hidden = $("otype").value === "market"; });
  edited();
});
for (const id of ["entry", "stop", "target", ...FIELDS]) {
  $(id).addEventListener(id.startsWith("lim") || $(id).tagName === "SELECT" ? "change" : "input", edited);
  if ($(id).tagName === "INPUT") $(id).addEventListener("change", edited);
}
$("atr-period").addEventListener("change", loadAtr);
$("comm-mode").addEventListener("change", subscribe);
function edited() {
  for (const f of FIELDS) cfg[f] = $(f).value;
  save();
  if (st.frozen) closeReview();                                  // (a change to what was reviewed: review again)
  paint();
}
$("sym").addEventListener("change", () => { if (st.frozen) closeReview(); loadSymbol($("sym").value); });
$("review").addEventListener("click", openReview);
$("back").addEventListener("click", closeReview);
$("place").addEventListener("click", place);
$("csv").addEventListener("click", () => {
  const blob = new Blob([toCSV(tradeLog(st.deals))], { type: "text/csv" });
  const a = el("a");
  a.href = URL.createObjectURL(blob);
  a.download = "ballast-journal.csv";
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
});

start();
