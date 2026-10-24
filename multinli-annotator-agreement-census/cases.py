"""Hand-traced fixture for the MultiNLI annotator-agreement / gold-derivation census.

The fixture is NLI-dataset-neutral and identical to audit 37's (SNLI): five synthetic rows whose census
counts are worked out by hand in TARGET, so the counting logic is checked against a known answer before it
touches real data. One row (r5) is a synthetic derivation anomaly (gold disagrees with the annotator
majority) so the mismatch path is exercised; the real-data predictions bet that no such row exists in the
released files.

r1  gold "entailment"   annotators [entailment]                                   (train-style single label)
    k=1 ; majority=entailment ; gold==majority -> match ; multi? no
r2  gold "neutral"       annotators [neutral,neutral,entailment,neutral,contradiction]
    k=5 ; majority=neutral (3/5) ; gold==majority -> match ; multi yes ; not unanimous
r3  gold "-"             annotators [entailment,neutral,contradiction,entailment,neutral]
    k=5 ; 2-2-1, no strict majority ; gold is "-" -> correct no-consensus ; multi yes ; not unanimous
r4  gold "contradiction" annotators [contradiction,contradiction,contradiction,contradiction,contradiction]
    k=5 ; majority=contradiction (5/5) ; gold==majority -> match ; multi yes ; unanimous
r5  gold "entailment"    annotators [neutral,neutral,entailment]
    k=3 ; majority=neutral (2/3) ; gold != majority -> MISMATCH ; multi yes ; not unanimous

n_total=5
n_labeled = r1,r2,r4,r5 = 4 ; n_no_consensus = r3 = 1 ; n_no_annotators = 0
n_gold_matches_majority = r1,r2,r4 = 3 ; n_gold_mismatch_majority = r5 = 1
n_labeled_without_majority = 0 ; n_no_consensus_with_majority = 0
n_multi (k>=2) = r2,r3,r4,r5 = 4 ; n_unanimous_multi = r4 = 1
"""


def _row(gold, annotators):
    return {"gold_label": gold, "annotator_labels": list(annotators),
            "sentence1": "a premise", "sentence2": "a hypothesis"}


FIXTURE = [
    _row("entailment", ["entailment"]),
    _row("neutral", ["neutral", "neutral", "entailment", "neutral", "contradiction"]),
    _row("-", ["entailment", "neutral", "contradiction", "entailment", "neutral"]),
    _row("contradiction", ["contradiction", "contradiction", "contradiction", "contradiction", "contradiction"]),
    _row("entailment", ["neutral", "neutral", "entailment"]),
]

TARGET = {
    "n_total": 5,
    "n_labeled": 4,
    "n_no_consensus": 1,
    "n_no_annotators": 0,
    "n_gold_matches_majority": 3,
    "n_gold_mismatch_majority": 1,
    "n_labeled_without_majority": 0,
    "n_no_consensus_with_majority": 0,
    "n_multi": 4,
    "n_unanimous_multi": 1,
}

# multinli_1.0.zip ships train + the two dev splits (the test splits are distributed without labels for
# the Kaggle evaluations, so they are not in this file). These are the raw jsonl line counts.
RAW_SPLIT_TOTAL = {"train": 392702, "dev_matched": 9815, "dev_mismatched": 9832}
SPLITS = ("train", "dev_matched", "dev_mismatched")

# MultiNLI validated only its dev and test sets (four additional annotators each); the training split is
# unvalidated, carrying the single author label. So, unlike SNLI (whose train file holds a validated
# subset), MultiNLI train is expected to be entirely single-annotator with no '-' rows. P3 bets this.
TRAIN_EXPECTED_HIST = {"1": 392702}
