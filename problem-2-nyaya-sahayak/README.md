# Nyaya Sahayak: Problem 2, an honest AI lawyer for everyday money disputes in India

A conversational assistant for three everyday problems:
- a **refund** that never came, or a defective product or service;
- a **landlord not returning a security deposit**;
- **salary not paid**.

It turns a messy story into a case summary: what happened, when, where, against whom, what proof exists and what is missing. It asks for missing or contradictory facts, explains where the person stands with cited sources, lists options in order, says when to get a lawyer or free legal aid, and drafts a legal notice.

It handles text in English, Hindi or Hinglish, and voice through the browser.

**Depth over breadth.** Three problems covered properly. Everything else (criminal, family, property title, replying to a summons) is recognised and routed to free legal aid, not answered.

## Run it

Requires Python 3.9 or newer, standard library only. No installs, no key, no network for the baseline.

```bash
python3 app.py web
```
Then open http://localhost:8765. The 🎤 button uses Chrome's speech recognition (English or Hindi).

```bash
python3 app.py chat
```
Chat in the terminal.

```bash
python3 app.py cases --output outputs/transcripts
```
Runs the 28 scripted test conversations (raw outputs): 16 originals plus 12 red-team cases added after an audit.

```bash
python3 -m unittest discover -s tests -v
```
Runs the tests (18 tests; one runs all 28 cases as sub-tests).

**Optional model.** Any OpenAI-compatible endpoint (Ollama, Groq, OpenRouter, or Kuku's gateway) writes a plain-language explanation in the user's language:

```bash
LLM_API_KEY=... python3 app.py web --llm-base-url http://localhost:11434/v1 --llm-model llama3.1
```

## How it avoids inventing law

This is the brief's central risk, so the design starts from it.

1. **Closed knowledge base** (`nyaya/kb.py`).
   - 14 provisions and helplines, each with a source URL, a verification level and a caveat.
   - Verification levels: `official` (read on a gov.in page), `secondary` (agreed by at least 2 reputable sources), or `general` (long-standing, stated only broadly).
   - Checked on 2026-11-21.
   - The assistant **cannot state any law that is not in this file**.
2. **Deterministic answers by default.** Every legal sentence in a reply is copied from the knowledge base and tagged `[ID]`, with a sources list. With no model, nothing is generated, so nothing can be invented.
3. **The model is boxed in** (`nyaya/guard.py`). It may only rewrite the explanation. Its text is rejected and the sourced answer shown instead if it does any of these:
   - cites an ID not supplied;
   - mentions any section, article, Act, IPC/BNS or case name not in the supplied provisions;
   - states an amount the user never gave;
   - promises an outcome.
4. **Honest about gaps.** Rent law is state law, so without a state the assistant says so. Facts whose official text wasn't re-checked are marked "general" and phrased with "generally". Every reply carries a "not legal advice" notice.

## What it knows (and doesn't)

| Problem | What it cites | Source quality |
|---|---|---|
| Consumer refund | National Consumer Helpline 1915; District/State/National Commission limits (₹50 lakh / ₹2 crore by amount paid, 2021 Rules); no fee up to ₹5 lakh; 2-year limit (s.69); online filing (e-Daakhil, possibly moving to e-Jagriti) | official / secondary |
| Unpaid salary | Code on Wages, 2019 in force from 21 Nov 2025; s.17 time limits (by the 7th of the next month; within 2 working days of leaving); s.45 claims within 3 years | secondary |
| Rent deposit | Model Tenancy Act, 2021 (only where a state adopted it; deposit cap of 2 months); Lok Adalat; CPC s.20 (where to sue); Order XXXVII summary suit; 3-year limitation | secondary / general |
| Everyone | Free legal aid: NALSA 15100, Section 12 eligibility; emergencies 112, 181, 1930 | official |

**Not covered:**
- criminal, family, property-title and employment-termination disputes;
- state-specific rent statutes;
- drafting court pleadings;
- practising arguments by playing the other side.

## Outputs

`outputs/transcripts/` holds each test conversation as `.json` (the structured reply) and `.txt` (what the user sees). `outputs/logs/` holds the run log and test results.

## Layout

- `app.py`: CLI, web server and the case runner.
- `nyaya/`: the knowledge base, intake (fact extraction), advisor (the reply), guard (anti-hallucination), and the model client.
- `cases/`: 16 test conversations.
- `tests/`: unit and red-team tests.
- `web/`: the browser UI (`index.html`, `app.js`, `app.css`, plus the shared Material 3 `m3.css` / `ui.js`; see ../DESIGN_SYSTEM.md).
