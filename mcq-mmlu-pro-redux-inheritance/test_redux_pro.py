"""Unit tests for audit 75 (standard library only). Apache-2.0.

Fixture trace (cases75.FIXTURE_*), row by row:
- Q one? (ok): joins MMLU (key 0) and MMLU-Pro 101 (4 shared options, same subject); key text kept.
- Q two? (miskey, expert says C): MMLU-Pro 102 keeps key 'f'; the expert answer 'g' is MMLU-Pro option C.
- Q three? (miskey, expert says '0'): digits, so unresolved unless a base is chosen; MMLU-Pro 103 keys 'i', another
  MMLU option (moved); with base 0 the expert answer is 'i', which is MMLU-Pro's key (A); base 1 gives -1 (none).
- Q four? (ok): the only MMLU-Pro row with this stem is stemez-Biology, not ori_mmlu, so not in MMLU-Pro.
- Q five? (bad_question_clarity): MMLU-Pro 105 has a double space in the stem and 'q ' as key (both normalise);
  filed under S1, not S2, so a cross-subject match; key kept.
- Same stem? (ok): MMLU-Pro 106 shares the stem but none of the options (it is MMLU's other 'Same stem?'), so
  stem_only and not in MMLU-Pro.
- Q seven? (ok): not in MMLU, so not joined at all.
- Q eight? ('expert', unsure): MMLU-Pro 108 shares 3 options; its key 'NEW' is no MMLU option (new); 'expert' rows
  are outside the inclusion table.
- Q nine? (no_correct_answer): two MMLU-Pro rows match, so ambiguous_pro: counted as in MMLU-Pro for inclusion,
  but no key status.
Inclusion by subject (error in, error out, ok in, ok out): S1 [3, 0, 1, 0], S2 [1, 0, 0, 2].
"""

import unittest

import cases75 as cs
import redux_pro as rp


class TestPieces(unittest.TestCase):
    def test_parse_correction(self):
        self.assertEqual(rp.parse_correction("C", ["a", "b", "c", "d"]), ("letters", (2,)))
        self.assertEqual(rp.parse_correction("A, C", ["a", "b", "c", "d"]), ("letters", (0, 2)))
        self.assertEqual(rp.parse_correction("0", ["i", "j", "k", "l"]), ("digits", (0,)))
        self.assertEqual(rp.parse_correction(" c ", ["a", "b", "c", "d"]), ("text", (2,)))
        self.assertEqual(rp.parse_correction("Paris", ["London", "paris", "Rome", "Oslo"]), ("text", (1,)))
        self.assertEqual(rp.parse_correction(None, ["a", "b"]), ("none", ()))
        self.assertEqual(rp.parse_correction("maybe both", ["a", "b"]), ("unmatched", ()))

    def test_single_correction(self):
        self.assertEqual(rp.single_correction("0", ["i", "j", "k", "l"]), ("digits", None))
        self.assertEqual(rp.single_correction("0", ["i", "j", "k", "l"], 0), ("digits", 0))
        self.assertEqual(rp.single_correction("0", ["i", "j", "k", "l"], 1), ("digits", None))
        self.assertEqual(rp.single_correction("2", ["i", "j", "k", "l"], 1), ("digits", 1))
        self.assertEqual(rp.single_correction("A, C", ["a", "b", "c", "d"]), ("letters", None))

    def test_key_status(self):
        ch = ["a", "b", "c", "d"]
        self.assertEqual(rp.key_status(ch, 0, ["x", " a"], 1), "kept")
        self.assertEqual(rp.key_status(ch, 0, ["x", "c"], 1), "moved")
        self.assertEqual(rp.key_status(ch, 0, ["x", "z"], 1), "new")

    def test_join_pro(self):
        idx = rp.pro_index(cs.FIXTURE_PRO)
        self.assertNotIn("Q four?", idx)
        st, row, fl = rp.join_pro("S2", "Q five?", ["q", "r", "s", "t"], idx)
        self.assertEqual((st, row["question_id"], fl), ("in_pro", 105, ("cross_subject",)))
        self.assertEqual(rp.join_pro("S2", "Same stem?", ["u", "v", "w", "x"], idx), ("not_in_pro", None,
                                                                                       ("stem_only",)))
        self.assertEqual(rp.join_pro("S1", "Q nine?", ["a9", "b9", "c9", "d9"], idx)[0], "ambiguous_pro")
        self.assertEqual(rp.join_pro("S1", "Nope?", ["a"], idx), ("not_in_pro", None, ()))

    def test_mmlu_index_skips_bad_key(self):
        mi = rp.mmlu_index(cs.FIXTURE_MMLU)
        self.assertEqual(len(mi), 9)

    def test_cmh_and_table(self):
        t = rp.two_by_two(4, 0, 1, 2)
        self.assertAlmostEqual(t["risk_ratio"], 3.0)
        self.assertAlmostEqual(t["chi_square_stat"], 7 * 64 / 120)
        h = rp.cmh([(3, 0, 1, 0), (1, 0, 0, 2)])
        self.assertAlmostEqual(h["sum_observed_minus_expected"], 2 / 3)
        self.assertAlmostEqual(h["cmh_stat"], 2.0)
        self.assertIsNone(h["mh_odds_ratio"])


class TestFixture(unittest.TestCase):
    def test_fixture_matches_target(self):
        S, flags = rp.analyse(cs.FIXTURE_REDUX, cs.FIXTURE_MMLU, cs.FIXTURE_PRO)
        got = rp.fixture_summary(S, flags)
        for k in cs.FIXTURE_TARGET:
            self.assertEqual(got[k], cs.FIXTURE_TARGET[k], k)
        self.assertEqual(set(got), set(cs.FIXTURE_TARGET))

    def test_flags_carry_no_text(self):
        _S, flags = rp.analyse(cs.FIXTURE_REDUX, cs.FIXTURE_MMLU, cs.FIXTURE_PRO)
        allowed = {"question_id", "category", "src", "label", "key_status", "pro_answer", "expert_answer",
                   "expert_answer_digits_0_based", "expert_answer_digits_1_based", "correction_format"}
        for f in flags:
            self.assertEqual(set(f), allowed)


if __name__ == "__main__":
    unittest.main()
