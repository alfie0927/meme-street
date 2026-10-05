"""Who supplies whom, who buys from whom, who competes: the internal links between companies. Players never see them;
they decide which companies appear together in two-company stories and how a move in one company spills over to
its partners and rivals, always as a fixed fraction of a zero-mean move."""
import math
import os
import random
import tempfile
import unittest
from unittest import mock

import _helpers
from _helpers import advance, drift, engine, join, make_engine, quiet

import relations


def companies(e):
    return [(s.ticker, s.sector, f"{s.name} {s.desc}") for s in e.stocks.values()
            if s.asset_type == "equity" and not s.moonshot]


class GraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = make_engine(80)
        cls.comp = companies(cls.e)
        cls.r = relations.Relations()
        cls.r.add(cls.comp)
        cls.tickers = {c[0] for c in cls.comp}

    def test_every_hand_written_company_exists_in_the_market(self):
        self.assertEqual(relations.CURATED - self.tickers, set())

    def test_the_links_make_sense_for_well_known_cases(self):
        r = self.r
        self.assertIn("SKYJ", r.customers("OILX"))                  # oil supplies the airline
        self.assertIn("OILX", r.customers("TRDL"))                  # drilling rigs supply the oil producer
        self.assertIn("MRHS", r.customers("CURA"))                  # a drug maker supplies the hospital chain
        self.assertIn("CRXP", r.customers("CURA"))                  # and the pharmacies
        self.assertIn("CLST", r.customers("LITH"))                  # lithium goes into batteries
        self.assertIn("VLTR", r.customers("CLST"))                  # and batteries into electric cars
        self.assertIn("NVXA", r.customers("NNCF"))                  # the foundry makes the chip designer's chips
        self.assertIn("DRON", r.rivals("AEGX"))
        self.assertIn("VLTR", r.rivals("CRLN"))
        self.assertIn("LEVT", r.rivals("VLTR"))                     # hover-cars compete with cars
        self.assertNotIn("FRBK", r.suppliers("HAIL"))               # a rideshare firm does not supply a grocer

    def test_links_are_consistent_from_both_sides(self):
        r = self.r
        for t in self.tickers:
            for c in r.customers(t):
                self.assertIn(t, r.suppliers(c))
            for s in r.suppliers(t):
                self.assertIn(t, r.customers(s))
            for v in r.rivals(t):
                self.assertIn(t, r.rivals(v))
            self.assertNotIn(t, r.suppliers(t) + r.customers(t) + r.rivals(t))
            self.assertFalse(set(r.rivals(t)) & (set(r.suppliers(t)) | set(r.customers(t))), t)

    def test_not_every_company_has_every_kind_of_link(self):
        n = len(self.tickers)
        for kind in ("supplier", "customer", "rival"):
            none = sum(1 for t in self.tickers if not self.r.partners(t, kind))
            self.assertGreater(none / n, 0.15, kind)                # plenty of companies have none...
            self.assertLess(none / n, 0.6, kind)                    # ...and plenty have some
        self.assertTrue(all(self.r.suppliers(t) or self.r.customers(t) or self.r.rivals(t) for t in self.tickers))

    def test_moonshots_and_derived_assets_are_not_in_the_graph(self):
        e = _helpers_real_engine(81)
        self.assertTrue(any(s.moonshot for s in e.stocks.values()))
        for s in e.stocks.values():
            if s.moonshot or s.asset_type != "equity":
                self.assertNotIn(s.ticker, e.relations)


def _helpers_real_engine(seed, **settings):
    from test_wild import real_engine
    return real_engine(seed, **settings)


class NewCompanyTests(unittest.TestCase):
    def setUp(self):
        self.r = relations.Relations()
        e = make_engine(82)
        self.r.add(companies(e))

    def test_a_new_company_is_linked_in_and_the_companies_already_there_get_the_other_side(self):
        r = self.r
        before = r.to_json()
        r.add([("NEWBIO", "pharma", "NewBio Therapeutics develops cancer drugs sold to hospitals and clinics")])
        customers = r.customers("NEWBIO")
        self.assertTrue(customers)                                  # it supplies someone
        for c in customers:
            self.assertIn("NEWBIO", r.suppliers(c))                 # so that company now has a new supplier
        self.assertTrue(set(customers) <= {"MRHS", "CRXP", "DDIA", "CLSC"}, customers)   # hospitals and pharmacies only
        self.assertTrue(r.rivals("NEWBIO"))                         # drug companies compete with each other
        after = r.to_json()
        self.assertTrue(all(x in after["supply"] for x in before["supply"]))     # nothing that existed was rearranged
        self.assertTrue(all(x in after["rival"] for x in before["rival"]))

    def test_the_hospital_chain_gains_a_supplier_when_a_drug_company_lists(self):
        r = self.r
        had = set(r.suppliers("MRHS"))
        for i in range(12):
            r.add([(f"NEWB{i}", "pharma", f"Biotech {i} drugs sold to hospitals")])
        self.assertTrue(set(r.suppliers("MRHS")) - had)

    def test_a_removed_company_disappears_from_everyone(self):
        r = self.r
        victims = r.customers("OILX") + r.suppliers("OILX") + r.rivals("OILX")
        r.remove("OILX")
        self.assertNotIn("OILX", r)
        for t in victims:
            self.assertNotIn("OILX", r.suppliers(t) + r.customers(t) + r.rivals(t))

    def test_saving_and_loading_keeps_the_graph(self):
        r = self.r
        again = relations.Relations.from_json(r.to_json())
        self.assertEqual(again.to_json(), r.to_json())
        again.add([("NEWBIO", "pharma", "NewBio drugs sold to hospitals")])      # and it can still grow

    def test_a_newcomer_with_no_fitting_partners_just_has_none(self):
        self.r.add([("ZZZZ", "meme", "A joke token")])
        self.assertEqual(self.r.suppliers("ZZZZ") + self.r.customers("ZZZZ"), [])


class EngineGraphTests(unittest.TestCase):
    def test_a_company_listed_while_running_is_linked_into_the_existing_ones(self):
        e = make_engine(83)
        before = set(e.relations.suppliers("MRHS"))
        for i in range(15):
            cfg = dict(next(c for c in e._read()[1].values() if c["ticker"] == "HLXB"), ticker=f"ZB{i:02d}",
                       name=f"Zeta Bio {i}", desc="Develops drugs sold to hospitals and clinics.")
            e.now += 1
            e._list(cfg, initial=False)
        self.assertTrue(any(f"ZB{i:02d}" in e.relations for i in range(15)))
        self.assertTrue(set(e.relations.suppliers("MRHS")) - before)

    def test_a_bankrupt_company_leaves_the_graph(self):
        e = make_engine(84)
        partners = e.relations.customers("NVXA") + e.relations.suppliers("NVXA") + e.relations.rivals("NVXA")
        s = e.stocks["NVXA"]
        s.fair = s.initial_price * 0.1
        s.distress_checked = False
        with mock.patch.object(random, "random", return_value=0.0):      # force the bankruptcy branch
            e._check_distress()
        self.assertNotIn("NVXA", e.stocks)
        self.assertNotIn("NVXA", e.relations)
        for t in partners:
            self.assertNotIn("NVXA", e.relations.suppliers(t) + e.relations.customers(t) + e.relations.rivals(t))

    def test_the_graph_survives_a_restart_and_an_old_save_gets_one(self):
        import json
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path = os.path.join(d, "state.json")
            random.seed(85)
            a = engine.Engine(state_file=path, bots=False)
            a.relations.customers_of["OILX"].discard("SKYJ")        # make the saved graph recognisably different
            a.relations.suppliers_of["SKYJ"].discard("OILX")
            a.tick(now=a.now)
            a.save()
            b = engine.Engine(state_file=path, bots=False)
            self.assertNotIn("SKYJ", b.relations.customers("OILX"))     # loaded from the save, not rebuilt
            self.assertIn("NVXA", b.relations.customers("NNCF"))
            state = json.load(open(path, encoding="utf-8"))
            state.pop("relations")                                  # a save from before the graph existed
            json.dump(state, open(path, "w", encoding="utf-8"))
            c = engine.Engine(state_file=path, bots=False)
            self.assertIn("SKYJ", c.relations.customers("OILX"))    # built from the companies, not loaded

    def test_players_never_see_suppliers_customers_or_rivals(self):
        e = make_engine(86)
        p = join(e, "snoop")
        e.tick(now=e.now)
        for ticker in ("NVXA", "MRHS", "OILX", "SKYJ"):
            persona = e.company_for(ticker)["persona"]
            self.assertEqual(set(persona), {"ceo", "cfo", "product", "city", "former_ceos"})
        def keys(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    yield str(k)
                    yield from keys(v)
            elif isinstance(obj, (list, tuple)):
                for v in obj:
                    yield from keys(v)
        names = {k.lower() for k in keys(e.init_for(p))}
        self.assertFalse({"supplier", "customer", "rival", "suppliers", "customers", "rivals", "relations"} & names)
        self.assertTrue(all("supplier" not in (s.persona or {}) for s in e.stocks.values()))

    def test_looking_at_a_company_page_does_not_disturb_the_random_numbers(self):
        a, b = make_engine(87), make_engine(87)
        for _ in range(5):
            a.company_for("NVXA")
        for e in (a, b):
            random.seed(1)                                          # the same random numbers for both
            e.tick(now=e.now + 1)
        self.assertEqual({k: s.fair for k, s in a.stocks.items()}, {k: s.fair for k, s in b.stocks.items()})


class StoryTests(unittest.TestCase):
    def test_two_company_stories_only_pair_companies_that_are_linked(self):
        e = make_engine(88)
        e.relations = relations.Relations()
        e.relations.add([("CURA", "pharma", "CuraGen drugs"), ("MRHS", "healthcare", "Meridian hospitals")])
        self.assertEqual(e.relations.customers("CURA"), ["MRHS"])          # the only link in the market
        for tk, s in e.stocks.items():
            if tk not in ("CURA", "MRHS"):
                s.revenue = 0.0                                             # only these two can be picked
        n0 = len(e.news_log)
        for _ in range(400):
            e.next_cross = e.now
            e._cross_stories()
        texts = [x["text"] for x in list(e.news_log)[n0:] if x["kind"] not in ("dividend", "earnings")]
        self.assertGreater(len(texts), 20)
        for t in texts:                                                     # every story pairs exactly these two
            self.assertIn(e.stocks["CURA"].name, t)
            self.assertIn(e.stocks["MRHS"].name, t)

    def test_a_company_with_no_customers_or_rivals_never_gets_a_story_about_them(self):
        e = make_engine(89)
        loner = "ZZLN"
        cfg = dict(next(c for c in e._read()[1].values() if c["ticker"] == "DOGO"), ticker=loner, name="Loner Corp",
                   sector="meme", desc="A joke token.")
        e._list(cfg, initial=False)
        e._assign_personas()
        e.relations = relations.Relations()
        e.relations.add([(loner, "meme", "Loner Corp A joke token")])
        self.assertEqual(e.relations.customers(loner) + e.relations.rivals(loner), [])
        s = e.stocks[loner]
        for tk in list(e.stocks):
            if tk != loner:
                e.stocks[tk].revenue = 0.0                          # only the loner can be picked
        s.revenue = 10.0
        before = len(e.news_log)
        for _ in range(60):
            e.next_cross = e.now
            e._cross_stories()
        self.assertEqual(len(e.news_log), before)

    def test_company_stories_name_suppliers_customers_and_rivals_from_the_graph(self):
        e = make_engine(90)
        s = e.stocks["CURA"]
        names = {e.stocks[t].name for t in e.relations.suppliers("CURA")}
        for _ in range(60):
            n = e._related_name(s, "supplier")
            if n:
                self.assertIn(n, names)
        none = next(t for t in sorted(e.relations.sector) if not e.relations.suppliers(t))
        self.assertIsNone(e._related_name(e.stocks[none], "supplier"))      # a company with no supplier names none


class SpilloverTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(91)
        self.r = self.e.relations

    def test_signs_follow_the_kind_of_link(self):
        r = self.r
        out = r.spill({"OILX": 0.10})
        self.assertGreater(out["SKYJ"], 0)                          # a supplier's good news reaches its customer
        out = r.spill({"SKYJ": 0.10})
        self.assertGreater(out["OILX"], 0)                          # a customer doing well helps its supplier
        out = r.spill({"AEGX": 0.10})
        self.assertLess(out["DRON"], 0)                             # a rival doing well hurts you

    def test_the_spillover_has_no_expected_move(self):
        rng = random.Random(5)
        r = self.r
        tickers = sorted(r.sector)
        total = {t: 0.0 for t in tickers}
        n = 4000
        for _ in range(n):
            moves = {t: rng.gauss(0, 0.01) for t in tickers}
            for t, v in r.spill(moves).items():
                total[t] += v
        for t in tickers:
            self.assertLess(abs(total[t] / n), 5 * 0.0025 / math.sqrt(n), t)

    def test_a_company_with_many_links_is_not_made_much_more_volatile(self):
        rng = random.Random(6)
        r = self.r
        tickers = sorted(r.sector)
        most = max(tickers, key=lambda t: len(r.suppliers(t)) + len(r.customers(t)) + len(r.rivals(t)))
        extra = []
        for _ in range(3000):
            moves = {t: rng.gauss(0, 0.01) for t in tickers}
            extra.append(r.spill(moves).get(most, 0.0))
        sd = math.sqrt(sum(x * x for x in extra) / len(extra))
        self.assertLess(sd, 0.01 * 0.35)           # well under a third of one company's own noise, even for the busiest

    def test_spillover_can_be_switched_off_and_flows_through_the_flush(self):
        e = self.e
        e.settings["daily_move_cap"] = 0
        e._pending = {"OILX": 0.05}
        start = e.stocks["SKYJ"].fair
        e._flush_moves()
        gain = e.stocks["SKYJ"].fair / start - 1
        self.assertGreater(abs(gain), 1e-4)
        e2 = make_engine(91, relation_spillover=0, daily_move_cap=0, sector_links={})
        for s in e2.stocks.values():
            s.dependencies = {}
        start = e2.stocks["SKYJ"].fair
        e2._pending = {"OILX": 0.05}
        e2._flush_moves()
        self.assertEqual(e2.stocks["SKYJ"].fair, start)

    def test_money_is_conserved_with_the_graph_running(self):
        e = make_engine(92)
        players = [join(e, f"rel{i}") for i in range(3)]
        e.tick(now=e.now)
        for k in range(400):
            e.tick(now=e.now + 1)
            if k % 9 == 0:
                e.trade(players[k % 3], random.choice(["OILX", "SKYJ", "CURA", "MRHS", "GOLD"]),
                        random.choice(["buy", "sell"]), 0.3)
        self.assertLess(abs(drift(e)), 1e-6)


if __name__ == "__main__":
    unittest.main()
