"""Hand-computed unit tests for the MathQA annotated_formula audit.

Every expected value here is computed by hand so the sandbox runner validates
the interpreter before the full-dataset pass. Standard library only.
"""

import math
import time
import unittest
from fractions import Fraction

import audit


class TestParseEval(unittest.TestCase):
    def _val(self, s):
        return audit.evaluate(audit.parse(s))

    def test_power_literal(self):
        v, ex = self._val("power(5, 4)")
        self.assertEqual(v, Fraction(625))
        self.assertTrue(ex)

    def test_nested_speed_example(self):
        # multiply(divide(multiply(48, const_1000), const_3600), 9)
        # 48*1000 = 48000; /3600 = 40/3; *9 = 120  (exact)
        v, ex = self._val("multiply(divide(multiply(48, const_1000), const_3600), 9)")
        self.assertEqual(v, Fraction(120))
        self.assertTrue(ex)

    def test_divide_is_exact_fraction(self):
        v, ex = self._val("divide(1, 3)")
        self.assertEqual(v, Fraction(1, 3))
        self.assertTrue(ex)

    def test_add_subtract_multiply(self):
        self.assertEqual(self._val("add(2, 3)")[0], Fraction(5))
        self.assertEqual(self._val("subtract(10, 4)")[0], Fraction(6))
        self.assertEqual(self._val("multiply(6, 7)")[0], Fraction(42))

    def test_negate_inverse(self):
        self.assertEqual(self._val("negate(5)")[0], Fraction(-5))
        self.assertEqual(self._val("inverse(4)")[0], Fraction(1, 4))

    def test_power_negative_exponent_exact(self):
        v, ex = self._val("power(2, negate(2))")
        self.assertEqual(v, Fraction(1, 4))
        self.assertTrue(ex)

    def test_power_fractional_exponent_is_float(self):
        v, ex = self._val("power(9, 0.5)")
        self.assertAlmostEqual(float(v), 3.0, places=9)
        self.assertFalse(ex)

    def test_sqrt_is_float(self):
        v, ex = self._val("sqrt(16)")
        self.assertAlmostEqual(float(v), 4.0, places=9)
        self.assertFalse(ex)

    def test_const_pi_inexact(self):
        v, ex = self._val("const_pi")
        self.assertFalse(ex)
        self.assertAlmostEqual(float(v), 3.141592653589793, places=9)

    def test_combinatorics_exact(self):
        self.assertEqual(self._val("factorial(5)")[0], Fraction(120))
        self.assertEqual(self._val("choose(5, 2)")[0], Fraction(10))
        self.assertEqual(self._val("permutation(5, 2)")[0], Fraction(20))

    def test_gcd_lcm_floor_reminder(self):
        self.assertEqual(self._val("gcd(12, 8)")[0], Fraction(4))
        self.assertEqual(self._val("lcm(4, 6)")[0], Fraction(12))
        self.assertEqual(self._val("floor(divide(7, 2))")[0], Fraction(3))
        self.assertEqual(self._val("reminder(17, 5)")[0], Fraction(2))

    def test_unsupported_op_raises(self):
        with self.assertRaises(audit.EvalError):
            self._val("sine(30)")

    def test_divide_by_zero_raises(self):
        with self.assertRaises(audit.EvalError):
            self._val("divide(1, 0)")

    def test_bare_n_reference_raises(self):
        # linear_formula style tokens must not silently evaluate
        with self.assertRaises(audit.EvalError):
            self._val("power(n1, n0)")

    def test_large_integer_power_is_exact_fraction(self):
        # power() with a big integer exponent stays exact-rational: this is the
        # kind of value that overflows float() and crashed v2 downstream. It is
        # well under the v4 magnitude cap (10^400 ~ 1329 bits), so it is still
        # evaluated exactly, not set aside.
        v, ex = self._val("power(10, 400)")
        self.assertIsInstance(v, Fraction)
        self.assertEqual(v, Fraction(10) ** 400)
        self.assertTrue(ex)

    def test_sqrt_of_over_range_fraction_no_overflow(self):
        # sqrt() of an over-range exact Fraction must not crash eval_op; it
        # returns an inexact (float) value (here inf), not OverflowError.
        v, ex = self._val("sqrt(power(10, 400))")
        self.assertFalse(ex)
        self.assertEqual(float(v), float("inf"))

    def test_fractional_power_of_over_range_fraction_no_overflow(self):
        v, ex = self._val("power(power(10, 400), 0.5)")
        self.assertFalse(ex)
        self.assertEqual(float(v), float("inf"))


class TestMagnitudeCap(unittest.TestCase):
    """v4: exact values whose construction would blow up (the v3 timeout, exit
    124) must raise EvalError FAST, so job.py marks the problem 'unevaluable'
    instead of hanging. Each test asserts both the error and that it returns in
    well under a second (the giant integer is never built)."""

    def _val(self, s):
        return audit.evaluate(audit.parse(s))

    def _assert_fast_evalerror(self, s, max_seconds=1.0):
        t0 = time.perf_counter()
        with self.assertRaises(audit.EvalError):
            self._val(s)
        self.assertLess(time.perf_counter() - t0, max_seconds)

    def test_power_tower_unevaluable_fast(self):
        # power(power(10,400),400) ~ 10^160000: outer est ~531600 bits > cap, so
        # the giant integer is never constructed. (This is the v3 timeout shape.)
        self._assert_fast_evalerror("power(power(10, 400), 400)")

    def test_deeper_power_tower_unevaluable_fast(self):
        self._assert_fast_evalerror("power(power(power(10, 400), 400), 2)")

    def test_large_factorial_unevaluable_fast(self):
        # factorial(100000) ~ 1.5M bits: rejected by n > MAX_VALUE_BITS.
        self._assert_fast_evalerror("factorial(100000)")

    def test_factorial_of_over_range_operand_fast(self):
        # factorial(power(10,400)): operand is a 10^400 int; the pure-int
        # short-circuit rejects it before lgamma sees an over-range float.
        self._assert_fast_evalerror("factorial(power(10, 400))")

    def test_large_choose_unevaluable_fast(self):
        # choose(power(10,400), power(10,200)): a beyond float range -> rejected
        # before math.comb runs O(min(b,a-b)) big-int multiplies (would hang).
        self._assert_fast_evalerror("choose(power(10, 400), power(10, 200))")

    def test_large_permutation_unevaluable_fast(self):
        self._assert_fast_evalerror("permutation(power(10, 400), power(10, 200))")

    def test_moderate_factorial_still_exact(self):
        # factorial(1000) ~ 8530 bits is under the cap: still evaluated exactly.
        v, ex = self._val("factorial(1000)")
        self.assertTrue(ex)
        self.assertEqual(v, Fraction(math.factorial(1000)))

    def test_moderate_choose_still_exact(self):
        # C(1000,500) ~ 996 bits is under the cap.
        v, ex = self._val("choose(1000, 500)")
        self.assertTrue(ex)
        self.assertEqual(v, Fraction(math.comb(1000, 500)))

    def test_power_just_under_cap_still_exact(self):
        # power(2, 60000) ~ 60000 bits < 65536 cap: still exact, built fast.
        v, ex = self._val("power(2, 60000)")
        self.assertTrue(ex)
        self.assertEqual(v, Fraction(2) ** 60000)

    def test_guarded_multiply_over_cap_fast(self):
        # Two under-cap powers multiplied past the cap must raise (guard on the
        # product), not silently return a 2x-cap giant.
        self._assert_fast_evalerror("multiply(power(2, 60000), power(2, 60000))")


class TestConstants(unittest.TestCase):
    def test_integer_const(self):
        self.assertEqual(audit.eval_const("const_100"), (Fraction(100), True))

    def test_decimal_const(self):
        v, ex = audit.eval_const("const_3_6")
        self.assertEqual(v, Fraction(18, 5))  # 3.6
        self.assertTrue(ex)

    def test_small_decimal_const(self):
        v, ex = audit.eval_const("const_0_2778")
        self.assertEqual(v, Fraction(2778, 10000))
        self.assertTrue(ex)

    def test_deg_to_rad_inexact(self):
        v, ex = audit.eval_const("const_deg_to_rad")
        self.assertFalse(ex)


class TestPureSubset(unittest.TestCase):
    def test_pure(self):
        self.assertTrue(audit.is_pure_exact_arithmetic(audit.parse("divide(add(2, 3), 4)")))

    def test_impure_const(self):
        self.assertFalse(audit.is_pure_exact_arithmetic(audit.parse("multiply(2, const_100)")))

    def test_impure_sqrt(self):
        self.assertFalse(audit.is_pure_exact_arithmetic(audit.parse("sqrt(16)")))


class TestOptionParsing(unittest.TestCase):
    def test_basic(self):
        opts = audit.parse_options("a ) 24 , b ) 120 , c ) 625 , d ) 720 , e ) 1024")
        self.assertEqual(opts["c"], "625")
        self.assertEqual(audit.parse_option_value(opts["c"])[0], Fraction(625))

    def test_fraction_option(self):
        self.assertEqual(audit.parse_option_value("3 / 4")[0], Fraction(3, 4))

    def test_units_option(self):
        self.assertEqual(audit.parse_option_value("500 kmph")[0], Fraction(500))

    def test_currency_option(self):
        self.assertEqual(audit.parse_option_value("Rs. 200")[0], Fraction(200))

    def test_percent_option(self):
        self.assertEqual(audit.parse_option_value("20 %")[0], Fraction(20))

    def test_thousands_comma_inside_option(self):
        opts = audit.parse_options("a ) 1,024 , b ) 2,048")
        self.assertEqual(audit.parse_option_value(opts["a"])[0], Fraction(1024))

    def test_decimal_option(self):
        self.assertEqual(audit.parse_option_value("12.5")[0], Fraction(25, 2))

    def test_non_numeric_option_raises(self):
        with self.assertRaises(audit.EvalError):
            audit.parse_option_value("none of the above")

    def test_two_numbers_option_raises(self):
        with self.assertRaises(audit.EvalError):
            audit.parse_option_value("between 10 and 20")

    def test_fraction_with_embedded_letters_no_crash(self):
        # v1 regression: a letter/unit between a digit and the slash made the
        # raw-text slash search return None while the stripped token still looked
        # like a fraction -> AttributeError on .group(). Must now parse cleanly.
        self.assertEqual(audit.parse_option_value("2nd/3")[0], Fraction(2, 3))
        self.assertEqual(audit.parse_option_value("rs 3 / 5")[0], Fraction(3, 5))

    def test_fraction_zero_denominator_raises(self):
        with self.assertRaises(audit.EvalError):
            audit.parse_option_value("3 / 0")


class TestMatch(unittest.TestCase):
    def test_exact(self):
        self.assertTrue(audit.rel_match(Fraction(625), Fraction(625), 0))
        self.assertFalse(audit.rel_match(Fraction(120), Fraction(625), 0))

    def test_tolerance(self):
        self.assertTrue(audit.rel_match(100.4, 100.0, 0.05))
        self.assertFalse(audit.rel_match(110.0, 100.0, 0.05))

    def test_tolerance_rational_path(self):
        # Both operands Fraction + tol>0 takes the exact-rational branch.
        self.assertTrue(audit.rel_match(Fraction(1004, 10), Fraction(100), 0.05))
        self.assertFalse(audit.rel_match(Fraction(110), Fraction(100), 0.05))

    def test_huge_fraction_no_overflow(self):
        # Regression (v2 crash): an exact Fraction too large to convert to float
        # (power(10, 400) ~ 1e400 overflows IEEE-754) must be compared in
        # rational space, not crash rel_match with OverflowError on float().
        huge = Fraction(10) ** 400
        self.assertTrue(audit.rel_match(huge, huge, 0))      # exact self-match
        self.assertTrue(audit.rel_match(huge, huge, 0.05))   # tol, rational path
        self.assertFalse(audit.rel_match(huge, Fraction(100), 0))
        self.assertFalse(audit.rel_match(huge, Fraction(100), 0.05))

    def test_huge_fraction_vs_float_no_overflow(self):
        # Mixed rational/float path must also survive an over-range operand.
        huge = Fraction(10) ** 400
        # float operand forces the _to_float_safe path; must not raise.
        self.assertFalse(audit.rel_match(huge, 3.14159, 0.05))


if __name__ == "__main__":
    unittest.main()
