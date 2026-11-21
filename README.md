# Kuku AI Generalist Assignment

Three independent prototypes for Kuku's AI Generalist assignment. Each is a standalone Python 3.9+ project with **no third-party dependencies**, its own tests and its own README.

| Folder | Problem | What it does | Tests |
|---|---|---|---|
| [`problem-1-promo-finder/`](problem-1-promo-finder/) | 1: Find the Promos | Finds and ranks 20–60 s promo clips in timestamped microdrama screenplays, with cut points that never fall inside a spoken line, hard quality gates, and an optional swappable LLM reviewer. Web app + CLI | 52 |
| [`problem-2-nyaya-sahayak/`](problem-2-nyaya-sahayak/) | 2: AI Lawyer | A text/voice assistant for three everyday money disputes in India (refund, rent deposit, unpaid salary). It cites only a closed, sourced knowledge base, and a guard rejects invented law. Web app + CLI | 18 (28 scripted conversations) |
| [`problem-3-continuity-checker/`](problem-3-continuity-checker/) | 3: Own problem | QA for AI-generated scripts: name drift, speaker-label aliases, unnamed recurring characters, unspeakable line timing, timing overlaps, wrong episode references. Web app + CLI | 19 + seeded-error evaluation |

The assignment asks for **one** submission; this repository holds all three as a portfolio. See [`submission/PROJECT_OVERVIEW.md`](submission/PROJECT_OVERVIEW.md) for which one is submitted and why.

## Quick start

```bash
git clone https://github.com/swostideep/kuku-ai-generalist-assignment.git
cd kuku-ai-generalist-assignment
```

Problem 1 (needs a show folder of timestamped episode `.txt` files):

```bash
cd problem-1-promo-finder && python3 run.py --show "path/to/show_folder" && python3 -m unittest discover -s tests
```

Problem 2 (no input files needed):

```bash
cd problem-2-nyaya-sahayak && python3 app.py web
```

Then open http://localhost:8765.

Problem 3:

```bash
cd problem-3-continuity-checker && python3 run.py --show "path/to/show_folder" && python3 -m unittest discover -s tests
```

### Web apps

All three apps share one Material Design 3 interface ([`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md); before/after in [`FRONTEND_REDESIGN_REPORT.md`](FRONTEND_REDESIGN_REPORT.md)).

| App | Command (from its folder) | URL |
|---|---|---|
| Promo Finder | `python3 web.py --shows "path/to/folder_of_shows"` | http://localhost:8701 |
| Nyaya Sahayak | `python3 app.py web` | http://localhost:8765 |
| Continuity Checker | `python3 web.py --shows "path/to/folder_of_shows"` | http://localhost:8703 |

No Kuku pack? `python3 samples/make_demo_show.py` writes an invented 8-episode show to `samples/`; then pass `--shows ../samples`.

Full steps are in [`submission/RUN_INSTRUCTIONS.md`](submission/RUN_INSTRUCTIONS.md).

## Confidentiality

The screenplay input pack is Kuku's confidential material. **None of it is in this repository.** That means:
- no scripts;
- no full-pack outputs;
- no documents or PDFs that quote it.

Tests use invented, synthetic screenplays. Problem 2's sample outputs (`problem-2-nyaya-sahayak/outputs/transcripts/`) come from its own invented test cases. The full-pack outputs, solution PDFs and evaluation reports are in the private submission package shared with Kuku.

## AI usage

All three projects were built with Claude Code (Claude Opus 5.5), directed and reviewed by the candidate. Each project's docs name where the AI got things wrong and how that was caught. An internal audit (also AI-run) found further defects, which were fixed in this version (v2.1). See [`submission/FINAL_COMPLETION_REPORT.md`](submission/FINAL_COMPLETION_REPORT.md).
