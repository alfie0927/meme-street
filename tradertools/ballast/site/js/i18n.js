// Ballast: every sentence the panel shows, in one place. English is complete; another language is a second table with
// the same keys (a missing key falls back to English). `t(key, vars)` fills {name} slots. The static page text is in
// index.html with data-t keys and is replaced only when a table has that key.
export const EN = {
  // refusals from risk.js and ticket.js (by key)
  "e.symbolDetails": "This symbol's trading details are missing. Open Ballast on the symbol again.",
  "e.balance": "The account balance is not available yet.",
  "e.riskEmpty": "Type your risk: a percent of your balance, or an amount of money.",
  "e.riskTooBig": "The risk cannot be more than 100% of your balance.",
  "e.entryEmpty": "Type the entry price.",
  "e.stopEmpty": "Type your stop: how far the price can move against you before the trade closes. The size appears here.",
  "e.noRate": "There is no price yet to turn this symbol's currency into {cur}, so the risk cannot be sized.",
  "e.commission": "The commission cannot be worked out for this symbol. Check it under Costs.",
  "e.fee": "This symbol's conversion fee is not valid.",
  "e.side": "Choose Buy or Sell.",
  "e.stopAtEntry": "The stop is at the entry price. Move it away from the entry.",
  "e.stopSideBuy": "For a buy, the stop must be below the entry.",
  "e.stopSideSell": "For a sell, the stop must be above the entry.",
  "e.noRoom": "Your loss limits leave no room for a new trade. Ballast will not place orders until they reset.",
  "e.minSize": "The smallest size this symbol allows would lose {min} at the stop, more than the {budget} {whose}. Nothing is placed. Use a closer stop or a bigger risk.",
  "e.minSize.chosen": "you chose",
  "e.minSize.limits": "your limits leave",
  "e.limitsUnknown": "Your loss limits cannot be checked right now (see Limits). Nothing is placed until they can.",
  "e.spreadBetting": "This is a spread-betting account: sizes there are stakes per point, which Ballast does not size. Use cTrader's own ticket.",
  "e.noSymbol": "Type a symbol name above, for example EURUSD.",
  "e.prediction": "This is a prediction-market symbol, which Ballast does not size.",
  "e.netted": "This is a netting account and you already hold {symbol}: a new order would change that position instead of opening a new one. Close it first, or use cTrader's own ticket.",
  "e.noQuote": "Waiting for this symbol's live price.",
  "e.stopTooClose": "The stop is too close: it must be at least 1 {unit1} beyond the {side} price, or it would be hit as soon as the order fills.",
  "e.entrySide.buy.limit": "A buy limit order must be below the current price.",
  "e.entrySide.buy.stop": "A buy stop order must be above the current price.",
  "e.entrySide.sell.limit": "A sell limit order must be above the current price.",
  "e.entrySide.sell.stop": "A sell stop order must be below the current price.",
  "e.targetInvalid": "The target is not a valid price.",
  "e.targetSide.buy": "For a buy, the target must be above the entry.",
  "e.targetSide.sell": "For a sell, the target must be below the entry.",
  "e.noSymbolFound": "No symbol called {name} on this account.",
  "e.noPath": "There is no price to turn {name}'s currency into {cur}, so its risk cannot be sized.",
  "e.notConnected": "Ballast runs inside cTrader and could not reach it here{why}.",
  // the ticket's result
  "r.lots": "{lots} lots",
  "r.units": "{units} {base}",
  "r.stopLine": "Stop {stop} · {dist} {unit} · loses {loss} if hit",
  "r.split": "{price} price + {comm} commission",
  "r.perUnit": "1 {unit1} = {value} on this size",
  "r.priceDistance": "{dist} {unit} is {price} in price",
  "r.conversion": "Valued in {cur} at 1 {quote} = {rate} {cur}",
  "r.target": "Target {target} · {rr} times your risk · you need to win more than {be}% of such trades to come out ahead, before costs",
  "r.cut": "Made smaller to stay inside your loss limits.",
  "r.capped": "Capped at the largest size this symbol allows.",
  "r.leverage": "This position is worth {x} times your balance: a close stop makes a big position. Check you have the margin.",
  "r.commUnset": "Commission is not set. If your account pays commission, set it under Costs; if it does not, choose \"none\" there.",
  "r.limitWarn": "{which} loss limit: {pct}% used.",
  "r.which.day": "Daily",
  "r.which.total": "Total",
  "r.atr": "ATR(14) on {period}: {atr} ({pips} {unit}). {k} x ATR = {kpips} {unit}.",
  "r.atrNone": "ATR(14) on {period}: not available yet.",
  "units.pips": "pips", "units.pip": "pip", "units.points": "points", "units.point": "point", "units.units": "units",
  // review
  "v.symbol": "Symbol", "v.side": "Side", "v.order": "Order", "v.entry": "Entry", "v.stop": "Stop", "v.target": "Target",
  "v.size": "Size", "v.loss": "Loss at the stop",
  "v.buy": "Buy", "v.sell": "Sell", "v.market": "Market", "v.limit": "Limit", "v.stopOrder": "Stop",
  "v.entryMarket": "at the market (now {price})",
  "v.stopValue": "{stop} · {dist} {unit}{fromFill}",
  "v.fromFill": " from the fill",
  "v.none": "none",
  "v.lossValue": "{loss}{comm}",
  "v.lossComm": ", commission included",
  "v.place": "{side} {lots} lots {symbol}",
  "v.sending": "Sending...",
  "v.sent": "Sent. cTrader order {id}.",
  "v.again": "The numbers changed since you reviewed: your loss limits now leave {room}. Review again.",
  "v.notPaid": "This copy is not the Store's paid plugin, so it does not place orders.",
  "v.trial": "Ballast Free sizes the trade. Placing it from here, with your loss limits enforced, is in Ballast.",
  // cTrader's refusals, in words
  "x.NOT_ENOUGH_MONEY": "Not enough free margin for this size. Use a wider stop or a smaller risk.",
  "x.MARKET_CLOSED": "The market for this symbol is closed now.",
  "x.TRADING_DISABLED": "Trading this symbol is switched off on your account.",
  "x.INVALID_VOLUME": "cTrader did not accept this size for the symbol.",
  "x.TRADING_BAD_VOLUME": "cTrader did not accept this size for the symbol.",
  "x.TRADING_BAD_STOPS": "cTrader did not accept the stop or target: they may be too close to the price for this symbol.",
  "x.timeout": "No answer from cTrader. Check your positions and orders before trying again.",
  "x.busy": "An order is already being sent.",
  "x.other": "cTrader refused the order: {why}.",
  // limits
  "l.none": "No loss limits set. If a firm funds your account, enter its daily and total loss limits below: Ballast then makes every new trade small enough that hitting its stop keeps you inside them.",
  "l.today": "Today", "l.total": "In total",
  "l.used": "Lost so far: {loss} of {limit} ({pct}%)",
  "l.worst": "If every open stop is hit: {worst}",
  "l.from": "Counted from {what}: {ref}",
  "l.ref.sodBalance": "today's opening balance",
  "l.ref.higher": "the higher of today's opening balance and equity",
  "l.ref.floor": "your firm's lowest allowed equity, plus the limit",
  "l.ref.initial": "the starting balance",
  "l.ref.trailing": "the highest balance or equity seen",
  "l.err.needStart": "Enter the starting balance: a limit in % needs it. Orders are blocked until then.",
  "l.err.history": "The account's history did not load, so today's loss cannot be checked. Orders are blocked until it loads.",
  "l.err.needSodEquity": "Your rule counts from the higher of today's opening balance and equity, and Ballast did not see today's opening equity (it was not open when the day began). Enter today's opening equity, or today's lowest allowed equity, under \"Exact figures from your firm\". Orders are blocked until then.",
  "l.unc.devicePeak": "Not sure: Ballast only knows the highest equity this device has seen. For a trailing limit, enter your firm's current lowest allowed equity under \"Exact figures from your firm\".",
  "l.room": "A new trade may lose at most {room}: Ticket makes it smaller to fit.",
  "l.reached": "A limit is reached: Ballast will not place orders until it resets.",
  "l.full": "No room left for a new trade: your open trades' stops would use the rest of a limit.",
  "l.dayBegan": "The day began at {hour} {zone} time ({local} your time).",
  "l.openNoStop": "{n} open trade(s) without a stop (or without a price yet) are counted at today's price only.",
  "l.device": "Saved on this device only: set your limits again on each computer or phone you use.",
  "l.gap": "Hitting a stop is assumed to cost what it shows. In a fast market or over a gap the fill can be worse, and a limit can still be passed.",
  // exposure
  "x2.none": "No open positions.",
  "x2.noStop": "no stop: no limit",
  "x2.noPrice": "no price yet",
  "x2.risk": "{fromNow} more if the stop is hit",
  "x2.fromEntry": "{fromEntry} from entry · {pct}% of balance",
  "x2.line": "{lots} lots at {entry} · stop {stop}",
  "x2.total": "At risk at the stops: {total} ({pct}% of balance), from the current price",
  "x2.totalNoStop": "plus {n} position(s) with no stop: no limit on their loss",
  "x2.after": "If every stop is hit: balance about {bal}, before commission and slippage.",
  // journal
  "j.none": "Trades placed from Ballast appear here once they close, each in R: its result divided by the money it risked.",
  "j.trades": "Trades (35 days)", "j.won": "Won", "j.avg": "Average", "j.avgWL": "Average win / loss", "j.pf": "Profit factor",
  "j.net": "Net", "j.streak": "Longest losing run",
  "j.perTrade": "{r} R per trade",
  "j.small": "With fewer than 30 trades these numbers can change a lot.",
  "j.incomplete": "Part of the history did not load, so some trades may be missing.",
  // sessions
  "s.open": "Open", "s.closed": "Closed", "s.there": "{time} there", "s.closes": "closes in {span}", "s.opens": "opens in {span}",
  "s.weekend": "The forex market is shut for the weekend. It reopens on Sunday at 17:00 New York time.",
  "s.overlap": "London and New York are both open: usually the busiest hours.",
  "s.openNow": "Open now: {list}.",
  "s.between": "Between sessions.",
  "s.yourTime": "Your time: {time}",
  // the free edition
  "f.limits": "Loss limits are in Ballast (the full version): set your daily and total limits the way your firm counts them, and every trade placed from Ballast is made small enough to stay inside them; at a limit, Ballast stops placing orders.",
  "f.journal": "The journal is in Ballast (the full version): every trade placed from Ballast, in R, with win rate, average R, profit factor and results by symbol.",
  // header
  "h.demo": "Demo", "h.live": "Live", "h.connecting": "Connecting to cTrader...", "h.notConnected": "Not connected",
  "h.full": "Risk toolkit", "h.trial": "Free: sizes and checks; does not place orders",
};

const TABLES = { en: EN };
let table = EN;

/** Chooses the language (cTrader passes ?lang=); English when there is no table for it. */
export function setLanguage(lang) {
  const code = String(lang || "en").slice(0, 2).toLowerCase();
  table = TABLES[code] ? { ...EN, ...TABLES[code] } : EN;
  return TABLES[code] ? code : "en";
}

/** Adds a language table (another file can call this). */
export function addLanguage(code, strings) {
  TABLES[code] = strings;
}

export function t(key, vars = {}) {
  const s = table[key] ?? EN[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m));
}

/** Replaces the text of every element with data-t when the chosen table has its key. */
export function applyStatic(root = document) {
  if (table === EN) return;
  root.querySelectorAll("[data-t]").forEach((e) => {
    const k = e.dataset.t;
    if (table[k] != null) e.textContent = table[k];
  });
}
