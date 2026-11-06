"""How strong must a model panel be to find MMLU-Pro's wrong keys, and do questions no model answers with the key
hold errors? Core logic for audit 84.

Audit 83 cut HELM's 78 MMLU models into seven disjoint panels of 10 by accuracy and found that weaker panels find
mostly the same wrong keys at lower precision. This audit repeats the design on a second harness and a 10-option
benchmark: TIGER-AI-Lab's 45 published MMLU-Pro archives, cut into four disjoint panels of 10 (ranks 1-10 is audit
77's panel), scored against MMLU-Redux 2.0's expert labels (audit 75's join). It also tests, before looking, audit
82's post-hoc lead: questions that no archive answers with the key.

The join, panel and flag functions are copied unchanged from audit 79 (distinct79.py, which copied them from audits
77 and 78); the margin, AUC, strata, budget counts and per-panel statistics are copied unchanged from audit 83
(panel83.py). New here: key counts across all archives, the no-key flag, the key-share score and the verdicts.
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


# ----- MMLU-Redux -> MMLU -> MMLU-Pro join (audit 75's rules, copied from audit 79) -----

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


# ----- The panel and the flag (copied from audit 79) -----

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


def flag_precision(flags, g):
    """(error-labelled, judged): among flagged questions MMLU-Redux judged (wrong key, OK or another error label),
    how many carry an error label. Unsure / conflicting labels are left out, as in audits 77-83."""
    err = n_flagged(g["miskey"], flags) + n_flagged(g["other_error"], flags)
    return err, err + n_flagged(g["ok"], flags)


# ----- Margin and AUC (copied from audit 83) -----

def margin(counts, key_i):
    """Consensus margin of a panel's votes: the most-picked non-key option's votes minus the key's votes."""
    other = max([n for i, n in enumerate(counts) if i != key_i] or [0])
    return other - counts[key_i]


def auc(pos, neg):
    """Probability that a positive scores above a negative, ties counting one half (Mann-Whitney), as a Fraction;
    None if either list is empty. Doubled average ranks keep the arithmetic exact."""
    if not pos or not neg:
        return None
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg], key=lambda t: t[0])
    n = len(allv)
    rank2_pos, i = 0, 0
    while i < n:
        j = i
        while j + 1 < n and allv[j + 1][0] == allv[i][0]:
            j += 1
        r2 = (i + 1) + (j + 1)
        rank2_pos += r2 * sum(1 for t in allv[i:j + 1] if t[1] == 1)
        i = j + 1
    n_pos, n_neg = len(pos), len(neg)
    return Fraction(rank2_pos - n_pos * (n_pos + 1), 2 * n_pos * n_neg)


# ----- Strata, budget counts, per-panel statistics (copied from audit 83) -----

def strata(acc, size, n):
    """The included models ranked by accuracy (ties by name, as select_panel), cut into n disjoint panels of `size`:
    ranks 1..size, size+1..2*size, ... None if there are fewer than size * n models."""
    ranked = select_panel(acc, len(acc))
    if len(ranked) < size * n:
        return None
    return [ranked[i * size:(i + 1) * size] for i in range(n)]


def margins(tallies, questions):
    """{q: the panel's consensus margin on q}."""
    return {q: margin(tallies[q][0], questions[q][1]) for q in questions}


def budget_counts(score, sets, budget):
    """Expected counts when the `budget` highest-scoring questions are sent to review and ties at the cut are broken
    uniformly at random: whole score levels are taken from the top; the level that straddles the cut contributes the
    fraction (budget - taken) / level size of its members. Returns one Fraction per set in `sets` (each a set of
    question ids): the expected number of reviewed questions from that set."""
    levels = {}
    for q, v in score.items():
        levels.setdefault(v, []).append(q)
    out = [Fraction(0)] * len(sets)
    taken = 0
    for v in sorted(levels, reverse=True):
        if taken >= budget:
            break
        qs = levels[v]
        f = Fraction(1) if taken + len(qs) <= budget else Fraction(budget - taken, len(qs))
        for i, s in enumerate(sets):
            out[i] += f * sum(1 for q in qs if q in s)
        taken = min(budget, taken + len(qs))
    return out


def stratum_stats(flags, score, g, budget):
    """One panel's numbers: frozen-rule flag count, precision (error-labelled, judged) and miskeys among its flags;
    AUC of its margin for Redux miskeys vs Redux-OK; expected error-labelled, judged and miskey counts among the
    `budget` questions with the highest margin (ties shared)."""
    err = set(g["miskey"]) | set(g["other_error"])
    judged = err | set(g["ok"])
    b_err, b_judged, b_mis = budget_counts(score, [err, judged, set(g["miskey"])], budget)
    return {"flags": n_flagged(g["all"], flags), "prec": flag_precision(flags, g),
            "miskeys": n_flagged(g["miskey"], flags),
            "auc": auc([score[q] for q in g["miskey"]], [score[q] for q in g["ok"]]),
            "b_err": b_err, "b_judged": b_judged, "b_miskey": b_mis}


def stats_json(st):
    """A JSON-safe copy of stratum_stats output (Fractions -> floats; the exact budget counts as 'p/q' strings)."""
    def fr(x):
        return None if x is None else float(x)
    e, j = st["prec"]
    return {"flags": st["flags"], "precision": [e, j, (e / j) if j else None], "miskeys": st["miskeys"],
            "auc_miskey_vs_ok": fr(st["auc"]),
            "budget": {"error_labelled": str(st["b_err"]), "judged": str(st["b_judged"]),
                       "miskeys": str(st["b_miskey"]),
                       "precision": fr(st["b_err"] / st["b_judged"]) if st["b_judged"] else None}}


def _bprec(st):
    return st["b_err"] / st["b_judged"] if st["b_judged"] else None


# ----- New in audit 84: key counts over every archive, the no-key flag, the key-share score, verdicts -----

def key_counts(models, preds, questions):
    """{q: (covered, key)}: how many of `models` have a record for q (a missing or unreadable answer still counts as
    covered), and how many of those picked q's key."""
    out = {}
    for q, (k, key_i) in questions.items():
        cov = key = 0
        for m in models:
            pm = preds.get(m, {})
            if q not in pm:
                continue
            cov += 1
            i = pred_index(pm[q], k)
            if i is not None and i == key_i:
                key += 1
        out[q] = (cov, key)
    return out


def nk_flags(kc, min_cov):
    """{q: (flagged, None)}: flagged when at least `min_cov` archives cover q and none of them picked the key."""
    return {q: (cov >= min_cov and key == 0, None) for q, (cov, key) in kc.items()}


def key_share(kc):
    """{q: minus the share of covering archives that picked the key} (higher = more suspect); 0 when uncovered."""
    return {q: (Fraction(-key, cov) if cov else Fraction(0)) for q, (cov, key) in kc.items()}


def predictions84(st, top20, base_err, base_judged, nk, unan, th):
    """Pre-registered P2-P7 with their numbers (P1 is decided in job.py). st: stratum_stats for panels S1..S4 (ranks
    1-10 ... 31-40); top20: stratum_stats for the ranks 1-20 panel; base_err / base_judged: error-labelled and judged
    Redux questions in the universe; nk: (error-labelled, judged) of the no-key flag; unan: (error-labelled, judged)
    of S1's flag at 10 of 10."""
    s1, s2, s4 = st[0], st[1], st[3]
    p = [_bprec(s1), _bprec(s2), _bprec(s4)]
    a = [s1["auc"], s4["auc"]]
    p20 = _bprec(top20)
    e_nk, j_nk = nk
    e_u, j_u = unan
    return {
        "P2_weaker_flags_more": s4["flags"] > s1["flags"],
        "P2_counts": [s1["flags"], s4["flags"]],
        "P3_budget_precision_falls": bool(all(x is not None for x in p) and p[0] > p[1] > p[2]),
        "P3_precision": [None if x is None else float(x) for x in p],
        "P4_auc_s1_above_s4": bool(all(x is not None for x in a) and a[0] > a[1]),
        "P4_auc": [None if x is None else float(x) for x in a],
        "P5_weakest_still_informative": bool(s4["b_judged"] and base_judged and
                                             s4["b_err"] * base_judged >= th["P5_mult"] * base_err * s4["b_judged"]),
        "P5_counts": [float(s4["b_err"]), float(s4["b_judged"]), base_err, base_judged],
        "P6_top20_not_better": bool(p20 is not None and p[0] is not None and p20 <= p[0]),
        "P6_precision": [None if p20 is None else float(p20), None if p[0] is None else float(p[0])],
        "P7_no_key_beats_unanimous": bool(j_nk >= th["P7_min_judged"] and j_u and
                                          Fraction(e_nk, j_nk) > Fraction(e_u, j_u)),
        "P7_counts": [e_nk, j_nk, e_u, j_u],
    }
