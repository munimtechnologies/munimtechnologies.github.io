"""Configuration, pinned audit-72 numbers, pre-registered thresholds and hand-traced fixtures for audit 74.
Thresholds were written on 2026-11-01 before any audit-74 number existed (audit 72's numbers were known and are
pinned below as a structural gate). Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc."""

import cases

# ----- audit 72, pinned (structural gate P1) -----
AUDIT72_FOCUS_MISALIGNED = {"zh": 180, "ko": 113}
AUDIT72_FLAGGED = ["ig|professional_law", "it|professional_law", "ja|moral_scenarios", "ja|professional_law",
                   "ko|high_school_world_history", "ny|professional_law", "sn|professional_law",
                   "so|professional_law", "tr|professional_law", "zh|high_school_world_history"]
FOCUS_N = 237                  # rows of high_school_world_history; English positions must be exactly 0..236

# ----- pre-registered -----
CAP = 8                        # fingerprint groups with more than CAP rows on either side stay unmatched
P3_MIN_KEEP = 0.90             # capped zh / ko focus misaligned >= this share of audit 72's 180 / 113, each
P4_MIN_N = 20
P4_MIN_CONTENT_KEY = 0.95      # capped zh+ko focus misaligned rows carrying the held question's key
P5_MIN_FILL = 0.50             # unmatched zh+ko focus rows that neighbour inference fills (pooled)
P6_MIN_MADE = 50
P6_MIN_AGREE = 0.90            # leave-one-out inferences equal to the fingerprint match (pooled zh+ko)
P7_MIN_N = 20
P7_MIN_KEY = 0.90              # inferred rows holding another question that carry that question's key (pooled)

# ----- hand-traced fixtures (reuse audit 72's FIXTURE_EN / FIXTURE_XX) -----
FIXTURE_EN = cases.FIXTURE_EN
FIXTURE_XX = cases.FIXTURE_XX

# cap 1: the ("1955",) group has 2 rows on each side -> over_cap; ("2000","2001") has no English partner.
FIXTURE_CAP1_MAPPING = {"s/test/1": "s/test/2", "s/test/2": "s/test/1", "s/test/4": "s/test/5"}
FIXTURE_CAP1_STATS = {"n": 7, "no_fingerprint": 1, "count_differs": 1, "over_cap": 2, "mapped": 3, "aligned": 0,
                      "misaligned": 3}
FIXTURE_CAP1_KEYS = {"misaligned": 3, "mis_key_equals_content": 3, "mis_key_equals_id": 0}
# cap 2 behaves exactly like align.align on this fixture.
FIXTURE_CAP2_STATS = {"n": 7, "no_fingerprint": 1, "count_differs": 1, "over_cap": 0, "mapped": 5, "aligned": 2,
                      "misaligned": 3}
FIXTURE_OFFSETS = {0: 0, 1: 1, 2: -1, 3: 0, 4: 1}

# infer: n=10; matched offsets below. 1 and 3 sit between different offsets; 5 -> 3 and 7 -> 5 (both neighbours -2);
# 8 -> 6 is blocked because position 2 already holds 6.
INFER_N = 10
INFER_OFFSETS = {0: 0, 2: 4, 4: -2, 6: -2, 9: -2}
INFER_TARGETS = [1, 3, 5, 7, 8]
INFER_EXPECTED = {5: 3, 7: 5}
# no matched position before 0 -> nothing.
INFER_EDGE = (3, {1: -1, 2: -1}, [0], {})
# 1 -> 4 is fine; 2 -> 5 is out of range for n=5.
INFER_RANGE = (5, {0: 3, 3: 3}, [1, 2], {1: 4})
# leave-one-out on INFER_OFFSETS: only position 6 gets an inference (from 4 and 9, both -2) and it is right.
LOO_EXPECTED = {"tested": 5, "made": 1, "agree": 1}

# build_map on audit 72's fixture with its mapping and a hand-given inference {5: 4}.
MAP_INFERRED = {5: 4}
MAP_EXPECTED = [
    {"sample_id": "s/test/0", "position": 0, "holds_position": 0, "how": "fingerprint", "key_fits_held": True,
     "key_fits_own_position": True, "label_on_row": "-", "label_of_held": "-"},
    {"sample_id": "s/test/1", "position": 1, "holds_position": 2, "how": "fingerprint", "key_fits_held": True,
     "key_fits_own_position": False, "label_on_row": "-", "label_of_held": "-"},
    {"sample_id": "s/test/2", "position": 2, "holds_position": 1, "how": "fingerprint", "key_fits_held": True,
     "key_fits_own_position": False, "label_on_row": "-", "label_of_held": "-"},
    {"sample_id": "s/test/3", "position": 3, "holds_position": 3, "how": "fingerprint", "key_fits_held": True,
     "key_fits_own_position": True, "label_on_row": "CS", "label_of_held": "CS"},
    {"sample_id": "s/test/4", "position": 4, "holds_position": 5, "how": "fingerprint", "key_fits_held": True,
     "key_fits_own_position": False, "label_on_row": "-", "label_of_held": "CA"},
    {"sample_id": "s/test/5", "position": 5, "holds_position": 4, "how": "neighbours", "key_fits_held": True,
     "key_fits_own_position": False, "label_on_row": "CA", "label_of_held": "-"},
    {"sample_id": "s/test/6", "position": 6, "holds_position": None, "how": "unresolved", "key_fits_held": None,
     "key_fits_own_position": True, "label_on_row": "-", "label_of_held": None},
]
SUMMARY_EXPECTED = {"n": 7, "fingerprint": 5, "neighbours": 1, "unresolved": 1, "holds_other": 4,
                    "holds_other_fingerprint": 3, "holds_other_neighbours": 1, "holds_other_key_fits_held": 4,
                    "neighbours_other_key_fits_held": 1, "neighbours_other_key_fits_own": 0, "label_wrong": 2}

FIXTURE_TARGET = {
    "cap1_mapping": FIXTURE_CAP1_MAPPING, "cap1_stats": FIXTURE_CAP1_STATS, "cap1_keys": FIXTURE_CAP1_KEYS,
    "cap2_stats": FIXTURE_CAP2_STATS, "offsets": FIXTURE_OFFSETS, "infer": INFER_EXPECTED,
    "infer_edge": INFER_EDGE[3], "infer_range": INFER_RANGE[3], "loo": LOO_EXPECTED, "map": MAP_EXPECTED,
    "summary": SUMMARY_EXPECTED,
}
