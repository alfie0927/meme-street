# SEO backlog

Ordered by expected signups per hour of work. Each item: query → page → change.

1. **Get indexed at all.** memestreet.net returns nothing in web search (2026-11-07). Owner: add the site to Google
   Search Console and Bing Webmaster Tools, submit `/sitemap.xml`. Unlocks positions, impressions and indexing checks.
2. ~~"position size calculator"~~ done 2026-11-08: `/tools/position-size-calculator`.
3. ~~Daily Chart server content~~ done 2026-11-07 (noscript how-to-play text and h1 on /daily).
4. **Numbered steps render as one paragraph** on lesson pages (and in-game): `1.` lines in `content/learn-*.md` are not a
   list in `learning.parse_learn`. Fix in the parser so both get an `<ol>` (needs the Learn page's renderer to follow).
5. **"investopedia simulator alternative"** (blocked 2026-11-10: investopedia.com cannot be fetched from the sandbox and web search returned only low-quality blogs, so competitor facts could not be sourced; needs the owner to paste the current facts and dates, or a run with fetch access) → `/vs/investopedia-simulator`. Fair comparison; sources and "as of" dates.
6. **"wall street survivor alternative"** → `/vs/wall-street-survivor`.
   Built 2026-11-11 by the reach plan (not this routine), not yet committed or live: `game/vspages.py` serves `/vs` and six pages (`/vs/investopedia-simulator`, `/vs/marketwatch-virtual-stock-exchange`, `/vs/howthemarketworks`, `/vs/wall-street-survivor`, `/vs/tradingview-paper-trading`, `/vs/wordle`). Do not rebuild them here. Every claim about another site sits in `VS` with its origin in `src`; the Investopedia and Wall Street Survivor facts come from third-party write-ups only, so the owner checks each page against the other site before it goes live. `game/vspages.py` is not on the seo-ship list: a change to it needs the owner.
7. ~~**Home page has no content without JS.** `/` is the SPA shell; `#guest-hero` text is in the HTML but thin. Add a
   short server-side intro and links to `/lessons`, `/daily`, `/about`.~~ done 2026-11-09.
8. **`/stock/{ticker}` pages** are SPA shells, not in the sitemap. Server-render a company page (name, sector, story,
   price chart image) for 180+ companies, only if they can carry real text (fictional companies get no search volume
   by name, so low priority).
9. **og:image per lesson**: a chart picture would lift click-through from social.
10. **Glossary as its own page per term** (`/lessons/glossary` holds every term): later, if glossary queries show impressions.
11. ~~**Home page `/` has the bare title "Meme Street", no canonical, and a description that does not say "play money / learn".**
    Serve it through `page_as("/", ...)` in `game/pages.py` (title like "Meme Street: a free stock market game with play money"). Needs a check that tests/test_guest.py and the home tests still pass. Next daily run.~~ done 2026-11-09.
12. **More tools near the calculator:** ~~risk/reward ratio calculator~~ done 2026-11-10 (`/tools/risk-reward-calculator`); ~~stop-loss calculator~~ done 2026-11-11 (`/tools/stop-loss-calculator`); next: a compound-interest or drawdown-recovery calculator only if it fits the lessons (check `content/learn-*.md` for a sourced formula first).
13. **`/about` is out of date on the course size**: it says "96 free lessons in 17 tracks"; `learning.load_content()` now gives 114 lessons in 20 tracks (the `/lessons` hub counts them live). Change the line in `web/about.html` or drop the numbers. Found 2026-11-11.
