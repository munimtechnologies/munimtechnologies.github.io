"""Hand-traced fixture for the OpenBookQA Main-vs-Additional consistency census.

Two synthetic mini-files (Main and Additional) in the exact raw OpenBookQA jsonl shape, whose
census counts are worked out by hand in TARGET below, so the census logic is checked against a
known answer before it ever touches the real data.

Each raw object is {"id", "question": {"stem", "choices": [{"text","label"}]}, "answerKey"}.
The identity of a question is (normalized stem, sorted normalized choice-texts); the gold is the
TEXT of the choice whose label == answerKey. All rows are in split "train".

Reasoning (Main):
- id 1  "Sky color?"  A=blue B=green  key A -> gold blue
- id 2  "Grass color?" A=blue B=green key B -> gold green
- id 3  "Sky color?"  A=blue B=green  key A -> gold blue   (same question as id 1, same gold)
- id 4  "Water state?" A=ice B=steam  key A -> gold ice
- id 5  "Grass color?" A=blue B=green key A -> gold blue    (same question as id 2, gold DIFFERS
                                                             -> within-Main gold conflict)
- id 6  "Dog sound?"  A=bark B=meow  key A -> gold bark     (only in Main)
  => rows 6, malformed 0, unique_ids 6, duplicate_ids 0, identity keys {sky, grass, water, dog}
     = 4, multi {sky(2 rows), grass(2 rows)} = 2, conflict {grass} = 1.

Reasoning (Additional):
- id 1 key A -> blue ; id 2 key B -> green ; id 3 key A -> blue ; id 5 key A -> blue
- id 4 key B -> steam  (DISAGREES with Main's id 4, which is key A -> ice)
- id 7  "Cat legs?" A=four B=two key A -> gold four  (only in Additional)
  => rows 6, malformed 0, unique_ids 6, duplicate_ids 0, identity keys {sky, grass, water, cat}
     = 4, multi {sky, grass} = 2, conflict {grass} = 1.

Cross-file (split train): shared ids {1,2,3,4,5} = 5; answer-key agree on 1,2,3,5 = 4,
disagree on 4 = 1; answer-text disagree on 4 (ice vs steam) = 1; only in Main {6} = 1;
only in Additional {7} = 1.
"""


def _row(qid, stem, a, b, key):
    return {
        "id": qid,
        "question": {"stem": stem, "choices": [
            {"text": a, "label": "A"}, {"text": b, "label": "B"},
        ]},
        "answerKey": key,
    }


FIXTURE_MAIN = [
    (_row("1", "Sky color?", "blue", "green", "A"), "train"),
    (_row("2", "Grass color?", "blue", "green", "B"), "train"),
    (_row("3", "Sky color?", "blue", "green", "A"), "train"),
    (_row("4", "Water state?", "ice", "steam", "A"), "train"),
    (_row("5", "Grass color?", "blue", "green", "A"), "train"),
    (_row("6", "Dog sound?", "bark", "meow", "A"), "train"),
]

FIXTURE_ADDITIONAL = [
    (_row("1", "Sky color?", "blue", "green", "A"), "train"),
    (_row("2", "Grass color?", "blue", "green", "B"), "train"),
    (_row("3", "Sky color?", "blue", "green", "A"), "train"),
    (_row("4", "Water state?", "ice", "steam", "B"), "train"),
    (_row("5", "Grass color?", "blue", "green", "A"), "train"),
    (_row("7", "Cat legs?", "four", "two", "A"), "train"),
]

TARGET = {
    "main_rows": 6,
    "main_malformed": 0,
    "main_unique_ids": 6,
    "main_duplicate_ids": 0,
    "main_unique_identity_keys": 4,
    "main_identity_keys_multi": 2,
    "main_identity_keys_conflict": 1,
    "additional_rows": 6,
    "additional_malformed": 0,
    "additional_unique_ids": 6,
    "additional_duplicate_ids": 0,
    "additional_unique_identity_keys": 4,
    "additional_identity_keys_multi": 2,
    "additional_identity_keys_conflict": 1,
    "crossfile_shared_ids": 5,
    "crossfile_answerkey_agree": 4,
    "crossfile_answerkey_disagree": 1,
    "crossfile_answer_text_disagree": 1,
    "crossfile_ids_only_in_main": 1,
    "crossfile_ids_only_in_additional": 1,
}
