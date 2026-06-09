# Session handoff — Phase 1 autonomous build (2026-06-09)

Built overnight via the TouchDesigner MCP bridge while you slept. Everything below is committed
and **pushed** to `origin/main` (so a `gt sync` won't touch it). Plain git throughout, not the
loom CLI.

## What got built (all verified live, all pushed)

| Commit | What | Verification |
|--------|------|--------------|
| `41cb0bd` | `bootstrap.py` — `aart_clock` namespace + `sg_template` | structure, wiring, extension instantiated |
| `04fd7cd` | `sg_clock` — Time COMP + 3 Beat CHOPs | 9 canonical channels; phase math cross-checks exactly (at 22 beats, phase_bar=0.617, phase_phrase=0.404) |
| `613333a` | `sg_map` — remap/clamp/quantize/polarity | 6 exact assertions pass (identity, remap, offset, invert, polarity, clamp) |
| `a9d4eee` | `sg_phase` — off-grid LFO ramp + wrap pulse | contract channels present, phase advancing, no errors |
| `c2a660a` | `sg` build-helper library | smoke-tested (build module, assert, destroy) |
| `876d3f6` | `aart_clock.tox` export + `dev/test-project.toe` | exported from the verified build |
| (this) | `USAGE.md` + this handoff | — |

Plus the composition check: `sg_clock` `phase_bar` (0.4) → `sg_map` (×100) → `value` 40 = expected.
The signal language flows across modules.

## Decisions I made autonomously (please sanity-check)

1. **`sg_template` structure** = In/Out CHOPs + flat internal network + `TemplateExt` (ext) + `help`
   DAT (docs) + `demo` COMP + `Aartclock` param page. Pragmatic reading of in/out/params/ext/docs/
   demo/internal — not nested container COMPs for in/out (the In/Out CHOPs *are* the I/O).
2. **`Play` is a single toggle** (on=play, off=stop) rather than separate Play/Stop pulses. Cleaner;
   the plan listed Play+Stop.
3. **Conditional stages use expressions, not bypass** — `bypass` is a node flag, not a parameter, so
   it can't hold an expression. `sg_map` clamp opens its bounds wide when off; quantize uses a
   negligible step when off.
4. **`sg_phase.ramp` is an alias of `phase`** (same value) for contract completeness.
5. **Did NOT refactor `sg_clock`/`sg_phase`/`sg_map` onto the `sg` helper** — they work; refactoring
   verified modules unattended wasn't worth the risk. Clean follow-up.

## Flags / things needing your eyes

- **Plan inconsistency (real):** the Phase 1 exit says "`sg_clock → sg_phase → sg_map` runs," but the
  fat-clock/off-grid-phase decision means `sg_phase` does **not** consume `sg_clock` — it's parallel.
  The actual slice is **clock→map** and **phase→map**. Either update the plan's exit wording, or add
  the deferred `sg_clock.pulse_* → sg_phase` Reset wiring to make a literal chain (the plan already
  describes sg_phase Reset as "alignable to a clock pulse"). Your call.
- **`seed.toe` and `dev/template.toe` not produced.** I built/verified against the running project,
  but the clean bridge-only `seed.toe` is a manual TD step (blank project + import bridge + save) per
  `docs/SEED-RUNBOOK.md`. Until it exists, "reproducible from seed + scripts" isn't fully closed
  (the *scripts* are reproducible — each is idempotent and re-verified).
- **Running TD points at `dev/test-project.1.toe`.** TD's incremental save created a `.1` version; I
  committed `dev/test-project.toe` and removed the stray. Next time you save in TD, do **Save As →
  `dev/test-project.toe`** (or disable incremental save) to converge.
- **`.claude/settings.json`** is untracked (your MCP permission config). I left it out of all commits
  — decide whether to track it (or move allowlist to `settings.local.json`).
- **Deferred in `sg_*` v1:** `sg_phase` Reset + beat-relative sync; `sg_map` Quantize is built but
  *not* asserted (mark for Trail-scope verify); `sg_template` param page is empty (modules add their
  own); `Version`/preset are Phase-4 per plan.

## Phase 1 status: ~90%

Done: boundary+runbook, bootstrap+template, the 3 modules (built+verified), sg helper, composition
check, USAGE seed, tox export. Remaining: produce `seed.toe`/`template.toe` (manual seed step), the
plan-exit wording call, optional helper-refactor of the 3 scripts.

## Suggested next steps

1. Resolve the clock→phase wording/wiring decision.
2. Produce `seed.toe` per the runbook (5 min in TD), then run `bootstrap.py` → save `template.toe`.
3. Poke the modules in TD (Trail/Info CHOP) to confirm feel — especially `sg_map` Quantize and
   `sg_phase` wrap pulse, the two I asserted least.
4. Phase 2: `sg_divide`, `sg_env` (now fast — the `sg` helper + the verified patterns are in place).
