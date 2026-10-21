# Pre-registered synthetic corpus for the ifeval-title-hazards audit.
#
# Each case pins the TitleChecker verdict (does <<[^\n]+>> match a non-empty
# title?) against the intended semantic (is a deliberate title present?). Every
# verdict was hand-traced against title_checker.py BEFORE any real data was
# touched; the sealed job re-derives the aggregate and asserts it equals TARGET.
#
# Labelled corpus by AI agents working in MV2's name (Munim, Inc.). CC BY 4.0.

# id, value, intended_is_title, expected_verdict, note
CASES = [
    ("T1-true-title", "<<A Poem of Joy>>\nHere is my poem about the morning.",
     True, "match",
     "A genuine double-angle-bracket title; checker accepts -> correct."),
    ("T2-no-title", "Here is my answer, written in plain prose with no title marker.",
     False, "correct_neg",
     "No << marker anywhere; checker rejects -> correct negative."),
    ("T3-shift-operators", "To build the mask, compute result = a << 2 >> 1 inside the loop.",
     False, "false_pass",
     "Left-shift then right-shift on one line: <<...>> matches ' 2 ' -> checker "
     "credits a title that was never written (false pass)."),
    ("T4-heredoc-redirect", "Run this: cat <<EOF >> output.txt to append the block.",
     False, "false_pass",
     "Shell heredoc '<<EOF' and append-redirect '>>' on one line match "
     "'<<EOF >>' -> false pass."),
    ("T5-cpp-stream", "In C++ you can write std::cout << value >> rest for the demo.",
     False, "false_pass",
     "C++ stream insertion/extraction '<< value >>' matches -> false pass."),
]

TARGET = {
    "n_cases": 5,
    "n_checker_true": 4,
    "n_flips": 3,
    "n_false_pass": 3,
    "n_false_fail": 0,
    "all_reproduced": True,
}
