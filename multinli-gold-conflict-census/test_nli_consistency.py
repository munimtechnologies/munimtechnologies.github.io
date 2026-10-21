# SPDX-License-Identifier: Apache-2.0
# Part of MV2's eval-reliability audits (Munim, Inc.). Made with AI.
"""Unit tests gating the MultiNLI gold-label conflict census."""

import unittest

from cases import FIXTURE_ROWS, TARGET
from nli_consistency import analyze, normalize


class TestNormalize(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize("The sky is blue."), "the sky is blue")
        self.assertEqual(normalize("the sky is blue ."), "the sky is blue")
        self.assertEqual(normalize("  A   man  runs. "), "a man runs")
        self.assertEqual(normalize("No period here"), "no period here")


class TestAnalyze(unittest.TestCase):
    def test_target(self):
        got = analyze(FIXTURE_ROWS)
        for key, want in TARGET.items():
            self.assertEqual(got[key], want, key)

    def test_no_consensus_excluded(self):
        got = analyze([("p", "h", "-"), ("p", "h", "-")])
        self.assertEqual(got["rows_valid"], 0)
        self.assertEqual(got["distinct_exact_pairs"], 0)

    def test_conflict_detected(self):
        got = analyze([("p", "h", "entailment"), ("p", "h", "neutral")])
        self.assertEqual(got["exact_conflict_pairs"], 1)
        self.assertEqual(got["_exact_conflicts"][("p", "h")], ["entailment", "neutral"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
