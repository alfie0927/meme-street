# SEO log

- 2026-11-07 · Setup. 96 lessons now server-rendered: https://memestreet.net/lessons and /lessons/{id} (title, description, canonical, LearningResource + Breadcrumb JSON-LD, links to the live game). PR pending.
- 2026-11-07 · Sitemap: duplicate /daily removed, noindex /terms and /privacy removed, SPA shells /learn and /leaders removed, 97 lesson URLs added (101 URLs). PR pending.
- 2026-11-07 · /learn and /leaders get their own title, description and canonical. PR pending.
- 2026-11-07 · /about: "In closed testing" removed (the site is live and sells), 1,000 MB start stated, retitled for "free stock market game / practise trading with play money", canonical added, links to /lessons and /daily. /bots/guide canonical. Links to /lessons from /about, /bots/guide and the game's footer. PR pending.
- 2026-11-07 · /daily: the how-to-play text, an h1 and links to /lessons and /about are now in the server HTML (noscript block, DAILY_BODY in game/pages.py): https://memestreet.net/daily. Test added. Live health check not possible (sandbox proxy blocks memestreet.net), checked locally.
- 2026-11-07 · /about no longer says "Free to play" (tests/test_guest.py forbids it: the site sells MB) and the lesson pages' header button says "Sign up", not "Play free".
