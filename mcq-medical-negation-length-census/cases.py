"""Hand-traced fixtures, real-data configuration and pinned audit-63 numbers for audit 68. Apache-2.0."""

from fractions import Fraction

# ----- Polarity / meta-option fixtures -----
POLARITY_CASES = [
    ("A 45-year-old man does not smoke. Which of the following is the most likely diagnosis?", "pos"),
    ("All of the following are true EXCEPT:", "neg"),
    ("Which drug isn't used in asthma?", "neg"),
    ("Which of the following is correct", "pos"),
    ("Nothing is known about the knot.", "pos"),
    ("Which is the least common site?", "neg"),
    ("", "pos"),
]

META_CASES = [
    ("All of the above", True),
    ("None", True),
    ("Both 1 and 2", True),
    ("Allopurinol", False),
    ("All patients with diabetes need insulin therapy daily", False),
    ("  neither a nor b. ", True),
]

# (options, gold, longest credit, shortest credit)
CREDIT_CASES = [
    (["aa", "b", "cccc"], 2, Fraction(1), Fraction(0)),
    (["xx", "yy", "z", "w"], 0, Fraction(1, 2), Fraction(0)),
    (["p", "qqq", "rr"], 0, Fraction(0), Fraction(1)),
    ([" a ", "b", "cc"], 1, Fraction(0), Fraction(1, 2)),
]

# ----- Accumulation fixture -----
# R1 pos s1 subject=A: lens [2,1,4], gold 2 unique longest -> pl 1, ps 0, chance 1/3, d 2/3.
# R2 neg s1 subject=A: lens [2,2,1,1], gold 0 tied longest -> pl 1/2, ps 0, chance 1/4, d 1/4; no unique longest.
# R3 neg s2 subject=B: lens [1,3,2,16], longest is the meta option -> pl 0, gold shortest -> ps 1, chance 1/4,
#                      d -1/4; has a meta option, so it is left out of nometa.
# R4 pos s2 subject=B: lens [3,2], gold 1 -> pl 0, ps 1, chance 1/2, d -1/2.
ROWS = [
    {"dataset": "toy", "split": "s1", "question": "Which is true?", "options": ["aa", "b", "cccc"], "gold": 2,
     "groups": ["subject=A"]},
    {"dataset": "toy", "split": "s1", "question": "All are true EXCEPT:", "options": ["xx", "yy", "z", "w"],
     "gold": 0, "groups": ["subject=A"]},
    {"dataset": "toy", "split": "s2", "question": "Which is not seen?", "options": ["p", "qqq", "rr",
                                                                                  "All of the above"],
     "gold": 0, "groups": ["subject=B"]},
    {"dataset": "toy", "split": "s2", "question": "Pick one.", "options": ["abc", "de"], "gold": 1,
     "groups": ["subject=B"]},
]


def _a(n, pl, ps, ch, d_sq, n_meta, n_ul, gold_ul):
    return {"n": n, "pl": pl, "ps": ps, "chance": ch, "d_sq": d_sq, "n_meta": n_meta, "n_ul": n_ul,
            "gold_ul": gold_ul}


F = Fraction
_R1 = _a(1, F(1), F(0), F(1, 3), F(4, 9), 0, 1, 1)
_R2 = _a(1, F(1, 2), F(0), F(1, 4), F(1, 16), 0, 0, 0)
_R3 = _a(1, F(0), F(1), F(1, 4), F(1, 16), 1, 1, 0)
_R4 = _a(1, F(0), F(1), F(1, 2), F(1, 4), 0, 1, 0)

ACC_TARGETS = {
    "toy|ALL": _a(4, F(3, 2), F(2), F(4, 3), F(59, 72), 1, 3, 1),
    "toy|pol=pos": _a(2, F(1), F(1), F(5, 6), F(25, 36), 0, 2, 1),
    "toy|pol=neg": _a(2, F(1, 2), F(1), F(1, 2), F(1, 8), 1, 1, 0),
    "toy|split=s1": _a(2, F(3, 2), F(0), F(7, 12), F(4, 9) + F(1, 16), 0, 1, 1),
    "toy|split=s2": _a(2, F(0), F(2), F(3, 4), F(1, 16) + F(1, 4), 1, 2, 0),
    "toy|split=s1|pol=pos": _R1,
    "toy|split=s1|pol=neg": _R2,
    "toy|split=s2|pol=neg": _R3,
    "toy|split=s2|pol=pos": _R4,
    "toy|nometa|pol=pos": _a(2, F(1), F(1), F(5, 6), F(25, 36), 0, 2, 1),
    "toy|nometa|pol=neg": _R2,
    "toy|subject=A": _a(2, F(3, 2), F(0), F(7, 12), F(4, 9) + F(1, 16), 0, 1, 1),
    "toy|subject=A|pol=pos": _R1,
    "toy|subject=A|pol=neg": _R2,
    "toy|subject=B": _a(2, F(0), F(2), F(3, 4), F(1, 16) + F(1, 4), 1, 2, 0),
    "toy|subject=B|pol=neg": _R3,
    "toy|subject=B|pol=pos": _R4,
}

# pos: lift 1/2 - 5/12 = 1/12; var (25/36 - 2/144) / 1 = 49/72; se sqrt(49/144) = 7/12.
# neg: lift 1/4 - 1/4 = 0; var 1/8; se 1/4. Contrast: -1/12 / sqrt(49/144 + 9/144) = -1/sqrt(58).
# ALL: pick_longest 3/8, pick_shortest 1/2, chance 1/3, lift 1/24, meta 1/4, unique longest 3/4, gold | ul 1/3;
#      var (59/72 - 4/576) / 3 = 13/48, se sqrt(13/192).
REPORT_TARGETS = {
    "toy|pol=pos": {"n": 2, "pick_longest": 0.5, "pick_shortest": 0.5, "chance": 5 / 12, "lift": 1 / 12,
                    "shortest_lift": 1 / 12, "ratio": 1.2, "se_lift": 7 / 12, "meta_share": 0.0,
                    "unique_longest_share": 1.0, "gold_given_unique_longest": 0.5},
    "toy|pol=neg": {"n": 2, "pick_longest": 0.25, "pick_shortest": 0.5, "chance": 0.25, "lift": 0.0,
                    "shortest_lift": 0.25, "ratio": 1.0, "se_lift": 0.25, "meta_share": 0.5,
                    "unique_longest_share": 0.5, "gold_given_unique_longest": 0.0},
    "toy|ALL": {"n": 4, "pick_longest": 0.375, "pick_shortest": 0.5, "chance": 1 / 3, "lift": 1 / 24,
                "shortest_lift": 1 / 6, "ratio": 1.125, "se_lift": (13 / 192) ** 0.5, "meta_share": 0.25, "unique_longest_share": 0.75,
                "gold_given_unique_longest": 1 / 3},
}
CONTRAST_Z = -1 / 58 ** 0.5

# ----- Real-data configuration -----
MMLU_PRO = {"hf": "TIGER-Lab/MMLU-Pro", "config": "default", "splits": ["test"],
            "cols": ["question_id", "question", "options", "answer_index", "category", "src"]}
MEDMCQA = {"hf": "openlifescienceai/medmcqa", "config": "default", "splits": ["train", "validation"],
           "cols": ["id", "question", "opa", "opb", "opc", "opd", "cop", "choice_type", "subject_name"]}
MEDQA = {"hf": "GBaker/MedQA-USMLE-4-options", "config": "default", "splits": ["train", "test"],
         "cols": ["question", "answer", "options", "answer_idx", "meta_info"]}

# Published split sizes (MedMCQA paper: train 182,822 / dev 4,183; MedQA paper, US 4-option: train 10,178 /
# test 1,273), also listed by the datasets-server size endpoint on 2026-10-30. Reported, not an abort gate.
EXPECTED_SIZES = {"medmcqa": {"train": 182822, "validation": 4183}, "medqa": {"train": 10178, "test": 1273}}

# Structural gate (aborts on mismatch): copied from audit 63's results.json, as in audits 66 and 67.
EXPECTED = {
    "n_valid": 12032,
    "family_n": {"ori_mmlu": 6810, "stemez": 4083, "scibench": 541, "theoremQA": 598},
    "src_pick_longest": {
        "stemez-Biology": (351, 0.6670736670736671),
        "stemez-Psychology": (305, 0.6700858704137392),
    },
}
