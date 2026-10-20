# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
#
# Faithful reproduction of the two IFEval checkers that pass a user-supplied
# string straight into Python's `re` engine without escaping it:
#
#   * KeywordFrequencyChecker  (instruction_id "keywords:frequency")
#       actual = len(re.findall(self._keyword, value, flags=re.IGNORECASE))
#       pass if  (actual < frequency)  for relation "less than"
#       pass if  (actual >= frequency) for relation "at least"
#
#   * ForbiddenWords           (instruction_id "keywords:forbidden_words")
#       for word in words:
#           if re.search(r"\b" + word + r"\b", value, flags=re.IGNORECASE):
#               return False   # a forbidden word was found -> instruction FAILED
#       return True
#
# Source (verbatim regex construction) confirmed against
# google-research/google-research instruction_following_eval/instructions.py:
# neither checker calls re.escape, so any regex metacharacter in the keyword /
# forbidden word is interpreted as a pattern rather than matched literally.
#
# "upstream"  = what the shipped checker does (raw string as a regex).
# "intended"  = the plainly-intended literal reading (re.escape the string).
# A hazard is any input where upstream disagrees with intended, or crashes.

import re

# Characters that change a string's meaning when read as a regex instead of a
# literal. If a keyword / forbidden word contains none of these, upstream and
# intended behave identically and there is no hazard.
REGEX_METACHARS = frozenset(".^$*+?{}[]\\|()")


def has_metachar(s):
    return any(c in REGEX_METACHARS for c in s)


# --- keywords:frequency ------------------------------------------------------

def _kf_pass(actual, frequency, relation):
    if relation == "less than":
        return actual < frequency
    if relation == "at least":
        return actual >= frequency
    raise ValueError("unknown relation: %r" % (relation,))


def kf_upstream(keyword, value, frequency, relation):
    """Verdict of the shipped checker: 'PASS', 'FAIL', or 'CRASH'."""
    try:
        actual = len(re.findall(keyword, value, flags=re.IGNORECASE))
    except re.error:
        return "CRASH"
    return "PASS" if _kf_pass(actual, frequency, relation) else "FAIL"


def kf_intended(keyword, value, frequency, relation):
    """Verdict under the plainly-intended literal reading of the keyword."""
    actual = len(re.findall(re.escape(keyword), value, flags=re.IGNORECASE))
    return "PASS" if _kf_pass(actual, frequency, relation) else "FAIL"


# --- keywords:forbidden_words ------------------------------------------------

def fw_upstream(word, value):
    """Verdict of the shipped checker for a single forbidden word."""
    try:
        found = re.search(r"\b" + word + r"\b", value, flags=re.IGNORECASE)
    except re.error:
        return "CRASH"
    # No forbidden word found -> instruction followed -> PASS.
    return "FAIL" if found else "PASS"


def fw_intended(word, value):
    """Verdict under the plainly-intended literal reading of the word."""
    found = re.search(r"\b" + re.escape(word) + r"\b", value, flags=re.IGNORECASE)
    return "FAIL" if found else "PASS"


def verdicts(case):
    """Return (upstream, intended) verdicts for a case dict."""
    if case["checker"] == "keyword_frequency":
        up = kf_upstream(case["keyword"], case["value"],
                         case["frequency"], case["relation"])
        intl = kf_intended(case["keyword"], case["value"],
                           case["frequency"], case["relation"])
    elif case["checker"] == "forbidden_words":
        up = fw_upstream(case["word"], case["value"])
        intl = fw_intended(case["word"], case["value"])
    else:
        raise ValueError("unknown checker: %r" % (case["checker"],))
    return up, intl
