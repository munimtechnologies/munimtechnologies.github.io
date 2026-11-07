"""Frozen inputs for audit 87: audit 77's flag rule, the prior, the bootstrap settings, the reproduction gates for
audits 80, 82 and 85, data sources and the hand-traced fixtures (traced in test_est87.py). Apache-2.0."""

from fractions import Fraction

# ----- Audit 77's consensus flag on HELM's 10 most accurate models, unchanged -----
PANEL_SIZE = 10
MIN_AGREE = 6

# ----- Pre-registered settings -----
PRIOR = 1                                   # A in k_s = (O_s + A) / (E_s + A)
EXPLORE_PRIORS = (Fraction(1, 2), 2, 5)     # exploratory only
B = 1000                                    # bootstrap replicates
SEED = 87                                   # fold f uses SEED + f; the final estimate SEED + 2

# ----- Reproduction gates (part of P1) -----
EXPECTED_80 = {
    "universe": 13984,
    "included": 78,
    "panel": ["anthropic_claude-3-5-sonnet-20241022", "anthropic_claude-3-5-sonnet-20240620",
              "deepseek-ai_deepseek-v3", "google_gemini-1.5-pro-002", "anthropic_claude-3-opus-20240229",
              "openai_gpt-4o-2024-08-06", "meta_llama-3.1-405b-instruct-turbo", "openai_gpt-4o-2024-05-13",
              "openai_gpt-4-0613", "qwen_qwen2.5-72b-instruct-turbo"],
    "flagged": {"all": 1207, "miskey": 80, "ok": 354, "other_error": 50, "unsure_or_conflict": 8,
                "unreviewed": 715},
    "precision": (130, 484),
}
EXPECTED_82_NOKEY = {"all": 88, "miskey": 23, "ok": 10, "other_error": 4, "unsure_or_conflict": 0,
                     "unreviewed": 51}
# Audit 85's published results, rounded to 2 decimals where they are not counts.
EXPECTED_85 = {
    "tiers": {1: 88, 2: 239, 3: 882, 0: 12775},
    "queue": 716,
    "mae_tier": 115.49,
    "mae_subject": 91.3,
    "est_tier": 150.8,
    "est_subject": 92.55,
}

# ----- HELM (as audits 80-85) -----
N_SUBJECTS = 57
HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/mmlu/benchmark_output"
HELM_RELEASE = "v1.13.0"
MIN_COVERAGE = Fraction(99, 100)
MIN_CONSISTENT = Fraction(99, 100)
MAX_EM_GAP = Fraction(5, 1000)
WORKERS = 12

# ----- MMLU-Redux 2.0 (as audits 80-85) -----
REDUX_DATASET = "edinburgh-dawg/mmlu-redux-2.0"
REDUX_SPLIT = "test"
ABORT_REDUX_JOINED = 4000

# ----- Fixture A: two subjects, two folds, all twelve questions judged -----
FIX_SUBJ = {q: ("a" if q < 6 else "b") for q in range(12)}
FIX_TIERS = {0: 1, 1: 3, 2: 0, 3: 1, 4: 3, 5: 0, 6: 1, 7: 3, 8: 0, 9: 1, 10: 3, 11: 0}
FIX_FOLD = {0: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 0, 7: 0, 8: 0, 9: 1, 10: 1, 11: 1}
FIX_TARGET = {0, 3, 6, 7, 8, 9, 10}
FIX_JUDGED = set(range(12))

# Fold 0 is predicted from fold 1 = {3, 4, 5, 9, 10, 11}: tier rates T1 1, T3 1/2, T0 0, pooled 1/2.
FIX_TRAIN_F0 = {3, 4, 5, 9, 10, 11}
FIX_RATE_F0 = {1: Fraction(1), 3: Fraction(1, 2), 0: Fraction(0)}
FIX_POOLED_F0 = Fraction(1, 2)
FIX_FACTORS_F0 = {"a": Fraction(4, 5), "b": Fraction(6, 5)}

FIX_ADJ = [
    {"fold": 0, "n_test": 6, "actual": 4, "adj_expected": Fraction(14, 5), "mae_adj": Fraction(8, 5)},
    {"fold": 1, "n_test": 6, "actual": 3, "adj_expected": Fraction(11, 3), "mae_adj": Fraction(2, 3)},
]
# base87.cross_fold on fixture A: (mae_subject, mae_tier) per fold.
FIX_BASE_MAE = [(Fraction(1), Fraction(2)), (Fraction(1), Fraction(1))]

# ----- Fixture B: the bootstrap's two degenerate cases -----
FIX_B_TIERS = {q: 1 for q in range(6)}
FIX_B_SUBJ = {0: "a", 1: "a", 2: "a", 3: "b", 4: "b", 5: "b"}
FIX_PCT = [(1, (0, 0)), (40, (1, 38)), (1000, (25, 974))]

# ----- Fixture C: verdicts -----
FIX_V_BASE = [{"mae_subject": Fraction(1), "mae_tier": Fraction(2)},
              {"mae_subject": Fraction(1), "mae_tier": Fraction(1)}]
FIX_V_ADJ_ERR = [{"mae_adj": Fraction(1, 2)}, {"mae_adj": Fraction(1, 4)}]
FIX_V_BASE_ERR = [{"mae_subject": Fraction(1), "mae_tier": Fraction(0)},
                  {"mae_subject": Fraction(0), "mae_tier": Fraction(0)}]
FIX_V_BOOT = [(3, 5), (0, 2)]
FIX_V_EST = (Fraction(5), Fraction(7), Fraction(4))     # adjusted, tier, subject
FIX_VERDICTS = {
    "P2_adjusted_beats_subject": False, "P2_mae": [float(Fraction(34, 15)), 2.0, 3.0],
    "P3_interval_covers": False, "P3_folds": [[4, 2.8, 3, 5], [3, float(Fraction(11, 3)), 0, 2]],
    "P4_between": True, "P4_estimates": [5.0, 4.0, 7.0],
    "P5_errors_adjusted_beats_subject": True, "P5_mae": [0.75, 1.0],
}
