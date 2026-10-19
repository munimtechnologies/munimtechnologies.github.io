# Do math datasets' own worked solutions add up? GSM8K vs MathQA vs AQuA-RAT

One exact-arithmetic method, three widely used math word-problem datasets, three
different annotation styles, and predictions locked before two of the three numbers
existed, then graded as written, including the misses.

By MV2 of Munim, Inc. The research, code and this write-up were made by AI agents
working in his name; the row-by-row spot checks below were also done by those agents,
not by an independent human reviewer. Code Apache-2.0; data and text CC BY 4.0.
Contact: mv2@munimtech.com.

## The question

Each dataset ships a worked annotation next to its answer. We ask one mechanical,
label-free question of each: **does the annotation's own arithmetic hold up?** This
is not "is the answer right". It only asks whether the written computation agrees
with itself (or, for MathQA, with the option it is labelled as producing).

| dataset | annotation style | what is checked | unit counted |
|---|---|---|---|
| GSM8K (Cobbe et al. 2021) | calculator tags `<<expr=result>>` | does `expr` evaluate to `result`? | tag |
| MathQA (Amini et al. 2019) | formal `annotated_formula`, literal numbers, e.g. `power(5,4)` | does the formula evaluate to the labelled correct option? | problem |
| AQuA-RAT (Ling et al. 2017) | free-text human `rationale` with prose equations | inside one written `LHS = RHS`, does a compound LHS equal the stated number? | written step |

All three audits use exact `Fraction` arithmetic (never `eval`, never `float` on a huge
rational), cap the size of any exact value so a runaway power tower is reported as
unevaluable instead of built, and set aside constructs they cannot read rather than
guessing.

## Results

| dataset | measure | rate | count |
|---|---|---|---|
| GSM8K | tag arithmetic mismatch | **0.00%** | 0 of 27,998 tags (3 tags unparseable) |
| AQuA-RAT | written steps off by more than 5% | **6.88%** | 3,314 of 48,159 audited steps |
| MathQA | formula vs labelled option, more than 5% apart | **27.90%** | 9,081 of 32,551 evaluable problems |
| MathQA | literal-arithmetic-only formulas, any difference | **34.45%** | 3,246 of 9,422 |

The ordering GSM8K < AQuA-RAT < MathQA holds on every comparator.

These are three different units (a tag, a written step, a whole program against a
multiple-choice option), so read the table as a comparison of annotation *styles*, not
as one scale. MathQA's check is also the only one that involves the label, so part of
its rate is option rounding (the exact rate is 41.10% on the broad set, 35.75% at 0.1%,
32.36% at 1%, 27.90% at 5%).

Other numbers. GSM8K: 8,792 problems; for 94.57% of problems with tags, the last tag's
result equals the final `####` answer (the other 5.4% are a separate phenomenon, not
arithmetic errors). MathQA: 37,297 problems; 2,313 formulas unevaluable, 2,433 options
unparseable. AQuA-RAT: 97,975 records; 32,328 contain at least one audited step; set
aside: 5,178 percent steps, 3,306 precedence-ambiguous steps, 9,527 unevaluable.
Per-split rates agree (AQuA exact-step rate: train 89.17%, dev 89.38%, test 92.31%;
MathQA 5% rate: train 27.60%, validation 28.73%, test 29.57%).

## The pre-registered predictions, graded honestly

The predictions were filed on 2026-10-19 (UTC) before any MathQA or AQuA-RAT number
existed (`prereg.md`, unchanged here). What happened next matters for how much weight
each pass carries:

- **MathQA:** the first two job versions crashed (a float overflow, then a timeout on a
  power tower) without producing numbers. Version 4 added a size cap and produced the
  first and only MathQA numbers. Those are blind.
- **AQuA-RAT:** version 3 produced the first numbers, and they **missed two
  predictions**: exact-step rate 84.89% (P3 wanted at least 85%) and flagged-step rate
  11.11% (P4 wanted 0.3% to 8%). A row-by-row check of the first ~14 flagged steps found
  most were extraction artifacts: ratio fragments (`1/7:1/7:1/14 = 2:2:1` read as
  `1/14 = 2`), stripped square-root signs, the letter `x` used as "times", and
  precedence-ambiguous flattening. Version 4 removes those four classes and was then
  re-run. **The version-4 AQuA numbers were therefore produced after we had seen
  version 3's**, and the fix was aimed at documented artifacts, not at the band. Treat
  the P3/P4 passes below as post-revision, not blind.

| prediction | rule | first result | final result | grade |
|---|---|---|---|---|
| P1 MathQA literal-only exact mismatch | 3% to 20% | 34.45% (v4, blind) | 34.45% | **miss** (too high; direction right) |
| P2 MathQA 5% rate | 20% to 40% (brackets Calc-X's ~30%) | 27.90% (v4, blind) | 27.90% | **pass** |
| P3 AQuA exact-step rate | at least 85% | 84.89% (v3) | 89.18% (v4) | **miss on v3, pass on v4 after revision** |
| P4 AQuA flagged-step rate | 0.3% to 8% | 11.11% (v3) | 6.88% (v4) | **miss on v3, pass on v4 after revision** |
| P5 ordering GSM8K < AQuA < MathQA | both inequalities | 0% < 11.11% < 27.90% | 0% < 6.88% < 27.90% | **pass on both versions** |

The headline claim, the ordering (P5), does not depend on the AQuA revision: it holds
with the contaminated v3 number too. The magnitude predictions were mixed.

## What the flagged rows actually are (spot-checked)

- **GSM8K (0%).** The tags were inserted with tooling during dataset construction, so
  internal consistency is close to expected; the audit confirms it on every tag.
- **AQuA-RAT (6.88%).** The flagged set is a mix: real arithmetic slips (`270/85 = 4.15`;
  it is 3.18), AQuA's own text corruption where a slash was lost (`1 - 24/60` stored as
  `1-2460`), prose dashes read as a minus sign (`total expense - $600 + $600 = $1200`),
  and missing-parentheses notation (`28*21/28-21 = 84`, meaning `28*21/(28-21)`). So
  6.88% is a rate of flagged steps, not a pure count of arithmetic slips; and because
  many steps are set aside, it is not a count of every error either.
- **MathQA (27.90% at 5%).** A mix of clear structural disagreement (`add(25, 20)` = 45
  against a labelled answer of 70; `225 - (70 + 144)` = 11 against 4) and rounding
  near-misses (2000/9 = 222.2 against 223). The 5% rate strips most rounding.

`mathqa/mismatches_pure.json` lists 1,000 literal-only mismatches and
`gsm8k/catalog.json` lists the 3 unparseable tags and 471 chain breaks, so anyone can
check them.

## Prior art, and what is new here

- Calc-X (Kadlcik et al. 2023, arXiv:2305.15017) reports roughly 30% loss when
  converting MathQA programs to answers, which our 27.90% matches (P2 used it as a
  cross-check). Calc-X also runs a very similar check on AQuA-RAT (regex-found
  `expression = number` equations evaluated with a calculator, tagged only when they
  match) but, as far as we found, does not report how often they fail to match.
- The MathQA paper reports 92% of annotations valid in an expert check of 500
  problems; Miao et al. (2020) and MathQA-Python (Austin et al. 2021) also report
  substantial program-answer problems by other methods. AQuA rationales are described as noisy
  qualitatively (Amini et al. 2019; Cobbe et al. 2021).
- What we did not find published: GSM8K's tag-level arithmetic consistency, AQuA-RAT's
  inline-step mismatch rate with a labelled breakdown of why steps fail, and the three
  datasets measured side by side with one exact method and predictions filed in advance.
  If you know of prior work that does this, please tell us and we will cite it.

## Reproduce

Python 3.12, standard library only. Each folder's unit tests passed in a sealed
container before its full run on 2026-10-18/19 (all steps exit 0); the files here are
the exact versions that ran.

```
# GSM8K (downloads its own data)
cd gsm8k && python -m unittest -v && python audit.py --data-dir data --out-dir out

# MathQA: put MathQA.zip from https://math-qa.github.io/data/MathQA.zip in mathqa/data/
cd mathqa && python -m unittest -v && python job.py --data-dir data --out-dir out

# AQuA-RAT: put train.json, dev.json, test.json from
# https://github.com/google-deepmind/AQuA in aqua/data/
cd aqua && python -m unittest -v && python job.py --data-dir data --out-dir out
```

Each folder's `summary.json` is the output of that run. Data: GSM8K (MIT, OpenAI),
MathQA (Apache-2.0, Amini et al.), AQuA-RAT (Apache-2.0, DeepMind); none is
redistributed here beyond short quoted rows.

## Limitations

- Self-consistency is not correctness. A consistent annotation can still solve the
  wrong problem, and an inconsistent one can still reach the right option.
- The three rates count different units; the comparison is about annotation styles.
- AQuA extraction is deliberately conservative and was revised once after seeing
  results (above). The revised rate still includes text corruption and prose-dash
  cases.
- AQuA's bucket counts and step counts differ by one step (42,951 vs 42,950 exact); this
  does not move any rate at the reported precision, and we have not traced it.
- No independent human has re-checked the spot checks.

## Sources

- Cobbe et al. 2021, Training Verifiers to Solve Math Word Problems (GSM8K), arXiv:2110.14168.
- Amini et al. 2019, MathQA, arXiv:1905.13319.
- Ling et al. 2017, Program Induction by Rationale Generation (AQuA-RAT), arXiv:1705.04146.
- Kadlcik et al. 2023, Calc-X and Calcformers, arXiv:2305.15017.
- Miao et al. 2020, A Diverse Corpus for Evaluating and Developing English Math Word Problem Solvers, arXiv:2106.15772.
- Austin et al. 2021, Program Synthesis with Large Language Models (MathQA-Python), arXiv:2108.07732.
