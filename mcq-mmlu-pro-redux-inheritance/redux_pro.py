"""Which of MMLU's expert-flagged errors did MMLU-Pro inherit? (audit 75)

MMLU-Redux 2.0 (Gema et al. 2024, arXiv 2406.04127; CC BY 4.0) gives an expert error label for 100 MMLU test
questions in each of 57 subjects and, for miskeyed ones, the answer the experts think is right. Its paper says that
"errors from the original MMLU persist in the extended MMLU-Pro benchmark" but gives no count. MMLU-Pro (Wang et al.
2024, arXiv 2406.01574; MIT) took 6,810 of its 12,032 test questions from MMLU (`src` "ori_mmlu-<subject>").

This module joins the two:
1. each Redux row to MMLU test by (subject, question, options) -- MMLU supplies the published key;
2. each joined MMLU question to MMLU-Pro's ori_mmlu rows by normalised question text, kept only when at least
   MIN_OVERLAP of MMLU's four options are among the MMLU-Pro options (generic stems repeat inside a subject);
3. classifies MMLU-Pro's key against MMLU's: kept (same text), moved (another MMLU option), new (neither);
4. for miskeyed rows, resolves the experts' suggested answer and checks it against MMLU-Pro's options and key;
5. compares how often flagged and expert-OK questions made it into MMLU-Pro (pooled and by subject, CMH).

Only ids, labels and counts leave this module: no question or option text. Standard library only. Apache-2.0.
Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import re

OK = "ok"
UNSURE = "expert"
ERROR_TYPES = ("bad_question_clarity", "bad_options_clarity", "no_correct_answer", "multiple_correct_answers",
               "wrong_groundtruth")
JUDGED = (OK,) + ERROR_TYPES
MISKEY = "wrong_groundtruth"
MIN_OVERLAP = 3
PRO_PREFIX = "ori_mmlu-"

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
SPLIT_RE = re.compile(r"\s*(?:,|;|/|&|\band\b)\s*")
LETTER_RE = re.compile(r"^\(?([A-Z])\)?\.?$")
DIGIT_RE = re.compile(r"^[0-9]$")

CHI2_CRIT_1DF_005 = 3.841
CHI2_CRIT_1DF_0001 = 10.828

VARIANTS = (("primary", None), ("digits_0_based", 0), ("digits_1_based", 1))


def norm(s):
    """Whitespace-normalised text (case and punctuation kept), as audit 62."""
    return " ".join(("" if s is None else str(s)).split())


def label_of(error_type):
    return "" if error_type is None else str(error_type).strip().lower()


def letter(i):
    return None if i is None else LETTERS[i]


# ----- the experts' suggested answer (as audit 69) -----

def parse_correction(raw, options):
    """correct_answer -> (format, indices): 'none', 'letters', 'text', 'digits' (base undocumented), 'unmatched'."""
    if raw is None or str(raw).strip() == "":
        return "none", ()
    s = str(raw).strip()
    k = len(options)
    tokens = [t for t in SPLIT_RE.split(s) if t != ""]
    letters = [LETTER_RE.match(t) for t in tokens]
    if tokens and all(letters):
        idx = tuple(LETTERS.index(m.group(1)) for m in letters)
        if all(i < k for i in idx):
            return "letters", idx
    hits = [i for i, o in enumerate(options) if str(o).strip().casefold() == s.casefold()]
    if len(hits) == 1:
        return "text", (hits[0],)
    if tokens and all(DIGIT_RE.match(t) for t in tokens) and all(int(t) <= k for t in tokens):
        return "digits", tuple(int(t) for t in tokens)
    return "unmatched", ()


def resolve(fmt, idx, k, digit_base=None):
    """Indices of the suggested answer, or None if unresolved (digits need digit_base 0 or 1)."""
    if fmt in ("letters", "text"):
        return idx
    if fmt == "digits" and digit_base in (0, 1):
        out = tuple(i - digit_base for i in idx)
        return out if all(0 <= i < k for i in out) else None
    return None


def single_correction(raw, choices, digit_base=None):
    """(format, index) where index is the ONE suggested option, or None."""
    fmt, idx = parse_correction(raw, choices)
    res = resolve(fmt, idx, len(choices), digit_base)
    if res is None or len(res) != 1:
        return fmt, None
    return fmt, res[0]


# ----- joins -----

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


def join_pro(subject, question, choices, index):
    """(status, row, flags). status: 'in_pro' (one MMLU-Pro row), 'ambiguous_pro' (several), 'not_in_pro'.
    Same-subject candidates are preferred; flags: 'stem_only' (the stem exists but no candidate shares
    MIN_OVERLAP options), 'cross_subject' (the one match is filed under another subject)."""
    cands = index.get(norm(question), [])
    if not cands:
        return "not_in_pro", None, ()
    good = [r for r in cands if overlap(choices, r["options"]) >= MIN_OVERLAP]
    if not good:
        return "not_in_pro", None, ("stem_only",)
    same = [r for r in good if pro_subject(r["src"]) == subject]
    pool = same if same else good
    if len(pool) > 1:
        return "ambiguous_pro", None, ()
    flags = () if same else ("cross_subject",)
    return "in_pro", pool[0], flags


def key_status(choices, key, options, pro_key):
    """'kept' (MMLU-Pro's key text is MMLU's key text), 'moved' (another MMLU option), 'new' (neither)."""
    g = norm(options[pro_key])
    if g == norm(choices[key]):
        return "kept"
    if g in set(norm(c) for i, c in enumerate(choices) if i != key):
        return "moved"
    return "new"


def pro_position(text, options):
    t = norm(text)
    for i, o in enumerate(options):
        if norm(o) == t:
            return i
    return None


# ----- statistics (as audit 69) -----

def two_by_two(a, b, c, d):
    """Pearson chi-square (df 1, no continuity correction) for [[a, b], [c, d]]; row 1 rate a/(a+b) vs c/(c+d)."""
    n = a + b + c + d
    r1, r2, c1, c2 = a + b, c + d, a + c, b + d
    rate1 = (a / r1) if r1 else None
    rate2 = (c / r2) if r2 else None
    stat = (n * (a * d - b * c) ** 2 / (r1 * r2 * c1 * c2)) if (n and r1 and r2 and c1 and c2) else None
    return {"table": [[a, b], [c, d]], "rate_1": rate1, "rate_2": rate2,
            "risk_ratio": (rate1 / rate2) if (rate1 is not None and rate2) else None,
            "chi_square_stat": stat, "df": 1,
            "rejected_0.05": (stat > CHI2_CRIT_1DF_005) if stat is not None else None,
            "rejected_0.001": (stat > CHI2_CRIT_1DF_0001) if stat is not None else None}


def cmh(strata):
    """Cochran-Mantel-Haenszel over 2x2 strata (a, b, c, d), no continuity correction, df 1."""
    num = var = or_n = or_d = 0.0
    n_inf = 0
    for a, b, c, d in strata:
        n = a + b + c + d
        if n < 2:
            continue
        r1, r2, c1, c2 = a + b, c + d, a + c, b + d
        num += a - r1 * c1 / n
        v = r1 * r2 * c1 * c2 / (n * n * (n - 1))
        var += v
        or_n += a * d / n
        or_d += b * c / n
        if v > 0:
            n_inf += 1
    stat = (num * num / var) if var > 0 else None
    return {"n_strata": len(strata), "n_informative_strata": n_inf, "sum_observed_minus_expected": num,
            "cmh_stat": stat, "df": 1, "mh_odds_ratio": (or_n / or_d) if or_d > 0 else None,
            "rejected_0.05": (stat > CHI2_CRIT_1DF_005) if stat is not None else None,
            "rejected_0.001": (stat > CHI2_CRIT_1DF_0001) if stat is not None else None}


# ----- the whole analysis -----

def analyse(redux_rows, mmlu_rows, pro_rows):
    """redux_rows: dicts subject, question, choices, answer, label, correct. mmlu_rows: subject, question, choices,
    answer. pro_rows: question_id, question, options, answer_index, category, src. Returns (summary, flags)."""
    mi = mmlu_index(mmlu_rows)
    pi = pro_index(pro_rows)
    S = {"redux_mmlu": {"joined": 0, "no_match": 0, "ambiguous": 0}, "redux_answer_equals_mmlu_key": 0,
         "pro_join": {"in_pro": 0, "ambiguous_pro": 0, "not_in_pro": 0, "stem_only": 0, "cross_subject": 0},
         "by_label": {}, "moved_labels": {}, "new_labels": {},
         "miskey": {"in_pro_unique": 0, "kept": 0, "moved": 0, "new": 0,
                    "corrections": {v: {"resolved": 0, "resolved_kept": 0, "kept_present": 0,
                                        "pro_key_is_correction": 0} for v, _b in VARIANTS}}}
    strata = {}
    flags = []
    for r in redux_rows:
        st, key = join_mmlu(r, mi)
        S["redux_mmlu"][st] += 1
        if st != "joined":
            continue
        choices = list(r["choices"])
        S["redux_answer_equals_mmlu_key"] += int(r["answer"] == key)
        lab = r["label"]
        bl = S["by_label"].setdefault(lab, {"n": 0, "in_pro": 0, "kept": 0, "moved": 0, "new": 0})
        bl["n"] += 1
        pst, prow, pflags = join_pro(r["subject"], r["question"], choices, pi)
        S["pro_join"][pst] += 1
        for f in pflags:
            S["pro_join"][f] += 1
        included = pst in ("in_pro", "ambiguous_pro")
        bl["in_pro"] += int(included)
        if lab in JUDGED:
            cell = strata.setdefault(r["subject"], [0, 0, 0, 0])
            cell[(0 if lab != OK else 2) + (0 if included else 1)] += 1
        if pst != "in_pro":
            continue
        opts = list(prow["options"])
        ks = key_status(choices, key, opts, prow["answer_index"])
        bl[ks] += 1
        if ks == "moved":
            S["moved_labels"][lab] = S["moved_labels"].get(lab, 0) + 1
        elif ks == "new":
            S["new_labels"][lab] = S["new_labels"].get(lab, 0) + 1
        expert = {}
        fmt = None
        for v, base in VARIANTS:
            fmt, ci = single_correction(r.get("correct"), choices, base)
            expert[v] = None if ci is None else letter(pro_position(choices[ci], opts))
            if lab == MISKEY and ci is not None and ci != key:
                c = S["miskey"]["corrections"][v]
                c["resolved"] += 1
                present = pro_position(choices[ci], opts) is not None
                if ks == "kept":
                    c["resolved_kept"] += 1
                    c["kept_present"] += int(present)
                c["pro_key_is_correction"] += int(norm(opts[prow["answer_index"]]) == norm(choices[ci]))
        if lab == MISKEY:
            S["miskey"]["in_pro_unique"] += 1
            S["miskey"][ks] += 1
        if lab != OK:
            flags.append({"question_id": prow["question_id"], "category": prow["category"], "src": prow["src"],
                          "label": lab, "key_status": ks, "pro_answer": letter(prow["answer_index"]),
                          "expert_answer": expert["primary"], "expert_answer_digits_0_based": expert["digits_0_based"],
                          "expert_answer_digits_1_based": expert["digits_1_based"], "correction_format": fmt})
    order = sorted(strata)
    a, b, c, d = (sum(strata[s][i] for s in order) for i in range(4))
    S["inclusion"] = {"pooled": two_by_two(a, b, c, d), "by_subject_cmh": cmh([tuple(strata[s]) for s in order]),
                      "strata": {s: strata[s] for s in order}}
    flags.sort(key=lambda f: f["question_id"])
    return S, flags


def _r6(x):
    return None if x is None else round(x, 6)


def fixture_summary(S, flags):
    """The fields the hand-traced fixture pins (floats rounded to 6 places)."""
    inc = S["inclusion"]
    p, h = inc["pooled"], inc["by_subject_cmh"]
    return {
        "redux_mmlu": S["redux_mmlu"], "redux_answer_equals_mmlu_key": S["redux_answer_equals_mmlu_key"],
        "pro_join": S["pro_join"], "by_label": S["by_label"], "moved_labels": S["moved_labels"],
        "new_labels": S["new_labels"], "miskey": S["miskey"],
        "inclusion_table": p["table"], "inclusion_rr": _r6(p["risk_ratio"]), "inclusion_chi2": _r6(p["chi_square_stat"]),
        "cmh_o_minus_e": _r6(h["sum_observed_minus_expected"]), "cmh_stat": _r6(h["cmh_stat"]),
        "cmh_mh_or": _r6(h["mh_odds_ratio"]), "cmh_informative": h["n_informative_strata"],
        "strata": inc["strata"],
        "flags": [(f["question_id"], f["label"], f["key_status"], f["pro_answer"], f["expert_answer"],
                   f["expert_answer_digits_0_based"], f["expert_answer_digits_1_based"], f["correction_format"])
                  for f in flags],
    }
