"""Unit tests for audit 72 (stdlib only). Every expected value was traced by hand. Apache-2.0."""

import unittest

import align as al
import cases


class TestOneRow(unittest.TestCase):
    def test_digit_runs(self):
        self.assertEqual(al.digit_runs("Born 1955年, page 12, ٢٠٢٠"), ["1955", "2020"])   # Arabic-Indic 2020
        self.assertEqual(al.digit_runs("１９５５"), ["1955"])                               # full-width, NFKC
        self.assertEqual(al.digit_runs("1,000 and 0042"), ["0", "42"])
        self.assertEqual(al.digit_runs("12 and 99"), [])
        self.assertEqual(al.digit_runs(None), [])

    def test_fingerprint(self):
        self.assertEqual(al.fingerprint("q 1955", ["x 1450", "1955", "", None]), ("1450", "1955"))
        self.assertEqual(al.fingerprint("no digits", ["a", "b"]), ())

    def test_key_and_index(self):
        self.assertEqual(al.key_index(" b "), 1)
        self.assertIsNone(al.key_index("E"))
        self.assertIsNone(al.key_index(None))
        self.assertEqual(al.index_of("high_school_world_history/test/17"), 17)
        self.assertIsNone(al.index_of("abc"))
        self.assertIsNone(al.index_of("a/test/x"))


class TestAlign(unittest.TestCase):
    def test_fixture_mapping(self):
        mapping, st = al.align(cases.FIXTURE_EN, cases.FIXTURE_XX)
        self.assertEqual(mapping, cases.FIXTURE_MAPPING)
        self.assertEqual(st["mapped"] + st["no_fingerprint"] + st["count_differs"], st["n"])

    def test_identity(self):
        mapping, st = al.align(cases.FIXTURE_EN, cases.FIXTURE_EN)
        self.assertEqual(st["misaligned"], 0)
        self.assertEqual(st["aligned"], 6)
        self.assertTrue(all(k == v for k, v in mapping.items()))

    def test_fixture_report(self):
        rep, mapping = al.compare_subject(cases.FIXTURE_EN, cases.FIXTURE_XX)
        self.assertEqual(rep, cases.FIXTURE_REPORT)
        self.assertEqual(mapping, cases.FIXTURE_MAPPING)

    def test_content_agreement(self):
        self.assertEqual(al.content_agreement(cases.FIXTURE_MAPPING, cases.FIXTURE_MAP_B), cases.FIXTURE_AGREEMENT)

    def test_lite(self):
        got = al.lite_compare(cases.FIXTURE_LITE_ROWS, cases.FIXTURE_LITE_FULL, cases.FIXTURE_LITE_EN,
                              cases.FIXTURE_LITE_MISALIGNED)
        self.assertEqual(got, cases.FIXTURE_LITE)


if __name__ == "__main__":
    unittest.main()
