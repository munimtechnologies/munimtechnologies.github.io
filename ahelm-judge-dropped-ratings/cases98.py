"""Audit 98: data source, gates, thresholds and the hand-traced fixtures (traces in test_grade98.py). Apache-2.0."""

from fractions import Fraction

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/audio/benchmark_output"
SUITE = "v1.0.0"  # AHELM's published suite (the one audit 93 read)
# The three run groups whose main metric is gpt4_audio_critique in HELM's schema_audio.yaml (checked 2026-11-10).
GROUPS = ("audiocaps", "air_bench_chat_knowledge", "air_bench_chat_reasoning")
WORKERS = 8

# Gates
TOL_RUN = 1e-6    # |our mean of per-instance judge values - HELM's stats.json mean|
TOL_CELL = 1e-6   # |a cell's value rebuilt from its runs - the published cell value|
MIN_GROUPS_LOADED = 3
MIN_RUNS = 50
MIN_RUNS_REPRODUCED = Fraction(95, 100)
MIN_CELLS_REPRODUCED = Fraction(90, 100)
ABORT_RUNS_REPRODUCED = Fraction(1, 2)

THRESHOLDS = {"P3_share": Fraction(1, 100), "P4_share": Fraction(1, 2), "P5_fall": 0.01, "P6_min": 1,
              "P7_share": Fraction(1, 2)}
PRINT_UNJUDGED = 40
PRINT_RATING_TEXT = 10

# ---- Fixtures ----
FIX_MODEL = [("air_bench_chat:subject=music,model=qwen_qwen2-audio-7b-instruct", "qwen_qwen2-audio-7b-instruct"),
             ("audiocaps:model=openai_gpt-4o-mini-transcribe_gpt-4o-2024-11-20",
              "openai_gpt-4o-mini-transcribe_gpt-4o-2024-11-20"),
             ("nomodel", "")]
FIX_CLASS = [(None, "missing"), ("   ", "empty"), ("Rating:4 good", "rating_text"), ("Rating: 6", "text"),
             ("**Rating:** 3", "text"), ("The rating: 2", "text"), ("x Rating:\n2", "rating_text")]
FIX_RECORDS = [
    {"instance_id": "id0", "train_trial_index": 0, "predicted_text": "A dog barks.",
     "stats": {"gpt4_audio_critique": 4.0}},
    {"instance_id": "id1", "train_trial_index": 0, "predicted_text": "", "stats": {"num_output_tokens": 0.0}},
    {"instance_id": "id2", "train_trial_index": 0, "predicted_text": "Rating: 5", "stats": {"gpt4_audio_critique": 5.0}},
    {"instance_id": "id3", "train_trial_index": 0, "predicted_text": "Music plays",
     "stats": {"gpt4_audio_critique": None}},
    {"instance_id": "id3", "train_trial_index": 0, "predicted_text": "dup", "stats": {"gpt4_audio_critique": 1.0}},
    {"instance_id": "id4", "train_trial_index": 1, "predicted_text": "x", "stats": {"gpt4_audio_critique": 1.0}},
    {"instance_id": "id5", "train_trial_index": 0, "predicted_text": "rain", "perturbation": {"name": "robustness"},
     "stats": {"gpt4_audio_critique": 2.0}},
    {"instance_id": "id6", "train_trial_index": 0, "predicted_text": None, "stats": {"gpt4_audio_critique": 2.5}},
    {"instance_id": "id7", "train_trial_index": 0, "predicted_text": "  rating: 3 ",
     "stats": {"gpt4_audio_critique": True}},
]
FIX_RUN_TARGET = {
    "counts": {"n_records": 9, "other_trial": 1, "perturbed": 1, "duplicate": 1, "kept": 6},
    "classes": {"missing": 1, "empty": 1, "rating_text": 1, "text": 3},
    "judged": 3, "sum": 11.5,
    "hist": {"1": 0, "2": 0, "3": 0, "4": 1, "5": 1, "other": 1},
    "unjudged": [("id1", "empty"), ("id3", "text"), ("id7", "text")],
    "unjudged_classes": {"missing": 0, "empty": 1, "rating_text": 0, "text": 2},
    "rating_text": [("id2", 5.0)],
}
FIX_STATS = [
    {"name": {"name": "gpt4_audio_critique", "split": "test", "perturbation": {"name": "robustness"}},
     "count": 5, "sum": 5.0, "mean": 1.0},
    {"name": {"name": "gpt4_audio_critique", "split": "test"}, "count": 998, "sum": 2994.0, "mean": 3.0},
    {"name": {"name": "num_instances", "split": "test"}, "count": 1, "sum": 1000.0, "mean": 1000.0},
    "junk",
]
FIX_STAT_TARGET = {"gpt4_audio_critique": {"count": 998, "sum": 2994.0, "mean": 3.0},
                   "num_instances": {"count": 1, "sum": 1000.0, "mean": 1000.0},
                   "bleu_4": None}
FIX_SPECS = [
    ({"metric_specs": [{"class_name": "helm.benchmark.metrics.basic_metrics.BasicGenerationMetric", "args": {}},
                       {"class_name": "helm.benchmark.metrics.gpt4_audio_critique_metrics.GPT4AudioCritiqueMetric",
                        "args": {"num_respondents": 1, "max_tokens": 200}}]}, 1),
    ({"metric_specs": []}, None),
    (None, None),
]
FIX_CORRECTED = [((10.0, 3, 1), 2.75), ((8.0, 2, 0), 4.0), ((0.0, 0, 0), None)]
FIX_GROUP = [
    {"title": "", "header": [{"value": "Model"}, {"value": "GPT-4o Judge Critique"}, {"value": "# eval"}],
     "rows": [[{"value": "M1"}, {"value": 3.0, "run_spec_names": ["a:model=m1", "b:model=m1"]}, {"value": 1000}],
              [{"value": "M2"}, {"value": None}, {"value": 5}],
              [{"value": "M3"}, {"value": 2.5, "run_spec_names": ["a:model=m3"]}, {"value": 500}]]},
    {"title": "sub", "rows": []},
]
FIX_GROUP_CELLS = [("M1", 3.0, ["a:model=m1", "b:model=m1"]), ("M3", 2.5, ["a:model=m3"])]
FIX_GROUP_NO_COL = [{"title": "", "header": [{"value": "Model"}, {"value": "BLEU-4"}], "rows": []}]
# cell_rule(value, [(count, sum)], tol)
FIX_RULES = [
    ((3.1, [(500, 1500.0), (500, 1600.0)]), "pooled"),
    ((3.5, [(400, 1200.0), (500, 2000.0)]), "mean_of_means"),
    ((3.6, [(400, 1200.0), (500, 2000.0)]), None),
    ((3.0, []), None),
    ((3.0, [(0, 0.0)]), None),
]
# cell_value(rule, [(count, sum, dropped)])
FIX_CELL_VALUES = [
    (("pooled", [(500, 1500.0, 0), (498, 1494.0, 2)]), 2.996),
    (("mean_of_means", [(400, 1200.0, 0), (3, 12.0, 1)]), 3.125),
    (("pooled", [(500, 1500.0, 0), (500, 1600.0, 0)]), 3.1),
    ((None, [(500, 1500.0, 0)]), None),
]
FIX_RANKS_IN = {"a": 3.0, "b": 2.0, "c": 3.0, "d": 4.5}
FIX_RANKS_OUT = {"d": 1, "a": 2, "c": 2, "b": 4}
FIX_TOPK = ({"m1": 5, "m2": 1, "m3": 3, "m4": 2}, 3, 10)
# predictions98(dropped, requested, top3, max_cell_fall, models_rank_changed, unjudged_empty, unjudged)
FIX_V_CASES = [
    ((10, 1000, 5, 0.01, 1, 4, 10),
     {"P2_drops_live": True, "P3_drops_rare": True, "P4_concentrated": True, "P5_headline_falls": True,
      "P6_rank_changes": True, "P7_not_mainly_empty": True}),
    ((11, 1000, 5, 0.0099, 0, 5, 10),
     {"P2_drops_live": True, "P3_drops_rare": False, "P4_concentrated": False, "P5_headline_falls": False,
      "P6_rank_changes": False, "P7_not_mainly_empty": False}),
    ((0, 1000, 0, 0.0, 0, 0, 0),
     {"P2_drops_live": False, "P3_drops_rare": True, "P4_concentrated": False, "P5_headline_falls": False,
      "P6_rank_changes": False, "P7_not_mainly_empty": False}),
    ((1, 0, 1, None, 2, 0, 1),
     {"P2_drops_live": True, "P3_drops_rare": False, "P4_concentrated": True, "P5_headline_falls": False,
      "P6_rank_changes": True, "P7_not_mainly_empty": True}),
]
