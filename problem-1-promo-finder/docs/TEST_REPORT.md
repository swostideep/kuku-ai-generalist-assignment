# Test report

**Final state (v2.1): 48 / 48 unit, adversarial and end-to-end tests pass.** The raw log is `outputs/logs/test_results.txt`.

- **Fixtures** are synthetic screenplays (`tests/fixtures.py`), so no Kuku text is in the tests.
- **Full-pack system checks** are below the table. Their logs are in `outputs/logs/`.
- **Re-run:** `python3 -m unittest discover -s tests -v`

## Unit, adversarial and end-to-end tests

| ID | Input | Expected | Actual | Result |
|---|---|---|---|---|
| P01 | Standard 25-cue episode | 25 blocks, 4 kinds; speaker "MARA", direction "Outraged, Accusing", 10.0 to 12.0 s, scene set, no warnings | As expected | Pass |
| P02 | `0:01:02,50` style timestamps | 62.5 s | 62.5 s | Pass |
| P03 | Cue with no timestamp | Warning; text not merged into a neighbour | 1 block + warning | Pass |
| P04 | End before start; `00:xx` | Both skipped with warnings | Only the valid block remains | Pass |
| P05 | Empty folder / empty file / missing path | Clear `ValueError`, no traceback in the CLI | As expected | Pass |
| P06 | Invalid UTF-8 byte, no EPISODE NUMBER line | Parsed with a warning; episode number taken from the file name (42) | As expected | Pass |
| P07 | Two files both "Episode 1" | Rejected as ambiguous | `ValueError` | Pass |
| P08 | "…who knows…" / "…is the maid."; `(O.S.) (Firm)` | First block marked `continues`; emotion "Firm" | As expected | Pass |
| C01 | Fixture episode | Every window 20 to 60 s | As expected | Pass |
| C02 | Overlapping dialogue (an interruption) | No cut inside any spoken line | Some windows rejected; none cut a line | Pass |
| C03 | Split sentence across the 50 s mark | No window ends at 50.0 s | None | Pass |
| C04 | Episode of 12 s | 0 windows, no crash | 0 | Pass |
| C05 | All windows | Hook beat within 3 s of the cut | As expected | Pass |
| C06 | Calm intro → accusation → threat → calm resolution | Best window opens on "You poisoned my sister!" and ends on the threat or the sting | As expected | Pass |
| C07 | Window ending after the resolution ("Good night.") | "Tension already resolved" penalty; gated out | As expected | Pass |
| C08 | Calm opening + strong ending (v1's weighted-sum defect) | Rejected by the hook gate despite cliffhanger ≥ 45 | As expected | Pass |
| S01 | "You framed my brother!" (Outraged) vs "The tea is ready." (Warm) | Accusation ≥ 30 points higher | As expected | Pass |
| S02 | "What?", "Viktor...", "Mother.", "Mother... Mara...", "My Lord?" as hooks | All < 45 | As expected | Pass |
| S02b | "You're alive.", "Burn it.", "Poison." | Not treated as bare reactions | As expected | Pass |
| S03 / S03b | "He did it."; "Arrested?" after "They arrested her!" | Flagged as needing unseen context or as an echo | As expected | Pass |
| S04 | Question / threat vs "Thank you." / "I forgive you." | Soft endings < 20, strong endings ≥ 40 higher | As expected | Pass |
| S05 | **Adversarial:** "You'll kill me with kindness." (Warm, Laughing) vs "I will kill you." (Menacing) | Joke < 45; threat ≥ 25 higher | Joke 32 | Pass |
| S05b | **Regression:** "beam crashes", "slapped" | Match the crash / slap lexicon | As expected | Pass |
| S06 | **Known limitation:** "Mother will kill me if I am late for dinner!" with no direction | Documents that it *passes* the hook gate (false positive) | 46 ≥ 45 | Pass (documented failure mode) |
| SEL01 to 04 | Overlapping windows, a gated high scorer, two picks from one episode, a cross-episode recap | Overlap suppressed; gated window never picked; one per episode in the first wave; recap dropped | As expected | Pass |
| J01 | Valid model review | 40/60 blend, model's reason used | As expected | Pass |
| J02 | **Hallucination:** cited block `B999` | Review discarded, rule score kept | As expected | Pass |
| J03 | Hook evidence cited from the end of the clip | Discarded | As expected | Pass |
| J04 | Score 150, "high", null | Discarded | As expected | Pass |
| J05 | Unknown candidate ID; same ID reviewed twice | Ignored; applied once | 1 applied, 2 problems logged | Pass |
| J06 | JSON inside ``` fences, or inside prose | Parsed | As expected | Pass |
| J07 | Model returns prose twice | 2 calls, then rules fallback with the error recorded | As expected | Pass |
| J08 | **Prompt injection / compromised model:** all scores 100 | Cut points unchanged, gated windows not rescued, script marked as data, model never sees absolute times | As expected | Pass |
| H01 | Local mock OpenAI-compatible HTTP server | Model path works end to end; second run served from cache (0 new calls) | As expected | Pass |
| H02 | Server returns HTTP 500 | Retry, then rules-only output with errors listed per episode | As expected | Pass |
| E01 / E01b | Two runs in one process; two processes with different hash seeds | Byte-identical promos | As expected | Pass |
| E02 | 3-episode show including a 12 s episode | All 6 output files written; episode 3 listed as having no promo | As expected | Pass |
| E03 | Episode 2 is a verbatim recap of episode 1 | Cross-episode duplicate dropped | As expected | Pass |
| X01 | Missing folder; `--llm-base-url` without a model; `--per-episode 0` | Exit code 2 with a message | As expected | Pass |

## Tests added in v2.1 (after the internal audit)

| ID | Input | Expected | Actual | Result |
|---|---|---|---|---|
| A01 | Score lists whose 80th-percentile hook is 31 vs above 45 | Gate 31 for the flat show; 45 for the rich one | As expected | Pass |
| A02 | Fixture with directions stripped | Still runs end-to-end | As expected. **This also passes on v2.0, so it is only a smoke test.** The proof is `outputs/logs/no_directions_check.txt` (full pack: 41 promos / 23 empty episodes → 75 / 6) | Pass (not discriminating) |
| A03 | 15 strong late-episode picks + 1 weaker episode-1 pick | Episode 1 lands in the first 10 with premise slots, and not without them | As expected | Pass |
| A04 | "Because she is marrying him." | Tagged as a reveal | As expected | Pass |

## Full-pack system checks

| Check | Expected | Actual | Log |
|---|---|---|---|
| Full run, 50 episodes | Completes, 0 parser warnings | 83 promos, 46 episodes covered, 4 episodes with no promo (8, 17, 19, 40), ≈45 s, ≈35 MB RSS | `logs/run_log.txt`, `run_summary.md` |
| Cross-process determinism (`PYTHONHASHSEED=12345`) | Identical | Identical | `logs/determinism_check.txt` |
| Format robustness: episode 12 with labels unbolded and times as `0:mm:ss,cc` | Same picks as the original | Identical picks and scores | Run by hand; noted here |
| Cut integrity over all 83 picks | 0 mid-line starts or ends | 0 / 0 | `logs/evaluation.txt` |
| Same-episode overlap > 30% | 0 | 0 | `logs/evaluation.txt` |

## Defects found by testing, and what I did

These are written down rather than hidden.

1. **Non-reproducible rationale text (product bug).**
   - *Found by:* the first cross-process re-run of the full pack. Scores and ranks were identical, but 29 fields differed: the emotion word quoted in "why it works".
   - *Cause:* the code iterated over a Python `set`, whose order changes between processes. The in-process test E01 could not see this.
   - *Fix:* iterate in written order. Test E01b now runs two processes with different seeds.
2. **Lexicon missed inflections (product bug).**
   - *Found by:* checking v1's strong picks that v2 rejected (false-negative analysis).
   - *Cause:* exact whole-word matching, so "crash" did not match "beam crashes". The E18 fire scene was rejected as a result.
   - *Fix:* simple inflections, including doubled consonants ("slapped"), with a guard so "die" does not match "dieting". Regression test S05b added. The fire scene now ranks #34.
3. **Lead detection split one character in two (product bug).**
   - *Found by:* reading the episode 1 picks.
   - *Cause:* "LADY MARA" in episode 1 and "MARA" elsewhere were counted as different people, so episode 1 clips lost the lead-character bonus.
   - *Fix:* canonical names that strip honorifics.
4. **Two wrong tests (test bugs, not product bugs).**
   - SEL04 used fake lines shorter than the 12-character minimum the duplicate check uses.
   - S06's first example ("This heat could kill a horse.") did not isolate the keyword effect, because a separate pronoun rule fired. I replaced it with an example that does. The test still documents a real failure mode.

## Not tested

- Any real LLM. None was available offline, so only the contract was tested, with a mock server.
- Real footage, and editor agreement.
