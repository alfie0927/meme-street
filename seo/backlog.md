# SEO backlog

Ordered by expected signups per hour of work. Each item: query → page → change.

1. **Get indexed at all.** memestreet.net returns nothing in web search (2026-11-07). Owner: add the site to Google
   Search Console and Bing Webmaster Tools, submit `/sitemap.xml`. Unlocks positions, impressions and indexing checks.
2. **"position size calculator"** → new `/tools/position-size-calculator`. A free tool (Monthly step 4); the game
   already has the sum in its risk tool, so the page can reuse the formula and link to `/lessons/position-sizing`.
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
