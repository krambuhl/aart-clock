# dev — build harness

Not shipped. The reproducible TouchDesigner projects and the demo builder used to develop and
verify the aart-clock toolkit.

## Contents

- **`seed.toe`** — minimal bridge-only seed (build by hand per `docs/SEED-RUNBOOK.md`). *(pending)*
- **`template.toe`** — committed output of `bootstrap.py` run on the seed. *(pending)*
- **`test-project.toe`** — working dev project: the MCP bridge + the pixel-art sketch + the built
  `aart_clock` library + the `p1_demo` chain.
- **`build_demo.py`** — reproducibly builds the Phase 1 demo (`p1_demo`) and binds the sketch noise
  to the clock.

## Rebuilding from scratch

Everything is built by running Python through the TouchDesigner MCP bridge. The source of truth is
the scripts; the `.toe`/`.tox` files are generated. Run order:

1. Open `dev/seed.toe` (bridge only), or any project with the bridge loaded.
2. Run the library builders, in order (each is idempotent):
   - `plugins/aart-clock-td/build/bootstrap.py` — namespace + module template
   - `plugins/aart-clock-td/build/sg_clock.py`
   - `plugins/aart-clock-td/build/sg_phase.py`
   - `plugins/aart-clock-td/build/sg_map.py`
   - `plugins/aart-clock-td/build/sg_divide.py`  (Phase 2; references sg_clock)
   - `plugins/aart-clock-td/build/sg_env.py`     (Phase 2)
3. Run `dev/build_demo.py` — builds Chain A (`clock → divide → env → map`) from the library
   modules and (if the pixel sketch is present) drives the noise scroll from the demo clock.

## Running a script through the bridge

Each script assigns its verification summary to a module-level `result`. Exec it into a namespace
seeded with the current globals (so it inherits TD's `op`/`project`), then read `result`:

```python
g = dict(globals())
exec(open('/abs/path/to/script.py').read(), g)
result = g['result']
```

(`print` / `return` are not captured by the bridge — see `docs/SEED-RUNBOOK.md` for the full set of
bridge gotchas.)
