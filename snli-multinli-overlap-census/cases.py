"""Hand-traced fixture for the SNLI x MultiNLI cross-overlap census.

Two synthetic mini-corpora whose counts are worked out by hand in TARGET below, so the census
logic is checked against a known answer before it ever touches real SNLI/MultiNLI data.

Each row is (premise, hypothesis, gold_label); gold '-' is excluded as malformed. The pair
key is (premise, hypothesis); the normalized key collapses whitespace and lowercases both.
Labels are OR-ed into a bitmask per pair, and a shared pair is "conflicting" when the union
of the two corpora's labels has more than one distinct label.

Reasoning:
- P1 = ("A man plays guitar.", "A person makes music."): in BOTH, entailment in each -> one
  exact shared pair, SAME label.
- P2 = ("A dog runs.", "The dog is sleeping."): in BOTH, contradiction in SNLI but neutral in
  MultiNLI -> one exact shared pair, CONFLICTING label.
- SNLI-only: ("A kid eats.", "A child is eating.", entailment).
- MultiNLI-only: ("A ship sails.", "A boat is on water.", entailment).
- P3 = ("Two women talk.", "People converse.") in SNLI (neutral) vs
  ("two  women   talk.", "people converse.") in MultiNLI (neutral): NOT an exact match
  (case/whitespace differ) but the SAME after normalization -> one ADDITIONAL normalized
  overlap, SAME label.
- One SNLI row has gold '-' and is dropped (malformed).

So SNLI: rows_kept 4, malformed 1, unique_pairs 4, unique_norm_pairs 4.
   MultiNLI: rows_kept 4, malformed 0, unique_pairs 4, unique_norm_pairs 4.
   exact_overlap_pairs 2 (P1, P2); same 1 (P1); conflict 1 (P2).
   norm_overlap_pairs 3 (P1, P2, P3); same 2 (P1, P3); conflict 1 (P2);
   norm_additional_over_exact 1 (P3, which is not an exact overlap).
"""

FIXTURE_SNLI = [
    ("A man plays guitar.", "A person makes music.", "entailment"),   # P1 (shared, same)
    ("A dog runs.", "The dog is sleeping.", "contradiction"),         # P2 (shared, conflict)
    ("A kid eats.", "A child is eating.", "entailment"),              # SNLI only
    ("Two women talk.", "People converse.", "neutral"),               # P3 (normalized overlap)
    ("Ignore this row.", "It has no gold.", "-"),                     # malformed (gold '-')
]

FIXTURE_MULTINLI = [
    ("A man plays guitar.", "A person makes music.", "entailment"),   # P1 (shared, same)
    ("A dog runs.", "The dog is sleeping.", "neutral"),               # P2 (shared, conflict)
    ("A ship sails.", "A boat is on water.", "entailment"),           # MultiNLI only
    ("two  women   talk.", "people converse.", "neutral"),            # P3 (normalized overlap)
]

TARGET = {
    "snli_rows_kept": 4,
    "snli_malformed": 1,
    "snli_unique_pairs": 4,
    "snli_unique_norm_pairs": 4,
    "multinli_rows_kept": 4,
    "multinli_malformed": 0,
    "multinli_unique_pairs": 4,
    "multinli_unique_norm_pairs": 4,
    "exact_overlap_pairs": 2,
    "exact_overlap_same_label": 1,
    "exact_overlap_conflicting_label": 1,
    "norm_overlap_pairs": 3,
    "norm_overlap_same_label": 2,
    "norm_overlap_conflicting_label": 1,
    "norm_additional_over_exact": 1,
}


def flatten(result):
    """Flatten a cross_census result to the flat keys used in TARGET."""
    return {
        "snli_rows_kept": result["snli"]["rows_kept"],
        "snli_malformed": result["snli"]["malformed"],
        "snli_unique_pairs": result["snli"]["unique_pairs"],
        "snli_unique_norm_pairs": result["snli"]["unique_norm_pairs"],
        "multinli_rows_kept": result["multinli"]["rows_kept"],
        "multinli_malformed": result["multinli"]["malformed"],
        "multinli_unique_pairs": result["multinli"]["unique_pairs"],
        "multinli_unique_norm_pairs": result["multinli"]["unique_norm_pairs"],
        "exact_overlap_pairs": result["exact_overlap_pairs"],
        "exact_overlap_same_label": result["exact_overlap_same_label"],
        "exact_overlap_conflicting_label": result["exact_overlap_conflicting_label"],
        "norm_overlap_pairs": result["norm_overlap_pairs"],
        "norm_overlap_same_label": result["norm_overlap_same_label"],
        "norm_overlap_conflicting_label": result["norm_overlap_conflicting_label"],
        "norm_additional_over_exact": result["norm_additional_over_exact"],
    }
