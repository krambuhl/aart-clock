# SEED-RUNBOOK

How to build `seed.toe` — the one un-scripted link in the aart-clock build pipeline — and the empirically settled boundary between what the seed must carry and what `bootstrap.py` constructs.

## Why a seed exists

The build pipeline is `Python build scripts → (executed via the TouchDesigner MCP bridge) → template.toe + module .tox artifacts`. Every script runs *through* the bridge (`mcp_webserver_base.tox`). That creates one bootstrapping constraint: the bridge cannot be built by a script that runs through it. The bridge must already exist before any scripting begins.

`seed.toe` is therefore a minimal, committed TouchDesigner project that carries only the bridge. It is the single artifact in the pipeline that is assembled by hand rather than reproduced from text — which is why its construction is captured here as a followable runbook. The reproducibility claim for the project is scoped accordingly: *the library is reproducible from `seed.toe` + the build scripts, and `seed.toe` itself is reproducible by following this runbook.*

## The settled seed/bootstrap boundary

Determined empirically against TouchDesigner 099.2023.12480 via the MCP bridge (probe run 2026-06-09): every operation `bootstrap.py` and the module build scripts require is constructable through the bridge. Nothing about an aart-clock module needs to be hand-built.

### In `seed.toe` (manual, not scripted)

- The MCP bridge component **`mcp_webserver_base.tox`** at `/project1/mcp_webserver_base`, imported from the vendored `plugins/touchdesigner-mcp-td/` directory **with its folder structure preserved** (the `.tox` references `modules/` by relative path; moving files breaks it).

That is the entire seed. Nothing else.

### In `bootstrap.py` (scripted via the bridge)

Everything aart-clock:

- The `/project1/aart_clock` namespace Base COMP.
- The `sg_template` module template (the `in / out / params / ext / docs / demo / internal` standard).
- Custom parameter pages and typed parameters.
- The extension scaffold (extension DAT + wired, promoted, initialized extension class).
- The canonical channel-naming contract and the shared sync/reset/wrap-detect primitive.

### Capabilities verified through the bridge

| Capability bootstrap needs | API exercised | Result |
|---|---|---|
| Create namespace + module COMPs | `parent.create('baseCOMP', name)` | works |
| Nested In/Out CHOPs | `comp.create('inCHOP'/'outCHOP', name)` | works |
| Internal CHOP creation + wiring | `create('constantCHOP', …)`, `outputConnectors[0].connect(...)` | works (`out1` ← `src` confirmed) |
| Custom parameter page | `comp.appendCustomPage(name)` | works |
| Typed params: Float / Pulse / Menu | `page.appendFloat/appendPulse/appendMenu`, `par.menuNames`/`menuLabels` | works (menu defaulted to first name) |
| Live parameter read-back | `comp.par.Bpm.eval()` | works |
| Extension DAT + source | `comp.create('textDAT', name)`, `dat.text = …` | works |
| Wire + promote + initialize extension | `par.extension1`, `par.promoteextension1`, `initializeExtensions()` | works (`len(comp.extensions) == 1`) |
| Cosmetics (color / comment / tags) | `comp.color`, `comp.comment`, `comp.tags` | works |

## Building `seed.toe`

Prerequisites: TouchDesigner **099.2023.12480** and the vendored bridge at `plugins/touchdesigner-mcp-td/` (already in this repo).

1. Launch TouchDesigner and start a new, empty project.
2. In `/project1`, remove any default operators so the network is empty.
3. Import the bridge: drag `plugins/touchdesigner-mcp-td/mcp_webserver_base.tox` into `/project1` so it lands at `/project1/mcp_webserver_base`. Do **not** move or rename anything inside `plugins/touchdesigner-mcp-td/` — the `.tox` resolves `modules/` by relative path.
4. Confirm the bridge is live: open the Textport (Alt+T) and verify the WebServer DAT is listening on `http://127.0.0.1:9981`.
5. Save the project as `dev/seed.toe`.
6. Commit `dev/seed.toe`.

`seed.toe` should contain exactly one operator of consequence: `/project1/mcp_webserver_base`.

## Producing `template.toe` from the seed

1. Open `dev/seed.toe` and connect the MCP server (the MCP client config is the project's responsibility, not the seed's).
2. Run `plugins/aart-clock-td/build/bootstrap.py` through the bridge. It constructs `/project1/aart_clock` and the module template.
3. Save the result as `dev/template.toe` and commit it.

`template.toe` is a regenerated artifact: it is the committed output of `bootstrap.py` run on `seed.toe`, not a hand-built file. The shipped `plugins/aart-clock-td/aart_clock.tox` is exported from the built `/project1/aart_clock` component.

## Appendix — bridge execution notes

These are gotchas for any script run via the MCP `execute_python_script` path; `bootstrap.py` and the module build scripts account for them.

- **Return values come from a variable named `result`.** The bridge executes the script at module scope and returns the value bound to `result`. `print(...)` output and `return` statements are **not** captured (`return` at module scope is a syntax error). Assign the data you want back to `result`.
- **Running a committed build file** (so the file on disk is exactly what executes): exec it into a namespace seeded with the current globals (which carry TD's `op`/`project`), then surface its `result`:

  ```python
  g = dict(globals())
  exec(open('/abs/path/plugins/aart-clock-td/build/bootstrap.py').read(), g)
  result = g['result']
  ```

  A bare `exec(open(...).read())` will run but its `result` is swallowed by the nested scope — pass the namespace and read `g['result']`.
- **Operator type names are passed as strings** to `create()` (e.g. `create('baseCOMP', 'aart_clock')`); this is the verified-working form through the bridge.
- The bridge operates on a **running instance**; it is not a headless build. Unattended/headless reproduction is out of scope for v1 (see PLAN.md → Future Work).
