"""Source keys, structural gate and pre-registered predictions for the MMLU-Pro source length census (audit 63).

Audit 62 found that MMLU-Pro's doubled pick-longest shortcut sits in its NEW questions (src stemez- / theoremQA- /
scibench-), not in the questions inherited from MMLU, and inferred by subtraction that the new-source biology and
psychology questions must score about 56% and 61%. This module keys the length census by source family, by
(category, provenance) and by (category, family) so those figures are measured directly.

Standard library only. Apache-2.0.
"""

MIN_FAMILY_N = 100   # a source family must have at least this many valid questions to enter P3/P4/P6
MIN_CELL_N = 50      # a category needs at least this many valid questions of BOTH provenances to enter P5


def family(src):
    """Source family: the src prefix before the first '-' (e.g. 'stemez-Biology' -> 'stemez')."""
    s = src or ""
    return s.split("-", 1)[0] if s else "unknown"


def provenance(src):
    return "ori_mmlu" if (src or "").startswith("ori_mmlu") else "new"


def census_rows(pro_rows, key_fn):
    """(key, labels, texts, answer_key) rows for gold_length.run_census, labelled by option position."""
    out = []
    for r in pro_rows:
        opts = list(r["options"] or [])
        out.append((key_fn(r), [str(j) for j in range(len(opts))], opts, str(r["answer_index"])))
    return out


def digest(census):
    """Exact summary of raw census accumulators: key -> (n_valid, n_degenerate, chance_sum, char longest_credit)."""
    return {k: (b["n_valid"], b["n_degenerate"], b["chance_sum"], b["char"]["longest_credit"])
            for k, b in census.items()}


def _close(a, b):
    return a is not None and abs(a - b) < 1e-12


def structural_gate(pooled, by_prov, by_cat, expected):
    """Pooled must reproduce audit 61, provenance audit 62, biology/psychology audit 61. Returns (ok, detail)."""
    detail = {
        "n_valid": {"got": pooled["n_valid"], "expected": expected["n_valid"],
                    "match": pooled["n_valid"] == expected["n_valid"]},
        "pooled_unique_longest": {"got": pooled["char"]["unique_longest_count"],
                                  "expected": expected["unique_longest"],
                                  "match": pooled["char"]["unique_longest_count"] == expected["unique_longest"]},
        "pooled_longest_accuracy": {"got": pooled["char"]["longest_accuracy"],
                                    "expected": expected["longest_accuracy"],
                                    "match": _close(pooled["char"]["longest_accuracy"],
                                                    expected["longest_accuracy"])},
        "clean_parse": {"got": [pooled["n_bad_key"], pooled["n_degenerate"]], "expected": [0, 0],
                        "match": pooled["n_bad_key"] == 0 and pooled["n_degenerate"] == 0},
    }
    for group, got_rep, exp in (("provenance", by_prov, expected["provenance"]),
                                ("category", by_cat, expected["category"])):
        for k, (n, acc) in sorted(exp.items()):
            e = got_rep.get(k)
            got = None if e is None else [e["n_valid"], e["char"]["longest_accuracy"]]
            detail["%s:%s" % (group, k)] = {
                "got": got, "expected": [n, acc],
                "match": e is not None and e["n_valid"] == n and _close(e["char"]["longest_accuracy"], acc)}
    return all(d["match"] for d in detail.values()), detail


def lift(e):
    return e["char"]["longest_accuracy"] - e["chance_accuracy"]


def predictions(by_family, by_cat_prov):
    """Pre-registered predictions, each a finding either way. Decided before any real number was seen."""
    bio = by_cat_prov.get("biology|new")
    psy = by_cat_prov.get("psychology|new")

    # P1: new-source biology questions score at least 50% for pick-longest (audit 62 implied ~56%).
    p1 = bool(bio and bio["n_valid"] and bio["char"]["longest_accuracy"] >= 0.50)
    # P2: new-source psychology questions score at least 50% for pick-longest (audit 62 implied ~61%).
    p2 = bool(psy and psy["n_valid"] and psy["char"]["longest_accuracy"] >= 0.50)

    lift_ori = lift(by_family["ori_mmlu"])
    new_fams = {k: v for k, v in by_family.items() if k != "ori_mmlu" and v["n_valid"] >= MIN_FAMILY_N}
    fam_lifts = {k: lift(v) for k, v in sorted(new_fams.items())}
    # P3: every new-source family (n >= 100) has a larger pick-longest lift than the MMLU-derived questions.
    p3 = bool(fam_lifts) and all(v > lift_ori for v in fam_lifts.values())
    # P4: the STEM-website family (stemez) carries the largest lift of the new-source families.
    top = max(fam_lifts, key=lambda k: fam_lifts[k]) if fam_lifts else None
    p4 = top == "stemez"
    # P6: in every new-source family (n >= 100) the gold is the unique shortest option in under 5% of questions.
    fam_short = {k: v["char"]["unique_shortest_rate"] for k, v in sorted(new_fams.items())}
    p6 = bool(fam_short) and all(v < 0.05 for v in fam_short.values())

    # P5: among categories with >= 50 valid questions of both provenances, the new-source lift exceeds the
    # MMLU-derived lift in a strict majority.
    cats = sorted({k.split("|", 1)[0] for k in by_cat_prov})
    eligible = []
    wins = []
    for c in cats:
        o = by_cat_prov.get(c + "|ori_mmlu")
        n = by_cat_prov.get(c + "|new")
        if not o or not n or o["n_valid"] < MIN_CELL_N or n["n_valid"] < MIN_CELL_N:
            continue
        eligible.append(c)
        if lift(n) > lift(o):
            wins.append(c)
    p5 = bool(eligible) and 2 * len(wins) > len(eligible)

    return {
        "P1_new_source_biology_pick_longest_at_least_50pct": p1,
        "P1_detail": {"n": bio and bio["n_valid"], "pick_longest": bio and bio["char"]["longest_accuracy"],
                      "chance": bio and bio["chance_accuracy"]},
        "P2_new_source_psychology_pick_longest_at_least_50pct": p2,
        "P2_detail": {"n": psy and psy["n_valid"], "pick_longest": psy and psy["char"]["longest_accuracy"],
                      "chance": psy and psy["chance_accuracy"]},
        "P3_every_new_family_lift_exceeds_ori_mmlu": p3,
        "P3_detail": {"lift_ori_mmlu": lift_ori, "family_lifts": fam_lifts},
        "P4_stemez_has_largest_new_family_lift": p4,
        "P4_detail": {"top_family": top},
        "P5_new_lift_exceeds_ori_in_majority_of_categories": p5,
        "P5_detail": {"eligible": eligible, "new_wins": wins},
        "P6_new_family_gold_unique_shortest_under_5pct": p6,
        "P6_detail": {"unique_shortest_rate": fam_short},
    }
