# Pre-registered synthetic corpus for the ifeval-paragraph-hazards audit.
#
# Each case pins the ParagraphChecker count (and whether it hard-fails on an
# interior-empty segment) and its EXACT-equality pass/fail against the
# ground-truth number of deliberate paragraphs. Every value was hand-traced
# against paragraph_checker.py BEFORE any real data was touched; the sealed job
# re-derives the aggregate and asserts it equals TARGET.
#
# Hand-trace of the two headlines:
#   "This note is ***very important*** to remember."  (one paragraph)
#       -> r"\s?\*\*\*\s?" matches at BOTH runs of '***' -> split into 3 segments
#       -> num=3, so the EXACT check against num_required=1 FAILS a good answer.
#   "Part one.\n***\n***\nPart two."  (two paragraphs, divider doubled)
#       -> split -> ["Part one.", "", "Part two."] -> interior empty -> HARD FAIL.
#   "a *** b *** c" on one line (one paragraph, '***' used as a separator)
#       -> split into 3 -> num=3 lands on num_required=3 -> FALSE PASS.
#
# Labelled corpus by AI agents working in MV2's name (Munim, Inc.). CC BY 4.0.

# id, value, num_required, intended_true_count, expected_num, expected_hard_fail,
#     expected_verdict, note
CASES = [
    ("P1-three-paragraphs",
     "First paragraph.\n***\nSecond paragraph.\n***\nThird paragraph.",
     3, 3, 3, False, "match",
     "Three paragraphs split by two standalone '***' lines; num=3, quota 3 -> pass."),
    ("P2-two-paragraphs",
     "Opening statement goes here.\n***\nClosing statement goes here.",
     2, 2, 2, False, "match",
     "Two paragraphs, one standalone divider; num=2, quota 2 -> pass."),
    ("P3-inline-emphasis-false-fail",
     "This note is ***very important*** to remember.",
     1, 1, 3, False, "false_fail",
     "One paragraph using inline '***emphasis***'; the divider regex matches at "
     "both asterisk runs -> num=3, so ==1 fails a correct one-paragraph answer."),
    ("P4-doubled-divider-hard-fail",
     "Part one.\n***\n***\nPart two.",
     2, 2, 3, True, "false_fail",
     "Two paragraphs but the divider was doubled, leaving an interior empty "
     "segment -> upstream returns False (hard fail) on a response that reads as 2."),
    ("P5-inline-separators-false-pass",
     "The plan is simple *** gather the data *** then ship it.",
     3, 1, 3, False, "false_pass",
     "A single prose line using '***' twice as visual separators; split into 3 "
     "segments -> num=3 lands on quota 3, passing a response with no real breaks."),
    ("P6-no-divider-correct-neg",
     "Just a single paragraph with no dividers at all here.",
     3, 1, 1, False, "correct_neg",
     "No divider; num=1, quota 3 -> correctly rejected."),
    ("P7-three-paragraphs-b",
     "Alpha block of text.\n***\nBeta block of text.\n***\nGamma block of text.",
     3, 3, 3, False, "match",
     "Three paragraphs, two standalone dividers; num=3, quota 3 -> pass."),
]

TARGET = {
    "n_cases": 7,
    "n_match": 3,
    "n_correct_neg": 1,
    "n_false_pass": 1,
    "n_false_fail": 2,
    "n_flips": 3,
    "all_reproduced": True,
}
