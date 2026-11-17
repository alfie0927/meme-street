# The sends, 17 November 2026 to 5 January 2027

For the roadmap's section 3, part 2 (`docs/ROADMAP.md`). Everything here is sent by you, from your own accounts, one
at a time. About 3 hours a week. Each link carries its own `ref` tag so the week's numbers show which send worked
(`python3 tools/visits.py --weekly` on the server, read into `growth/weekly.md` every Monday).

**Before any send:** the fixes of 17 November must be live (merge the branch `fix/leaks-c-home-learn-count`, then
tell me to deploy). Until then a stranger still meets the board of house bots and the locked lesson link.

## Week of 17 November (about 1.5 hours)

### 1. The trading name and an address on the domain (30 minutes)

- Pick the name the site gives as its operator, for example "Meme Street Games". Tell me, and I put it in the
  terms, the About page and the foot of every email.
- Make an address such as `hello@memestreet.net` that forwards to your own inbox. A free forwarder does it
  (ImprovMX, or the forwarding your domain registrar includes). It needs one DNS change (the MX records), which is
  yours to make. It does not touch the website. Tell me the address and I replace the Gmail one everywhere.
- A caution, not legal advice: the shop already sells passes, and UK rules for online sellers generally expect the
  trader's own name and a postal address to be available to customers. A trading name alone may not meet that.
  Check it before the teacher emails (roadmap R9 and R4).

### 2. Your own result to 10 to 20 people you know (20 minutes)

Play today's Daily, press **Share**, and paste the result to one person at a time with a line of your own. The
share text already carries the challenge link ("beat my score"). Two openers:

```
I've been building a two-minute stock chart game. Here's my score today, can you beat it? Takes two minutes, no sign-up.
```

```
Quick favour: would you play today's chart (two minutes, no account) and tell me the first thing that confused you?
```

The second one is worth more. Write down what each person says, word for word.

### 3. Search Console and Bing (15 minutes)

- Google Search Console: add `memestreet.net` (the DNS record or the HTML tag it offers), then submit
  `https://memestreet.net/sitemap.xml`.
- Bing Webmaster Tools: "Import from Google Search Console".
- In the SEO routine's network settings, allow `memestreet.net`, so its runs can fetch the live site.

## Week of 23 November (about 3.5 hours)

### 4. Show HN (a weekday, 14:00 to 17:00 UK time; stay two hours)

The full draft is `growth/launch.md`. Three things in it must change first:

**The link.** Send people to the game, not the home page:

```
https://memestreet.net/daily?ref=hn
```

**The paragraph "How it pays for itself".** Its first sentence ("the lessons are open to everyone") is not true.
Use this instead:

```
How it pays for itself: the Daily Chart, the market and the first unit of lessons are open to everyone, and a free account does two lessons a day. MB are never sold. The shop sells two memberships: Pro opens the whole lesson path, leverage and 32 more chart indicators; Expert adds the scripted bots and backtests. MB can never be cashed out, and the return boards rank percentage return, so nothing bought can lift a place on them.
```

**Two answers in the table.**

| Question | Answer |
|---|---|
| "Why would I pay?" | You may never need to: the Daily, the market, 17 indicators, the drawing tools and two lessons a day are open. Pro opens the whole lesson path, leverage and more indicators; Expert adds bots and backtests. |
| "Are the bots labelled on the boards?" | No name carries a tag, but the Daily's board says how many of its results are players and how many are house traders (computer-run), and nothing counts a house trader as a player. They see only the candles shown so far and pay the same 0.1%. |

**Your three answers, decided before you post** (the readers will ask; one directory, The DLES, refuses games with
AI-generated content, so the first answer matters beyond Hacker News):

1. Was AI used to build it? Say so plainly in the first comment if it was. Being found out later costs more.
2. How are the house traders shown? The answer above.
3. Is it open source? Yes or no, and one line why.

Then answer every comment, plainly, and thank people for the faults they find. Their words are the best list of
what to fix.

### 5. The first 20 teacher and society emails

The texts, with the priced class offer, are in `growth/schools.md`. One person at a time, never a list. The
contacts to work through are in `growth/outreach_contacts.md`.

## Week of 30 November (about 3 hours)

### 6. Ten daily-game directories

The listing texts are in `growth/directories.md`. Use the link `https://memestreet.net/daily?ref=<directory name>`
for each, so each one shows as its own row.

### 7. One post on r/WebGames

Read the subreddit's rules on the day (they change, and they are strict about titles and sign-ups). The Daily fits
its main rule: playable in the browser with no account.

```
Title: Meme Street Daily Chart: trade one mystery stock chart for two minutes (no sign-up)
Link:  https://memestreet.net/daily?ref=webgames
```

Stay for the comments, as on Hacker News.

### 8. 20 more emails

## Week of 7 December (about 3 hours)

### 9. itch.io and CrazyGames

The builds and the steps are in `growth/portals/README.md`. itch.io first (the frame is live).

### 10. 20 more emails

## Week of 14 December (about 1 hour)

### 11. Read the numbers with me

I run `tools/visits.py --weekly` on the server and we fill `growth/weekly.md`. Reply to everyone who wrote, and ask
each of them one question: "what nearly stopped you?"

## Week of 5 January (about 1 hour)

### 12. One follow-up to the teachers who did not reply

The text is in `growth/schools.md`.

## The dates that decide (roadmap, section 8)

- **20 December, players.** Of the people who finish a Daily, 10% or more returning on another day or leaving an
  email is worth building on. Under 5% after 500 real visitors means the Daily does not hold people.
- **16 January, money.** From 60 priced emails: 3 paid pre-orders means the class version gets built; 1 means a
  side income at best; none, with nobody asking the price, closes the class route.
- **31 January.** If both failed, this stops being an income project. The site stays up as a portfolio piece.
