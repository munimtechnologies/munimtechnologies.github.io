"""Census of duplicate (goal, sol1, sol2) triples with conflicting gold labels in PIQA.

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried
out by AI agents working in MV2's name.

A PIQA example is a (goal, sol1, sol2) triple with a gold label in {0, 1} naming which
solution is correct. If the SAME triple appears more than once with DIFFERENT gold labels,
the gold is self-contradicting and any score computed against it is partly noise. A goal
that recurs with DIFFERENT solution pairs is NOT a defect: PIQA reuses goals across many
distinct solution pairs by design, so the same goal can legitimately take label 0 in one
example and label 1 in another. This module separates the two: triple conflicts are the
defect; goal reuse is reported as context.

Apache-2.0.
"""
from collections import defaultdict


def normalize(s):
    """Collapse all whitespace runs to a single space, strip, and lowercase."""
    if s is None:
        return ""
    return " ".join(str(s).split()).lower()


def label_of(row):
    """Return the gold label of a PIQA row as an int 0 or 1.

    PIQA ships labels in a separate .lst file, one line per example, each the character
    "0" or "1"; the loader attaches it to the row under "label". Accept an int/bool 0 or 1
    or the strings "0"/"1", and raise on anything else so a schema change is never silently
    read as a single class.
    """
    if "label" not in row or row["label"] is None:
        raise KeyError("row has no 'label': %r" % (sorted(row.keys()),))
    v = row["label"]
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        if v in (0, 1):
            return v
        raise ValueError("unexpected integer label %r" % (v,))
    if isinstance(v, str):
        t = v.strip()
        if t in ("0", "1"):
            return int(t)
    raise ValueError("uninterpretable label %r" % (v,))


def census(rows):
    """Count duplicate (goal, sol1, sol2) triples with conflicting gold labels.

    rows: iterable of dicts with 'goal', 'sol1', 'sol2' and a gold 'label' (0/1). Returns a
    dict of integer counts plus a small list of real examples.
    """
    rows = list(rows)
    n = len(rows)

    exact_triple = defaultdict(list)   # (g, s1, s2)               -> list of int labels
    norm_triple = defaultdict(list)    # (norm g, norm s1, norm s2) -> list of int labels
    goal_count = defaultdict(int)      # g                         -> number of examples
    unique_goals = set()
    malformed = 0

    for r in rows:
        g = r.get("goal")
        s1 = r.get("sol1")
        s2 = r.get("sol2")
        if g is None or s1 is None or s2 is None:
            malformed += 1
            continue
        try:
            a = label_of(r)
        except (KeyError, ValueError):
            malformed += 1
            continue
        unique_goals.add(g)
        goal_count[g] += 1
        exact_triple[(g, s1, s2)].append(a)
        norm_triple[(normalize(g), normalize(s1), normalize(s2))].append(a)

    triple_dup_groups = 0
    triple_conflict_groups = 0
    triple_conflict_rows = 0
    exact_conflict_norm_keys = set()
    exact_triple_conflict_examples = []
    for (g, s1, s2), labels in exact_triple.items():
        if len(labels) >= 2:
            triple_dup_groups += 1
        if len(set(labels)) >= 2:
            triple_conflict_groups += 1
            triple_conflict_rows += len(labels)
            exact_conflict_norm_keys.add((normalize(g), normalize(s1), normalize(s2)))
            if len(exact_triple_conflict_examples) < 10:
                exact_triple_conflict_examples.append({
                    "goal": g,
                    "sol1_prefix": s1[:160],
                    "sol2_prefix": s2[:160],
                    "labels": sorted(set(labels)),
                    "n_rows": len(labels),
                })

    norm_triple_conflict_groups = 0
    norm_additional = 0
    for key, labels in norm_triple.items():
        if len(set(labels)) >= 2:
            norm_triple_conflict_groups += 1
            if key not in exact_conflict_norm_keys:
                norm_additional += 1

    goal_duplicate_groups = sum(1 for c in goal_count.values() if c >= 2)

    return {
        "rows": n,
        "malformed": malformed,
        "unique_goals": len(unique_goals),
        "unique_triples": len(exact_triple),
        "triple_duplicate_groups": triple_dup_groups,
        "triple_conflict_groups": triple_conflict_groups,
        "triple_conflict_rows": triple_conflict_rows,
        "norm_triple_conflict_groups": norm_triple_conflict_groups,
        "norm_additional": norm_additional,
        "goal_duplicate_groups": goal_duplicate_groups,
        "exact_triple_conflict_examples": exact_triple_conflict_examples,
    }


def public_summary(result):
    """One-line human summary of a census result dict."""
    return (
        "%d rows, %d unique goals, %d unique triples; "
        "%d triple duplicate groups, %d with conflicting gold labels (%d rows); "
        "%d normalized conflicts (%d additional); "
        "%d goals reused across examples (context)." % (
            result["rows"], result["unique_goals"], result["unique_triples"],
            result["triple_duplicate_groups"], result["triple_conflict_groups"],
            result["triple_conflict_rows"], result["norm_triple_conflict_groups"],
            result["norm_additional"], result["goal_duplicate_groups"],
        )
    )
