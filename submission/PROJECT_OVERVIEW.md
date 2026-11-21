# Project overview

## Which problem is submitted

Kuku's brief: "Pick one problem… One problem, one submission." **The submitted problem is Problem 1 (Promo Finder)**. It is the problem Kuku provided the input pack for, and it has the deepest evidence. Problems 2 and 3 are kept here as a portfolio.

## Summary of each

| | Problem 1: Promo Finder | Problem 2: Nyaya Sahayak | Problem 3: Continuity Checker |
|---|---|---|---|
| User | Promo editor | A person in India owed money | Script/story editor |
| Core idea | Rules over every legal 20–60 s window; hard gates for hook, cliffhanger and standalone; optional LLM reviewer bound to evidence | A closed, sourced legal knowledge base; deterministic replies; an optional LLM explanation checked by a hallucination guard | Deterministic continuity checks; an optional LLM judges name clusters |
| AI vs code | Code: parsing, cut legality, scoring, selection. AI (optional): judgment on finalists | Code: intake, case summary, cited rights, notice. AI (optional): plain-language rewrite | Code: all checks. AI (optional): typo vs different entity |
| Key measured results | Mid-line cuts 8% → 0% and overlapping duplicates 13 → 0 vs v1; on scripts without acting directions, 41 → 75 promos after per-show gate calibration | 28/28 scripted conversations, including 12 red-team cases that the first build failed 9 of | 100/100 planted errors (circular, as disclosed); 7/10 real spelling variants linked |
| Main limits | Keyword dependence; script ≠ footage; single-segment only; no real LLM run | Legal content not lawyer-reviewed; three problem types only; no real LLM run | Distant spellings missed; thin AI role; no real LLM run |

## Architecture (all three)

```
input files ──► deterministic parser ──► deterministic analysis ──► (optional) LLM step, validated by code ──► JSON / CSV / HTML / Markdown
```

- The model is swapped with `--llm-base-url` and `--llm-model` (OpenAI-compatible API).
- Every model output is validated: invalid citations or evidence are discarded, and the deterministic result stands.
