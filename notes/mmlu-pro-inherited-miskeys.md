# MMLU-Pro kept MMLU's expert-flagged wrong keys; model consensus points to them but cannot confirm them

MV2, Munim, Inc. (mv2@munimtech.com), 4 November 2026; updated 5 November 2026 with audit 80. This work was carried
out by AI agents working in MV2's name. Text CC BY 4.0; code Apache-2.0.

## Abstract

MMLU-Redux 2.0's experts re-annotated 5,700 MMLU questions and marked 106 as having a wrong answer key. Five
pre-registered audits (75-79) followed those questions into MMLU-Pro, the 10-option benchmark built partly from MMLU.
MMLU-Pro holds 55 of them and still uses MMLU's disputed key on 52 (audit 75). On the 46 where the experts' answer is
one of MMLU-Pro's options, all 45 published models in TIGER-AI-Lab's archives pick the experts' answer more often
than the key (audit 76). Turned around, a flag that fires when at least 6 of the 10 most accurate models agree on one
non-key option finds Redux miskeys at 5.7 times the base rate, but only 18.1% of the flagged questions the experts
judged carry an error label (audit 77). Options MMLU-Pro added explain part of that gap (audit 78), and removing
duplicate archives of the same model barely changes it (audit 79). Requiring all 10 models to agree roughly doubles
the precision. A sixth audit (80) re-ran the same flag on the original MMLU with a different harness and model set
(Stanford CRFM's HELM outputs) against all 5,700 Redux labels: it finds 80 of the 106 miskeys and reaches 26.9%
precision, most of the gain coming from virology. Model consensus is a good way to rank questions for expert review,
not a substitute for it.

## 1. Method

Every audit joins MMLU-Redux 2.0 (`edinburgh-dawg/mmlu-redux-2.0`, 57 subjects x 100 questions) to MMLU test by
question text and options, then to MMLU-Pro's 6,810 MMLU-derived questions by question text plus at least 3 of MMLU's
4 options (audit 75's rule). 5,690 of 5,700 Redux rows join MMLU, and 2,829 (49.6%) are in MMLU-Pro. Model answers
come from TIGER-AI-Lab's published per-question archives on GitHub (45 of 48 archives pass the join). Each audit
pre-registered its predictions, ran in a sealed container, and had to reproduce the previous audits' numbers before
its own predictions were scored.

## 2. The keys MMLU-Pro inherited (audit 75)

MMLU-Pro keeps MMLU's disputed key on 52 of the 55 Redux-miskeyed questions it holds (94.5%), led by college
chemistry (18) and virology (8). On 24 of the 26 corrections given as a letter or text, the experts' answer is still
one of MMLU-Pro's options, so most fixes would be a one-letter key change. The 3 keys MMLU-Pro did change (ids 2817,
8122, 8780; 2817 is in its changelog) all match the experts' answer when Redux's digit answers are read 0-based, the
only coherent reading (post-hoc). Flagged questions entered MMLU-Pro at about the rate of expert-OK ones (51.6% vs
49.6%, risk ratio 1.04, not significant).

## 3. What the models answer (audit 76)

On the 46 inherited miskeys whose experts' answer is among MMLU-Pro's options, the 45 models' 2,070 predictions pick
the experts' answer 1,041 times and MMLU-Pro's key 283 times (50.3% vs 13.7%). Every model prefers the experts'
answer, which is picked 11.8 times as often as an average other distractor and leads on 37 of the 46 questions. The
result holds on the 24 letter or text corrections alone (464 vs 127), so it does not rest on the 0-based digit
reading. The models side with the key on 9 questions, most lopsidedly on 9677 (40 vs 1) and 6639 (34 vs 3): those
expert labels are the first to re-check. Rescoring the 46 would lift every model by +0.04 to +0.23 points.

## 4. A consensus flag, and its precision (audit 77)

A question is flagged when at least 6 of the 10 most accurate archives pick the same non-key option and more of them
pick it than the key. The flag fires on 36 of 55 Redux-miskeyed questions (65.5%) and on 294 of 2,553 Redux-OK ones
(11.5%), a ratio of 5.68, and recovers 34 of audit 76's 46. But the pre-registered precision prediction failed: only
65 of the 359 flagged questions the experts judged (18.1%) carry any error label. Across MMLU-Pro the flag fires on
1,210 questions (10.1%). Requiring all 10 to agree flags 201 and raises the precision to 36.4% (exploratory). On ids
6639, 8972, 9677 and 9947 all 10 panel models pick MMLU-Pro's key over the experts' answer.

## 5. Where flags on cleared questions point (audit 78)

On flagged miskeys the consensus option is one of MMLU's own four options 36 of 36 times. On flagged Redux-OK questions
it is an option MMLU-Pro added in 185 of 290 cases (63.8%), more than the 56.7% of the panel's scattered wrong picks
but about the 64.1% share added options have among all non-key options. So added options, which can make a second
answer defensible, explain part of the gap, while 105 flags on cleared questions still point at MMLU's own
distractors. Law, predicted to stand out, did not (69 of 139 added).

## 6. Duplicate archives (audit 79)

Audit 77's ten panel slots held only six model lines: three Claude 3.5 Sonnet archives, two GPT-4o versions and two
runs labelled `arx`. Archives of one model share wrong answers more often than the median pair of different models
(64.4-70.5% vs 55.3%), but a panel with one archive per named line is barely more precise: 60 of 315 (19.0%) against
65 of 359 (18.1%). Some differently named pairs share wrong answers more than any same-name pair (up to 81.5%), so
names capture only part of the dependence. The agreement threshold matters far more: with the one-per-line panel,
precision rises from 19.0% at 6 of 10 to 34.5% at 10 of 10 (20 of 58), while recall falls from 34 to 17 of 55.

## 7. An independent replication on MMLU (audit 80)

Audit 80 applied audit 77's flag, unchanged, to the original 4-option MMLU test set, using the per-question outputs of
HELM MMLU release v1.13.0 (78 models whose answers reproduce HELM's own scores; the panel is the 10 most accurate, from
Claude 3.5 Sonnet at 87.7% to Qwen2.5 72B at 83.3%) and all 5,700 Redux labels (106 miskeys, all joined). The flag
fires on 80 of the 106 miskeys (75.5%) and on 354 of 5,285 Redux-OK questions (6.7%), a ratio of 11.3, and 130 of the
484 flagged questions the experts judged (26.9%) carry an error label, against a 6.0% base rate. At 10 of 10 the
precision is 67 of 132 (50.8%). Five of six predictions held; the structural check failed on one part, because MMLU's
test set has 58 duplicated or unkeyed questions, not the at most 42 the pre-registration allowed for.

The gain over MMLU-Pro is mostly one subject. Virology holds 33 of the 106 miskeys, 30 of them flagged, and 39 of its
42 flagged, judged questions carry an error label. Without virology the precision is 91 of 442 (20.6%), close to
MMLU-Pro's 18.1%. Outside Redux's sample, all 10 panel models pick the same non-key option on 16 more virology
questions (post-hoc; listed in audit 80), the first MMLU questions this line of work would send to an expert. Audit
81, pre-registered on 5 November 2026, asks whether flags that both panels raise on the same MMLU question, with the
same answer, are more precise than either panel alone.

## 8. Recommendations

- **MMLU-Pro maintainers:** the 52 inherited keys are listed by `question_id` in audit 75; on 46 of them the experts'
  answer is an option and the models side with the experts. Ids 9677 and 6639, where the models side with the key,
  deserve a second expert look before any change.
- **Benchmark users:** the rescoring effect is small (under a quarter of a point per model), so leaderboards barely
  move; it is still a correctness fix.
- **Anyone using model consensus to find label errors:** treat a flag as a priority for review. At 6 of 10, about 1 in
  5 flags on MMLU-Pro and about 1 in 4 on MMLU carries an expert error label; at 10 of 10, about 1 in 3 and 1 in 2.
  Precision depends heavily on how damaged a subject's key is. De-duplicating models by name buys less than a point;
  raising the threshold buys much more, at a cost in recall.

## Limits

MMLU-Redux labels are expert judgments, not verified facts, and cover 100 questions per subject. A flag on a cleared
question may be a shared model mistake, a second defensible answer, or an error the experts missed; these audits
cannot tell them apart. Audits 75-79 use one harness (TIGER-AI-Lab's 5-shot chain-of-thought archives); audit 80 uses
another (HELM's joint multiple-choice prompt), with models up to late 2024. The virology finding and the 16 unreviewed
virology questions are post-hoc readings, not tested predictions.

## Related work (checked 2026-11-05)

Gema et al., "Are We Done with MMLU?" (NAACL 2025, arXiv 2406.04127) built MMLU-Redux. Wang et al., "MMLU-Pro"
(NeurIPS 2024, arXiv 2406.01574) built MMLU-Pro and keep a changelog of key fixes. Kim et al., "Correlated Errors in
Large Language Models" (ICML 2025, arXiv 2506.07962) measure shared wrong answers across models. "Nine Judges, Two
Effective Votes" (arXiv 2605.29800) shows correlated errors limit LLM-judge panels. "Auditing MCQA Benchmarks through
Probability Landscapes" (arXiv 2608.30372) ranks MMLU items for review from model probabilities. Land and Bikel,
"Auditing LLM Benchmarks with Item Response Theory" (EMNLP 2026, arXiv 2605.30504) flag likely mislabels from 114
models' answers on seven benchmarks (not MMLU or MMLU-Pro) and score them against an LLM reviewer. "Are LLMs Better
than Reported?" (arXiv 2410.18889) re-labels data with an LLM ensemble. We found no earlier count of the Redux
miskeys MMLU-Pro inherited, or test of answer consensus against Redux's expert labels on MMLU-Pro or MMLU.

## Code and data

Repository: github.com/munimtechnologies/munimtechnologies.github.io. Folders (Apache-2.0 code, CC BY 4.0 text and
results): mcq-mmlu-pro-redux-inheritance (75), mcq-mmlu-pro-inherited-miskey-models (76),
mcq-mmlu-pro-model-consensus-miskeys (77), mcq-mmlu-pro-consensus-added-options (78),
mcq-mmlu-pro-consensus-distinct-panel (79), mcq-mmlu-helm-consensus-miskeys (80),
mcq-mmlu-cross-harness-consensus (81, pre-registered). Catalogue: eval-reliability-audits. Only ids, letters, counts
and hashes are published, never question or option text. MMLU and MMLU-Pro are MIT-licensed; MMLU-Redux 2.0 is CC BY
4.0; HELM is Apache-2.0.
