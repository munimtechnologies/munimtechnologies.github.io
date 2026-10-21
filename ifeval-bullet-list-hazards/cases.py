# Pre-registered synthetic corpus for the ifeval-bullet-list-hazards audit.
#
# Each case pins the BulletListChecker count and its EXACT-equality pass/fail
# against the ground-truth number of deliberate markdown bullet points. Every
# value was hand-traced against bullet_checker.py BEFORE any real data was
# touched; the sealed job re-derives the aggregate and asserts it equals TARGET.
#
# Hand-trace of the two over-count headlines:
#   "-5 degrees" on its own line  -> "^\s*-.*$" matches (dash, no space needed)
#       -> counted as a bullet though CommonMark renders no list item.
#   "*italic*"  on its own line   -> "^\s*\*[^\*].*$" matches ('*' then 'i')
#       -> counted as a bullet though it renders as italic text.
#   "**bold**"  on its own line   -> "[^\*]" fails on the second '*' -> NOT counted (correct).
#
# Labelled corpus by AI agents working in MV2's name (Munim, Inc.). CC BY 4.0.

# id, value, num_required, intended_true_count, expected_count, expected_verdict, note
CASES = [
    ("B1-three-asterisks",
     "* first\n* second\n* third",
     3, 3, 3, "match",
     "Three genuine '* ' bullets; checker counts 3, quota 3 -> correct pass."),
    ("B2-two-dashes",
     "- alpha\n- beta",
     2, 2, 2, "match",
     "Two genuine '- ' bullets; checker counts 2, quota 2 -> correct pass."),
    ("B3-negative-number-false-pass",
     "Here are my picks:\n- apples\n- oranges\nThe temperature dropped to\n-5 degrees overnight.",
     3, 2, 3, "false_pass",
     "Two real bullets plus a line starting '-5' (negative number) counted as a "
     "third bullet, so the total lands on the quota 3 -> false pass."),
    ("B4-horizontal-rule-false-fail",
     "* one\n* two\n* three\n---\n* four",
     4, 4, 5, "false_fail",
     "Four real '* ' bullets, but the '---' horizontal rule is counted as a fifth "
     "bullet, so the exact-equality check (==4) fails -> false fail."),
    ("B5-italic-line-false-fail",
     "- step one\n- step two\n*note this is important*",
     2, 2, 3, "false_fail",
     "Two real '- ' bullets, but the '*italic*' line is counted as a third "
     "bullet, so ==2 fails -> false fail."),
    ("B6-no-bullets",
     "Just a sentence with no bullets at all.",
     2, 0, 0, "correct_neg",
     "No bullet markers; checker counts 0, quota 2 -> correct reject."),
    ("B7-bold-heading-control",
     "**Summary**\n- a\n- b\n- c",
     3, 3, 3, "match",
     "The '**Summary**' bold heading is correctly NOT counted ('[^\\*]' guard); "
     "three real '- ' bullets, quota 3 -> correct pass."),
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
