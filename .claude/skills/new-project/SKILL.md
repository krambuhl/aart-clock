---
name: new-project
description: Generate an aart-clock signal program from a natural-language description — prefabbed from the sg_* toolkit, built and verified through the TouchDesigner MCP bridge. Use when the user describes a signal/visual behavior they want and asks to make, build, or generate a program/patch/project from it.
---

# /new-project — generate a signal program from a description

Turn a natural-language description of desired signal behavior into a **verified, idempotent build
script** that prefabs a program from the aart-clock `sg_*` toolkit, built through the TouchDesigner
MCP bridge.

The output is a `dev/build_demo.py`-shaped script — read that file first; it is the canonical example
of everything below (copying modules out of the namespace, wiring with Select CHOPs, setting params,
returning a verification `result`). A generated program is just another one of those.

This skill **generates, builds, and verifies. It does not commit.** Stop at the report; the user
commits when a program is good enough to keep.

---

## Step 0 — Confirm the bridge is alive

Before anything, confirm the running TouchDesigner instance is reachable (per the project CLAUDE.md):

```
get_td_nodes on /project1/aart_clock
```

If it 404s or the namespace is missing, TD isn't running or the library isn't built — stop and ask
the user to start TD / run the bootstrap chain (`bootstrap.py → sg_clock → …`, see `dev/README.md`).
Do not try to build a program against a missing library.

---

## Step 1 — Parse the description into a signal graph

Map the description onto modules. Work **hybrid**: start from a canonical chain when one fits, and
compose beyond it using the module catalog + channel contract when it doesn't. Don't force-fit a
description into a recipe that doesn't match — the recipes are backbones, not a closed menu.

### Canonical chains (trusted backbones)

| Chain | Shape | Use when the description wants… |
|---|---|---|
| **Spine** | `sg_clock → sg_phase → sg_map` | a clock-locked sweep/ramp in a range (rotation, position, a one-sweep-per-bar value) |
| **Grid spine** | `sg_clock → sg_map` (feed a `phase_*` ramp) | a grid-locked phase with no off-grid rate — simpler than the spine |
| **Chain A** | `sg_clock → sg_divide → sg_env → sg_map` | a rhythmic, percussive envelope — pulses/plucks on a beat division (strobe, pulse, throb) |
| **Chain B (lfo)** | `sg_lfo → sg_map` | continuous free or beat-synced modulation with a waveform (breathing, wobble, sway) |
| **Chain B (random)** | `sg_random → sg_map` | noisy / wandering / stochastic modulation (flicker, drift, jitter) |

Sync any free module to the clock by wiring a clock pulse (e.g. `pulse_bar`) into its input.

### Module catalog (for composing off-recipe)

- **sg_clock** — master transport. Params `Bpm`, `Play`, `Reset`, `Barbeats`, `Phrasebars`.
  Outputs: counters `beat`/`bar`/`phrase`; ramps `phase_beat`/`phase_bar`/`phase_phrase`; pulses
  `pulse_beat`/`pulse_bar`/`pulse_phrase`.
- **sg_phase** — off-grid normalized phase. Input: a pulse to re-zero (clock-lock). Params `Rate` (Hz),
  `Offset`, `Synctoinput`. Outputs `phase`, `ramp`, `pulse_wrap`.
- **sg_divide** — clock division/multiplication; rides the clock's Time COMP (auto tempo-locked).
  Params `Clock` (path, default `../sg_clock`), `Division`, `Multiplication`, `Offset`, `Gatewidth`.
  Outputs `phase`, `gate`, `pulse`.
- **sg_lfo** — periodic oscillator. Input: pulse to reset. Params `Shape`, `Rate`, `Offset`,
  `Polarity`, `Synctoinput`. Outputs `value`, `phase`, `pulse_wrap`.
- **sg_random** — noise source. Params `Mode` (White Noise / Random Walk / Brownian), `Seed`, `Rate`,
  `Polarity`. Output `value`.
- **sg_env** — ADSR envelope (wraps TD Trigger CHOP). Input: a **time-sliced** gate/pulse. Params
  `Attack`, `Decay`, `Release`, `Sustain`, `Mode` (AR / AD / ADSR / Loop). Output `env`.
- **sg_map** — shaping. Params `Inlow`/`Inhigh` → `Outlow`/`Outhigh`, `Invert`, `Clamp`
  (+`Clamplow`/`Clamphigh`), `Quantize` (+`Steps`). Output `value`.

### Signal-language contract (how modules connect)

Five types: **Phase** (0–1 loop), **Gate** (0/1), **Pulse** (one-sample event), **Value** (0–1 unipolar
/ −1..1 bipolar), **Vector** (multi-channel, not in v1). Channels are named `<role>_<scope>` when scoped
(`phase_beat`, `pulse_wrap`) or a bare role when not (`value`, `gate`, `env`, `ramp`). **Wire modules
by matching channel names** — pick the named channel with a Select CHOP and connect it to the next
module's input. Two hard rules from the field notes:

- **sg_env needs a real time-sliced edge** — a Constant won't trigger it. Feed it a clock pulse or a
  divide gate, never a static value.
- **Polarity is a convention on Value**, set via the module's `Polarity` param + the map output range —
  not a separate signal type.

---

## Step 2 — Name it (kebab file, underscore node, confirm on collision)

Derive a short slug from the description (`"a punchy strobe on every bar"` → `strobe-bar`). The slug
appears in two forms, and they are **not** the same:

- **Script filename** — kebab-case: `dev/programs/strobe-bar.py` (matches repo file convention).
- **TD node name** — underscore: container `/project1/strobe_bar`, bus `/project1/strobe_bar_bus`.
  **TouchDesigner node names cannot contain dashes** (`.create()` throws "Illegal node name"). Convert
  the kebab slug to underscores for every operator name. `NAME = slug.replace('-', '_')`.

**Check for collision first.** If `dev/programs/<slug>.py` already exists, surface it and ask:
overwrite (rebuild — the script is idempotent so this is clean) or pick a new name. Never silently
clobber.

---

## Step 3 — Write the build script

Write to `dev/programs/<slug>.py`. Mirror `dev/build_demo.py` exactly. The script must:

1. **Header docstring** recording the original description verbatim + the chosen chain.
2. **Be idempotent** — destroy `/project1/<slug>` if it exists, then rebuild.
3. **Copy modules out of the namespace** (`/project1/aart_clock`) into the container — programs
   *consume* the library, they don't build into it. Never build into `/project1/aart_clock`.
4. **Wire with Select CHOPs** picking named channels (the `pick_gate`/`pick_env` pattern in build_demo).
5. **Set params** from the description's intent.
6. **Add a short Select bus** at `/project1/<slug>-bus` mirroring the output, so the signal is
   direct-indexable: `op('/project1/<slug>-bus')['value']`.
7. **Add a Trail CHOP** (`trail1`) on the output so there's a live contour to eyeball in the refine loop.
8. **Call `sg.arrange(container)`** so the graph lays out tidily on rebuild.
9. **End by assigning `result`** — a verification dict (see Step 5).

### Skeleton

```python
"""<slug>.py — generated aart-clock program (dev harness, not shipped).

Description: <the user's verbatim description>
Chain: <e.g. sg_clock -> sg_divide -> sg_env -> sg_map>

Run via the bridge:
    g = dict(globals()); exec(open(<this>).read(), g); result = g['result']
Idempotent: destroys and rebuilds /project1/<slug>.
"""

import sys
BUILD = '/Users/krambuhl/Sites/aart-clock/plugins/aart-clock-td/build'
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)
import sg  # noqa: E402

NS = '/project1/aart_clock'
NAME = '<slug>'
PROG = '/project1/' + NAME


def build():
    ns = op(NS)
    if op(PROG):
        op(PROG).destroy()
    prog = op('/project1').create('baseCOMP', NAME)
    prog.comment = '<description> | <chain>'
    prog.color = (0.2, 0.5, 0.5)

    def cp(modname, x, y):
        n = prog.copy(ns.op(modname)) or prog.op(modname)
        n.nodeX, n.nodeY = x, y
        return n

    # --- copy + configure modules (see build_demo.py build_chain) ---
    # clk = cp('sg_clock', ...); clk.par.Bpm = ...
    # ... wire with Select CHOPs picking named channels ...

    # --- output bus + trail (always) ---
    out_src = ...  # the final module's out1
    bus = op(PROG + '-bus') or op('/project1').create('selectCHOP', NAME + '-bus')
    bus.par.chop = out_src.path
    bus.par.channames = '*'
    bus.comment = "program bus - op('%s-bus')['value']" % PROG
    trail = prog.create('trailCHOP', 'trail1')
    out_src.outputConnectors[0].connect(trail.inputConnectors[0])

    sg.arrange(prog)
    return prog, out_src


def run():
    prog, out_src = build()
    return {
        'program': prog.path,
        'nodes': sorted(c.name for c in prog.children),
        # deterministic assertions (ranges, ratios, map math):
        # 'value_range': [round(...), round(...)],
        # feel/stochastic — note, don't fake an assertion:
        'feel': 'eyeball <waveform/contour/distribution> on trail1',
        'bus': prog.path + '-bus',
        'errors': sg.errors(prog),
    }


result = run()
```

### Optional: visual binding (only when the description names a visual)

**Default is signals-only** — the toolkit's identity is "generates and shapes signals, no rendering."
Stop at the output bus + Trail and go no further **unless the description explicitly names a visual
target** (e.g. "drive the pixel sketch's scroll", "pulse a Circle TOP's radius"). Only then, wire the
output into that target — `build_demo.py`'s `bind_sketch_noise` is the pattern: **guarded** (no-op if
the target isn't present) and **reported** in `result` (`'bound': True/False`). Never reach for a
visual the user didn't ask for.

---

## Step 4 — Build it through the bridge

Run the committed script so what executes is exactly what's on disk (project CLAUDE.md pattern):

```python
g = dict(globals())
exec(open('/Users/krambuhl/Sites/aart-clock/dev/programs/<slug>.py').read(), g)
result = g['result']
```

Watch the bridge gotchas: build dynamic/edge-driven behavior across separate calls (a Trigger CHOP
won't respond in the same cook), drive triggers with real time-sliced signals, and remember imported
helpers use `import td; td.op(...)`.

---

## Step 5 — Verify (split deterministic vs feel)

Honor the project's hard line:

- **Deterministic behavior** (clock math, divide ratios, map ranges/transforms) → **exact assertions**
  in `result` (read channel values, assert the range/ratio). And `sg.errors(prog)` **must be empty**.
- **Feel / stochastic behavior** (LFO waveform, envelope contour, noise distribution) → **eyeball it on
  `trail1`** and note it in `result`. Do **not** fake an assertion for feel.

If `errors` is non-empty or an assertion fails, fix the script and rebuild before reporting.

**Catching transients from the bridge.** A Trail CHOP only cooks when its viewer is active in the TD
UI — `trail1` reads 0 samples over the bridge, so it's for the *user's* eyes, not readback. To prove a
short-lived event (a punchy env, a brief gate) actually fires, poll the output value across **separate**
bridge calls (one cook per call — same-call reads don't advance time). If the event is too fast to
catch (e.g. a few-millisecond AD spike), temporarily widen it (stretch `Decay`, raise `Gatewidth`),
catch the nonzero peak across polls, then **restore the original value**. Report what you caught; never
fake the feel assertion.

---

## Step 6 — Report, then offer the refine loop

Report concisely and stop:

```
Built /project1/<slug>   (errors: none)
Script:  dev/programs/<slug>.py
Chain:   <chain>
Ref:     op('/project1/<slug>-bus')['value']
Watch:   trail1  (<what to eyeball>)
```

Then offer to **refine**: tweak params, re-wire, swap a module, retune for feel — re-running the
idempotent script each time. Loop until the user accepts. If the first build already nails it, accept
immediately; force nothing.

**Do not commit.** The user decides when a program is worth keeping and commits it themselves.

---

## Guardrails

- Never build into `/project1/aart_clock` (the shipped library) — programs are siblings at `/project1/<slug>`.
- Never auto-wire a visual the description didn't name.
- Never fake an assertion for feel-based behavior.
- Never commit.
- TD's incremental save can leave `dev/*.[0-9]*.toe` strays. They're gitignored and idempotent — leave them be; don't flag, delete, or mention them.
