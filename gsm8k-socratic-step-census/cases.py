# cases.py -- pre-registered evaluator fixture for the GSM8K main-vs-socratic step and
# annotation census. Written BEFORE any real GSM8K data is read.
#
# The fixture exercises every branch:
#   * A: socratic = main with a sub-question before every line   (steps + annotations identical)
#   * B: same step count, one annotation changed and miscomputed   (both differ; 1 mismatch class)
#   * C: one line lacks the ' ** ' separator, one step gains a comma (steps differ, annotations same)
#   * D: question only in main;  E: question only in socratic

MAIN_ROWS = [
    {"question": "A?", "answer": "Step a1 = <<2+3=5>>5.\nStep a2 = <<5*2=10>>10.\n#### 10"},
    {"question": "B?", "answer": "Cost is <<4*3=12>>12.\n#### 12"},
    {"question": "C?", "answer": "Half is <<10/2=5>>5.\nThen <<5+1=6>>6.\n#### 6"},
    {"question": "D?", "answer": "Only main <<1+1=2>>2.\n#### 2"},
]

SOCRATIC_ROWS = [
    {"question": "A?", "answer": "How much first? ** Step a1 = <<2+3=5>>5.\n"
                                 "How much then? ** Step a2 = <<5*2=10>>10.\n#### 10"},
    {"question": "B?", "answer": "What is the cost? ** Cost is <<4*3=13>>13.\n#### 13"},
    {"question": "C?", "answer": "Half is <<10/2=5>>5.\nWhat next? ** Then, <<5+1=6>>6.\n#### 6"},
    {"question": "E?", "answer": "Only soc? ** <<3*3=9>>9.\n#### 9"},
]

QUESTION_KEY = "question"
ANSWER_KEY = "answer"

# Hand-traced expected counts (integer-only public summary).
#   pairs A,B,C; socratic lines in pairs 2+1+2=5, with separator 2+1+1=4;
#   step counts equal in A,B,C; steps identical only in A; annotations identical in A,C.
#   main annotations: 2+1+2+1 = 6, all match. socratic: 2+1+2+1 = 6, B's 4*3=13 mismatches.
TARGET = {
    "pairs": 3,
    "only_in_main": 1,
    "only_in_socratic": 1,
    "socratic_lines_in_pairs": 5,
    "socratic_lines_with_separator": 4,
    "step_count_equal": 3,
    "steps_identical": 1,
    "annotations_identical": 2,
    "annotations_differ": 1,
    "main_annotations_total": 6,
    "socratic_annotations_total": 6,
    "main_annotation_classes": {"match": 6, "rounded": 0, "mismatch": 0,
                                "unparseable_expr": 0, "unparseable_result": 0},
    "socratic_annotation_classes": {"match": 5, "rounded": 0, "mismatch": 1,
                                    "unparseable_expr": 0, "unparseable_result": 0},
}

# Reproducibility cross-check against audit 19 (gsm8k-calculator-annotation-census, frozen
# results): the MAIN files' combined annotation classes must reproduce it exactly.
AUDIT19_MAIN_CLASSES = {"match": 27995, "rounded": 0, "mismatch": 0,
                        "unparseable_expr": 2, "unparseable_result": 1}

# Pre-registered predictions for the REAL data (recorded before reading it; not a gate):
#   P1 every main question pairs with a socratic one (audit 24): pairs == 8,792.
#   P2 annotation sequences are identical in at least 99% of pairs.
#   P3 the socratic files have 0 'mismatch' annotations, like the main files.
#   P4 at least 99% of socratic lines in pairs carry the ' ** ' separator.
PREDICTIONS = {
    "P1_pairs": 8792,
    "P2_min_annotation_identical_share": 0.99,
    "P3_socratic_mismatch": 0,
    "P4_min_separator_share": 0.99,
}
