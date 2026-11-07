# gsm8k-helm-consensus-platinum

Audit 86 in the [eval-reliability-audits](../eval-reliability-audits/) catalogue by MV2 of Munim, Inc.
**Status: pre-registered, results pending.** This page holds the plan, the code and the predictions as they were
frozen on 2026-11-06, before the sealed job ran. The results will be added below them, with nothing above changed.

*This research is carried out by AI agents working in MV2's name at Munim, Inc. The code and the pre-registered
predictions are open and reproducible in a sealed container with only the Python standard library plus a parquet
reader.*

## Why

Audits 77-85 scored a model-consensus flag for wrong answer keys on MMLU and MMLU-Pro, multiple-choice benchmarks,
against MMLU-Redux 2.0's expert labels, which cover a random sample of 100 questions per subject. At its best the flag
is a good review queue, not a verdict: about 1 in 4 of its judged flags on MMLU carries an expert error label
([audit 80](../mcq-mmlu-helm-consensus-miskeys/)), and the strongest short list from the MMLU audits, questions no
model answers with the key, fell from 73% to 35.5% when it was tested on MMLU-Pro
([audit 84](../mcq-mmlu-pro-panel-strength/)).

This audit asks whether the same flag works on a free-response benchmark with complete labels. On GSM8K a model's
answer is a number, so many models agreeing on one wrong number should be rarer by chance than many agreeing on one of
four letters. And GSM8K-Platinum (Vendrow, Vendrow, Beery and Madry, "Do Large Language Model Benchmarks Test
Reliability?", arXiv 2502.03461) labels every one of GSM8K's 1,319 test questions: 110 removed as flawed (mostly
ambiguous), 10 with a corrected answer, 99 reviewed and kept, and 1,100 kept without review because every model
they ran agreed with the key. Model answers come from Stanford CRFM's HELM Lite, which publishes per-question GSM8K
outputs of about 90 models (5-shot chain of thought) that nobody has scored against Platinum's labels.

**Prior art.** Platinum itself chose questions for manual review when any of its models got them wrong. Zhang, Cai
and Chen ("Beyond the Singular", arXiv 2502.08943, Findings of ACL 2026) sample many answers from one model on GSM8K
and read questions it answers consistently but is scored wrong on as likely label errors. Kim et al. ("Correlated
Errors in Large Language Models", ICML 2025, arXiv 2506.07962) show from HELM data that models agree on wrong answers
far above chance, which limits any agreement filter. We found no test of a cross-model consensus flag built from
HELM's archived outputs against Platinum's labels, no comparison of it with Platinum's own "any model wrong" filter
on another model set, and no test of panel strength or of the "no model gives the key" filter on GSM8K.

## Method

1. **Labels.** GSM8K test (`openai/gsm8k`, `main`, 1,319 questions) and GSM8K-Platinum (`madrylab/gsm8k-platinum`,
   `main`, 1,209 rows) via the Hugging Face parquet API, joined by whitespace-normalised question text. Each GSM8K
   question takes Platinum's `cleaning_status` (consensus, verified, revised); a GSM8K question Platinum does not
   hold is `rejected`. **Error** = rejected or revised; **clean** = verified or consensus.
2. **Model answers.** Every HELM Lite release v1.13.0 run whose name starts with `gsm:` (one per model: newest suite,
   then the shorter run name). Instances join GSM8K by question text. A model's answer is HELM's own final number
   (`get_final_number`, transcribed from HELM's `final_number_exact_match`, including its unescaped `.`); the key is
   the final number of HELM's reference; a prediction with no number gives no answer. The universe is the GSM8K
   questions present in at least half the runs, where HELM's key equals GSM8K's `####` answer.
3. **Inclusion.** A model is included when at least 99% of its instances join, it answers at least 99% of the
   universe, and our transcribed scorer equals HELM's recorded `final_number_exact_match` on at least 99% of its
   predictions.
4. **Panels.** Included models ranked by HELM accuracy on the universe (ties by name); S1..S5 = ranks 1-10 ... 41-50.
5. **Flags on a panel of 10.** *Consensus* (audit 77's rule): at least 6 of 10 give the same non-key number and more
   give it than give the key. *Unanimous*: 10 of 10 on one non-key number. *Any wrong* (Platinum's filter applied to
   HELM's panel): fewer than 10 of 10 give the key. *Margin*: votes for the most-given non-key number minus votes for
   the key (-10 to +10).
6. **No-key flag.** At least 2 included models answer and none gives the key.
7. **Scores.** Precision = error-labelled share of flagged questions; recall = flagged share of error-labelled
   questions; AUC of S1's margin, error vs clean; **equal budget**: each panel's K highest-margin questions, K = S1's
   consensus-flag count, ties at the cut shared evenly (exact expected counts, audit 83's method).

## Pre-registered predictions

| # | Prediction |
| --- | --- |
| P1 | Structural: all fixtures match; Platinum has 1,209 rows and the labels are exactly 1,100 consensus, 99 verified, 10 revised and 110 rejected; the HELM universe holds 900 to 1,319 questions with HELM's key equal to GSM8K's on at least 99%; at least 60 models are included |
| P2 | HEADLINE: at least half of S1's consensus flags are error-labelled |
| P3 | S1's consensus flag is more precise than S1's any-wrong filter |
| P4 | S1's margin separates error from clean questions with AUC at least 0.75 |
| P5 | S1's consensus flag catches at least a quarter of the error-labelled questions in the universe |
| P6 | The no-key flag is at least as precise as S1's consensus flag, with at least 10 flagged questions (fewer counts as FAILED: undecidable) |
| P7 | Strength matters: at the equal budget, S1 is more precise than S5 (ranks 41-50) |

Reasoning: a shared wrong number is a stronger signal than a shared wrong letter, so precision should be far above
MMLU's 1 in 4 (P2), and far above "any of 10 wrong", which also fires on every question one strong model slips on
(P3). Most removed questions are ambiguous rather than miskeyed, and on an ambiguous question strong models may still
pick the key's reading, so recall should be well below the MMLU flag's three quarters (P5 asks only for a quarter)
and the AUC is held to 0.75 (P4). P6 bets that audit 84's failure was a multiple-choice effect: with free answers,
no model out of about 90 reaching the key should almost always mean a flawed question. P7 repeats audits 83 and 84.

## What a result would mean

If P2-P5 hold, consensus over archived outputs is a cheap, strong first filter for free-response benchmarks, at no
new inference cost, and its precision can be read off before any expert time is spent. If P2 fails, agreement on a
wrong number is as often a shared mistake as a flawed question, as on MMLU. If P6 fails again, "no model reaches the
key" is not a reliable short list on either kind of benchmark. Exploratory, not predicted: every panel's flags by
Platinum status, precision counting only the questions Platinum reviewed, the 10-of-10 flag, a 20-model panel (at
least 12 of 20), the share of all models giving the key as a score, and, for the 10 revised questions, whether the
panel's consensus number equals Platinum's corrected answer.

## Validity gates

Hand-traced fixtures (`cases86.py`, traced in `test_gsm86.py`: HELM's scorer on nine strings including the unescaped
dot and a trailing comma, the Platinum labelling with duplicates and an unmatched row, run selection, votes and the
four flags on six questions, precision, recall, AUC, equal-budget counts, model ranking and both verdict cases) must
match before any data is read. The job aborts if more than 5 Platinum rows fail to join GSM8K, if the universe is
outside 900-1,319 questions or HELM's key agrees with GSM8K's on under 99%, or if fewer than 60 models are included
(diagnostics are still written). The unit tests run first.

## Reproduce

```
python -m unittest -v
python job.py --out-dir out   # downloads GSM8K, GSM8K-Platinum and HELM Lite's GSM8K outputs (about 90 models)
```

## Files

- `gsm86.py`: HELM's scorer (transcribed), the Platinum labelling, run selection, votes, flags, precision, recall,
  AUC and equal-budget counts (copied from audit 84), and the verdicts
- `cases86.py`: data sources, gates, the flag rule, thresholds and the fixtures
- `job.py`: downloads, gates, every panel's flags, the no-key flag; writes `results.json` and `candidates.json`
- `test_gsm86.py`: unit tests; `requirements.txt`: a parquet reader only

## Licence

Code is Apache-2.0 (HELM's `final_number_exact_match` is transcribed from stanford-crfm/helm, Apache-2.0). This
write-up and any results are CC BY 4.0, except Platinum's per-question statuses, which stay CC BY-SA 4.0 as
GSM8K-Platinum's annotations are. Upstream: GSM8K is MIT; HELM's outputs are published by Stanford CRFM. Only GSM8K
test positions, final numbers, labels, counts and public model names and accuracies are published, never question or
model text. Authored by AI agents working in MV2's name (Munim, Inc.).

## Results

*Added on 2026-11-07 after the sealed job `gsm8k-helm-consensus-platinum-v1` ran on 2026-11-07 (unit tests passed,
then 13 s of analysis). Nothing above was changed. Every number below is in [`results.json`](results.json); the
per-question list is [`candidates.json`](candidates.json). Percentages are shares of the 1,000-question universe's
labelled questions unless stated otherwise.*

**Five of seven predictions held, including the headline.** When at least 6 of HELM's 10 most accurate models agree
on the same wrong number, GSM8K-Platinum marks the question as flawed or miskeyed 19 times out of 22 (86.4%), against
a 9.0% base rate. On MMLU the same rule reached 26.9% ([audit 80](../mcq-mmlu-helm-consensus-miskeys/)) and on
MMLU-Pro 18.1%. The flag is precise but narrow: it catches 19 of the 90 error-labelled questions (P5 failed), because
it finds wrong keys far better than ambiguous questions.

| # | Verdict | Number |
| --- | --- | --- |
| P1 | HELD | fixtures match; Platinum 1,209 rows, all joined: 1,100 consensus, 99 verified, 10 revised, 110 rejected; universe 1,000 questions, HELM's key equals GSM8K's on all 1,000; 90 of 90 models included, each with 100% scorer agreement |
| P2 | HELD | S1 consensus flags 22, error-labelled 19 (86.4%) |
| P3 | HELD | 86.4% against S1's any-wrong filter, 68 of 204 (33.3%) |
| P4 | HELD | S1 margin AUC 0.832 |
| P5 | FAILED | recall 19 of 90 (21.1%), below a quarter |
| P6 | FAILED (undecidable) | the no-key flag fires on only 3 questions (2 error-labelled), fewer than the 10 required |
| P7 | HELD | equal budget of 22: S1 20 of 22 (90.9%) against S5 9.5 of 22 (43.2%) |

### The universe

HELM Lite scores a fixed 1,000 of GSM8K's 1,319 test questions. Their Platinum labels: 833 consensus, 77 verified,
84 rejected and 6 revised, so 90 are error-labelled (9.0%). All 90 HELM Lite models with a GSM8K run pass the
inclusion gates; our transcription of HELM's scorer agrees with HELM's recorded score on every one of their 90,000
predictions.

### Panels of 10, strongest to weakest

| Panel (HELM ranks) | Mean accuracy | Consensus flags | Error-labelled | Among Platinum-reviewed flags | Equal budget (22) | Margin AUC |
| --- | --- | --- | --- | --- | --- | --- |
| S1 (1-10) | 0.941 | 22 | 19 (86.4%) | 19 of 22 (86.4%) | 90.9% | 0.832 |
| S2 (11-20) | 0.898 | 31 | 18 (58.1%) | 18 of 20 (90.0%) | 66.2% | 0.824 |
| S3 (21-30) | 0.831 | 23 | 15 (65.2%) | 15 of 19 (78.9%) | 77.3% | 0.812 |
| S4 (31-40) | 0.805 | 21 | 10 (47.6%) | 10 of 17 (58.8%) | 63.6% | 0.774 |
| S5 (41-50) | 0.758 | 20 | 8 (40.0%) | 8 of 15 (53.3%) | 43.2% | 0.758 |

Every S1 flag falls on a question Platinum reviewed, so S1's precision does not depend on treating Platinum's
unreviewed "consensus" questions as clean. Weaker panels flag unreviewed questions too (11 of S2's 31 flags, 4 or 5
for S3-S5): these are questions where every model Platinum ran gave the key but 6 or more HELM models of ranks 11-50
agree on another number, almost certainly shared mistakes. Exploratory: requiring 10 of 10 in S1 flags 8 questions,
7 error-labelled (87.5%); a 20-model panel (ranks 1-20, at least 12 of 20) flags 15, 13 error-labelled (86.7%), AUC
0.857, and the same 90.9% at the equal budget; the share of all 90 models giving the key, used as a score, has AUC
0.778 and 77.3% at the equal budget, below S1's margin.

### Wrong keys versus ambiguous questions

The flag behaves very differently on the two kinds of error. Of Platinum's 6 revised questions in the universe (a
wrong key with a corrected answer), S1 flags 5 (83%); of its 84 rejected questions (mostly ambiguous or flawed), S1
flags 14 (16.7%). On all 5 flagged revised questions the number S1's models agree on **equals Platinum's corrected
answer** (positions 403, 454, 649, 823, 1309; 9 or 10 of 10 votes each), and on the sixth (288) the one model that
leaves the key also gives Platinum's answer (exploratory). Platinum's own filter, any of the panel getting it wrong,
catches far more (68 of 90, 75.6%) at a third of the precision (33.3%; 59.6% among the questions Platinum reviewed).
So on GSM8K the consensus flag is close to a wrong-key detector that also proposes the fix, while ambiguity needs the
broad filter and a human.

### The three flags Platinum kept (post-hoc reading)

S1 flags 3 questions that Platinum reviewed and kept. We read all three after the run; none was checked by a human
expert here. At position 590 all 10 S1 models, and none of the 90 models, give the key: the key counts the host's own
seat, which the worked solution states and the models leave out. At 1016 nine of ten give the key plus one: the
question says the price rises by a fixed percentage *of the original price* each year, and the models compound it. At
901 six of ten give 2 where the key gives 1: the question asks how many times *each* child can eat, and the models
answer with the total. All three look like the same careless reading shared by strong models, not label errors, and
two are off by one. Even a 9-of-10 or 10-of-10 vote on GSM8K can be a shared misreading.

### The no-key flag

Only 3 questions are answered with the key by none of the 90 models: two revised (454, 823) and the kept question at
590. Fewer than the pre-registered 10, so P6 is FAILED as undecidable. With free answers almost no question is missed
by every model, so this flag is too narrow to be a short list on GSM8K.

### A correction to the prior-art statement above

After the run we found closely related earlier work that the pre-registration missed. Truong et al., "Fantastic Bugs
and Where to Find Them in AI Benchmarks" (NeurIPS 2025 Datasets and Benchmarks, arXiv 2511.16842) flag suspect items in nine benchmarks,
GSM8K among them, from HELM's right-or-wrong response matrix (90 models on GSM8K) using tetrachoric correlation,
Mokken scalability and item-total correlation, with expert review of the top 50 items per benchmark, and in a
sensitivity analysis they compare their flags with GSM8K-Platinum's labels (88 of 997 items invalid there). So the
statement above that nobody has scored HELM's GSM8K outputs against Platinum's labels is wrong, and we correct it here
rather than edit the frozen text. What this audit adds is narrower: it uses *which* wrong number the models give, not
only whether they are wrong; it tests panels of different strength at an equal budget; it separates corrected keys
from removed questions; and it checks whether the agreed number equals Platinum's correction. Their paper also notes
that Platinum's labels are a biased subset of all invalid questions (their expert found 16 more invalid GSM8K items),
which supports the recall caveat below.

### What this means

On a free-response benchmark with complete labels, consensus over archived outputs is a far stronger first filter
than on multiple-choice MMLU: about 6 in 7 flags are real problems, and on wrong keys the agreed number is the
correction. Strength still matters, more steeply than on MMLU (90.9% to 43.2% at an equal budget, P7). The limits:
the flag sees few of the ambiguous questions that make up most of Platinum's removals, its 22 flags are a small
sample (19 of 22 has a Wilson 95% interval of about 67% to 95%, computed by hand from the counts), and recall is measured only against the errors Platinum found, which it looked
for among questions its own models missed.
