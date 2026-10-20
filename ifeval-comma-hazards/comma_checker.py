# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
#
# Faithful reproduction of Google's IFEval punctuation:no_comma checker
# (CommaChecker in instruction_following_eval/instructions.py), plus the
# plainly-intended reading (detect ANY Unicode comma, not only ASCII U+002C).
#
# Shipped checker (verbatim mechanism):
#     return not re.search(r"\,", value)
# i.e. the response passes "no_comma" iff it contains no ASCII comma U+002C.
#
# The intended reading treats a character as a comma iff its Unicode name
# contains the word "COMMA" (e.g. FULLWIDTH COMMA U+FF0C, IDEOGRAPHIC COMMA
# U+3001, ARABIC COMMA U+060C, ARMENIAN COMMA U+055D). This is a crisp,
# reproducible definition using only the standard library (unicodedata).

import re
import unicodedata


def ifeval_no_comma(value: str) -> bool:
    """Reproduces IFEval CommaChecker: True iff no ASCII comma is present."""
    return not re.search(r"\,", value)


def comma_chars(value: str):
    """Return the list of characters in value whose Unicode name contains
    'COMMA' (the principled 'any comma' set)."""
    out = []
    for ch in value:
        name = unicodedata.name(ch, "")
        if "COMMA" in name:
            out.append(ch)
    return out


def has_any_comma(value: str) -> bool:
    """True iff value contains any character named '... COMMA ...'."""
    return len(comma_chars(value)) > 0


def intended_no_comma(value: str) -> bool:
    """Plainly-intended reading: True iff the text contains no comma of any
    script (ASCII or otherwise)."""
    return not has_any_comma(value)


def nonascii_comma_chars(value: str):
    """Comma characters other than ASCII U+002C."""
    return [c for c in comma_chars(value) if c != ","]


def evaluate_case(case):
    """Return (shipped_pass, intended_pass, flip) for a hand-built case.

    The case 'text' is given as a list of Unicode code points so the file is
    pure ASCII and encoding-independent."""
    text = "".join(chr(cp) for cp in case["text_codepoints"])
    shipped = ifeval_no_comma(text)
    intended = intended_no_comma(text)
    flip = shipped != intended
    return shipped, intended, flip
