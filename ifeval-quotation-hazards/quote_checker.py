# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
#
# Faithful reproduction of Google's IFEval startend:quotation checker
# (QuotationChecker in instruction_following_eval/instructions.py), plus the
# plainly-intended reading (accept ANY double quotation mark, not only ASCII
# U+0022).
#
# Shipped checker (verbatim mechanism):
#     value = value.strip()
#     return len(value) > 1 and value[0] == '"' and value[-1] == '"'
# i.e. the response "is wrapped in double quotation marks" iff, after stripping,
# its first and last characters are both the ASCII QUOTATION MARK U+0022.
#
# The intended reading treats a character as a double quotation mark iff its
# Unicode name contains "QUOTATION MARK" and the mark is a DOUBLE one (its name
# contains "DOUBLE", or it is the ASCII U+0022 whose name is simply
# "QUOTATION MARK"), and is NOT a SINGLE quotation mark. That covers the curly
# typographic pair LEFT/RIGHT DOUBLE QUOTATION MARK (U+201C/U+201D), the German
# low-9 pair (U+201E), the double angle guillemets (U+00AB/U+00BB) and the ASCII
# quote, while excluding single quotes (U+2018/U+2019) and the apostrophe. This
# is a crisp, reproducible definition using only the standard library.

import unicodedata


def is_double_quote(ch: str) -> bool:
    """True iff ch is a double quotation mark of any script."""
    name = unicodedata.name(ch, "")
    if "QUOTATION MARK" not in name:
        return False
    if "SINGLE" in name:
        return False
    return ("DOUBLE" in name) or (ch == '"')


def shipped_quotation(value: str) -> bool:
    """Reproduces IFEval QuotationChecker: ASCII U+0022 at both ends."""
    value = value.strip()
    return len(value) > 1 and value[0] == '"' and value[-1] == '"'


def intended_quotation(value: str) -> bool:
    """Plainly-intended reading: wrapped in a double quotation mark of any
    script at both ends."""
    value = value.strip()
    return len(value) > 1 and is_double_quote(value[0]) and is_double_quote(value[-1])


def boundary_chars(value: str):
    """Return (first, last) characters of the stripped value, or (None, None)."""
    v = value.strip()
    if len(v) < 1:
        return None, None
    return v[0], v[-1]


def nonascii_double_quote_boundaries(value: str):
    """Boundary characters that are double quotation marks but not the ASCII
    U+0022 (the characters the shipped checker cannot see)."""
    first, last = boundary_chars(value)
    out = []
    for ch in (first, last):
        if ch is not None and is_double_quote(ch) and ch != '"':
            out.append(ch)
    return out


def evaluate_case(case):
    """Return (shipped_pass, intended_pass, flip) for a hand-built case.

    The case text is given as a list of Unicode code points so the file is pure
    ASCII and encoding-independent."""
    text = "".join(chr(cp) for cp in case["text_codepoints"])
    shipped = shipped_quotation(text)
    intended = intended_quotation(text)
    flip = shipped != intended
    return shipped, intended, flip
