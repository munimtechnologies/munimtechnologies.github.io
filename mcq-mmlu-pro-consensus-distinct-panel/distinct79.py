"""Does audit 77's model-consensus flag change when the panel holds one archive per model? Core logic for audit 79.

Audit 77 flagged MMLU-Pro questions where at least 6 of the 10 most accurate published models pick the same non-key
option (and more of them than pick the key). Its 10 slots came from fewer distinct models: three Claude 3.5 Sonnet
archives, two GPT-4o versions and two runs labelled arx. This audit builds a second panel of the 10 most accurate
archives with at most one archive per model line, re-applies the same flag, and compares both panels against
MMLU-Redux 2.0's expert labels. It also measures how often two archives give the same wrong answer, within a model
line and across lines.

The join, panel and flag functions are copied unchanged from audits 77 and 78 (consensus77.py, added78.py).
Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

from fractions import Fraction

LETTERS = "ABCDEFGHIJ"
OK = "ok"
MISKEY = "wrong_groundtruth"
ERROR_TYPES = ("bad_question_clarity", "bad_options_clarity", "no_correct_answer", "multiple_correct_answers",
               MISKEY)
MIN_OVERLAP = 3
PRO_PREFIX = "ori_mmlu-"
FAMILIES = ("ori_mmlu", "stemez", "theoremQA", "scibench")


def pred_index(pred, k):
    """Index of a predicted letter A-J within k options, or None when missing / malformed / out of range."""
    if not isinstance(pred, str):
        return None
    p = pred.strip().upper()
    if len(p) != 1 or p not in LETTERS:
        return None
    i = LETTERS.index(p)
    return i if i < k else None


# ----- MMLU-Redux -> MMLU -> MMLU-Pro join (audit 75's rules, copied from audits 77/78) -----

def norm(s):
    return " ".join(("" if s is None else str(s)).split())


def label_of(error_type):
    return "" if error_type is None else str(error_type).strip().lower()


def mmlu_index(mmlu_rows):
    out = {}
    for r in mmlu_rows:
        ch = list(r["choices"] or [])
        a = r["answer"]
        if not isinstance(a, int) or a < 0 or a >= len(ch):
            continue
        out.setdefault((r["subject"], norm(r["question"]), tuple(norm(c) for c in ch)), []).append(a)
    return out


def join_mmlu(redux_row, index):
    ch = list(redux_row["choices"] or [])
    cands = index.get((redux_row["subject"], norm(redux_row["question"]), tuple(norm(c) for c in ch)))
    if not cands:
        return "no_match", None
    if len(set(cands)) > 1:
        return "ambiguous", None
    return "joined", cands[0]


def pro_subject(src):
    s = src or ""
    return s[len(PRO_PREFIX):] if s.startswith(PRO_PREFIX) else None


def pro_index(pro_rows):
    out = {}
    for r in pro_rows:
        if pro_subject(r["src"]) is None:
            continue
        out.setdefault(norm(r["question"]), []).append(r)
    return out


def overlap(choices, options):
    return len(set(norm(c) for c in choices) & set(norm(o) for o in options or []))


def join_pro_pool(subject, question, choices, index):
    cands = index.get(norm(question), [])
    if not cands:
        return "not_in_pro", [], ()
    good = [r for r in cands if overlap(choices, r["options"]) >= MIN_OVERLAP]
    if not good:
        return "not_in_pro", [], ("stem_only",)
    same = [r for r in good if pro_subject(r["src"]) == subject]
    pool = same if same else good
    if len(pool) > 1:
        return "ambiguous_pro", pool, ()
    flags = () if same else ("cross_subject",)
    return "in_pro", pool, flags


def redux_labels(redux_rows, mmlu_rows, pro_rows):
    mi = mmlu_index(mmlu_rows)
    pi = pro_index(pro_rows)
    counts = {"redux_mmlu": {"joined": 0, "no_match": 0, "ambiguous": 0},
              "pro_join": {"in_pro": 0, "ambiguous_pro": 0, "not_in_pro": 0, "stem_only": 0, "cross_subject": 0},
              "label_conflicts": 0}
    labels, ambiguous_ids, miskey_ids = {}, set(), set()
    for r in redux_rows:
        st, _key = join_mmlu(r, mi)
        counts["redux_mmlu"][st] += 1
        if st != "joined":
            continue
        pst, pool, pflags = join_pro_pool(r["subject"], r["question"], list(r["choices"]), pi)
        counts["pro_join"][pst] += 1
        for f in pflags:
            counts["pro_join"][f] += 1
        if pst == "ambiguous_pro":
            ambiguous_ids.update(int(p["question_id"]) for p in pool)
        elif pst == "in_pro":
            qid = int(pool[0]["question_id"])
            lab = r["label"]
            if lab == MISKEY:
                miskey_ids.add(qid)
            if qid in labels and labels[qid] != lab:
                counts["label_conflicts"] += 1
                labels[qid] = "conflict"
            else:
                labels[qid] = lab
    return labels, ambiguous_ids, miskey_ids, counts


# ----- The panel and the flag (copied from audits 77/78) -----

def accuracy(correct, n):
    return Fraction(correct, n) if n else Fraction(0)


def select_panel(acc, size):
    return sorted(acc, key=lambda m: (-accuracy(*acc[m]), m))[:size]


def votes(preds, k):
    counts, none = [0] * k, 0
    for p in preds:
        i = pred_index(p, k)
        if i is None:
            none += 1
        else:
            counts[i] += 1
    return counts, none


def consensus(counts, key_i):
    best, top, tied = None, 0, False
    for i, n in enumerate(counts):
        if i == key_i:
            continue
        if n > top:
            best, top, tied = i, n, False
        elif n == top and n > 0:
            tied = True
    if best is None or tied:
        return None, top
    return best, top


def flag_question(counts, key_i, min_agree):
    ci, n = consensus(counts, key_i)
    flagged = ci is not None and n >= min_agree and n > counts[key_i]
    return flagged, ci, n


def panel_flags(panel, preds_by_model, questions, min_agree):
    flags, tallies = {}, {}
    for q, (k, key_i) in questions.items():
        counts, none = votes([preds_by_model.get(m, {}).get(q) for m in panel], k)
        f, ci, _n = flag_question(counts, key_i, min_agree)
        flags[q] = (f, ci)
        tallies[q] = (counts, none)
    return flags, tallies


def groups(qids, family, labels, ambiguous_ids):
    g = {"miskey": [], "ok": [], "other_error": [], "unsure_or_conflict": [], "unreviewed_ori_mmlu": [],
         "ambiguous_ori_mmlu": [], "all": []}
    for f in FAMILIES:
        g[f] = []
    for q in sorted(qids):
        fam = family[q]
        g["all"].append(q)
        if fam in FAMILIES:
            g[fam].append(q)
        lab = labels.get(q)
        if lab == MISKEY:
            g["miskey"].append(q)
        elif lab == OK:
            g["ok"].append(q)
        elif lab in ERROR_TYPES:
            g["other_error"].append(q)
        elif lab is not None:
            g["unsure_or_conflict"].append(q)
        elif fam == "ori_mmlu":
            g["ambiguous_ori_mmlu" if q in ambiguous_ids else "unreviewed_ori_mmlu"].append(q)
    return g


def n_flagged(ids, flags):
    return sum(1 for q in ids if flags[q][0])


# ----- New in audit 79: one archive per model line, flag precision, shared wrong answers -----

def line_of(model, lines):
    """The model line of an archive: lines maps archive names to a shared line; any other archive is its own line."""
    return lines.get(model, model)


def select_distinct_panel(acc, size, lines):
    """The `size` most accurate archives (ties broken by name, as select_panel), keeping only the most accurate
    archive of each model line."""
    seen, out = set(), []
    for m in sorted(acc, key=lambda m: (-accuracy(*acc[m]), m)):
        ln = line_of(m, lines)
        if ln in seen:
            continue
        seen.add(ln)
        out.append(m)
        if len(out) == size:
            break
    return out


def flag_precision(flags, g):
    """(error-labelled, judged): among flagged questions MMLU-Redux judged (wrong key, OK or another error label),
    how many carry an error label. Unsure / conflicting labels are left out, as in audit 77's P4."""
    err = n_flagged(g["miskey"], flags) + n_flagged(g["other_error"], flags)
    return err, err + n_flagged(g["ok"], flags)


def wrong_agreement(pa, pb, questions):
    """(same, both_wrong): questions where both archives give a valid non-key answer, and how many of those are the
    same option."""
    same = both = 0
    for q, (k, key_i) in questions.items():
        ia, ib = pred_index(pa.get(q), k), pred_index(pb.get(q), k)
        if ia is None or ib is None or ia == key_i or ib == key_i:
            continue
        both += 1
        same += 1 if ia == ib else 0
    return same, both


def median(values):
    s = sorted(values)
    n = len(s)
    if n == 0:
        return None
    if n % 2:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def pair_rates(models, preds, questions, lines):
    """Shared-wrong-answer rates for every pair of the given archives, split into within-line and cross-line pairs.
    Keys are 'a|b' with a < b; values are (same, both_wrong, rate as a Fraction)."""
    within, cross = {}, {}
    ms = sorted(set(models))
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            a, b = ms[i], ms[j]
            same, both = wrong_agreement(preds[a], preds[b], questions)
            r = Fraction(same, both) if both else Fraction(0)
            (within if line_of(a, lines) == line_of(b, lines) else cross)["%s|%s" % (a, b)] = (same, both, r)
    return within, cross


def predictions79(g, flags_a, flags_d, within, cross, th):
    """Pre-registered P2-P6 with their counts (P1 is decided in job.py). flags_a: audit 77's panel; flags_d: the
    one-archive-per-line panel."""
    fm, nm = n_flagged(g["miskey"], flags_d), len(g["miskey"])
    fo, no = n_flagged(g["ok"], flags_d), len(g["ok"])
    ed, jd = flag_precision(flags_d, g)
    ea, ja = flag_precision(flags_a, g)
    fs, ns = n_flagged(g["stemez"], flags_d), len(g["stemez"])
    fx, nx = n_flagged(g["ori_mmlu"], flags_d), len(g["ori_mmlu"])
    med = median([v[2] for v in cross.values()])
    wmin = min(v[2] for v in within.values()) if within else None
    return {
        "P2_distinct_ratio": bool(nm and no and fm and fm * no >= th["P2_ratio"] * fo * nm),
        "P2_counts": [fm, nm, fo, no],
        "P3_distinct_precision_higher": bool(ja and jd and Fraction(ed, jd) > Fraction(ea, ja)),
        "P3_counts": [ed, jd, ea, ja],
        "P4_distinct_recall": fm >= th["P4_min_miskeys"],
        "P4_counts": [fm, nm],
        "P5_within_line_above_cross_median": bool(within and cross and wmin > med),
        "P5_counts": [str(wmin), str(med), len(within), len(cross)],
        "P6_stemez_below_mmlu": bool(ns and nx and Fraction(fs, ns) < Fraction(fx, nx)),
        "P6_counts": [fs, ns, fx, nx],
    }
