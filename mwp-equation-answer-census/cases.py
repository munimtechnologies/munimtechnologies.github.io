# Pre-registered synthetic corpus for the mwp-equation-answer-census audit.
#
# These cases pin the behaviour of the two evaluators (infix + prefix) and the
# three verdicts (match / mismatch / unevaluable) BEFORE any real dataset is
# touched. Each verdict was hand-traced against mwp_eval.py; the sealed job
# re-derives the aggregate and asserts it equals the pre-registered target.
#
# Labelled corpus by AI agents working in MV2's name (Munim, Inc.). CC BY 4.0.

# id, notation, equation, numbers, answer, expected_verdict, note
CASES = [
    ("S1-infix-match", "infix", "( 76.0 - 25.0 )", [], 51.0, "match",
     "SVAMP-style infix subtraction; evaluates to the annotated answer."),
    ("S2-infix-nested-match", "infix", "( ( 3.0 + 4.0 ) * 2.0 )", [], 14.0, "match",
     "Nested infix; (3+4)*2 = 14 matches."),
    ("S3-infix-mismatch", "infix", "( 2.0 + 2.0 )", [], 5.0, "mismatch",
     "Equation evaluates to 4 but the annotated answer is 5 -> inconsistency."),
    ("S4-infix-div-match", "infix", "( 10.0 / 4.0 )", [], 2.5, "match",
     "Division; 10/4 = 2.5 matches."),
    ("P1-prefix-match", "prefix", "- number0 number1", [18.0, 10.0], 8.0, "match",
     "ASDiv/MAWPS-style prefix; 18-10 = 8 matches."),
    ("P2-prefix-order-match", "prefix", "- number1 number0", [11.0, 12.0], 1.0, "match",
     "Operand order: number1-number0 = 12-11 = 1 matches."),
    ("P3-prefix-mul-match", "prefix", "* number0 number1", [3.0, 4.0], 12.0, "match",
     "3*4 = 12 matches."),
    ("P4-prefix-mismatch", "prefix", "+ number0 number1", [2.0, 3.0], 6.0, "mismatch",
     "2+3 = 5 but the annotated answer is 6 -> inconsistency."),
    ("P5-prefix-divzero-unevaluable", "prefix", "/ number0 number1", [5.0, 0.0], 2.0,
     "unevaluable", "Division by zero -> cannot be evaluated; not counted as a mismatch."),
    ("P6-prefix-literal-match", "prefix", "* number0 2", [5.0], 10.0, "match",
     "Literal constant token alongside a number slot; 5*2 = 10 matches."),
]

TARGET = {
    "n_cases": 10,
    "n_match": 7,
    "n_mismatch": 2,
    "n_unevaluable": 1,
    "all_reproduced": True,
}
