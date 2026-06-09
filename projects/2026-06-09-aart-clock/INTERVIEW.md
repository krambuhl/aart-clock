# INTERVIEW — aart-clock

The walked decision tree behind [PLAN.md](./PLAN.md). One heading per resolved question: the recommendation, the answer, and the rationale. Research-grounded recommendations cite [RESEARCH.md](./RESEARCH.md).

## Round 1 — Framing (research-independent)

### v1 scope boundary
- **Recommendation:** v1 = the 7-module MVP (clock, phase, divide, lfo, random, env, map); defer `sg_function` + `sg_logic` to v1.1.
- **Answer:** v1 = MVP 7, defer 2.
- **Rationale:** The MVP success criteria are defined around exactly these seven and the two patch chains they enable. `sg_function` (curve editor) is heavier UI work; `sg_logic` has a non-native Latch. Keeping them out keeps the first milestone sharp.

### Slug
- **Recommendation:** `aart-clock` (matches repo/README).
- **Answer:** `make-clock` initially; reconciled to `2026-06-09-aart-clock` in Round 2 once the research sub-agent had already committed the dossier under that date-stamped slug.
- **Rationale:** The plan must co-locate with RESEARCH.md in one project dir; the research already owned `2026-06-09-aart-clock`, so adopting it avoided a migration and matched the repo name.

### Phase decomposition
- **Recommendation:** Foundation, then per-layer.
- **Answer:** Vertical MVP slice first.
- **Rationale:** Each phase ends in a runnable patch, widening the toolkit rather than stacking horizontal layers. The clock is the spine everything hangs off, so the first slice proves it end to end.

### PR / commit cadence
- **Recommendation:** One PR per module.
- **Answer:** Solo repo — commit to `main`, one commit per module.
- **Rationale:** Per the workspace convention, single-contributor repos with no PR review skip branch ceremony. The foundation lands as its own commit first.

## Round 2 — Research-grounded design

### Slug reconciliation
- **Recommendation:** Use `2026-06-09-aart-clock` (the slug the research already owns).
- **Answer:** Use `2026-06-09-aart-clock`.
- **Rationale:** Plan co-locates with RESEARCH.md, no migration, matches the repo name. (RESEARCH.md §1–10.)

### Core signal-type conflict (Bipolar vs Color)
- **Recommendation:** Bipolar, drop Color (Color is a visual concern → Future Work).
- **Answer:** Bipolar — *and* fold it into the Value/Vector range rather than a distinct type.
- **Rationale:** In modular terms unipolar (0–1) and bipolar (−1..1) are the same CV at different ranges. Folding polarity into a convention on Value/Vector drops the type surface from six to five and keeps the language composable. `sg_map` owns conversion. (RESEARCH key-decision #10.)

### Phase 1 vertical slice
- **Recommendation:** `clock → phase → map`.
- **Answer:** `clock → phase → map`.
- **Rationale:** Validating the transport spine + output stage first means every later module plugs into a tested backbone, and `sg_map` appearing early gives every signal a verified output stage. (RESEARCH §1, §3.)

### Verification gate
- **Recommendation:** Hybrid — manual Trail/Info scopes now, plus a small `sg_clock` harness spike in the foundation.
- **Answer:** Hybrid, but move the spike *later* in the plan, with the intent to spawn a separate plan for the real harness.
- **Rationale:** TD has no test runner; manual scopes + demo patches are the idiomatic v1 gate. The harness is a real effort of unknown cost, so a late-phase spike scopes it and seeds a dedicated `/loom-plan`. (RESEARCH §9.)

## Round 3 — Plan-panel forks (composition / abstraction / naming)

### Clock/phase seam
- **Recommendation:** Fat clock + off-grid phase.
- **Answer:** Fat clock + off-grid phase.
- **Rationale:** The panel flagged that `sg_clock` and `sg_phase` both emitted phase ramps + wrap pulses — one concept in two modules. Making `sg_clock` the sole beat-synced phase source and `sg_phase` the off-grid / arbitrary-rate specialist gives each a distinct identity, keeps the common (synced) case a one-module patch, and deviates least from the original spec. (composition panel finding #1.)

### "Trigger" type name collision
- **Recommendation:** Rename to `Pulse`.
- **Answer:** Rename to `Pulse`.
- **Rationale:** All three panel lenses escalated the collision: TD's native Trigger CHOP is an ADSR engine (which `sg_env` is built on), so naming the one-sample-event type "Trigger" is a permanent ambiguity. "Pulse" matches the research's own term (LFO `Pulse` type) and leaves the native operator sole ownership of "trigger." Channels become `pulse_*`. (naming panel finding #1.)

### `bipolar` overload (sg_lfo output)
- **Recommendation:** Single `value` channel + Polarity param; drop the separate `bipolar` output.
- **Answer:** Single `value` + polarity param.
- **Rationale:** `bipolar` named both the polarity *convention* and a literal output channel — a same-name-two-concepts violation that contradicted the fold-in decision. One `value` channel with a Polarity param de-overloads the word, removes the "two places do conversion" smell, and keeps `sg_map` the conversion owner. (naming panel finding #3, composition #2/#3.)

## Folded-in panel findings (no fork — recommendation accepted directly)

- **Canonical channel-naming contract into Phase 1** — pin per-type channel names + ordering, not just connector placement, or every junction needs a Rename/Select CHOP. (composition #5, abstraction, naming #2.)
- **Shared sync/reset/wrap-detect primitive** — four modules share it today (past the rule of three); extract into the module standard rather than reinventing it four times. (abstraction #2.)
- **Defer `Version` param + preset support to Phase 4** — both are unresolved Open questions in the research; baking unknown-shape slots into 7 modules is speculative. Help text stays in v1. (abstraction #1.)
- **Mark `Vector` provisional** — no v1 module produces a Vector, so the convention is untested-by-construction; document as forward-looking. (composition #4.)
- **Polarity carrier** — the convention gets a channel-level marker so polarity travels with the signal, not in tribal docs. (composition #3.)

## Late addition (user)

### Usage / integration documentation
- **Answer (user-initiated):** Ensure the project clearly documents *how the system is used with TouchDesigner projects.*
- **Resolution:** Usage documentation promoted to a first-class, graded deliverable at two altitudes — per-module `docs`/`demo` and a project-level integration guide (install + signal-language reference + the two chain walkthroughs) — threaded through every phase, seeded in Phase 1, completed in Phase 4.
- **Rationale:** The original success criterion is that an artist works "without writing custom project logic." That is achievable only if the consumption workflow is documented, so the docs are how the criterion is met and proven — not an afterthought.
