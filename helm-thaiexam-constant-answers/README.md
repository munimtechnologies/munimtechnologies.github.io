# Audit 111: HELM ThaiExam v1.2.0, ONET cells that equal a constant answer (a desk check)

Status: **desk check, 2026-11-12.** Read by hand from HELM's public archive, not pre-registered and not re-run in a
sealed container. Every one of the 42 published ONET cells is reproduced from the records read.

Part of [eval-reliability-audits](../eval-reliability-audits/) by MV2 of Munim, Inc. Made with AI agents working in
MV2's name.

## What was checked

HELM's ThaiExam leaderboard (release `v1.2.0`, 42 models; files under
`gs://crfm-helm-public/thaiexam/benchmark_output/`) scores five Thai exams (ONET, IC, TGAT, TPAT-1, A-Level) with
`multiple_choice_joint`: the prompt holds five in-context examples, then the question with options `A` to `E` (`A` to
`D` in IC), the model may write **one token** (`max_tokens` 1), and the cell is strict `exact_match` on the letter.
HELM picks the five examples once per exam, so every question and every model sees the same five.

Questions: (1) how far is each ONET cell above what one letter repeated 162 times would score; (2) how many answers
are not a letter at all because the one-token limit cut them off; (3) which letters the fixed examples show
(HELM issue [#2224](https://github.com/stanford-crfm/helm/issues/2224), open since 2024-01-11, says the example sampler
balances on the answer's text, not its letter, so some letters may never be shown; it gives no counts).

## Method

- ONET gold letters: all 162 test instances read from `instances.json` (one run; the scenario is the same in all).
- ONET predictions: `display_predictions.json` of all 42 runs (34 in `runs/v1.0.0`, 6 in `runs/v1.1.0`, 2 in
  `runs/v1.2.0`, as listed in `releases/v1.2.0/runs_to_run_suites.json`): count of each predicted letter, of non-letter
  outputs, and of `exact_match` credits per letter.
- In-context examples: the first request of each exam (Llama 3 Instruct 8B; ONET also Llama 3.1 Instruct Turbo 8B,
  same five examples in the same order).
- Llama 3 Instruct (8B), all five exams; and three other runs seen on the way (marked post hoc).
- Completeness check: in every run, credits = published cell x 162, and the letters plus non-letter outputs add up
  to 162. All 42 hold. Per-model counts are in [results.json](results.json).

## Results

**Gold letters.** ONET's 162 golds are A 31, B 34, C 36, D 30, E 30, and one question (`id144`) has two references
tagged correct (A and E). So answering the same letter every time scores 32 (A), 34 (B), **36 (C, the best, 0.222)**,
30 (D) or **31 (E, 0.191)**. Uniform guessing gives about 0.2.

**The five ONET examples are answered E, E, D, D, D.** A, B and C are never shown. The other exams show more letters:
TGAT E B D A C (all five), A-Level D B A D E, TPAT-1 D B A D C, IC A C D D A (B never shown).

**The bottom four ONET cells are what a constant answer scores.**

| Model (HELM name) | ONET EM | Credits /162 | Most common answer | Non-letter outputs |
| --- | --- | --- | --- | --- |
| SEA-LION 7B Instruct | 0.185 | 30 | E, 86 times | 0 |
| Llama 3 Instruct (8B) | 0.191 | 31 | **E, 162 times** | 0 |
| Mixtral Instruct (8x7B) | 0.210 | 34 | **E, 158 times** | 0 |
| Llama 3.1 Instruct Turbo (8B) | 0.216 | 35 | **E, 128 times** | 16 |
| *next lowest:* Mixtral Instruct (8x22B) | 0.253 | 41 | E, 79 times | **30** |

- **Llama 3 Instruct (8B) answered E on all 162 questions**, so its published ONET cell (0.191) is exactly the
  always-E score. Mixtral 8x7B answered E 158 times (its other 4 answers gave 3 credits). Llama 3.1 8B answered E 128
  times (27 right).
- All four sit at or below always-C (36), and two (SEA-LION 7B, Llama 3 8B) are below uniform guessing. The next
  lowest cell (Mixtral 8x22B, 41) is above every constant letter. Among these four, the published order reflects
  which letter each model repeats, not what it knows.
- No other model repeats one letter more than 82 times (Typhoon 7B, E 82; Mixtral 8x22B, E 79; then
  SambaLingo-Thai-Chat, D 68).
- The E excess is concentrated: over all 6,804 ONET answers E is 25.8% (1,755) against 19.1% of golds (31 of 162),
  but without the three near-constant models it is 20.7% (1,307 of 6,318).

**Llama 3 Instruct (8B) answers the last option in every exam.** E on 451 of 470 questions in the four exams whose
options run to E (TGAT mixes four- and five-option questions, so a few of its E answers may have no option E), and D
on 90 of 95 in IC, whose questions have only A to D. Its five published cells (ONET 31/162,
A-Level 28/127, TGAT 12/65, IC 20/95, TPAT-1 21/116) reproduce its ThaiExam macro score of 0.1976. So its whole
ThaiExam row measures a fixed position, not Thai knowledge. Because it also answers D in IC, where the examples are
A C D D A, this is a last-option habit, not copying the ONET examples' letters.

**One token cuts off 49 answers (0.72% of 6,804), 30 of them Mixtral 8x22B's.** Mixtral Instruct (8x22B) began 28
answers with `Answer` and 2 with `The` (18.5% of its ONET answers). Llama 3.1 Instruct Turbo (8B) wrote 16 Thai
first tokens (13 `ข`, 3 `คำ`), Llama 3.1 Instruct Turbo (70B) 2, OpenThaiGPT 7B 1. All score 0, and the letter that
would have followed is unknown. The `ข` outputs do not behave like the Thai label for option 2 (B): only 2 of the
13 questions answered `ข` have the gold B (`id44`, `id120`), about what chance gives, so `ข` is most likely the start
of `ข้อ` ("choice"), cut after one token. If Mixtral 8x22B had
answered the 30 cut-off questions as well as it did the other 132 (41 of 132), it would gain about 9 credits
(about 0.31); this is an estimate, not a measurement.

**Seen on the way (post hoc, three runs):** Mixtral 8x7B answered E on 12 TGAT questions that have only four options
(no mapped option, scored 0). It answered A on 63 of 95 IC questions. Llama 3.1 8B answered A on 61 of 95 IC
questions. So the collapse onto one letter is not E-specific for these two models.

## What this does and does not show

- No published number is mis-scored: every credit checked is a correct letter. The finding is that four of 42 ONET
  cells (and Llama 3 8B's whole ThaiExam row) do not separate the model from a constant answer. For those models the
  leaderboard ranks letter habits.
- The five ONET examples show only D and E (issue #2224's mechanism, measured here), but the data do not show that
  they cause the E answers: Llama 3 8B answers the last option even where the examples show three letters.

## Suggestions (for HELM and for readers of the ThaiExam table)

1. Publish a constant-answer baseline beside each multiple-choice column (here: ONET 0.222 for always-C) and flag runs
   where one letter is 90% or more of the answers (two ONET runs, Llama 3 8B and Mixtral 8x7B).
2. Balance the in-context examples by answer letter (#2224), so that an exam's examples show every letter.
3. Allow a few more output tokens and read the first letter (as most MMLU-style harnesses do), or report
   non-letter outputs as their own column; HELM closed the related one-token issue
   [#2467](https://github.com/stanford-crfm/helm/issues/2467) as not planned on 2026-02-03.

## Limits

- Read by hand from the archive through a web reader, one pass per file; not re-run in a container and not
  pre-registered. The 42-of-42 cell reproduction and the per-run totals of 162 are the main check that the reading
  is complete. The gold letters were cross-checked against two runs: the always-E run scores exactly 31 (the 30 E
  golds plus `id144`), and Llama 3.1 8B's seven D answers score as the golds say (6 right, `id158` wrong).
- Only ONET was read for all 42 models; the other four exams only for Llama 3 8B and, post hoc, two IC and one TGAT
  run. The `id144` double gold was read once and agrees with the counts.
- Why a model repeats a letter (position habit, in-context examples or the chat template) is not tested.

## Prior art

- HELM issue #2224 (example sampling balances by reference text, not letter) and #2467 (one-token answers are cut
  off; closed as not planned). Neither gives counts for any leaderboard, and neither mentions ThaiExam.
- Few-shot label and position biases are well known in general (for example "majority label" and "recency" bias in
  in-context learning). We found no measurement of them on HELM's ThaiExam leaderboard, and no ThaiExam issue on
  HELM's tracker besides a schema description fix (#3972) and model additions.

## Licence

Text and numbers: CC BY 4.0. Authored by AI agents working in MV2's name (Munim, Inc.).
