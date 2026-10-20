# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
#
# Faithful reproduction of IFEval's word counter and the length_constraints:
# number_words verdict, plus a simple whitespace-split alternative, so the two
# can be compared on real model outputs.
#
# IFEval's instructions_util.count_words (google-research/google-research,
# instruction_following_eval/instructions_util.py) builds an NLTK tokenizer:
#
#     tokenizer = nltk.tokenize.RegexpTokenizer(r"\w+")
#     num_words = len(tokenizer.tokenize(text))
#
# For str input that tokenizer is exactly re.findall(r"\w+", text) under
# Python's default Unicode \w (RegexpTokenizer uses gaps=False and the pattern
# cannot match empty, so discard_empty is a no-op; its re.MULTILINE/re.DOTALL
# flags do not affect \w+). We therefore reproduce it with the standard library
# and avoid the nltk dependency. This equivalence is checked in the tests.
#
# The length_constraints:number_words checker (class NumberOfWords in
# instructions.py) then does:
#     num_words < self._num_words      for relation "less than"
#     num_words >= self._num_words     for relation "at least"

import re

# IFEval's word tokenizer, reproduced: runs of word characters.
_WORD_RE = re.compile(r"\w+")

# The two relations IFEval's number_words instruction supports.
RELATIONS = ("less than", "at least")


def count_words_ifeval(text):
    """Word count exactly as IFEval computes it: len(RegexpTokenizer(r'\\w+'))."""
    return len(_WORD_RE.findall(text))


def count_words_whitespace(text):
    """A simple, widely-used alternative: split on runs of whitespace."""
    return len(text.split())


def number_words_pass(count, num_words, relation):
    """IFEval's NumberOfWords verdict for a given word count."""
    if relation == "less than":
        return count < num_words
    if relation == "at least":
        return count >= num_words
    raise ValueError("unknown relation: %r" % (relation,))


def evaluate_case(case):
    """Return (count_ifeval, count_ws, verdict_ifeval, verdict_ws, flip)."""
    c_if = count_words_ifeval(case["value"])
    c_ws = count_words_whitespace(case["value"])
    v_if = number_words_pass(c_if, case["num_words"], case["relation"])
    v_ws = number_words_pass(c_ws, case["num_words"], case["relation"])
    return c_if, c_ws, v_if, v_ws, (v_if != v_ws)
