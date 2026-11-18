# Ballast: the owner's manual

Ballast is a risk toolkit for traders, sold in the cTrader Store as one subscription. It runs inside cTrader (Web,
Windows, Mac and the phone apps) as a "web plugin": a static web page that cTrader opens in a frame and talks to
through its Plugin API v2. It has five tools: **Ticket** (position size from risk and stop, commission included,
review then place), **Limits** (daily and total loss limits the way funded-account firms count them), **Exposure**
(risk at the stops of open positions), **Journal** (trades in R) and **Sessions** (the market's clock). It gives no
signals and no advice.

- For buyers: [USER_GUIDE.md](USER_GUIDE.md). For the Store form: [LISTING.md](LISTING.md).
- How it fits the business: `docs/ROADMAP.md` section 3. How the code works: `docs/HOW_IT_WORKS.md` section 18.

## Files

| Path | What |
|---|---|
| `site/` | Everything that is published (one static folder, no build step) |
| `site/index.html`, `site/trial/index.html` | The paid edition and the free one (the same page with `data-edition="trial"`: no Place button) |
| `site/js/app.js` | The panel: the five tabs, settings per account, review and place |
| `site/js/risk.js` | Sizing maths (pure): rounding down, conversion into the account's money at the stop, commission, the conversion fee, ATR, number parsing |
| `site/js/limits.js` | Loss limits (pure): daily and total loss on equity, the day in a firm's time zone |
| `site/js/journal.js` | Trades from labels, in R; statistics; CSV |
| `site/js/sessions.js` | The sessions clock |
| `site/js/history.js` | Reads closed deals in full, or says it could not |
| `site/js/ticket.js` | Builds the order or says why not; `createPlacer`, the only way an order is sent |
| `site/js/host.js` | The only file that talks to cTrader |
| `site/js/host-mock.js` | The same functions over a stand-in demo account (`?mock=1`) |
| `site/vendor/` | cTrader's SDK (`@spotware-web-team/sdk` 2.1.5, `sdk-external-api` 2.0.1, with zod, uuid, rxjs) bundled into one file, and its licences (MIT, ISC, Apache-2.0). Rebuild with `vendor-build.sh` |
| `site/brand/` | The mark (a boat with its ballast keel), the wordmark, the page that renders the store image |
| `site/_headers` | The security policy on Cloudflare Pages: no network connections at all, so Ballast cannot send data anywhere |
| `site/probe.html`, `site/js/probe.js` | The one-off platform check on a demo account. **Delete before the listing goes live** |
| `listing/` | The 300 x 300 store image and four 840-px screenshots |
| `test/` | `node --test`: 61 tests with worked examples |
| `../../tests/test_tradertools.py` | The panel in a real browser (5 tests) |

## Run it on this computer

```
cd tradertools/ballast/site
python -m http.server 8765
```

Open `http://127.0.0.1:8765/index.html?mock=1&symbol=EURUSD`. The stand-in is a 10,000 USD demo account with two
open positions (one without a stop) and three closed trades; symbols `EURUSD`, `GBPUSD`, `USDJPY`, `EURJPY`,
`XAUUSD`, `US500`, `BTCUSD`; add `&theme=light` for the light theme; the trial is `/trial/index.html?mock=1`.

## Test it

```
cd tradertools/ballast && node --test test/*.test.js     # the maths, under a second
cd tests && python -m unittest test_tradertools           # the panel in Edge or Chrome, about 40 s
```

CI runs both (the `tradertools` job, and `test_tradertools` inside the test parts).

## Stage 0: the probe (you, about 30 minutes, on a demo account)

The SDK's own help pages describe an older API; the code follows the package. These are not yet seen on a real
account: the unit of `volume`, whether every cTrader app speaks Plugin API v2, whether a closed deal keeps its
order's label, storage, chart bars, and the plugin `id`.

1. Host the site (below) and note its address, for example `https://ballast-toolkit.pages.dev`.
2. In cTrader Web on a **demo** account: Algo, Plugins, Create. Name "Ballast probe", the image
   `listing/store-image-300.png`, placement "Block in Active Symbol Panel" (L) and, for mobile, "Bottom sheet from
   the symbol Overview tab" (80%). URL `https://<your address>/probe.html`. Tick the confirmations, Publish. It stays
   private to your account.
3. Open it on EURUSD. If "Connect FAILED" shows, stop and send me the text.
4. Click the order tests in order: 1 (market order, smallest size, stop and target 50 pips), 2 (close it), 3 (a limit
   order 10% below the price), 4 (cancel it); wait 10 seconds; 5 (read the closed deals). They stay off on a live
   account.
5. Reload the panel once; hide it for 20 seconds and show it again.
6. Do 3 and 4 again in the phone app.
7. Copy the "Results to send back" box (from both) and paste it to me.

What it decides (I read the results and make the changes):
- `UNITS_PER_VOLUME` in `host.js`, from `position.volume` against `quantity` and `lotSize`. Then `VOLUME_CHECKED`
  becomes `true`. **Until it is, the panel sizes trades but has no Place button** ("switched off until the volume
  unit is confirmed"): a wrong unit would multiply every order, so it stays off rather than guessed.
- Whether a position's `commission` is one side or both, and whether the opening commission leaves the balance at the
  open (compare the balance before and after test 1). Ballast counts one more side at the close either way (the
  careful side); if the opening side leaves the balance at the open, today's opening balance must add it back.
- Whether the journal's R works (the label on the closing deal) and whether the ATR stop works (chart bars).
- If orders fail on both Web and the phone, the fallback is a desktop-only plugin in C#.

## Hosting (you, once, about 20 minutes, free)

Cloudflare Pages, free plan. Nothing on the game's server changes.
1. A Cloudflare account. Workers & Pages, Create, Pages.
2. Either "Upload assets" and drag in the `site` folder (simplest), or connect the GitHub repository with root
   directory `tradertools/ballast/site`, no build command, and production branch `tradertools-live` (only your merge
   moves it).
3. Name the project (for example `ballast-toolkit`). The address is `https://<name>.pages.dev`. The `_headers` file
   applies by itself.

## Build the plugins in cTrader (you, after the probe)

Two plugins, both in cTrader Web: Algo, Plugins, Create.
- **Ballast** (paid): URL `https://<address>/index.html`. Placements: Block in Active Symbol Panel (L), Tab in Trade
  Watch, Separate window; mobile: Bottom sheet from the symbol Overview tab (80%), Bottom sheet from the Trade app
  tabs (80%). Image: `listing/store-image-300.png`.
- **Ballast Free**: the same, URL `https://<address>/trial/`.

Note each plugin's id (cTrader passes it to the page as `?id=`). Put the paid one into `PAID_IDS` in
`site/js/app.js`, so only that plugin's page places orders, and re-upload the site.

## Publish in the Store (you)

1. Become a seller: cTrader Store, "Join as a seller"; identity check (photo ID, selfie, proof of address); a Visa or
   Mastercard in your name for payouts (weekly, minimum $50, from funds at least 14 days old; the Store keeps 30%).
2. Publish the paid plugin with the text and images in `LISTING.md`, the subscription prices there, and attach Ballast
   Free as its trial.
3. Review takes 1 to 3 working days; a rejection comes with reasons and 30 days to fix.

## Release a new version

1. `node --test`, `test_tradertools`, then the demo checklist below, on Web and the phone.
2. Bump `VERSION` in `site/js/app.js`; upload the `site` folder again. Every buyer gets it at their next open.
3. Only a change of address or placements needs a new plugin build and a new Store version.

**The demo checklist (15 minutes):** the balance matches cTrader; one size matches a sum by hand (with commission);
a JPY pair, gold and an index each size; "too close" and "smallest size" messages appear; a market order arrives once
with its stop and target; a double tap gives one position; a limit order is placed and cancelled; a closed trade
appears in the journal in R and moves the daily limit; a reached limit blocks Place; settings survive a reload; the
same on the phone.

## The rules this product keeps

- No signals, no advice, no profit claims (UK FCA PERG 8.30: software that tells someone to buy or sell can be
  investment advice; a calculator, an order ticket and a journal are not).
- An order goes out only from a real click on the review (`isTrusted`), once (`createPlacer`), never retried, never on
  load, a timer or the address; the limits are checked again at the click.
- Sizes round down; rates are taken on the side that makes the loss larger, at the stop as well as now; commission and
  the conversion fee are in; a size that would lose more than chosen is refused.
- With limits set, orders are blocked (fail closed) whenever the figures cannot be trusted: the history, the open
  positions or the pending orders did not load; the balance is over 90 seconds old; an open trade cannot be valued; a
  pending order has no stop; a % limit has no starting balance; a trailing limit has no floor from the firm; the
  "higher of" rule has no opening equity while something was open as the day began. Pending orders count at their
  stops, and an order just sent is held against the room until the account shows it.
- A price that has not updated for two minutes is not used.
- It sends no data anywhere and keeps settings on the device, per account.
