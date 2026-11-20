# AGENTS.md — Đảo Đèn Lồng

3D game + headless sim for the Day 12 AI SDLC lab. Requirements: PRD-0 / tickets (lab board). Current: **Ticket-02, Test Contract v1.1** (3 nights).

## Commands
- Tests (must be green before you finish): `python3 -m unittest discover -s tests -t .`
- Scenario evidence: `python3 tools/run_scenarios.py --phase phase-N` (writes `docs/proof/phase-N/`)
- Headless: `python3 -m lantern.headless --seed 1 --night {1,2,3} --ticks 600 --out out.jsonl`
- Game (3D): `python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt` then `.venv/bin/python -m lantern.app` (Windows dev: `python -m lantern.app`)

## Layout
- `lantern/sim.py` rules, deterministic, NO rendering imports. Step order = Ticket-02's 12 mandatory steps (docstring); keep new logic in the right step.
- `lantern/maps.py` standard maps; angles `(r cos a, r sin a)` from +X toward +Z. `lantern/config.py` standard non-tuning numbers.
- `lantern/headless.py` CLI. `lantern/contract_io.py` input/scenario validation (exit 2).
- `lantern/app.py` 3D view only: reads sim state, never owns game rules.
- `game.contract.json` tuning = the ONLY place for contract numbers; sim reads it at runtime.
- `tests/scenarios/<name>/{scenario,inputs,expect}.json` headless scenarios (`night` in expect).

## Rules
- Contract output format is exact: compact JSON lines, coords rounded 3 dp, events tick = k+1, first line `night_start`.
- Determinism: all randomness from `Game.rng` (seeded). No `time`, no global `random`, no dict-order tricks.
- Timers are integer ticks (`round(s*60)`); emit seconds only in snapshots.
- Shade states only: spawning, wander, chase, recoil, stunned. Iterate entities in id order (`idkey`).
- Creative extras must not change headless output (gate them in the app layer, or behind a flag off in headless).
- Never edit files in `docs/proof/**/runs/` by hand; regenerate with the script.
- Never weaken/delete a test to make it pass. If a ticket changed a rule, update the test, mark it `# T0N:` and list it in `docs/notes/phase-N-spec.md`.
- Before blaming the engine for a red test, re-derive the expectation from the ticket's step order (AI wrote 4 wrong expectations so far).
- A "full night" scenario must assert `end_ticks`, otherwise an early loss hides the perf check.
- Assumptions for ambiguous requirements go in `docs/notes/phase-N-*.md`.
- Small commits, one concern each.
