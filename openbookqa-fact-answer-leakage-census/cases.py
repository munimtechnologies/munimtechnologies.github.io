"""Hand-traced fixture for the OpenBookQA fact->answer lexical-leakage census.

Five synthetic OpenBookQA-Additional-like rows in the raw jsonl shape. The census counts are worked
out by hand in TARGET below, so the counting logic is checked against a known answer before it touches
real data.

Each raw object is {"id", "question": {"stem", "choices": [{"text","label"}, ...]}, "answerKey",
"fact1"}. Gold = text of the choice whose label == answerKey. "In fact" = normalized choice text is a
non-empty substring of the normalized fact.

q1  choices A:"water" B:"fire"  key A (gold "water")  fact "water is wet and water flows"
    - gold "water" in fact -> gold_in_fact
    - distractor "fire" in fact? no -> 0 distractor hits
    - fact == a choice? no
q2  choices A:"rock" B:"tree"  key B (gold "tree")  fact "the sky is blue"
    - gold "tree" in fact? no
    - distractor "rock" in fact? no -> 0
    - fact == a choice? no
q3  choices A:"sun" B:"moon"  key A (gold "sun")  fact "sun"
    - gold "sun" in fact "sun" -> gold_in_fact
    - distractor "moon" in "sun"? no -> 0
    - fact == a choice? "sun" == choice A -> yes; and fact == gold -> yes
q4  choices 1:"a" 2:"b"  key "9"  fact "whatever"
    - answerKey "9" matches no label {1,2} -> MALFORMED, excluded
q5  choices A:"ice" B:"steam"  key A (gold "ice")  fact "steam rises from hot water"
    - gold "ice" in fact? no
    - distractor "steam" in fact -> yes -> 1 distractor hit (any_distractor)
    - fact == a choice? no

Valid rows: q1, q2, q3, q5 (4). Malformed: q4 (1).
- n_gold_in_fact: q1, q3 = 2
- n_any_distractor_in_fact: q5 = 1
- total_distractor_in_fact: q5 contributes 1; others 0 -> 1
- n_distractors_total: each valid row has 1 distractor -> 4
- n_fact_eq_a_choice: q3 = 1
- n_fact_eq_gold_choice: q3 = 1
- gold_coverage_rate = 2/4 = 0.5 ; distractor_coverage_rate = 1/4 = 0.25 (gold > distractor)
"""


def _row(id_, choices, answer_key, fact1):
    """choices is a list of (label, text) pairs."""
    return {
        "id": id_,
        "question": {"stem": id_, "choices": [{"text": t, "label": l} for l, t in choices]},
        "answerKey": answer_key,
        "fact1": fact1,
    }


FIXTURE = [
    _row("q1", [("A", "water"), ("B", "fire")], "A", "water is wet and water flows"),
    _row("q2", [("A", "rock"), ("B", "tree")], "B", "the sky is blue"),
    _row("q3", [("A", "sun"), ("B", "moon")], "A", "sun"),
    _row("q4", [("1", "a"), ("2", "b")], "9", "whatever"),
    _row("q5", [("A", "ice"), ("B", "steam")], "A", "steam rises from hot water"),
]

TARGET = {
    "n_valid": 4,
    "n_malformed": 1,
    "n_gold_in_fact": 2,
    "n_any_distractor_in_fact": 1,
    "total_distractor_in_fact": 1,
    "n_distractors_total": 4,
    "n_fact_eq_a_choice": 1,
    "n_fact_eq_gold_choice": 1,
}
