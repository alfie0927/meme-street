// The parts of cTrader's Plugin API v2 SDK that Exact Risk Ticket uses, bundled into one file (the panel may load
// files only from its own address). Rebuild with tradertools/ctrader-risk/vendor-build.sh.
export { createClientAdapter } from "@spotware-web-team/sdk-external-api";
export {
  accountInfo, asset, cancelOrder, closePosition, dealHistory, handshake, newOrder, pendingOrders, positions,
  sdkVersion, subscribeExecutions, subscribeQuotes, symbolById, symbolByName, symbols,
} from "@spotware-web-team/sdk";
export { firstValueFrom } from "rxjs";
