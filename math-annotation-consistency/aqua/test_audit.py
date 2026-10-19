"""Unit tests for the v4 AQuA-RAT audit extractor.

Every case below is either a real rationale fragment from v3's genuine-error
catalogue that was found by hand to be an extraction artifact (and must now be
dropped or set aside), or a real internal arithmetic error that must still be
caught. Standard library only; run with `python -m unittest -v`.
"""

import unittest

import audit


def statuses(rationale):
    return [s["status"] for s in audit.audit_rationale(rationale)]


def oks(rationale):
    return [s for s in audit.audit_rationale(rationale) if s["status"] == "ok"]


def genuine(rationale):
    return [s for s in oks(rationale) if s["reldiff"] > 0.05]


class EvaluatorBasics(unittest.TestCase):
    def test_exact_step_kept(self):
        g = oks("area = 5*6 = 30")
        self.assertEqual(len(g), 1)
        self.assertTrue(g[0]["exact"])

    def test_precedence_respected_in_eval(self):
        v, nops = audit.eval_expr("36 * 5/18")
        self.assertEqual(v, 10)
        self.assertEqual(nops, 2)

    def test_division_before_multiplication_same_precedence(self):
        # left-to-right: 7*6*5/3*2 = 140 (NOT 35)
        v, _ = audit.eval_expr("7*6*5 / 3*2")
        self.assertEqual(v, 140)


class RatioArtifactsDropped(unittest.TestCase):
    def test_colon_ratio_three_way(self):
        # "1/14 = 2" is cut from the ratio 1/7:1/7:1/14 = 2:2:1 -> not an equation
        self.assertEqual(genuine("1/7:1/7:1/14 = 2:2:1"), [])

    def test_colon_ratio_second(self):
        self.assertEqual(genuine("1/4: 1/2: 1/1 = 2:4:8"), [])


class RadicalArtifactsDropped(unittest.TestCase):
    def test_stripped_sqrt(self):
        # sqrt(3)/4 * 16 * 16 = 64*sqrt(3); stripping the radical leaves 3/4*...=64
        self.assertEqual(genuine("Area = √3/4 * 16 * 16 = 64√3 cm2"), [])


class TimesLetterArtifactsDropped(unittest.TestCase):
    def test_x_as_times_splits_run(self):
        r = ("5358 x 51\t= 5358 x (50 + 1)\n= 5358 x 50 + 5358 x 1\n"
             "= 267900 + 5358\n= 273258.")
        # The only surviving audited step is the correct 267900+5358 = 273258.
        self.assertEqual(genuine(r), [])
        self.assertTrue(all(s["exact"] for s in oks(r)))


class PrecedenceAmbiguitySetAside(unittest.TestCase):
    def test_div_then_mult_is_ambiguous(self):
        sts = statuses("n(S) = 7*6*5 / 3*2 = 35")
        self.assertIn("ambiguous", sts)
        self.assertNotIn("ok", sts)

    def test_two_divisions_ambiguous(self):
        self.assertTrue(audit.has_ambiguous_precedence("12/3/2"))

    def test_mult_then_div_not_ambiguous(self):
        self.assertFalse(audit.has_ambiguous_precedence("36 * 5/18"))

    def test_parens_disambiguate(self):
        self.assertFalse(audit.has_ambiguous_precedence("(7*6*5)/(3*2)"))


class RealErrorsStillCaught(unittest.TestCase):
    def test_genuine_division_error_preserved(self):
        # 270/85 = 3.176..., not 4.15 -> a real internal error, with a unit after
        g = genuine("time = 270/85 = 4.15 hrs")
        self.assertEqual(len(g), 1)
        self.assertAlmostEqual(g[0]["leftval"], 270 / 85, places=6)

    def test_plain_wrong_sum(self):
        g = genuine("so 12 + 7 = 25 apples")
        self.assertEqual(len(g), 1)

    def test_unit_after_rhs_is_not_truncation(self):
        # 36*5/18 = 10 m/s is exact; the trailing unit must not drop it
        g = oks("speed = 36 * 5/18 = 10 m/s")
        self.assertEqual(len(g), 1)
        self.assertTrue(g[0]["exact"])


class PercentStillSetAside(unittest.TestCase):
    def test_percent_set_aside(self):
        self.assertIn("percent", statuses("20% * 50 = 10%"))


if __name__ == "__main__":
    unittest.main()
