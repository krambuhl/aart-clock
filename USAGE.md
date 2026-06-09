# Using aart-clock

A modular signal toolkit for TouchDesigner. Patch `sg_*` modules together to drive visuals
with modular-synth concepts — clocks, phases, envelopes, modulation, mapping — without writing
custom project logic.

> Status: **v1 Phase 1** (foundation). Modules available: `sg_clock`, `sg_phase`, `sg_map`.
> `sg_divide`, `sg_env`, `sg_lfo`, `sg_random` arrive in Phases 2-3. This guide grows with them.

## Install

Drop the toolkit into your project:

1. Drag **`plugins/aart-clock-td/aart_clock.tox`** into your network. It's a container holding
   each `sg_*` module as a sub-component.
2. Copy the module(s) you want (e.g. `sg_clock`, `sg_map`) out of the container into your network,
   or use them in place.

You don't need the build pipeline or the MCP bridge to *use* the toolkit — those are for
*developing* it (see "Building" below).

## Signal language

Every module speaks one language — five channel-convention types:

| Type | Range | Meaning |
|------|-------|---------|
| Phase | 0-1 | normalized looping time |
| Gate | 0/1 | sustained binary state |
| Pulse | one-sample 1 | single-frame event (NOT TD's Trigger CHOP, which is an envelope) |
| Value | 0-1 unipolar / -1..1 bipolar | continuous scalar; polarity is a convention, not a type |
| Vector | xyz | multi-channel Value (forward-looking; not produced in v1) |

**Channel names** follow `<role>_<scope>` when scoped (`phase_beat`, `pulse_wrap`) and a bare role
when not (`value`, `phase`, `ramp`). Wire modules by matching these names.

## Modules

### sg_clock — master transport
The heartbeat. A self-contained BPM clock (internal Time COMP + Beat CHOPs, runs independently of
the global timeline).

- **Params:** `Bpm`, `Play`, `Reset`, `Barbeats` (beats per bar), `Phrasebars` (bars per phrase).
- **Outputs:** `beat` / `bar` / `phrase` (counters); `phase_beat` / `phase_bar` / `phase_phrase`
  (0-1 ramps); `pulse_beat` / `pulse_bar` / `pulse_phrase` (one-sample pulses).

### sg_phase — off-grid phase (chainable)
A free-running normalized phase at an arbitrary rate. Free-running on its own, but wire a pulse
into its **input** to align it to a clock — that's what makes `clock → phase → map` a real chain.

- **Input `in1`:** a pulse (e.g. `sg_clock`'s `pulse_bar`). Each pulse re-zeros the phase, locking
  its loop to the clock. Leave unwired for pure free-running.
- **Params:** `Rate` (Hz), `Offset` (0-1 phase offset), `Synctoinput` (reset on input pulse; on by default).
- **Outputs:** `phase` (0-1), `ramp` (alias of phase), `pulse_wrap` (one-sample pulse each cycle).

### sg_map — signal shaping
Remap and shape any Value.

- **Params:** `Inlow`/`Inhigh` -> `Outlow`/`Outhigh` (scale + offset, and polarity: set the output
  range to `-1..1` for bipolar), `Invert`, `Clamp` (+`Clamplow`/`Clamphigh`), `Quantize` (+`Steps`).
- **Output:** `value`.

## Walkthroughs (Phase 1 slice)

**The chain — `sg_clock → sg_phase → sg_map`** (see the live `p1_demo` in `dev/test-project.toe`):

1. Drop `sg_clock`. Set `Bpm` (e.g. 120), `Play` on.
2. `Select` CHOP -> pick `pulse_bar` from `sg_clock/out1`. Wire it into `sg_phase`'s **input** —
   the phase now resets every bar, locked to the clock.
3. On `sg_phase`, set `Rate` so the loop matches the bar (at 120 BPM a bar is 2s -> `Rate` 0.5)
   for a clean one-sweep-per-bar; or pick any rate for polyrhythmic feel against the reset.
4. `Select` -> pick `phase` from `sg_phase/out1` into `sg_map`. Set `Outlow`/`Outhigh` to your
   range (e.g. 0-360 for rotation, or `-1..1` for bipolar modulation). Optionally `Quantize`.
5. `sg_map`'s `value` output is a bar-synced sweep in your range — wire it to any visual parameter.

**Shortcuts off the same spine:**
- Skip `sg_phase` and feed a `sg_clock` `phase_*` ramp straight into `sg_map` for grid-locked phase.
- Leave `sg_phase`'s input unwired for free-running modulation (its `pulse_wrap` fires once per cycle,
  handy for one-shots).

## Building (developers)

aart-clock is built **build-script-first** through the TouchDesigner MCP bridge. The Python build
scripts are the source of truth; the `.tox` is generated.

- `dev/seed.toe` — bridge-only seed (see `docs/SEED-RUNBOOK.md`).
- `plugins/aart-clock-td/build/bootstrap.py` — builds the `aart_clock` namespace + module template.
- `plugins/aart-clock-td/build/sg_*.py` — one build script per module.
- `plugins/aart-clock-td/build/sg/` — the shared build-helper library.

Run a build script via the bridge:

```python
g = dict(globals())
exec(open('/abs/.../build/sg_clock.py').read(), g)
result = g['result']   # the script's verification summary
```
