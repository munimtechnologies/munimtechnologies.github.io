"""Global-MMLU KEY-DRIFT forensics (audit 71): why do some translations carry a different answer key from English?

Audit 70 found that Global-MMLU's Chinese (zh) and Korean (ko) test sets give a different answer letter from
English on 176 and 116 of 14,042 questions (German 5, Italian 3, Yoruba 2, Japanese 1, the other 35 languages 0),
while its English rows are exactly MMLU's test set. This module tells the possible causes apart, row by row:

- the translated options were REORDERED and the letter followed the answer (same answer, new letter);
- the options kept their places and the key MOVED to another option (a different answer);
- the options cannot be matched one to one across languages (unresolved).

Options are matched across languages only where no translation is needed: identical text after Unicode NFKC and
stripping, or the same non-empty sequence of numbers. The module also joins English rows to MMLU-Redux 2.0's expert
labels by subject and option texts, to see whether drifted keys sit on questions the experts flagged.

Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import re
import unicodedata
from fractions import Fraction

LETTERS = "ABCD"
OPTION_COLS = ("option_a", "option_b", "option_c", "option_d")
NUMBER_RE = re.compile(r"\d+")
CORRECTION_RE = re.compile(r"^\(?([A-D])\)?\.?$")

OK = "ok"
UNSURE = "expert"
MISKEY = "wrong_groundtruth"
ERROR_TYPES = ("bad_question_clarity", "bad_options_clarity", "no_correct_answer", "multiple_correct_answers",
               "wrong_groundtruth")
KINDS = ("same_answer_new_letter", "different_answer_same_order", "different_answer_reordered", "unresolved")


# ----- one option, one question -----

def norm(s):
    return "" if s is None else unicodedata.normalize("NFKC", str(s)).strip()


def numbers(s):
    """The numbers in an option, in order, as canonical decimal strings (digits of any script; leading zeros
    dropped)."""
    return tuple(str(int(m)) for m in NUMBER_RE.findall(norm(s)))


def signature(option):
    return norm(option), numbers(option)


def key_index(answer):
    """'A'..'D' (any case, outer spaces ignored) -> 0..3; anything else -> None."""
    s = "" if answer is None else str(answer).strip().upper()
    return LETTERS.index(s) if len(s) == 1 and s in LETTERS else None


def is_valid(options, key):
    """At least two options, none blank, and an integer key that indexes one of them."""
    if not isinstance(options, (list, tuple)) or len(options) < 2:
        return False
    if any(o is None or str(o).strip() == "" for o in options):
        return False
    return isinstance(key, int) and not isinstance(key, bool) and 0 <= key < len(options)


def sig_matches(en_sig, xx_sig):
    """Same option without translating: identical text, or the same non-empty number sequence."""
    if en_sig[0] != "" and en_sig[0] == xx_sig[0]:
        return True
    return en_sig[1] != () and en_sig[1] == xx_sig[1]


def matches(en_option, xx_option):
    return sig_matches(signature(en_option), signature(xx_option))


def permutation_sigs(en_sigs, xx_sigs):
    """perm[j] = index of the English option that translated option j matches, when every translated option matches
    exactly one English option and every English option is matched exactly once; otherwise None."""
    k = len(en_sigs)
    if k == 0 or len(xx_sigs) != k:
        return None
    perm = []
    for xs in xx_sigs:
        hits = [i for i, es in enumerate(en_sigs) if sig_matches(es, xs)]
        if len(hits) != 1:
            return None
        perm.append(hits[0])
    return tuple(perm) if len(set(perm)) == k else None


def permutation(en_options, xx_options):
    return permutation_sigs(tuple(signature(o) for o in en_options), tuple(signature(o) for o in xx_options))


def order_of(perm):
    if perm is None:
        return "unresolved"
    return "same_order" if perm == tuple(range(len(perm))) else "reordered"


def kind_of(order, answer):
    """Why a translated key letter differs from English's, from the option order and whether the answer is the
    same option."""
    if answer == "unknown":
        return "unresolved"
    if answer == "same":
        return "same_answer_new_letter"
    return "different_answer_" + order


def pick_longest_credit(options, key):
    """Tie-aware pick-longest credit: 1/t when the key is one of t tied longest options (lengths after strip)."""
    L = [len(str(o).strip()) for o in options]
    hi = max(L)
    return Fraction(1, L.count(hi)) if L[key] == hi else Fraction(0)


# ----- one translation against English -----

def reference(en_rows):
    """{sample_id: English row plus its option signatures}, valid rows only."""
    ref = {}
    for r in en_rows:
        if is_valid(r["options"], r["key"]):
            ref[r["sample_id"]] = dict(r, sigs=tuple(signature(o) for o in r["options"]))
    return ref


def tally_language(ref, rows):
    """Compare one translation with English row by row. Returns (counts, mismatches) where mismatches maps
    sample_id -> (translated key, kind) for valid rows whose key letter differs from English's.

    counts['key_mismatch_all'] counts letter differences on every row found in English, valid or not (audit 70's
    definition); 'cells' cross letter (same / differs) x option order x answer (same / different / unknown)."""
    c = {"n_rows": 0, "missing_in_reference": 0, "invalid": 0, "compared": 0, "key_mismatch_all": 0,
         "key_equal": 0, "key_mismatch": 0, "cells": {}, "kinds": {}}
    mism = {}
    for r in rows:
        c["n_rows"] += 1
        e = ref.get(r["sample_id"])
        if e is None:
            c["missing_in_reference"] += 1
            continue
        if r["key"] != e["key"]:
            c["key_mismatch_all"] += 1
        if not is_valid(r["options"], r["key"]) or len(r["options"]) != len(e["options"]):
            c["invalid"] += 1
            continue
        c["compared"] += 1
        perm = permutation_sigs(e["sigs"], tuple(signature(o) for o in r["options"]))
        order = order_of(perm)
        if perm is None:
            answer = "unknown"
        else:
            answer = "same" if perm[r["key"]] == e["key"] else "different"
        same_letter = r["key"] == e["key"]
        cell = "%s|%s|answer_%s" % ("letter_same" if same_letter else "letter_differs", order, answer)
        c["cells"][cell] = c["cells"].get(cell, 0) + 1
        if same_letter:
            c["key_equal"] += 1
        else:
            c["key_mismatch"] += 1
            kind = kind_of(order, answer)
            c["kinds"][kind] = c["kinds"].get(kind, 0) + 1
            mism[r["sample_id"]] = (r["key"], kind)
    return c, mism


def overlap(a, b):
    """a, b: {sample_id: key}. Shared ids, and how many of them carry the same key in both."""
    shared = set(a) & set(b)
    return {"shared": len(shared), "same_key": sum(1 for s in shared if a[s] == b[s])}


# ----- MMLU-Redux expert labels -----

def normalise_label(error_type):
    return "" if error_type is None else str(error_type).strip().lower()


def label_class(label):
    if label == OK:
        return "ok"
    if label in ERROR_TYPES:
        return "error"
    if label == UNSURE:
        return "unsure"
    return "other"


def letter_correction(raw):
    """A single-letter correction such as 'B', '(c)' or 'D.' -> 0..3; anything else (several letters, digits, text,
    empty) -> None."""
    if raw is None:
        return None
    m = CORRECTION_RE.match(norm(raw).upper())
    return LETTERS.index(m.group(1)) if m else None


def options_key(subject, options):
    return subject, tuple(norm(o) for o in options)


def join_redux(en_rows, redux_rows):
    """Join MMLU-Redux rows to English rows on (subject, option texts) where that key is unique on both sides.
    Returns ({sample_id: redux row}, stats); joined + not_found + ambiguous == n_redux."""
    en_idx, rx_idx = {}, {}
    for r in en_rows:
        en_idx.setdefault(options_key(r["subject"], r["options"]), []).append(r)
    for r in redux_rows:
        rx_idx.setdefault(options_key(r["subject"], r["options"]), []).append(r)
    joined = {}
    st = {"n_redux": len(redux_rows), "joined": 0, "not_found": 0, "ambiguous": 0, "question_equal": 0,
          "key_equal": 0}
    for k, rs in rx_idx.items():
        es = en_idx.get(k, [])
        if not es:
            st["not_found"] += len(rs)
            continue
        if len(rs) != 1 or len(es) != 1:
            st["ambiguous"] += len(rs)
            continue
        e, x = es[0], rs[0]
        joined[e["sample_id"]] = x
        st["joined"] += 1
        if norm(e.get("question")) == norm(x.get("question")):
            st["question_equal"] += 1
        if e["key"] == x["key"]:
            st["key_equal"] += 1
    return joined, st


def redux_profile(ids, joined):
    """Expert labels of the given English sample_ids that joined to MMLU-Redux."""
    out = {"n": 0, "joined": 0, "classes": {}, "labels": {}}
    for s in ids:
        out["n"] += 1
        x = joined.get(s)
        if x is None:
            continue
        out["joined"] += 1
        c = label_class(x["label"])
        out["classes"][c] = out["classes"].get(c, 0) + 1
        out["labels"][x["label"]] = out["labels"].get(x["label"], 0) + 1
    return out


def correction_agreement(keys, joined):
    """keys: {sample_id: a translation's key}. Over joined miskeyed rows whose correction is one letter different
    from the published key: how often the translation's key equals the experts' correction, the published key, or
    neither."""
    out = {"n": 0, "equals_correction": 0, "equals_published": 0, "other": 0}
    for s in sorted(keys):
        x = joined.get(s)
        if x is None or x["label"] != MISKEY:
            continue
        c = letter_correction(x.get("correct"))
        if c is None or c == x["key"]:
            continue
        out["n"] += 1
        k = keys[s]
        if k == c:
            out["equals_correction"] += 1
        elif k == x["key"]:
            out["equals_published"] += 1
        else:
            out["other"] += 1
    return out
