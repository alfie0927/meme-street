# The series bible (step 1 of the studio)

Every reel is one part of one series. This page is what stays the same in every part: who it is about, where it happens,
and the rules nobody breaks. `bible.json` holds the same facts as data (slots, lengths, safe zones, the hook's word lists).

## The series
**Meme Street: one real stock chart a day.** At midnight UTC a real US stock's chart goes up on memestreet.net with its name
hidden. A visitor sees the 60 trading days before, then gets two minutes to trade the next 120 with practice money. At the
end the name is revealed. The reels exist to make a stranger want to play today's chart, and come back tomorrow.

## The day (four reels, UTC)
| Slot | Part | What it does | Engine |
|---|---|---|---|
| 04:00 | The new chart | Today's chart is live. It shows only the 60 days BEFORE the game, never what comes next, and asks the day's vote. | any |
| 09:00 | A new way in | A way of showing the game nobody has seen yet, in its own art style. Uses charts that are already revealed. | any |
| 16:00 | A new way in | The same job, a different idea and a different style from 09:00 and from the last seven. | any |
| 23:30 | The answer | The story behind today's chart. ALWAYS the same form: the ride (below). | `ride` |

04:00 asks, 23:30 answers and reports the count ("7 of 9 of you said buy"): that is the loop that brings a viewer back.

## The cast (every one drawn in code)
- **The chart.** The hero of every reel. It is always a REAL price line, never invented, and it is always doing something: a
  road, a rope, a race, a line being drawn. A chart sitting still in a panel is the thing we do not make.
- **The product.** What the company makes, modelled from its real parts (`explainer/models3d.js`). In the answer reel it
  rides the chart.
- **The crowd.** Cut-out people with a drawn face that shows one feeling at a time (joy, shock, sad, smug). Buyers wear
  green, sellers wear red when a reel sets them against each other.
- **The narrator.** One voice for the answer reel (the pipeline's). The promo reels may be silent: music, hits and words on
  screen.

## The rules nobody breaks
1. **Real or nothing.** Every price, date and figure comes from the game's data or the day's researched sources. No invented
   numbers, no invented quotes, no made-up people. A real person is named only when the research names them as a public figure.
2. **Never spoil a live chart.** Before 23:30 on its day, a reel may show a chart's 60 days of history and nothing after.
3. **The Triple Hook** opens every reel (`studio.py lint` enforces it):
   - **Context**: what this is about, in the first words, SAID and SHOWN and WRITTEN, all three meaning the same thing.
   - **Lean**: a number, a proof, a pain or something unexpected that makes the viewer want the next line.
   - **Snapback**: a line that pulls the other way from where they were leaning.
4. **Frame 0 is already moving** and shows something the viewer recognises. Never black, never a logo, never a still card.
5. **Nothing overlaps, ever.** Words have their own place; nothing is drawn over the subject or under Instagram's own buttons
   (keep words inside x 60 to 1020, y 250 to 1600).
6. **A choice in the last second.** Every reel ends on a question with two or three answers to comment (A, B, C).
7. **Every hit is heard.** Whatever lands, bursts, counts or cuts on screen has its sound one frame later; the music sits
   under the voice.
8. **Every frame is checked** (`check.py`) and the contact sheets are looked at before a reel is shown to anyone.
9. **A style is used once a week.** 09:00 and 16:00 never share a style with each other or with the last seven of their kind.
   The 23:30 answer never changes form.
10. **$0, no credits, no copies.** Only free tools and the no-credit music library. A model reel lends its STYLE only: never
    its characters, pictures, words, music, or a real brand's look.
11. **Practice money.** Every caption carries "Practice money only. Not investment advice."

## The answer reel's form: the ride
The chart is a landscape: a ridge whose skyline is the price line, with a road along its edge. A mystery crate stands at the
start. The Triple Hook is said while the landscape builds itself. On the reveal the crate bursts and the company's product
drives out, then rides the road in one continuous shot: each event of the story is a set piece standing at its own place on
the chart, and the product is there, at that price, when the narrator reaches it. It ends on the whole chart, the vote, and
"A new mystery chart goes live at midnight."
