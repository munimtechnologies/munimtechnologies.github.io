"""Hand-traced fixture for the QASC composition->answer lexical-leakage census.

Five synthetic QASC-like rows (nested shape). The census counts are worked out by hand in TARGET
below, so the counting logic is checked against a known answer before it touches real data. The fixture
rows use three choices each; real QASC is 8-way, but the logic is choice-count-agnostic.

Gold = the choice whose label == answerKey. "In field" = normalized gold text is a non-empty substring
of the normalized fact field. A row with no answerKey is unannotated (like the public test split) and
skipped. An annotated row whose answerKey matches no choice is malformed and excluded.

r1  gold "wind"  distractors sun/rain
    fact1 "turbines turn wind into motion" -> gold in fact1 (yes); distractors in fact1: 0
    fact2 "motion can make electricity"    -> gold in fact2 (no);  distractors in fact2: 0
    combined "wind can make electricity"   -> gold in combined (yes); distractors in combined: 0
    in either single fact: yes (fact1). in combined but NOT single: no.
r2  gold "ice"  distractors steam/fog
    fact1 "cold freezes water"             -> gold (no); distractors: 0
    fact2 "frozen water is solid"          -> gold (no); distractors: 0
    combined "ice forms when water freezes"-> gold (yes); distractors: 0
    in either single fact: NO. in combined but NOT single: YES  (composition-only leak -> example)
r3  gold "sun"  distractors moon/star
    fact1 "the sun is a star"              -> gold (yes); distractor "star" in fact1 -> 1
    fact2 "stars give light"               -> gold (no);  distractor "star" in "stars" -> 1
    combined "the sun gives light"         -> gold (yes); distractors: 0
    in either single fact: yes (fact1). in combined but NOT single: no.
r4  NO answerKey -> unannotated, skipped
r5  answerKey "Z" matches no choice -> malformed, excluded

Valid rows: r1, r2, r3 (3). Unannotated: r4 (1). Malformed: r5 (1).
n_distractors_total = 2+2+2 = 6
gold_in_fact1 = r1,r3 = 2 ; gold_in_fact2 = 0 ; gold_in_combinedfact = r1,r2,r3 = 3
dist_in_fact1 = r3 = 1 ; dist_in_fact2 = r3 = 1 ; dist_in_combinedfact = 0
n_gold_in_either_single = r1,r3 = 2 ; n_gold_in_combined_not_single = r2 = 1
gold_rate_combinedfact = 3/3 = 1.0 > gold_rate_fact1 = 2/3 > gold_rate_fact2 = 0
dist_rate_combinedfact = 0/6 = 0
"""


def _row(stem, labels_texts, answer_key, fact1, fact2, combinedfact):
    choices = [{"text": t, "label": l} for (l, t) in labels_texts]
    row = {"question": {"stem": stem, "choices": choices},
           "fact1": fact1, "fact2": fact2, "combinedfact": combinedfact}
    if answer_key is not None:
        row["answerKey"] = answer_key
    return row


FIXTURE = [
    _row("q1", [("A", "wind"), ("B", "sun"), ("C", "rain")], "A",
         "turbines turn wind into motion", "motion can make electricity",
         "wind can make electricity"),
    _row("q2", [("A", "ice"), ("B", "steam"), ("C", "fog")], "A",
         "cold freezes water", "frozen water is solid",
         "ice forms when water freezes"),
    _row("q3", [("A", "sun"), ("B", "moon"), ("C", "star")], "A",
         "the sun is a star", "stars give light",
         "the sun gives light"),
    _row("q4", [("A", "a"), ("B", "b"), ("C", "c")], None,
         "f1", "f2", "cf"),
    _row("q5", [("A", "a"), ("B", "b"), ("C", "c")], "Z",
         "f1", "f2", "cf"),
]

TARGET = {
    "n_valid": 3,
    "n_unannotated": 1,
    "n_malformed": 1,
    "n_distractors_total": 6,
    "gold_in_fact1": 2,
    "gold_in_fact2": 0,
    "gold_in_combinedfact": 3,
    "dist_in_fact1": 1,
    "dist_in_fact2": 1,
    "dist_in_combinedfact": 0,
    "n_gold_in_either_single": 2,
    "n_gold_in_combined_not_single": 1,
}
