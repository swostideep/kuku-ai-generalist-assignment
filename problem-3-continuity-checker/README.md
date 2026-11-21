# Script Continuity Checker (Problem 3)

**One person:** the story or script editor who signs off AI-generated microdrama episodes.
**One step:** screenplay QA before voice and video generation.
**One output:** a ranked list of continuity defects. Each one has its episode, cue ID, timestamp, evidence and a suggested fix.

> **Public repo note:** the evidence below was measured on Kuku's confidential 50-episode input pack. Names and lines from
> that pack are deliberately not reproduced here. The full report, test report and interview notes are in the private
> submission package.

## The problem, and evidence that it's real

When AI writes a series episode by episode, it drifts. Measured on Kuku's own pack:

- **One family/estate name appears in at least 10 different spellings** across episodes (an 11th is uncertain). The checker links 7 of them.
- **A main antagonist is labelled only by a description** (e.g. "TALL STRANGER") for 53 lines across 10 episodes, while the camera directions use his real name. Voice and character assets keyed by speaker label would treat him as two people. The checker suggests the real name from co-occurrence.
- **The lead character has two speaker labels** (with and without an honorific), and so do two other characters.
- **10 lines are timed faster than 5 words per second.** They can't be spoken in their slot.
- **3 lines overlap the same speaker's previous line.**

Public reporting notes viewer complaints about discontinuity in AI dramas (Asia Economy, July 2026; MIT Technology Review, May 2026). I found no public source on name errors specifically. I have no Kuku data on re-render costs, so the cost argument is reasoning, not measurement.

## Run it

Requires Python 3.9 or newer, standard library only. A 50-episode show takes about 0.15 s.

```bash
python3 run.py --show "path/to/show_folder"
```
Writes `outputs/report.html`, `report.md`, `findings.csv` and `findings.json`. The exit code is 1 when errors are found, so it can gate a pipeline.

```bash
python3 evaluate_seeded.py --show "path/to/show_folder" --seed 7
```
Recall on planted errors. Names are detected from the show itself.

```bash
python3 -m unittest discover -s tests -v
```
Runs 15 tests on synthetic scripts.

Optional model review (any OpenAI-compatible endpoint):

```bash
LLM_API_KEY=... python3 run.py --show <folder> --llm-base-url http://localhost:11434/v1 --llm-model llama3.1
```

## What it checks (all deterministic)

| Check | Rule |
|---|---|
| NAME_DRIFT | Proper nouns (dialogue, action, camera text, loglines, notes) grouped by spelling similarity: ≥0.72 with the same first 3 letters, or differing only in the first letter |
| LABEL_ALIAS | Speaker labels equal after removing honorifics; LORD X + LADY X with no plain X = a couple, not flagged |
| UNNAMED_RECURRING | A descriptive speaker label in 2+ episodes; suggests the name camera text uses while it speaks |
| SPEECH_RATE | Over 4.5 words/s is a warning, over 5.0 an error |
| SELF_OVERLAP | A speaker starts a line before their previous line ends |
| SCENE_BOUNDS | Cues outside their scene; gaps or overlaps between scenes |
| CONTINUITY_REF | "Picks up from Episode N" must point to the previous episode |

**The optional model** only judges whether flagged spellings are the same entity. It may only label spellings the checker found, and it never deletes a finding.

## Quality

- **Planted errors:** 100 per seed across 5 types, on 2 seeds. 100/100 caught, with 0 unrelated new findings. The first version caught 76/100; each miss was a real bug, now fixed.
  - Caveat: the same author wrote the error generator and the checker, so this is partly circular.
- **Real drift:** 7 of 10 confirmed spelling variants linked; distant spellings are missed.
- **Precision on the pack:** an AI-assisted review (not yet repeated by the candidate) of all 40 findings gave 21 clear defects, 14 borderline fast lines, 3 unverified and 2 debatable.
- **Success metrics for a real team:**
  - editor acceptance of flags (target ≥ 70%);
  - continuity defects found after rendering;
  - re-renders caused by the script;
  - QA minutes per episode.

## Limits

- Spelling similarity can't link distant variants, or tell a typo from a deliberate alias.
- Covers names, labels and timing only; no wardrobe or prop continuity yet.
- Built on one show's format. No real LLM was run.

**AI usage:** built with Claude Code (Claude Opus 5.5). Where it went wrong: it reused a parser that normalised "LADY X" to "X", hiding exactly the label inconsistencies this tool reports. The seeded evaluation exposed it (label recall 5/20), and it was fixed.
