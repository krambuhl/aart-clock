# PLAN — aart-clock

A modular timing, rhythm, modulation, and signal-processing toolkit for TouchDesigner. Composable `sg_*` modules let visual systems be driven with concepts borrowed from modular synthesis. This project generates and shapes signals only — visual rendering is explicitly out of scope.

## Context

Research foundation: [RESEARCH.md](./RESEARCH.md) — a fact-anchored dossier on *how* to build the `sg_*` library in TouchDesigner, cited against `docs.derivative.ca`. The plan below treats those findings as input.

aart-clock models time, rhythm, envelopes, and modulation as first-class, patchable building blocks — the way Eurorack, Monome, and OXI One treat control voltage. The artist composes reusable signal networks (`Clock → Phase → Gates → Pulses → Envelopes → Modulation → Mapping → Visual`) instead of wiring visual behavior directly. The whole toolkit hangs off one shared signal language, so the foundation phase that defines that language — and the reproducible build pipeline that produces it — is the most load-bearing work in the plan.

### Build & verification substrate (TouchDesigner MCP)

The [touchdesigner-mcp](https://github.com/8beeeaaat/touchdesigner-mcp) server bridges this agent to a running TouchDesigner instance over HTTP (`127.0.0.1:9981`) via the `mcp_webserver_base.tox` component. Verified live this session against **TD 099.2023.12480** (macOS): the bridge can create/destroy operators, get/set parameters, run arbitrary Python, and — critically — **read live CHOP channel values** (probe: an LFO CHOP read back at 0.407, time-sliced, sub-ms cook). This capability reshapes the project from "plan-then-hand-off" into a reproducible, agent-driven build pipeline with in-session verification.

Two consequences drive the architecture:

1. **Source of truth is a Python build script, not a binary.** Because networks can be constructed programmatically through the bridge, each module is authored as a committed Python build script that constructs its network via the TD API; the `.tox` is a generated artifact. This dissolves the externalize-to-text problem (the script *is* the diffable text) and makes every module reproducible — rerun the script, get an identical network.
2. **Verification is live and continuous, not deferred.** Since channel values are readable in-session, correctness is checked as modules are built rather than punted to a future harness. (The one limit: the bridge needs a *running* instance, so unattended/headless CI remains future work — see Out of scope.)

### Build pipeline & repo structure

The pipeline is a reproducible chain: **Python build scripts → (executed via the MCP bridge) → `template.toe` + module `.tox` artifacts**, all committed.

```
build/
├── bootstrap.py        # reproduces the aart_clock substrate (namespace, module template, conventions) onto the seed
├── sg/                 # the thin 'sg' build-helper library (extracted in Phase 1 — see Module standard)
├── sg_clock.py         # per-module build scripts (raw TD API → sg helper once extracted)
├── sg_phase.py
└── ...
seed.toe               # minimal committed seed: ONLY the MCP bridge (mcp_webserver_base.tox)
template.toe           # committed result of running bootstrap.py on seed.toe — the reproducible base
tox/                   # committed generated .tox artifacts (the distributable palette)
docs/                  # usage docs + SEED-RUNBOOK.md (manual steps to rebuild seed.toe)
USAGE.md               # project-level integration guide (see below)
```

- **`seed.toe`** carries only the MCP bridge (whose relative-path/manual-import constraint makes it the one thing not worth scripting). Committed as a trusted minimal binary. It is the one un-scripted link in the chain, so its construction is captured as a committed, followable **`docs/SEED-RUNBOOK.md`** (the manual steps to rebuild the seed from a blank project + the vendored bridge `.tox`). The reproducibility claim is therefore scoped precisely: *reproducible from `seed.toe` + scripts, where `seed.toe` itself is reproducible by the runbook* — not "fully reproducible from text alone."
- **`bootstrap.py`** reproduces everything else on top of the seed via the bridge — the `/project1/aart_clock` namespace base, the module template scaffold, and the shared conventions. `template.toe` is the committed output of `bootstrap` on `seed`. The exact seed/bootstrap boundary (what must live in the seed vs what bootstrap can place) is settled as the first deliverable of Phase 1, before the "reproducible" exit condition can be checked.
- Modules are built into the **running project under `/project1/aart_clock`**; the existing pixel-art sketch (`content → pixel_up → out_square`) stays in the project as a real demo *consumer* of the signals.
- **Both** the build script (source of truth, reviewed via its diff) **and** the generated `.tox` (distributable release artifact) are committed. The `.tox` lets a consumer drop a module into their project without running the build; the script is what we actually review and reproduce from.

### Signal language (the shared contract)

Five core signal types, each a normalized CHOP channel convention:

| Type | Range | Description |
|------|-------|-------------|
| Phase | 0–1 | Normalized looping time |
| Gate | 0/1 | Binary sustained state |
| Pulse | one-sample pulse | Single-frame event |
| Value | 0–1 (unipolar) / −1..1 (bipolar) | Continuous scalar, carries a polarity convention |
| Vector | xyz | Multi-channel Value (provisional — see below) |

**Polarity is a convention on Value/Vector, not a separate type.** Unipolar (0–1) is the default; bipolar (−1..1) where sign matters (LFO output, modulation depth). Modules emit a single `value` channel with a **Polarity param** (unipolar/bipolar) rather than two range-variant channels; `sg_map` owns conversion. The channel-naming contract carries a polarity marker readable downstream (a channel suffix and/or an Info-CHOP-readable flag) so polarity travels with the signal. (This reconciles the README's six-type list — which included "Color" — with the plan brief's. Color is a visual concern → Future Work; README updated in Phase 4.)

**"Pulse," not "Trigger."** The single-frame-event type is named **Pulse** to avoid a permanent collision with TouchDesigner's native **Trigger CHOP**, which is an ADSR envelope generator (and which `sg_env` is built *on*). A Pulse is produced by an LFO CHOP `Pulse` type or a Logic CHOP rising/falling edge, kept in time-sliced CHOP-land (RESEARCH §2). Channels are `pulse_*`.

**Vector is provisional.** No v1 module produces a Vector — only `sg_map` passes one through — so the convention is forward-looking and untested-by-construction in v1.

### Module standard

Every `sg_*` module is a **Base COMP** (headless signal shell) **authored as a Python build script** and following one internal structure:

```
sg_<name>
├── in        # In CHOPs (left connectors, signal in)
├── out       # Out CHOPs (right connectors, signal out)
├── params    # custom parameter pages
├── ext       # XxxExt Python extension class (API / help)
├── docs      # description + help text
├── demo      # example patch (doubles as a verification + usage artifact)
└── internal  # the CHOP-graph implementation
```

Standard conventions, grounded in RESEARCH §4:

- **Build-script-first.** The module's canonical form is its `build/sg_<name>.py`. The first 2–3 modules are written against the **raw TD Python API** (`op().create()`, `.par`, `.connect`); once the repeated patterns surface (In/Out CHOP setup, channel naming, the sync/reset/wrap sub-chain, param shortening), they are extracted into a thin **`sg` build-helper library** (`build/sg/`) that later scripts call. The helper is extracted on evidence (rule of three), not designed up front.
- **CHOP-graph-first.** Continuous per-sample math lives in native, time-sliced CHOP networks. Python (extension / CHOP Execute DAT) is reserved for event reactions, state, and the API surface — never the hot per-sample loop (RESEARCH §5). The one sanctioned exception is `sg_random`'s reproducible walk/brownian/chaos, which runs a seeded Python loop over a known time base (RESEARCH §6).
- **Frame-rate independence comes from time slicing, not frame counting** (RESEARCH §1).
- **Canonical channel-naming contract.** The foundation pins per-type channel names + ordering: `<role>_<scope>` for scoped channels (`phase_beat`, `pulse_wrap`), bare role for unscoped (`value`, `gate`, `env`, `ramp`). Value/Vector channels carry the polarity marker.
- **Shared sync/reset/wrap-detect primitive.** `sg_clock`, `sg_phase`, `sg_lfo`, `sg_divide` share a Reset behavior + the wrap-detect chain (Logic falling-edge on a 0→1 ramp → `pulse_wrap`) + a Free/Beat/Bar/Phrase **Sync mode** convention. Lives in the `sg` helper / template as one definition, not four.
- **Custom-param naming constraints** (RESEARCH §4): uppercase-first, no underscores, ≤ ~10–12 chars. The standard fixes the shortening algorithm (lead with scope noun: `BeatsPerBar` → `BarBeats`, `BarsPerPhrase` → `PhraseBars`) + free-form labels, and reuses the COMP's built-in lowercase `play`.
- **Verification baked into the build script.** Where the module's behavior is deterministic, its build script (or a sibling `verify` block) sets known inputs, advances to known frames, and asserts on output channel values read back through the bridge. Stochastic/feel behavior is scoped manually (see Verification).
- Each module carries embedded **help text** (the Pulse-vs-Trigger-CHOP note lives here). `Version` string + preset support are **deferred to Phase 4** (conventions unresolved — see Open questions).

### Usage & integration documentation (a first-class deliverable)

The success criterion is that an artist builds BPM-synced animation, rhythmic events, generative modulation, and envelope-driven motion **without writing custom project logic** — achievable only if *how to use aart-clock inside a TouchDesigner project* is clearly documented. Usage docs are a graded deliverable, threaded through every phase, at two altitudes:

- **Per-module usage** — every module's `docs`/`demo` answers "how do I wire this into my project": named inputs/outputs, params, a minimal worked patch. The `demo` patch doubles as verification + copy-paste starting point.
- **Project-level integration guide** (`USAGE.md`) — installing the `sg_*` family into a TD project (drop the committed `.tox` / palette), the signal-language quick reference (five types + polarity + channel-naming cheat sheet), how signals flow between modules, **the build pipeline itself** (how to reproduce `template.toe` from seed + run module scripts), and **the two success-criteria chains as step-by-step walkthroughs**. This is the artifact that proves "no custom project logic required."

The guide is seeded in Phase 1 and completed in Phase 4.

## Scope

**In (v1 = the 7-module MVP + the reproducible build pipeline):**

- The build pipeline: `seed.toe`, `bootstrap.py`, `template.toe`, the `sg` build-helper library, `tox/` artifact policy.
- Layer 1 — Timing: `sg_clock`, `sg_phase`, `sg_divide`
- Layer 2 — Generation: `sg_lfo`, `sg_random`
- Layer 3 — Shaping: `sg_env`, `sg_map`
- The shared signal language + module standard + module template.

v1 is complete when both success-criteria patch chains run end to end:

```
sg_clock → sg_phase → sg_divide → sg_env → sg_map      (Chain A)
sg_lfo → sg_map                                         (Chain B)
```

with all resulting signals available to drive arbitrary TouchDesigner visual systems, and the whole library reproducible from `seed.toe` + the build scripts (`seed.toe` itself reproducible via `docs/SEED-RUNBOOK.md`).

**Deferred (v1.1, fast-follow):**

- `sg_function` (custom curve editor — heavier UI; LFO CHOP Source Wave covers the simple case, RESEARCH §3)
- `sg_logic` (gate/pulse boolean processing — Logic CHOP maps ~1:1 but Latch has no native S-R, RESEARCH §2)

**Out (Future Work — separate plans/projects):**

- **Unattended / headless CI** — the MCP bridge needs a running instance, so true headless verification (load `.tox`, step frames, assert, no GUI) is its own effort and its own `/loom-plan`.
- Visual generators, color systems, instancing systems, scene composition
- MIDI, OSC, Ableton Link, DMX
- Performance tooling

## Phases

The build is a sequence of **vertical slices**: each phase ends with a runnable patch and passing verification, widening the toolkit rather than stacking horizontal layers. Cadence is one commit per module directly to `main` (solo repo — no PR ceremony); **each module commit pairs its build script (source) with the regenerated `.tox` artifact.** The pipeline/foundation lands as its own commit first within Phase 1.

### Phase 1 — Foundation: reproducible pipeline + first vertical slice (`sg_clock → sg_phase → sg_map`)

The build pipeline, signal language, and module standard, proven by the thinnest real chain.

- **Settle the seed/bootstrap boundary first** (gated deliverable) — empirically determine, via the bridge, what must live in `seed.toe` (the bridge + anything bootstrap can't place) vs what `bootstrap.py` can construct. This resolves before the rest of Phase 1, because the phase's "reproducible" exit condition is otherwise uncheckable. Capture the seed-construction steps in **`docs/SEED-RUNBOOK.md`**.
- **`seed.toe`** committed (MCP bridge + whatever the boundary requires) and **`bootstrap.py`** authored — reproduces the `/project1/aart_clock` namespace, module template scaffold, channel-naming contract, and the sync/reset/wrap convention onto the seed. `template.toe` committed as bootstrap's output.
- **Signal-language contract** documented (five types + polarity + channel-naming rule).
- `sg_clock` (build script) — master transport on a **Time COMP + Beat CHOP** (not Timer CHOP, RESEARCH §1), the **sole beat-synced phase source**. Outputs: `beat`/`bar`/`phrase` counters, `phase_beat`/`phase_bar`/`phase_phrase` ramps, `pulse_beat`/`pulse_bar`/`pulse_phrase`. Params: BPM, play (built-in), Stop, Reset, BarBeats, PhraseBars.
- `sg_phase` (build script) — the **off-grid phase specialist**: normalized looping phase at an arbitrary rate (free Hz or beat-relative) decoupled from the grid, with offset + Reset (alignable to a clock pulse). Outputs: `phase`, `ramp`, `pulse_wrap`.
- `sg_map` (build script) — scale, offset, clamp, invert, quantize, curve; owns unipolar↔bipolar conversion.
- **Extract the `sg` build-helper library** from the patterns the three scripts share.
- **Verification:** live MCP assertions on `sg_clock` beat timing and `sg_map` deterministic transforms (known input → known frame → asserted channel value); Trail/Info scope on `sg_phase` ramp feel.
- **Integration guide seeded** — `USAGE.md` with install, signal-language reference, the build-pipeline reproduction steps, and the `sg_clock → sg_phase → sg_map` walkthrough.
- **Exit:** the seed/bootstrap boundary is settled and `SEED-RUNBOOK.md` is followable; `sg_clock → sg_phase → sg_map` runs and passes verification; the library is reproducible from `seed.toe` + scripts; the `sg` helper exists; a new user can follow the guide to a working patch.

### Phase 2 — Complete Chain A (`sg_divide`, `sg_env`)

- `sg_divide` (build script via `sg` helper) — clock division/multiplication, offset, swing (Beat CHOP Multiples/Shift, RESEARCH §1). Outputs: `phase`, `gate`, `pulse`. **Swing prototyped first** (see Risks).
- `sg_env` (build script) — envelope wrapping the **Trigger CHOP** (TD's native ADSR engine, RESEARCH §7). Modes: AR/AD/ADSR/Looping. Inputs: `gate`, `pulse`. Output: `env`.
- **Verification:** live assertions on `sg_divide` ratios (deterministic); Trail/Info scope on `sg_env` envelope shape.
- **Usage docs:** per-module `docs`/`demo`; integration guide gains the full Chain A walkthrough.
- **Exit:** full Chain A runs end to end, verified, and documented.

### Phase 3 — Generation sources (`sg_lfo`, `sg_random`)

- `sg_lfo` (build script) — oscillator on the LFO CHOP. Shapes: Sine/Triangle/Saw/Square/Random Hold/Random Smooth. Sync mode, phase offset, reset. Outputs: `value` (Polarity param), `phase`, `pulse_wrap`.
- `sg_random` (build script) — White Noise + smooth via **Noise CHOP** (`Seed`); Walk/Brownian/Chaos via **seeded Python over a known time base** (RESEARCH §6). Deterministic seeding via `tdu.rand(seed)`. Outputs: `value` (Polarity param).
- **Verification:** live assertion that `sg_random` is deterministic per seed (same seed + same frame → same value, read twice through the bridge); Trail/Info scope on `sg_lfo` waveform feel + random distribution.
- **Usage docs:** per-module `docs`/`demo`; integration guide gains the Chain B walkthrough.
- **Exit:** Chain B `sg_lfo → sg_map` runs and is verified; both chains live. **MVP achieved.**

### Phase 4 — v1 hardening + packaging

- **`Version` string convention + preset support pass** across all seven modules (resolves two Open questions).
- Help-text + `docs`/`demo` completeness; **palette packaging** of the `sg_*` `.tox` family in `tox/`.
- **Reproducibility audit:** rebuild `seed.toe` from `SEED-RUNBOOK.md`, run `bootstrap.py` + all module scripts via the bridge, and confirm the result is **functionally equivalent** — every module's verification assertions pass and both chains run — not byte-identical (TD `.tox`/`.toe` binaries embed timestamps/IDs and won't reproduce byte-for-byte; the build script is the source of truth, the `.tox` a regenerated artifact). This is the proof the pipeline is genuinely reproducible.
- **Integration guide completion** — both chains finalized as polished walkthroughs; install/quick-reference current with the final API.
- README reconcile (drop Color, document polarity, Trigger→Pulse).
- **Exit:** v1 packaged; the entire library reproducible from text + seed; both chains verified.

## Dependencies

- **Build-time substrate:** a running TouchDesigner (099.2023.12480) with the MCP bridge (`mcp_webserver_base.tox`) loaded, and this agent connected via the touchdesigner-mcp server. Required to build/verify any module.
- All modules depend on the **Phase 1 foundation** (pipeline + signal language + channel contract + template + `sg` helper).
- `sg_phase` optionally takes an `sg_clock` pulse for Reset alignment; otherwise independent.
- `sg_divide` depends on `sg_clock`.
- `sg_env` needs a gate/pulse source (`sg_clock` or `sg_divide`).
- `sg_map` depends only on the signal-type/channel contract.
- `sg_lfo` sync mode depends on `sg_clock`; free-run independent.
- `sg_random` independent (seeded).
- Native operators relied on: Time COMP, Beat CHOP, LFO CHOP, Logic CHOP, Trigger CHOP, Noise CHOP, Info CHOP, Trail CHOP; `tdu` Python module.

## Verification

Channel values are readable live through the MCP bridge, so verification is continuous and per-phase, not deferred. The gate is **hybrid** (RESEARCH §9 + the live-bridge capability proven this session):

- **Live MCP assertions for deterministic behavior** — clock beat/bar/phrase timing, `sg_map` scale/clamp/quantize/invert, `sg_divide` ratios, `sg_random` per-seed determinism. The build/verify script sets known inputs, advances the timeline to known frames, reads the output channel via the bridge, and asserts. (Time-slicing means a free-running read drifts per cook, so assertions pin the frame; this is why the gate is per-behavior, not blanket.)
- **Manual Trail CHOP + Info CHOP scopes for stochastic / feel behavior** — LFO waveform shape, random distributions, envelope contour — with a screenshot captured in `docs`. The pass criterion is explicit, not "a human glanced at it": the scope must **match the expected shape documented in the module's `demo`/help text** (e.g. "sine sweeps smoothly −1..1 at the set frequency", "AR envelope rises in attack, falls in release, no sustain plateau"). The documented expected shape is written *before* the scope is judged.
- **Per-module `demo` patch + `USAGE.md` walkthroughs** are graded deliverables: a phase is not done until a new user could follow its docs to the working patch it exits on.
- **Reproducibility is itself verified** in Phase 4: rebuild the whole library from `seed.toe` (per `SEED-RUNBOOK.md`) + scripts and confirm functional equivalence — passing per-module assertions + passing chains — rather than byte-identical binaries.

Unattended/headless CI (no running GUI) is out of scope for v1 — it needs a different harness and is its own future plan.

## Risks

- **MCP bridge is a live-instance dependency** — building/verifying needs TD running with the bridge loaded; a stale or moved `mcp_webserver_base.tox` breaks the connection (its relative-path constraint). *Mitigation:* `seed.toe` pins the bridge in a known-good state; bootstrap never moves it; reconnect/reimport + restart on version mismatch (documented).
- **Time-sliced reads are nondeterministic per cook** — a naive channel read drifts frame to frame. *Mitigation:* assertions pin the timeline to known frames and only assert on deterministic behavior; stochastic/feel signals are scoped, not asserted.
- **TD / MCP version drift** — the server enforces semver; a TD or server upgrade can break the bridge. *Mitigation:* pin TD 099.2023.12480 in the plan; treat a bridge break as a reimport-`.tox`-and-restart runbook step.
- **Brownian/Chaos reproducibility** — Noise CHOP Brownian/Harmonic can't be 1-sample-limited under time slicing (RESEARCH §6). *Mitigation:* `sg_random` uses Noise CHOP for white/smooth, seeded Python for reproducible walk/brownian/chaos; the per-seed determinism is an asserted check in Phase 3.
- **Swing in `sg_divide`** — Beat CHOP may not express uneven swing as one param (RESEARCH open Qs). *Mitigation:* prototype swing first thing in Phase 2; fall back to a custom curve/lookup.
- **Committed `.tox` binaries are opaque in git** — review can't read them. *Mitigation:* the build script is the reviewed source of truth; the `.tox` is treated as a regenerated release artifact, not the thing humans diff.
- **Frame-rate dependence** — naive per-frame counting breaks under drops. *Mitigation:* build exclusively on time-sliced CHOPs; never count `me.time.frame`.

## Open questions

- Module versioning convention (no first-party prescription, RESEARCH §8) — settle the `Version` string convention in Phase 4.
- Palette preset machinery (parameter presets vs `storage` vs Preset CHOP, RESEARCH §4) — resolve before the Phase 4 preset pass.
- `sg_logic` Latch (no native S-R) and `sg_divide` swing — former deferred to v1.1; latter a Phase 2 risk prototyped early.

*(The seed/bootstrap boundary — formerly an open question — is now Phase 1's first gated deliverable, captured in `docs/SEED-RUNBOOK.md`, so the foundation's reproducibility exit is checkable.)*

*(Resolved by the MCP rework: the `.tox` externalize-to-text workflow — build-script-first makes the script the diffable source, so this is no longer an open question. Headless/CI feasibility — moved to Future Work as an explicit separate plan.)*

## Decisions

- **v1 = the 7-module MVP + the reproducible build pipeline**; `sg_function` + `sg_logic` deferred to v1.1.
- **Slug = `2026-06-09-aart-clock`** (co-located with RESEARCH.md).
- **TouchDesigner MCP is the build + verification substrate** (TD 099.2023.12480, bridge over `127.0.0.1:9981`). Live capability — create/param/Python/**read channel values** — verified this session.
- **Build-script-first source of truth.** Each module is a committed Python build script; the `.tox` is a generated artifact. Dissolves externalize-to-text.
- **Reproducible base:** committed minimal `seed.toe` (MCP bridge only) + `bootstrap.py` → committed `template.toe`. The whole library rebuilds from text + seed.
- **Build API: raw TD Python first, extract a thin `sg` helper library** on the rule of three (in the Phase 1 foundation).
- **Artifact policy: commit both** the build script (reviewed source) and the generated `.tox` (distributable artifact).
- **Build into the running project** under `/project1/aart_clock`; the pixel-art sketch stays as a demo consumer.
- **Verification = hybrid**: live MCP channel assertions for deterministic behavior (pinned frames), manual Trail/Info scopes for stochastic/feel; verification per-phase, not deferred. Unattended/headless CI is future work.
- **Five core signal types**; bipolar is a polarity convention on Value/Vector (single `value` channel + Polarity param); Color → Future Work; Vector provisional.
- **Single-frame event type = `Pulse`**, not Trigger; channels `pulse_*`.
- **Clock/phase seam = fat clock + off-grid phase.**
- **Vertical-slice phasing**; Phase 1 anchored by `sg_clock → sg_phase → sg_map`.
- **`sg_clock` on Time COMP + Beat CHOP**, not Timer CHOP.
- **Canonical channel-naming contract + shared sync/reset/wrap primitive** land in the Phase 1 foundation.
- **`Version` + preset deferred to Phase 4**; help text in the v1 template.
- **One commit per module to `main`** (script + regenerated `.tox` together).
- **Usage/integration documentation is a first-class, graded deliverable**, threaded through every phase.

## Revision log

### 2026-06-09 — Rework around the TouchDesigner MCP build pipeline

**Rationale:** The [touchdesigner-mcp](https://github.com/8beeeaaat/touchdesigner-mcp) bridge was connected and verified live (TD 099.2023.12480) — the agent can create operators, set params, run Python, and read live CHOP channel values in a running instance. This reshapes the project from plan-then-hand-off into a reproducible, agent-driven build pipeline with in-session verification.

Changes from the prior version:
- Added the **build & verification substrate** (MCP bridge) and the **build pipeline** (`seed.toe` + `bootstrap.py` → `template.toe` + `tox/` artifacts) to Context.
- **Source of truth is now a Python build script per module**; `.tox` is a generated artifact. This **dissolves the externalize-to-text open question**.
- **Build API:** raw TD Python first, extract a thin `sg` helper on the rule of three (Phase 1).
- **Reproducible base:** committed minimal `seed.toe` (bridge only, rebuildable via `docs/SEED-RUNBOOK.md`) + `bootstrap.py`; the seed/bootstrap boundary is Phase 1's first gated deliverable.
- **Verification moved from deferred to per-phase, hybrid:** live MCP channel assertions for deterministic behavior (pinned frames), manual Trail/Info scopes with explicit pass criteria for stochastic/feel. The old "Phase 4 harness spike" is removed; **unattended/headless CI moves to Future Work** (the bridge needs a running instance).
- **Artifact policy:** commit both build script (source) and generated `.tox` (distributable).
- **Topology:** build into the running `/project1` under `/project1/aart_clock`; the pixel sketch stays as a demo consumer.
- Reproducibility claims scoped honestly (functional equivalence, not byte-identical; seed reproducible by runbook) per the evaluator pass.

All prior decisions (Pulse rename, fat-clock/off-grid-phase seam, five types with bipolar as a polarity convention, vertical-slice phasing, usage docs as a graded deliverable) carry forward unchanged.
