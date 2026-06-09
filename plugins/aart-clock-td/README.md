# aart-clock-td

The aart-clock TouchDesigner plugin: a modular timing, rhythm, modulation, and signal-processing toolkit, shipped as a single component.

## What ships

- **`aart_clock.tox`** — one container component holding the `sg_*` signal modules as internal sub-components. Drop it into a project once to get the whole family; individual modules can still be copied out. (Generated artifact — the source of truth is `build/`.)

## How it's built

The toolkit is **build-script-first**: each module is authored as a Python build script that constructs its network via the TouchDesigner MCP bridge. The `.tox` is a generated, committed artifact.

```
build/
├── bootstrap.py     # constructs the /project1/aart_clock namespace + module template onto the seed
├── sg/              # thin 'sg' build-helper library (extracted once 2-3 modules share patterns)
├── sg_clock.py      # per-module build scripts
├── sg_phase.py
├── sg_map.py
└── …
```

Pipeline: `dev/seed.toe` (bridge only) → run `build/bootstrap.py` + module scripts through the bridge → `dev/template.toe` + `aart_clock.tox`. See `docs/SEED-RUNBOOK.md` for the seed and the boundary between hand-built and scripted.

## Signal language

Five core types — Phase, Gate, **Pulse** (one-sample event), Value, Vector — with polarity (unipolar/bipolar) a convention on Value/Vector, not a separate type. See the project `PLAN.md` and `USAGE.md` for the full contract and module reference.
