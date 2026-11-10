"""Unit tests for the audit 99 follow-up, with the hand traces. Standard library only. Apache-2.0.

Hand traces:
- tokens("Rule: X + Y = Z"): lower "rule: x + y = z"; runs of [a-z0-9] and single operators: rule x + y = z (":" is
  skipped). "The apple + a Pear": the apple + a pear -> articles dropped -> apple + pear. "X+Y" -> x + y (glued
  operators still split). "ice-cream" -> ice - cream. None -> [].
- ("Rule: X Y + Z", "Rule: X + Y Z"): both normalise to "rule x y z" (quasi-exact 1); operator sequences "+" and "+"
  (OA 1); tokens rule x y + z vs rule x + y z differ (PX 0) -> ops_misplaced. In the run fixture, i2's
  " rule: x y + z" has the gold's tokens in another case -> format_only.
- ("X + Y = Y", "X + Y = Y."): exact 0 (the period); both normalise to "x y y"; operators "+=" both; tokens equal
  because "." is not a token -> format_only.
- ("apple + the pear", "apple + pear"): gold normalises "apple  the pear" -> article removed -> "apple pear"; tokens
  drop "the" -> equal -> format_only.
- ("Rule: X + Y = Z", "Rule: X + Y = Z ="): both normalise to "rule x y z"; operators "+=" vs "+==" -> ops_blind.
- (["A + B", "X + Y"], "x + y"): "A + B" normalises to "b" (the article "a" is removed), so only "X + Y" matches;
  exact 0 (case), OA 1, PX 1 -> format_only.
- Run fixture: 7 records; the perturbed i2 record, the valid-split i3 record and the second i1 trial-0 record are
  dropped; i1 t0 exact, i1 t1 ops_blind, i2 t0 ops_misplaced, i2 t1 format_only. Trial 0: n 2, em 1, qem 2, oa 2,
  px 1. Trial 1: n 2, em 0, qem 2, oa 1, px 1. Audit 99 totals: em 1, qem 4, oa 3, blind 1, other_norm 2.
- pick(["a","b","c"], "ab"): h = 97, then 97*131 + 98 = 12805; 12805 mod 3 = 1 -> "b".
"""

import unittest

import cases99b as C
import grade99b as b


class TestFollowUp(unittest.TestCase):
    def test_tokens(self):
        for text, want in C.FIX_TOKENS:
            self.assertEqual(b.tokens(text), want, text)

    def test_grades(self):
        for (gold, pred), want in C.FIX_GRADES_B:
            r = b.grade_record_b([gold], pred)
            self.assertEqual((r["em"], r["qem"], r["oa"], r["px"], r["cls"]), want, (gold, pred))

    def test_multi(self):
        (golds, pred), want = C.FIX_MULTI_B
        r = b.grade_record_b(golds, pred)
        self.assertEqual((r["em"], r["qem"], r["oa"], r["px"], r["cls"]), want)

    def test_classes_nest(self):
        # EM implies PX implies OA implies QEM on every fixture
        for (gold, pred), _ in C.FIX_GRADES_B:
            r = b.grade_record_b([gold], pred)
            self.assertLessEqual(r["em"], r["px"])
            self.assertLessEqual(r["px"], r["oa"])
            self.assertLessEqual(r["oa"], r["qem"])

    def test_run(self):
        s = b.summarize_run_b(C.FIX_INSTANCES_B, C.FIX_PREDS_B)
        for k, want in C.FIX_RUN_B.items():
            self.assertEqual(s[k], want, k)

    def test_v1_totals(self):
        s = b.summarize_run_b(C.FIX_INSTANCES_B, C.FIX_PREDS_B)
        self.assertEqual(b.v1_totals(s["classes"], [s["trials"]]), C.FIX_V1_TOTALS)

    def test_pick(self):
        for (lst, salt), want in C.FIX_PICK:
            self.assertEqual(b.pick(lst, salt), want)


if __name__ == "__main__":
    unittest.main()
