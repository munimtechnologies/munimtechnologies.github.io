# SPDX-License-Identifier: Apache-2.0
# Part of MV2's eval-reliability audits (Munim, Inc.). Made with AI.
"""Pre-registered fixtures for the GSM8K calculator-annotation census.

These are fixed BEFORE any dataset row is read. The census is only trusted if
the evaluator reproduces every per-case label and the aggregate TARGET exactly.
"""

# (expression, stated_result, expected_label)
ANNOTATION_CASES = [
    ("48/2", "24", "match"),      # exact integer division
    ("3*4", "12", "match"),       # exact product
    ("10+5", "15", "match"),      # exact sum
    ("100-1", "99", "match"),     # exact difference
    (".5*10", "5", "match"),      # leading-dot literal, exact
    ("2/3", "0.67", "rounded"),   # 0.6666... shown to 2 places -> rounded, not error
    ("5+5", "11", "mismatch"),    # true 10, stated 11 -> genuine mismatch
    ("sqrt(4)", "2", "unparseable_expr"),  # a call -> outside the whitelist
]

# Aggregate over ANNOTATION_CASES: 5 match, 1 rounded, 1 mismatch, 1 unparseable.
TARGET = {"match": 5, "mismatch": 1, "rounded": 1, "unparseable_expr": 1}

# (answer_text, expected_has_annotation, expected_final_matches_last)
SOLUTION_CASES = [
    ("Half of 48 is <<48/2=24>> and one more makes <<24+1=25>>.\n#### 25", True, True),
    ("Doubling ten gives <<10*2=20>>.\n#### 21", True, False),
    ("No arithmetic is needed here, just reasoning.\n#### 7", False, None),
]
