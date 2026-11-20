# AGENTS.md — Đảo Đèn Lồng

3D game + headless sim for the Day 12 AI SDLC lab. Requirements: PRD-0 / tickets (lab board). Current: **Ticket-04, Test Contract v1.3** (bench, soak, leaderboard, accessibility, release). Design: `docs/adr/`, breaking changes: `CHANGELOG.md`.

## Commands
- Tests (must be green before you finish): `python3 -m unittest discover -s tests -t .`
- Scenario evidence: `python3 tools/run_scenarios.py --phase phase-N` (writes `docs/proof/phase-N/`)
- Headless: `python3 -m lantern.headless --seed 1 --night {1,2,3} --ticks 600 --out out.jsonl`
- Bench / soak: `.venv/bin/python -m lantern.app --bench --seed 42 --duration 30 --out bench.json` · `.venv/bin/python -m lantern.soak --seed 7 --nights 10 --out soak.json`
- Look at the game: `.venv/bin/python -m lantern.app --screenshot shot.png --night N` (or `--ui keys`, `--overview`), then READ the png.
- Game (3D): `python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt` then `.venv/bin/python -m lantern.app` (Windows dev: `python -m lantern.app`)

## Layout
- `lantern/sim.py` rules, deterministic, NO rendering imports. Step order = Ticket-02's 12 mandatory steps (docstring); keep new logic in the right step.
- `lantern/maps.py` standard maps; angles `(r cos a, r sin a)` from +X toward +Z. `lantern/config.py` standard non-tuning numbers.
- `lantern/headless.py` CLI. `lantern/contract_io.py` input/scenario validation (exit 2).
- `lantern/client.py` (Ursina) view + input only; `lantern/app.py` entry (`--bench`, `--export-leaderboard`, `--screenshot`, `--ui`, `--overview`).
- `lantern/soak.py`, `lantern/bench_scene.py` (bench scene + FPS math), `lantern/storage.py` (leaderboard, settings, keybinds; `$DDL_HOME`).
- `game.contract.json` tuning = the ONLY place for contract numbers; sim reads it at runtime.
- `tests/scenarios/<name>/{scenario,inputs,expect}.json` headless scenarios (`night` in expect).

## Rules
- Contract output format is exact: compact JSON lines, coords rounded 3 dp, events tick = k+1, first line `night_start`.
- Determinism: all randomness from `Game.rng` (seeded). No `time`, no global `random`, no dict-order tricks.
- Timers are integer ticks (`round(s*60)`); fuel is integer FU (1/60). Emit seconds/fuel floats only in output.
- Shade states only: spawning, wander, chase, recoil, stunned, drain. Iterate entities in id order (`idkey`).
- Creative extras must not change headless output (gate them in the app layer, or behind a flag off in headless).
- Never edit files in `docs/proof/**/runs/` by hand; regenerate with the script.
- Never weaken/delete a test to make it pass. If a ticket changed a rule, update the test, mark it `# T0N:` and list it in `docs/notes/phase-N-spec.md`.
- Before blaming the engine for a red test, re-derive the expectation from the ticket's step order (AI wrote 6 wrong expectations so far; usual miss: step 2 fuel burn/decay before step 5).
- A "full night" scenario must assert `end_ticks`, otherwise an early loss hides the perf check.
- Assumptions for ambiguous requirements go in `docs/notes/phase-N-*.md`.
- A ticket rule marked [THAY THẾ] => update tests (`# T0N`), add a CHANGELOG breaking entry; record design in an ADR.
- Client perf: never create one Entity per moving object part; use shared vertex-colour meshes under the RigidBodyCombiner; only assign Text/colour on change (`settext`/`setcolor`).
- Ursina font lacks symbols (● ⚠ emoji) and `Entity` has properties like `right`/`up`: don't use them as attribute names. Verify UI with a screenshot.
- Bench numbers only count with `minimized_frames: 0` (Panda sleeps 0.1 s/frame when minimized).
- Small commits, one concern each.
