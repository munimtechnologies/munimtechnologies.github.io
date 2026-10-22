"""Cross-dataset overlap census between SNLI and MultiNLI.

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried
out by AI agents working in MV2's name.

SNLI and MultiNLI are the two canonical natural-language-inference corpora, and they are
routinely concatenated into a single training set (the "AllNLI" set used by, e.g.,
sentence-transformers). This census asks a structural-integrity question that mixing them
raises but that per-corpus de-duplication cannot answer: does any identical (premise,
hypothesis) pair appear in BOTH corpora, and if so, do SNLI and MultiNLI assign it the SAME
gold label or CONFLICTING ones?

- A shared pair with the SAME label is a benign cross-corpus duplicate (harmless redundancy,
  but a leakage risk if one corpus is used to train and the other to evaluate).
- A shared pair with CONFLICTING labels means the merged "AllNLI" gold is self-contradicting
  on that pair: no model can satisfy both annotations at once.

The identity of an example is its (premise, hypothesis) string pair; the gold compared is the
three-way NLI label (entailment / neutral / contradiction). Rows whose ``gold_label`` is
``"-"`` (no annotator majority) carry no usable gold and are excluded.

Apache-2.0.
"""

LABEL_BIT = {"entailment": 1, "neutral": 2, "contradiction": 4}


def normalize(s):
    """Collapse all whitespace runs to a single space, strip, and lowercase."""
    if s is None:
        return ""
    return " ".join(str(s).split()).lower()


def _bit(label):
    """Return the bit for a canonical NLI label, or 0 for '-'/unknown (excluded)."""
    return LABEL_BIT.get(label, 0)


def _labels(mask):
    """Return the sorted label names present in a gold bitmask."""
    return sorted(l for l, b in LABEL_BIT.items() if mask & b)


def build_index(rows):
    """Index an iterable of rows by (premise, hypothesis).

    rows: iterable whose items are indexable with [0]=premise, [1]=hypothesis, [2]=gold
    (any further fields, e.g. split, are ignored). Rows with gold '-' or an unknown label
    are counted as malformed and skipped. Returns (exact, norm, stats) where ``exact`` maps a
    raw (premise, hypothesis) pair to a gold bitmask (OR of every label seen for that pair)
    and ``norm`` maps the whitespace/case-normalized pair to its bitmask.
    """
    exact = {}
    norm = {}
    kept = 0
    malformed = 0
    for row in rows:
        p, h, g = row[0], row[1], row[2]
        b = _bit(g)
        if b == 0:
            malformed += 1
            continue
        kept += 1
        k = (p, h)
        exact[k] = exact.get(k, 0) | b
        nk = (normalize(p), normalize(h))
        norm[nk] = norm.get(nk, 0) | b
    stats = {
        "rows_kept": kept,
        "malformed": malformed,
        "unique_pairs": len(exact),
        "unique_norm_pairs": len(norm),
    }
    return exact, norm, stats


def cross_census(snli_rows, multinli_rows, max_examples=50):
    """Census identical (premise, hypothesis) pairs shared by SNLI and MultiNLI.

    Returns per-corpus stats plus exact and normalized cross-overlap counts, each split into
    same-label and conflicting-label pairs, and up to ``max_examples`` real shared pairs.
    A pair is "conflicting" when the union of the labels the two corpora give it has more
    than one distinct label.
    """
    s_exact, s_norm, s_stats = build_index(snli_rows)
    m_exact, m_norm, m_stats = build_index(multinli_rows)

    exact_keys = s_exact.keys() & m_exact.keys()
    exact_same = 0
    exact_conflict = 0
    exact_overlap_norm = set()
    examples = []
    for k in exact_keys:
        union = s_exact[k] | m_exact[k]
        conflict = bin(union).count("1") > 1
        if conflict:
            exact_conflict += 1
        else:
            exact_same += 1
        exact_overlap_norm.add((normalize(k[0]), normalize(k[1])))
        if len(examples) < max_examples:
            examples.append({
                "premise": k[0][:200],
                "hypothesis": k[1][:200],
                "snli_labels": _labels(s_exact[k]),
                "multinli_labels": _labels(m_exact[k]),
                "conflict": conflict,
            })

    norm_keys = s_norm.keys() & m_norm.keys()
    norm_same = 0
    norm_conflict = 0
    norm_additional = 0
    for k in norm_keys:
        union = s_norm[k] | m_norm[k]
        if bin(union).count("1") > 1:
            norm_conflict += 1
        else:
            norm_same += 1
        if k not in exact_overlap_norm:
            norm_additional += 1

    return {
        "snli": s_stats,
        "multinli": m_stats,
        "exact_overlap_pairs": len(exact_keys),
        "exact_overlap_same_label": exact_same,
        "exact_overlap_conflicting_label": exact_conflict,
        "norm_overlap_pairs": len(norm_keys),
        "norm_overlap_same_label": norm_same,
        "norm_overlap_conflicting_label": norm_conflict,
        "norm_additional_over_exact": norm_additional,
        "examples": examples,
    }


def public_summary(result):
    """One-line human summary of a cross-census result dict."""
    return (
        "SNLI %d pairs, MultiNLI %d pairs; %d identical (premise, hypothesis) pairs shared "
        "(%d same-label, %d conflicting-label); %d normalized overlaps (%d additional, "
        "%d conflicting)." % (
            result["snli"]["unique_pairs"], result["multinli"]["unique_pairs"],
            result["exact_overlap_pairs"], result["exact_overlap_same_label"],
            result["exact_overlap_conflicting_label"], result["norm_overlap_pairs"],
            result["norm_additional_over_exact"], result["norm_overlap_conflicting_label"],
        )
    )
