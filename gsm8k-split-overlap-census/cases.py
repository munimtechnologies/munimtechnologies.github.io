# cases.py -- pre-registered evaluator fixture for the GSM8K split-overlap census.
#
# This fixture and its TARGET are written BEFORE any real GSM8K data is read, so the
# analysis code is pinned to known-correct counts on a tiny hand-traced corpus
# (3 train rows + 4 test rows) that exercises every branch:
#   * one question identical in both splits with agreeing answers  (T1 / E1)
#   * one question identical in both splits with CONFLICTING answers (T2 / E2)
#   * one question equal only after normalization (double space / case) (T3 / N1)
#   * one test-only question with no match at all                    (X1)

TRAIN = [
    {"question": "What is 2+2?",
     "answer": "2+2=4\n#### 4"},
    {"question": "How many apples remain after eating 3?",
     "answer": "10-3=7\n#### 7"},
    {"question": "A car drives 60 miles in 1 hour. What is its speed?",
     "answer": "60/1=60\n#### 60"},
]

TEST = [
    {"question": "What is 2+2?",
     "answer": "#### 4"},                      # exact match to T1, answers agree
    {"question": "How many apples remain after eating 3?",
     "answer": "#### 8"},                      # exact match to T2, answer CONFLICT (7 vs 8)
    {"question": "A car drives 60 miles in 1 hour.  What is its speed?",
     "answer": "#### 60"},                     # double space -> normalized match to T3, agree
    {"question": "What is the capital of France?",
     "answer": "#### 0"},                      # test-only, no overlap
]

# Hand-traced expected counts (the integer-only public summary).
TARGET = {
    "train_rows_valid": 3,
    "test_rows_valid": 4,
    "train_distinct_exact": 3,
    "test_distinct_exact": 4,
    "exact_overlap_pairs": 2,
    "exact_overlap_answer_conflicts": 1,
    "norm_overlap_pairs": 3,
    "norm_overlap_answer_conflicts": 1,
}
