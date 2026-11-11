"""The Learn lessons as plain pages for search engines and new visitors (`/lessons`, `/lessons/{id}`; 2026-11-07).

The in-game Learn page loads its lessons with JavaScript, so a search engine sees none of them. These pages are made
on the server from the same `content/learn-*.md` (learning.load_content), with a title, description, canonical
address and schema.org data each, and link back into the game for the live charts and chart tests."""
import html
import json
import re

import learning

CSS = """:root{--bg:#08090b;--line:#262d33;--line2:#1a1f24;--txt:#dce3e8;--mut:#7d8a93;--up:#3ad07a;--acc:#4cc3cc;
 --mono:ui-monospace,"Cascadia Mono","SF Mono",Consolas,"Liberation Mono",Menlo,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.65 var(--mono)}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:860px;margin:0 auto;padding:0 16px}
header{display:flex;align-items:center;gap:12px;padding:14px 0;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;color:var(--txt)}.brand img{width:26px;height:26px;border-radius:3px}
.sp{flex:1}.btn{display:inline-block;padding:8px 14px;border-radius:2px;border:1px solid var(--line);color:var(--txt);font:600 14px var(--mono)}
.btn.go{background:var(--up);border-color:var(--up);color:#04140a}.btn:hover{text-decoration:none;border-color:var(--acc)}
.crumb{color:var(--mut);font-size:13px;margin:22px 0 8px}h1{font:700 clamp(24px,5vw,34px)/1.25 var(--mono);margin:0 0 10px}
.lead{font-size:17px;color:#b9c3ca;margin:0 0 20px}h2{font:700 16px var(--mono);margin:30px 0 6px;padding-bottom:6px;border-bottom:1px solid var(--line)}
p,li{color:#c6cfd5}.box{border-left:3px solid var(--acc);background:#4cc3cc10;padding:10px 14px;margin:14px 0}
.box.warn{border-color:#e0a03a;background:#e0a03a10}.box.tip{border-color:var(--up);background:#3ad07a10}
.tbl{overflow-x:auto}table{border-collapse:collapse;margin:12px 0;font-size:14px}td,th{border:1px solid var(--line);padding:6px 10px;text-align:left}
.try{border:1px solid var(--line);padding:12px 14px;margin:14px 0}.nav{display:flex;justify-content:space-between;gap:12px;margin:30px 0;flex-wrap:wrap}
.cta{border:1px solid var(--up);padding:16px;margin:30px 0}.cta p{margin:0 0 10px}
ol.toc,ul.toc{padding-left:20px}.toc li{margin:4px 0}.toc small{color:var(--mut)}
footer{padding:30px 0 40px;color:var(--mut);font-size:13px}"""
HEAD = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,'
        'initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#08090b"><title>{t}</title>'
        '<meta name="description" content="{d}"><link rel="canonical" href="{url}"><meta property="og:title" content="{t}">'
        '<meta property="og:description" content="{d}"><meta property="og:url" content="{url}"><meta property="og:type" '
        'content="article"><meta property="og:image" content="https://memestreet.net/brand/memestreet_header_peaks.png">'
        '<link rel="icon" href="/favicon.ico" sizes="any"><link rel="apple-touch-icon" href="/brand/apple-touch-icon.png">'
        '<script type="application/ld+json">{ld}</script><style>{css}</style></head><body><div class="wrap">'
        '<header><a class="brand" href="/"><img src="/brand/memestreet_logo_peaks.png" alt="" width="26" height="26">'
        'Meme Street</a><span class="sp"></span><a href="/lessons" class="btn">Lessons</a><a href="/#join" class="btn go">'
        'Sign up</a></header>')
CTA = ('<div class="cta"><p><b>Practise it on a live market, free.</b> Every account starts with 1,000 MB of practice '
       'money (no cash value, never paid out) on a fictional market that runs around the clock.</p>'
       '<a class="btn go" href="/#join">Create a free account</a> <a class="btn" href="/daily">Play today\'s Daily Chart</a></div>')
FOOT = ('<footer><a href="/lessons">All lessons</a> · <a href="/daily">Daily Chart</a> · <a href="/tools/position-size-calculator">'
        'Position size calculator</a> · <a href="/tools/risk-reward-calculator">Risk reward calculator</a> · <a href="/about">About Meme Street</a>'
        ' · <a href="/bots/guide">Trading bots</a> · <a href="/vs">Compare</a><br>Everything on Meme Street is fictional and nothing is investment '
        'advice. MB are practice money with no cash value.</footer></div></body></html>')

CALC_PATH = "/tools/position-size-calculator"
CALC_TITLE = "Position size calculator: how many shares to buy for a 1% risk | Meme Street"
CALC_DESC = ("Free position size calculator. Enter your account, the risk you accept, your entry and your stop, and it "
             "gives the number of shares, the amount at risk and the profit at your target. Works for long and short trades.")
CALC_BODY = """<p class="crumb"><a href="/lessons">Lessons</a> › Tools</p><h1>Position size calculator</h1>
<p class="lead">Position size = (account &times; risk %) &divide; (entry &minus; stop). Enter the four numbers and the
calculator gives the number of shares to buy so that, if your stop is hit, you lose only the share of your account you chose.</p>
<form id="f" class="try" onsubmit="return false">
<p><label>Account size <input id="acct" type="number" min="0" step="any" value="1000"></label>
<label>Risk per trade, % of account <input id="risk" type="number" min="0" step="any" value="1"></label></p>
<p><label>Entry price <input id="entry" type="number" min="0" step="any" value="50"></label>
<label>Stop price <input id="stop" type="number" min="0" step="any" value="48"></label>
<label>Target, in R (reward &divide; risk) <input id="rr" type="number" min="0" step="any" value="2"></label></p>
</form>
<div id="out" class="box tip" aria-live="polite">Enter your numbers above.</div>
<noscript><p>This calculator needs JavaScript. The sum is: shares = (account &times; risk %) &divide; |entry &minus; stop|.</p></noscript>
<h2>How it works</h2>
<p>Your risk is the amount you lose if the stop is hit, not the size of the trade. Take the account times the risk
percentage (1% of 1,000 is 10). Divide it by the distance from entry to stop (50 to 48 is 2 per share) and you get the shares
to buy (5). The position is then 5 &times; 50 = 250, which is 25% of the account, yet a stop-out costs only 1%.</p>
<p>The wider the stop, the smaller the position. If the stop is above the entry the trade is a short, and the same formula
applies.</p>
<div class="box warn"><b>Watch out:</b> a stop can gap, so the real loss can be bigger than the number shown. The result also
leaves out fees and does not check that you can afford the position. On Meme Street the fee is 0.1% on each side of a trade.</div>
<p>Learn the idea behind it in <a href="/lessons/position-sizing">The 1% rule and sizing by risk</a>, then
<a href="/lessons/stop-placement">where to put the stop</a> and <a href="/lessons/r-multiples">what R multiples mean</a>.
In the game, the <b>Position size and risk</b> tool under every stock's chart does this sum and fills in the trade for you.</p>
<script>
(function(){var $=function(i){return document.getElementById(i)},o=$("out");
function fmt(x){return x.toLocaleString("en-US",{maximumFractionDigits:2})}
function go(){var a=+$("acct").value,r=+$("risk").value,e=+$("entry").value,s=+$("stop").value,rr=+$("rr").value;
if(!(a>0&&r>0&&e>0&&s>0)||e===s){o.textContent="Enter an account, a risk %, an entry and a stop that differs from the entry.";return}
var d=Math.abs(e-s),risk=a*r/100,n=risk/d,val=n*e,short=s>e,t=short?e-d*rr:e+d*rr;
var h="<b>"+(short?"Short":"Long")+" "+fmt(n)+" shares</b> (position "+fmt(val)+", "+fmt(val/a*100)+"% of the account).<br>"
+"If the stop at "+fmt(s)+" is hit you lose "+fmt(risk)+" ("+fmt(r)+"% of the account); the stop is "+fmt(d/e*100)+"% from entry.";
if(rr>0)h+="<br>At "+fmt(rr)+"R the target is "+fmt(t)+" and the profit "+fmt(risk*rr)+".";
if(t<=0&&rr>0)h+=" (That target is below zero, so a short cannot reach it.)";
o.innerHTML=h}
document.getElementById("f").addEventListener("input",go);go()})();
</script>"""

RR_PATH = "/tools/risk-reward-calculator"
RR_TITLE = "Risk reward ratio calculator: reward to risk and the win rate you need | Meme Street"
RR_DESC = ("Free risk reward ratio calculator. Enter your entry, stop and target and it gives the reward to risk ratio, "
           "the break-even win rate, and the profit or loss in R. Works for long and short trades.")
RR_BODY = """<p class="crumb"><a href="/lessons">Lessons</a> › Tools</p><h1>Risk reward ratio calculator</h1>
<p class="lead">Reward to risk = |target &minus; entry| &divide; |entry &minus; stop|. A long at 100 with a stop at 95 and a
target at 110 risks 5 to make 10, which is 2 to 1. Enter your three prices and the calculator gives the ratio and the win
rate you need to break even before costs.</p>
<form id="f" class="try" onsubmit="return false">
<p><label>Entry price <input id="entry" type="number" min="0" step="any" value="100"></label>
<label>Stop price <input id="stop" type="number" min="0" step="any" value="95"></label>
<label>Target price <input id="target" type="number" min="0" step="any" value="110"></label></p>
</form>
<div id="out" class="box tip" aria-live="polite">Enter your prices above.</div>
<noscript><p>This calculator needs JavaScript. The sum is: reward to risk = |target &minus; entry| &divide; |entry &minus; stop|,
and the break-even win rate = 1 &divide; (1 + reward to risk).</p></noscript>
<h2>How it works</h2>
<p>Risk is the distance from entry to stop; reward is the distance from entry to target. Their ratio is the reward to risk.
Measured in R (one R is the amount you risk), a stop-out is &minus;1R and a target hit at 2 to 1 is +2R.</p>
<p>The win rate you need is 1 &divide; (1 + reward to risk), before costs. At 1 to 1 you must win half the time, at 2 to 1
one trade in three, at 3 to 1 one in four. A higher ratio lets you be wrong more often, but a far target is also hit less
often, so the ratio alone does not make a trade good.</p>
<div class="box warn"><b>Watch out:</b> fees and gaps are not in the sum, so the real break-even win rate is a little higher.
On Meme Street the fee is 0.1% on each side of a trade.</div>
<p>Learn the idea in <a href="/lessons/r-multiples">R-multiples and reward to risk</a>, then work out how many shares to
buy with the <a href="/tools/position-size-calculator">position size calculator</a>.</p>
<script>
(function(){var $=function(i){return document.getElementById(i)},o=$("out");
function fmt(x){return x.toLocaleString("en-US",{maximumFractionDigits:2})}
function go(){var e=+$("entry").value,s=+$("stop").value,t=+$("target").value;
if(!(e>0&&s>0&&t>0)||e===s){o.textContent="Enter an entry, a stop and a target. The stop must differ from the entry.";return}
var short=s>e;if(short?!(t<e):!(t>e)){o.textContent="For a "+(short?"short the target must be below":"long the target must be above")+" the entry.";return}
var risk=Math.abs(e-s),rew=Math.abs(t-e),rr=rew/risk,be=100/(1+rr);
o.innerHTML="<b>"+(short?"Short":"Long")+": "+fmt(rr)+" to 1 reward to risk.</b><br>Risk "+fmt(risk)+" per share ("+fmt(risk/e*100)
+"% of entry), reward "+fmt(rew)+" per share ("+fmt(rew/e*100)+"%).<br>Hit the target: +"+fmt(rr)+"R. Hit the stop: &minus;1R."
+"<br>Break-even win rate before costs: "+fmt(be)+"%."}
document.getElementById("f").addEventListener("input",go);go()})();
</script>"""

RR_LINK = ('<div class="try">Try it: the <a href="/tools/risk-reward-calculator">free risk reward ratio calculator</a> '
           "does this sum for you.</div>")
CALC_LINK = ('<div class="try">Try it: the <a href="/tools/position-size-calculator">free position size calculator</a> '
             "does this sum for you.</div>")


def inline(s):
    """Escaped text with the curriculum's **bold** and [text](/path) (site paths only, as the Learn page allows)."""
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"\[([^\]]+)\]\((/[^)\s\"]*)\)", r'<a href="\2">\1</a>', s)


def body_html(lesson):
    out = []
    for b in lesson["body"]:
        if "p" in b:
            out.append(f"<p>{inline(b['p'])}</p>")
        elif "h" in b:
            out.append(f"<h2>{inline(b['h'])}</h2>")
        elif "list" in b:
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in b["list"]) + "</ul>")
        elif "table" in b:
            head, *rows = b["table"]
            out.append('<div class="tbl"><table><tr>' + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
                       + "</table></div>")
        elif "test" in b:
            out.append(f'<div class="try">Chart test: <a href="/learn?test={b["test"]}">try one on a real Meme Street '
                       "chart</a>, then see what the price did next.</div>")
        elif "chart" in b:
            out.append(f'<div class="try">This lesson has a live example chart: <a href="/learn?l={lesson["id"]}">open '
                       "it in the game</a>.</div>")
        elif "try" in b:
            out.append(f'<div class="try">Try it: <a href="{html.escape(b["href"])}">{inline(b["try"])}</a></div>')
        elif "q" in b:
            out.append(f'<div class="try"><b>Check yourself:</b> {inline(b["q"])} <a href="/learn?l={lesson["id"]}">Answer it in the game</a>.</div>')
        elif "task" in b:
            out.append(f'<div class="try"><b>Do it on the market:</b> {inline(b["text"])} <a href="/learn?l={lesson["id"]}">Open the lesson</a>.</div>')
        elif "calc" in b:
            out.append(f'<div class="try"><b>Work it out:</b> a {b["calc"]} calculation with fresh numbers each day. '
                       f'<a href="/learn?l={lesson["id"]}">Do it in the game</a>.</div>')
        elif "mine" in b:
            out.append(f'<div class="try">In the game this lesson shows <a href="/learn?l={lesson["id"]}">your own trading '
                       "numbers</a> next to the idea.</div>")
        else:
            k = next((k for k in ("here", "tip", "warn") if k in b), None)     # an unknown block is skipped, never a 500 (loop 10)
            if k:
                label = {"here": "On Meme Street", "tip": "Tip", "warn": "Watch out"}[k]
                out.append(f'<div class="box {k}"><b>{label}:</b> {inline(b[k])}</div>')
    return "".join(out)


class Lessons:
    def __init__(self, site):
        self.site = site
        self.tracks, self.lessons = learning.load_content()
        self.by_id = {x["id"]: x for x in self.lessons}
        self.track = {t["id"]: t for t in self.tracks}
        self.hub_text = (f"{len(self.lessons)} free trading lessons in {len(self.tracks)} tracks: charts, candlesticks, "
                         "indicators, orders, risk management, shorting, options and trading psychology, each a few "
                         "minutes long, with practice on a live market.")

    def paths(self):
        return ["/lessons"] + [f"/lessons/{x['id']}" for x in self.lessons]

    def page(self, lid):
        """A lesson's page, or None if there is no such lesson."""
        x = self.by_id.get(lid)
        if x is None:
            return None
        i = self.lessons.index(x)
        tr = self.track[x["track"]]
        url = f"{self.site}/lessons/{lid}"
        ld = [{"@context": "https://schema.org", "@type": "LearningResource", "name": x["title"], "description": x["summary"],
               "url": url, "timeRequired": f"PT{x['minutes']}M", "learningResourceType": "lesson", "isAccessibleForFree": True,
               "inLanguage": "en", "educationalLevel": "beginner",
               "provider": {"@type": "Organization", "name": "Meme Street", "url": self.site + "/"}},
              {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "Lessons", "item": self.site + "/lessons"},
                  {"@type": "ListItem", "position": 2, "name": tr["title"], "item": f"{self.site}/lessons#{tr['id']}"},
                  {"@type": "ListItem", "position": 3, "name": x["title"], "item": url}]}]
        siblings = [y for y in self.lessons if y["track"] == x["track"]]
        nav = '<div class="nav">'
        if i > 0:
            nav += f'<a href="/lessons/{self.lessons[i - 1]["id"]}">&larr; {html.escape(self.lessons[i - 1]["title"])}</a>'
        if i + 1 < len(self.lessons):
            nav += f'<a href="/lessons/{self.lessons[i + 1]["id"]}">{html.escape(self.lessons[i + 1]["title"])} &rarr;</a>'
        nav += "</div>"
        toc = "".join(f"<li><b>{html.escape(y['title'])}</b></li>" if y is x else
                      f"<li><a href=\"/lessons/{y['id']}\">{html.escape(y['title'])}</a></li>" for y in siblings)
        return (HEAD.format(t=html.escape(f"{x['title']} | Meme Street trading lessons"), d=html.escape(x["summary"]),
                            url=url, ld=json.dumps(ld).replace("</", "<\\/"), css=CSS)
                + f'<p class="crumb"><a href="/lessons">Lessons</a> › <a href="/lessons#{tr["id"]}">{html.escape(tr["title"])}</a>'
                f' · {x["minutes"]} min read</p><h1>{html.escape(x["title"])}</h1><p class="lead">{inline(x["summary"])}</p>'
                + body_html(x) + (CALC_LINK if lid == "position-sizing" else RR_LINK if lid == "r-multiples" else "") + nav + CTA + f'<h2>More in {html.escape(tr["title"])}</h2><ol class="toc">{toc}</ol>' + FOOT)

    def calculator(self):
        """The free position size calculator (works without an account; the sum runs in the page)."""
        url = self.site + CALC_PATH
        ld = [{"@context": "https://schema.org", "@type": "WebApplication", "name": "Position size calculator",
               "url": url, "description": CALC_DESC, "applicationCategory": "FinanceApplication",
               "operatingSystem": "Any", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
               "provider": {"@type": "Organization", "name": "Meme Street", "url": self.site + "/"}},
              {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "Lessons", "item": self.site + "/lessons"},
                  {"@type": "ListItem", "position": 2, "name": "Position size calculator", "item": url}]}]
        css = CSS + "label{display:inline-block;margin:6px 14px 6px 0}input{display:block;margin-top:4px;width:11em;max-width:100%;" \
            "padding:6px;background:#0d1013;color:var(--txt);border:1px solid var(--line);font:15px var(--mono)}"
        return (HEAD.format(t=html.escape(CALC_TITLE), d=html.escape(CALC_DESC), url=url,
                            ld=json.dumps(ld).replace("</", "<\\/"), css=css) + CALC_BODY + CTA + FOOT)

    def risk_reward(self):
        """The free risk reward ratio calculator (works without an account; the sum runs in the page)."""
        url = self.site + RR_PATH
        ld = [{"@context": "https://schema.org", "@type": "WebApplication", "name": "Risk reward ratio calculator",
               "url": url, "description": RR_DESC, "applicationCategory": "FinanceApplication",
               "operatingSystem": "Any", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
               "provider": {"@type": "Organization", "name": "Meme Street", "url": self.site + "/"}},
              {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "Lessons", "item": self.site + "/lessons"},
                  {"@type": "ListItem", "position": 2, "name": "Risk reward ratio calculator", "item": url}]}]
        css = CSS + "label{display:inline-block;margin:6px 14px 6px 0}input{display:block;margin-top:4px;width:11em;max-width:100%;" \
            "padding:6px;background:#0d1013;color:var(--txt);border:1px solid var(--line);font:15px var(--mono)}"
        return (HEAD.format(t=html.escape(RR_TITLE), d=html.escape(RR_DESC), url=url,
                            ld=json.dumps(ld).replace("</", "<\\/"), css=css) + RR_BODY + CTA + FOOT)

    def hub(self):
        url = self.site + "/lessons"
        d = self.hub_text
        ld = {"@context": "https://schema.org", "@type": "Course", "name": "Learn to trade: the Meme Street course",
              "description": d, "url": url, "isAccessibleForFree": True, "inLanguage": "en",
              "provider": {"@type": "Organization", "name": "Meme Street", "url": self.site + "/"},
              "hasCourseInstance": {"@type": "CourseInstance", "courseMode": "online", "courseWorkload": "PT"
                                    + str(sum(x["minutes"] for x in self.lessons)) + "M"},
              "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD", "category": "Free"}}
        parts = []
        for t in self.tracks:
            items = "".join(f'<li><a href="/lessons/{x["id"]}">{html.escape(x["title"])}</a> <small>{x["minutes"]} min · '
                            f'{inline(x["summary"])}</small></li>' for x in self.lessons if x["track"] == t["id"])
            parts.append(f'<h2 id="{t["id"]}">{html.escape(t["title"])}</h2><p>{inline(t["blurb"])}</p><ol class="toc">{items}</ol>')
        return (HEAD.format(t="Learn to trade: free stock trading lessons | Meme Street", d=html.escape(d), url=url,
                            ld=json.dumps(ld).replace("</", "<\\/"), css=CSS)
                + f'<p class="crumb">Lessons</p><h1>Learn to trade, free</h1><p class="lead">{html.escape(d)} Read them '
                "here, then practise each idea with 1,000 MB of practice money on Meme Street's fictional market.</p>"
                + CTA + '<p class="try">Free tools: <a href="/tools/position-size-calculator">position size calculator</a> · <a href="/tools/risk-reward-calculator">risk reward ratio calculator</a></p>'
                + "".join(parts) + FOOT)


if __name__ == "__main__":
    L = Lessons("https://memestreet.net")
    assert len(L.paths()) == len(L.lessons) + 1
    for x in L.lessons:
        s = L.page(x["id"])
        assert s.count("<h1>") == 1 and f'href="https://memestreet.net/lessons/{x["id"]}"' in s, x["id"]
        assert "**" not in s and "<script>" not in s.split("</script>", 1)[1], x["id"]
    c = L.calculator()
    assert c.count("<h1>") == 1 and f'href="https://memestreet.net{CALC_PATH}"' in c and c.count("<script>") == 1
    r = L.risk_reward()
    assert r.count("<h1>") == 1 and f'href="https://memestreet.net{RR_PATH}"' in r and r.count("<script>") == 1
    assert 'href="/tools/position-size-calculator"' in L.page("position-sizing")
    assert L.page("nope") is None and L.hub().count("/lessons/") >= len(L.lessons)
    assert inline("**a** [b](/x) <i>") == '<b>a</b> <a href="/x">b</a> &lt;i&gt;'
    print("ok", len(L.lessons), "lessons")
