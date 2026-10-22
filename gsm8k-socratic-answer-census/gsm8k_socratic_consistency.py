# gsm8k_socratic_consistency.py -- census of FINAL-ANSWER agreement between GSM8K's
# "main" and "socratic" answer files for the same questions.
#
# GSM8K ships each problem twice: once in main (train.jsonl / test.jsonl) and once in
# socratic (train_socratic.jsonl / test_socratic.jsonl). The socratic answer interleaves
# self-asked sub-questions before each reasoning step, but it is the SAME problem and uses
# the same `#### <final answer>` convention. The two files should therefore agree on the
# final answer for every shared question. This census matches rows by exact question text
# and reports where they do not agree (and where a question is present in only one file).
#
# Authored by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.
# The GSM8K corpus keeps its own licence (Cobbe et al. 2021, openai/grade-school-math, MIT).


def final_answer(answer_text):
    """Return the normalized final answer taken from AFTER the last '####' marker:
    strip surrounding whitespace, drop thousands commas, and drop a leading '$'.
    Returns None if the text has no '####' marker (the only near-normalization rule)."""
    if not isinstance(answer_text, str) or "####" not in answer_text:
        return None
    tail = answer_text.rsplit("####", 1)[1]
    return tail.strip().replace(",", "").lstrip("$").strip()


def _build(rows, question_key, answer_key):
    """Return (raw_valid_count, {question -> final_answer}). A row is valid iff its
    question and answer are both strings. First answer wins on a duplicate question."""
    raw = 0
    mapping = {}
    for r in rows:
        q = r.get(question_key)
        a = r.get(answer_key)
        if not (isinstance(q, str) and isinstance(a, str)):
            continue
        raw += 1
        mapping.setdefault(q, final_answer(a))
    return raw, mapping


def census(main_rows, socratic_rows, question_key="question", answer_key="answer",
           max_examples=50):
    """Census of final-answer agreement between a main file and its socratic twin."""
    main_raw, main_map = _build(main_rows, question_key, answer_key)
    soc_raw, soc_map = _build(socratic_rows, question_key, answer_key)

    in_both = main_map.keys() & soc_map.keys()
    only_main = main_map.keys() - soc_map.keys()
    only_soc = soc_map.keys() - main_map.keys()

    agree = 0
    disagree = 0
    disagree_examples = []
    for q in sorted(in_both):
        if main_map[q] == soc_map[q]:
            agree += 1
        else:
            disagree += 1
            if len(disagree_examples) < max_examples:
                disagree_examples.append({
                    "question": q,
                    "main_final": main_map[q],
                    "socratic_final": soc_map[q],
                })

    return {
        "main_rows_valid": main_raw,
        "socratic_rows_valid": soc_raw,
        "main_distinct_questions": len(main_map),
        "socratic_distinct_questions": len(soc_map),
        "questions_in_both": len(in_both),
        "questions_only_in_main": len(only_main),
        "questions_only_in_socratic": len(only_soc),
        "final_answer_agree": agree,
        "final_answer_disagree": disagree,
        "disagree_examples": disagree_examples,
    }


def public_summary(result):
    """Integer-only subset compared against the pre-registered TARGET."""
    return {
        "main_rows_valid": result["main_rows_valid"],
        "socratic_rows_valid": result["socratic_rows_valid"],
        "main_distinct_questions": result["main_distinct_questions"],
        "socratic_distinct_questions": result["socratic_distinct_questions"],
        "questions_in_both": result["questions_in_both"],
        "questions_only_in_main": result["questions_only_in_main"],
        "questions_only_in_socratic": result["questions_only_in_socratic"],
        "final_answer_agree": result["final_answer_agree"],
        "final_answer_disagree": result["final_answer_disagree"],
    }
