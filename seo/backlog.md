# SEO backlog

Ordered by expected signups per hour of work. Each item: query → page → change.

1. **Get indexed at all.** memestreet.net returns nothing in web search (2026-11-07). Owner: add the site to Google
   Search Console and Bing Webmaster Tools, submit `/sitemap.xml`. Unlocks positions, impressions and indexing checks.
2. ~~"position size calculator"~~ done 2026-11-08: `/tools/position-size-calculator`.
3. ~~Daily Chart server content~~ done 2026-11-07 (noscript how-to-play text and h1 on /daily).
4. **Numbered steps render as one paragraph** on lesson pages (and in-game): `1.` lines in `content/learn-*.md` are not a
   list in `learning.parse_learn`. Fix in the parser so both get an `<ol>` (needs the Learn page's renderer to follow).
5. **"investopedia simulator alternative"** → `/vs/investopedia-simulator`. Fair comparison; sources and "as of" dates.
6. **"wall street survivor alternative"** → `/vs/wall-street-survivor`.
7. **Home page has no content without JS.** `/` is the SPA shell; `#guest-hero` text is in the HTML but thin. Add a
   short server-side intro and links to `/lessons`, `/daily`, `/about`.
8. **`/stock/{ticker}` pages** are SPA shells, not in the sitemap. Server-render a company page (name, sector, story,
   price chart image) for 180+ companies, only if they can carry real text (fictional companies get no search volume
   by name, so low priority).
9. **og:image per lesson**: a chart picture would lift click-through from social.
10. **Glossary as its own page per term** (`/lessons/glossary` holds every term): later, if glossary queries show impressions.
11. **Home page `/` has the bare title "Meme Street", no canonical, and a description that does not say "play money / learn".**
    Serve it through `page_as("/", ...)` in `game/pages.py` (title like "Meme Street: a free stock market game with play money"). Needs a check that tests/test_guest.py and the home tests still pass. Next daily run.
12. **More tools near the calculator:** risk/reward ratio calculator, "R multiple" explainer, stop-loss calculator (same page pattern in `lessonpages.py`).
