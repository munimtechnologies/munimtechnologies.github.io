"""Global-MMLU ALIGNMENT MAP (audit 74).

Audits 72 and 73 matched translated rows to English rows by a digit fingerprint (align.py) and found 180 Chinese and
113 Korean rows of high_school_world_history holding another English question. They also flagged eight other cells
(Japanese moral_scenarios, professional_law in seven languages) whose "misaligned" rows all carry their own
position's key. Those looked like matcher artifacts: when hundreds of rows share one fingerprint (every MMLU
moral-scenarios question contains "as of 2020"), order-preserving matching shifts by one place wherever a
translation adds or drops a number.

This module adds three things:
- capped_align: align.py's matcher, except that a fingerprint group with more than `cap` rows on either side stays
  unmatched (counted as over_cap). Passages in world history give small groups; templates give huge ones.
- infer / leave_one_out: fill a row the fingerprint left unmatched from its neighbours. When the nearest matched rows
  before and after it hold questions shifted by the same offset d, the row is taken to hold position j+d (if that
  position exists and no other row holds it). Leave-one-out on matched rows measures how often this rule is right.
- build_map / summarize: a per-position map (ids, offsets, keys, labels; no question text).

Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import align as al


def capped_align(en_rows, xx_rows, cap):
    """As al.align, but groups with more than `cap` rows on either side stay unmatched. Returns (mapping, stats);
    mapped + no_fingerprint + count_differs + over_cap == n."""
    def groups(rows):
        g = {}
        for r in sorted(rows, key=al._order):
            if r["fp"]:
                g.setdefault(r["fp"], []).append(r["sample_id"])
        return g

    ge, gx = groups(en_rows), groups(xx_rows)
    st = {"n": len(xx_rows), "no_fingerprint": sum(1 for r in xx_rows if not r["fp"]), "count_differs": 0,
          "over_cap": 0, "mapped": 0, "aligned": 0, "misaligned": 0}
    mapping = {}
    for fp in sorted(gx):
        xs, es = gx[fp], ge.get(fp, [])
        if len(xs) != len(es):
            st["count_differs"] += len(xs)
            continue
        if len(xs) > cap:
            st["over_cap"] += len(xs)
            continue
        for x, e in zip(xs, es):
            mapping[x] = e
            st["mapped"] += 1
            st["aligned" if x == e else "misaligned"] += 1
    return mapping, st


def key_report(en_by_id, xx_rows, mapping):
    """Misaligned rows under `mapping`, and how many carry the key of the paired English question (content) or of
    the English question with their own sample_id (id)."""
    out = {"misaligned": 0, "mis_key_equals_content": 0, "mis_key_equals_id": 0}
    for x in xx_rows:
        s = x["sample_id"]
        m = mapping.get(s)
        if m is None or m == s:
            continue
        out["misaligned"] += 1
        out["mis_key_equals_content"] += int(x["key"] == en_by_id[m]["key"])
        out["mis_key_equals_id"] += int(x["key"] == en_by_id[s]["key"])
    return out


def offsets_from(mapping):
    """{translated sample_id: English sample_id} -> {position: held position - position}."""
    out = {}
    for s, m in mapping.items():
        j, c = al.index_of(s), al.index_of(m)
        if j is not None and c is not None:
            out[j] = c - j
    return out


def infer(n, offsets, targets):
    """offsets: {position: offset} of matched positions. For each target position j (ascending), when the nearest
    matched positions before and after j both have offset d, and 0 <= j+d < n, and j+d is held by no matched
    position and by no earlier inference, infer that j holds j+d. Returns {position: held position}."""
    known = sorted(offsets)
    used = set(j + d for j, d in offsets.items())
    out = {}
    taken = set()
    for j in sorted(targets):
        before = [p for p in known if p < j]
        after = [p for p in known if p > j]
        if not before or not after:
            continue
        d1, d2 = offsets[before[-1]], offsets[after[0]]
        if d1 != d2:
            continue
        c = j + d1
        if 0 <= c < n and c not in used and c not in taken:
            out[j] = c
            taken.add(c)
    return out


def leave_one_out(n, offsets):
    """Hide each matched position in turn and infer it from the others: how often is an inference made, and how
    often does it equal the fingerprint match?"""
    made = agree = 0
    for j in sorted(offsets):
        rest = {p: d for p, d in offsets.items() if p != j}
        got = infer(n, rest, [j])
        if j in got:
            made += 1
            agree += int(got[j] == j + offsets[j])
    return {"tested": len(offsets), "made": made, "agree": agree}


def build_map(en_rows, xx_rows, mapping, inferred):
    """One subject: one record per translated row, in position order. `inferred`: {position: held position}."""
    en = {al.index_of(r["sample_id"]): r for r in en_rows}
    rows = []
    for x in sorted(xx_rows, key=al._order):
        j = al.index_of(x["sample_id"])
        m = mapping.get(x["sample_id"])
        if m is not None:
            c, how = al.index_of(m), "fingerprint"
        elif j in inferred:
            c, how = inferred[j], "neighbours"
        else:
            c, how = None, "unresolved"
        rows.append({
            "sample_id": x["sample_id"], "position": j, "holds_position": c, "how": how,
            "key_fits_held": None if c is None else x["key"] == en[c]["key"],
            "key_fits_own_position": x["key"] == en[j]["key"],
            "label_on_row": x["label"], "label_of_held": None if c is None else en[c]["label"],
        })
    return rows


def summarize(records):
    out = {"n": 0, "fingerprint": 0, "neighbours": 0, "unresolved": 0, "holds_other": 0,
           "holds_other_fingerprint": 0, "holds_other_neighbours": 0, "holds_other_key_fits_held": 0,
           "neighbours_other_key_fits_held": 0, "neighbours_other_key_fits_own": 0, "label_wrong": 0}
    for r in records:
        out["n"] += 1
        out[r["how"]] += 1
        c = r["holds_position"]
        if c is None or c == r["position"]:
            continue
        out["holds_other"] += 1
        out["holds_other_" + r["how"]] += 1
        out["holds_other_key_fits_held"] += int(bool(r["key_fits_held"]))
        if r["how"] == "neighbours":
            out["neighbours_other_key_fits_held"] += int(bool(r["key_fits_held"]))
            out["neighbours_other_key_fits_own"] += int(bool(r["key_fits_own_position"]))
        out["label_wrong"] += int(r["label_on_row"] != r["label_of_held"])
    return out
