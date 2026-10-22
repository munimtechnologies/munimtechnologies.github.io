# cases.py -- pre-registered evaluator fixture for the GSM8K main-vs-socratic
# final-answer census. Written BEFORE any real GSM8K data is read.
#
# The fixture exercises every branch:
#   * a shared question whose finals AGREE                     (Natalia: 24 == 24)
#   * a shared question whose finals DISAGREE                  (Weng: 5 vs 7)
#   * a shared question that agrees only after comma-stripping (Julie: "1,000" vs "1000")
#   * a question present ONLY in main                          (Betty)
#   * a question present ONLY in socratic                      (James)

MAIN_ROWS = [
    {"question": "Natalia sold clips. How many in total?",
     "answer": "She sold 48/2 = <<48/2=24>>24 in May.\n#### 24"},
    {"question": "Weng earns per hour. How much did she earn?",
     "answer": "She earned 12 * 50/60 = <<12*50/60=10>>10... wait.\n#### 5"},
    {"question": "Betty is saving for a wallet. How much more?",
     "answer": "She needs 100 - 90 = <<100-90=10>>10 dollars.\n#### 10"},
    {"question": "Julie reads a book. How many pages tomorrow?",
     "answer": "She should read <<...>> pages.\n#### 1,000"},
]

SOCRATIC_ROWS = [
    {"question": "Natalia sold clips. How many in total?",
     "answer": "How many did she sell in May? She sold 48/2 = <<48/2=24>>24.\n#### 24"},
    {"question": "Weng earns per hour. How much did she earn?",
     "answer": "How much per minute? 12/60 = <<12/60=0.2>>0.2. Total?\n#### 7"},
    {"question": "James writes letters. How many pages a year?",
     "answer": "How many pages per letter? 3.\n#### 3"},
    {"question": "Julie reads a book. How many pages tomorrow?",
     "answer": "How many pages left? She should read <<...>> pages.\n#### 1000"},
]

QUESTION_KEY = "question"
ANSWER_KEY = "answer"

# Hand-traced expected counts (integer-only public summary).
TARGET = {
    "main_rows_valid": 4,
    "socratic_rows_valid": 4,
    "main_distinct_questions": 4,
    "socratic_distinct_questions": 4,
    "questions_in_both": 3,
    "questions_only_in_main": 1,
    "questions_only_in_socratic": 1,
    "final_answer_agree": 2,
    "final_answer_disagree": 1,
}
