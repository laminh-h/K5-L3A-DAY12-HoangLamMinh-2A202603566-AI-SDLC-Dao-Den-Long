---
name: verify-phase
description: Run the game headless, check every scenario, and save evidence for a phase. Use before tagging phase-N or after changing game rules.
---

1. `python -m unittest discover -s tests -t .` — must be OK (includes perf test: full night <= 30 s).
2. For each requirement of the phase without a scenario, add `tests/scenarios/NN_name/` with
   `scenario.json` (contract format), `inputs.json`, `expect.json`
   (`seed`, `ticks`, `requirement`, optional `events` exact list, `end_state`, `end_score`, `end_ticks`).
   Derive expected values from the requirement + tuning, NOT by copying the program output.
3. `python tools/run_scenarios.py --phase phase-N` — every row PASS (runs twice, byte-identical).
4. Update `docs/proof/phase-N/README.md` traceability table (requirement -> how -> evidence -> result).
   Write "chưa đạt" + reason for anything not met. Never hand-edit `runs/`.
5. If a check fails, fix the code (or the test with a written reason in docs/notes), then repeat.
6. Full-night scenarios must set `end_ticks` so an early loss cannot hide a perf regression.
