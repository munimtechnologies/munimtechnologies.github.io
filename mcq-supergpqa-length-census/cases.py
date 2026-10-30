"""Hand-traced fixtures and real-data configuration for the SuperGPQA answer-length census (audit 64).

SuperGPQA (m-a-p/SuperGPQA; 26,529 questions, about 9.67 options each) wrote its distractors with LLM help and
reports that answers average 12.86 tokens against 12.64 for options overall, i.e. "confusing options in similar
lengths". A similar mean does not rule out a pick-the-longest shortcut (audit 62 found MMLU-Pro's added
distractors SHORTER on average while the shortcut still doubled), so audit 64 runs the exact length census.

Three fixtures are checked for exact equality before any real file is read:
- FIXTURE_ROWS / TARGET: the shared length-census core, reused VERBATIM from audits 52/60-63;
- SG_ROWS / SG_TARGET_*: SuperGPQA row conversion (answer_letter -> option index) and keys, hand-traced below;
- SG_QUALITY_TARGET and the position chi-square fixture.
Then the same pipeline must reproduce audit 61's pooled MMLU-Pro numbers exactly (structural gate).

Apache-2.0.
"""

from fractions import Fraction

# ----- Length-census core fixture (VERBATIM from audits 52/60-63) -----
# (key, labels, texts, answer_key) -- the generic census keys on the first element.
FIXTURE_ROWS = [
    # cs5: 5-option questions, chance 1/5
    ("cs5", ["A", "B", "C", "D", "E"], ["a", "bb", "ccc", "dddd", "eeeee"], "E"),  # gold 5 > {1,2,3,4} uniq long
    ("cs5", ["A", "B", "C", "D", "E"], ["xx", "xx", "xx", "xx", "x"], "E"),        # gold 1 < {2,2,2,2} uniq short

    # mc4: 4-option plus a 2-option row and two unusable rows
    ("mc4", ["0", "1", "2", "3"], ["qqqq", "r", "ss", "t"], "0"),                  # gold 4 > {1,2,1} uniq long
    ("mc4", ["0", "1", "2", "3"], ["aa", "bbbb", "cccc", "d"], "2"),               # gold 4 tied with 1; credit 1/2
    ("mc4", ["0", "1"], [" pp ", "qqqq"], "0"),                                    # gold strips to 2 < 4 uniq short
    ("mc4", ["0", "1", "2", "3"], ["a", "b", "c", "d"], "9"),                      # bad_key: "9" not a label
    ("mc4", ["0"], ["x"], "0"),                                                    # degenerate: single option
]

TARGET = {
    "cs5": {
        "n_valid": 2,
        "n_bad_key": 0,
        "n_degenerate": 0,
        "option_count_hist": {5: 2},
        "chance_sum": Fraction(2, 5),
        "char": {
            "n_valid": 2,
            "unique_longest": 1,
            "unique_shortest": 1,
            "sum_gold": 6,
            "sum_distractor": 18,
            "n_distractor": 8,
            "longest_credit": Fraction(1),
            "shortest_credit": Fraction(1),
        },
        "token": {
            "n_valid": 2,
            "unique_longest": 0,
            "unique_shortest": 0,
            "sum_gold": 2,
            "sum_distractor": 8,
            "n_distractor": 8,
            "longest_credit": Fraction(2, 5),
            "shortest_credit": Fraction(2, 5),
        },
    },
    "mc4": {
        "n_valid": 3,
        "n_bad_key": 1,
        "n_degenerate": 1,
        "option_count_hist": {4: 2, 2: 1},
        "chance_sum": Fraction(1),
        "char": {
            "n_valid": 3,
            "unique_longest": 1,
            "unique_shortest": 1,
            "sum_gold": 10,
            "sum_distractor": 15,
            "n_distractor": 7,
            "longest_credit": Fraction(3, 2),
            "shortest_credit": Fraction(1),
        },
        "token": {
            "n_valid": 3,
            "unique_longest": 0,
            "unique_shortest": 0,
            "sum_gold": 3,
            "sum_distractor": 7,
            "n_distractor": 7,
            "longest_credit": Fraction(1),
            "shortest_credit": Fraction(1),
        },
    },
}


# ----- SuperGPQA conversion fixture (new in audit 64) -----
# Digest = (n_valid, n_bad_key, chance_sum, char longest_credit).
SG_ROWS = [
    # S1 Engineering/easy/text: letter A -> 0; "aaa"=3 > 1, 2 -> credit 1, chance 1/3. Text matches.
    {"uuid": "s1", "discipline": "Engineering", "difficulty": "easy", "is_calculation": False,
     "options": ["aaa", "b", "cc"], "answer_letter": "A", "answer": "aaa"},
    # S2 Engineering/hard/calculation: letter B -> 1; "22"=2 ties "33"=2 -> credit 1/2, chance 1/3.
    {"uuid": "s2", "discipline": "Engineering", "difficulty": "hard", "is_calculation": True,
     "options": ["1", "22", "33"], "answer_letter": "B", "answer": "22"},
    # S3 Philosophy/easy/text: letter C -> 2, but only 2 options -> bad_key; letter out of range (mismatch).
    {"uuid": "s3", "discipline": "Philosophy", "difficulty": "easy", "is_calculation": False,
     "options": ["x", "y"], "answer_letter": "C", "answer": "z"},
    # S4 Philosophy/hard/text: letter A -> 0; " same " strips to 4, ties "same"=4, "longer"=6 is max -> credit 0,
    #    chance 1/3. Text matches after strip; the gold text is duplicated by option 1.
    {"uuid": "s4", "discipline": "Philosophy", "difficulty": "hard", "is_calculation": False,
     "options": [" same ", "same", "longer"], "answer_letter": "A", "answer": "same"},
    # S5 Philosophy/middle/unknown flag: letter B -> 1; "rr"=2 > 1 -> credit 1, chance 1/2. Answer text "RR"
    #    differs in case from the option -> letter/text mismatch (census still uses the letter).
    {"uuid": "s5", "discipline": "Philosophy", "difficulty": "middle", "is_calculation": None,
     "options": ["q", "rr"], "answer_letter": "B", "answer": "RR"},
]

SG_TARGET_DISCIPLINE = {
    "Engineering": (2, 0, Fraction(2, 3), Fraction(3, 2)),           # S1 + S2
    "Philosophy": (2, 1, Fraction(5, 6), Fraction(1)),               # S3 bad, S4 + S5
}

SG_TARGET_CALC = {
    "text": (2, 1, Fraction(2, 3), Fraction(1)),                     # S1 + S4 valid, S3 bad
    "calculation": (1, 0, Fraction(1, 3), Fraction(1, 2)),           # S2
    "unknown": (1, 0, Fraction(1, 2), Fraction(1)),                  # S5
}

SG_TARGET_DIFFICULTY = {
    "easy": (1, 1, Fraction(1, 3), Fraction(1)),                     # S1 valid, S3 bad
    "hard": (2, 0, Fraction(2, 3), Fraction(1, 2)),                  # S2 + S4
    "middle": (1, 0, Fraction(1, 2), Fraction(1)),                   # S5
}

SG_QUALITY_TARGET = {
    "n_rows": 5,
    "letter_unparseable": 0,
    "letter_out_of_range": 1,                                        # S3
    "letter_text_mismatch": 2,                                       # S3, S5
    "gold_duplicated": 1,                                            # S4
    "any_duplicate_options": 1,                                      # S4
}
SG_QUALITY_EXAMPLES = {"letter_text_mismatch": ["s3", "s5"], "gold_duplicated": ["s4"]}

# Position chi-square fixture: k=4, counts [3, 1, 1, 3], expected 2 each -> (1 + 1 + 1 + 1) / 2 = 2.
CHI_INDICES = [0, 0, 0, 1, 2, 3, 3, 3]
CHI_K = 4
CHI_TARGET = {"n": 8, "counts": [3, 1, 1, 3], "chi2": Fraction(2)}


# ----- Real-data configuration (HuggingFace datasets-server parquet API) -----
SUPERGPQA = {
    "hf": "m-a-p/SuperGPQA",
    "config": "default",
    "splits": ["train"],
    "cols": ["uuid", "options", "answer", "answer_letter", "discipline", "field", "difficulty", "is_calculation"],
}
PAPER_ROW_COUNT = 26529

MMLU_PRO = {
    "hf": "TIGER-Lab/MMLU-Pro",
    "config": "default",
    "splits": ["test"],
    "cols": ["options", "answer_index"],
}

# Structural gate, copied from the results.json of audit 61 (pooled MMLU-Pro).
EXPECTED_MMLU_PRO = {
    "n_valid": 12032,
    "unique_longest": 1655,
    "longest_accuracy": 0.18376805370862884,
}
