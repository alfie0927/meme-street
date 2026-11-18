// Ballast, stage 0: what does cTrader really give a web plugin? Each answer goes into one block of text the owner copies
// back. Orders are possible only on an account cTrader reports as demo, only from a real click, and only at the
// symbol's smallest size. Delete this file and probe.html before the Store listing.
import {
  accountInfo, availablePeriods, cancelOrder, closePosition, createClientAdapter, dealHistory, firstValueFrom, handshake, newOrder,
  pendingOrders, positions, sdkVersion, subscribeQuotes, symbolByName, trendbars,
} from "../vendor/ctrader-sdk.js";

const $ = (id) => document.getElementById(id);
const res = { when: new Date().toISOString(), sdk: sdkVersion, query: Object.fromEntries(new URLSearchParams(location.search)) };
const show = () => { $("out").value = JSON.stringify(res, null, 1); };
function step(label, value) {
  const li = document.createElement("li");
  li.textContent = `${label}: ${typeof value === "string" ? value : JSON.stringify(value)}`;
  $("steps").append(li);
  show();
}
const msg = (t) => { $("t-msg").textContent = t; };
let adapter, sym, lastQuote, positionId, orderId;
const call = (fn, payload) => firstValueFrom(fn(adapter, payload, { timeoutMs: 10000 }));
const err = (e) => ({ error: (e && (e.code || e.message)) || String(e) });

async function run() {
  try {
    adapter = createClientAdapter();
    const hello = await firstValueFrom(handshake(adapter));
    res.hello = { hostKind: hello.hostKind, hostVersion: hello.hostVersion, requests: hello.requestTypes, subscriptions: hello.subscriptionTypes };
    step("Connected", `${hello.hostKind} ${hello.hostVersion}, ${hello.requestTypes.length} request types`);
  } catch (e) {
    res.hello = err(e);
    step("Connect FAILED", res.hello);
    return;
  }
  try {
    const a = await call(accountInfo, null);
    res.account = { environment: a.environmentType, currency: a.depositCurrency, balance: a.balance, equity: a.equity, type: a.accountType };
    step("Account", res.account);
  } catch (e) {
    res.account = err(e);
    step("Account FAILED", res.account);
  }
  const name = res.query.symbol || "EURUSD";
  try {
    sym = ((await call(symbolByName, { name })).symbols || [])[0];
    res.symbol = sym || "not found";
    step("Symbol " + name, sym ? { lotSize: sym.lotSize, minVolume: sym.minVolume, volumeStep: sym.volumeStep, digits: sym.digits, pipPosition: sym.pipPosition } : "not found");
  } catch (e) {
    res.symbol = err(e);
    step("Symbol FAILED", res.symbol);
  }
  try {
    const k = "ert.probe";
    res.storage = { before: localStorage.getItem(k) };
    localStorage.setItem(k, res.when);
    res.storage.after = localStorage.getItem(k);
    step("Storage (reload the panel: 'before' should then show the last visit)", res.storage);
  } catch (e) {
    res.storage = err(e);
    step("Storage FAILED", res.storage);
  }
  if (sym) {
    res.quotes = { total: 0, whileHidden: 0, hiddenSpells: 0 };
    subscribeQuotes(adapter, { symbolIds: [sym.symbolId] }).subscribe({
      next: (q) => {
        lastQuote = q;
        res.quotes.total += 1;
        if (document.hidden) res.quotes.whileHidden += 1;
        if (res.quotes.total === 1) step("First quote", q);
        if (res.quotes.total % 20 === 0) show();
      },
      error: (e) => step("Quotes FAILED", err(e)),
    });
    document.addEventListener("visibilitychange", () => { if (document.hidden) res.quotes.hiddenSpells += 1; show(); });
  }
  try {
    const ps = (await call(availablePeriods, null)).periods || [];
    res.periods = ps.map((p) => p.code + "=" + p.name).join(", ");
    const h1 = (ps.find((p) => /hour/i.test(p.name)) || ps[0] || {}).code;
    const bars = sym && h1 ? (await call(trendbars, { symbolId: sym.symbolId, period: h1, count: 20 })).bars || [] : [];
    res.bars = { period: h1, count: bars.length, first: bars[0], last: bars[bars.length - 1] };
    step("Chart bars", res.bars.count + " bars of " + h1);
  } catch (e) {
    res.bars = err(e);
    step("Chart bars FAILED", res.bars);
  }
  try {
    const open = (await call(positions, null)).positions || [];
    res.openPositions = open.slice(0, 3);
    step("Open positions", open.length);
  } catch (e) {
    res.openPositions = err(e);
    step("Open positions FAILED", res.openPositions);
  }
  const demo = res.account && res.account.environment === "demo";
  if (!demo) {
    msg("cTrader does not report this account as demo, so the order tests stay off.");
    return;
  }
  $("t-market").disabled = !sym;
  $("t-limit").disabled = !sym;
  $("t-deals").disabled = false;
}

function smallest() {
  return sym.minVolume || sym.volumeStep;
}

$("t-market").addEventListener("click", async (ev) => {
  if (!ev.isTrusted) return;
  $("t-market").disabled = true;
  const req = { symbolId: sym.symbolId, orderType: "market", side: "buy", volume: smallest(), stopLossPips: 50, takeProfitPips: 50, stopLossTriggerMethod: "trade", label: "BLST r=1.00 id=probe001" };
  try {
    res.market = { request: req, answer: await call(newOrder, req) };
    await new Promise((r) => setTimeout(r, 2000));
    const open = (await call(positions, null)).positions || [];
    const p = open.filter((x) => x.symbolId === sym.symbolId).sort((a, b) => (a.openTimestamp < b.openTimestamp ? 1 : -1))[0];
    res.market.position = p || "no open position found";
    if (p) {
      positionId = p.positionId;
      $("t-close").disabled = false;
    }
    msg(p ? `Opened: volume ${p.volume}, quantity ${p.quantity}, stop ${p.stopLoss}, target ${p.takeProfit}. Now close it (2).` : "The order was answered, but no position was found.");
  } catch (e) {
    res.market = { request: req, ...err(e) };
    msg("Market order FAILED: " + JSON.stringify(err(e)));
  }
  show();
});

$("t-close").addEventListener("click", async (ev) => {
  if (!ev.isTrusted || !positionId) return;
  $("t-close").disabled = true;
  try {
    res.close = { answer: await call(closePosition, { positionId }) };
    msg("Closed. Wait a few seconds, then run test 5 to see whether the closed deal kept its label.");
  } catch (e) {
    res.close = err(e);
    msg("Close FAILED: " + JSON.stringify(err(e)));
  }
  show();
});

$("t-limit").addEventListener("click", async (ev) => {
  if (!ev.isTrusted || !lastQuote) { msg("Wait for the first quote."); return; }
  $("t-limit").disabled = true;
  const f = 10 ** sym.digits;
  const entry = Math.round(lastQuote.bid * 0.9 * f) / f;              // 10% below: it will not fill
  const pip = 10 ** -sym.pipPosition;
  const req = { symbolId: sym.symbolId, orderType: "limit", side: "buy", volume: smallest(), entryPrice: entry,
                stopLoss: Math.round((entry - 50 * pip) * f) / f, takeProfit: Math.round((entry + 50 * pip) * f) / f, stopLossTriggerMethod: "trade", label: "BLST r=1.00 id=probe002" };
  try {
    res.limit = { request: req, answer: await call(newOrder, req) };
    orderId = res.limit.answer.orderId;
    await new Promise((r) => setTimeout(r, 1500));
    res.limit.pending = ((await call(pendingOrders, null)).pendingOrders || []).find((o) => o.orderId === orderId) || "not in the pending list";
    $("t-cancel").disabled = !orderId;
    msg(`Limit order ${orderId} placed at ${entry}. Now cancel it (4).`);
  } catch (e) {
    res.limit = { request: req, ...err(e) };
    msg("Limit order FAILED: " + JSON.stringify(err(e)));
  }
  show();
});

$("t-cancel").addEventListener("click", async (ev) => {
  if (!ev.isTrusted || !orderId) return;
  $("t-cancel").disabled = true;
  try {
    res.cancel = { answer: await call(cancelOrder, { orderId }) };
    msg("Cancelled.");
  } catch (e) {
    res.cancel = err(e);
    msg("Cancel FAILED: " + JSON.stringify(err(e)));
  }
  show();
});

$("t-deals").addEventListener("click", async (ev) => {
  if (!ev.isTrusted) return;
  const now = Date.now();
  try {
    const r = await call(dealHistory, { fromTimestamp: new Date(now - 2 * 86400000).toISOString(), toTimestamp: new Date(now).toISOString() });
    res.deals = { count: (r.deals || []).length, hasMore: r.hasMore, last: (r.deals || []).slice(0, 5) };
    msg(`${res.deals.count} deals read. Copy the results below.`);
  } catch (e) {
    res.deals = err(e);
    msg("Deals FAILED: " + JSON.stringify(err(e)));
  }
  show();
});

run();
