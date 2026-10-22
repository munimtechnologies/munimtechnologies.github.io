"""Hand-traced fixture for the BoolQ gold-conflict census.

Six synthetic rows whose counts are worked out by hand in TARGET below, so the census
logic is checked against a known answer before it ever touches real BoolQ data.

Reasoning (normalize = collapse whitespace + strip + lowercase):
- rows 1-2: identical (question, passage), opposite answers -> ONE exact (q,p) conflict,
  2 rows. This question appears with two answers -> a question conflict too.
- rows 3-4: question and passage differ only by case/trailing space, so they are two
  DISTINCT exact (q,p) keys (no exact duplicate) but ONE normalized key with opposite
  answers -> an ADDITIONAL conflict found only after normalization. Because the two
  questions differ exactly, neither exact-question group has two answers on its own.
- rows 5-6: same question, two DIFFERENT passages, opposite answers -> a question-only
  conflict (legitimate in BoolQ), NOT a (q,p) conflict.

So: rows 6; unique questions {r1=r2, r3, r4, r5=r6} = 4; unique passages all 5 distinct;
exact (q,p) duplicate groups = 1 (rows 1-2); exact (q,p) conflict groups = 1 (rows 1-2),
conflict rows = 2; normalized (q,p) conflict groups = 2 (rows 1-2 and rows 3-4), of which
1 is additional (rows 3-4); exact-question conflict groups = 2 (the tomato and penguin
questions).
"""

FIXTURE = [
    {"question": "is a tomato a fruit", "title": "Tomato",
     "passage": "A tomato is botanically a fruit.", "answer": True},
    {"question": "is a tomato a fruit", "title": "Tomato",
     "passage": "A tomato is botanically a fruit.", "answer": False},

    {"question": "can you see the great wall from space", "title": "Great Wall of China",
     "passage": "The Great Wall is hard to see from low Earth orbit.", "answer": False},
    {"question": "Can you see the great wall from space ", "title": "Great Wall of China",
     "passage": "the great wall is hard to see from low earth orbit.", "answer": True},

    {"question": "do penguins live at the north pole", "title": "Penguin",
     "passage": "Penguins live almost exclusively in the Southern Hemisphere.", "answer": False},
    {"question": "do penguins live at the north pole", "title": "Penguin",
     "passage": "Some northern zoos keep penguins in captivity.", "answer": True},
]

TARGET = {
    "rows": 6,
    "unique_questions": 4,
    "unique_passages": 5,
    "qp_duplicate_groups": 1,
    "qp_conflict_groups": 1,
    "qp_conflict_rows": 2,
    "norm_qp_conflict_groups": 2,
    "norm_additional": 1,
    "question_conflict_groups": 2,
}
