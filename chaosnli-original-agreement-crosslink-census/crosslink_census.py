"""Does the original 5-annotator agreement predict whether a crowd of 100 reaches consensus?

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

Audit 40 (chaosnli-strict-majority-census) measured, over the ChaosNLI re-annotations, how often the
original gold survives 100 fresh votes and how often 100 humans reach no strict majority. Audits 37/38
measured the original SNLI/MNLI 5-annotator agreement behind each gold. This audit JOINS the two: for
every ChaosNLI SNLI and MNLI-matched example we look up its ORIGINAL example (by uid == pairID), read the
original `gold_label` and `annotator_labels` (up to 5 votes), bucket it by how many of those original
annotators agreed with the original gold (5 = unanimous, 4, 3 = bare majority, or "-" = no original
majority), and cross-tabulate each bucket against the ChaosNLI 100-vote outcome:

  - does the original gold still match the 100-vote plurality?
  - do the 100 votes reach a strict majority (a label with > 50 of 100)?

The question is whether original annotator agreement is predictive: do examples that 5 annotators agreed
on unanimously stay decisive at 100 votes, while the 3-2 "bare majority" golds dissolve into crowd
ambiguity? ChaosNLI reports entropy and old-vs-plurality disagreement, but not (to our knowledge) a
census cross-tabulated against the ORIGINAL 5-annotator agreement level. That cross-tab is this audit's
novel lens.

This module operates on already-joined records, so it is file-free and fully unit-testable. Apache-2.0.
"""

NAMES_3WAY = ("e", "n", "c")

# Buckets by original agreement-with-gold; "dash" = original gold was "-" (no majority), "other" = a
# safety bucket (valid gold but fewer than 3 matching votes, which 5-label dev/test should never hit).
BUCKETS = ("5", "4", "3", "dash", "other")
_BUCKET_PREFIX = {"5": "b5", "4": "b4", "3": "b3", "dash": "bdash", "other": "bother"}
_PER_BUCKET_KEYS = ("n", "old_eq_plur", "old_diff_plur", "strict", "no_strict")

_TOTAL_KEYS = ("n_joined", "n_orig_gold_valid", "n_orig_gold_dash", "n_old_eq_origgold")


def norm_label(x):
    """Normalise an NLI label to e/n/c; blank / '-' / unrecognised -> None."""
    if x is None:
        return None
    s = str(x).strip().lower()
    if not s:
        return None
    if s[0] in ("e", "n", "c"):
        return s[0]
    return None


def plurality(counts, names):
    """Single label with the strict argmax of ``counts``; a tie for the max -> None."""
    if not counts:
        return None
    mx = max(counts)
    winners = [names[i] for i, c in enumerate(counts) if c == mx]
    return winners[0] if len(winners) == 1 else None


def strict_majority(counts, names):
    """Label held by strictly more than half the votes, else None ([50,50,0] -> None)."""
    total = sum(counts)
    if total <= 0:
        return None
    for i, c in enumerate(counts):
        if c * 2 > total:
            return names[i]
    return None


def agreement_count(annotator_labels, gold):
    """How many of the original annotator labels equal the (normalised) original gold."""
    g = norm_label(gold)
    if g is None:
        return None
    return sum(1 for a in (annotator_labels or []) if norm_label(a) == g)


def _bucket_of(orig_gold, annotator_labels):
    """Return the agreement bucket name for a joined example."""
    if norm_label(orig_gold) is None:
        return "dash"
    n_agree = agreement_count(annotator_labels, orig_gold)
    if n_agree == 5:
        return "5"
    if n_agree == 4:
        return "4"
    if n_agree == 3:
        return "3"
    return "other"


def _empty_bucket():
    return {k: 0 for k in _PER_BUCKET_KEYS}


def census(records, max_examples=5):
    """Cross-tabulate ChaosNLI 100-vote outcomes by original agreement bucket.

    Each record: ``uid``, ``subset``, ``orig_gold`` (raw original gold), ``annotator_labels`` (list of
    raw original votes), ``old`` (raw ChaosNLI old_label), ``counts`` (per-label 100-vote counts),
    ``names`` (label-name tuple aligned to counts).
    """
    totals = {k: 0 for k in _TOTAL_KEYS}
    buckets = {b: _empty_bucket() for b in BUCKETS}
    examples_orig_unanimous_no_strict = []  # 5/5 agreed originally, yet 100 reach no strict majority
    examples_bare_majority_flipped = []      # 3/5 originally, and 100-vote plurality flips the old gold

    for r in records:
        totals["n_joined"] += 1
        names = r.get("names", NAMES_3WAY)
        counts = r["counts"]
        og = norm_label(r.get("orig_gold"))
        old = norm_label(r.get("old"))
        plur = plurality(counts, names)
        strict = strict_majority(counts, names)

        if og is None:
            totals["n_orig_gold_dash"] += 1
        else:
            totals["n_orig_gold_valid"] += 1
            if old is not None and old == og:
                totals["n_old_eq_origgold"] += 1

        b = _bucket_of(r.get("orig_gold"), r.get("annotator_labels"))
        cell = buckets[b]
        cell["n"] += 1
        if old is not None and plur is not None:
            if old == plur:
                cell["old_eq_plur"] += 1
            else:
                cell["old_diff_plur"] += 1
        if strict is None:
            cell["no_strict"] += 1
        else:
            cell["strict"] += 1

        if b == "5" and strict is None and len(examples_orig_unanimous_no_strict) < max_examples:
            examples_orig_unanimous_no_strict.append(
                {"uid": r.get("uid"), "subset": r.get("subset"), "old": old,
                 "counts": counts, "names": list(names)})
        if b == "3" and old is not None and plur is not None and old != plur \
                and len(examples_bare_majority_flipped) < max_examples:
            examples_bare_majority_flipped.append(
                {"uid": r.get("uid"), "subset": r.get("subset"), "old": old, "plurality": plur,
                 "counts": counts, "names": list(names)})

    return {
        "totals": totals,
        "buckets": buckets,
        "examples_orig_unanimous_no_strict": examples_orig_unanimous_no_strict,
        "examples_bare_majority_flipped": examples_bare_majority_flipped,
    }


def flatten(stats):
    """Flatten the census into a single integer dict for comparison against a frozen TARGET."""
    out = {}
    for k in _TOTAL_KEYS:
        out[k] = stats["totals"][k]
    for b in BUCKETS:
        pre = _BUCKET_PREFIX[b]
        for k in _PER_BUCKET_KEYS:
            out["%s_%s" % (pre, k)] = stats["buckets"][b][k]
    return out


def no_strict_rate(stats, bucket):
    """Fraction of a bucket's records that reach no strict 100-vote majority (0.0 if empty)."""
    c = stats["buckets"][bucket]
    return (c["no_strict"] / c["n"]) if c["n"] else 0.0


def old_flip_rate(stats, bucket):
    """Fraction of a bucket's records whose old gold differs from the 100-vote plurality (0.0 if empty)."""
    c = stats["buckets"][bucket]
    denom = c["old_eq_plur"] + c["old_diff_plur"]
    return (c["old_diff_plur"] / denom) if denom else 0.0
