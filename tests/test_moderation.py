"""Chat moderation: a word filter that sees through disguises, reports that remove a message by themselves once enough
different players agree, mutes that get longer, appeals that a moderator can lift, a trade-first gate for new accounts,
and a log of everything. Chat never touches money or prices."""
import os
import random
import tempfile
import unittest

from _helpers import drift, engine, join, make_engine

import social

DAY = 86400


def fresh(seed=1, **settings):
    e = make_engine(seed, **settings)
    e.now = (int(e.now // DAY) + 1) * DAY + 100
    e.tick(now=e.now)
    return e


def say(e, p, text):
    e.now += 2
    return e.post_chat(p, text)


class FilterTests(unittest.TestCase):
    def test_plain_bad_words_and_their_endings_are_masked(self):
        self.assertEqual(social.clean_chat("what the fuck"), "what the ****")
        self.assertEqual(social.clean_chat("fucking hell"), "******* hell")
        self.assertEqual(social.clean_chat("SHITTY take"), "****** take")

    def test_look_alike_letters_and_spacing_do_not_get_past_it(self):
        for text in ("sh!t", "f u c k", "f.u.c.k", "fuuuuck", "$h1t", "b1tch", "a$$hole", "fvck".replace("v", "u"),
                     "ＦＵＣＫ", "fúck", "sh*t".replace("*", "!")):
            masked = social.clean_chat(f"you {text} you")
            self.assertEqual(masked.count("*"), len(masked) - len("you  you"), (text, masked))

    def test_other_languages_are_covered(self):
        self.assertNotIn("mierda", social.clean_chat("esto es mierda"))
        self.assertNotIn("scheisse", social.clean_chat("so eine Scheisse"))
        self.assertNotIn("putain", social.clean_chat("putain!"))

    def test_ordinary_words_are_left_alone(self):
        for text in ("I assume the class hit the target", "bitcoin is not a stock", "the putative buyer",
                     "flame retardant coatings", "Scunthorpe united", "a classic assessment", "compute the count",
                     "shiny new gold", "pass it on", "I think this will hit 100", "Shell oil", "bastion"):
            self.assertEqual(social.clean_chat(text), text, text)

    def test_the_message_keeps_its_own_accents_and_length(self):
        self.assertEqual(social.clean_chat("mañana vamos a comprar"), "mañana vamos a comprar")
        self.assertEqual(len(social.clean_chat("fúck this")), len("fúck this"))

    def test_words_can_be_added_by_a_content_pack(self):
        e = fresh(1, chat_bad_words=["gobbledy"])
        a = join(e, "adder")
        ok, _, m = say(e, a, "total gobbledy gook")
        self.assertTrue(ok)
        self.assertEqual(m["text"], "total ******** gook")
        self.assertEqual(social.clean_chat("total gobbledy gook"), "total gobbledy gook")      # the default list is unchanged


class GateTests(unittest.TestCase):
    def test_a_new_account_must_trade_before_it_can_chat_or_report(self):
        e = fresh(2, chat_min_trades=3)
        a, b = join(e, "rookie"), join(e, "oldhand")
        ok, msg, _ = say(e, a, "hello")
        self.assertFalse(ok)
        self.assertIn("3 trades", msg)
        for k in range(3):
            e.now += 2
            e.trade(a, "CLDR", "buy", 0.05)
        self.assertTrue(say(e, a, "hello")[0])
        mid = e.chat[-1]["id"]
        ok, msg = e.report_chat(b, mid)                                  # b has not traded: reports don't count
        self.assertFalse(ok)
        self.assertIn("trades", msg)

    def test_the_gate_is_off_when_set_to_zero_and_shown_on_the_profile(self):
        e = fresh(3, chat_min_trades=2)
        a = join(e, "gated")
        self.assertFalse(e.me_for(a)["chat_ready"])
        e.settings["chat_min_trades"] = 0
        self.assertTrue(e.me_for(a)["chat_ready"])


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.e = fresh(11)
        self.bad = join(self.e, "troll")
        self.r = [join(self.e, f"citizen{i}") for i in range(4)]
        self.mid = say(self.e, self.bad, "you are all idiots")[2]["id"]

    def test_one_or_two_reports_wait_for_a_moderator_and_the_third_removes_the_message(self):
        e = self.e
        self.assertIn("moderator", e.report_chat(self.r[0], self.mid)[1])
        self.assertIn("moderator", e.report_chat(self.r[1], self.mid)[1])
        self.assertEqual(len(e.chat), 1)
        ok, msg = e.report_chat(self.r[2], self.mid)
        self.assertTrue(ok)
        self.assertIn("removed", msg)
        self.assertEqual(len(e.chat), 0)
        self.assertEqual(e.take_auto_deletes(), [self.mid])
        self.assertEqual(e.take_auto_deletes(), [])

    def test_the_same_player_reporting_three_times_counts_once(self):
        e = self.e
        for _ in range(4):
            e.report_chat(self.r[0], self.mid)
        self.assertEqual(len(e.chat), 1)
        self.assertEqual(self.bad.strikes, 0)

    def test_the_author_is_muted_told_and_it_is_logged(self):
        e = self.e
        for r in self.r[:3]:
            e.report_chat(r, self.mid)
        self.assertEqual(self.bad.strikes, 1)
        self.assertAlmostEqual(e.muted[self.bad.token] - e.now, 600, delta=1)
        self.assertTrue(any("reported by 3 players" in n for n in self.bad.notices))
        ok, msg, _ = say(e, self.bad, "hello?")
        self.assertFalse(ok)
        self.assertIn("muted", msg)
        entry = e.mod_log[-1]
        self.assertEqual((entry["actor"], entry["action"], entry["name"]), ("auto", "mute", "troll"))

    def test_the_mutes_get_longer_each_time_up_to_a_day(self):
        e = self.e
        lengths = []
        for k in range(4):
            e.now += 100000
            mid = say(e, self.bad, f"another insult number {k}")[2]["id"]
            for r in self.r[:3]:
                e.now += 1
                e.report_chat(r, mid)
            lengths.append(round(e.muted[self.bad.token] - e.now))
        self.assertEqual(lengths, [600, 3600, 86400, 86400])
        self.assertEqual(self.bad.strikes, 4)

    def test_the_threshold_is_a_setting(self):
        e = self.e
        e.settings["chat_report_threshold"] = 2
        e.report_chat(self.r[0], self.mid)
        self.assertEqual(len(e.chat), 1)
        e.report_chat(self.r[1], self.mid)
        self.assertEqual(len(e.chat), 0)

    def test_reports_for_other_messages_do_not_add_up(self):
        e = self.e
        second = say(e, self.bad, "second insult")[2]["id"]
        e.report_chat(self.r[0], self.mid)
        e.report_chat(self.r[1], self.mid)
        e.report_chat(self.r[2], second)
        self.assertEqual(len(e.chat), 2)

    def test_money_is_untouched(self):
        e = self.e
        for r in self.r[:3]:
            e.report_chat(r, self.mid)
        self.assertLess(abs(drift(e)), 1e-6)


class AppealTests(unittest.TestCase):
    def setUp(self):
        self.e = fresh(21)
        self.bad = join(self.e, "misjudged")
        self.r = [join(self.e, f"voter{i}") for i in range(3)]
        mid = say(self.e, self.bad, "a perfectly fine opinion")[2]["id"]
        for r in self.r:
            self.e.report_chat(r, mid)

    def test_only_a_muted_player_can_appeal_once_with_some_words(self):
        e = self.e
        self.assertFalse(e.appeal(self.r[0], "I am not muted at all")[0])
        self.assertFalse(e.appeal(self.bad, "no")[0])
        self.assertTrue(e.appeal(self.bad, "That was a joke between friends, sorry.")[0])
        ok, msg = e.appeal(self.bad, "Please look at it again")
        self.assertFalse(ok)
        self.assertIn("already", msg)

    def test_an_appeal_shows_for_the_admin_and_the_player_sees_its_state(self):
        e = self.e
        e.appeal(self.bad, "That was a joke between friends, sorry.")
        view = e.admin_social()
        self.assertEqual([a["name"] for a in view["appeals"]], ["misjudged"])
        self.assertNotIn("token", str(view["appeals"][0].keys()))                # the token never leaves the server
        self.assertEqual(e.me_for(self.bad)["appeal"], "open")

    def test_lifting_unmutes_forgives_the_strike_and_tells_the_player(self):
        e = self.e
        e.appeal(self.bad, "That was a joke between friends, sorry.")
        aid = e.appeals[-1]["id"]
        ok, _ = e.resolve_appeal(aid, "lift")
        self.assertTrue(ok)
        self.assertNotIn(self.bad.token, {t for t, u in e.muted.items() if u > e.now})
        self.assertEqual(self.bad.strikes, 0)
        self.assertTrue(any("lifted" in n for n in self.bad.notices))
        self.assertTrue(say(e, self.bad, "thank you")[0])
        self.assertEqual(e.mod_log[-1]["action"], "appeal lifted")
        self.assertFalse(e.resolve_appeal(aid, "lift")[0])                       # already decided

    def test_denying_keeps_the_mute_and_the_strike(self):
        e = self.e
        e.appeal(self.bad, "That was a joke between friends, sorry.")
        aid = e.appeals[-1]["id"]
        self.assertTrue(e.resolve_appeal(aid, "deny")[0])
        self.assertGreater(e.muted[self.bad.token], e.now)
        self.assertEqual(self.bad.strikes, 1)
        self.assertEqual(e.me_for(self.bad)["appeal"], "denied")
        self.assertFalse(e.resolve_appeal(aid, "maybe")[0])

    def test_after_a_denial_a_second_mute_can_be_appealed_again(self):
        e = self.e
        e.appeal(self.bad, "That was a joke between friends, sorry.")
        e.resolve_appeal(e.appeals[-1]["id"], "deny")
        self.assertTrue(e.appeal(self.bad, "I would like another look please")[0])


class AdminActionsAreLoggedTests(unittest.TestCase):
    def test_admin_delete_and_mute_and_unmute_leave_a_trail(self):
        e = fresh(31)
        a = join(e, "target")
        mid = say(e, a, "something")[2]["id"]
        e.delete_chat(mid, "admin")
        e.mute("target", 300, "admin")
        e.mute("target", 0, "admin")
        self.assertEqual([x["action"] for x in e.mod_log], ["delete", "mute", "unmute"])
        self.assertEqual(e.admin_social()["mod_log"][0]["action"], "unmute")        # newest first
        e.mute("target", 300)                                                       # internal callers log nothing
        self.assertEqual(len(e.mod_log), 3)


class PersistenceTests(unittest.TestCase):
    def test_strikes_appeals_and_the_log_survive_a_restart(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(41)
            e = engine.Engine(state_file=path)
            e.now = (int(e.now // DAY) + 1) * DAY + 100
            e.tick(now=e.now)
            e.settings["chat_min_trades"] = 0
            bad = join(e, "persist")
            rs = [join(e, f"pr{i}") for i in range(3)]
            mid = say(e, bad, "rude words here")[2]["id"]
            for r in rs:
                e.report_chat(r, mid)
            e.appeal(bad, "Please reconsider this mute")
            e.save()
            f = engine.Engine(state_file=path)
            b2 = next(p for p in f.players.values() if p.name == "persist")
            self.assertEqual(b2.strikes, 1)
            self.assertEqual([a["status"] for a in f.appeals], ["open"])
            self.assertEqual(f.mod_log[-1]["action"], "appeal")
            self.assertGreater(f.muted[b2.token], f.now - 1)

    def test_an_old_save_without_any_of_it_loads(self):
        e = fresh(42)
        self.assertEqual(list(e.mod_log), [])
        self.assertEqual(e.appeals, [])
        p = join(e, "fresh")
        self.assertEqual(p.strikes, 0)


if __name__ == "__main__":
    unittest.main()
