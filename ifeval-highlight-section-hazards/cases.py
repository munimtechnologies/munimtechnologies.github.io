# Pre-registered synthetic corpus for the ifeval-highlight-section-hazards audit.
#
# Each case pins the HighlightSectionChecker count and pass/fail against the
# ground-truth number of deliberately highlighted sections. Every value was
# hand-traced against highlight_checker.py BEFORE any real data was touched; the
# sealed job re-derives the aggregate and asserts it equals TARGET.
#
# Hand-trace of the headline hazard, "***only one***" (one bold-italic span):
#   singles findall -> ["**"(empty,skip), "*only one*"(counted), "**"(empty,skip)] = 1
#   doubles findall -> ["**only one**"(counted)]                                   = 1
#   num_highlights = 2, but there is ONE visual highlighted section.
#
# Labelled corpus by AI agents working in MV2's name (Munim, Inc.). CC BY 4.0.

# id, value, num_required, intended_true_count, expected_verdict, note
CASES = [
    ("C1-two-singles",
     "*first point* and then *second point*",
     2, 2, "match",
     "Two genuine single-asterisk highlights; checker counts 2, quota 2 -> pass is correct."),
    ("C2-triple-overcount",
     "Here is ***only one*** highlighted span.",
     2, 1, "false_pass",
     "ONE bold-italic span counted as 2 (single + double); quota 2 falsely satisfied."),
    ("C3-triple-correct",
     "A single ***emphasis*** span here.",
     1, 1, "match",
     "Same over-count (checker 2) but quota 1, so the verdict is still correct."),
    ("C4-empty-guard",
     "A rule of thumb: **  ** means nothing on its own.",
     1, 0, "correct_neg",
     "'**  **' strips to empty -> not counted; checker count 0, quota 1 -> correct reject."),
    ("C5-two-doubles",
     "Key terms: **alpha** and **beta** are defined.",
     2, 2, "match",
     "Two genuine double-asterisk highlights; checker counts 2, quota 2 -> pass is correct."),
    ("C6-no-highlight",
     "Plain prose with no markdown emphasis anywhere in it.",
     1, 0, "correct_neg",
     "No asterisks at all; checker count 0, quota 1 -> correct reject."),
]

TARGET = {
    "n_cases": 6,
    "n_match": 3,
    "n_correct_neg": 2,
    "n_false_pass": 1,
    "n_false_fail": 0,
    "n_flips": 1,
    "all_reproduced": True,
}
