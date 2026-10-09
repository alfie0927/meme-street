"""The revenue model (revenue_model.py): the arithmetic of what a player pays in fees."""
import unittest

import _helpers  # noqa: F401  (puts the project folder on the path)
import revenue_model as rm


class FeesPaidTests(unittest.TestCase):
    def test_a_player_who_never_trades_pays_nothing_and_nobody_pays_more_than_they_have(self):
        self.assertEqual(rm.fees_paid(10000, 0.001, 0, 0.25, 30), 0.0)
        for tpd in (1, 10, 100, 1000, 100000):
            self.assertLessEqual(rm.fees_paid(10000, 0.001, tpd, 0.25, 365), 10000.0)
        self.assertAlmostEqual(rm.fees_paid(10000, 0.5, 1000, 1.0, 5), 10000.0)       # a fee that eats the whole balance each day

    def test_for_small_amounts_it_is_the_fee_times_the_money_traded(self):
        got = rm.fees_paid(10000, 0.001, 2, 0.1, 3)                                    # 6 trades of 1,000 MB at 0.1%
        self.assertAlmostEqual(got, 6.0, delta=0.01)

    def test_more_trading_more_days_or_a_higher_fee_always_pays_more(self):
        base = rm.fees_paid(10000, 0.001, 10, 0.25, 20)
        self.assertGreater(rm.fees_paid(10000, 0.001, 20, 0.25, 20), base)
        self.assertGreater(rm.fees_paid(10000, 0.001, 10, 0.25, 40), base)
        self.assertGreater(rm.fees_paid(10000, 0.002, 10, 0.25, 20), base)
        self.assertGreater(rm.fees_paid(10000, 0.001, 10, 0.5, 20), base)

    def test_the_balance_scales_everything_linearly(self):
        self.assertAlmostEqual(rm.fees_paid(20000, 0.001, 10, 0.25, 20), 2 * rm.fees_paid(10000, 0.001, 10, 0.25, 20))


class ModelTests(unittest.TestCase):
    def test_the_default_player_mix_adds_up(self):
        self.assertAlmostEqual(sum(a[1] for a in rm.ARCHETYPES), 1.0)
        rows, total = rm.model(signups=1000)
        self.assertAlmostEqual(sum(x["players"] for x in rows), 1000)
        self.assertAlmostEqual(sum(x["fees_total"] for x in rows), total)
        self.assertAlmostEqual(sum(x["share_of_fees"] for x in rows), 1.0)
        self.assertTrue(all(x["left"] >= 0 for x in rows))

    def test_a_few_heavy_traders_pay_most_of_the_fees(self):
        rows, _ = rm.model()
        share = rm.top_decile_share(rows)
        self.assertGreater(share, 0.5)
        self.assertLessEqual(share, 1.0)

    def test_if_everyone_plays_the_same_the_top_tenth_pays_a_tenth(self):
        rows, _ = rm.model([("same", 1.0, 10, 0.25, 20)])
        self.assertAlmostEqual(rm.top_decile_share(rows), 0.1)

    def test_income_depends_on_the_fee_and_scales_with_sign_ups(self):
        _, a = rm.model(fee=0.001, signups=1000)
        _, b = rm.model(fee=0.002, signups=1000)
        _, c = rm.model(fee=0.001, signups=2000)
        self.assertGreater(b, a)
        self.assertLess(b, 2 * a)                                  # (twice the fee is less than twice the income: balances run out)
        self.assertAlmostEqual(c, 2 * a)

    def test_the_report_names_its_assumptions_and_prints_every_fee_level(self):
        text = rm.report()
        self.assertIn("ASSUMPTIONS", text)
        for f in rm.FEES:
            self.assertIn(f"{f:.3%}", text)
        self.assertNotIn("free", text.lower())


if __name__ == "__main__":
    unittest.main()
