// The parts of cTrader's Plugin API v2 SDK that Ballast uses, bundled into one file (the panel may load
// files only from its own address). Rebuild with tradertools/ballast/vendor-build.sh.
export { createClientAdapter } from "@spotware-web-team/sdk-external-api";
export {
  accountInfo, asset, availablePeriods, cancelOrder, closePosition, dealHistory, handshake, newOrder, pendingOrders,
  positions, sdkVersion, subscribeExecutions, subscribeQuotes, symbolById, symbolByName, symbols, trendbars,
} from "@spotware-web-team/sdk";
export { firstValueFrom } from "rxjs";
