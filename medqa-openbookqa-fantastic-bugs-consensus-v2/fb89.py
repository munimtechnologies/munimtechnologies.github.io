"""Answer-level consensus inside one reviewed sample: new logic for audit 89 (copied unchanged into v2).

Fantastic Bugs (Truong et al., NeurIPS 2025 Datasets and Benchmarks, arXiv 2511.16842; data stair-lab/fantastic-bugs,
MIT) published expert reviews of the most anomalous MedQA and OpenBookQA items, ranked by an item statistic on HELM
Lite's right/wrong matrices. Unlike most of their MMLU splits, both splits hold items the reviewers judged valid and
items they judged invalid, so audit 77's consensus flag can be compared on the two kinds inside one benchmark and one
selection. This file reads the reviews into frozen categories, finds a reviewer's suggested option where the review
names one, and scores the pre-registered predictions. Standard library only. Apache-2.0. Authored by AI agents
working in the name of MV2, Munim, Inc.
"""

from fractions import Fraction

from base89 import norm

SPLITS = ("med_qa", "openbookqa")
CATEGORIES = ("invalid", "unclear", "valid")
_WORDS = {"med_qa": {"valid": "valid", "invalid": "invalid"},
          "openbookqa": {"correct": "valid", "incorrect": "invalid"}}
_STRIP = ",.:;!?"


def _lower(review):
    return norm(review).lower()


def _first_word(r):
    return r.split(" ", 1)[0].strip(_STRIP) if r else ""


def fb_category(split, review):
    """A Fantastic Bugs review -> 'valid', 'invalid' or 'unclear'. MedQA: first word 'valid' / 'invalid'. OpenBookQA:
    first word 'correct' (the key is right) / 'incorrect' (the key is wrong). Anything else, or another split, is
    'unclear' and left out of every prediction."""
    return _WORDS.get(split, {}).get(_first_word(_lower(review)), "unclear")


def suggested_option(review, options):
    """For a review whose first word is 'incorrect': the index of the option the reviewer names, or None. The text
    after the first word (leading ' :,.-' removed) must equal one option (case-insensitive, whitespace-normalised);
    failing that, exactly one non-empty option must be a prefix of it."""
    r = _lower(review)
    if _first_word(r) != "incorrect":
        return None
    parts = r.split(" ", 1)
    rest = (parts[1] if len(parts) > 1 else "").lstrip(" :,.-")
    opts = [norm(o).lower() for o in (options or [])]
    exact = [i for i, o in enumerate(opts) if o == rest]
    if len(exact) == 1:
        return exact[0]
    pref = [i for i, o in enumerate(opts) if o and rest.startswith(o)]
    return pref[0] if len(pref) == 1 else None


def _share(t):
    return Fraction(t[0], t[1]) if t[1] else None


def predictions89(flag_inv, flag_val, auc_med, flag_obqa_val, th):
    """Pre-registered verdicts P2-P6 (P1 is decided in job.py). flag_inv / flag_val: (flagged, n) among placed MedQA
    items reviewed invalid / valid; auc_med: (margin AUC invalid vs valid as a Fraction or None, n invalid, n valid);
    flag_obqa_val: (flagged, n) among placed OpenBookQA items reviewed correct. A verdict whose groups are smaller
    than th's minimum (or whose AUC is missing) is False and listed as undecidable."""
    mn, mv = th["min_n"], th["min_n_valid"]
    und = []

    def need(name, ok):
        if not ok:
            und.append(name)
        return ok

    v = {}
    n = "P2_consensus_separates_medqa"
    v[n] = bool(need(n, flag_inv[1] >= mn and flag_val[1] >= mn) and _share(flag_inv) > _share(flag_val))
    n = "P3_margin_auc_medqa"
    v[n] = bool(need(n, auc_med[1] >= mn and auc_med[2] >= mn and auc_med[0] is not None)
                and auc_med[0] >= th["P3_min_auc"])
    n = "P4_medqa_valid_quiet"
    v[n] = bool(need(n, flag_val[1] >= mv) and _share(flag_val) <= th["P4_max_share"])
    n = "P5_openbookqa_valid_quiet"
    v[n] = bool(need(n, flag_obqa_val[1] >= mv) and _share(flag_obqa_val) <= th["P5_max_share"])
    n = "P6_medqa_invalid_caught"
    v[n] = bool(need(n, flag_inv[1] >= mn) and _share(flag_inv) >= th["P6_min_share"])
    v["undecidable"] = sorted(und)
    return v
