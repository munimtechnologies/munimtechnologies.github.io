"""Audit 93: data source, gates, thresholds and the hand-traced fixtures (traces in test_grade93.py). Apache-2.0."""

from fractions import Fraction

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/audio/benchmark_output"
SUITE = "v1.0.0"  # AHELM's published suite (crfm.stanford.edu/helm/audio/latest/config.js, checked 2026-11-09)
# The seven run groups whose main metric is wer_score in HELM's schema_audio.yaml.
GROUPS = ("librispeech", "librispeech_fairness", "multilingual_librispeech", "fleurs", "fleurs_fairness",
          "speech_robust_bench", "ami")
WORKERS = 8

# Gates
TOL = 1e-6                    # |our mean of per-record values - HELM's stats.json mean|, per run and per cell
MIN_GROUPS_LOADED = 6         # of the 7 group pages
MIN_RUNS_REPRODUCED = Fraction(99, 100)   # share of listed runs that download and reproduce HELM's main stat
MIN_CELLS_REPRODUCED = Fraction(95, 100)  # share of headline WER cells reproduced as the mean of their runs
MIN_RUNS = 100
ABORT_RUNS_REPRODUCED = Fraction(90, 100)

THRESHOLDS = {"P3_share": Fraction(1, 2), "P4_share": Fraction(1, 100), "P5_rise": 0.01, "P6_min": 1}
PRINT_EMPTIES = 40
PRINT_PUNCT = 20

# ---- Fixtures ----
FIX_NORM = [("Hello, World!", "hello world"), ("  A-B  c. ", "ab c"), ("...", ""), ("The cat", "the cat"),
            ("。", "。")]
FIX_CLASS = [("", "empty"), ("  \n ", "empty"), (None, "missing"), ("...", "punct_only"), (" - ", "punct_only"),
             ("hi", "text"), ("。", "text")]
FIX_MODEL = [("librispeech:model=google_gemini-1.5-pro-001", "google_gemini-1.5-pro-001", True),
             ("speech_robust_bench:subject=librispeech_gnoise,level=1,model=openai_whisper-1_gpt-4o-2024-11-20",
              "openai_whisper-1_gpt-4o-2024-11-20", False)]
FIX_RECORDS = [
    {"instance_id": "id0", "train_trial_index": 0, "predicted_text": "hello there",
     "stats": {"wer_score": 0.5, "mer_score": 0.5}},
    {"instance_id": "id1", "train_trial_index": 0, "predicted_text": "", "stats": {"wer_score": 0.0, "mer_score": 0.0}},
    {"instance_id": "id2", "train_trial_index": 0, "predicted_text": "exact",
     "stats": {"wer_score": 0.0, "mer_score": 0.0}},
    {"instance_id": "id3", "train_trial_index": 0, "predicted_text": "...",
     "stats": {"wer_score": 1.0, "mer_score": 1.0}},
    {"instance_id": "id3", "train_trial_index": 0, "predicted_text": "x", "stats": {"wer_score": 9.0}},
    {"instance_id": "id4", "train_trial_index": 1, "predicted_text": "", "stats": {"wer_score": 0.0}},
    {"instance_id": "id5", "train_trial_index": 0, "predicted_text": " ", "stats": {"wer_score": 0.25}},
]
FIX_RUN_TARGET = {
    "counts": {"n_records": 7, "other_trial": 1, "duplicate": 1, "perturbed": 0, "kept": 5},
    "classes": {"missing": 0, "empty": 2, "punct_only": 1, "text": 2},
    "metrics": {
        "wer_score": {"n": 5, "sum": 1.75, "n_empty": 2, "empty_nonzero": 1, "sum_empty": 0.25,
                      "corrected_sum": 3.5, "zeros": 2, "zero_empty": 1},
        "mer_score": {"n": 4, "sum": 1.5, "n_empty": 1, "empty_nonzero": 0, "sum_empty": 0.0,
                      "corrected_sum": 2.5, "zeros": 2, "zero_empty": 1},
    },
    "empty_ids": ["id1", "id5"],
    "punct_ids": ["id3"],
}
FIX_STATS = [
    {"name": {"name": "wer_score", "split": "test", "perturbation": {"name": "robustness"}}, "mean": 9.0, "count": 1},
    {"name": {"name": "wer_score", "split": "test"}, "mean": 0.3, "count": 1},
    {"name": {"name": "num_instances", "split": "test"}, "mean": 500.0, "count": 1},
]
FIX_STAT_TARGET = {"wer_score": 0.3, "num_instances": 500.0, "cer_score": None}
FIX_GROUP = [
    {"title": "", "header": [{"value": "Model"}, {"value": "WER", "lower_is_better": True}, {"value": "# eval"}],
     "rows": [[{"value": "M1", "run_spec_names": ["x:model=m1"]},
               {"value": 0.2, "run_spec_names": ["x:model=m1", "y:model=m1"]},
               {"value": 500, "run_spec_names": ["x:model=m1", "y:model=m1", "z:model=m1"]}],
              [{"value": "M2"}, {"value": None}, {"value": 5}]]},
    {"title": "sub", "rows": [[{"value": "M1", "run_spec_names": ["q:model=m1"]}]]},
]
FIX_GROUP_RUNS = {"x:model=m1", "y:model=m1", "z:model=m1", "q:model=m1"}
FIX_GROUP_CELLS = [("M1", 0.2, ["x:model=m1", "y:model=m1"])]
FIX_RANKS_IN = {"a": 0.1, "b": 0.2, "c": 0.2, "d": 0.05}
FIX_RANKS_OUT = {"d": 1, "a": 2, "b": 3, "c": 3}
# predictions93(n_empty, empty_all_zero, n_empty_gemini, n_records, max_cell_rise, models_rank_changed, runs_multi_ref)
FIX_V_CASES = [
    ((10, True, 5, 1000, 0.01, 1, 0),
     {"P2_guard_live": True, "P3_gemini_majority": True, "P4_rare": True, "P5_headline_moves": True,
      "P6_rank_changes": True, "P7_single_reference": True}),
    ((11, False, 5, 1000, 0.0099, 0, 1),
     {"P2_guard_live": False, "P3_gemini_majority": False, "P4_rare": False, "P5_headline_moves": False,
      "P6_rank_changes": False, "P7_single_reference": False}),
    ((0, True, 0, 1000, 0.0, 0, 0),
     {"P2_guard_live": False, "P3_gemini_majority": False, "P4_rare": True, "P5_headline_moves": False,
      "P6_rank_changes": False, "P7_single_reference": True}),
]
