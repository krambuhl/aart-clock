# PLAN — aart-clock

A modular timing, rhythm, modulation, and signal-processing toolkit for TouchDesigner. Composable `sg_*` modules let visual systems be driven with concepts borrowed from modular synthesis. This project generates and shapes signals only — visual rendering is explicitly out of scope.

## Context

Research foundation: [RESEARCH.md](./RESEARCH.md) — a fact-anchored dossier on *how* to build the `sg_*` library in TouchDesigner, cited against `docs.derivative.ca`. The plan below treats those findings as input. (Caveat carried from the dossier: WebSearch/WebFetch were unavailable to the research sub-agent, so first-party API claims are well-grounded but community/CI idioms are lighter — see Open questions.)

aart-clock models time, rhythm, envelopes, and modulation as first-class, patchable building blocks — the way Eurorack, Monome, and OXI One treat control voltage. The artist composes reusable signal networks (`Clock → Phase → Gates → Pulses → Envelopes → Modulation → Mapping → Visual`) instead of wiring visual behavior directly. The whole toolkit hangs off one shared signal language, so the foundation phase that defines that language is the most load-bearing work in the plan.

### Signal language (the shared contract)

Five core signal types, each a normalized CHOP channel convention:

| Type | Range | Description |
|------|-------|-------------|
| Phase | 0–1 | Normalized looping time |
| Gate | 0/1 | Binary sustained state |
| Pulse | one-sample pulse | Single-frame event |
| Value | 0–1 (unipolar) / −1..1 (bipolar) | Continuous scalar, carries a polarity convention |
| Vector | xyz | Multi-channel Value (provisional — see below) |

**Polarity is a convention on Value/Vector, not a separate type.** Unipolar (0–1) is the default; bipolar (−1..1) is used where sign matters (LFO output, modulation depth). Modules emit a single `value` channel with a **Polarity param** (unipolar/bipolar) rather than two range-variant channels; `sg_map` owns conversion between the two. So that polarity travels *with* the signal rather than living only in docs, the channel-naming contract (Phase 1) carries a polarity marker readable downstream (a channel suffix and/or an Info-CHOP-readable flag). (This reconciles the README's six-type list — which included "Color" — with the plan brief's. Color is a visual/rendering concern and moves to Future Work; the README is updated to match in Phase 4.)

**"Pulse," not "Trigger."** The single-frame-event type is named **Pulse** to avoid a permanent collision with TouchDesigner's native **Trigger CHOP**, which is an ADSR envelope generator (and which `sg_env` is built *on*). A Pulse is produced by an LFO CHOP `Pulse` type or a Logic CHOP rising/falling edge, kept in time-sliced CHOP-land (RESEARCH §2). Naming the type "Pulse" leaves the native Trigger CHOP sole ownership of the word "trigger."

**Vector is provisional.** No v1 module produces a Vector — only `sg_map` is specified to pass one through — so the convention is forward-looking and untested-by-construction in v1. It is documented as a contract a future producer must honor, not exercised end-to-end by the MVP.

### Module standard

Every `sg_*` module is a **Base COMP** (headless signal shell, no panel gadgets) following one internal structure:

```
sg_<name>
├── in        # In CHOPs (left connectors, signal in)
├── out       # Out CHOPs (right connectors, signal out)
├── params    # custom parameter pages
├── ext       # XxxExt Python extension class (API / help)
├── docs      # description + help text
├── demo      # example patch (doubles as the verification artifact)
└── internal  # the CHOP-graph implementation
```

Standard conventions, grounded in RESEARCH §4:

- **CHOP-graph-first.** Continuous per-sample math lives in native, time-sliced CHOP networks. Python (extension / CHOP Execute DAT) is reserved for event reactions, state, and the API surface — never the hot per-sample loop (RESEARCH §5). The one sanctioned exception is `sg_random`'s reproducible walk/brownian/chaos, which runs a seeded Python loop over a known time base because Brownian noise can't be 1-sample-limited under time slicing (RESEARCH §6); the standard names this as an explicit exception, not a leak.
- **Frame-rate independence comes from time slicing, not frame counting.** Build on time-sliced CHOPs and read seconds/beats; never count `me.time.frame` (RESEARCH §1).
- **Canonical channel-naming contract.** The foundation pins per-type channel names *and ordering* (not just connector placement), so two modules wire together without a Rename/Select CHOP at every junction. The scheme is `<role>_<scope>` for scoped channels (`phase_beat`, `pulse_wrap`) and a bare role name for unscoped ones (`value`, `gate`, `env`, `ramp`); the rule (bare = unscoped, prefixed = scoped) is written into the contract so later modules don't improvise `value_lfo`/`lfo_value`. Value/Vector channels carry the polarity marker described above.
- **Shared sync/reset/wrap-detect primitive.** `sg_clock`, `sg_phase`, `sg_lfo`, and `sg_divide` all share a Reset behavior and the wrap-detect chain (Logic CHOP falling-edge on a 0→1 ramp → `pulse_wrap`); modules that sync share a Free/Beat/Bar/Phrase **Sync mode** convention. These are a shared sub-template in the standard (four callers today — past the rule of three), so the time-slice-pulse gotcha is fixed in one place rather than reinvented four times.
- **Custom-param naming constraints** (RESEARCH §4): first letter uppercase, no underscores, keep names ≤ ~10–12 chars. The standard fixes the *shortening algorithm* (lead with the scope noun, drop interior connectors: `BeatsPerBar` → `BarBeats`, `BarsPerPhrase` → `PhraseBars`) + a free-form friendly label, and reuses the COMP's built-in lowercase `play` rather than a custom `Play`.
- **Externalize Python to text DATs**, committed alongside the binary `.tox`, so the code stays diffable in git even though the network topology is opaque (RESEARCH §10).
- Each module carries embedded **help text** (the Pulse-vs-Trigger-CHOP note lives here). `Version` string + preset support are **deferred to Phase 4** (their conventions are unresolved — see Open questions), not baked into the v1 template.

A module **template** (skeleton `.tox` + extension stub + the shared sync/reset/wrap sub-chain) is produced in Phase 1 so every later module starts from the standard rather than re-deriving it.

### Usage & integration documentation (a first-class deliverable)

The success criterion is that an artist can build BPM-synced animation, rhythmic events, generative modulation, and envelope-driven motion **without writing custom project logic** — which is achievable only if *how to use aart-clock inside a TouchDesigner project* is clearly documented. Usage documentation is therefore a graded deliverable, not a nice-to-have, and is threaded through every phase rather than deferred to the end.

It has two altitudes:

- **Per-module usage** — every module's `docs`/`demo` must answer "how do I wire this into my project": the module's inputs/outputs (named per the channel contract), its params, and a minimal worked patch. The `demo` patch doubles as both the verification artifact and the copy-paste starting point.
- **Project-level integration guide** — a repo-level guide (`USAGE.md` or a `docs/` set) covering: installing the `sg_*` family into a TD project (palette / `.tox` drop), the signal-language quick reference (the five types + polarity + channel-naming cheat sheet), how signals flow between modules, and **the two success-criteria chains written as step-by-step walkthroughs** an artist can follow to a working result. This is the artifact that proves "no custom project logic required."

The integration guide is seeded in Phase 1 (install + signal-language reference + the first chain) and grows with each phase as modules land; the two complete chain walkthroughs are finished in Phase 4.

## Scope

**In (v1 = the 7-module MVP):**

- Layer 1 — Timing: `sg_clock`, `sg_phase`, `sg_divide`
- Layer 2 — Generation: `sg_lfo`, `sg_random`
- Layer 3 — Shaping: `sg_env`, `sg_map`
- The shared signal language + module standard + module template.

v1 is complete when both success-criteria patch chains run end to end:

```
sg_clock → sg_phase → sg_divide → sg_env → sg_map      (Chain A)
sg_lfo → sg_map                                         (Chain B)
```

with all resulting signals available to drive arbitrary TouchDesigner visual systems.

**Deferred (v1.1, fast-follow):**

- `sg_function` (custom curve editor — heavier UI work; the LFO CHOP Source Wave input covers the simple curve case in the interim, RESEARCH §3)
- `sg_logic` (gate/pulse boolean processing — Logic CHOP maps ~1:1 but the Latch mode has no native S-R primitive, RESEARCH §2)

**Out (Future Work — separate plans/projects under the aart ecosystem):**

- Visual generators, color systems, instancing systems, scene composition
- MIDI, OSC, Ableton Link, DMX
- Performance tooling
- The full headless test harness (a Phase 4 spike scopes it; the harness itself becomes its own `/loom-plan`)

## Phases

The build is a sequence of **vertical slices**: each phase ends with a runnable patch, widening the toolkit rather than stacking horizontal layers. Cadence is one commit per module directly to `main` (solo single-contributor repo — no PR ceremony per the workspace convention); the foundation/template lands as its own commit first within Phase 1.

### Phase 1 — Foundation + first vertical slice (`sg_clock → sg_phase → sg_map`)

The signal language and module standard, proven by the thinnest real chain. Everything in the toolkit hangs off the clock and ends at a mapping stage, so validating that spine first means every later module plugs into a tested backbone.

- **Signal-language contract** — the five types + polarity convention + the canonical channel-naming/ordering rule, as a documented reference.
- **Module standard + skeleton template `.tox`** — Base COMP shell, In/Out CHOPs, `XxxExt` stub, param-page conventions + shortening algorithm, externalize-to-text wiring, the shared sync/reset/wrap-detect sub-chain, help-text scaffolding. (No `Version`/preset slot yet.)
- `sg_clock` — master transport on a **Time COMP + Beat CHOP** (not the Timer CHOP, RESEARCH §1), and the **sole beat-synced phase source**. Outputs: `beat`/`bar`/`phrase` counters, `phase_beat`/`phase_bar`/`phase_phrase` ramps, `pulse_beat`/`pulse_bar`/`pulse_phrase`. Params: BPM, play (built-in), Stop, Reset, BarBeats (label "Beats Per Bar"), PhraseBars (label "Bars Per Phrase").
- `sg_phase` — the **off-grid phase specialist**: normalized looping phase at an arbitrary rate (free Hz or beat-relative multiplier) decoupled from the transport grid, with phase offset and Reset (alignable to a clock pulse). Distinct from `sg_clock`'s fixed beat/bar/phrase ramps. Outputs: `phase`, `ramp`, `pulse_wrap` (shared wrap-detect chain). Built on the LFO CHOP ramp for free mode.
- `sg_map` — signal mapping: scale, offset, clamp, invert, quantize, curve; owns the unipolar↔bipolar conversion (the conversion math is a documented reusable snippet so generators don't copy-paste it).
- **Integration guide seeded** — `USAGE.md` with installation (palette / `.tox` drop), the signal-language + channel-contract quick reference, and the `sg_clock → sg_phase → sg_map` chain written as a step-by-step walkthrough. Each of the three modules ships its per-module `docs`/`demo` usage section.
- **Exit:** `sg_clock → sg_phase → sg_map` runs; the signal language, channel contract, and module standard are validated by three structurally-distinct real modules (transport source, off-grid generator, pure transform) built on them; a new user can follow the guide to a working patch.

### Phase 2 — Complete Chain A (`sg_divide`, `sg_env`)

- `sg_divide` — clock division/multiplication, offset, swing. Built on Beat CHOP Multiples/Shift Offset/Shift Step for division and staggering (RESEARCH §1). Outputs: `phase`, `gate`, `pulse`. **Swing is prototyped first** (see Risks) — Beat CHOP may not express uneven subdivision as a single param.
- `sg_env` — envelope generator wrapping the **Trigger CHOP** (TD's native ADSR engine, RESEARCH §7). Modes: AR (attack+release, zeroed sustain), AD, ADSR, Looping (re-trigger / periodic gate). Inputs: `gate`, `pulse`. Output: `env`.
- **Usage docs** — `sg_divide` and `sg_env` ship per-module `docs`/`demo`; the integration guide gains the full Chain A walkthrough.
- **Exit:** full Chain A `sg_clock → sg_phase → sg_divide → sg_env → sg_map` runs end to end and is documented as a followable walkthrough.

### Phase 3 — Generation sources (`sg_lfo`, `sg_random`)

- `sg_lfo` — continuous oscillator on the LFO CHOP. Shapes: Sine, Triangle, Saw, Square, Random Hold, Random Smooth. Sync mode (to clock, via the shared sync convention), phase offset, reset. Outputs: `value` (with Polarity param, unipolar/bipolar), `phase`, `pulse_wrap`.
- `sg_random` — randomized source. White Noise + smooth via **Noise CHOP** (`Seed` param); Random Walk / Brownian / Chaos via **seeded Python over a known time base** where strict reproducibility is required (RESEARCH §6). Deterministic seeding via `tdu.rand(seed)`. Outputs: `value` (with Polarity param).
- **Usage docs** — `sg_lfo` and `sg_random` ship per-module `docs`/`demo`; the integration guide gains the Chain B walkthrough.
- **Exit:** Chain B `sg_lfo → sg_map` runs; both success-criteria chains are live and documented. **MVP achieved.**

### Phase 4 — v1 hardening + verification-harness spike

- **`Version` string convention + preset support pass** across all seven modules, once their conventions are settled (this is the resolution of two Open questions, not v1-template speculation).
- Help-text + `docs`/`demo` completeness; palette packaging of the `sg_*` family.
- **Integration guide completion** — both success-criteria chains finalized as polished step-by-step walkthroughs; the install/quick-reference sections brought current with the final API. This is the deliverable that proves the "no custom project logic" success criterion.
- README reconcile (drop Color from the core-type list, document the polarity convention, rename Trigger→Pulse in the type list).
- **Verification-harness spike:** a proof-of-concept headless Python test that loads `sg_clock`, steps frames, and asserts on CHOP channel values — scoped narrowly, to *learn the cost*. This phase explicitly seeds a follow-up `/loom-plan` for the real test harness; it does not attempt to build the harness itself.
- **Exit:** v1 packaged; harness follow-up plan scoped.

## Dependencies

- All modules depend on the **Phase 1 foundation** (signal language + channel contract + module standard + template, incl. the shared sync/reset/wrap primitive).
- `sg_phase` can take an optional `sg_clock` pulse for Reset alignment; otherwise independent (free mode).
- `sg_divide` divides a clock — depends on `sg_clock`.
- `sg_env` needs a gate/pulse source (`sg_clock` or `sg_divide`).
- `sg_map` depends only on the signal-type/channel contract (takes any Value/Vector).
- `sg_lfo` sync mode depends on `sg_clock`; free-run is independent.
- `sg_random` is independent (seeded).
- External: TouchDesigner (Derivative). Native operators relied on: Time COMP, Beat CHOP, LFO CHOP, Logic CHOP, Trigger CHOP, Noise CHOP, Info CHOP, Trail CHOP; `tdu` Python module.

## Verification

No Jest equivalent exists in TouchDesigner. v1 gates on (RESEARCH §9):

- **Per-module `demo` patch** — each module ships an example patch that doubles as its verification artifact.
- **Trail CHOP + Info CHOP scopes** — signal correctness is confirmed by watching the output channel over time (Trail) and introspecting op state (Info), with a screenshot captured in `docs`.
- **OP Snippets**-style worked examples per module.

The per-module `demo` patches and the project-level integration guide (see Usage & integration documentation) are graded deliverables, not optional: a phase is not done until a new user could follow its docs to the working patch the phase exits on.

Automated testing is deferred: the Phase 4 spike builds a single proof-of-concept headless test (on `sg_clock`) to learn whether a real frame-stepping harness is worth pursuing, and seeds a separate plan for it. v1 does not block on automated coverage.

## Risks

- **Brownian/Chaos reproducibility** — Noise CHOP Brownian/Harmonic can't be 1-sample-limited under time slicing, so strict reproducibility for walks/chaos needs seeded Python over a known time base, not time-sliced Brownian (RESEARCH §6). *Mitigation:* `sg_random` uses Noise CHOP for white/smooth, seeded Python for reproducible walk/brownian/chaos (the standard's sanctioned CHOP/Python exception).
- **Swing in `sg_divide`** — Beat CHOP covers offset/staggering but musical *swing* (uneven subdivision) may not be a native one-param feature (RESEARCH open questions). *Mitigation:* prototype swing first thing in Phase 2; fall back to a custom curve/lookup if Beat CHOP can't express it.
- **Binary `.tox` in git** — opaque to review/diff. *Mitigation:* externalize all Python to text DATs (baked into the module standard); rely on Trail/Info screenshots for review context.
- **Param-name constraints** — uppercase-first, no underscores, length limits will bite plan-stated names. *Mitigation:* the standard's shortening algorithm + friendly labels + reuse of built-in `play`, encoded in the template so it's not re-litigated per module.
- **Frame-rate dependence** — naive per-frame counting breaks under frame drops. *Mitigation:* build exclusively on time-sliced CHOPs; never count `me.time.frame`.
- **Polarity convention leaks silently** — a bipolar signal into a unipolar consumer just looks wrong, no error. *Mitigation:* the channel-naming contract carries a polarity marker so polarity travels with the signal, not in tribal docs.

## Open questions

Carried from RESEARCH.md (mostly blocked by the sub-agent's lack of web/forum access):

- Exact externalize-to-text workflow for `.tox` (the relevant Derivative wiki pages are stubs) — resolve before Phase 1 wires the template's externalize step.
- Module versioning convention (no first-party prescription found) — settle the `Version` string convention in Phase 4, before the preset/version pass.
- Palette preset machinery specifics (parameter presets vs `storage` vs Preset CHOP) — resolve before the Phase 4 preset pass.
- Headless/CI feasibility detail — the Phase 4 spike exists to answer this.
- `sg_logic` Latch (no native S-R) and `sg_divide` swing implementation — the former is deferred to v1.1; the latter is a Phase 2 risk prototyped early.

## Decisions

- **v1 = the 7-module MVP**; `sg_function` + `sg_logic` deferred to v1.1.
- **Slug = `2026-06-09-aart-clock`** (the project the research already owns; plan co-locates with RESEARCH.md).
- **Five core signal types**; bipolar is a polarity convention on Value/Vector (single `value` channel + Polarity param), not a distinct type; Color dropped to Future Work; Vector marked provisional.
- **Single-frame event type named `Pulse`**, not Trigger — leaves the native Trigger CHOP sole ownership of "trigger." Channels are `pulse_*`.
- **Clock/phase seam = fat clock + off-grid phase**: `sg_clock` is the sole beat-synced phase source; `sg_phase` is the off-grid / arbitrary-rate specialist.
- **Vertical-slice phasing**; Phase 1 anchored by `sg_clock → sg_phase → sg_map`.
- **`sg_clock` on Time COMP + Beat CHOP**, not Timer CHOP.
- **Canonical channel-naming contract** + **shared sync/reset/wrap-detect primitive** land in the Phase 1 foundation.
- **`Version` + preset support deferred to Phase 4** (unresolved conventions); help text stays in the v1 template.
- **Verification = manual Trail/Info scopes + demo patch** for v1; headless harness is a Phase 4 spike that seeds its own plan.
- **One commit per module to `main`** (solo repo, no PR ceremony).
- **Externalize Python to text DATs** as part of the module standard.
- **Usage/integration documentation is a first-class, graded deliverable** — per-module `docs`/`demo` plus a project-level integration guide (install + signal-language reference + the two chain walkthroughs), threaded through every phase. It is how the "no custom project logic" success criterion is met and proven.
