# SPDX-License-Identifier: Apache-2.0
# Part of MV2's eval-reliability audits (Munim, Inc.). Made with AI.
"""Pre-registered fixtures for the NLI gold-label conflict census.

Fixed BEFORE any dataset row is read. The census is trusted only if analyze()
reproduces TARGET exactly on these synthetic rows.
"""

# (premise, hypothesis, gold_label)
FIXTURE_ROWS = [
    # Exact-duplicate pair with CONFLICTING gold labels -> exact + norm conflict.
    ("A man runs.", "A person moves.", "entailment"),
    ("A man runs.", "A person moves.", "contradiction"),
    # Exact-duplicate pair with the SAME label -> a duplicate, but NOT a conflict.
    ("A dog sleeps.", "An animal rests.", "entailment"),
    ("A dog sleeps.", "An animal rests.", "entailment"),
    # Same pair under normalization only (case / spacing / trailing period) with
    # conflicting labels -> a norm conflict but NOT an exact conflict.
    ("The sky is blue.", "It is daytime.", "neutral"),
    ("the sky is blue .", "it is daytime .", "contradiction"),
    # No-consensus row -> excluded entirely.
    ("A kid plays.", "A child is happy.", "-"),
]

TARGET = {
    "rows_valid": 6,            # 7 rows minus the one '-' row
    "distinct_exact_pairs": 4,  # man/person, dog/animal, sky(exact), sky(spaced)
    "exact_conflict_pairs": 1,  # man/person only
    "duplicate_exact_pairs": 2, # man/person and dog/animal each occur twice
    "distinct_norm_pairs": 3,   # man/person, dog/animal, sky (both collapse)
    "norm_conflict_pairs": 2,   # man/person and sky
}
