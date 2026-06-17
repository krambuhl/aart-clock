# aart-clock — agent guide

aart-clock is a modular signal toolkit for **TouchDesigner**: composable `sg_*` modules (clock,
phase, divide, lfo, random, env, map) that drive visuals with modular-synth concepts. It generates
and shapes signals only — no rendering. See `USAGE.md` for the consumer view, `PLAN.md` (under
`projects/2026-06-09-aart-clock/`) for the design and decisions.

## How work happens here: the TouchDesigner MCP bridge

Modules are built and verified by driving a **running** TouchDesigner instance through the
[touchdesigner-mcp](https://github.com/8beeeaaat/touchdesigner-mcp) server (HTTP `127.0.0.1:9981`,
via `plugins/touchdesigner-mcp-td/mcp_webserver_base.tox`). The MCP tools (`mcp__touchdesigner__*`)
let you create operators, set params, run Python, and **read live CHOP channel values** — that last
one is how we verify.

Before building, confirm the bridge is alive (`get_td_nodes` on `/project1/aart_clock`). If it 404s,
TD isn't running or the bridge component isn't cooking — ask the user to start it.

### Running Python through the bridge (`execute_python_script`)

The bridge execs at module scope and returns the value bound to a variable named **`result`**.
`print()` output and `return` statements are **not** captured.

To run a committed build script (so what executes is exactly what's on disk), exec it into a
namespace seeded with the current globals, then surface its `result`:

```python
g = dict(globals())
exec(open('/abs/path/plugins/aart-clock-td/build/sg_clock.py').read(), g)
result = g['result']
```

### Bridge gotchas (learned the hard way)

- **Unbound in the exec scope:** `me`, `absTime`, and TD type globals (`CHOP`, `baseCOMP`, etc.).
  Use `op('/abs/path')`, pass operator **type names as strings** to `.create()` (e.g.
  `parent.create('lfoCHOP', 'x')`), and filter by `child.family == 'CHOP'` instead of `type=CHOP`.
- **Imported modules don't get the injected `op` builtin.** Inside `build/sg/__init__.py` and any
  helper, use `import td; td.op(...)`.
- **`bypass` is a node flag, not a parameter** — it can't hold an expression. Make stages
  conditional via their own params instead (e.g. open a Limit's bounds wide when "off"; use a
  negligible step to disable quantize).
- **Reset a Par to constant without `ParMode`** (also unbound): copy a known-constant par's mode,
  `p.mode = otherpar.mode`.
- **State machines need cooks between changes.** A Trigger CHOP (and anything edge-driven) won't
  show a response if you change its input and read the result in the *same* bridge call — the cook
  hasn't advanced. Verify dynamic behavior across separate calls, or with the manual pulse
  (`tr.par.trigger.pulse()`).
- **Constant CHOP is not time-sliced** — changing its value is not an "edge," so it won't trigger a
  Trigger CHOP. Drive triggers with real time-sliced signals (clock pulse, divide gate, an LFO).
- **Trigger CHOP:** `threshold` is a *toggle*; the real levels are `threshup`/`threshdown` (set
  ~0.5 so a 0→1 gate crosses). Triggers on input increasing across the threshold.
- TD's incremental save can leave `dev/test-project.N.toe` strays — delete before committing.

## Build-script-first workflow

The **source of truth is the Python build script**, not the binary `.tox`. Each module is
`plugins/aart-clock-td/build/sg_<name>.py`; the `.tox` is a generated, committed artifact (commit
both). This dissolves the "binary .tox isn't diffable" problem.

- **Scripts are idempotent** — they destroy and rebuild their module so a rerun reproduces it.
- **Each script ends by assigning `result`** to a verification summary (channels, ranges, errors).
- **Verify by reading channel values** through the bridge: exact assertions for deterministic
  behavior (clock math, map transforms, divide ratios), and `sg.errors(c)` should be empty. Feel /
  stochastic behavior (LFO waveform, envelope contour, noise distribution) is eyeballed on a Trail
  CHOP — note it, don't fake an assertion.
- **`build/sg/`** is the shared helper: `sg.module()`, `sg.pfloat/pint/ptoggle/ppulse`,
  `sg.rename/merge/out/inchop/help`, `sg.arrange()` (topological layout — call it so rebuilds stay
  tidy), `sg.errors()`. Prefer it for new modules.
- **Rebuild order** (idempotent): `bootstrap.py` → `sg_clock` → `sg_phase` → `sg_map` →
  `sg_divide` → `sg_env` → `sg_lfo` → `sg_random` → `dev/build_demo.py`. See `dev/README.md`.

Modules build into the running project under **`/project1/aart_clock`** (the namespace, which is the
shipped container). The pixel-art sketch and the `p1_demo` chain live in `dev/test-project.toe`.

## Repo layout

```
plugins/touchdesigner-mcp-td/   vendored MCP bridge (don't move files inside — relative paths)
plugins/aart-clock-td/          the toolkit plugin
  build/                          build scripts (source of truth) + sg/ helper
  aart_clock.tox                  shipped container (all sg_* as sub-components; generated)
dev/                            build harness (not shipped): seed/template/test-project.toe, build_demo.py
docs/SEED-RUNBOOK.md            the seed/bootstrap boundary + how to build seed.toe
USAGE.md                        consumer guide (install, modules, walkthroughs)
projects/2026-06-09-aart-clock/ the loom plan: PLAN.md, RESEARCH.md, INTERVIEW.md, sessions/
```

## Module conventions

**Signal language — five types:** Phase (0–1 loop), Gate (0/1), **Pulse** (one-sample event —
named Pulse, *not* Trigger, to avoid colliding with TD's Trigger CHOP), Value (0–1 unipolar /
−1..1 bipolar), Vector (multi-channel Value, provisional). **Polarity is a convention on
Value/Vector**, not a separate type — modules emit one `value` channel + a Polarity param.

**Channel-naming contract:** `<role>_<scope>` for scoped channels (`phase_beat`, `pulse_wrap`), a
bare role for unscoped (`value`, `gate`, `env`, `ramp`). Wire modules by matching names.

**Module standard:** each `sg_*` is a Base COMP with `in` / `out` (In/Out CHOPs) / `params` (custom
page) / `ext` (extension) / `docs` (help) / `demo` / `internal` (the CHOP graph). CHOP-graph-first;
Python only for events/state/API, never the per-sample loop. Build on time-sliced CHOPs; never count
`me.time.frame`. Custom param names: uppercase-first, no underscores, ≤ ~12 chars (short name +
friendly label).

**Concise signal refs:** a `Select` CHOP bus at a short path is direct-indexable —
`op('/project1/clk')['beat']` beats `op('/project1/p1_demo/sg_clock/out1')['beat']`. CHOPs can't have
global `op.name` shortcuts (COMP-only); `op.clock` is set on the demo clock COMP for param access.

## Git

Solo repo — **commit directly to `main` with plain `git`** (not the loom CLI, which committed onto
the wrong base here). **Push promptly**: a `gt sync` in another session will hard-reset local `main`
to `origin/main` and discard unpushed commits (it ate the research + plan once; recovered via
`git reflog`). Commit messages: descriptive subject, body explains *why*, end with the agent
co-author trailer. Commit the build script and the regenerated `.tox` together.
