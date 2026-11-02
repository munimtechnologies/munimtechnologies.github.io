"""Model-consensus miskey flags for MMLU-Pro, checked against MMLU-Redux 2.0's experts. Core logic for audit 77.

Audit 76 found that on 46 MMLU-Pro questions whose key MMLU-Redux's experts marked wrong, 45 published models pick
the experts' answer far more often than the key. This audit turns that into a question-level flag for all 12,032
MMLU-Pro questions: a question is FLAGGED when at least MIN_AGREE of the PANEL_SIZE most accurate published models
pick the same option other than the key, and more of them pick it than pick the key. The flag is then validated
where experts have looked (MMLU-Redux 2.0's labels, joined to MMLU-Pro with audit 75's rules) and applied where they
have not.

Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

from fractions import Fraction

LETTERS = "ABCDEFGHIJ"
OK = "ok"
UNSURE = "expert"
MISKEY = "wrong_groundtruth"
ERROR_TYPES = ("bad_question_clarity", "bad_options_clarity", "no_correct_answer", "multiple_correct_answers",
               MISKEY)
JUDGED = (OK,) + ERROR_TYPES
MIN_OVERLAP = 3
PRO_PREFIX = "ori_mmlu-"
FAMILIES = ("ori_mmlu", "stemez", "theoremQA", "scibench")


def pred_index(pred, k):
    """Index of a predicted letter A-J within k options, or None when missing / malformed / out of range
    (the same rule as audits 65, 66 and 76)."""
    if not isinstance(pred, str):
        return None
    p = pred.strip().upper()
    if len(p) != 1 or p not in LETTERS:
        return None
    i = LETTERS.index(p)
    return i if i < k else None


# ----- MMLU-Redux -> MMLU -> MMLU-Pro join (audit 75's rules, unchanged) -----

def norm(s):
    return " ".join(("" if s is None else str(s)).split())


def label_of(error_type):
    return "" if error_type is None else str(error_type).strip().lower()


def mmlu_index(mmlu_rows):
    """{(subject, norm question, tuple of norm choices): [answer, ...]} over MMLU rows with a valid key."""
    out = {}
    for r in mmlu_rows:
        ch = list(r["choices"] or [])
        a = r["answer"]
        if not isinstance(a, int) or a < 0 or a >= len(ch):
            continue
        out.setdefault((r["subject"], norm(r["question"]), tuple(norm(c) for c in ch)), []).append(a)
    return out


def join_mmlu(redux_row, index):
    """('joined', MMLU key) | ('no_match', None) | ('ambiguous', None)."""
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
    """{norm question: [row, ...]} over MMLU-Pro rows whose src starts with 'ori_mmlu-'."""
    out = {}
    for r in pro_rows:
        if pro_subject(r["src"]) is None:
            continue
        out.setdefault(norm(r["question"]), []).append(r)
    return out


def overlap(choices, options):
    return len(set(norm(c) for c in choices) & set(norm(o) for o in options or []))


def join_pro_pool(subject, question, choices, index):
    """(status, pool, flags) with audit 75's rule: candidates share the normalised stem and at least MIN_OVERLAP of
    MMLU's options; same-subject candidates are preferred. status 'in_pro' (pool of one), 'ambiguous_pro' (pool of
    several, all returned) or 'not_in_pro'."""
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
    """Redux label per MMLU-Pro question_id for single matches. Returns (labels, ambiguous_ids, miskey_ids, counts):
    labels {qid: label} ('conflict' if two Redux rows with different labels match one id), ambiguous_ids (every id in
    an ambiguous pool), miskey_ids (ids single-matched by a wrong_groundtruth row), counts as audit 75 reports them."""
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


# ----- The panel and the flag -----

def accuracy(correct, n):
    return Fraction(correct, n) if n else Fraction(0)


def select_panel(acc, size):
    """acc: {model: (correct, n_joined)}. The `size` most accurate models; ties broken by model name."""
    return sorted(acc, key=lambda m: (-accuracy(*acc[m]), m))[:size]


def votes(preds, k):
    """Raw predictions -> (list of k pick counts, number missing or malformed)."""
    counts, none = [0] * k, 0
    for p in preds:
        i = pred_index(p, k)
        if i is None:
            none += 1
        else:
            counts[i] += 1
    return counts, none


def consensus(counts, key_i):
    """(index, count) of the single most-picked option other than the key; (None, top count) if no non-key option
    was picked or the top is tied."""
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
    """(flagged, consensus index or None, consensus count). FLAGGED: one non-key option is picked by at least
    min_agree panel models and by more of them than pick the key."""
    ci, n = consensus(counts, key_i)
    flagged = ci is not None and n >= min_agree and n > counts[key_i]
    return flagged, ci, n


def panel_flags(panel, preds_by_model, questions, min_agree):
    """questions: {qid: (k, key_i)}; preds_by_model: {model: {qid: raw pred}}. A panel model with no joined
    prediction on a question counts as missing. Returns ({qid: (flagged, consensus index)}, {qid: (counts, none)})."""
    flags, tallies = {}, {}
    for q, (k, key_i) in questions.items():
        counts, none = votes([preds_by_model.get(m, {}).get(q) for m in panel], k)
        f, ci, _n = flag_question(counts, key_i, min_agree)
        flags[q] = (f, ci)
        tallies[q] = (counts, none)
    return flags, tallies


# ----- Groups and the pre-registered predictions -----

def groups(qids, family, labels, ambiguous_ids):
    """Question ids by Redux status and by MMLU-Pro source family."""
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


def predictions(g, flags, targets, th):
    """g: groups(); flags: {qid: (flagged, consensus index)}; targets: {qid: experts' answer index} for audit 76's
    targets present in the data. Returns the verdicts P2-P6 with their counts (P1 is decided in job.py)."""
    fm, nm = n_flagged(g["miskey"], flags), len(g["miskey"])
    fo, no = n_flagged(g["ok"], flags), len(g["ok"])
    tq = sorted(targets)
    ft = [q for q in tq if flags[q][0]]
    matched = [q for q in ft if flags[q][1] == targets[q]]
    judged = g["miskey"] + g["ok"] + g["other_error"]
    errs = g["miskey"] + g["other_error"]
    fj, fe = n_flagged(judged, flags), n_flagged(errs, flags)
    fu, nu = n_flagged(g["unreviewed_ori_mmlu"], flags), len(g["unreviewed_ori_mmlu"])
    fs, ns = n_flagged(g["stemez"], flags), len(g["stemez"])
    fr, nr = n_flagged(g["ori_mmlu"], flags), len(g["ori_mmlu"])
    return {
        "P2_miskey_flag_rate_5x_ok": bool(nm and no and fm > 0 and fm * no >= th["P2_ratio"] * fo * nm),
        "P2_counts": [fm, nm, fo, no],
        "P3_recall_and_match_on_targets": bool(tq and ft and Fraction(len(ft), len(tq)) >= th["P3_recall"]
                                               and Fraction(len(matched), len(ft)) >= th["P3_match"]),
        "P3_counts": [len(ft), len(tq), len(matched)],
        "P4_flag_precision_on_judged": bool(fj and Fraction(fe, fj) >= th["P4_precision"]),
        "P4_counts": [fe, fj],
        "P5_unreviewed_above_ok": bool(nu and no and fu * no > fo * nu),
        "P5_counts": [fu, nu, fo, no],
        "P6_stemez_above_mmlu_derived": bool(ns and nr and fs * nr > fr * ns),
        "P6_counts": [fs, ns, fr, nr],
    }


def curve(tallies, keys, g, ms):
    """Exploratory: flagged counts per group for each min_agree in ms (panel fixed)."""
    out = []
    for m in ms:
        fl = {q: (flag_question(tallies[q][0], keys[q], m)[0], None) for q in tallies}
        out.append({"min_agree": m, **{name: [n_flagged(ids, fl), len(ids)] for name, ids in sorted(g.items())}})
    return out
