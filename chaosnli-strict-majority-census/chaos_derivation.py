"""Does an NLI benchmark's original gold label survive 100 fresh annotations, and do 100 humans even
reach a strict majority?

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

The gold-label-derivation family (audits 37 SNLI, 38 MultiNLI, 39 ANLI) checks how a benchmark's single
gold label relates to the per-annotator votes behind it. Audits 37/38 were tautological (gold IS the
majority of its own 5 votes); audit 39 (ANLI) was the first non-tautological one (gold is the writer's
label, compared to separate verifiers). This audit goes further: ChaosNLI (Nie, Zhou and Bansal, EMNLP
2020) re-collected *100* fresh crowd annotations for a sample of SNLI, MNLI-matched and alphaNLI dev
examples. So we can ask two questions the original 5-annotator pipeline cannot:

  1. Does the original benchmark gold (`old_label`, the 5-annotator majority) match the 100-annotator
     plurality (`majority_label`)? ChaosNLI reports these disagree on 378 SNLI and 508 MNLI records; we
     reproduce that from the raw files as a verification.
  2. How often do even 100 fresh annotators fail to reach a STRICT majority (no label with > 50 of the
     100 votes)? Those are examples that are genuinely ambiguous to a large crowd, yet the benchmark
     still assigns a single hard gold label. ChaosNLI's `majority_label` is a plurality (argmax), not a
     strict-majority threshold, so this strict-majority census is the audit's novel lens.

The module is label-space-neutral: it works on a per-label integer count vector and its label names, so
the same code covers 3-way NLI (e/n/c) and alphaNLI's 2-choice (1/2).

Apache-2.0.
"""


def norm_label(x):
    """Normalise a label to a canonical token.

    3-way NLI labels collapse to a single letter e/n/c (handles 'e'/'entailment'/'E' etc.); alphaNLI's
    choice labels '1'/'2' (or ints) pass through as '1'/'2'. Anything empty or unrecognised -> None.
    """
    if x is None:
        return None
    s = str(x).strip().lower()
    if not s:
        return None
    if s[0] in ("e", "n", "c"):
        return s[0]
    if s in ("1", "2"):
        return s
    return None


def plurality(counts, names):
    """Return the single label name with the strict argmax of ``counts``; a tie for the max -> None."""
    if not counts:
        return None
    mx = max(counts)
    winners = [names[i] for i, c in enumerate(counts) if c == mx]
    return winners[0] if len(winners) == 1 else None


def strict_majority(counts, names):
    """Return the label name held by strictly more than half the total votes, else None.

    e.g. counts=[60,30,10] -> that label (60*2 > 100); counts=[50,50,0] or [40,35,25] -> None.
    """
    total = sum(counts)
    if total <= 0:
        return None
    for i, c in enumerate(counts):
        if c * 2 > total:
            return names[i]
    return None


_FLAT_KEYS = (
    "n_records", "n_sum100", "n_old_eq_majority", "n_old_differs_majority", "n_majority_eq_plurality",
    "n_strict_exists", "n_no_strict_majority", "n_old_eq_strict", "n_old_differs_strict",
    "n_old_on_no_strict",
)


def census(records, max_examples=5):
    """Count the derivation / stability outcome over an iterable of parsed ChaosNLI records.

    Each record is a dict: ``uid``, ``old`` (normalised old gold), ``majority`` (normalised ChaosNLI
    majority_label), ``counts`` (per-label integer votes, summing to 100), ``names`` (label-name tuple
    aligned with ``counts``).
    """
    s = {k: 0 for k in _FLAT_KEYS}
    entropy_sum = 0.0
    entropy_n = 0
    entropy_max = 0.0
    examples_old_differs_majority = []
    examples_no_strict_with_old = []
    for r in records:
        s["n_records"] += 1
        counts = r["counts"]
        names = r["names"]
        if sum(counts) == 100:
            s["n_sum100"] += 1
        old = r["old"]
        maj = r["majority"]
        plur = plurality(counts, names)
        strict = strict_majority(counts, names)

        if old is not None and maj is not None:
            if old == maj:
                s["n_old_eq_majority"] += 1
            else:
                s["n_old_differs_majority"] += 1
                if len(examples_old_differs_majority) < max_examples:
                    examples_old_differs_majority.append(
                        {"uid": r.get("uid"), "old": old, "majority": maj, "counts": counts,
                         "names": list(names)})
        if plur is not None and maj is not None and plur == maj:
            s["n_majority_eq_plurality"] += 1

        if strict is None:
            s["n_no_strict_majority"] += 1
            if old is not None:
                s["n_old_on_no_strict"] += 1
                if len(examples_no_strict_with_old) < max_examples:
                    examples_no_strict_with_old.append(
                        {"uid": r.get("uid"), "old": old, "counts": counts, "names": list(names)})
        else:
            s["n_strict_exists"] += 1
            if old is not None:
                if old == strict:
                    s["n_old_eq_strict"] += 1
                else:
                    s["n_old_differs_strict"] += 1

        ent = r.get("entropy")
        if isinstance(ent, (int, float)):
            entropy_sum += ent
            entropy_n += 1
            entropy_max = max(entropy_max, ent)

    out = dict(s)
    out["entropy_mean"] = (entropy_sum / entropy_n) if entropy_n else None
    out["entropy_max"] = entropy_max if entropy_n else None
    out["examples_old_differs_majority"] = examples_old_differs_majority
    out["examples_no_strict_with_old"] = examples_no_strict_with_old
    return out


def flatten(stats):
    """Integer census keys only (drops entropy and examples) for comparison against a frozen TARGET."""
    return {k: stats[k] for k in _FLAT_KEYS}
