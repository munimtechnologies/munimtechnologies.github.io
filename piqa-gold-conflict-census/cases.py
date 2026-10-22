"""Hand-traced fixture for the PIQA gold-conflict census.

Seven synthetic rows whose counts are worked out by hand in TARGET below, so the census
logic is checked against a known answer before it ever touches real PIQA data.

Reasoning (normalize = collapse whitespace + strip + lowercase; the gold label 0/1 names
which solution is correct):
- rows 1-2: identical (goal, sol1, sol2), opposite labels -> ONE exact triple conflict,
  2 rows. Goal G1 appears in 2 examples.
- rows 3-4: sol1 differs only by case and a trailing space, so the two rows are two DISTINCT
  exact triples (no exact duplicate) but ONE normalized triple with opposite labels -> an
  ADDITIONAL conflict found only after normalization. Goal G2 appears in 2 examples.
- rows 5-6: same goal G3, two DIFFERENT solution pairs, opposite labels -> legitimate goal
  reuse (context), NOT a triple conflict. Goal G3 appears in 2 examples.
- row 7: goal G4 appears once -> not a goal duplicate.

So: rows 7; unique goals {G1,G2,G3,G4} = 4; unique exact triples = 6 (G1 once as rows 1=2,
the two distinct G2 triples, the two G3 triples, the G4 triple); exact triple duplicate
groups = 1 (rows 1-2); exact triple conflict groups = 1 (rows 1-2), conflict rows = 2;
normalized triple conflict groups = 2 (rows 1-2 and rows 3-4), of which 1 is additional
(rows 3-4); goal duplicate groups = 3 (G1, G2, G3 each appear twice; G4 only once).
"""

FIXTURE = [
    {"goal": "boil an egg", "sol1": "Lower the egg into boiling water for ten minutes.",
     "sol2": "Lower the egg into cold oil for ten minutes.", "label": 0},
    {"goal": "boil an egg", "sol1": "Lower the egg into boiling water for ten minutes.",
     "sol2": "Lower the egg into cold oil for ten minutes.", "label": 1},

    {"goal": "open a stuck jar lid", "sol1": "Twist the lid Anticlockwise",
     "sol2": "Freeze the jar for an hour first.", "label": 0},
    {"goal": "open a stuck jar lid", "sol1": "twist the lid anticlockwise ",
     "sol2": "Freeze the jar for an hour first.", "label": 1},

    {"goal": "keep bread fresh", "sol1": "Store the loaf in a paper bag.",
     "sol2": "Store the loaf in direct sunlight.", "label": 0},
    {"goal": "keep bread fresh", "sol1": "Seal the loaf in an airtight container.",
     "sol2": "Leave the loaf uncovered on the counter for a week.", "label": 1},

    {"goal": "remove a splinter", "sol1": "Use clean tweezers to pull it out.",
     "sol2": "Hit the area with a hammer.", "label": 0},
]

TARGET = {
    "rows": 7,
    "unique_goals": 4,
    "unique_triples": 6,
    "triple_duplicate_groups": 1,
    "triple_conflict_groups": 1,
    "triple_conflict_rows": 2,
    "norm_triple_conflict_groups": 2,
    "norm_additional": 1,
    "goal_duplicate_groups": 3,
}
