"""Census of duplicate (question, passage) pairs with conflicting gold answers in BoolQ.

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried
out by AI agents working in MV2's name.

A BoolQ example is a (question, passage, yes/no answer) triple. If the SAME question and
passage appear more than once with DIFFERENT gold answers, the gold is self-contradicting
and any score computed against it is partly noise. A question that appears with two
different passages and two different answers is NOT a defect: the BoolQ answer is defined
relative to its passage, so the same question can legitimately be yes against one passage
and no against another. This module separates the two.

Apache-2.0.
"""
from collections import defaultdict


def normalize(s):
    """Collapse all whitespace runs to a single space, strip, and lowercase."""
    if s is None:
        return ""
    return " ".join(str(s).split()).lower()


def answer_of(row):
    """Return the gold answer of a BoolQ row as a bool.

    BoolQ's official files use a JSON boolean under "answer". Some redistributions use
    "label" (0/1, or the strings "True"/"False"/"true"/"false"/"yes"/"no"). Raise if
    neither key is present or the value cannot be interpreted, so a schema change is never
    silently read as a single class.
    """
    if "answer" in row and row["answer"] is not None:
        v = row["answer"]
    elif "label" in row and row["label"] is not None:
        v = row["label"]
    else:
        raise KeyError("row has neither 'answer' nor 'label': %r" % (sorted(row.keys()),))
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        if v in (0, 1):
            return bool(v)
        raise ValueError("unexpected integer answer %r" % (v,))
    if isinstance(v, str):
        t = v.strip().lower()
        if t in ("true", "1", "yes"):
            return True
        if t in ("false", "0", "no"):
            return False
    raise ValueError("uninterpretable answer %r" % (v,))


def census(rows):
    """Count duplicate (question, passage) pairs with conflicting gold answers.

    rows: iterable of dicts with 'question', 'passage' and a gold answer ('answer' or
    'label'). Returns a dict of integer counts plus a small list of real examples.
    """
    rows = list(rows)
    n = len(rows)

    exact_qp = defaultdict(list)    # (q, p)                 -> list of bool answers
    norm_qp = defaultdict(list)     # (norm q, norm p)       -> list of bool answers
    exact_q = defaultdict(set)      # q                      -> set of bool answers
    unique_q = set()
    unique_p = set()
    malformed = 0

    for r in rows:
        q = r.get("question")
        p = r.get("passage")
        if q is None or p is None:
            malformed += 1
            continue
        try:
            a = answer_of(r)
        except (KeyError, ValueError):
            malformed += 1
            continue
        unique_q.add(q)
        unique_p.add(p)
        exact_qp[(q, p)].append(a)
        norm_qp[(normalize(q), normalize(p))].append(a)
        exact_q[q].add(a)

    qp_dup_groups = 0
    qp_conflict_groups = 0
    qp_conflict_rows = 0
    exact_conflict_norm_keys = set()
    exact_qp_conflict_examples = []
    for (q, p), answers in exact_qp.items():
        if len(answers) >= 2:
            qp_dup_groups += 1
        if len(set(answers)) >= 2:
            qp_conflict_groups += 1
            qp_conflict_rows += len(answers)
            exact_conflict_norm_keys.add((normalize(q), normalize(p)))
            if len(exact_qp_conflict_examples) < 10:
                exact_qp_conflict_examples.append({
                    "question": q,
                    "passage_prefix": p[:200],
                    "answers": sorted(set(str(x) for x in answers)),
                    "n_rows": len(answers),
                })

    norm_qp_conflict_groups = 0
    norm_additional = 0
    for key, answers in norm_qp.items():
        if len(set(answers)) >= 2:
            norm_qp_conflict_groups += 1
            if key not in exact_conflict_norm_keys:
                norm_additional += 1

    question_conflict_groups = sum(1 for a in exact_q.values() if len(a) >= 2)

    return {
        "rows": n,
        "malformed": malformed,
        "unique_questions": len(unique_q),
        "unique_passages": len(unique_p),
        "qp_duplicate_groups": qp_dup_groups,
        "qp_conflict_groups": qp_conflict_groups,
        "qp_conflict_rows": qp_conflict_rows,
        "norm_qp_conflict_groups": norm_qp_conflict_groups,
        "norm_additional": norm_additional,
        "question_conflict_groups": question_conflict_groups,
        "exact_qp_conflict_examples": exact_qp_conflict_examples,
    }


def public_summary(result):
    """One-line human summary of a census result dict."""
    return (
        "%d rows, %d unique questions, %d unique passages; "
        "%d (q,p) duplicate groups, %d with conflicting gold answers (%d rows); "
        "%d normalized conflicts (%d additional); "
        "%d question-only conflicts (context)." % (
            result["rows"], result["unique_questions"], result["unique_passages"],
            result["qp_duplicate_groups"], result["qp_conflict_groups"],
            result["qp_conflict_rows"], result["norm_qp_conflict_groups"],
            result["norm_additional"], result["question_conflict_groups"],
        )
    )
