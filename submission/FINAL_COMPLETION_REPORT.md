# Final completion report (public version)

**Candidate:** Swostideep Nayak. **Fresh validation:** 2026-11-21, on this repository's code. The full-pack outputs are in the private submission package, not in this repo.

| Project | Tests (fresh run) | Full-pack result (Kuku's confidential pack, run locally) |
|---|---|---|
| Problem 1: Promo Finder | 52/52 pass (incl. 4 web API) | 83 ranked promos from 14,615 legal windows (1,146 pass the gates); 4 episodes without a promo; byte-identical across separate processes; 0% mid-line cuts, 0 overlapping same-episode pairs. On the pack with acting directions removed: 75 promos / 6 empty episodes (v2.0 gave 41 / 23) |
| Problem 2: Nyaya Sahayak | 18/18 pass, including all 28 scripted conversations | Transcripts in `problem-2-nyaya-sahayak/outputs/transcripts/` (invented test cases). The web app was tested live: one rent-deposit message gave the correct amount, state, evidence, citations and draft notice |
| Problem 3: Continuity Checker | 19/19 pass (incl. 4 web API) | 40 findings (15 errors, 25 warnings) in about 0.15 s; planted-error evaluation 100/100 on seeds 7 and 11 (circular, as disclosed); real recall 7 of 10 confirmed spelling variants |

**Frontend (added after the main build):** all three apps now have a working Material 3 web interface on one shared design system. The engines and CLI outputs are unchanged. See [`../FRONTEND_REDESIGN_REPORT.md`](../FRONTEND_REDESIGN_REPORT.md) and [`../DESIGN_SYSTEM.md`](../DESIGN_SYSTEM.md).

## Fixed after the internal audit (v2.1)

- **Problem 1:**
  - per-show gate calibration;
  - premise slots;
  - relationship-reveal cues;
  - readable rationales;
  - `reproduce.sh` now regenerates the no-directions brittleness log.
- **Problem 2:** 12 red-team cases fixed (monthly rate × months, landlord-side users, harassment, negation, past tense, partial refunds, cheque bounce, insurance, government jobs, "50k", fraud).
- **Problem 3:** the overstated "11 spellings" claim was corrected (10 confirmed + 1 uncertain). The seeded evaluation detects names from the show instead of hard-coding them.
- **All:** AI-performed verification is attributed to the AI, not the candidate. Show-specific names and lines were removed from the public code.

## Still open

- **No real LLM run.** The optional model paths are tested only with mock servers.
- **Problem 1:** keyword dependence; the best premise cut is not chosen; no editor labels.
- **Problem 2:** the knowledge base is not reviewed by a lawyer (mostly secondary sources); voice input had a bug that entered English speech twice; it is fixed and checked with simulated speech events, but not yet re-tested with a real microphone.
- **Problem 3:** distant spelling variants are missed.
- **Candidate:** the personal re-review of the top 10 promos is pending.
