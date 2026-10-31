"""MMMLU ROW-ALIGNMENT helpers (audit 73): does each row of OpenAI's MMMLU hold the MMLU question at the same position,
and did Global-MMLU copy MMMLU's rows position for position?

Audits 71 and 72 traced Global-MMLU's Chinese and Korean answer-key differences to misplaced rows in one subject.
Global-MMLU (arXiv 2412.03304) took ten of its languages from MMMLU, and openai/MMMLU discussion 13 (October 2024)
noted that MMMLU's ZH_CN and KO_KR high_school_world_history questions are in a different order from MMLU's. This
module puts MMMLU rows on MMLU's positional sample_ids ('subject/test/k', k counted within the subject in file
order, the ids Global-MMLU uses) so that align.compare_subject can count the misplaced rows without translating.

Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import hashlib

import align as al

MMMLU_OPTION_COLS = ("A", "B", "C", "D")
SUM_KEYS = ("n", "no_fingerprint", "count_differs", "mapped", "aligned", "misaligned") + al.COUNTERS


def canon_subject(s):
    """MMMLU Subject -> MMLU subject name. Some SW_KE / YO_NG rows carry file names such as
    'college_mathematics_test.csv_sw-KE.csv' (openai/MMMLU discussion 15); keep the part before '_test'."""
    t = al.norm(s)
    if ".csv" in t:
        t = t.split("_test")[0]
    return t


def digest(question, options):
    """Short sha256 of the normalised question and options, to test row identity without keeping text."""
    parts = [al.norm(question)] + [al.norm(o) for o in options]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]


def _blank(sample_id, subject, fp, key):
    return {"sample_id": sample_id, "subject": subject, "fp": fp, "key": key, "label": "-", "annotated": False,
            "knowledge": ""}


def english_rows(records):
    """cais/mmlu 'all' test records in file order (question, subject, choices, answer 0-3) -> rows with positional
    sample_ids."""
    seen, rows = {}, []
    for rec in records:
        subj = al.norm(rec.get("subject"))
        k = seen.get(subj, 0)
        seen[subj] = k + 1
        choices = list(rec.get("choices") or [])
        ans = rec.get("answer")
        key = ans if isinstance(ans, int) and not isinstance(ans, bool) and 0 <= ans <= 3 else None
        rows.append(_blank("%s/test/%d" % (subj, k), subj, al.fingerprint(rec.get("question"), choices), key))
    return rows


def mmmlu_rows(en_rows, records):
    """One MMMLU config in file order, put on English BY POSITION: row i takes English row i's sample_id and subject.
    Returns (rows, tally); tally counts rows whose own Subject (canonicalised) agrees with English's."""
    tally = {"n": len(records), "subject_agree": 0, "subject_malformed": 0}
    rows = []
    for i, rec in enumerate(records):
        if i >= len(en_rows):
            break
        e = en_rows[i]
        raw = al.norm(rec.get("Subject"))
        if ".csv" in raw:
            tally["subject_malformed"] += 1
        if canon_subject(raw) == e["subject"]:
            tally["subject_agree"] += 1
        options = [rec.get(c) for c in MMMLU_OPTION_COLS]
        r = _blank(e["sample_id"], e["subject"], al.fingerprint(rec.get("Question"), options),
                   al.key_index(rec.get("Answer")))
        r["digest"] = digest(rec.get("Question"), options)
        rows.append(r)
    return rows, tally


def compare_language(en_by_subject, rows, flag_min, focus_subject):
    """Every subject of one positional translation against English. Returns (total, cells, misaligned_ids, flagged,
    focus_mapping): cells keeps subjects with any misaligned row or same-position key difference; flagged lists
    subjects with at least flag_min misaligned rows."""
    by_subject = {}
    for r in rows:
        by_subject.setdefault(r["subject"], []).append(r)
    total, cells, misaligned, flagged, focus_mapping = {}, {}, set(), [], {}
    for subj in sorted(by_subject):
        rep, mapping = al.compare_subject(en_by_subject[subj], by_subject[subj])
        for k in SUM_KEYS:
            total[k] = total.get(k, 0) + rep[k]
        misaligned.update(s for s, m in mapping.items() if s != m)
        if rep["misaligned"] or rep["key_differs_same_id"]:
            cells[subj] = rep
        if rep["misaligned"] >= flag_min:
            flagged.append(subj)
        if subj == focus_subject:
            focus_mapping = mapping
    return total, cells, misaligned, flagged, focus_mapping


def gm_row(rec):
    """One Global-MMLU record (sample_id, question, option_a..d, answer letter) -> compact row."""
    options = [rec.get(c) for c in al.OPTION_COLS]
    return {"sample_id": al.norm(rec.get("sample_id")), "digest": digest(rec.get("question"), options),
            "fp": al.fingerprint(rec.get("question"), options), "key": al.key_index(rec.get("answer"))}


def inherit_compare(gm_rows, mm_by_id, misaligned_ids):
    """Global-MMLU rows against the MMMLU row at the same position (same sample_id). identical = same normalised
    text and key; fp_key_equal = same fingerprint and key (robust to small text edits)."""
    out = {"n": 0, "not_in_mmmlu": 0, "identical": 0, "fp_key_equal": 0, "on_misaligned": 0,
           "on_misaligned_identical": 0, "on_misaligned_fp_key_equal": 0}
    for r in gm_rows:
        out["n"] += 1
        m = mm_by_id.get(r["sample_id"])
        if m is None:
            out["not_in_mmmlu"] += 1
            continue
        same = r["digest"] == m["digest"] and r["key"] == m["key"]
        fk = r["fp"] == m["fp"] and r["key"] == m["key"]
        out["identical"] += int(same)
        out["fp_key_equal"] += int(fk)
        if r["sample_id"] in misaligned_ids:
            out["on_misaligned"] += 1
            out["on_misaligned_identical"] += int(same)
            out["on_misaligned_fp_key_equal"] += int(fk)
    return out
