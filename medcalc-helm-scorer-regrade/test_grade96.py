"""Unit tests for audit 96 (medcalc-helm-scorer-regrade). Standard library only. Apache-2.0.

Hand traces (cases96.py):
- HELM: physical '303' in [287.8766, 318.1794] -> 1; the same output for lab or dosage -> ValueError inside the try
  -> 0 (#4351); ' 9\\n' strips to '9' == '9' -> 1; '9.0' != '9' -> 0; the quoted duration parses to 18*7+1 = 127
  days -> 1; '(18, 1)' does not parse -> 0 (#4365); a quoted duration followed by text still parses, because
  re.match is anchored only at the start -> 1; '12/4/2020' parses with strptime like '12/04/2020' -> 1; 'abc' and
  '5 mg' raise in float() -> 0; '4.75' at the inclusive lower limit -> 1.
- Grades: lab/dosage '303' -> R = C = 1 (range_lab / range_dosage); '250' out of range and '303 mg' not a number ->
  0; '(18, 1)', '(18 weeks, 1 day)' and "('18 weeks', '1 day')" -> 127 days -> C 1 (duration_format), R 0;
  '(18, 2)' -> 128 -> 0; '(18 weeks, 1)' labels only one part -> 0; '9.0' for '9' and '4.50' for '4.5' -> C 1
  (same_value); '9.4' for '9' -> 0 (rounding is not in C); 'nan' for 'NaN' -> not finite -> 0.
- rounded_only: round(9.4) = 9 -> 1; round(9.6) = 10 -> 0; equal values -> 0; a non-integer reference -> 0.
- Durations: ' ( '2 weeks' , '3 days' ) ' -> 17; mismatched quotes, three parts or no parentheses -> None.
- Runs: two medcalc_bench keys for a_x, the v4.0.0 one wins (1 dropped); b_y's key with num_output_tokens is kept;
  med_qa is ignored.
- Ranks {a: 1/2, b: 1/2, c: 1/4} -> {a: 1, b: 1, c: 3}; tau-b of [1,2,3] vs [1,3,2]: 2 concordant, 1 discordant ->
  1/3; a constant list -> None.
- Verdicts: case 1 all held; case 2 none (mean gain 7/200 < 1/20, 119 < 120, 4800 >= 4719); case 3 every boundary
  held (mean 1/20, 175, 4700 < 4719, 3, 3); case 4 the minimum gain 1/100 < 1/50 fails P3.
"""

import unittest

import cases96 as C
import grade96 as g


class TestHelm(unittest.TestCase):
    def test_helm_score(self):
        for pred, ref, extra, cat, want in C.FIX_HELM:
            with self.subTest(pred=pred, cat=cat):
                self.assertEqual(g.helm_score(pred, ref, extra, cat), want)


class TestGrades(unittest.TestCase):
    def test_grade(self):
        for pred, ref, extra, cat, h, r, c, cls in C.FIX_GRADE:
            with self.subTest(pred=pred, cat=cat):
                self.assertEqual(g.grade(pred, ref, extra, cat), {"h": h, "r": r, "c": c, "cls": cls})

    def test_rounded_only(self):
        for pred, ref, want in C.FIX_ROUND:
            with self.subTest(pred=pred, ref=ref):
                self.assertEqual(g.rounded_only(pred, ref), want)

    def test_duration_days(self):
        for pred, want in C.FIX_DAYS:
            with self.subTest(pred=pred):
                self.assertEqual(g.duration_days(pred), want)

    def test_plain_number(self):
        self.assertEqual(g.plain_number(" 12.0\n"), 12.0)
        self.assertIsNone(g.plain_number("inf"))
        self.assertIsNone(g.plain_number(""))
        self.assertIsNone(g.plain_number(None))


class TestRunsRanks(unittest.TestCase):
    def test_select_runs(self):
        self.assertEqual(g.select_runs(C.FIX_RUNS, C.PREFIX), C.FIX_RUNS_TARGET)

    def test_ranks(self):
        self.assertEqual(g.min_ranks(C.FIX_ACC), C.FIX_RANKS)

    def test_tau(self):
        for xs, ys, want in C.FIX_TAU:
            got = g.kendall_tau_b(xs, ys)
            if want is None:
                self.assertIsNone(got)
            else:
                self.assertAlmostEqual(got, want, places=12)


class TestVerdicts(unittest.TestCase):
    def test_verdicts(self):
        for args, want in C.FIX_V_CASES:
            with self.subTest(args=args):
                self.assertEqual(g.predictions96(*args, C.THRESHOLDS), want)


if __name__ == "__main__":
    unittest.main()
