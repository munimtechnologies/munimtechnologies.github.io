"""Hand-traced fixture for the ARC<->OpenBookQA cross-dataset overlap census.

Two synthetic mini-datasets A (ARC-like) and B (OpenBookQA-like) in the raw jsonl question shape.
The census counts are worked out by hand in TARGET below, so the logic is checked against a known
answer before it touches real data.

Each raw object is {"id", "question": {"stem", "choices": [{"text", "label"}, ...]}, "answerKey"}.
Identity = (normalized stem, frozenset of normalized choice texts); gold = text of the choice whose
label == answerKey.

Dataset A (4 rows):
- a1  stem S1  A:aa B:bb  key A -> identity (s1,{aa,bb}), gold aa
- a2  stem S2  A:cc B:dd  key A -> identity (s2,{cc,dd}), gold cc
- a3  stem S3  A:ee B:ff  key A -> identity (s3,{ee,ff}), gold ee
- a4  stem S5  1:mm 2:nn  key 9 -> answerKey "9" matches no label {1,2} -> malformed, excluded
  => rows 4, malformed 1. Non-malformed identities: (s1,{aa,bb}),(s2,{cc,dd}),(s3,{ee,ff}) = 3.
     Non-malformed stems: {s1,s2,s3} = 3.

Dataset B (4 rows):
- b1  stem S1  A:aa B:bb  key A -> identity (s1,{aa,bb}), gold aa  (SHARED identity w/ a1, SAME gold)
- b2  stem S2  A:cc B:dd  key B -> identity (s2,{cc,dd}), gold dd  (SHARED identity w/ a2, gold DIFFERS
                                                                    -> cross-dataset gold conflict)
- b3  stem S3  A:gg B:hh  key A -> identity (s3,{gg,hh}), gold gg  (same STEM S3 as a3 but different
                                                                    choices -> shared stem, NOT a
                                                                    shared identity)
- b4  stem S4  A:ii B:jj  key A -> identity (s4,{ii,jj}), gold ii  (unique to B)
  => rows 4, malformed 0. Non-malformed identities: 4. Non-malformed stems: {s1,s2,s3,s4} = 4.

Cross overlap A|B:
- shared identities: (s1,{aa,bb}) and (s2,{cc,dd}) = 2.
- shared-identity gold conflict: (s1) golds {aa}|{aa} -> no; (s2) golds {cc}|{dd} -> yes. => 1.
- shared stems: A {s1,s2,s3} & B {s1,s2,s3,s4} = {s1,s2,s3} = 3.
"""


def _row(id_, stem, choices, answer_key):
    """choices is a list of (label, text) pairs."""
    return {
        "id": id_,
        "question": {"stem": stem, "choices": [{"text": t, "label": l} for l, t in choices]},
        "answerKey": answer_key,
    }


FIXTURE_A = [
    _row("a1", "S1", [("A", "aa"), ("B", "bb")], "A"),
    _row("a2", "S2", [("A", "cc"), ("B", "dd")], "A"),
    _row("a3", "S3", [("A", "ee"), ("B", "ff")], "A"),
    _row("a4", "S5", [("1", "mm"), ("2", "nn")], "9"),
]

FIXTURE_B = [
    _row("b1", "S1", [("A", "aa"), ("B", "bb")], "A"),
    _row("b2", "S2", [("A", "cc"), ("B", "dd")], "B"),
    _row("b3", "S3", [("A", "gg"), ("B", "hh")], "A"),
    _row("b4", "S4", [("A", "ii"), ("B", "jj")], "A"),
]

TARGET = {
    "a_rows": 4,
    "b_rows": 4,
    "a_malformed": 1,
    "b_malformed": 0,
    "a_distinct_identities": 3,
    "b_distinct_identities": 4,
    "a_distinct_stems": 3,
    "b_distinct_stems": 4,
    "shared_identities": 2,
    "shared_identity_gold_conflict": 1,
    "shared_stems": 3,
}
