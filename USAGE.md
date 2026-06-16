# Using aart-clock

A modular signal toolkit for TouchDesigner. Patch `sg_*` modules together to drive visuals
with modular-synth concepts — clocks, phases, envelopes, modulation, mapping — without writing
custom project logic.

> Status: **v1 MVP complete** (Phase 3). All seven modules available: `sg_clock`, `sg_phase`,
> `sg_divide`, `sg_lfo`, `sg_random`, `sg_env`, `sg_map`. Remaining for v1: Phase 4 hardening
> (presets, `Version`, packaging polish).

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

### sg_lfo — periodic oscillator
A continuous LFO. Sine / Triangle / Saw / Square, on the Polarity convention, with a phase + wrap
pulse and a reset input for clock-sync.

- **Input `in1`:** a pulse to reset/align the phase (e.g. `sg_clock` `pulse_bar`). Free-running if unwired.
- **Params:** `Shape`, `Rate` (Hz), `Offset` (0-1 phase), `Polarity` (unipolar/bipolar), `Synctoinput`.
- **Outputs:** `value` (in the Polarity range), `phase` (0-1), `pulse_wrap`.
- *For random modulation (random hold/smooth), use `sg_random` — see below.*

### sg_random — randomized source
Noise-based modulation with a deterministic seed.

- **Params:** `Mode` (White Noise / Random Walk / Brownian), `Seed` (same seed → same sequence),
  `Rate` (Hz, how fast it varies), `Polarity`.
- **Output:** `value` (Polarity range).
- *v1: Chaos mode deferred (needs a stateful logistic map).*

### sg_divide — clock division / multiplication
Derives a slower or faster pulse/gate/phase from a clock. It rides the referenced clock's Time
COMP, so it's automatically tempo-locked and phase-aligned — no reset wiring.

- **Params:** `Clock` (path to the `sg_clock` module, default `../sg_clock`), `Division`,
  `Multiplication` (net period = Division / Multiplication beats), `Offset` (beats), `Gatewidth`
  (fraction of the period the gate is high).
- **Outputs:** `phase` (0-1 at the divided rate), `gate` (0/1), `pulse` (one-sample).
- *v1: Swing not yet implemented (Beat CHOP can't express uneven swing as one param).*

### sg_env — envelope generator
An ADSR envelope (wraps TD's Trigger CHOP). Feed it a gate or pulse; it outputs a shaped envelope.

- **Input `in1`:** a **time-sliced** gate/pulse (e.g. `sg_clock`'s `pulse_beat`, or `sg_divide`'s
  `gate`). NOTE: a non-time-sliced Constant won't trigger it — it needs a real signal edge.
- **Params:** `Attack`, `Decay`, `Release` (seconds), `Sustain` (level 0-1), `Mode`:
  - **AR** — attack, hold at peak while gated, release on gate-off
  - **AD** — attack then decay to zero per trigger (ignores gate length); good for percussive plucks
  - **ADSR** — full envelope
  - **Loop** — completes and re-triggers every (A+D+R) for a repeating envelope
- **Output:** `env` (0-1).

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

**Chain A — a clock-synced rhythmic envelope** (`sg_clock → sg_divide → sg_env → sg_map`; the live
`p1_demo` builds this):

1. `sg_clock` — set `Bpm`, `Play` on.
2. `sg_divide` — set its `Clock` param to the clock (`../sg_clock` if a sibling); set `Division`
   (e.g. 1 = per beat, 2 = every two beats, 4 = per bar). It's auto-locked to the clock's tempo.
3. `Select` → `gate` from `sg_divide` → into `sg_env`'s input. Set `sg_env` `Mode` to **AD** with a
   `Decay` shorter than the beat for a percussive pluck on every division.
4. `Select` → `env` from `sg_env` → into `sg_map`; shape to your range.
5. `sg_map`'s `value` is a rhythmic envelope locked to the clock — wire it to brightness, scale,
   opacity, anything. (Try pointing the noise's transform at it instead of the clock scroll.)

**Chain B — free modulation** (`sg_lfo → sg_map`, or `sg_random → sg_map`):

1. Drop `sg_lfo` (set `Shape`, `Rate`) or `sg_random` (set `Mode`, `Seed`, `Rate`).
2. `Select` → `value` → into `sg_map`; shape to your range / `Quantize` for stepped motion.
3. `value` is continuous modulation — wire it anywhere. Sync the LFO to the beat by feeding a
   clock pulse into its input, or leave it free-running.

## Referencing signals concisely

Typing `op('/project1/p1_demo/sg_clock/out1')['beat']` in every expression gets old. Two shortcuts:

- **Clock bus** — a `Select` CHOP named `clk` at `/project1` mirrors all the clock's channels, so you
  index it directly: `op('/project1/clk')['beat']`, `op('/project1/clk')['phase_bar']`. (Make your own
  bus for any signal you reference a lot — a `Null`/`Select` CHOP at a short path is a CHOP, so the
  `['channel']` access just works. TD can't give a *CHOP* a global `op.name` shortcut, only COMPs.)
- **Module shortcut** — the demo clock has a Global OP Shortcut, so `op.clock` reaches the module
  from anywhere (handy for params: `op.clock.par.Bpm`). Set one via a COMP's Common page →
  *Global OP Shortcut*.

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
