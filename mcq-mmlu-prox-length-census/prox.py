"""Does MMLU-Pro's answer-length shortcut survive translation? Core logic for audit 67.

Audits 61-63 found that on MMLU-Pro a question-free "pick the longest option" heuristic scores 18.4% pooled (chance
11.1%) and about 67% on the STEM-website (src stemez-) biology and psychology questions. MMLU-ProX (li-lab/MMLU-ProX)
translates MMLU-Pro into 29 languages with the options kept in the same order. This module joins every translated
question back to its English MMLU-Pro row and, per language, measures on the same questions:

- the tie-aware pick-longest accuracy in the translation, against the exact variable-k chance baseline and against
  English pick-longest on the very same questions;
- retention: the translation's lift over chance divided by English's lift over chance;
- agreement: where English has a unique longest option, how often the translation's unique longest option is the
  same one.

Lengths are characters (Unicode code points) after str.strip(). Standard library only. Apache-2.0.
"""

from fractions import Fraction

import model_length as ml

NA = "N/A"
N_SLOTS = 10
JOIN_KEYS = ("question_id_src", "question_id")

P1_MIN_OK_SHARE = 0.95
MIN_LANGS = 25          # P2-P5 and P7 are scored only when at least this many languages were analysed
P3_FLOOR = 0.5
P3_MIN = 25
P4_LOW, P4_HIGH = 0.6, 1.2
P5_MIN = 0.70
P6_TOL = 0.005
NO_SPACE = ("zh", "ja", "ko")


def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def slots(xrow):
    """The ten option columns of an MMLU-ProX row, in order."""
    return [xrow.get("option_%d" % j) for j in range(N_SLOTS)]


def _blank(o):
    return o is None or str(o).strip() in ("", NA)


def unique_longest(options):
    """Index of the unique longest option, or None when the maximum length is tied."""
    L = ml.lens(options)
    m = max(L)
    return L.index(m) if L.count(m) == 1 else None


def join_row(xrow, pro_by_id, key):
    """(status, MMLU-Pro row or None). status: ok | no_id | answer_differ | padding_differ | empty_option.
    The translated row must carry the English answer index, have N/A (or blank) in every slot past the English option
    count k, and a non-blank option in each of the first k slots."""
    q = pro_by_id.get(_int(xrow.get(key)))
    if q is None:
        return "no_id", None
    if _int(xrow.get("answer_index")) != q["answer_index"]:
        return "answer_differ", q
    s = slots(xrow)
    k = len(q["options"])
    if k > N_SLOTS or not all(_blank(o) for o in s[k:]):
        return "padding_differ", q
    if any(o is None or str(o).strip() == "" for o in s[:k]):
        return "empty_option", q
    return "ok", q


def best_key(xrows, pro_by_id):
    """Join statuses under each candidate key; the key with the most 'ok' rows wins (ties: the first key)."""
    res = {}
    for key in JOIN_KEYS:
        st = {}
        for r in xrows:
            s, _ = join_row(r, pro_by_id, key)
            st[s] = st.get(s, 0) + 1
        res[key] = st
    best = max(JOIN_KEYS, key=lambda k: (res[k].get("ok", 0), -JOIN_KEYS.index(k)))
    return best, res


def new_acc():
    return {"n": 0, "pl": Fraction(0), "chance": Fraction(0), "en_pl": Fraction(0), "ul_den": 0, "ul_agree": 0}


def add(acc, en_options, x_options, gold):
    """One question: English options (MMLU-Pro), translated options (same order, same k) and the gold index."""
    k = len(en_options)
    acc["n"] += 1
    acc["pl"] += ml.pick_longest_credit(x_options, gold)
    acc["chance"] += Fraction(1, k)
    acc["en_pl"] += ml.pick_longest_credit(en_options, gold)
    e = unique_longest(en_options)
    if e is not None:
        acc["ul_den"] += 1
        if unique_longest(x_options) == e:
            acc["ul_agree"] += 1


def keys_for(row):
    """Audit 65's keys (ALL, fam:*, both biology + psychology subsets) plus the MMLU-Pro category."""
    return ml.keys_for(row) + ["cat:" + str(row["category"])]


def analyse_language(xrows, pro_by_id):
    """Join one language's rows under the best key, skip duplicate MMLU-Pro ids, accumulate per key.
    Returns (info, accumulators)."""
    best, status = best_key(xrows, pro_by_id)
    accs = {}
    seen = set()
    dup = 0
    src_match = 0
    identical = 0
    for r in xrows:
        s, q = join_row(r, pro_by_id, best)
        if s != "ok":
            continue
        qid = q["question_id"]
        if qid in seen:
            dup += 1
            continue
        seen.add(qid)
        k = len(q["options"])
        xo = [str(o) for o in slots(r)[:k]]
        eo = [str(o) for o in q["options"]]
        if (r.get("src") or "") == (q["src"] or ""):
            src_match += 1
        if [o.strip() for o in xo] == [o.strip() for o in eo]:
            identical += 1
        for key in keys_for(q):
            add(accs.setdefault(key, new_acc()), eo, xo, q["answer_index"])
    n = len(xrows)
    info = {"rows": n, "key": best, "join_status": status, "joined": len(seen), "duplicates": dup,
            "ok_share": len(seen) / n if n else 0.0, "src_match": src_match,
            "options_identical_to_english": identical}
    return info, accs


def report(acc):
    n = acc["n"]
    if not n:
        return {"n": 0}
    pl = acc["pl"] / n
    ch = acc["chance"] / n
    en = acc["en_pl"] / n
    lift = pl - ch
    en_lift = en - ch
    return {
        "n": n,
        "pick_longest": float(pl),
        "chance": float(ch),
        "lift": float(lift),
        "en_pick_longest": float(en),
        "en_lift": float(en_lift),
        "retention": float(lift / en_lift) if en_lift else None,
        "ul_den": acc["ul_den"],
        "ul_agreement": acc["ul_agree"] / acc["ul_den"] if acc["ul_den"] else None,
    }


def _median(vals):
    v = sorted(vals)
    if not v:
        return None
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2


def predictions(reports, join_info, n_expected, min_langs=MIN_LANGS, p3_min=P3_MIN):
    """Pre-registered predictions. reports: lang -> key -> report (languages with joined rows); join_info: lang ->
    {'ok_share': float, ...} for every attempted language. Decided before any MMLU-ProX file was opened."""
    langs = sorted(reports)
    enough = len(langs) >= min_langs
    all_r = {l: reports[l].get("ALL", {}) for l in langs}

    # P1: every one of the 29 languages joins at least 95% of its test rows cleanly.
    shares = {l: join_info[l].get("ok_share", 0.0) for l in join_info}
    p1 = len(join_info) == n_expected and all(s >= P1_MIN_OK_SHARE for s in shares.values())

    # P2: pick-longest beats chance pooled in every analysed language.
    lifts = {l: all_r[l].get("lift") for l in langs}
    p2 = enough and all(lifts[l] is not None and lifts[l] > 0 for l in langs)

    # P3: on STEM-website biology + psychology pick-longest scores at least 50% in at least 25 languages.
    bp = {l: reports[l].get("sub:stemez-biopsy", {}).get("pick_longest") for l in langs}
    p3_wins = [l for l in langs if bp[l] is not None and bp[l] >= P3_FLOOR]
    p3 = enough and len(p3_wins) >= p3_min

    # P4: the median language keeps between 60% and 120% of English's pooled lift on the same questions.
    ret = {l: all_r[l].get("retention") for l in langs}
    med_ret = _median([v for v in ret.values() if v is not None])
    p4 = enough and med_ret is not None and P4_LOW <= med_ret <= P4_HIGH

    # P5: in the median language, English's unique longest option is still the unique longest at least 70% of the time.
    agr = {l: all_r[l].get("ul_agreement") for l in langs}
    med_agr = _median([v for v in agr.values() if v is not None])
    p5 = enough and med_agr is not None and med_agr >= P5_MIN

    # P6: the 'en' config reproduces English MMLU-Pro's pooled pick-longest on the same questions within 0.5 points.
    en = all_r.get("en", {})
    gap = abs(en["pick_longest"] - en["en_pick_longest"]) if en.get("n") else None
    p6 = gap is not None and gap <= P6_TOL

    # P7: Chinese, Japanese and Korean each keep less pooled lift than the median language.
    p7 = (enough and med_ret is not None
          and all(ret.get(l) is not None and ret[l] < med_ret for l in NO_SPACE))

    return {
        "P1_every_language_joins_95pct": p1,
        "P1_detail": {"ok_share": shares, "min": P1_MIN_OK_SHARE, "n_expected": n_expected},
        "P2_pick_longest_beats_chance_in_every_language": p2,
        "P2_detail": {"lift": lifts},
        "P3_stemez_biopsy_at_least_half_in_25_languages": p3,
        "P3_detail": {"pick_longest": bp, "at_least_half": p3_wins, "needed": p3_min},
        "P4_median_retention_in_0_6_1_2": p4,
        "P4_detail": {"retention": ret, "median": med_ret, "range": [P4_LOW, P4_HIGH]},
        "P5_median_unique_longest_agreement_at_least_0_70": p5,
        "P5_detail": {"ul_agreement": agr, "median": med_agr},
        "P6_en_config_reproduces_english_within_0_005": p6,
        "P6_detail": {"gap": gap, "tolerance": P6_TOL},
        "P7_zh_ja_ko_below_median_retention": p7,
        "P7_detail": {"languages": list(NO_SPACE), "retention": {l: ret.get(l) for l in NO_SPACE},
                      "median": med_ret},
        "languages_analysed": len(langs),
    }
