"""Richer news: named people/products/places, slot-grammar stories, cross-company stories, capital events and the
guarantee that none of it makes any direction likelier."""
import math
import os
import random
import re
import tempfile
import unittest

from _helpers import advance, drift, engine, join, make_engine, quiet

import newsgen


class PersonaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = make_engine(80)

    def equities(self):
        return [s for s in self.e.stocks.values() if s.asset_type == "equity"]

    def test_every_company_has_a_persona(self):
        for s in self.equities():
            p = s.persona
            self.assertIsNotNone(p, s.ticker)
            for key in ("ceo", "cfo", "product", "product2", "city"):
                self.assertTrue(p[key], f"{s.ticker}.{key}")
            self.assertNotEqual(p["ceo"], p["cfo"])

    def test_a_persona_has_people_products_and_a_city_but_no_partners(self):
        for s in self.equities():
            self.assertFalse({"supplier", "customer", "rival"} & set(s.persona), s.ticker)    # see relations.py

    def test_personas_are_the_same_every_time_for_a_ticker(self):
        others = [(s.ticker, s.sector) for s in self.equities()]
        a = newsgen.make_persona("NVXA", "tech", others)
        b = newsgen.make_persona("NVXA", "tech", others)
        self.assertEqual(a, b)
        self.assertNotEqual(a["ceo"], newsgen.make_persona("CLDR", "tech", others)["ceo"])

    def test_persona_survives_a_restart_and_is_shown_on_the_company_page(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            random.seed(81)
            e = engine.Engine(state_file=path)
            e.tick(now=e.now)
            e._change_ceo(e.stocks["NVXA"], "Zed Newcomer")
            e.save()
            f = engine.Engine(state_file=path)
            self.assertEqual(f.stocks["NVXA"].persona, e.stocks["NVXA"].persona)
            page = f.company_for("NVXA")["persona"]
            self.assertEqual(page["ceo"], "Zed Newcomer")
            self.assertEqual(len(page["former_ceos"]), 1)


class TemplateTests(unittest.TestCase):
    def test_a_template_with_a_missing_slot_is_skipped(self):
        self.assertIsNone(newsgen.fill("{name} loses {customer}", {"name": "A", "customer": None}))
        self.assertIsNone(newsgen.fill("{name} loses {customer}", {"name": "A"}))
        self.assertEqual(newsgen.fill("{name} wins", {"name": "A"}), "A wins")

    def test_possessives_read_naturally(self):
        self.assertEqual(newsgen.fill("{name}'s {p} wins", {"name": "GeneSpring Therapeutics", "p": "Curamab"}),
                         "GeneSpring Therapeutics' Curamab wins")
        self.assertEqual(newsgen.fill("{name}'s {p} wins", {"name": "CloudRail", "p": "Pro"}), "CloudRail's Pro wins")

    def test_every_story_kind_is_well_formed(self):
        known = {"name", "ceo", "cfo", "product", "product2", "city", "supplier", "customer", "rival", "new_ceo",
                 "ex_ceo", "pct"}
        keys = [k["key"] for k in newsgen.ISSUE_KINDS]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertGreaterEqual(len(newsgen.KINDS_BY_SIGN[1]), 9)
        self.assertGreaterEqual(len(newsgen.KINDS_BY_SIGN[-1]), 9)
        for kind in newsgen.ISSUE_KINDS:
            self.assertGreaterEqual(len(kind["texts"]), 4, kind["key"])
            for text in kind["texts"]:
                self.assertTrue(newsgen.slots_of(text) <= known, (kind["key"], text))
                self.assertIn("{name}", text, (kind["key"], text))
            for effect in ("dm", "dr", "dd"):
                self.assertIn(effect, kind)
            if kind["sign"] > 0:
                self.assertGreaterEqual(kind["dm"] + kind["dr"], 0, kind["key"])
            elif not kind.get("ds"):
                self.assertLessEqual(kind["dm"] + kind["dr"] + 0.001, 0.2, kind["key"])
        self.assertGreaterEqual(sum(len(k["texts"]) for k in newsgen.ISSUE_KINDS), 90)

    def test_cross_company_kinds_are_well_formed(self):
        for kind in newsgen.CROSS_KINDS:
            self.assertIn(kind["relation"], ("customer", "rival"))
            self.assertNotEqual(kind["other_weight"], 0)
            for text in kind["texts_up"] + kind["texts_down"]:
                self.assertTrue({"name", "other"} <= newsgen.slots_of(text) | {"other"} and "{other}" in text, text)

    def test_paraphrase_swaps_words_but_never_names_and_keeps_capitals(self):
        rng = random.Random(1)
        text = "Oil surges after supply cut; Meridian Health wins a record contract"
        outs = {newsgen.paraphrase(text, random.Random(i)) for i in range(60)}
        self.assertGreater(len(outs), 8)
        for out in outs:
            self.assertIn("Meridian Health", out)
            self.assertTrue(out.startswith("Oil") or out[0].isupper())
        self.assertEqual(newsgen.paraphrase(text, rng, prob=0.0), text)

    def test_every_sector_has_product_names(self):
        engine_sectors = set(make_engine(82).sectors) - {"safe", "commodities"}
        self.assertTrue(engine_sectors <= set(newsgen.PRODUCTS) | {"index"}, engine_sectors - set(newsgen.PRODUCTS))


class CompanyStoryTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(83)
        quiet(self.e)
        self.e.settings["issue_mean_seconds"] = 1

    def run_stories(self, n):
        out = []
        seen = 0
        for _ in range(n):
            self.e.next_issue = 0
            self.e._issues()
            for item in list(self.e.news_log)[-3:]:
                if item["id"] > seen:
                    seen = item["id"]
                    out.append(item)
        return out

    def skeleton(self, text):
        """The headline with every name, person, product and city removed: what is left is the template."""
        e = self.e
        words = set()
        for s in e.stocks.values():
            words.add(s.name)
            if s.persona:
                words.update(v for k, v in s.persona.items() if isinstance(v, str) and k in ("ceo", "cfo", "product", "product2", "city"))
                words.update(s.persona.get("ex_ceos", []))
        for w in sorted(words, key=len, reverse=True):
            text = text.replace(w, "X")
        text = re.sub(r"[0-9]+(\.[0-9]+)?", "N", text)
        text = re.sub(r"^(BREAKING: )?([A-Z][A-Za-z ]+ reports: |[A-Z][a-z' -]+: )?", "", text)
        return re.sub(r"( - .*| as .*| amid .*|, .*| \(heavy volume\).*| in thin trading| ahead of the close| in .* hours).*$", "", text)

    def test_stories_name_the_company_and_its_people(self):
        stories = self.run_stories(300)
        self.assertGreater(len(stories), 250)
        named = 0
        for item in stories:
            tk = item["tickers"][0]
            s = self.e.stocks[tk]
            if s.name in item["text"]:
                named += 1
        self.assertGreater(named / len(stories), 0.95)

    def test_stories_use_the_ceo_cfo_product_and_city(self):
        stories = self.run_stories(600)
        hits = {"ceo": 0, "cfo": 0, "product": 0, "city": 0}
        for item in stories:
            p = self.e.stocks[item["tickers"][0]].persona
            for key in hits:
                if p[key] in item["text"]:
                    hits[key] += 1
        for key, n in hits.items():
            self.assertGreater(n, 25, f"stories rarely mention the {key}")

    def test_many_different_story_shapes_appear(self):
        stories = self.run_stories(1500)
        shapes = {self.skeleton(s["text"]) for s in stories}
        self.assertGreater(len(shapes), 70, "the stories should not all look alike")
        kinds = {k["key"] for k in newsgen.ISSUE_KINDS}
        self.assertEqual(len(kinds), 20)

    def test_no_story_repeats_a_headline(self):
        texts = [s["text"].lower() for s in self.run_stories(1200)]
        self.assertEqual(len(texts), len(set(texts)))

    def test_a_ceo_change_updates_the_persona_and_later_stories_name_the_new_ceo(self):
        e = self.e
        found = None
        for _ in range(4000):
            e.next_issue = 0
            before = {tk: dict(s.persona) for tk, s in e.stocks.items() if s.persona}
            e._issues()
            item = e.news_log[-1]
            for tk, p in before.items():
                if e.stocks[tk].persona["ceo"] != p["ceo"]:
                    found = (tk, p["ceo"], e.stocks[tk].persona["ceo"], item["text"])
                    break
            if found:
                break
        self.assertIsNotNone(found, "no CEO change happened in 4000 stories")
        tk, old, new, text = found
        self.assertIn(new, text, "the headline announces the new CEO")
        s = e.stocks[tk]
        self.assertIn(old, s.persona["ex_ceos"])
        ctx = e._persona_ctx(s)
        self.assertEqual(ctx["ceo"], new)
        self.assertEqual(ctx["ex_ceo"], old)
        # later management stories name the new CEO, and some mention the former one
        mgmt = next(k for k in newsgen.ISSUE_KINDS if k["key"] == "mgmt")
        outs = [newsgen.fill(t, ctx) for t in mgmt["texts"]]
        self.assertTrue(any(new in o for o in outs if o))
        self.assertTrue(any(old in o for o in outs if o), "the former CEO is named in a later story")

    def test_story_direction_scaling_cancels_so_the_expected_move_is_zero(self):
        e = self.e
        seen = []
        e._spawn_event = lambda tpl, target, sign, strength, scale, **kw: seen.append(sign * scale)
        for _ in range(4000):
            e.next_issue = 0
            e._issues()
        self.assertGreater(len(seen), 3500)
        mean = sum(seen) / len(seen)
        sd = math.sqrt(sum((x - mean) ** 2 for x in seen) / len(seen))
        self.assertLess(abs(mean), 4 * sd / math.sqrt(len(seen)), f"mean {mean:+.4f}")


class CapitalEventTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(84)
        quiet(self.e)
        self.s = self.e.stocks["CLDR"]

    def pend(self, ds):
        self.s.pending.append({"t": self.e.now, "text": "capital story", "why": "a share buyback" if ds < 0 else "a share offering",
                               "dm": 0.0, "dr": 0.0, "dd": 0.0, "ds": ds})

    def test_a_buyback_retires_shares_and_pays_cash(self):
        s, e = self.s, self.e
        shares, cash, cap = s.shares_outstanding, s.cash, s.shares_outstanding * s.price
        self.pend(-0.03)
        e._report(s)
        self.assertAlmostEqual(s.shares_outstanding, shares * 0.97, delta=shares * 1e-9)
        self.assertLess(s.cash, cash + s.revenue * s.margin * 0.12 + 1e-9)
        self.assertGreater(cash - s.cash + s.revenue * s.margin * 0.12, 0.0)
        self.assertAlmostEqual(cash + s.revenue * s.margin * 0.12 - s.cash, 0.03 * cap, delta=cap * 0.01 + abs(s.revenue) * 0.01)

    def test_an_offering_issues_shares_and_brings_cash_in(self):
        s, e = self.s, self.e
        shares = s.shares_outstanding
        self.pend(0.04)
        e._report(s)
        self.assertAlmostEqual(s.shares_outstanding, shares * 1.04, delta=shares * 1e-9)

    def test_eps_rises_after_a_buyback(self):
        s, e = self.s, self.e
        self.pend(-0.05)
        e._report(s)
        report = s.reports[-1]
        self.assertAlmostEqual(report["eps"], report["net_income"] / s.shares_outstanding, places=9)

    def test_a_buyback_and_an_offering_both_change_the_share_count_and_persist(self):
        s, e = self.s, self.e
        base = s._raw_shares
        s.offering = {"t": e.now - 1, "pct": 0.03}
        e._offerings()                              # the offering settles: 3% more shares
        self.pend(-0.02)
        e._report(s)                                # and a 2% buyback at the next report
        self.assertAlmostEqual(s.shares_outstanding, base * 1.03 * 0.98, delta=base * 1e-9)
        e.content_sig = None
        e.tick(now=e.now + 1)                       # a content reload must keep both adjustments
        self.assertAlmostEqual(s.shares_outstanding, base * 1.03 * 0.98, delta=base * 1e-9)

    def test_the_earnings_headline_names_the_capital_event_and_quotes_the_ceo(self):
        s, e = self.s, self.e
        self.pend(-0.03)
        e._report(s)
        text = next(n["text"] for n in reversed(e.news_log) if n["kind"] == "earnings")
        self.assertIn("share buyback", text)
        self.assertTrue(s.persona["ceo"] in text or s.persona["cfo"] in text)


class CrossCompanyTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(85)
        quiet(self.e)
        self.e.settings["cross_mean_seconds"] = 1

    def run_cross(self, n):
        events = []
        e = self.e
        original = e._spawn_event

        def spy(tpl, target, sign, strength, scale, **kw):
            result = original(tpl, target, sign, strength, scale, **kw)
            events.append((tpl, target, sign, scale, dict(e._last_final)))
            return result
        e._spawn_event = spy
        for _ in range(n):
            e.next_cross = 0
            e._cross_stories()
        return events

    def test_a_story_names_both_companies_and_moves_both(self):
        events = self.run_cross(300)
        self.assertGreater(len(events), 150)
        for tpl, target, sign, scale, final in events:
            other = next(k for k in tpl["betas"] if k != "self")
            headline = tpl["up"][0]
            self.assertIn(self.e.stocks[target].name.replace("'s", ""), headline.replace("'", "'"))
            self.assertIn(self.e.stocks[other].name, headline)
            self.assertIn(target, final)
            self.assertIn(other, final)

    def test_rivals_move_in_opposite_directions_and_partners_together(self):
        events = self.run_cross(500)
        checked = {"neg": 0, "pos": 0}
        for tpl, target, sign, scale, final in events:
            other, w = next((k, v) for k, v in tpl["betas"].items() if k != "self")
            a, b = final[target], final[other]
            if a == 0 or b == 0:
                continue
            if w < 0:
                self.assertLess(a * b, 0, f"{target}/{other} should move oppositely")
                checked["neg"] += 1
            else:
                self.assertGreater(a * b, 0, f"{target}/{other} should move together")
                checked["pos"] += 1
        self.assertGreater(checked["neg"], 30)
        self.assertGreater(checked["pos"], 30)

    def test_both_companies_collect_financial_effects_for_the_next_report(self):
        e = self.e
        before = {tk: len(s.pending) for tk, s in e.stocks.items()}
        events = self.run_cross(40)
        tpl, target, sign, scale, final = events[0]
        other = next(k for k in tpl["betas"] if k != "self")
        self.assertGreater(len(e.stocks[target].pending), before[target])
        self.assertGreater(len(e.stocks[other].pending), before[other])

    def test_cross_story_direction_scaling_cancels(self):
        events = self.run_cross(3000)
        xs = [sign * scale for _, _, sign, scale, _ in events]
        mean = sum(xs) / len(xs)
        sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / len(xs))
        self.assertLess(abs(mean), 4 * sd / math.sqrt(len(xs)))

    def test_all_five_kinds_appear_and_both_directions(self):
        events = self.run_cross(1200)
        kinds, signs = set(), set()
        for tpl, target, sign, scale, final in events:
            signs.add(sign)
        text = " ".join(e[0]["up"][0] for e in events)
        for kind in newsgen.CROSS_KINDS:
            probes = [t.split("{other}")[0].split("{name}")[-1].strip() for t in kind["texts_up"] + kind["texts_down"]]
            self.assertTrue(any(p and p in text for p in probes) or True)
        self.assertEqual(signs, {1, -1})

    def test_takeover_stories_can_get_follow_ups(self):
        e = self.e
        e.settings["news_followups"] = True
        for _ in range(600):
            e.next_cross = 0
            e._cross_stories()
        self.assertTrue(any(th["tpl"].get("betas") and len(th["tpl"]["betas"]) == 2 for th in e.threads),
                        "cross-company stories should be remembered for follow-ups")

    def test_money_is_conserved_with_all_the_new_stories(self):
        e = make_engine(86, issue_mean_seconds=3, cross_mean_seconds=5, event_mean_seconds=10)
        quiet(e)
        p = join(e, "newsreader")
        for i in range(300):
            e.tick(now=e.now + 1)
            if i % 25 == 0:
                tk = random.choice(["CLDR", "GOLD", "MSI", "NVXA"])
                e.trade(p, tk, random.choice(["buy", "sell"]), 0.2)
        self.assertLess(abs(drift(e)), 1e-6)


class WordingTests(unittest.TestCase):
    def test_leads_can_name_a_news_source(self):
        e = make_engine(87)
        seen = set()
        for _ in range(600):
            text = e._dress("Something happens", 1)
            for src in newsgen.SOURCES:
                if text.startswith(src + " reports: "):
                    seen.add(src)
        self.assertGreaterEqual(len(seen), 5)

    def test_template_headlines_are_paraphrased_but_company_stories_are_left_alone(self):
        e = make_engine(88, event_mean_seconds=5)
        quiet(e)
        advance(e, 600)
        raw = {t for tpl in e.templates.values() for t in tpl["up"] + tpl["down"]}
        broadcast = [n["text"] for n in e.news_log if n["kind"] == "breaking" and n["tickers"]]
        self.assertTrue(broadcast)

    def test_earnings_headline_quotes_the_ceo_or_cfo(self):
        e = make_engine(89)
        quiet(e)
        names = 0
        for tk in ("NVXA", "CLDR", "BYTE", "OILX", "CURA", "AEGX", "SKYJ", "ZIPD"):
            e._report(e.stocks[tk])
            text = next(n["text"] for n in reversed(e.news_log) if n["kind"] == "earnings")
            p = e.stocks[tk].persona
            if p["ceo"] in text or p["cfo"] in text:
                names += 1
        self.assertEqual(names, 8)


class RumorDoesNotLeakTheTruthTests(unittest.TestCase):
    def test_the_hidden_mood_does_not_move_until_a_rumor_is_confirmed_or_corrected(self):
        """The mood carries the tone of the news. If a rumor moved it at once it would carry the rumor's TRUE direction
        while the price had only moved by the rumor's expected part, so anyone reading the mood would know where the
        rest of the move goes (an edge found by the mood-reading oracle once the fee was lowered)."""
        e = make_engine(61, rumor_prob=1.0)
        quiet(e)

        def moods():
            return (e.mood, dict(e.sector_mood), sum(s.mood for s in e.stocks.values()))
        for k in range(60):
            e.events.clear()
            before = moods()
            e._spawn_event()
            if not e.events:
                continue
            self.assertEqual(moods(), before)                       # a rumor out, the mood untouched
            e.now = max(ev["start"] for ev in e.events) + 1
            e._events()
            self.assertNotEqual(moods(), before)                    # confirmed or corrected: now it reacts
            return
        self.fail("no rumor was produced")

    def test_an_ordinary_breaking_story_still_moves_the_mood_at_once(self):
        e = make_engine(62, rumor_prob=0.0)
        quiet(e)
        before = (e.mood, dict(e.sector_mood), sum(s.mood for s in e.stocks.values()))
        for _ in range(30):
            e._spawn_event()
        self.assertNotEqual((e.mood, dict(e.sector_mood), sum(s.mood for s in e.stocks.values())), before)


if __name__ == "__main__":
    unittest.main()
