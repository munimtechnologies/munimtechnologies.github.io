"""Hand-traced fixture for the ARC disjointness / leakage / gold-conflict census.

Two synthetic mini-splits X and Y in the raw ARC jsonl shape. The census counts are worked out by
hand in TARGET below, so the logic is checked against a known answer before it touches real data.

Each raw object is {"id", "question": {"stem", "choices": [{"text", "label"}, ...]}, "answerKey"}.
Identity = (normalized stem, frozenset of normalized choice texts); gold = text of the choice whose
label == answerKey.

Split X (easy-like, 4 rows):
- x1  stem S1  A:aa B:bb  key A -> identity (s1,{aa,bb}), gold aa
- x2  stem S2  A:cc B:dd  key B -> identity (s2,{cc,dd}), gold dd
- x3  stem S1  A:aa B:bb  key B -> identity (s1,{aa,bb}), gold bb  (same identity as x1, gold DIFFERS
                                                                    -> within-X gold conflict)
- x4  stem S2  1:cc 2:dd  key 3 -> answerKey "3" matches no label {1,2} -> malformed, excluded
  => rows 4, malformed 1, unique_ids 4, dup_ids 0. Non-malformed identities:
     (s1,{aa,bb}) golds [aa,bb] -> multi, conflict; (s2,{cc,dd}) golds [dd] -> single.
     => unique_identity_keys 2, identity_keys_multi 1, identity_keys_conflict 1.

Split Y (challenge-like, 3 rows):
- y1  stem S9  A:pp B:qq  key A -> identity (s9,{pp,qq}), gold pp
- x1  stem S1  A:aa B:bb  key A -> identity (s1,{aa,bb}), gold aa  (SAME id x1 as in X; shared id and
                                                                    shared identity across X and Y)
- y3  stem S2  A:cc B:dd  key B -> identity (s2,{cc,dd}), gold dd  (shared identity with X, same gold)
  => rows 3, malformed 0, unique_ids 3, dup_ids 0; 3 distinct identities, multi 0, conflict 0.

Overlap X|Y:
- ids: X {x1,x2,x3,x4}, Y {y1,x1,y3} -> shared {x1} = 1.
- identities (non-malformed): X {(s1,{aa,bb}),(s2,{cc,dd})}, Y {(s9,..),(s1,..),(s2,..)}
  -> shared {(s1,{aa,bb}),(s2,{cc,dd})} = 2.
- shared-identity gold conflict: (s1,{aa,bb}) golds X{aa,bb} | Y{aa} = {aa,bb} -> conflict;
  (s2,{cc,dd}) golds X{dd} | Y{dd} = {dd} -> no. => 1.
"""


def _row(id_, stem, choices, answer_key):
    """choices is a list of (label, text) pairs."""
    return {
        "id": id_,
        "question": {"stem": stem, "choices": [{"text": t, "label": l} for l, t in choices]},
        "answerKey": answer_key,
    }


FIXTURE_X = [
    _row("x1", "S1", [("A", "aa"), ("B", "bb")], "A"),
    _row("x2", "S2", [("A", "cc"), ("B", "dd")], "B"),
    _row("x3", "S1", [("A", "aa"), ("B", "bb")], "B"),
    _row("x4", "S2", [("1", "cc"), ("2", "dd")], "3"),
]

FIXTURE_Y = [
    _row("y1", "S9", [("A", "pp"), ("B", "qq")], "A"),
    _row("x1", "S1", [("A", "aa"), ("B", "bb")], "A"),
    _row("y3", "S2", [("A", "cc"), ("B", "dd")], "B"),
]

NAMES = ["X", "Y"]
PAIRS = [("X", "Y")]

TARGET = {
    "X_rows": 4,
    "X_malformed": 1,
    "X_unique_ids": 4,
    "X_duplicate_ids": 0,
    "X_unique_identity_keys": 2,
    "X_identity_keys_multi": 1,
    "X_identity_keys_conflict": 1,
    "Y_rows": 3,
    "Y_malformed": 0,
    "Y_unique_ids": 3,
    "Y_duplicate_ids": 0,
    "Y_unique_identity_keys": 3,
    "Y_identity_keys_multi": 0,
    "Y_identity_keys_conflict": 0,
    "ov_X_Y_shared_ids": 1,
    "ov_X_Y_shared_identities": 2,
    "ov_X_Y_shared_identity_gold_conflict": 1,
}
