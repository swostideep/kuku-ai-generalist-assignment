# AI usage disclosure

| Tool | What it contributed | What was checked, and by whom |
|---|---|---|
| An earlier AI-assisted prototype, v1 (folder `codex_promo_finder`; the tool used was not recorded) | First prototype: parser, window scoring, optional model reranker, two-page PDF | Audited in [AUDIT_v1.md](AUDIT_v1.md): 11 defects found |
| Claude Code (Claude Opus 5.5) for v2 | Independent audit of v1; problem-choice matrix; v2 code (parser, signals, gates, selection, model client, reports); 44 tests; evaluation script; draft docs and PDF; a first-pass script review of the top-20 picks | Claude ran everything on the full pack, read the top-20 transcripts and generated the doc figures from `outputs/logs/`. **None of this has been repeated by the candidate yet** (see the checklist below) |

## Where the AI got it wrong: one concrete case

**What happened.** The AI-written v2 code was supposed to be deterministic. The first time the full pack was re-run in a *separate process*, the ranking and scores matched. But 29 text fields differed: the emotion word quoted in "why it works" switched, for example from "accusing" to "outraged".

**How it was found.** A determinism check that compares two full runs in separate processes. The AI's own unit test (E01) ran both runs in one process, so it passed and hid the bug.

**Cause.** The code looked up words from a performance direction ("Outraged, Accusing") through a Python `set`. Set order changes between processes (hash randomisation).

**Fix.**
- Iterate in written order.
- Add test E01b, which runs two processes with different `PYTHONHASHSEED` values. The reproduce script now checks this on every run.

**Lesson.** "Deterministic" claims need a test that varies the process, not just repeats the call.

## Other AI mistakes caught in this project (all fixed, see [TEST_REPORT.md](TEST_REPORT.md))

- **Lexicon matched whole words only**, so "crash" did not match "crashes". A strong fire-and-collapsing-beam scene was silently rejected. Found by comparing v1's good picks with v2's output.
- **Lead-character detection** treated "LADY MARA" and "MARA" as different people.
- **Two wrong test expectations:** a fixture too short for the duplicate check, and an "adversarial" example that was actually caught by a different rule.
- **Tuning on the same show the tool is evaluated on** is a risk the AI kept drifting towards: each fix of a visible bad pick nudged the rules towards this show. I stopped tuning once the remaining errors were genuine limits of rules, not bugs. The interview run on a new show is the real test.

## Data handling

- The confidential input pack was processed locally. It was read by the AI coding assistant as the brief allows, and not uploaded to any other service.
- No model API was called on the scripts. The model path was tested only against a local mock server.

## Candidate verification checklist

Status as of 2026-11-22: **1 of 4 done.** Each item is ticked only when actually done.

- [ ] Run `./reproduce.sh` yourself and confirm the log numbers match the PDF.
- [x] Open at least 10 picks and check each against the screenplay. Done for the top 10 on 2026-11-22 (verdicts drafted with an AI assistant and adopted): 5 accept, 5 maybe, 0 reject; recorded in `MY_REVIEW_WORKSHEET.md` and `my_top10_review.csv`, so the raw outputs stay unedited.
- [ ] Read `promo_finder/candidates.py` (`is_clean_cut`, `score_window`, `calibrate_gates`) until you can explain them without notes.
- [ ] Change one thing yourself (e.g. a gate or a lexicon word), re-run, and explain the effect.
