# Design: problem choice, framing, architecture

## 1. Which problem, and why

Each problem was scored 1 (weak) to 5 (strong) on each criterion, for this assignment and a 2 to 3 hour build.

| Criterion | P1 Find the promos | P2 AI lawyer (India) | P3 Own problem |
|---|---|---|---|
| Real, stated user pain | 5: an editor watches every episode, every week | 5: very large need | 3: I would have to prove it's real with my own research |
| Value to Kuku | 5: promos drive acquisition for every new show | 1: outside Kuku's business | 4: possible, but not shown |
| Test data available | 5: 50 timed episodes provided | 2: I'd have to write the cases | 2: I'd have to collect it |
| Can output quality be checked? | 4: timestamps are exact; hook and cliff are judgeable from the script | 2: legal correctness needs expert review | 2: depends on the problem |
| Feasible in 2 to 3 h, and working | 5: and I already had a working v1 | 2: grounding in statutes, multiple languages, voice, safety | 3 |
| Risk of harm from a wrong answer | Low: a human posts the clip | High: wrong legal advice hurts people | Low |
| Fits "run it on a new input in the interview" | 5: a new show folder | 3 | 3 |
| Room for a non-generic idea | 4: performance directions, cut integrity, gates | 3 | 4 |
| **Total** | **38** | **20** | **24** |

**Decision: Problem 1.** It is the only option with real input data, an output that can be checked down to the timestamp, and a direct line to Kuku's growth. It also had an existing working baseline whose defects I could find and measure. Problem 2 is a worthy problem, but in this time a responsible version would mostly be a disclaimer around retrieval of real statutes. Problem 3 would spend most of the time proving the problem exists.

## 2. The real problem behind the brief

An editor's scarce resource is **attention per show**. They don't need a model to "be creative". They need the 50 to 100 minutes of a new show reduced to roughly 20 clips that are worth watching, with cut points that already work. A shortlist is useful only if:

1. the cut points are **usable as given**: no half-lines, timed to the script;
2. the top of the list is **mostly right**, so the editor stops reviewing early;
3. each pick says **why**, so the editor can reject it in seconds;
4. it is **not five versions of one scene**.

The tool therefore optimises for editor review time, not for an imagined "virality score".

## 3. Requirements

- **Functional:**
  - Parse a show folder or a single episode.
  - Propose clips of 20 to 60 s, each with episode, start/end times, hook, cliffhanger and a one-line reason.
  - Rank them, explain the ranking, and flag episodes that have no good promo.
  - Output for both people and machines.
- **Non-functional:**
  - Deterministic.
  - Offline by default, with zero dependencies.
  - Under about 1 minute per show.
  - The model can be swapped with a flag.
  - Every number traces back to script evidence.
  - Confidential text is sent to a model only when the user opts in.

## 4. Assumptions (the brief was silent)

1. Scripts follow the pack's cue format. Small variations are tolerated, and anything not understood produces a warning.
2. Script timestamps match the final cut. If the edit drifts, the timestamps drift with it.
3. One continuous segment per promo is the first deliverable. The brief allows joins, but a continuous clip needs no editing decisions and has no continuity risk.
4. A promo pulls viewers into episode 1, so clarity for a stranger matters more than late-series payoff. Late-episode picks are still allowed: the title already tells viewers he is a duke.
5. Up to 2 picks per episode, and 0 if nothing passes the gates. It is better to say "episode 8 has no promo" than to pad the list.
6. Scores rank clips within one show. They are not predictions of performance.

## 5. Architecture options considered

| | A. Rules over every window, model reranks finalists (chosen) | B. Model reads whole episodes and proposes clips | C. Model labels every beat, code assembles windows |
|---|---|---|---|
| Timestamp accuracy | Exact by construction | The model invents or misplaces times, so every output needs re-checking | Exact |
| Works offline / free | Yes | No | No |
| Cost per show | Rules free; model ≈73k input tokens (measured) | One long-context call per episode, roughly 5 to 10× more | One call per line: highest |
| Ceiling on judgment | Limited by how many good candidates the rules find (recall) | Highest | High |
| Explainability | Every sub-score has a reason | Low | Medium |
| Failure mode | Misses subtle drama | Hallucinated or overlapping clips | Many calls, so many failure points |

A is the right fit for this assignment: free, reproducible, testable, and a model can be plugged in later without code changes. C is the natural next step if the rules' recall turns out to be the bottleneck once editor labels exist (see section 9).

## 6. Code versus model

| Job | Who | Why |
|---|---|---|
| Parsing, timestamps, cut legality, 20 to 60 s limits, duplicate removal, posting order | Code | Exact, auditable, and must never be "creative" |
| First-pass hook, cliffhanger and clarity signals | Code (lexicons + performance directions + structure) | Free, fast, explainable; good at structure (questions, interruptions, threats, closing lines) |
| Nuanced judgment: is this actually gripping, is it resolved, can a stranger follow it | Model (optional) | Rules cannot read sarcasm, subtext or a quiet reveal |
| Final decision to post | Human editor | They watch the footage: performance, lighting and pacing are not in the text |

## 7. Failure handling

- **Bad input.** Clear error and exit code 2 for: a missing folder, an empty folder, an empty file, no timed blocks, or duplicate episode numbers. Recoverable problems become warnings: missing or malformed timestamps, or an end before its start.
- **Episodes without a good clip.** Reported by name. Nothing is padded.
- **Model failures.**
  - Timeout, HTTP error or bad JSON: retry once, then fall back to rules for that episode and log it.
  - A review citing a block outside the clip, or with evidence in the wrong place, is discarded.
  - Non-numeric or out-of-range scores, unknown candidate IDs and duplicate reviews are discarded.
- **Prompt injection.** Script text is marked as data. More importantly, nothing the model returns can move a cut point or rescue a gated window.

## 8. Evaluation strategy

- **Measured now**, see [QUALITY_REVIEW.md](QUALITY_REVIEW.md):
  - Structural metrics recomputed from the script for any output: cut integrity, duration, speech in the first 3 s, openings that need unseen context, overlap, distinct rationales.
  - A script-only top-20 review of v1 and v2 (not blind; I wrote v2).
- **Needs Kuku:**
  - **Editor acceptance@20** using `ranked_promos.csv`.
  - **Minutes from new show to 10 approved promos**, against the current manual baseline.
  - Downstream: thumb-stop rate (3 s views ÷ impressions), completion rate, and installs or episode-1 starts per promo.
  - Every editor verdict becomes a label for tuning the gates and few-shot model prompts.

## 9. Scaling to every show

- **Volume.** The rules cost about 45 s of CPU per 50-episode show, so all shows can run as a batch on every upload. The model adds about 46 small calls per show, cached by content hash.
- **Storage.** One JSON per show (≈0.4 MB) plus the editor verdict CSV. Verdicts flow back as training and evaluation data.
- **Monitoring.**
  - Parser warnings per show (catches a format change).
  - Share of episodes with no qualifying promo.
  - Model error and discard rate.
  - Editor acceptance rate per show and over time.
- **Next steps, in order:**
  1. Collect editor verdicts.
  2. Tune the gates.
  3. Few-shot the model with accepted and rejected examples.
  4. Add 2 to 3 segment "cold open" montages (best hook from one moment, best cliff from another).
  5. Add shot-level video checks (face visible, no cut mid-motion) once footage is available.
- **Privacy.** Run the model locally or on a gateway with a no-retention policy. Send only finalist excerpts, never whole scripts.
