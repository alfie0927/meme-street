# Exact Risk Ticket (working name)

A panel inside cTrader that sizes a trade from the risk the trader chooses and the stop distance, converts that risk
into the account's currency for any symbol, and places the order with its stop and target attached, after a review
step. It also shows the day's realised loss against the trader's own limits and keeps a log of its trades in R. It
gives no signals and no advice. It is sold in the cTrader Store (the plan: `docs/ROADMAP.md`, section 3).

It is a static web page: cTrader opens it in a frame and talks to it through its Plugin API v2. Nothing in the game
(`game/`, `web/`) uses it, and it uses nothing of the game.

## Files

| Path | What |
|---|---|
| `site/js/risk.js` | The maths, pure: sizing (always rounded down), the conversion into the account's currency, R, the loss light |
| `site/js/ticket.js` | From the inputs to one order request or a plain reason why not; `createPlacer`, the only way an order is sent |
| `site/js/host.js` | The only file that talks to cTrader (the vendored SDK) |
| `site/js/host-mock.js` | The same functions over fixed data, for `?mock=1` and the browser test |
| `site/js/app.js`, `site/index.html`, `site/trial/index.html`, `site/app.css` | The panel; the trial is the same page with `data-edition="trial"` |
| `site/probe.html`, `site/js/probe.js` | Stage 0 only: what cTrader really gives a web plugin. **Delete before the Store listing.** |
| `site/vendor/ctrader-sdk.js`, `site/vendor/LICENSES.txt` | cTrader's SDK (`@spotware-web-team/sdk` 2.1.5, `sdk-external-api` 2.0.1) with zod, uuid and rxjs, bundled into one file: a plugin may load files only from its own address. MIT, ISC and Apache-2.0 |
| `vendor-build.sh`, `vendor-entry.mjs` | Rebuild the bundle (pinned versions) |
| `site/_headers` | The page's security policy on Cloudflare Pages: scripts and styles from this site only, **no network connections at all** (`connect-src 'none'`), so it cannot send data anywhere |
| `test/*.test.js` | `node --test`: worked examples for every kind of symbol, the boundary, the blocks, one order per click |
| `../../tests/test_tradertools.py` | The page in a real browser against the stand-in |

## Testing

```
cd tradertools/ctrader-risk && node --test test/*.test.js        # the maths (21 tests, under a second)
cd tests && python -m unittest test_tradertools                   # the page in Edge or Chrome (about 8 s)
```

By hand: `python -m http.server 8765` in `site/`, then open `http://127.0.0.1:8765/index.html?mock=1&symbol=EURUSD`
(also `GBPUSD`, `USDJPY`, `EURJPY`, `XAUUSD`, `US500`, `BTCUSD`; `?theme=light`). The stand-in is a 10,000 USD demo
account; `window.__mock` holds the orders "sent".

## What the SDK gives (read from the package, 18 November 2026)

The help pages describe an older v0.0.x API (`createNewOrder`, volume "in cents", balance in integers with
`moneyDigits`). The package on npm is v2 and different: `handshake`, `accountInfo` (with `depositCurrency`, `equity`
and `environmentType` demo or live), `symbolByName` (`lotSize`, `minVolume`, `volumeStep`, `digits`, `pipPosition`,
`baseAssetId`, `quoteAssetId`), `symbols`, `asset`, `subscribeQuotes` (`bid`, `ask`), `newOrder` (`orderType`
market/limit/stop..., `side` buy/sell, `volume`, `stopLossPips`, `takeProfitPips`, `stopLoss`, `takeProfit`,
`entryPrice`, `label`), `positions`, `pendingOrders`, `closePosition`, `cancelOrder`, `dealHistory` (`netProfit`,
`label`, `closingTime`) and `subscribeExecutions`. v2 also has `breakEven` and trailing on orders and a positions
list, which v0 lacked: break-even and trailing rules are possible later.

**Not known until the probe:** the unit of `volume` (units of the base asset, or hundredths: `UNITS_PER_VOLUME` in
`host.js`), whether the host on Web, desktop and phone speaks v2 at all, whether a closed deal keeps the order's
label (the log's R needs it), whether `localStorage` survives, whether a hidden panel keeps receiving prices, and the
value of `id` that cTrader passes.

## Stage 0: the probe (owner, about 30 minutes, on a demo account)

1. Host the site (below) and note its address, for example `https://exact-risk-ticket.pages.dev`.
2. In cTrader Web (a **demo** account): Algo, Plugins, Create. Name "ERT probe", any 300x300 image, placement
   "Block in Active Symbol Panel" (size L) and on mobile "Bottom sheet from the symbol Overview tab" (80%). URL:
   `https://<your address>/probe.html`. Tick the confirmations and Publish. It stays private to your account.
3. Open it on EURUSD. The list fills in. If "Connect FAILED" shows, stop and send me the text.
4. Click the order tests in order: 1 (a market order at the smallest size with a stop and target 50 pips away), 2
   (close it), 3 (a limit order 10% below the price, which will not fill), 4 (cancel it), then wait 10 seconds and 5
   (read the closed deals). The buttons stay off on a live account.
5. Reload the panel once (for the storage check). Hide the panel for 20 seconds, show it again.
6. Do 3 and 4 again on the phone app (the same plugin appears under the symbol's Overview).
7. Copy the "Results to send back" box (from both) and paste it to me.

**What decides what:** if the connect fails or orders are refused on both, the fallback is a desktop-only plugin in
C#. If the deal does not keep the label, the log shows money only. `position.volume` against `quantity` and
`lotSize` settles the volume unit.

## Hosting (owner, once, about 20 minutes)

Cloudflare Pages, free plan; no change to the game's server.
1. A Cloudflare account; Workers & Pages, Create, Pages, "Upload assets" (simplest: drag the `site` folder in), or
   connect the GitHub repository with root directory `tradertools/ctrader-risk/site`, no build command, production
   branch `tradertools-live` (only your merge moves it).
2. The project's address is `<name>.pages.dev`. The `_headers` file applies by itself.
3. Each release: drag the folder in again (or merge to `tradertools-live`). A version number shows in the panel's footer.

## Releasing (each version)

1. `node --test`, `test_tradertools`, then the 15-minute demo checklist below, on Web and the phone.
2. Bump `VERSION` in `site/js/app.js`. Upload. Existing buyers get it at their next open.
3. Only a change of address or placement needs a new plugin build in cTrader and a new Store version.

**The demo checklist:** the balance matches cTrader; one size matches a sum done by hand; a JPY pair, gold and an
index each size and show their conversion; the "too small" and "wrong side" messages appear; a market order arrives
once with its stop and target as shown; a double tap gives one position; a limit order is placed and cancelled; a
closed trade appears in the log and moves the light; red locks Place; settings survive a reload; the same on the phone.

## Before the listing (stage 1)

- Delete `site/probe.html` and `site/js/probe.js`.
- Put the paid plugin's id into `PAID_IDS` in `site/js/app.js` (cTrader passes it as `?id=`), so only the paid
  plugin's page places orders. The trial plugin's URL is `.../trial/`.
- Store listing: the price ($19 launch, $29 after), screenshots (3, at least 800 px wide), a 300x300 image, and the
  copy in `docs/ROADMAP.md` section 3. No links to other sites in the listing.

## Rules this product keeps

- No signals, no advice, no profit claims (UK FCA PERG 8.30: software that tells a user to buy or sell can count as
  investment advice; a calculator and an order ticket do not).
- An order goes out only from a real click on the review screen (`isTrusted`), once (`createPlacer`), never retried,
  never on load, on a timer or from the address.
- The size is always rounded down, conversions are taken on the side that makes the risk larger, and a size that
  would risk more than chosen is refused, never rounded up.
- It sends no data anywhere (the security policy enforces it) and keeps its settings in the browser only.
