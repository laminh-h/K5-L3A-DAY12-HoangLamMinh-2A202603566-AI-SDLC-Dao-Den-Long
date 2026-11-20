# AGENTS.md — Đảo Đèn Lồng

3D game + headless sim for the Day 12 AI SDLC lab. Requirements: PRD-0 / tickets (lab board), Test Contract v1.0.

## Commands
- Tests (must be green before you finish): `python3 -m unittest discover -s tests -t .`
- Scenario evidence: `python3 tools/run_scenarios.py --phase phase-N` (writes `docs/proof/phase-N/`)
- Headless: `python3 -m lantern.headless --seed 1 --night 1 --ticks 600 --out out.jsonl`
- Game (3D): `python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt` then `.venv/bin/python -m lantern.app` (Windows dev: `python -m lantern.app`)

## Layout
- `lantern/sim.py` game rules, deterministic, NO rendering imports. `lantern/headless.py` CLI. `lantern/contract_io.py` input/scenario validation (exit 2).
- `lantern/app.py` 3D view only: reads sim state, never owns game rules.
- `game.contract.json` tuning = the ONLY place for contract numbers; sim reads it at runtime.
- `tests/scenarios/<name>/{scenario,inputs,expect}.json` headless scenarios.

## Rules
- Contract output format is exact: compact JSON lines, coords rounded 3 dp, events tick = k+1.
- Determinism: all randomness from `Game.rng` (seeded). No `time`, no global `random`, no dict-order tricks.
- Creative extras must not change headless output (gate them in the app layer, or behind a flag off in headless).
- Never edit files in `docs/proof/**/runs/` by hand; regenerate with the script.
- Never weaken/delete a test to make it pass. If a requirement changed, update the test AND note why in `docs/notes/`.
- Assumptions for ambiguous requirements go in `docs/notes/phase-N-assumptions.md`.
- Small commits, one concern each.
