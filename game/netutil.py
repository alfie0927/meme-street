"""Small network helpers shared by the game server and the gateway (neither may import the other: importing the server
builds a game)."""

LOOPBACK = {"127.0.0.1", "::1", "localhost"}
TICKER_RENAMES = {"BULL2": "2LMSI", "BEAR2": "2SMSI"}   # old product tickers and what they are called now


def caller_address(peer, headers, trust_proxy=False):
    """The caller's address. A forwarding header (anyone can send one) is believed in two cases: `trust_proxy` is on
    (a proxy on another machine), or the request came from this very computer, which is where a tunnel such as
    Cloudflare's runs when the game is shared from your own PC. Without this every visitor through a tunnel would
    look like one address, and the sign-up and login limits would apply to all of them together.

    `headers` is anything with a lower-case-key `.get`."""
    if trust_proxy or peer in LOOPBACK:
        fwd = headers.get("cf-connecting-ip", "") or headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()[:64]
    return peer or "unknown"
