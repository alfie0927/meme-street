# Short-form finance hooks: what breaks out on YouTube Shorts

Built 2026-11-07 for the @memestreetgame Reels lab. Public YouTube Shorts metadata and English auto-captions only (yt-dlp
`--flat-playlist` and `--skip-download --write-auto-subs`); no video or audio downloaded. Raw data stayed in the session
scratchpad; the 60 hand-coded openers are in hook_shapes.tsv next to this file.

## How far to trust this
- 419 Shorts from 12 channels (latest 40 each); 60 caption files; the spoken comparison is the top 3 per channel (29,
  all 2x the channel median or more) against the bottom 2 (19, all 0.5x or less).
- Outlier multiple = views / the channel's own median Short. YouTube rounds counts, so multiples are good to a few %.
- Title patterns: low to moderate confidence. Mechanical first-3-second features: nothing reliable either way. Opener
  shapes: large and consistent across two coders and across channels, but the categories were designed after reading
  these openers, so treat them as a strong hypothesis to test on our own reels, not proof.
- 9 of 12 channels have a median Short under 2.5k views; only BallGame Trivia (55k) and GothamChess (1.65M) show
  outliers at scale. YouTube, not Instagram; no faceless neon-chart channel with traction, so nothing here tests our look.

## Channels
| channel | subs | kind | median views |
|---|---|---|---|
| @BlackGirlStocks | 199k | trading education with chart quizzes | 2.3k |
| @StickTraderMind | 20.1k | stick-figure trading psychology | 1.2k |
| @CoinEngineer | 127k | faceless animated explainers, AI-style voice | 245 |
| @stockmarketcartoons | 29 | silent market cartoons | 424 |
| @AnimatedFinance | 796 | animated economics lessons | 617 |
| @TheTradingGeek | 1.87M | trading education (format only) | 9.6k |
| @marktrader.academy | 29.3k | "Buy or Sell?" chart quizzes and lessons | 2.0k |
| @ClayTrader | 639k | live-trade clips | 1.1k |
| @verifiedinvestingshorts | 26.7k | Shorts-first lessons | 469 |
| @TraderTVLive | 594k | trading-floor stories | 1.45k |
| @ballgametriv | 95.1k | sports quiz and game Shorts | 55k |
| @GothamChess | 8.48M | chess clips (format only) | 1.65M |

## The finding that matters: opener shapes (hand-coded, then re-coded blind; agreement 82%, kappa 0.80)
| shape | top (me) | bottom (me) | top (blind) | bottom (blind) |
|---|---|---|---|---|
| viewer question read aloud | 2 | 0 | 2 | 0 |
| confession (first person, a consequence) | 2 | 0 | 3 | 0 |
| curiosity gap / withheld point | 4 | 0 | 5 | 0 |
| concrete surprise (named person + number, contrast, odd scene) | 5 | 0 | 3 | 1 |
| direct teaching statement or demo | 7 | 0 | 6 | 0 |
| live commentary | 3 | 4 | 4 | 5 |
| game rule | 3 | 2 | 3 | 2 |
| greeting / promo | 1 | 4 | 2 | 2 |
| generic self-help address | 0 | 5 | 0 | 7 |
| result flex | 0 | 2 | 0 | 2 |
| other | 2 | 2 | 1 | 0 |

Specific openers: 20 of 29 top vs 0 of 19 bottom (blind: 19 vs 1). Generic openers (self-help address, greeting or
promo, result flex): 1 of 29 vs 11 of 19 (blind: 2 vs 11). In 8 of 10 channels the top group has the higher share of
specific openers and none has a lower one. Example from one voice (Stick Trader Mind): top "Here's a brain fact that
should terrify..."; bottom "Ever feel like you're reliving the same losing trade", "Let's be honest, your biggest
losing streak...".

## What does not separate winners from losers
| feature (spoken hook, first 3 s) | top 29 | bottom 19 |
|---|---|---|
| hook length (median words) | 9 | 9 |
| number or named thing in first 3 s | 31% | 37% |
| question-form hook | 21% | 32% |
| "you" in the hook | 21% | 37% |
| duration (median s) | 59 | 53 |
| talking speed (words a second) | 3.41 | 3.18 |
| matches one of the 26 hooks.json formulas | 17% | 32% |
| hookscore.py (median) | 41 | 43 |
| any call to action in the last ~22 words | 21% | 47% (p 0.06; link/promo 1 vs 4, follow/subscribe 2 vs 4) |

The hook scorer the writer must pass today (50+) does not separate winners from losers here (41 vs 43; the skill itself
reports AUC 0.56 within a creator).

## Titles of all 419 (thirds of 139)
First person (I / my / we): 22 top vs 10 bottom (p 0.04; inside channels 23 vs 10, p 0.02). Stakes words: 28 vs 16
(p 0.07). Question form 47 vs 34 (p 0.11). Numbers 32 vs 35, "you" 22 vs 22, quiz format 11 vs 12, lesson format 33
vs 34: no difference. About 17 comparisons were run, so one or two at p < 0.05 are expected by chance.

## Formats inside channels (post hoc)
- BallGame Trivia, same game-show frame: "How many [position] are better than [named player]?" 4 of 4 above 1.69x
  (median 2.35x); "Keep 4, Cut 4" 7 of 7 at 1.0x or more (median 1.91x); "NFL Pictionary" 6 of 6 below 0.75x. The
  question has to start an argument; the quiz mechanic alone is average.
- Mark Trader "Buy or Sell?" chart quizzes: 5 Shorts, median 1.20x (0.75-1.35x), level with its lessons (1.23x).
- Black Girl Stocks "X vs Y: which is better": 3 of 3 at 4.35-10.43x (median 5.65x) vs 0.96x for its other 35.
- TraderTV Live first-person trading stories: median 2.31x (6) vs 0.97x for the other 33; the top spoken hook in the
  corpus is "I only got dinged once by management for..." ("One Losing Trade Almost Cost Me My Job", 19.3x).
- Coin Engineer (faceless, AI-style voice): 7 of its 8 top captioned Shorts run 32 s or less (median 15 s), single
  surprising facts ("Mr. Beast gave away $50,000 on...", "Wait, a game from 1991 might have the Bitcoin..."), three
  repeat their first line at the end; its 2 bottom ones run 56-64 s and open "What's up guys?".

## Shapes missing from hooks.json
1. The Reply: read a real viewer's question and answer it ("Okay, so someone asked what time frame..."): 10.4x, 5.7x, 4.3x.
2. The Withheld Point: "Here's a brain fact that should terrify...", "Okay, so you have your level set up. Cool, but".
3. Two And One: "Two trades, two levels. One holds," (8.5x; one case).
4. Wait, what: "Wait, a game from 1991 might have the Bitcoin" (6.5x); named person plus number (7.7x).
5. The Anecdote: drop into a personal story ("I only got dinged once by management for...", 19.3x).
6. The Rule: "Name five... without going over", "Keep four, cut four": neutral alone, the topic decides.
Avoid: greetings ("What's up guys?"), generic address or maxim ("If you keep over trading, your problem might not be
discipline"), result flexes ("plus $2,249"), link/promo and "like and subscribe" endings.

## Ten hook lines for @memestreetgame (numbers are placeholders: use the day's real facts)
| # | format | hook line | shape borrowed |
|---|---|---|---|
| 1 | Stock story | "Ember Dragon Ranches lost 31% in a day. Its dragons were fine." | concrete surprise |
| 2 | Chart quiz | "Same level, two charts. One breakout is real, one is a trap." | two and one |
| 3 | Chart lesson | "A player's stop keeps getting hit. Look at where she put it." | the reply (needs a real question) |
| 4 | Skit (Rookie) | "I lost 400 practice MB on one breakout. The volume warned me." | first-person confession |
| 5 | Chart lesson | "Your support line is drawn. Good, but the volume disagrees." | withheld point |
| 6 | Chart lesson | "Spike or retest: one entry lost 40% on this chart." | versus |
| 7 | Chart quiz | "Four breakouts. Keep two, cut two. Which survive a stop?" | game rule with an argument |
| 8 | Stock story | "Wait, dragons for rent, and the stock just rose 22%?" | wait, what |
| 9 | Stock story | "...and that is when Griffin Air Freight lost its level." | anecdote, mid-story cold open |
| 10 | Chart quiz | "This candle warned us three bars before the drop. Can you spot it?" | withheld point plus a question |

## Method and limits
Words rebuilt from json3 with start times; the hook is every word starting before 3.0 s; talking speed counts talking
time only. Number, named-thing, stakes, loop and CTA flags are lexicon-based and crude. About 30 comparisons with no
correction for multiple tests; Shorts cluster within channels; auto-captions have errors; on-screen text and the
picture are half the hook and none of that is in a caption; two coders, one unblinded; YouTube, not Instagram.
