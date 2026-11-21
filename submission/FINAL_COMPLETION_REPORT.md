# Final completion report (written at the time of the first commit)

## Verified in this version (v2.1)

| Project | Tests | Full-pack result (run locally on Kuku's confidential pack; outputs not in this repo) |
|---|---|---|
| Problem 1: Promo Finder | 48/48 pass | 83 ranked promos; identical across separate processes; this repo's code reproduces the private package's outputs byte-for-byte |
| Problem 2: Nyaya Sahayak | 18/18 pass (28/28 scripted conversations) | Transcripts in `problem-2-nyaya-sahayak/outputs/transcripts/` (invented cases, not confidential) |
| Problem 3: Continuity Checker | 15/15 pass; seeded evaluation 100/100 (seed 7) | 40 findings; this repo's code reproduces the private package's findings exactly |

## What was fixed after the internal audit

- **Problem 1:**
  - per-show gate calibration (scripts without acting directions: 41 promos / 23 empty episodes → 75 / 6);
  - premise slots in the first wave;
  - relationship-reveal cues;
  - readable rationales.
- **Problem 2:** 12 red-team inputs (the first build failed 9 and half-handled 1) are now handled and kept as regression cases: monthly rate × months, landlord-side users, harassment disclosures, negation, past-tense hearings, partial refunds, cheque bounce, insurance, government jobs, "50k", fraud.
- **Problem 3:** the overstated headline was corrected ("11 spellings" → "10 confirmed + 1 uncertain"; recall 7/10). The seeded evaluation now detects names from the show instead of hard-coding them.
- **All:** verification done by the AI is no longer written in the candidate's voice.

## Preparing this public repository

- Every file was scanned against the confidential pack: any 6-word overlap, character or place names, or the show title. Flagged code comments and tests were rewritten with invented names.
- Docs that quote the pack were moved to the private package only.
- Behaviour was re-verified after sanitising (identical outputs, all tests pass).

## Still open (honest)

- **No real LLM** has been run in any project. The model paths are tested only against mock servers.
- **Problem 1:** keyword dependence; the best premise cut is not chosen; no editor labels yet.
- **Problem 2:** the legal knowledge base is not lawyer-reviewed (mostly secondary sources).
- **Problem 3:** distant spelling variants are missed.
- **Candidate actions:**
  - re-check the picks and findings personally;
  - fill in name, roll number and links in the private PDFs;
  - submit one problem.
