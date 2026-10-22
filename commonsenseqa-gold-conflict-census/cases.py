"""Hand-traced fixture for the CommonsenseQA gold-conflict census.

Eight synthetic rows whose counts are worked out by hand in TARGET below, so the census
logic is checked against a known answer before it ever touches real CommonsenseQA data.

Each row mimics the release schema: {"answerKey": L, "question": {"stem": ..., "choices":
[{"label": L, "text": ...}, ...]}}. The item key is (stem, sorted tuple of option texts),
so option ORDER does not matter; the gold compared is the answer TEXT (the text of the
choice whose label == answerKey), so relabelling the same answer is never a conflict.
normalize = collapse whitespace + strip + lowercase.

Reasoning:
- rows 1-2 (stem S1, same three options): answerKey picks different TEXTS (x vs y) -> ONE
  exact item conflict, 2 rows. Stem S1 appears in 2 examples.
- rows 3-4 (stem S2): option texts differ only by case/trailing space, so two DISTINCT exact
  items (no exact duplicate), but after normalization ONE item; the golds normalize to
  different texts (red vs blue) -> an ADDITIONAL conflict found only after normalization.
  Stem S2 appears in 2 examples.
- rows 5-6 (stem S3, identical options, same gold "p"): an exact DUPLICATE item that is NOT
  a conflict (same gold). Stem S3 appears in 2 examples.
- rows 7-8 (stem S4, DIFFERENT option sets): legitimate stem reuse (context), NOT an item
  conflict and NOT a duplicate item. Stem S4 appears in 2 examples.

So: rows 8; unique stems {S1,S2,S3,S4} = 4; unique exact items = 6 (S1 once, the two distinct
S2 items, the S3 item, the two distinct S4 items); item duplicate groups = 2 (S1, S3); item
conflict groups = 1 (S1), conflict rows = 2; normalized conflict groups = 2 (S1 and S2), of
which 1 additional (S2); stem duplicate groups = 4 (S1-S4 each appear twice).
"""


def _q(stem, choices, answer_label):
    return {"answerKey": answer_label,
            "question": {"stem": stem,
                         "choices": [{"label": l, "text": t} for l, t in choices]}}


FIXTURE = [
    # rows 1-2: same stem + same option set, different gold TEXT -> exact conflict.
    _q("What opens a locked door?", [("A", "a key"), ("B", "a hammer"), ("C", "a song")], "A"),
    _q("What opens a locked door?", [("A", "a key"), ("B", "a hammer"), ("C", "a song")], "B"),

    # rows 3-4: options differ only by case/space; golds normalize to different texts
    # -> no exact conflict, one additional normalized conflict.
    _q("Name a warm colour.", [("A", "Red"), ("B", "Blue")], "A"),
    _q("Name a warm colour.", [("A", "red "), ("B", "blue")], "B"),

    # rows 5-6: identical item, same gold -> duplicate without conflict.
    _q("Pick a fruit.", [("A", "pear"), ("B", "chair")], "A"),
    _q("Pick a fruit.", [("A", "pear"), ("B", "chair")], "A"),

    # rows 7-8: same stem, different option sets -> legitimate stem reuse (context).
    _q("Choose the correct one.", [("A", "moon"), ("B", "nail")], "A"),
    _q("Choose the correct one.", [("A", "up"), ("B", "van")], "B"),
]

TARGET = {
    "rows": 8,
    "unique_stems": 4,
    "unique_items": 6,
    "item_duplicate_groups": 2,
    "item_conflict_groups": 1,
    "item_conflict_rows": 2,
    "norm_item_conflict_groups": 2,
    "norm_additional": 1,
    "stem_duplicate_groups": 4,
}
