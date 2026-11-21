# Run instructions

**Requirements:** Python 3.9 or newer, nothing to install. The examples use `python3`; on Windows use `python`.

## Problem 1: Promo Finder

```bash
cd problem-1-promo-finder
```

Run the tests (52, synthetic data, about 20 s):

```bash
python3 -m unittest discover -s tests -v
```

Run on a show folder of episode `.txt` files (or a single episode file). It writes to `./outputs/`:

```bash
python3 run.py --show "path/to/show_folder"
```

Or use the web app, then open http://localhost:8701. `--shows` takes one show folder or a folder of show folders; results go to `outputs/web/<show>/`:

```bash
python3 web.py --shows "path/to/folder_of_shows"
```

Optional LLM review (CLI only). Any OpenAI-compatible endpoint works, for example Ollama:

```bash
python3 run.py --show "path/to/show_folder" --llm-base-url http://localhost:11434/v1 --llm-model llama3.1
```

Reproduce all outputs and logs, plus a v1-vs-v2 evaluation when a v1 output is supplied:

```bash
./reproduce.sh "path/to/show_folder" ["path/to/v1/ranked_promos.json"]
```

**Expected screenplay format:** `**LABEL (Direction):**` on one line, then `Start: (mm:ss.xx) | End: (mm:ss.xx)`, then the text. Variations (no bold, h:mm:ss, comma decimals) are tolerated; anything unparseable is reported in `outputs/parse_report.json`.

## Problem 2: Nyaya Sahayak (AI lawyer)

```bash
cd problem-2-nyaya-sahayak
```

Run the tests (18; one runs all 28 scripted conversations):

```bash
python3 -m unittest discover -s tests -v
```

Browser UI, then open http://localhost:8765 (voice input works in Chrome):

```bash
python3 app.py web
```

Chat in the terminal:

```bash
python3 app.py chat
```

Regenerate the 28 conversation transcripts:

```bash
python3 app.py cases --output outputs/transcripts
```

## Problem 3: Continuity Checker

```bash
cd problem-3-continuity-checker
```

Run the tests (19):

```bash
python3 -m unittest discover -s tests -v
```

Run the checker. It writes `outputs/report.html` and more, and exits with 1 if errors are found:

```bash
python3 run.py --show "path/to/show_folder"
```

Or use the web app, then open http://localhost:8703:

```bash
python3 web.py --shows "path/to/folder_of_shows"
```

Recall on planted errors:

```bash
python3 evaluate_seeded.py --show "path/to/show_folder" --seed 7
```

## Demo show (no Kuku pack needed)

From the repository root, write an invented 8-episode show with planted continuity errors to `samples/The Lantern House/`:

```bash
python3 samples/make_demo_show.py
```

Then run either screenplay app on it, for example `cd problem-3-continuity-checker && python3 web.py --shows ../samples`.
