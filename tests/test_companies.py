"""The companies as shipped: a spread of small, mid and large caps in every industry, a distinct description for each, and
the save migration that keeps a company's financials in proportion when the content packs change its size."""
import collections
import json
import os
import random
import tempfile
import unittest

from _helpers import engine, make_engine

SKIP_SECTORS = ("commodities", "safe")          # spot prices and the two safe-haven funds have no company size


def size(cap):
    return "large" if cap >= engine.LARGE_CAP else "mid" if cap >= engine.SMALL_CAP else "small"


class CompanyContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = make_engine(5)
        cls.equities = [s for s in cls.e.stocks.values()
                        if s.asset_type == "equity" and not s.moonshot and s.sector not in SKIP_SECTORS]

    def test_every_industry_has_more_than_one_size_and_there_are_plenty_of_each(self):
        by = collections.defaultdict(set)
        counts = collections.Counter()
        for s in self.equities:
            cls_ = size(s.market_cap_base)
            by[s.sector].add(cls_)
            counts[cls_] += 1
        for sector, sizes in by.items():
            self.assertGreaterEqual(len(sizes), 2, f"{sector} has only {sizes}")
        for cls_ in ("small", "mid", "large"):
            self.assertGreaterEqual(counts[cls_], 35, counts)
        self.assertGreaterEqual(sum(1 for sizes in by.values() if len(sizes) == 3), 15)

    def test_small_caps_are_more_volatile_than_large_caps_on_average(self):
        vols = collections.defaultdict(list)
        for s in self.equities:
            vols[size(s.market_cap_base)].append(s.vol)
        mean = {k: sum(v) / len(v) for k, v in vols.items()}
        self.assertGreater(mean["small"], mean["mid"])
        self.assertGreater(mean["mid"], mean["large"])

    def test_every_company_says_what_it_does_in_its_own_words(self):
        descs = {}
        for s in self.equities:
            words = s.desc.split()
            self.assertGreaterEqual(len(words), 14, (s.ticker, s.desc))
            self.assertNotIn(s.desc, descs.values(), s.ticker)
            descs[s.ticker] = s.desc
        by = collections.defaultdict(list)
        for s in self.equities:
            by[s.sector].append(s)
        for sector, members in by.items():                                  # rivals are told apart by their first words
            openings = [" ".join(s.desc.split()[:4]).lower() for s in members]
            self.assertEqual(len(openings), len(set(openings)), sector)

    def test_financials_stay_in_proportion_to_size(self):
        for s in self.equities:
            if s.revenue > 0:
                ps = s.market_cap_base / s.revenue                        # price-to-sales at the reference price
                self.assertTrue(0.05 < ps < 80, (s.ticker, s.market_cap_base, s.revenue))


class SizeMigrationTests(unittest.TestCase):
    def saved(self, tmp):
        path = os.path.join(tmp, "state.json")
        random.seed(3)
        e = engine.Engine(state_file=path)
        e.tick(now=e.now + 1)
        e.save()
        with open(path, encoding="utf-8") as fh:
            return e, path, json.load(fh)

    def load(self, path, d):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
        random.seed(4)
        return engine.Engine(state_file=path)

    def test_a_save_from_before_the_sizes_were_spread_has_its_financials_scaled(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            e, path, d = self.saved(tmp)
            tk = "RUNE"                                                     # 27.4 billion before, a small cap now
            old = engine.CAPS_BEFORE_SIZES[tk]
            s = e.stocks[tk]
            k = s.market_cap_base / old
            self.assertLess(k, 0.1)
            for v in d["stocks"].values():                                  # (as an old save: no cap_base, old-sized numbers)
                v.pop("cap_base", None)
            v = d["stocks"][tk]
            v["revenue"], v["cash"], v["debt"] = s.revenue / k, s.cash / k, s.debt / k
            v["reports"] = [{"t": 1.0, "revenue": s.revenue / k, "net_income": s.revenue * s.margin / k, "eps": 0.5}]
            untouched = "NVXA"                                              # not in the table: its size never changed
            self.assertNotIn(untouched, engine.CAPS_BEFORE_SIZES)
            f = self.load(path, d)
            g = f.stocks[tk]
            self.assertAlmostEqual(g.revenue, s.revenue, places=9)
            self.assertAlmostEqual(g.cash, s.cash, places=9)
            self.assertAlmostEqual(g.debt, s.debt, places=9)
            self.assertAlmostEqual(g.reports[-1]["revenue"], s.revenue, places=9)
            self.assertEqual(g.reports[-1]["eps"], 0.5)                      # per share: unchanged
            self.assertAlmostEqual(f.stocks[untouched].revenue, e.stocks[untouched].revenue, places=12)

    def test_a_normal_restart_changes_nothing_and_a_later_resize_scales_again(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            e, path, d = self.saved(tmp)
            self.assertEqual(d["stocks"]["NVXA"]["cap_base"], e.stocks["NVXA"].market_cap_base)
            f = self.load(path, d)
            for tk in ("NVXA", "RUNE", "FERT"):
                self.assertAlmostEqual(f.stocks[tk].revenue, e.stocks[tk].revenue, places=12)
            d["stocks"]["FERT"]["cap_base"] = 2 * e.stocks["FERT"].market_cap_base   # the pack halved it since
            g = self.load(path, d)
            self.assertAlmostEqual(g.stocks["FERT"].revenue, e.stocks["FERT"].revenue / 2, places=9)


if __name__ == "__main__":
    unittest.main()
