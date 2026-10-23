"""Hand-traced fixture for the SciQ support->answer lexical-leakage census.

Five synthetic SciQ-like rows. The census counts are worked out by hand in TARGET below, so the
counting logic is checked against a known answer before it touches real data.

Each object is {"question", "correct_answer", "distractor1", "distractor2", "distractor3", "support"}.
Gold = correct_answer. "In support" = normalized choice text is a non-empty substring of the normalized
support. A row with no "correct_answer" key is malformed. A valid row with empty support contributes to
n_empty_support and is excluded from the leak rates.

r1  gold "water"  distractors fire/earth/air  support "water is a liquid that flows"
    - with support; gold "water" in support -> gold_in_support
    - distractors: none of fire/earth/air in support -> 0 distractor hits
    - support == a choice? no
r2  gold "tree"  distractors rock/sand/clay  support "the sky is blue today"
    - with support; gold "tree" in support? no
    - distractors: none in support -> 0
    - support == a choice? no
r3  gold "sun"  distractors moon/star/cloud  support ""  (empty)
    - no support -> n_empty_support; distractors NOT counted
r4  gold "ice"  distractors steam/mist/fog  support "steam rises when ice melts then boils"
    - with support; gold "ice" in support -> gold_in_support
    - distractors: "steam" in support -> yes (1 hit, any_distractor); mist/fog no -> 1
    - support == a choice? no
r5  NO correct_answer key  support "whatever"  -> MALFORMED, excluded

Valid rows: r1, r2, r3, r4 (4). Malformed: r5 (1).
With support: r1, r2, r4 (3). Empty support: r3 (1).
- n_gold_in_support: r1, r4 = 2
- n_any_distractor_in_support: r4 = 1
- total_distractor_in_support: r4 contributes 1; others 0 -> 1
- n_distractors_total: 3 per with-support row -> 3*3 = 9
- n_support_eq_a_choice: 0
- gold_coverage_rate = 2/3 ; distractor_coverage_rate = 1/9 (gold > distractor)
"""


def _row(question, correct, distractors, support):
    """distractors is a 3-tuple of strings."""
    return {
        "question": question,
        "correct_answer": correct,
        "distractor1": distractors[0],
        "distractor2": distractors[1],
        "distractor3": distractors[2],
        "support": support,
    }


_R5 = {
    "question": "q5",
    "distractor1": "a",
    "distractor2": "b",
    "distractor3": "c",
    "support": "whatever",
}

FIXTURE = [
    _row("q1", "water", ("fire", "earth", "air"), "water is a liquid that flows"),
    _row("q2", "tree", ("rock", "sand", "clay"), "the sky is blue today"),
    _row("q3", "sun", ("moon", "star", "cloud"), ""),
    _row("q4", "ice", ("steam", "mist", "fog"), "steam rises when ice melts then boils"),
    _R5,
]

TARGET = {
    "n_valid": 4,
    "n_malformed": 1,
    "n_with_support": 3,
    "n_empty_support": 1,
    "n_gold_in_support": 2,
    "n_any_distractor_in_support": 1,
    "total_distractor_in_support": 1,
    "n_distractors_total": 9,
    "n_support_eq_a_choice": 0,
}
