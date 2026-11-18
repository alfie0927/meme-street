// Ballast: the panel. Five tools over one account: Ticket (size, review, place), Limits (daily and total loss, the way
// funded-account firms count them), Exposure (open risk at the stops), Journal (trades in R) and Sessions (the
// market's clock). The maths is in risk.js, limits.js, journal.js and sessions.js; ticket.js builds the order and is
// the only way one is sent; host.js (cTrader) or host-mock.js (?mock=1) supplies the account and prices; every
// sentence shown is in i18n.js.
import { applyStatic, setLanguage, t } from "./i18n.js";
import { bySymbol, newTradeId, stats, toCSV, tradeLog } from "./journal.js";
import { dayStart, limitState } from "./limits.js";
import {
  atr, commissionPerUnit, conversionPath, conversionRate, lotDecimals, marketEntry, parseNumber, pipSize, positionRisk,
  rewardRisk, roundPrice, targetFromR,
} from "./risk.js";
import { fxWeekOpen, sessionState, span } from "./sessions.js";
import { buildOrder, createPlacer } from "./ticket.js";

const VERSION = "1.1.0";
// The paid plugin's id in the cTrader Store (the `id` query parameter). Empty until the Store gives one; then only
// that id may place orders from this page. ponytail: a determined copier can get round it; there is no server.
const PAID_IDS = [];
const KEY = "ballast.v1";

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const edition = document.body.dataset.edition === "trial" ? "trial" : "full";
const full = edition === "full";
const canPlace = full && (PAID_IDS.length === 0 || PAID_IDS.includes(params.get("id")));
document.documentElement.dataset.theme = params.get("theme") === "light" ? "light" : "dark";
document.documentElement.lang = setLanguage(params.get("lang"));
applyStatic();
const DEC = (1.5).toLocaleString().includes(",") ? "," : ".";
const num = (v) => parseNumber(v, DEC);
const browserTz = (() => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"; } catch { return "UTC"; } })();
const TZS = [[browserTz, `Your time zone (${browserTz})`], ["UTC", "UTC"], ["Europe/Prague", "Prague (FTMO and others)"],
             ["Europe/Athens", "Athens: many brokers' server time"], ["America/New_York", "New York (forex day ends 17:00)"],
             ["Europe/London", "London"], ["Asia/Dubai", "Dubai"], ["Asia/Singapore", "Singapore"], ["Australia/Sydney", "Sydney"]]
  .filter((x, i, a) => a.findIndex((y) => y[0] === x[0]) === i);
const TZ_NAME = { "Europe/Prague": "Prague", "Europe/Athens": "Athens", "America/New_York": "New York", "Europe/London": "London",
                  "Asia/Dubai": "Dubai", "Asia/Singapore": "Singapore", "Australia/Sydney": "Sydney", UTC: "UTC" };

$("version").textContent = "v" + VERSION;
$("edition").textContent = t(full ? "h.full" : "h.trial");
$("acct").textContent = t("h.connecting");

// ---- storage: one record per account, in this browser or app only ---------------------------------------------------
let cfg = {};
let cfgKey = KEY;
function load(key) {
  try { return JSON.parse(localStorage.getItem(key)) || {}; } catch { return {}; }
}
function save() {
  try { localStorage.setItem(cfgKey, JSON.stringify(cfg)); } catch { /* storage may be off: settings last for this visit */ }
}

const st = { host: null, acct: null, sym: null, list: [], assetId: {}, assetName: {}, depositAsset: null, usdAsset: null,
             quotes: {}, quoteKey: "", stopQuotes: () => {}, details: {}, positions: [], deals: [], dealsComplete: false,
             built: null, frozen: null, limits: null, atr: null, tradeId: newTradeId(), side: "buy", painting: false, sent: false };

// ---- numbers: one format, the reader's own ---------------------------------------------------------------------------
const nf = (x, d) => (Number.isFinite(x) ? x.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }) : "-");
const CUR_DEC = { BTC: 8, ETH: 6, JPY: 0, HUF: 0, KRW: 0 };
const cur = () => (st.acct ? st.acct.currency : "");
const money = (x) => `${nf(x, CUR_DEC[cur()] ?? 2)} ${cur()}`;
const price = (x, s = st.sym) => nf(x, s ? s.digits : 5);
const isPoints = (s) => s && s.pipPosition === 0;
const unit = (s, one = false) => t(isPoints(s) ? (one ? "units.point" : "units.points") : (one ? "units.pip" : "units.pips"));
function baseName(s) {
  const n = s && st.assetName[s.baseAssetId];
  return n && n.length <= 6 ? n : t("units.units");
}
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
/** A refusal from the maths, in the reader's words. */
function why(r) {
  if (!r) return "";
  if (r.key === "minSize") return t("e.minSize", { min: money(r.minRisk), budget: money(r.budget), whose: t(r.cut ? "e.minSize.limits" : "e.minSize.chosen") });
  if (r.key === "entrySide") return t(`e.entrySide.${st.side}.${$("otype").value}`);
  if (r.key === "targetSide") return t(`e.targetSide.${st.side}`);
  if (r.key === "stopTooClose") return t("e.stopTooClose", { unit1: unit(st.sym, true), side: st.side === "buy" ? "bid" : "ask" });
  if (r.key === "netted") return t("e.netted", { symbol: st.sym ? st.sym.name : "" });
  if (r.key === "noRate") return t("e.noRate", { cur: cur() });
  return r.key ? t("e." + r.key) : r.message;
}

// ---- start-up --------------------------------------------------------------------------------------------------------
const FIELDS = ["risk", "risk-mode", "stop-unit", "target-unit", "comm-mode", "comm", "atr-period", "lim-day", "lim-day-mode",
                "lim-total", "lim-total-mode", "lim-start", "lim-rule", "lim-trail", "lim-hour", "lim-tz", "lim-open", "lim-totalfloor"];
const DAILY_FIELDS = ["lim-dayfloor", "lim-sodeq"];            // (today's figures: forgotten when the day resets)
const DEFAULTS = { risk: "1", "risk-mode": "percent", "stop-unit": "pips", "target-unit": "r", "comm-mode": "unset",
                   "lim-day-mode": "pct", "lim-total-mode": "pct", "lim-rule": "balance", "lim-trail": "static",
                   "lim-hour": "0", "lim-tz": "Europe/Prague", "lim-open": "stops" };

async function start() {
  for (let h = 0; h < 24; h++) $("lim-hour").add(new Option(String(h).padStart(2, "0") + ":00", String(h)));
  for (const [v, text] of TZS) $("lim-tz").add(new Option(text, v));
  showTab(load(KEY).tab || "ticket");
  if (!canPlace) {
    $("place").hidden = true;
    $("review-note").hidden = false;
    $("review-note").textContent = t(full ? "v.notPaid" : "v.trial");
  }
  if (!full) {
    $("limits-form").hidden = true;
    $("limits-out").textContent = t("f.limits");
    for (const id of ["journal-tables", "journal-log-card"]) $(id).hidden = true;
    $("csv").hidden = true;
    $("journal-sum").textContent = t("f.journal");
  }
  try {
    st.host = params.has("mock") ? await import("./host-mock.js") : await import("./host.js");
    await st.host.connect();
    st.acct = await st.host.account();
  } catch (e) {
    $("acct").textContent = t("h.notConnected");
    banner(t("e.notConnected", { why: e && e.message ? ` (${e.message})` : "" }));
    return;
  }
  cfgKey = `${KEY}.${st.acct.login}`;
  cfg = load(cfgKey);
  for (const f of FIELDS) if (cfg[f] != null || DEFAULTS[f] != null) $(f).value = cfg[f] ?? DEFAULTS[f];
  showAccount();
  try {
    st.list = await st.host.symbolList();
    const ids = [...new Set(st.list.flatMap((s) => [s.baseAssetId, s.quoteAssetId]).filter((x) => x != null))];
    for (const a of await st.host.assets(ids)) {
      st.assetId[a.name] = a.assetId;
      st.assetName[a.assetId] = a.name;
    }
  } catch { /* without the list only same-currency symbols can be sized; the ticket says so */ }
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
  setInterval(refreshAll, 30000);                           // (reading only: nothing is ever sent on a timer)
  setInterval(renderSessions, 30000);
}

function showAccount() {
  const a = st.acct;
  $("acct").textContent = `${t(a.environment === "demo" ? "h.demo" : "h.live")} · ${money(a.balance)}`;
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
    try { for (const d of await st.host.symbolsById(missing)) st.details[d.symbolId] = d; } catch { /* exposure shows "no price yet" */ }
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
    if (st.sym && q.symbolId === st.sym.symbolId) $("px").textContent = `${price(o.bid)} / ${price(o.ask)}`;
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
    banner(name ? t("e.noSymbolFound", { name }) : "");
  } else {
    st.details[st.sym.symbolId] = st.sym;
    banner(pathOf(st.sym.quoteAssetId) ? "" : t("e.noPath", { name, cur: cur() }));
    cfg.symbol = name;
    save();
    $("opt-pips").textContent = isPoints(st.sym) ? "points away" : "pips away";
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
  const u = $("stop-unit").value;
  if (s && Number.isFinite(stop) && Number.isFinite(entry) && u !== "price") {
    const d = u === "pips" ? stop * pipSize(s.pipPosition) : stop * (st.atr || NaN);
    stop = roundPrice(st.side === "buy" ? entry - d : entry + d, s.digits);
  }
  let target = num($("target").value);
  if (!Number.isFinite(target)) target = null;
  else if ($("target-unit").value === "r" && s && Number.isFinite(stop)) target = targetFromR(st.side, entry, stop, target, s.digits);
  const rate = s ? rateFor(s, stop) : NaN;
  let commission = 0;
  const cm = $("comm-mode").value;
  if (s && cm !== "unset" && cm !== "none") {
    const value = num($("comm").value);
    const lotUnits = s.lotSize * (s.unitsPerVolume || 1);
    const toUsd = s.quoteAssetId === st.usdAsset ? 1 : (() => { const r = conversionRate(pathOf(s.quoteAssetId, st.usdAsset), st.quotes); return r.ok ? r.rate : NaN; })();
    const usdToDep = st.usdAsset === st.depositAsset ? 1 : (() => { const r = conversionRate(pathOf(st.usdAsset), st.quotes); return r.ok ? r.rate : NaN; })();
    commission = Number.isFinite(value)
      ? commissionPerUnit({ mode: cm, value }, { lotUnits, usdPerUnit: entry * toUsd, usdToDeposit: usdToDep, depositPerUnit: entry * rate })
      : NaN;
  }
  const L = st.limits;
  return {
    symbol: s, side: st.side, orderType, entry, stop, target, quote, balance: st.acct ? st.acct.balance : NaN,
    riskMode: $("risk-mode").value, risk: num($("risk").value), rate, commission,
    feeRate: s && s.quoteAssetId !== st.depositAsset ? s.feeRate || 0 : 0,
    room: full && L && L.room != null ? L.room : null, limitsKnown: full && L ? L.known : true,
    accountType: st.acct && st.acct.accountType,
    positionOnSymbol: !!(s && st.positions.some((p) => p.symbolId === s.symbolId)), tradeId: st.tradeId,
  };
}

function renderTicket() {
  const inp = ticketInputs();
  st.built = buildOrder(inp);
  const out = $("result");
  out.textContent = "";
  const s = st.sym;
  const lotD = s ? lotDecimals(s) : 2;
  const L = full && st.limits;
  if (!st.built.ok) {
    out.append(el("p", st.built.key === "stopEmpty" || st.built.key === "noQuote" ? "neutral" : "warn", why(st.built)));
  } else {
    const r = st.built.review;
    out.append(el("div", "big", t("r.lots", { lots: nf(r.lots, lotD) })), el("div", "mut small", t("r.units", { units: nf(r.units, r.units < 10 ? 2 : 0), base: baseName(s) })));
    out.append(el("div", null, t("r.stopLine", { stop: price(r.stop), dist: nf(r.pips, 1), unit: unit(s), loss: money(r.riskMoney) })));
    if (r.commissionRisk > 0) out.append(el("div", "mut small", t("r.split", { price: money(r.priceRisk), comm: money(r.commissionRisk) })));
    const perPip = r.units * pipSize(s.pipPosition) * inp.rate;
    out.append(el("div", "mut small", t("r.perUnit", { unit1: unit(s, true), value: money(perPip) })));
    if (s.pipPosition !== 4 && s.pipPosition !== 2 && !isPoints(s)) {
      out.append(el("div", "mut small", t("r.priceDistance", { dist: nf(r.pips, 1), unit: unit(s), price: nf(Math.abs(r.entry - r.stop), s.digits) })));
    }
    if (s.quoteAssetId !== st.depositAsset && st.assetName[s.quoteAssetId]) {
      out.append(el("div", "mut small", t("r.conversion", { cur: cur(), quote: st.assetName[s.quoteAssetId], rate: nf(inp.rate, 5) })));
    }
    const rr = inp.target ? rewardRisk(inp.entry, inp.stop, inp.target) : null;
    if (rr) out.append(el("div", "mut small", t("r.target", { target: price(inp.target), rr: nf(rr.rr, 2), be: nf(rr.breakEvenWinRate * 100, 0) })));
    if (r.cut) out.append(el("div", "warn", t("r.cut")));
    if (r.capped) out.append(el("div", "warn", t("r.capped")));
    if (r.leverage > 20) out.append(el("div", "warn", t("r.leverage", { x: nf(r.leverage, 0) })));
  }
  if ($("comm-mode").value === "unset" && s) out.append(el("div", "mut small", t("r.commUnset")));
  if (L) {
    for (const [k, x] of [["day", L.day], ["total", L.total]]) {
      if (x && !x.error && (x.light === "amber" || x.light === "red")) out.append(el("div", "warn", t("r.limitWarn", { which: t("r.which." + k), pct: nf(x.used * 100, 0) })));
    }
  }
  const atrOn = $("stop-unit").value === "atr";
  document.querySelectorAll(".atr-row").forEach((e) => { e.hidden = !atrOn; });
  if (atrOn && s) {
    const period = $("atr-period").selectedOptions[0]?.text || "";
    if (st.atr) {
      const pips = st.atr / pipSize(s.pipPosition);
      const k = num($("stop").value);
      $("atr-line").textContent = t("r.atr", { period, atr: nf(st.atr, s.digits), pips: nf(pips, 1), unit: unit(s), k: Number.isFinite(k) ? nf(k, 2) : "-", kpips: Number.isFinite(k) ? nf(pips * k, 1) : "-" });
    } else {
      $("atr-line").textContent = t("r.atrNone", { period });
    }
  }
  const cm = $("comm-mode").value;
  document.querySelectorAll(".comm-row").forEach((e) => { e.hidden = cm === "unset" || cm === "none"; });
  const sumText = { unset: "· not set", none: "· no commission", lot: `· ${$("comm").value || "?"} ${cur()} a lot, each side`,
                    million: `· ${$("comm").value || "?"} USD a million, each side`, percent: `· ${$("comm").value || "?"}% each side` };
  $("costs-sum").textContent = sumText[cm] || "";
  document.querySelectorAll("[data-risk]").forEach((b) => b.classList.toggle("on", $("risk-mode").value === "percent" && num($("risk").value) === Number(b.dataset.risk)));
  $("review").disabled = !st.built.ok;
}

// ---- limits -------------------------------------------------------------------------------------------------------------
function openRisk() {
  let fromEntry = 0;
  let fromNow = 0;
  let noStop = 0;
  let unknown = 0;
  const rows = st.positions.map((p) => {
    const d = st.details[p.symbolId];
    const rate = d ? rateFor(d, p.stopLoss) : NaN;
    const u = d ? d.unitsPerVolume || 1 : 1;
    const risk = d && Number.isFinite(rate) ? positionRisk(p, rate, u) : undefined;
    const q = st.quotes[p.symbolId];
    const exitNow = q ? (p.side === "buy" ? q.bid : q.ask) : NaN;
    const now = risk == null || !Number.isFinite(exitNow) ? risk : positionRisk({ ...p, entryPrice: exitNow }, rate, u);
    if (risk === null) noStop += 1;
    else if (risk === undefined) unknown += 1;
    else {
      fromEntry += risk;
      fromNow += Number.isFinite(now) ? now : risk;
    }
    return { p, d, risk, now };
  });
  return { rows, fromEntry, fromNow, noStop, unknown };
}

function computeLimits() {
  const a = st.acct;
  if (!a || !full) return null;
  const startBal = num($("lim-start").value);
  const asMoney = (id, modeId) => {
    const v = num($(id).value);
    if (!Number.isFinite(v)) return null;                   // (empty: no limit)
    return $(modeId).value === "pct" ? (Number.isFinite(startBal) && startBal > 0 ? (startBal * v) / 100 : NaN) : v;
  };
  const now = Date.now();
  const tz = $("lim-tz").value || "UTC";
  const dayFrom = dayStart(now, Number($("lim-hour").value) || 0, tz);
  const equity = Number.isFinite(a.equity) ? a.equity : a.balance;
  if (!cfg.sod || cfg.sod.day !== dayFrom) {                // (the day's opening equity, if this panel sees the day begin)
    cfg.sod = { day: dayFrom, equity: now - dayFrom < 15 * 60000 ? equity : null };
    cfg.daily = { day: dayFrom };                           // (today's typed figures are forgotten at the reset)
    for (const f of DAILY_FIELDS) $(f).value = "";
    save();
  }
  const peak = Math.max(cfg.peak || 0, a.balance, equity);
  if (peak !== cfg.peak) { cfg.peak = peak; save(); }
  const exp = openRisk();
  const worstEquity = $("lim-open").value === "stops" ? equity - exp.fromNow : equity;
  const sodTyped = num($("lim-sodeq").value);
  const s = limitState({ balance: a.balance, equity, worstEquity, deals: st.deals, dayFrom, dealsOk: st.dealsComplete,
                         rule: $("lim-rule").value, sodEquity: Number.isFinite(sodTyped) ? sodTyped : cfg.sod.equity,
                         dayFloor: num($("lim-dayfloor").value), dayLimit: asMoney("lim-day", "lim-day-mode"),
                         totalLimit: asMoney("lim-total", "lim-total-mode"), initial: startBal, totalMode: $("lim-trail").value,
                         peak, totalFloor: num($("lim-totalfloor").value) });
  s.openNoStop = $("lim-open").value === "stops" ? exp.noStop + exp.unknown : 0;
  s.dayFrom = dayFrom;
  s.tz = tz;
  return s;
}

function renderLimits() {
  const s = (st.limits = computeLimits());
  if (!full) return;
  const box = $("limits-out");
  box.textContent = "";
  if (!s || (!s.day && !s.total)) {
    box.append(el("p", "mut", t("l.none")), el("p", "mut small", t("l.device")));
    $("light-tab").hidden = true;
    return;
  }
  const lights = [s.day, s.total].filter(Boolean).map((x) => x.light);
  const lightAll = lights.includes("unknown") ? "unknown" : lights.includes("red") ? "red" : lights.includes("amber") ? "amber" : "green";
  $("light-tab").hidden = false;
  $("light-tab").className = "dot " + lightAll;
  for (const [name, x] of [["l.today", s.day], ["l.total", s.total]]) {
    if (!x) continue;
    box.append(el("h3", null, t(name)));
    if (x.error) {
      box.append(el("p", "bad", t("l.err." + x.error)));
      continue;
    }
    const meter = el("div", "meter");
    const bar = el("i", x.light);
    bar.style.width = Math.min(100, x.used * 100).toFixed(1) + "%";
    meter.append(bar);
    box.append(el("div", null, t("l.used", { loss: money(x.loss), limit: money(x.limit), pct: nf(x.used * 100, 0) })), meter);
    if (x.worst > x.loss + 0.005) box.append(el("div", "small", t("l.worst", { worst: money(x.worst) })));
    box.append(el("div", "mut small", t("l.from", { what: t("l.ref." + x.refCode), ref: money(x.ref) })));
    if (x.uncertain) box.append(el("p", "warn", t("l.unc." + x.uncertain)));
  }
  if (s.room != null) {
    const reached = [s.day, s.total].some((x) => x && !x.error && x.light === "red");
    box.append(el("p", s.room > 0 ? null : "bad", s.room > 0 ? t("l.room", { room: money(s.room) }) : t(reached ? "l.reached" : "l.full")));
  }
  if (s.day) {
    const local = new Date(s.dayFrom).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    box.append(el("p", "mut small", t("l.dayBegan", { hour: String($("lim-hour").value).padStart(2, "0") + ":00", zone: TZ_NAME[s.tz] || s.tz, local })));
  }
  if (s.openNoStop) box.append(el("p", "warn", t("l.openNoStop", { n: s.openNoStop })));
  box.append(el("p", "mut small", t("l.gap")), el("p", "mut small", t("l.device")));
}

// ---- exposure -----------------------------------------------------------------------------------------------------------
function renderExposure() {
  const box = $("exposure-out");
  box.textContent = "";
  if (!st.positions.length) {
    box.append(el("p", "mut", t("x2.none")));
    return;
  }
  const exp = openRisk();
  const bal = st.acct.balance;
  for (const { p, d, risk, now } of exp.rows) {
    const row = el("div", "row");
    const left = el("div");
    const lots = d ? nf(p.volume / d.lotSize, lotDecimals(d)) : String(p.volume);
    left.append(el("b", null, `${p.symbolName} ${t(p.side === "buy" ? "v.buy" : "v.sell")}`),
                el("div", "mut small", t("x2.line", { lots, entry: price(p.entryPrice, d), stop: p.stopLoss ? price(p.stopLoss, d) : t("v.none") })));
    const right = el("div", "num");
    if (risk === null) right.append(el("span", "bad", t("x2.noStop")));
    else if (risk === undefined) right.append(el("span", "mut", t("x2.noPrice")));
    else right.append(el("b", null, t("x2.risk", { fromNow: money(now) })), el("div", "mut small", t("x2.fromEntry", { fromEntry: money(risk), pct: nf((risk / bal) * 100, 2) })));
    row.append(left, right);
    box.append(row);
  }
  box.append(el("h3", null, t("l.total")));
  box.append(el("div", null, t("x2.total", { total: money(exp.fromNow), pct: nf((exp.fromNow / bal) * 100, 2) })));
  if (exp.noStop) box.append(el("p", "bad", t("x2.totalNoStop", { n: exp.noStop })));
  else box.append(el("div", "mut small", t("x2.after", { bal: money(bal - exp.fromEntry) })));
}

// ---- journal ------------------------------------------------------------------------------------------------------------
function renderJournal() {
  if (!full) return;
  const trades = tradeLog(st.deals);
  const s = stats(trades);
  const box = $("journal-sum");
  box.textContent = "";
  if (!s.count) {
    box.append(el("p", "mut", t("j.none")));
  } else {
    const dl = el("dl");
    const add = (k, v) => dl.append(el("dt", null, t(k)), el("dd", null, v));
    add("j.trades", String(s.count));
    add("j.won", `${s.wins} (${nf(s.winRate * 100, 0)}%)`);
    add("j.avg", s.avgR === null ? "-" : t("j.perTrade", { r: nf(s.avgR, 2) }));
    add("j.avgWL", `${s.avgWinR === null ? "-" : nf(s.avgWinR, 2) + " R"} / ${s.avgLossR === null ? "-" : nf(s.avgLossR, 2) + " R"}`);
    add("j.pf", s.profitFactor === null ? "-" : nf(s.profitFactor, 2));
    add("j.net", money(s.net));
    add("j.streak", String(s.maxLosingStreak));
    box.append(dl);
    if (s.count < 30) box.append(el("p", "mut small", t("j.small")));
  }
  if (!st.dealsComplete) box.append(el("p", "warn", t("j.incomplete")));
  const sym = $("journal-sym").tBodies[0];
  sym.textContent = "";
  for (const x of bySymbol(trades)) {
    const r = sym.insertRow();
    [x.symbol, x.count, nf(x.winRate * 100, 0) + "%", x.avgR === null ? "-" : nf(x.avgR, 2), money(x.net)].forEach((v, i) => {
      const c = r.insertCell();
      c.textContent = v;
      if (i) c.className = "num" + (i === 4 ? (x.net >= 0 ? " pos" : " neg") : "");
    });
  }
  const log = $("journal-log").tBodies[0];
  log.textContent = "";
  for (const tr of trades.slice(0, 50)) {
    const r = log.insertRow();
    [new Date(tr.closed).toLocaleDateString(), tr.symbol, t(tr.side === "buy" ? "v.buy" : "v.sell"), money(tr.net), tr.r === null ? "-" : nf(tr.r, 2)].forEach((v, i) => {
      const c = r.insertCell();
      c.textContent = v;
      if (i >= 3) c.className = "num " + (tr.net >= 0 ? "pos" : "neg");
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
    left.append(el("b", null, s.name), el("div", "mut small", t("s.there", { time: s.local })));
    const right = el("div", "num");
    right.append(s.open ? el("span", "open-badge", t("s.open")) : el("span", "mut", t("s.closed")),
                 el("div", "mut small", s.next ? t(s.open ? "s.closes" : "s.opens", { span: span(s.next - now) }) : ""));
    row.append(left, right);
    box.append(row);
  }
  const open = ss.filter((s) => s.open).map((s) => s.name);
  box.append(el("p", "small", !fxWeekOpen(now) ? t("s.weekend") : open.includes("London") && open.includes("New York") ? t("s.overlap") : open.length ? t("s.openNow", { list: open.join(", ") }) : t("s.between")),
             el("p", "mut small", t("s.yourTime", { time: new Date(now).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) })));
}

// ---- painting ---------------------------------------------------------------------------------------------------------
function paint() {
  renderLimits();                                           // (first: the ticket sizes against the limits' room)
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
  st.sent = false;
  const r = st.frozen.review;
  const s = st.sym;
  const typeName = t({ market: "v.market", limit: "v.limit", stop: "v.stopOrder" }[r.orderType]);
  const rows = [["v.symbol", r.symbol], ["v.side", t(r.side === "buy" ? "v.buy" : "v.sell")], ["v.order", typeName],
                ["v.entry", r.orderType === "market" ? t("v.entryMarket", { price: price(r.entry) }) : price(r.entry)],
                ["v.stop", t("v.stopValue", { stop: price(r.stop), dist: nf(r.pips, 1), unit: unit(s), fromFill: r.orderType === "market" ? t("v.fromFill") : "" })],
                ["v.target", r.target ? price(r.target) : t("v.none")], ["v.size", t("r.lots", { lots: nf(r.lots, lotDecimals(s)) })],
                ["v.loss", t("v.lossValue", { loss: money(r.riskMoney), comm: r.commissionRisk > 0 ? t("v.lossComm") : "" })]];
  const dl = $("review-list");
  dl.textContent = "";
  for (const [k, v] of rows) dl.append(el("dt", null, t(k)), el("dd", null, v));
  $("place").textContent = t("v.place", { side: t(r.side === "buy" ? "v.buy" : "v.sell"), lots: nf(r.lots, lotDecimals(s)), symbol: r.symbol });
  $("place").className = "go " + r.side;
  $("place-msg").textContent = "";
  $("place").disabled = false;
  $("again").hidden = true;
  for (const id of ["ticket-form", "result", "review"]) $(id).hidden = true;   // (the review takes the form's place)
  $("reviewbox").hidden = false;
  $("app").scrollIntoView({ block: "start" });
}

function closeReview() {
  st.frozen = null;
  $("reviewbox").hidden = true;
  for (const id of ["ticket-form", "result", "review"]) $(id).hidden = false;
}

function refusal(res) {
  if (res.code === "timeout" || res.code === "busy") return t("x." + res.code);
  const raw = String(res.message || "").replace(/^cTrader refused the order: /, "").replace(/\.$/, "");
  const code = Object.keys({ NOT_ENOUGH_MONEY: 1, MARKET_CLOSED: 1, TRADING_DISABLED: 1, INVALID_VOLUME: 1, TRADING_BAD_VOLUME: 1, TRADING_BAD_STOPS: 1 }).find((c) => raw.includes(c));
  return code ? t("x." + code) : t("x.other", { why: raw || "unknown reason" });
}

async function place(ev) {
  if (!ev.isTrusted || !canPlace || !st.frozen || st.sent) return;   // (a real click only)
  const now = buildOrder(ticketInputs());                           // (the limits and the account, checked again now)
  if (!now.ok && ["limit", "limits", "netted", "account", "quote", "symbol"].includes(now.code)) {
    $("place-msg").textContent = why(now);
    return;
  }
  if (st.limits && st.limits.room != null && st.frozen.review.riskMoney > st.limits.room + 1e-9) {
    $("place-msg").textContent = t("v.again", { room: money(st.limits.room) });
    return;
  }
  $("place").disabled = true;
  $("place-msg").textContent = t("v.sending");
  const res = await placer.place(st.frozen.request);
  if (res.ok) {
    st.sent = true;
    $("place-msg").textContent = t("v.sent", { id: res.answer && res.answer.orderId != null ? "#" + res.answer.orderId : "" });
    $("again").hidden = false;
    st.tradeId = newTradeId();                                     // (the next trade gets its own id)
    setTimeout(refreshAll, 1500);
  } else {
    $("place-msg").textContent = refusal(res);
  }
}

// ---- events -------------------------------------------------------------------------------------------------------------
function showTab(name) {
  document.querySelectorAll("[data-tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === name)));
  document.querySelectorAll(".tab").forEach((x) => { x.hidden = x.id !== "tab-" + name; });
  try { const g = load(KEY); g.tab = name; localStorage.setItem(KEY, JSON.stringify(g)); } catch { /* fine */ }
}
document.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
document.querySelectorAll("[data-side]").forEach((b) => b.addEventListener("click", () => {
  st.side = b.dataset.side;
  document.querySelectorAll("[data-side]").forEach((x) => x.classList.toggle("on", x === b));
  edited();
}));
document.querySelectorAll("[data-risk]").forEach((b) => b.addEventListener("click", () => {
  $("risk").value = b.dataset.risk;
  $("risk-mode").value = "percent";
  edited();
}));
$("otype").addEventListener("change", () => {
  document.querySelectorAll(".entry-row").forEach((e) => { e.hidden = $("otype").value === "market"; });
  edited();
});
for (const id of ["entry", "stop", "target", ...FIELDS, ...DAILY_FIELDS]) {
  const e = $(id);
  e.addEventListener(e.tagName === "SELECT" ? "change" : "input", edited);
  if (e.tagName === "INPUT") e.addEventListener("change", edited);
}
for (const id of ["entry", "stop", "target", "risk"]) {
  $(id).addEventListener("keydown", (ev) => { if (ev.key === "Enter" && !$("review").disabled) openReview(); });
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
$("again").addEventListener("click", () => {
  $("stop").value = "";
  $("target").value = "";
  closeReview();
  paint();
});
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
