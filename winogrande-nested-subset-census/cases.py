"""Hand-traced fixture for the WinoGrande nested-subset / gold-consistency census.

Two synthetic mini-splits A and B, in the exact raw WinoGrande jsonl shape, where A is meant to be
a nested subset of B. The census counts are worked out by hand in TARGET below, so the logic is
checked against a known answer before it ever touches the real data.

Each raw object is {"qID", "sentence", "option1", "option2", "answer"} with answer "1" or "2".
Identity is the normalized (sentence, option1, option2) triple; gold is the answer.

Split A (xs-like):
- q1 "The _ is blue"  sky/sea   ans 1
- q2 "The _ is green" grass/rock ans 1
- q3 "The _ is red"   rose/leaf  ans 1   (NOT carried into B -> a nesting violation)
  => rows 3, unique_qids 3, dup_qids 0, 3 distinct identities, multi 0, conflict 0.

Split B (s-like, should be a superset of A):
- q1 "The _ is blue"  sky/sea   ans 1    (shared with A, same answer)
- q2 "The _ is green" grass/rock ans 2    (shared with A but answer DIFFERS: A=1, B=2)
- q4 "The _ is blue"  sky/sea   ans 2    (same identity as q1, different gold -> within-B conflict)
- q5 "The _ is blue"  sky/sea   ans 1    (same identity as q1, same gold -> benign duplicate)
  => rows 4, unique_qids 4, dup_qids 0. Identities: {blue/sky/sea (q1,q4,q5), green/grass/rock (q2)}
     = 2 keys; blue key has answers {1,2,1} -> multi 1, conflict 1.

Nesting A->B (by qID): A {q1,q2,q3}, B {q1,q2,q4,q5}. shared {q1,q2} = 2;
qids only in A (missing from B) {q3} = 1; shared answer conflict: q2 (A=1, B=2) = 1.
"""


def _row(qid, sentence, opt1, opt2, answer):
    return {
        "qID": qid,
        "sentence": sentence,
        "option1": opt1,
        "option2": opt2,
        "answer": answer,
    }


FIXTURE_A = [
    _row("q1", "The _ is blue", "sky", "sea", "1"),
    _row("q2", "The _ is green", "grass", "rock", "1"),
    _row("q3", "The _ is red", "rose", "leaf", "1"),
]

FIXTURE_B = [
    _row("q1", "The _ is blue", "sky", "sea", "1"),
    _row("q2", "The _ is green", "grass", "rock", "2"),
    _row("q4", "The _ is blue", "sky", "sea", "2"),
    _row("q5", "The _ is blue", "sky", "sea", "1"),
]

NAMES = ["A", "B"]
PAIRS = ["A->B"]

TARGET = {
    "A_rows": 3,
    "A_unique_qids": 3,
    "A_duplicate_qids": 0,
    "A_unique_identity_keys": 3,
    "A_identity_keys_multi": 0,
    "A_identity_keys_conflict": 0,
    "B_rows": 4,
    "B_unique_qids": 4,
    "B_duplicate_qids": 0,
    "B_unique_identity_keys": 2,
    "B_identity_keys_multi": 1,
    "B_identity_keys_conflict": 1,
    "nest_A_B_shared_qids": 2,
    "nest_A_B_qids_only_in_smaller": 1,
    "nest_A_B_shared_answer_conflict": 1,
}
