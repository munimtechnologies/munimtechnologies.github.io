# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Audit 114: desk check of HELM's MIMIC-IV Billing Code ICD-code extraction.

HELM_PATTERN and helm_extract() are transcribed from stanford-crfm/helm,
src/helm/benchmark/metrics/mimiciv_billing_code_metrics.py (Apache-2.0; file last changed in
commit 859a823, 2025-08-22). The gold string is built by HELM's scenario as ",".join(codes).

edin_format() re-implements the documented behaviour of reformat_icd10() in
JoakimEdin/medical-coding-reproducibility, prepare_data/utils.py (commit 1087eac), the
repository HELM's maintainers name as the source of this dataset (HELM issue #3689):
ICD-10 diagnosis codes get a period after the third character (always, so 'I10' becomes
'I10.'), ICD-10-PCS procedure codes keep no period, and the target is procedures plus
diagnoses. It is written from that behaviour, not copied.

Every code below is a format example from the public ICD-10-CM / ICD-10-PCS code sets.
None is a value from MIMIC-IV. Standard library only.
"""
import json
import re

HELM_PATTERN = r"\b[A-Z]\d{1,3}(?:\.\d{1,4})?\.?\b"


def helm_extract(text):
    """HELM's MIMICIVBillingCodeMetric.extract_icd_codes, transcribed."""
    if not text:
        return []
    cleaned_text = re.sub(r"\*\*", "", text)
    codes = re.findall(HELM_PATTERN, cleaned_text)
    return [code.rstrip(".").strip() for code in codes]


def edin_format(code, is_diag):
    """Format of one code in the dataset's target list (see module docstring)."""
    code = "".join(code.split("."))
    if not is_diag:
        return code
    return code[:3] + "." + code[3:]


def full_code(code):
    """A code compared in full: periods removed, upper case."""
    return code.replace(".", "").strip().upper()


def f1(ref, pred):
    """Micro F1 of one instance, as HELM computes it with scikit-learn (2tp / (|ref| + |pred|))."""
    ref, pred = set(ref), set(pred)
    tp = len(ref & pred)
    if tp == 0:
        return 0.0
    precision = tp / len(pred)
    recall = tp / len(ref)
    return 2 * precision * recall / (precision + recall)


def helm_f1(gold_codes, prediction_text):
    """HELM's per-instance F1: gold_codes is a list of (raw code, is_diag)."""
    gold_text = ",".join(edin_format(c, d) for c, d in gold_codes)
    return f1(helm_extract(gold_text), helm_extract(prediction_text))


def full_f1(gold_codes, predicted_codes):
    """F1 with every gold code compared in full."""
    return f1([full_code(c) for c, _ in gold_codes], [full_code(c) for c in predicted_codes])


# (format class, raw code without a period, is_diag)
CODES = [
    ("cm_three_characters", "I10", True),
    ("cm_digits_after_period", "E119", True),
    ("cm_digits_after_period", "I5023", True),
    ("cm_letter_after_period", "S72001A", True),
    ("cm_letter_after_period", "T380X5A", True),
    ("cm_letter_after_period", "W19XXXA", True),
    ("cm_letter_in_third_place", "Z3A38", True),
    ("cm_letter_in_third_place", "C7A00", True),
    ("pcs_procedure", "0DTJ4ZZ", False),
    ("pcs_procedure", "5A1955Z", False),
    ("pcs_procedure", "BW03ZZZ", False),
    ("pcs_procedure", "XW033E5", False),
]


def classify(raw, is_diag):
    """What HELM's extraction keeps of one gold code: intact, truncated or dropped."""
    got = helm_extract(edin_format(raw, is_diag))
    if not got:
        return "dropped", got
    if len(got) == 1 and full_code(got[0]) == full_code(raw):
        return "intact", got
    if len(got) == 1 and full_code(raw).startswith(full_code(got[0])):
        return "truncated", got
    return "other", got


# Instance-level examples: (name, gold codes, prediction text, predicted codes in full)
EXAMPLES = [
    ("procedure_never_scored", [("0DTJ4ZZ", False), ("E119", True), ("I10", True)], "E11.9, I10", ["E119", "I10"]),
    ("wrong_extension_credited", [("S72001A", True)], "S72.92XA", ["S7292XA"]),
    ("two_codes_collapse", [("S72001A", True), ("S72002A", True)], "S72.001A", ["S72001A"]),
    ("gestation_code_dropped", [("Z3A38", True), ("O80", True)], "O80", ["O80"]),
]


def run():
    rows = []
    counts = {}
    for cls, raw, is_diag in CODES:
        verdict, got = classify(raw, is_diag)
        rows.append({"class": cls, "code": raw, "gold_form": edin_format(raw, is_diag),
                     "helm_extracts": got, "verdict": verdict})
        counts[verdict] = counts.get(verdict, 0) + 1
    examples = []
    for name, gold, text, pred_full in EXAMPLES:
        examples.append({"example": name, "helm_f1": round(helm_f1(gold, text), 4),
                         "full_code_f1": round(full_f1(gold, pred_full), 4)})
    return {"audit": 114, "pattern": HELM_PATTERN, "codes": rows, "verdict_counts": counts,
            "examples": examples}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
