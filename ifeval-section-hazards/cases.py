# Pre-registered synthetic corpus for the ifeval-section-hazards audit.
#
# Each case pins the SectionChecker count (num_sections = len(re.split(...)) - 1)
# and its >= pass/fail against the ground-truth number of deliberate sections.
# Every value was hand-traced against section_checker.py BEFORE any real data was
# touched; the sealed job re-derives the aggregate and asserts it equals TARGET.
# All cases use section_spliter = "Section".
#
# Hand-trace of the headlines (pattern r"\s?Section\s?\d+\s?"):
#   "...refer to Section 3 below..."  -> matches the inline cross-reference
#       -> inflates num past the quota -> FALSE PASS under >=.
#   "...the subSection3 helper..."    -> 'Section3' matches inside the word
#       -> inflates num past the quota -> FALSE PASS under >=.
#   "Section One / Section Two / Section Three" -> no \d+ -> matches NOTHING
#       -> num=0, and 0 >= 3 -> FALSE FAIL on a correct answer.
#
# Labelled corpus by AI agents working in MV2's name (Munim, Inc.). CC BY 4.0.

# id, value, spliter, num_required, intended_true_count, expected_num,
#     expected_verdict, note
CASES = [
    ("S1-three-sections",
     "Section 1\nIntro content.\nSection 2\nMore content.\nSection 3\nFinal content.",
     "Section", 3, 3, 3, "match",
     "Three digit-marked sections; num=3, quota 3 -> pass."),
    ("S2-two-sections",
     "Section 1\nFirst part here.\nSection 2\nSecond part here.",
     "Section", 2, 2, 2, "match",
     "Two digit-marked sections; num=2, quota 2 -> pass."),
    ("S3-inline-crossref-false-pass",
     "Section 1\nIntro. Please refer to Section 3 below for the summary.\nSection 2\nConclusion.",
     "Section", 3, 2, 3, "false_pass",
     "Only two real sections, but the inline 'Section 3' cross-reference is "
     "counted, so num=3 >= 3 passes a response with too few sections."),
    ("S4-substring-false-pass",
     "Section 1\nDefine the subSection3 helper in your code.\nSection 2\nDone.",
     "Section", 3, 2, 3, "false_pass",
     "Only two real sections, but 'Section3' inside 'subSection3' is matched, so "
     "num=3 >= 3 passes a response with too few sections."),
    ("S5-spelled-out-false-fail",
     "Section One\nThe introduction.\nSection Two\nThe body.\nSection Three\nThe conclusion.",
     "Section", 3, 3, 0, "false_fail",
     "Three correctly marked sections using number WORDS; the \\d+ requirement "
     "matches nothing, so num=0 and 0 >= 3 fails a correct answer."),
    ("S6-four-sections",
     "Section 1\nContent A.\nSection 2\nContent B.\nSection 3\nContent C.\nSection 4\nContent D.",
     "Section", 4, 4, 4, "match",
     "Four digit-marked sections; num=4, quota 4 -> pass."),
    ("S7-no-sections-correct-neg",
     "Here is my answer without any marked sections at all.",
     "Section", 3, 0, 0, "correct_neg",
     "No section markers; num=0, quota 3 -> correctly rejected."),
]

TARGET = {
    "n_cases": 7,
    "n_match": 3,
    "n_correct_neg": 1,
    "n_false_pass": 2,
    "n_false_fail": 1,
    "n_flips": 3,
    "all_reproduced": True,
}
