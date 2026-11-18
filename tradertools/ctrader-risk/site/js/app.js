// The panel: reads the inputs, sizes the trade with risk.js, builds the order with ticket.js, and sends it only from
// a real click on the review screen. host.js (cTrader) or host-mock.js (?mock=1) supplies the account and prices.
import {
  conversionPath, conversionRate, dayStart, lossLight, marketEntry, money, pipSize, realisedLossSince, rewardRisk,
  summary, targetFromR, tradeLog,
} from "./risk.js";
import { buildOrder, createPlacer } from "./ticket.js";

const VERSION = "0.1.0";
// The paid plugin's id in the cTrader Store (the `id` query parameter). Empty until the Store gives one; then only
// that id may place orders from this page. ponytail: a determined copier can get round it; there is no server.
const PAID_IDS = [];
const STORE_KEY = "ert.v1";

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const edition = document.body.dataset.edition === "trial" ? "trial" : "full";
const canPlace = edition === "full" && (PAID_IDS.length === 0 || PAID_IDS.includes(params.get("id")));
document.documentElement.dataset.theme = params.get("theme") === "light" ? "light" : "dark";
$("version").textContent = "v" + VERSION;
$("edition").textContent = edition === "trial" ? "Trial: calculates, shows the limits; does not place orders" : "Exact Risk Ticket";

const settings = load();
const st = { host: null, acct: null, sym: null, list: [], depositAsset: null, path: null, quotes: {}, stopQuotes: null,
             side: "buy", deals: [], built: null, frozen: null, limitReached: false };

function load() {
  try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; } catch { return {}; }
}
function save() {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(settings)); } catch { /* storage may be off: settings last for this visit */ }
}
const num = (v) => {
  const x = Number(String(v ?? "").replace(",", ".").trim());
  return String(v ?? "").trim() === "" || !Number.isFinite(x) ? NaN : x;
};
const fmt = (x, d) => (Number.isFinite(x) ? x.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }) : "-");
function banner(text) {
  $("banner").hidden = !text;
  $("banner").textContent = text || "";
}

// ---- start-up -------------------------------------------------------------------------------------------------
async function start() {
  for (let h = 0; h < 24; h++) $("lim-hour").add(new Option(String(h).padStart(2, "0") + ":00", String(h)));
  $("risk").value = settings.risk ?? "1";
  $("risk-mode").value = settings.riskMode || "percent";
  $("stop-unit").value = settings.stopUnit || "pips";
  $("target-unit").value = settings.targetUnit || "r";
  $("lim-day").value = settings.limDay ?? "";
  $("lim-total").value = settings.limTotal ?? "";
  $("lim-start").value = settings.limStart ?? "";
  $("lim-hour").value = String(settings.limHour ?? 0);
  if (!canPlace) {
    $("place").hidden = true;
    $("review-note").hidden = false;
    $("review-note").textContent = edition === "trial"
      ? "The trial calculates the size and shows the loss limits. Placing the order from here is in the full version."
      : "This copy is not the Store's paid plugin, so it does not place orders.";
  }
  try {
    st.host = params.has("mock") ? await import("./host-mock.js") : await import("./host.js");
    await st.host.connect();
    st.acct = await st.host.account();
  } catch (e) {
    $("acct").textContent = "Not connected";
    banner("This panel runs inside cTrader. It could not reach cTrader here" + (e && e.message ? ` (${e.message})` : "") + ".");
    return;
  }
  if (!$("lim-start").value) $("lim-start").value = String(st.acct.balance);
  showAccount();
  st.list = await st.host.symbolList().catch(() => []);
  const ids = [...new Set(st.list.flatMap((s) => [s.baseAssetId, s.quoteAssetId]).filter((x) => x != null))];
  const names = await st.host.assets(ids).catch(() => []);
  const dep = names.find((a) => a.name === st.acct.currency);
  st.depositAsset = dep ? dep.assetId : null;
  await loadSymbol(params.get("symbol") || settings.symbol || "EURUSD");
  st.host.onExecution(() => refreshAccount());
  await refreshDeals();
  setInterval(refreshAccount, 60000);           // (reading only: nothing is ever sent on a timer)
}

function showAccount() {
  const a = st.acct;
  $("acct").textContent = `${a.environment === "demo" ? "Demo" : "Live"} · balance ${fmt(a.balance, 2)} ${a.currency}`;
}

async function refreshAccount() {
  try { st.acct = await st.host.account(); showAccount(); } catch { /* keep the last figures */ }
  await refreshDeals();
}

async function refreshDeals() {
  const now = Date.now();
  st.deals = await st.host.deals(now - 35 * 86400000, now).catch(() => st.deals);
  renderLog();
  compute();
}

async function loadSymbol(name) {
  name = String(name || "").trim().toUpperCase();
  $("sym").value = name;
  if (st.stopQuotes) st.stopQuotes();
  st.sym = name ? await st.host.symbol(name).catch(() => null) : null;
  if (!st.sym) {
    banner(`No symbol called ${name || "(empty)"} on this account.`);
    compute();
    return;
  }
  banner("");
  settings.symbol = name;
  save();
  st.path = st.depositAsset == null ? null : conversionPath(st.list, st.sym.quoteAssetId, st.depositAsset);
  if (!st.path) banner(`There is no price to turn ${name}'s currency into ${st.acct.currency}, so the risk cannot be sized.`);
  const ids = [st.sym.symbolId, ...(st.path || []).map((p) => p.symbolId)];
  st.stopQuotes = st.host.quotes([...new Set(ids)], (q) => {
    st.quotes[q.symbolId] = { bid: q.bid, ask: q.ask };
    if (q.symbolId === st.sym.symbolId) $("px").textContent = `${fmt(q.bid, st.sym.digits)} / ${fmt(q.ask, st.sym.digits)}`;
    compute();
  });
  compute();
}

// ---- the sum ---------------------------------------------------------------------------------------------------
function inputs() {
  const s = st.sym;
  const orderType = $("otype").value;
  const quote = s ? st.quotes[s.symbolId] : null;
  const entry = orderType === "market" ? marketEntry(st.side, quote) : num($("entry").value);
  let stop = num($("stop").value);
  if ($("stop-unit").value === "pips" && s && Number.isFinite(stop) && Number.isFinite(entry)) {
    const d = stop * pipSize(s.pipPosition);
    stop = Math.round((st.side === "buy" ? entry - d : entry + d) * 10 ** s.digits) / 10 ** s.digits;
  }
  let target = num($("target").value);
  if (!Number.isFinite(target)) target = null;
  else if ($("target-unit").value === "r" && s && Number.isFinite(stop)) target = targetFromR(st.side, entry, stop, target, s.digits);
  const conv = conversionRate(st.path, st.quotes);
  return { symbol: s, side: st.side, orderType, entry, stop, target, quote, balance: st.acct ? st.acct.balance : NaN,
           riskMode: $("risk-mode").value, risk: num($("risk").value), rate: conv.ok ? conv.rate : NaN, limitReached: st.limitReached };
}

function compute() {
  updateLimits();
  const inp = inputs();
  st.built = buildOrder(inp);
  const out = $("result");
  out.textContent = "";
  const cur = st.acct ? st.acct.currency : "";
  if (!st.built.ok) {
    const p = document.createElement("p");
    p.className = "warn";
    p.textContent = st.built.message;
    out.append(p);
  } else {
    const r = st.built.review;
    const big = document.createElement("div");
    big.className = "big";
    big.textContent = `${fmt(r.lots, 2)} lots`;
    const line = document.createElement("div");
    line.textContent = `${fmt(r.units, 2)} units · risk ${money(r.riskMoney)} ${cur} of ${money(r.budget)} · stop ${fmt(r.pips, 1)} pips`;
    out.append(big, line);
    const rr = inp.target ? rewardRisk(inp.entry, inp.stop, inp.target) : null;
    if (rr) {
      const t = document.createElement("div");
      t.className = "mut";
      t.textContent = `Target ${fmt(inp.target, st.sym.digits)} · ${fmt(rr.rr, 2)} times the risk · breaks even at ${fmt(rr.breakEvenWinRate * 100, 0)}% wins, before costs`;
      out.append(t);
    }
    if (r.capped) {
      const c = document.createElement("div");
      c.className = "warn";
      c.textContent = "Capped at the largest size this symbol allows.";
      out.append(c);
    }
  }
  $("review").disabled = !st.built.ok;
  if (st.frozen && !$("reviewbox").hidden && !sameReview(st.frozen, st.built)) closeReview();
}

function sameReview(a, b) {
  return b.ok && JSON.stringify(a.request) === JSON.stringify(b.request);
}

// ---- the limits and the log ------------------------------------------------------------------------------------
function updateLimits() {
  const hour = Number($("lim-hour").value) || 0;
  const from = dayStart(Date.now(), hour, -new Date().getTimezoneOffset());
  const dayLoss = realisedLossSince(st.deals, from);
  const limDay = num($("lim-day").value);
  const limTotal = num($("lim-total").value);
  const startBal = num($("lim-start").value);
  const totalLoss = st.acct && Number.isFinite(startBal) ? Math.max(0, startBal - st.acct.balance) : 0;
  const dl = lossLight(dayLoss, limDay);
  const tl = lossLight(totalLoss, limTotal);
  paintLight($("light-day"), dl, "day");
  paintLight($("light-total"), tl, "total");
  st.limitReached = dl === "red" || tl === "red";
  const cur = st.acct ? st.acct.currency : "";
  const parts = [`Closed today: ${money(dayLoss)} ${cur} lost${Number.isFinite(limDay) ? ` of ${money(limDay)}` : ""}`];
  if (Number.isFinite(limTotal)) parts.push(`down ${money(totalLoss)} of ${money(limTotal)} from ${money(startBal)}`);
  parts.push("Open trades are not counted. The limit locks this panel only, not the rest of cTrader.");
  $("limits-out").textContent = parts.join(" · ");
}

function paintLight(el, light, what) {
  el.hidden = light === "off";
  el.className = "light " + light;
  el.textContent = light === "red" ? `${what}: limit` : light === "amber" ? `${what}: 80%` : `${what}: ok`;
}

function renderLog() {
  const log = tradeLog(st.deals).slice(0, 20);
  const s = summary(log);
  $("log-sum").textContent = s.count
    ? `${s.count} trades placed here, last 35 days · ${fmt(s.winRate * 100, 0)}% won · average ${s.avgR === null ? "-" : fmt(s.avgR, 2) + " R"} · profit factor ${s.profitFactor === null ? "-" : fmt(s.profitFactor, 2)}`
    : "Trades placed from this panel show here once they close.";
  const body = $("log").tBodies[0];
  body.textContent = "";
  for (const t of log) {
    const row = body.insertRow();
    const cells = [new Date(t.closed).toLocaleDateString(), t.symbol, t.side, money(t.net), t.r === null ? "-" : fmt(t.r, 2) + " R"];
    cells.forEach((v, i) => {
      const c = row.insertCell();
      c.textContent = v;
      if (i >= 3) c.className = "num " + (t.net >= 0 ? "pos" : "neg");
    });
  }
}

// ---- review and place: the only path to an order ----------------------------------------------------------------
const placer = createPlacer((request) => st.host.placeOrder(request));

function openReview() {
  if (!st.built || !st.built.ok) return;
  st.frozen = st.built;
  const r = st.frozen.review;
  const d = st.sym.digits;
  const rows = [["Symbol", r.symbol], ["Side", r.side === "buy" ? "Buy" : "Sell"], ["Order", r.orderType],
                ["Entry", r.orderType === "market" ? `market (now ${fmt(r.entry, d)})` : fmt(r.entry, d)],
                ["Stop", `${fmt(r.stop, d)} (${fmt(r.pips, 1)} pips)`], ["Target", r.target ? fmt(r.target, d) : "none"],
                ["Size", `${fmt(r.lots, 2)} lots (${fmt(r.units, 2)} units)`], ["Risk", `${money(r.riskMoney)} ${st.acct.currency}`]];
  const dl = $("review-list");
  dl.textContent = "";
  for (const [k, v] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = k;
    const dd = document.createElement("dd");
    dd.textContent = v;
    dl.append(dt, dd);
  }
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
  if (!ev.isTrusted || !canPlace || !st.frozen || st.limitReached) return;     // (a real click only)
  $("place").disabled = true;
  $("place-msg").textContent = "Sending...";
  const res = await placer.place(st.frozen.request);
  $("place-msg").textContent = res.ok ? `Sent. cTrader order ${res.answer && res.answer.orderId != null ? "#" + res.answer.orderId : "accepted"}.` : res.message;
  if (res.ok) setTimeout(refreshAccount, 1500);
}

// ---- events ----------------------------------------------------------------------------------------------------
document.querySelectorAll("[data-side]").forEach((b) => b.addEventListener("click", () => {
  st.side = b.dataset.side;
  document.querySelectorAll("[data-side]").forEach((x) => x.classList.toggle("on", x === b));
  compute();
}));
$("otype").addEventListener("change", () => {
  document.querySelectorAll(".entry-row").forEach((e) => { e.hidden = $("otype").value === "market"; });
  compute();
});
for (const id of ["entry", "stop", "target", "risk", "lim-day", "lim-total", "lim-start"]) $(id).addEventListener("input", onSetting);
for (const id of ["stop-unit", "target-unit", "risk-mode", "lim-hour"]) $(id).addEventListener("change", onSetting);
function onSetting() {
  Object.assign(settings, { risk: $("risk").value, riskMode: $("risk-mode").value, stopUnit: $("stop-unit").value,
                            targetUnit: $("target-unit").value, limDay: $("lim-day").value, limTotal: $("lim-total").value,
                            limStart: $("lim-start").value, limHour: Number($("lim-hour").value) });
  save();
  compute();
}
$("sym").addEventListener("change", () => loadSymbol($("sym").value));
$("review").addEventListener("click", openReview);
$("back").addEventListener("click", closeReview);
$("place").addEventListener("click", place);

start();
