"""Unit tests for audit 91 (math-helm-scorer-regrade). Standard library only. Apache-2.0.

Hand traces of the FIX_GRADE expectations (g = HELM's reference answer, p = HELM's output answer; H = is_equiv(g, p)):
 1  g '5', p '5' -> H 1; A boxed, is_equiv 1 -> 1.
 2  g '10001', p '10,001': _strip_string leaves the comma -> H 0; value: '10,001' matches the thousands pattern ->
    10001 = 10001 -> A 1, value_format.
 3  g '\\frac{3}{2}' (brace count closes at the last '}'), p '1.5': strings differ (only '0.5' is rewritten) -> H 0;
    value 3/2 = 3/2 -> A 1, value_format.
 4  p None (no \\boxed or \\fbox) -> H 0; no fallback; unboxed: last $..$ '7(3y+2) = 21y + 14' -> after last '=' ->
    '21y + 14'; is_equiv strips spaces -> '21y+14' -> A 1, unboxed (route unboxed_math).
 5  p None -> H 0; 'answer is' -> line ' $7$.' -> segment '7' -> A 1, unboxed (unboxed_phrase).
 6  '\\boxed 5' has no braces: last_boxed_only_string finds no '}' -> g None; p None -> is_equiv(None, None) = 1 -> H 1;
    A: gold fallback '\\boxed 5' -> '5'; output unboxed phrase '7.' -> '7' -> 0 -> down-flip both_none.
 7  as 6 but the output says 5 -> H 1 (both None), A 1 -> no flip.
 8  g None, p '5' -> H 0; A: gold fallback '5' -> is_equiv('5', '5') -> A 1, gold_fallback (route boxed).
 9  output '\\fbox{12}': last_boxed_only_string returns '\\fbox{12}', remove_boxed rejects it -> p None -> H 0;
    fallback_answer -> '12' -> A 1, pred_fallback (route fallback).
10  '9901' vs '10001' -> H 0, A 0.
11  p '5\\text{cm}': no '\\text{ ' with a space, so _remove_right_units keeps it -> H 0; value drops the trailing
    \\text{cm} -> 5 -> A 1, value_format.
12  p '3\\text{ cm}\\text{ m}': _remove_right_units asserts 2 parts, gets 3 -> exception -> raw compare -> H 0;
    value: strip_safe returns the raw string, both \\text tails removed -> 3 -> A 1, value_format.
13  g '-\\frac{1}{3}', p '-1/3' -> _fix_a_slash_b -> '\\frac{-1}{3}' != '-\\frac{1}{3}' -> H 0; value -1/3 both -> A 1.
14  '(1,2)' vs '(1, 2)': spaces removed -> H 1, A 1.
15  no box, no 'answer is', no $..$ -> candidate '' -> H 0, A 0 (unboxed_none).
16  last $..$ 'x^2 = 4' -> '4' != '2' -> H 0, A 0.
17  '$$' -> '$', segment 'n = 6' -> '6' -> H 0, A 1, unboxed.
18  reference and output both without an answer -> H 1; A: no gold answer -> 0 (no_gold) -> both_none.
19  g '\\frac12' -> _fix_fracs -> '\\frac{1}{2}'; p '0.5' -> '\\frac{1}{2}' -> H 1, A 1.

FIX_VALUE: '2/4' -> _fix_a_slash_b -> '\\frac{2}{4}' -> 1/2; '\\$18.90' -> '18.90' -> 189/10; '0.50' stays -> 1/2;
'1,2' matches no number pattern -> None; '' -> None.
FIX_UNBOXED: the last 'answer is' wins (case-insensitive); '\\(' and '\\)' become '$'; '\\$' is dropped before
splitting on '$'.
FIX_RUNS: R1 and R2 share (a_x, algebra): R2's suite v1.8.0 is newer -> kept, 1 dropped; the gsm: run is ignored.
"""

import unittest

import cases91 as C
import grade91 as g


class TestGrade(unittest.TestCase):
    def test_grade_fixture(self):
        for gold, pred, h, a, route, cls in C.FIX_GRADE:
            r = g.grade(gold, pred)
            self.assertEqual((r["h"], r["a"], r["route"], g.flip_class(r)), (h, a, route, cls), (gold, pred))

    def test_helm_transcription_matches_its_docstrings(self):
        self.assertEqual(g.remove_boxed("\\boxed{\\frac{2}{3}}"), "\\frac{2}{3}")
        self.assertEqual(g._fix_fracs("\\frac1b"), "\\frac{1}{b}")
        self.assertEqual(g._fix_fracs("\\frac12"), "\\frac{1}{2}")
        self.assertEqual(g._fix_fracs("\\frac1{72}"), "\\frac{1}{72}")
        self.assertEqual(g._fix_a_slash_b("2/3"), "\\frac{2}{3}")
        self.assertEqual(g._fix_sqrt("\\sqrt3"), "\\sqrt{3}")
        self.assertEqual(g.is_equiv(None, None), 1.0)
        self.assertEqual(g.is_equiv("1", None), 0.0)

    def test_value(self):
        for s, w in C.FIX_VALUE:
            self.assertEqual(g.value(s), w, s)

    def test_unboxed(self):
        for pred, w in C.FIX_UNBOXED:
            self.assertEqual(g.unboxed_candidate(pred), w, pred)

    def test_runs(self):
        self.assertEqual(g.select_runs(C.FIX_RUNS, C.HELM_PREFIX), C.FIX_RUNS_TARGET)

    def test_ranks_tau(self):
        self.assertEqual(g.min_ranks(C.FIX_ACC), C.FIX_RANKS)
        for x, y, w in C.FIX_TAU:
            t = g.kendall_tau_b(x, y)
            if w is None:
                self.assertIsNone(t)
            else:
                self.assertAlmostEqual(t, w, places=12)

    def test_verdicts(self):
        for args, w in C.FIX_V_CASES:
            self.assertEqual(g.predictions91(*args, C.THRESHOLDS), w, args)


if __name__ == "__main__":
    unittest.main()
