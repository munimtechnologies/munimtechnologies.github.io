"""Do MMLU-Pro's model-consensus flags point at options MMLU-Pro ADDED? Core logic for audit 78.

Audit 77 flagged 1,210 MMLU-Pro questions where at least 6 of the 10 most accurate published models pick the same
non-key option (and more of them than pick the key). Most flags on questions MMLU-Redux 2.0's experts reviewed fell on
questions they cleared. Redux reviewed MMLU's four options; MMLU-Pro added up to six more per question. This audit maps
every MMLU-derived MMLU-Pro question back to its MMLU row, labels each MMLU-Pro option ORIGINAL (one of MMLU's four)
or ADDED, and asks whether the consensus option on a flagged question is one MMLU-Pro added.

The join, panel and flag functions are copied unchanged from audit 77 (consensus77.py). Standard library only.
Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
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
ORIGINAL = "original"
ADDED = "added"


def pred_index(pred, k):
    """Index of a predicted letter A-J within k options, or None when missing / malformed / out of range."""
    if not isinstance(pred, str):
        return None
    p = pred.strip().upper()
    if len(p) != 1 or p not in LETTERS:
        return None
    i = LETTERS.index(p)
    return i if i < k else None


# ----- MMLU-Redux -> MMLU -> MMLU-Pro join (audit 75's rules, copied from audit 77) -----

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


# ----- The panel and the flag (copied from audit 77) -----

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


# ----- New in audit 78: MMLU -> MMLU-Pro map for every MMLU test row, option origins -----

def map_mmlu_to_pro(mmlu_rows, pro_rows):
    """Join every MMLU row with a valid key to MMLU-Pro with audit 75's pool rule (same normalised stem, at least 3 of
    MMLU's options among MMLU-Pro's, same subject preferred). Returns (mapping {MMLU-Pro qid: tuple of MMLU's
    normalised choices}, counts). counts tallies MMLU rows by join status, plus 'multi_mmlu': MMLU-Pro ids reached by
    MMLU rows with two different choice sets, which are dropped."""
    pi = pro_index(pro_rows)
    counts = {"in_pro": 0, "ambiguous_pro": 0, "not_in_pro": 0, "multi_mmlu": 0}
    seen = {}
    for r in mmlu_rows:
        ch = list(r["choices"] or [])
        a = r["answer"]
        if not isinstance(a, int) or a < 0 or a >= len(ch):
            continue
        st, pool, _f = join_pro_pool(r["subject"], r["question"], ch, pi)
        counts[st] += 1
        if st != "in_pro":
            continue
        seen.setdefault(int(pool[0]["question_id"]), set()).add(tuple(norm(c) for c in ch))
    mapping = {}
    for qid in sorted(seen):
        if len(seen[qid]) > 1:
            counts["multi_mmlu"] += 1
        else:
            mapping[qid] = next(iter(seen[qid]))
    return mapping, counts


def origins(options, mmlu_choices):
    """(per-option 'original' | 'added', intact). An option is ORIGINAL when its normalised text is one of MMLU's
    choices. intact: MMLU has four distinct choices and every one of them is among MMLU-Pro's options."""
    s = set(mmlu_choices)
    opts = [norm(o) for o in options]
    return [ORIGINAL if o in s else ADDED for o in opts], (len(s) == 4 and s <= set(opts))


def consensus_origin(flags, origin_by_q, qids):
    """(original, added): flagged questions in qids with known origins, by the origin of their consensus option."""
    o = a = 0
    for q in qids:
        f, ci = flags[q]
        if not f or q not in origin_by_q:
            continue
        if origin_by_q[q][ci] == ADDED:
            a += 1
        else:
            o += 1
    return o, a


def wrong_pick_origin(tallies, keys, flags, origin_by_q, qids):
    """(original, added): the panel's non-key picks on UNFLAGGED questions in qids with known origins."""
    o = a = 0
    for q in qids:
        if flags[q][0] or q not in origin_by_q:
            continue
        for i, n in enumerate(tallies[q][0]):
            if i == keys[q] or n == 0:
                continue
            if origin_by_q[q][i] == ADDED:
                a += n
            else:
                o += n
    return o, a


def predictions78(g, flags, tallies, keys, origin_by_q, category, th):
    """Pre-registered P2-P5 with their counts (P1 is decided in job.py)."""
    om, am = consensus_origin(flags, origin_by_q, g["miskey"])
    oo, ao = consensus_origin(flags, origin_by_q, g["ok"])
    wo, wa = wrong_pick_origin(tallies, keys, flags, origin_by_q, g["ori_mmlu"])
    law = [q for q in g["ori_mmlu"] if category[q] == "law"]
    rest = [q for q in g["ori_mmlu"] if category[q] != "law"]
    ol, al = consensus_origin(flags, origin_by_q, law)
    orr, ar = consensus_origin(flags, origin_by_q, rest)
    return {
        "P2_miskey_consensus_original": bool(om + am and Fraction(om, om + am) >= th["P2_original"]),
        "P2_counts": [om, am],
        "P3_ok_consensus_added_share": bool(oo + ao and Fraction(ao, oo + ao) >= th["P3_added"]),
        "P3_counts": [oo, ao],
        "P4_ok_added_above_wrong_pick_baseline": bool(oo + ao and wo + wa and ao * (wo + wa) > wa * (oo + ao)),
        "P4_counts": [oo, ao, wo, wa],
        "P5_law_added_above_rest": bool(ol + al and orr + ar and al * (orr + ar) > ar * (ol + al)),
        "P5_counts": [ol, al, orr, ar],
    }
