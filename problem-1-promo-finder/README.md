# Kuku Promo Finder v2

Problem 1 ("Find the Promos"): a tool that reads timestamped microdrama screenplays and proposes ranked 20 to 60 second promo clips. Each clip comes with exact cut points, its hook, its cliffhanger, a one-line reason, and the script evidence behind it.

v2 is an audited rebuild of my first version (`codex_promo_finder`). It keeps v1's core idea: deterministic timestamps, an explainable score, and an optional model. It fixes defects found in the audit: cuts inside spoken lines, near-duplicate picks, template rationales, and a weighted sum that let a strong ending rescue a weak hook. The v1 audit is in the private submission package (it quotes the confidential scripts).

**Confidential:** the input pack and everything in `outputs/` contain Kuku script text. Share them only with the Kuku reviewers (private repo or restricted link), never publicly.

## v2.1 changes (after an internal audit; the full review is in the private submission package)

- **Per-show gate calibration:** gate = min(default, the show's 80th percentile). A show written without acting directions no longer collapses: on the 50 episodes with directions removed, 41 promos / 23 empty episodes became 75 / 6. This show's results are unchanged.
- **Premise slots:** the first wave always includes the best promos from the opening episodes (`--premise-slots 2`).
- **Relationship-reveal cues and readable rationales.**

> **Public repo note:** the screenplay pack, all full-pack outputs, and docs that quote it (v1 audit, quality review,
> walkthrough, interview guide, solution PDF) are **not** in this repository; they are in the private submission package.

## Run it

Requires Python 3.9 or newer. The engine uses only the standard library: no installs, no API key, no network.

```bash
python3 run.py --show "path/to/show_folder"
```

- Outputs go to `./outputs/`; use `--output <dir>` to change this.
- `--show` also accepts a single episode `.txt` file. That is the "new input in the interview" case.
- The full 50-episode pack takes about 45 to 60 s on an Apple M2 laptop and peaks at about 33 MB RAM (`outputs/logs/resource_usage.txt`).

**Web app.** Run the command below, then open http://localhost:8701. Choose a show, click "Analyse the script" (the same pipeline, with a progress bar), then search, filter and open each promo: hook, cliffhanger, timestamps, scores and screenplay lines. Results are written to `outputs/web/<show>/`.

```bash
python3 web.py --shows "path/to/folder_of_shows"
```

Optional model review (CLI only) uses any OpenAI-compatible endpoint, so changing the model is just a flag:

```bash
# local, free: Ollama
python3 run.py --show <folder> --llm-base-url http://localhost:11434/v1 --llm-model llama3.1
# hosted (Groq / OpenRouter / Kuku's gateway / Anthropic or Gemini OpenAI-compatible endpoints)
export LLM_API_KEY=...   # never hard-coded
python3 run.py --show <folder> --llm-base-url https://api.groq.com/openai/v1 --llm-model <model>
```

To regenerate every raw output, re-run the tests and redo the v1-vs-v2 evaluation in one go:

```bash
./reproduce.sh "<show folder>" "<v1 outputs/ranked_promos.json>"
```

Run the tests on their own (52 tests, stdlib `unittest`, synthetic fixtures only):

```bash
python3 -m unittest discover -s tests -v
```

Useful flags:
- `--per-episode N`: maximum picks per episode (default 2).
- `--first-wave N`: the top N ranks use at most one pick per episode (default 10).
- `--min-hook`, `--min-cliff`, `--min-standalone`: quality-gate thresholds (defaults 45, 45, 40).
- `--llm-finalists N`: finalists per episode sent to the model (default 6).
- `--no-cache`: ignore cached model replies.

## Outputs (`outputs/`)

| File | What it is |
|---|---|
| `ranked_promos.json` | The ranked picks. Each has segments (episode, start/end times, first/last block IDs), the hook and cliffhanger with block ID, speaker and performance direction, the reason, sub-scores, clarity notes, the full transcript of the clip, and its `post_wave` |
| `ranked_promos.csv` | The same list for an editor's spreadsheet, with blank `editor_verdict` and `editor_notes` columns |
| `review.html` | Self-contained review page for the editor: each pick with its script, hook line in yellow, last line before the cut in blue (local file, not published) |
| `candidate_pool.json` | The top 12 distinct windows per episode, including ones the quality gates rejected, with `rejected_reasons` (for auditing misses) |
| `run_summary.md` | Counts, gates, the episodes with no qualifying promo, top 10 |
| `parse_report.json` | Parser warnings (0 on this pack) |
| `logs/` | Run log, cross-process determinism check, test results, v1-vs-v2 evaluation |

## How it works

```
episode .txt ──► parser.py ──► candidates.py ─────────────► select.py ─────────────► report.py
                 timed blocks  legal cuts, 20-60 s windows,  per-episode NMS, recap    JSON / CSV / HTML
                 + warnings    5 sub-scores, hard gates      dedupe, posting order
                                      │
                                      └─(optional) judge.py: model rates finalists by block ID; code validates
```

1. **Parse (code).** Every `**LABEL (Direction):**` + `Start | End` cue becomes a block with a stable ID (`B17`), a kind (dialogue, action, sfx or camera), a speaker, a performance direction ("Outraged, Accusing"), and a scene. Problems are reported as warnings rather than dropped silently. Accepted variants: h:mm:ss timestamps, comma decimals, unbolded labels, stacked parentheticals, non-UTF-8 bytes.
2. **Legal cut points (code).**
   - A cut may never fall inside a spoken line, or between the two halves of a sentence split across blocks ("…the poison exists" / "…is the maid").
   - Starts and ends snap to a camera-shot boundary within 1.5 s, so cuts land on shot changes.
3. **Score every legal 20 to 60 s window (code).** 14,615 windows for this show.
   - **Hook (30%):** the strongest beat starting in the first 3 s, minus 5 points per second of delay.
   - **Cliffhanger (30%):** the last line or beat before the cut.
   - **Standalone clarity (20%):** can a stranger follow the opening.
   - **Tension arc (12%):** does tension build or deflate across the clip.
   - **Pacing (8%):** line density, dead air, length.
   - Signals come from small readable lexicons, plus the screenplay's own performance directions: the writers already label each line "Menacing" or "Tender". The script's own "cliffhanger sting" sound cues and each episode's closing line also count.
4. **Hard gates.** A window must pass three minimums: hook ≥ 45, cliffhanger ≥ 45, standalone ≥ 40. It also needs at least 3 lines of dialogue. A weighted sum alone let a great ending carry a weak opening; the gates stop that. Rejected windows stay in `candidate_pool.json` with the reason.
5. **Select.**
   - Up to 2 picks per episode, never overlapping by 30% or more.
   - Recap clips that repeat another episode's lines are dropped.
   - Ranking is by score, but the first 10 ranks hold at most one promo per episode, so the first posts test different story hooks.
6. **Optional model review.**
   - The model rates each episode's top 6 finalists for hook, cliffhanger and standalone, and says whether the tension resolves inside the clip.
   - It must cite block IDs. A cited hook must sit in the first 3 s and a cited ending near the cut, or the review is discarded.
   - The model never sees absolute timestamps and cannot create or move a cut.
   - The final score is 40% rules + 60% model. The model's one-sentence reason replaces the rule-built one.
   - Bad JSON is retried once. A failed call falls back to rules for that episode and is logged.
   - Replies are cached by a hash of prompt and model, so reruns are free and reproducible.

## What is and isn't done

- **Built and verified:** everything above, run on the full pack, with 52 passing tests (48 for the engine, 4 for the web app). Determinism is checked across processes.
- **Model path:** tested only against a local mock OpenAI-compatible server. No real model was run, because none was available in this environment and none was needed for the baseline. Real model quality is therefore **unmeasured**.
- **Not built:**
  - Multi-segment promos that join moments, as the brief allows. Every pick is one continuous segment.
  - Video, audio or performance analysis.
  - Calibration against real editor choices or ad results.

## Layout

```
run.py              CLI
web.py              web app server (stdlib); site in web/ (see ../DESIGN_SYSTEM.md)
evaluate.py         reference-free quality checks (v1 vs v2), recomputed from the screenplay
reproduce.sh        regenerate outputs + logs
promo_finder/       parser, signals, candidates, select, judge, report, pipeline
tests/              unit, adversarial and end-to-end tests with synthetic fixtures
docs/               design, test report and AI usage (the PDF, audit and reviews quote the script, so they are private)
outputs/            raw outputs from the full input pack (created when you run it; not in this public repo)
```
