"""Unit tests for audit 88 (standard library only). Run: python -m unittest -v. Apache-2.0.

Hand traces:
- Categories: 'Poor question: None of ...' has no 'incorrect' first word and no word 'key' -> other; 'Validity unclear'
  has first word 'validity', not 'valid' -> other; 'keyboard issue' has first word 'keyboard' and no 'bad key' ->
  other; 'Key, wrong option' lower-cases to first word 'key,' -> stripped 'key' -> key.
- Mojibake: UTF-8 bytes of 'e acute' (C3 A9) and of the right single quote (E2 80 99) read as Mac Roman give
  U+221A U+00A9 and U+201A U+00C4 U+00F4; encoding those back to Mac Roman and decoding as UTF-8 restores the text.
  'Raoult' + U+2019 encodes to Mac Roman D5, which is not valid UTF-8 there -> unchanged. Greek mu U+03BC is not in
  Mac Roman -> unchanged.
- Placement: row 0 normalises to q0's key (exact); row 1 matches only after repair (repaired, q1); row 2 is q2's key
  (the 'Dup Q' text is shared by q2 and q3, but the options pick q2); row 3 has 'Dup Q' with unknown options -> two
  text matches -> ambiguous; row 4 differs from q4 only in an option's case -> one text match -> question_only;
  row 5 matches nothing -> none.
- Kappa: pairs TT, TT, TF, FF: observed 3/4, rater A 3/4 true, rater B 1/2 true, chance 3/8 + 1/8 = 1/2 ->
  (3/4 - 1/2) / (1/2) = 1/2. TF, FT: observed 0, chance 1/2 -> -1. All TT: chance 1 -> None.
- Verdicts case 1: 6/10 >= 1/2; 4/10 > 1/8; 2/20 <= 1/4; 7/12 > 5/40; 7/12 >= 1/2; 1 overlap -> all held.
  Case 2: key rows 4 < 5 (P2, P3 undecidable), valid rows 9 < 10 (P4 undecidable); 3/10 is not > 3/10; 3/10 < 1/2;
  0 overlaps of 3 -> all false. Case 3: 5/10 >= 1/2 holds at the boundary; 5/10 is not > 5/10; 5/20 <= 1/4 holds at
  the boundary; 5/10 > 0/5; no S1-flagged kept question -> P7 undecidable.
"""

import unittest
from fractions import Fraction

import base88 as qm
import cases88 as C
import fb88 as fb


class TestReviews(unittest.TestCase):
    def test_categories(self):
        for split, review, want in C.FIX_CAT:
            self.assertEqual(fb.fb_category(split, review), want, (split, review))

    def test_mojibake(self):
        self.assertEqual("Café’s Q".encode("utf-8").decode("mac_roman"), C.FIX_MOJI[0][0])
        for s, want in C.FIX_MOJI:
            self.assertEqual(fb.demojibake(s), want)

    def test_answer_keys(self):
        for s, want in C.FIX_AK:
            self.assertEqual(fb.parse_answer_key(s), want, s)


class TestPlacement(unittest.TestCase):
    def test_place(self):
        out, counts = fb.place(C.FIX_PLACE_ROWS, C.FIX_QIDS)
        self.assertEqual(out, C.FIX_PLACE)
        self.assertEqual(counts, C.FIX_PLACE_COUNTS)

    def test_redux_group(self):
        for lab, want in C.FIX_RGROUP:
            self.assertEqual(fb.redux_group(lab), want)

    def test_redux_group_matches_base_groups(self):
        labels = {0: "wrong_groundtruth", 1: "ok", 2: "bad_options_clarity", 3: "expert"}
        g = qm.groups(5, labels)
        names = {"miskey": "miskey", "ok": "ok", "other_error": "other_error", "unsure_or_conflict": "unsure",
                 "unreviewed": "unreviewed"}
        for name, mine in names.items():
            for q in g[name]:
                self.assertEqual(fb.redux_group(labels.get(q)), mine)

    def test_first_per_qid(self):
        self.assertEqual(fb.first_per_qid(C.FIX_UNITS), C.FIX_UNITS_KEPT)

    def test_count(self):
        units = [{"c": "key", "f": True}, {"c": "key", "f": False}, {"c": "valid", "f": True}]
        self.assertEqual(fb.count(units, lambda u: u["c"] == "key", lambda u: u["f"]), (1, 2))


class TestStats(unittest.TestCase):
    def test_kappa(self):
        for pairs, want in C.FIX_KAPPA:
            self.assertEqual(fb.kappa(pairs), want)

    def test_auc_copied(self):
        self.assertEqual(qm.auc([3, 2], [1, 2]), Fraction(7, 8))
        self.assertIsNone(qm.auc([], [1]))

    def test_consensus_flag_copied(self):
        self.assertEqual(qm.flag_question([1, 6, 3, 0], 0, 6), (True, 1, 6))
        self.assertEqual(qm.flag_question([6, 3, 1, 0], 0, 6), (False, 1, 3))
        self.assertEqual(qm.margin([2, 6, 1, 1], 0), 4)

    def test_verdicts(self):
        for args, want in C.FIX_V_CASES:
            self.assertEqual(fb.predictions88(*args, C.THRESHOLDS), want)


if __name__ == "__main__":
    unittest.main()
