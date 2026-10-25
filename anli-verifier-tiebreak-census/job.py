"""Run the ANLI verifier-tiebreak census on the official release.

Reads the main ANLI examples from anli_v1.0.zip into a uid -> {round, split, gold} index, parses the
separately released verifier_labels_R1-3.jsonl, joins them by uid, and tallies -- over the k=3 (tiebreak)
lines, overall and per round and per gold class -- whether the third verifier sides with the writer's
gold, the other first verifier, or a third label. The hand-traced fixture is asserted BEFORE any real
file is touched.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from tiebreak_census import LETTERS, ROUNDS, census_tiebreak, flatten, parse_verifier_row


SPLITS = cases.SPLITS


def read_verifier(path):
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if line:
                rows.append(parse_verifier_row(json.loads(line)))
    return rows


def _member_round_split(name):
    if not name.endswith(".jsonl") or name.endswith("/"):
        return None, None
    parts = name.split("/")
    rnd = next((p for p in parts if p in ROUNDS), None)
    stem = parts[-1][:-len(".jsonl")]
    split = stem if stem in SPLITS else None
    return rnd, split


def read_main(zip_path):
    index = {}
    totals = {}
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            rnd, split = _member_round_split(name)
            if rnd is None or split is None:
                continue
            n = 0
            with zf.open(name) as fh:
                for raw in fh:
                    line = raw.decode("utf-8").strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    index[obj.get("uid")] = {"round": rnd, "split": split, "gold": obj.get("label")}
                    n += 1
            totals["%s/%s" % (rnd, split)] = n
    return index, totals


def _rates(tally):
    n = tally["n"]
    nt = tally["n_tiebreak"]
    mf = tally["majority_formed"]
    out = dict(tally)
    out["firsttwo_differ_rate"] = (tally["firsttwo_differ"] / n) if n else None
    out["no_majority_rate"] = (tally["no_majority"] / n) if n else None
    out["match_rate_given_majority"] = (tally["match"] / mf) if mf else None
    out["tiebreak_gold_rate"] = (tally["tiebreak_gold"] / nt) if nt else None
    out["tiebreak_other_rate"] = (tally["tiebreak_other"] / nt) if nt else None
    out["tiebreak_third_rate"] = (tally["tiebreak_third"] / nt) if nt else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix_stats = census_tiebreak([parse_verifier_row(o) for o in cases.FIXTURE_VERIFIER_RAW],
                                cases.build_gold_index(cases.FIXTURE_MAIN_RAW))
    fix = flatten(fix_stats)
    target_met = (set(fix) == set(cases.TARGET)) and all(fix[k] == cases.TARGET[k] for k in cases.TARGET)
    print("[fixture] target_met =", target_met)
    if not target_met:
        for k in sorted(set(fix) | set(cases.TARGET)):
            o, t = fix.get(k), cases.TARGET.get(k)
            if o != t:
                print("  MISMATCH %-28s observed=%r target=%r" % (k, o, t))
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Locate the two inputs in the (reused) data volume.
    verifier_files = sorted(glob.glob(os.path.join(args.data_dir, "*verifier*.jsonl")))
    zips = sorted(glob.glob(os.path.join(args.data_dir, "*.zip")))
    print("[diag] verifier files:", verifier_files)
    print("[diag] zip files:", zips)
    if not verifier_files:
        print("FATAL: no verifier jsonl found in data dir", file=sys.stderr)
        sys.exit(3)
    if not zips:
        print("FATAL: no anli zip found in data dir", file=sys.stderr)
        sys.exit(4)

    # 3. Read both sides and run the tiebreak census.
    verifier_rows = read_verifier(verifier_files[0])
    gold_index, main_totals = read_main(zips[0])
    print("[diag] verifier lines =", len(verifier_rows), " main examples =", len(gold_index))
    stats = census_tiebreak(verifier_rows, gold_index)
    t = stats["totals"]
    print("[diag] totals =", t)

    overall = _rates(stats["overall"])
    by_round = {r: _rates(stats["by_round"][r]) for r in ROUNDS}
    by_class = {g: _rates(stats["by_class"][g]) for g in LETTERS}

    # 4. Pre-registered predictions (held/failed reported honestly).
    o = stats["overall"]
    # P1 (structural, finding either way): among k=3 lines the first two verifiers differ on >99%
    # (ANLI adds a third verifier only on disagreement; shortfalls are protocol anomalies like audit 46's
    # 22 k2_split pairs).
    ft_rate = (o["firsttwo_differ"] / o["n"]) if o["n"] else None
    p1 = ft_rate is not None and ft_rate > cases.MIN_FIRSTTWO_DIFFER_RATE
    # P2 (directional, finding either way): among genuine tiebreaks (first two differ, gold is one of them)
    # the third verifier sides with the writer's gold on >50% -- the tiebreaker recovers the gold.
    tg_rate = (o["tiebreak_gold"] / o["n_tiebreak"]) if o["n_tiebreak"] else None
    p2 = tg_rate is not None and tg_rate > cases.MIN_TIEBREAK_GOLD_RATE
    # P3 (structural cross-check): gold == strict verifier majority on >99% of ALL joined lines
    # (reproduces audit 39's 29,765 / 29,803 = 0.9987).
    al_rate = (t["all_lines_match"] / t["n_joined"]) if t["n_joined"] else None
    p3 = al_rate is not None and al_rate > cases.MIN_ALL_LINES_MATCH_RATE

    predictions = {
        "P1_firsttwo_differ_above_min": p1,
        "P2_tiebreak_recovers_gold_above_half": p2,
        "P3_all_lines_match_above_min": p3,
    }
    print("[diag] k3 firsttwo_differ_rate =", None if ft_rate is None else round(ft_rate, 4),
          " firsttwo_agree =", o["firsttwo_agree"])
    print("[diag] n_tiebreak =", o["n_tiebreak"],
          " tiebreak_gold/other/third =", o["tiebreak_gold"], o["tiebreak_other"], o["tiebreak_third"],
          " gold_rate =", None if tg_rate is None else round(tg_rate, 4))
    print("[diag] k3 no_majority =", o["no_majority"], " match/differ =", o["match"], o["differ"])
    print("[diag] all_lines match/differ/no_majority =",
          t["all_lines_match"], t["all_lines_differ"], t["all_lines_no_majority"],
          " match_rate =", None if al_rate is None else round(al_rate, 4))
    for r in ROUNDS:
        tr = by_round[r]
        print("[diag] round %s: n_k3=%d tiebreak_gold_rate=%s no_majority=%d" %
              (r, tr["n"], None if tr["tiebreak_gold_rate"] is None else round(tr["tiebreak_gold_rate"], 4),
               tr["no_majority"]))
    for g in LETTERS:
        cg = by_class[g]
        print("[diag] class %s: n_k3=%d tiebreak_gold_rate=%s no_majority=%d" %
              (g, cg["n"], None if cg["tiebreak_gold_rate"] is None else round(cg["tiebreak_gold_rate"], 4),
               cg["no_majority"]))
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    out = {
        "dataset": "ANLI v1.0 (Nie, Williams, Dinan, Bansal, Weston and Kiela, 2020), R1/R2/R3, joined to "
                   "the separately released verifier_labels_R1-3.jsonl by uid. ANLI adds a third verifier "
                   "only when the first two disagree, so every k=3 verifier line is a tiebreak. This audit "
                   "isolates the k=3 lines and tallies -- overall, per round and per gold class -- whether "
                   "the third verifier sides with the writer's adversarial gold, the other first verifier, "
                   "or a third label, and how decisively the gold survives the tiebreak. The all-lines "
                   "match/differ/no-majority totals reproduce audit 39 as a cross-check. Reuses audits "
                   "39/45/46/47 label/majority primitives verbatim.",
        "rows_as_expected": (t["n_orphan"] == 0 and t["n_gold_unexpected"] == 0),
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "main_totals_by_round_split": main_totals,
        "totals": t,
        "overall": overall,
        "by_round": by_round,
        "by_class": by_class,
        "examples_tiebreak_differ": stats["examples_tiebreak_differ"],
        "predictions": predictions,
        "note": "k=3 lines are ANLI's tiebreak subset: the protocol adds a third verifier only when the "
                "first two disagree. 'n_tiebreak' counts k=3 lines where the first two genuinely differ AND "
                "the writer's gold is one of the two disputed labels, so the third verifier's vote decides "
                "whether the gold becomes the strict majority; tiebreak_gold/other/third partition those by "
                "whether the third verifier picked the gold, the other first label, or a distinct third "
                "label (no majority). 'firsttwo_agree' on a k=3 line is a protocol anomaly (a third verifier "
                "was added although the first two already agreed). P1 (structural) bets the first two "
                "verifiers differ on >99% of k=3 lines (a finding either way). P2 (directional) bets the "
                "third verifier sides with the writer's gold on >50% of genuine tiebreaks. P3 (cross-check) "
                "bets gold == strict verifier majority on >99% of all joined lines (reproduces audit 39). "
                "This audit measures AGREEMENT, not label correctness.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
