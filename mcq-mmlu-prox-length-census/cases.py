"""Hand-traced fixtures, real-data configuration and pinned audit-63 numbers for audit 67. Apache-2.0."""

from fractions import Fraction

NA = "N/A"


def _x(qsrc, qid, options, answer_index, src):
    row = {"question_id_src": qsrc, "question_id": qid, "answer_index": answer_index, "src": src}
    padded = list(options) + [NA] * (10 - len(options))
    for j in range(10):
        row["option_%d" % j] = padded[j]
    return row


# ----- English (MMLU-Pro) fixture rows -----
# P10 lens [2,1,4], gold 2 is the unique longest: English credit 1, unique longest index 2.
# P11 lens [2,2,1,1], gold 0 tied longest with index 1: English credit 1/2, no unique longest.
# P12 lens [1,3,2], gold 0, unique longest index 1: English credit 0.
PRO_ROWS = [
    {"question_id": 10, "options": ["aa", "b", "cccc"], "answer_index": 2, "category": "biology",
     "src": "stemez-Biology"},
    {"question_id": 11, "options": ["xx", "yy", "z", "w"], "answer_index": 0, "category": "psychology",
     "src": "ori_mmlu-high_school_psychology"},
    {"question_id": 12, "options": ["p", "qqq", "rr"], "answer_index": 0, "category": "math",
     "src": "theoremQA-Math"},
]

# ----- Translated fixture rows (one language) -----
# X1 -> P10: lens [6,1,2], unique longest 0 (English 2: disagree), gold 2 credit 0.            ok
# X2 -> P11: lens [3,2,1,1], unique longest 0 = gold, credit 1; English has no unique longest.  ok
# X3 -> P12: lens [1,4,2], unique longest 1 (English 1: agree), gold 0 credit 0.               ok
# X4 -> id 13 is not in MMLU-Pro.                                                              no_id
# X5 -> P12 with answer_index 1 instead of 0.                                                  answer_differ
# X6 -> P11 (k = 4) with a real option in slot 4.                                              padding_differ
# X7 -> P10 again, identical to X1: joins, then skipped as a duplicate.                        ok (duplicate)
X_ROWS = [
    _x(10, 900, ["dddddd", "e", "ff"], 2, "stemez-Biology"),
    _x(11, 901, ["aaa", "bb", "c", "d"], 0, "ori_mmlu-high_school_psychology"),
    _x(12, 902, ["s", "tttt", "uu"], 0, "theoremQA-Math"),
    _x(13, 903, ["a", "b"], 0, "stemez-Biology"),
    _x(12, 904, ["s", "tttt", "uu"], 1, "theoremQA-Math"),
    _x(11, 905, ["aaa", "bb", "c", "d", "extra"], 0, "ori_mmlu-high_school_psychology"),
    _x(10, 906, ["dddddd", "e", "ff"], 2, "stemez-Biology"),
]

# Under question_id_src: 4 ok (one a duplicate), 1 no_id, 1 answer_differ, 1 padding_differ.
# Under question_id (900-906): nothing matches MMLU-Pro ids 10-12, so 7 no_id. Best key: question_id_src.
JOIN_TARGET = {
    "best": "question_id_src",
    "status": {"question_id_src": {"ok": 4, "no_id": 1, "answer_differ": 1, "padding_differ": 1},
               "question_id": {"no_id": 7}},
    "joined": 3,
    "duplicates": 1,
}

# ALL over X1-X3: n 3; pl 0 + 1 + 0 = 1; chance 1/3 + 1/4 + 1/3 = 11/12; English pl 1 + 1/2 + 0 = 3/2;
# English has a unique longest in P10 and P12 (den 2); the translation agrees only on P12 (1).
ACC_TARGETS = {
    "ALL": {"n": 3, "pl": Fraction(1), "chance": Fraction(11, 12), "en_pl": Fraction(3, 2), "ul_den": 2,
            "ul_agree": 1},
    "fam:stemez": {"n": 1, "pl": Fraction(0), "chance": Fraction(1, 3), "en_pl": Fraction(1), "ul_den": 1,
                   "ul_agree": 0},
    "sub:stemez-biopsy": {"n": 1, "pl": Fraction(0), "chance": Fraction(1, 3), "en_pl": Fraction(1), "ul_den": 1,
                          "ul_agree": 0},
    "fam:ori_mmlu": {"n": 1, "pl": Fraction(1), "chance": Fraction(1, 4), "en_pl": Fraction(1, 2), "ul_den": 0,
                     "ul_agree": 0},
    "sub:ori-biopsy": {"n": 1, "pl": Fraction(1), "chance": Fraction(1, 4), "en_pl": Fraction(1, 2), "ul_den": 0,
                       "ul_agree": 0},
    "fam:theoremQA": {"n": 1, "pl": Fraction(0), "chance": Fraction(1, 3), "en_pl": Fraction(0), "ul_den": 1,
                      "ul_agree": 1},
    "cat:biology": {"n": 1, "pl": Fraction(0), "chance": Fraction(1, 3), "en_pl": Fraction(1), "ul_den": 1,
                    "ul_agree": 0},
    "cat:psychology": {"n": 1, "pl": Fraction(1), "chance": Fraction(1, 4), "en_pl": Fraction(1, 2), "ul_den": 0,
                       "ul_agree": 0},
    "cat:math": {"n": 1, "pl": Fraction(0), "chance": Fraction(1, 3), "en_pl": Fraction(0), "ul_den": 1,
                 "ul_agree": 1},
}

# ALL report: pick_longest 1/3; chance 11/36; lift 1/36; English 1/2; English lift 7/36; retention 1/7; agreement 1/2.
# fam:theoremQA: English lift 0 - 1/3 = -1/3, lift -1/3, retention 1.
REPORT_TARGETS = {
    "ALL": {"n": 3, "pick_longest": 1 / 3, "chance": 11 / 36, "lift": 1 / 36, "en_pick_longest": 0.5,
            "en_lift": 7 / 36, "retention": 1 / 7, "ul_den": 2, "ul_agreement": 0.5},
    "fam:theoremQA": {"n": 1, "pick_longest": 0.0, "chance": 1 / 3, "lift": -1 / 3, "en_pick_longest": 0.0,
                      "en_lift": -1 / 3, "retention": 1.0, "ul_den": 1, "ul_agreement": 1.0},
}

# ----- Real-data configuration -----
MMLU_PRO = {
    "hf": "TIGER-Lab/MMLU-Pro",
    "config": "default",
    "splits": ["test"],
    "cols": ["question_id", "options", "answer_index", "category", "src"],
}

PROX = {
    "hf": "li-lab/MMLU-ProX",
    "split": "test",
    "cols": ["question_id", "question_id_src", "answer_index", "src"] + ["option_%d" % j for j in range(10)],
}

# The 29 configs listed by the datasets-server info endpoint on 2026-10-30 (read before any file was opened).
LANGS = ["af", "ar", "bn", "cs", "de", "en", "es", "fr", "hi", "hu", "id", "it", "ja", "ko", "mr", "ne", "pt", "ru",
         "sr", "sw", "te", "th", "uk", "ur", "vi", "wo", "yo", "zh", "zu"]

# Structural gate: copied from audit 63's results.json (mcq-mmlu-pro-source-length-census-v1), as in audit 66.
EXPECTED = {
    "n_valid": 12032,
    "family_n": {"ori_mmlu": 6810, "stemez": 4083, "scibench": 541, "theoremQA": 598},
    "src_pick_longest": {
        "stemez-Biology": (351, 0.6670736670736671),
        "stemez-Psychology": (305, 0.6700858704137392),
    },
}
