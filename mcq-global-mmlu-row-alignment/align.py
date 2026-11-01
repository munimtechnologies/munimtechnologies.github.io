"""Global-MMLU ROW-ALIGNMENT check (audit 72): does each translated row hold the same question as the English row with
the same sample_id?

Audit 71 (mcq-global-mmlu-key-drift) found that every one of Global-MMLU's 176 Chinese and 116 Korean answer-letter
differences from English sits in one subject, high_school_world_history. This module tests a mechanism without
translating anything: a translated row is matched to the English row holding the same question by a
language-independent FINGERPRINT, the set of digit runs of three or more digits (years, page numbers, amounts) in its
question and options. Within each fingerprint the k-th translated row (in sample_id order) is matched to the k-th
English row, when both sides have the same number of rows with that fingerprint; rows without a fingerprint, or in a
fingerprint whose counts differ, stay unmatched (never guessed).

For each matched row whose question is NOT the English question with the same sample_id (misaligned), the module
asks whether the translated answer key and annotation fields (cultural_sensitivity_label, is_annotated,
required_knowledge) follow the row's own content or its sample_id.

Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import re
import unicodedata

LETTERS = "ABCD"
OPTION_COLS = ("option_a", "option_b", "option_c", "option_d")
NUMBER_RE = re.compile(r"\d+")
MIN_RUN = 3


# ----- one row -----

def norm(s):
    return "" if s is None else unicodedata.normalize("NFKC", str(s)).strip()


def digit_runs(s):
    """Runs of at least MIN_RUN digits (any script; NFKC folds full-width) as canonical decimal strings."""
    out = []
    for m in NUMBER_RE.findall(norm(s)):
        if len(m) >= MIN_RUN:
            try:
                out.append(str(int(m)))
            except ValueError:
                out.append(m)
    return out


def fingerprint(question, options):
    """Sorted distinct digit runs of the question and all options; () when there are none."""
    runs = set(digit_runs(question))
    for o in options:
        runs.update(digit_runs(o))
    return tuple(sorted(runs))


def key_index(answer):
    """'A'..'D' (any case, outer spaces ignored) -> 0..3; anything else -> None."""
    s = "" if answer is None else str(answer).strip().upper()
    return LETTERS.index(s) if len(s) == 1 and s in LETTERS else None


def index_of(sample_id):
    """'subject/test/17' -> 17; None when the id has no integer tail."""
    try:
        return int(str(sample_id).rsplit("/", 1)[1])
    except (IndexError, ValueError):
        return None


def _order(r):
    i = index_of(r["sample_id"])
    return (i is None, i if i is not None else 0, str(r["sample_id"]))


# ----- one subject: translation against English -----

def align(en_rows, xx_rows):
    """Match translated rows to English rows of ONE subject by fingerprint, order-preserving within a fingerprint.
    Returns ({translated sample_id: English sample_id}, stats); mapped + no_fingerprint + count_differs == n."""
    def groups(rows):
        g = {}
        for r in sorted(rows, key=_order):
            if r["fp"]:
                g.setdefault(r["fp"], []).append(r["sample_id"])
        return g

    ge, gx = groups(en_rows), groups(xx_rows)
    st = {"n": len(xx_rows), "no_fingerprint": sum(1 for r in xx_rows if not r["fp"]), "count_differs": 0,
          "mapped": 0, "aligned": 0, "misaligned": 0}
    mapping = {}
    for fp in sorted(gx):
        xs, es = gx[fp], ge.get(fp, [])
        if len(xs) != len(es):
            st["count_differs"] += len(xs)
            continue
        for x, e in zip(xs, es):
            mapping[x] = e
            st["mapped"] += 1
            st["aligned" if x == e else "misaligned"] += 1
    return mapping, st


COUNTERS = ("same_id_fp_both", "same_id_fp_agree", "key_differs_same_id", "key_differs_misaligned",
            "key_differs_aligned", "key_differs_unmapped", "mis_key_equals_content", "mis_key_equals_id",
            "mis_label_wrong_for_content", "mis_label_differs", "mis_label_follows_id", "mis_label_follows_content",
            "mis_annot_differs", "mis_annot_follows_id", "mis_knowledge_differs", "mis_knowledge_follows_id")


def _add(d, k, n=1):
    d[k] = d.get(k, 0) + n


def compare_subject(en_rows, xx_rows):
    """One subject. en_rows / xx_rows: dicts with sample_id, fp, key, label, annotated, knowledge. Every translated
    row's sample_id must be in en_rows. Returns (report, mapping)."""
    en = {r["sample_id"]: r for r in en_rows}
    mapping, st = align(en_rows, xx_rows)
    rep = dict(st)
    for k in COUNTERS:
        rep[k] = 0
    rep["label_wrong_detail"] = {}
    rep["offsets"] = {}
    for x in sorted(xx_rows, key=_order):
        s = x["sample_id"]
        e = en[s]
        if x["fp"] and e["fp"]:
            rep["same_id_fp_both"] += 1
            rep["same_id_fp_agree"] += int(x["fp"] == e["fp"])
        m = mapping.get(s)
        if x["key"] != e["key"]:
            rep["key_differs_same_id"] += 1
            if m is None:
                rep["key_differs_unmapped"] += 1
            elif m == s:
                rep["key_differs_aligned"] += 1
            else:
                rep["key_differs_misaligned"] += 1
        if m is None or m == s:
            continue
        c = en[m]
        rep["mis_key_equals_content"] += int(x["key"] == c["key"])
        rep["mis_key_equals_id"] += int(x["key"] == e["key"])
        if x["label"] != c["label"]:
            rep["mis_label_wrong_for_content"] += 1
            _add(rep["label_wrong_detail"], "%s|%s" % (x["label"], c["label"]))
        if e["label"] != c["label"]:
            rep["mis_label_differs"] += 1
            if x["label"] == e["label"]:
                rep["mis_label_follows_id"] += 1
            elif x["label"] == c["label"]:
                rep["mis_label_follows_content"] += 1
        if e["annotated"] != c["annotated"]:
            rep["mis_annot_differs"] += 1
            rep["mis_annot_follows_id"] += int(x["annotated"] == e["annotated"])
        if e["knowledge"] != c["knowledge"]:
            rep["mis_knowledge_differs"] += 1
            rep["mis_knowledge_follows_id"] += int(x["knowledge"] == e["knowledge"])
        i, j = index_of(m), index_of(s)
        if i is not None and j is not None:
            _add(rep["offsets"], str(i - j))
    return rep, mapping


def content_agreement(map_a, map_b):
    """Two languages' mappings of the same subject: over ids matched in both, how often both rows hold the same
    English question, overall and where both are misaligned."""
    out = {"both_mapped": 0, "same_content": 0, "both_misaligned": 0, "both_misaligned_same_content": 0}
    for s in sorted(set(map_a) & set(map_b)):
        out["both_mapped"] += 1
        same = map_a[s] == map_b[s]
        out["same_content"] += int(same)
        if map_a[s] != s and map_b[s] != s:
            out["both_misaligned"] += 1
            out["both_misaligned_same_content"] += int(same)
    return out


# ----- Global-MMLU-Lite against the full set -----

def lite_compare(lite_rows, full_by_id, en_by_id, misaligned):
    """lite_rows / full_by_id values: dicts with options (normalised tuple), key, label, fp. misaligned: the full-set
    sample_ids of this language that hold another English question. Does Lite reuse the full-set rows?"""
    out = {"n": 0, "not_in_full": 0, "identical_to_full": 0, "key_equal_full": 0, "label_equal_full": 0,
           "on_misaligned_ids": 0, "on_misaligned_identical_to_full": 0, "on_misaligned_key_equals_en_same_id": 0,
           "on_misaligned_fp_equals_en_same_id": 0}
    for r in lite_rows:
        out["n"] += 1
        f = full_by_id.get(r["sample_id"])
        if f is None:
            out["not_in_full"] += 1
            continue
        ident = r["options"] == f["options"] and r["key"] == f["key"]
        out["identical_to_full"] += int(ident)
        out["key_equal_full"] += int(r["key"] == f["key"])
        out["label_equal_full"] += int(r["label"] == f["label"])
        if r["sample_id"] in misaligned:
            out["on_misaligned_ids"] += 1
            out["on_misaligned_identical_to_full"] += int(ident)
            e = en_by_id.get(r["sample_id"])
            if e is not None:
                out["on_misaligned_key_equals_en_same_id"] += int(r["key"] == e["key"])
                out["on_misaligned_fp_equals_en_same_id"] += int(r["fp"] == e["fp"])
    return out
