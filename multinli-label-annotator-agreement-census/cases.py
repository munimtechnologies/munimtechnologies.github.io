"""Hand-traced fixture for the MultiNLI per-gold-label annotator-agreement census.

Six synthetic rows, worked out by hand into TARGET, so the per-class tally logic is checked against a
known answer before it touches the real multinli_1.0.zip. Each row is (gold_label, five annotator labels).
The fixture exercises all three gold classes, unanimous and split rows, and one "-" (no-majority) row.
It is identical to the SNLI fixture (audit 42) because the census module is dataset-agnostic; the only
dataset-specific constants are the member names and expected row count below.

  rA gold=e votes[e,e,e,e,e]  -> e: 5 agree, unanimous, majority e
  rB gold=e votes[e,e,e,n,c]  -> e: 3 agree, not unanimous, majority e (3 of 5)
  rC gold=n votes[n,n,n,e,c]  -> n: 3 agree, not unanimous, majority n
  rD gold=n votes[n,n,n,n,e]  -> n: 4 agree, not unanimous, majority n
  rE gold=c votes[c,c,c,c,c]  -> c: 5 agree, unanimous, majority c
  rF gold=- votes[e,n,c,e,n]  -> dash (no gold class, skipped from per-label)

n_total=6 ; n_dash=1 ; n_valid=5
e: n=2 unanimous=1 labels_total=10 labels_agree=8 gold_eq_majority=2   (rate 0.5 ; indiv 0.8)
n: n=2 unanimous=0 labels_total=10 labels_agree=7 gold_eq_majority=2   (rate 0.0 ; indiv 0.7)
c: n=1 unanimous=1 labels_total=5  labels_agree=5 gold_eq_majority=1   (rate 1.0 ; indiv 1.0)
"""

E = "entailment"
N = "neutral"
C = "contradiction"


def _rec(gold, votes):
    return {"gold": gold, "annotators": votes}


FIXTURE = [
    _rec(E, [E, E, E, E, E]),
    _rec(E, [E, E, E, N, C]),
    _rec(N, [N, N, N, E, C]),
    _rec(N, [N, N, N, N, E]),
    _rec(C, [C, C, C, C, C]),
    _rec("-", [E, N, C, E, N]),
]


TARGET = {
    "n_total": 6,
    "n_dash": 1,
    "n_valid": 5,
    "e_n": 2, "e_unanimous": 1, "e_labels_total": 10, "e_labels_agree": 8, "e_gold_eq_majority": 2,
    "n_n": 2, "n_unanimous": 0, "n_labels_total": 10, "n_labels_agree": 7, "n_gold_eq_majority": 2,
    "c_n": 1, "c_unanimous": 1, "c_labels_total": 5, "c_labels_agree": 5, "c_gold_eq_majority": 1,
}

# Minimum per-class unanimous-rate spread we pre-register as "meaningfully label-dependent" (P3).
MIN_UNANIMOUS_SPREAD = 0.05

# MultiNLI 1.0 validated five-vote dev splits (both carry annotator_labels + genre). raw = 20,000 rows
# (10,000 matched + 10,000 mismatched); audit 38 confirmed each raw dev file ships 10,000 rows.
MNLI_MEMBERS = ("multinli_1.0_dev_matched.jsonl", "multinli_1.0_dev_mismatched.jsonl")
EXPECTED_TOTAL_ROWS = 20000
