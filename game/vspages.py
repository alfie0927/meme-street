"""Comparison pages (/vs and /vs/<slug>): Meme Street beside the practice-trading sites people search for, and the
Daily Chart beside Wordle (docs/REACH_PLAN.md, "Search"). Plain HTML through lessonpages' page shell.

Every statement about another site is in VS below, with where it came from in `src` (never printed). The page prints
the date (ASOF) and sends the reader to that site for the current details. Before changing a claim, check it on their
site and move ASOF. Nothing here says what another site lacks: only what it is. `python game/vspages.py` checks the pages."""
import html
import json

from lessonpages import CSS, CTA, FOOT, HEAD

ASOF = "November 2026"
OURS = {"trade": "180+ made-up companies, with indices and funds", "prices": "Made by the game's price model. Nobody's trade moves a price.",
        "hours": "All day, every day", "start": "1,000 MB (practice money, no cash value)"}
CANNOT = ("It has no real companies, no real prices and no real news, so it will not teach you anything about a particular "
          "share. A made-up market is also a model: real markets can behave in ways it does not. It is for learning how "
          "charts, orders and risk work.")


def _sim(short, name, site, what, start, pick, src, trade="Real US stocks", hours="While the real exchanges are open", prices="The real market's"):
    """A simulator that trades the real market: the rows every such page shares."""
    return {"short": short, "name": name, "site": site, "what": what, "pick": pick, "src": src,
            "title": f"{short} alternative, compared",
            "h1": f"Meme Street and {name}: which to practise on",
            "desc": f"Meme Street beside {name}: the real market in its hours, or a made-up one that never closes, "
                    f"with lessons and a two-minute daily game. As of {ASOF}.",
            "lead": f"{name[0].upper() + name[1:]} lets you practise on the real market with virtual cash. Meme Street is a different "
                    "kind of practice: a made-up market that runs around the clock, with lessons and a two-minute game each "
                    "day. This page sets the two side by side so you can pick the one that fits.",
            "rows": [["What you trade", trade, OURS["trade"]], ["Prices", prices, OURS["prices"]],
                     ["When prices move", hours, OURS["hours"]], ["Practice money to start", start, OURS["start"]]],
            "ours": "you want a market that is open whenever you have ten minutes, lessons that lead straight into practice, "
                    "and a short game to come back to each day"}


VS = {
    "investopedia-simulator": _sim(
        "Investopedia Simulator", "the Investopedia Simulator", "https://www.investopedia.com/simulator/",
        "The Investopedia Simulator is a practice account for the real stock market, run by the finance site Investopedia. "
        "You buy and sell real US-listed shares with virtual cash, and you can join games against other players or start "
        "one for your own group.",
        "$100,000 of virtual cash in the standard game", "you want to practise on the real companies you read about, at their real prices",
        "web search 2026-11-11: several 2026 reviews agree ($100,000 default game, games with others, real US shares); investopedia.com blocks our reader."),
    "marketwatch-virtual-stock-exchange": _sim(
        "MarketWatch Virtual Stock Exchange", "MarketWatch's Virtual Stock Exchange", "https://www.marketwatch.com/games",
        "MarketWatch's Virtual Stock Exchange is a stock market game from the news site MarketWatch. You join a public game "
        "or create your own, public or private, and trade real shares with a virtual portfolio. Whoever creates a game "
        "sets its starting cash and its rules.",
        "Set by whoever creates the game", "you want a private game on real shares for a class or a group of friends, with rules you set",
        "web search 2026-11-11: a current MarketWatch games FAQ (the host sets the starting budget, margin and short selling), the 2021 game page and VSE instructor guide."),
    "howthemarketworks": _sim(
        "HowTheMarketWorks", "HowTheMarketWorks", "https://www.howthemarketworks.com/",
        "HowTheMarketWorks is a stock market game from Stock-Trak, built around classrooms. Teachers create contests with "
        "their own dates, starting cash, commissions and trading rules, and students trade real US stocks and ETFs. The "
        "standard version is paid for by sponsors, and schools can get one without adverts.",
        "A $100,000 practice portfolio; class contests set their own", "you teach a class and want contests on real shares with rules you control",
        "web search 2026-11-11: howthemarketworks.com home, classroom and contest-help pages; Stock-Trak's promo sheet.",
        trade="Real US stocks and ETFs"),
    "wall-street-survivor": _sim(
        "Wall Street Survivor", "Wall Street Survivor", "https://www.wallstreetsurvivor.com/",
        "Wall Street Survivor pairs a stock market game with courses, articles and videos about investing. You start with "
        "$100,000 of virtual money, buy shares in real companies, and can join leagues and contests against other players.",
        "$100,000 of virtual money", "you want courses about investing in real companies next to a game that trades them",
        "web search 2026-11-11, checked against wallstreetsurvivor.com's own home, courses and stock-market-game pages ($100,000, courses, contests and private leagues)."),
    "tradingview-paper-trading": _sim(
        "TradingView paper trading", "TradingView paper trading", "https://www.tradingview.com/support/solutions/43000516466-paper-trading-main-functionality/",
        "Paper trading is a practice account inside TradingView, the charting platform. You place practice orders straight "
        "from its charts of real markets, with its charting tools around you. The account starts at $100,000 and can be "
        "reset at any time.",
        "$100,000 by default, and you can reset it", "you already chart on TradingView, or you want to practise on real markets inside a full charting platform",
        "web search 2026-11-11: TradingView's help page 'Paper Trading: main functionality'.",
        trade="Whatever real market is on your chart", hours="While that market is open"),
}
VS["wordle"] = {
    "short": "Wordle", "name": "Wordle", "site": "https://www.nytimes.com/games/wordle/index.html",
    "title": "Games like Wordle: a daily chart game in two minutes",
    "h1": "A game like Wordle, for charts",
    "desc": "The Daily Chart is a daily game like Wordle for people who like charts: one made-up stock chart a day, the "
            "same for everyone, two minutes to trade it, and a grid of squares to share.",
    "lead": "If you like one small game a day that everyone else is playing too, the Daily Chart is that with a price "
            "chart instead of a word. One chart a day, two minutes on the clock, and a result to share.",
    "what": "Wordle is The New York Times' daily word game. Everyone gets the same five-letter word, six guesses to find "
            "it, and a grid of coloured squares to share when they are done. One puzzle a day, and then you wait for tomorrow's.",
    "rows": [["What you do", "Guess a five-letter word", "Trade one made-up stock chart with 1,000 MB of practice money"],
             ["How often", "One puzzle a day, the same for everyone", "One chart a day, the same for everyone. The next starts at midnight UTC."],
             ["How long", "Six guesses", "Two minutes: a new candle prints every second"],
             ["What you share", "A grid of coloured squares", "A grid of eight squares and your return"],
             ["What you keep", "A streak and your statistics", "A streak, your statistics and a place on the day's board"]],
    "col": "the Daily Chart", "differs": "What the Daily Chart adds",
    "diff": ['<b>No account needed to play.</b> Open <a href="/daily">the Daily Chart</a> and press Play. A free account puts your result on the board and keeps your streak.',
             "<b>The chart cannot be looked up.</b> The stock is made up, and the candles still to come do not reach your browser until their second arrives.",
             "<b>You can go short.</b> If you think the price will fall, sell first and buy back later.",
             "<b>A lesson for each chart.</b> After the game, a link goes to the lesson that fits what the chart did.",
             "<b>It is practice money.</b> MB have no cash value and are never paid out."],
    "cannot": "It is not a puzzle with one right answer. A price chart is noisy, so a good decision can lose and a bad one "
              "can win on any single day. The number that means something is your average over many days.",
    "pick": "you want a calm word puzzle", "ours": "you like the one-a-day habit and want it with a price chart and a clock",
    "src": "common knowledge: nytimes.com/games/wordle.",
}


def paths():
    return ["/vs"] + [f"/vs/{s}" for s in VS]


def _diff(n_lessons, n_tracks):
    return ["<b>The market is made up.</b> 180+ fictional companies, indices and funds, with news that moves their prices. No real tickers, so nothing here can be read as a tip about a real share.",
            "<b>It never closes.</b> Prices move all day, every day, and a game day lasts 30 real minutes, so a week here holds far more opens, closes and earnings reports than a week of a real market.",
            '<b>A two-minute game each day.</b> The <a href="/daily">Daily Chart</a> gives everyone the same chart, two minutes to trade it, and a board to compare returns.',
            f'<b>Lessons tied to the market.</b> {n_lessons} short <a href="/lessons">lessons</a> in {n_tracks} tracks, each one practised on the live market.',
            "<b>1,000 MB to start.</b> MB are practice money: no cash value, never paid out.",
            "<b>What is sold.</b> Opening an account is free. The shop sells extra MB and two memberships: Pro, with leverage and more chart indicators, and Expert, with scripted bots and backtests."]


def _shell(site, path, title, desc, crumb, body):
    url, e = site + path, html.escape
    ld = [{"@context": "https://schema.org", "@type": "WebPage", "name": title, "description": desc, "url": url,
           "publisher": {"@type": "Organization", "name": "Meme Street", "url": site + "/"}},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "name": n, "item": site + p} for i, (n, p) in enumerate(crumb)]}]
    return HEAD.format(t=e(title + " | Meme Street"), d=e(desc), url=url, ld=json.dumps(ld).replace("</", "<\\/"), css=CSS) + body + FOOT


def page(site, slug, n_lessons, n_tracks):
    """One comparison page, or None if there is no such page."""
    v, e = VS.get(slug), lambda s: html.escape(s, quote=False)
    if v is None:
        return None
    us = v.get("col", "Meme Street")
    rows = "".join(f"<tr><th>{e(a)}</th><td>{e(b)}</td><td>{e(c)}</td></tr>" for a, b, c in v["rows"])
    others = "".join(f'<li><a href="/vs/{s}">{e(o["h1"])}</a></li>' for s, o in VS.items() if s != slug)
    body = (f'<p class="crumb"><a href="/vs">Compare</a> › {e(v["short"])}</p><h1>{e(v["h1"])}</h1><p class="lead">{e(v["lead"])}</p>'
            f'<h2>What {e(v["name"])} is</h2><p>{e(v["what"])}</p>'
            f'<h2>Side by side</h2><div class="tbl"><table><tr><th></th><th>{e(v["short"])}</th><th>{us[0].upper() + us[1:]}</th></tr>{rows}</table></div>'
            f'<h2>{v.get("differs", "What Meme Street does differently")}</h2><ul>'
            + "".join(f"<li>{d}</li>" for d in v.get("diff") or _diff(n_lessons, n_tracks))
            + f'</ul><h2>What it cannot do</h2><p>{v.get("cannot", CANNOT)}</p>'
            f'<h2>Which to pick</h2><ul><li>Pick {e(v["name"])} if {e(v["pick"])}.</li><li>Pick {us} if {e(v["ours"])}.</li>'
            "<li>They do different jobs, and nothing stops you using both.</li></ul>"
            f'<p><small>What this page says about {e(v["name"])} is as of {ASOF} and may have changed since: '
            f'<a href="{html.escape(v["site"])}" rel="nofollow noopener">their own site</a> has the current details. {e(v["short"])} '
            "belongs to its owner, and Meme Street has no connection with it.</small></p>"
            + CTA + f'<h2>More comparisons</h2><ul class="toc">{others}</ul>')
    return _shell(site, f"/vs/{slug}", v["title"], v["desc"], [("Compare", "/vs"), (v["short"], f"/vs/{slug}")], body)


HUB_DESC = ("How Meme Street, a made-up stock market that never closes, compares with the simulators that trade the real "
            "market, and how its Daily Chart compares with Wordle.")


def hub(site):
    items = "".join(f'<li><a href="/vs/{s}">{html.escape(v["h1"], quote=False)}</a></li>' for s, v in VS.items())
    return _shell(site, "/vs", "How Meme Street compares with other trading simulators", HUB_DESC, [("Compare", "/vs")],
                  f'<p class="crumb">Compare</p><h1>How Meme Street compares</h1><p class="lead">{HUB_DESC} Each page says what '
                  f'the other site is, sets the two side by side, and says when the other one is the better pick.</p><ul class="toc">{items}</ul>' + CTA)


if __name__ == "__main__":
    S = "https://memestreet.net"
    assert hub(S).count("/vs/") >= len(VS) and page(S, "nope", 1, 1) is None
    for slug, v in VS.items():
        s = page(S, slug, 96, 17)
        assert s.count("<h1>") == 1 and f'rel="canonical" href="{S}/vs/{slug}"' in s and ASOF in s and v["site"] in s, slug
        assert len(v["title"] + " | Meme Street") <= 70 and len(v["desc"]) <= 185 and "free to play" not in s.lower(), (slug, len(v["title"]), len(v["desc"]))
        assert v["src"] not in s and s.count("<tr>") == len(v["rows"]) + 1, slug
    print("ok", len(VS), "comparison pages")
