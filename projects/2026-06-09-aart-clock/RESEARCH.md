# RESEARCH — aart-clock (TouchDesigner signal toolkit)

Fact-anchored dossier on **how** to build the `sg_*` modular signal library in TouchDesigner (TD). Every claim cites an observable or a Derivative docs URL. All docs URLs are `docs.derivative.ca` (the official operator/Python wiki) unless noted.

Scope reminder: aart-clock generates and shapes signals only (Phase / Gate / Trigger / Value / Bipolar / Vector). It does not render. The plan is strong on *what*; this dossier anchors the *how* and flags where the plan may fight TD idioms.

---

## 1. Transport & timing primitives

### TD already has a global tempo/beat system — the Time COMP
- Every component can have its own timeline/clock via a **Time COMP** placed at `<comp>/local/time`; this is called **Component Time**. The default global one is `/local/time`, cloned from the master `/sys/local/time`. (Time COMP — https://docs.derivative.ca/Time_COMP)
- The Time COMP exposes the transport surface aart-clock's `sg_clock` wants to mirror: `Play` (0/1), `Rate` (fps), `Start`/`End` frames, `Range Limit` (Loop/Hold), `Signature` (beats-per-measure + note value), and **`Tempo` (BPM)**. (Time COMP params — https://docs.derivative.ca/Time_COMP)
- You can set BPM in Python directly: `op('/local/time').tempo = 140`. (Beat CHOP — https://docs.derivative.ca/Beat_CHOP)
- A Time COMP with **`Run Independently` on** is *not* dependent on parent Time COMPs — pausing a higher Time COMP won't pause it. This is the lever for "ride global tempo vs. build independent transport." (Time COMP — https://docs.derivative.ca/Time_COMP)

### Beat CHOP — beat-synced ramps/pulses riding (or not) the Time COMP
- The **Beat CHOP** turns the BPM of a referenced Time COMP into repeating ramps, pulses and counters. It can generate a ramp every 1/4, 1/2, 1, 2, 4, 8, 32 beats, or any fractional `Period` (e.g. 3.33 beats). It also emits a **counter of ramps generated** and a **Count+Ramp** type (continuously rising ramp = cycles since start). (Beat CHOP — https://docs.derivative.ca/Beat_CHOP)
- Beat CHOP **Play Mode** is the global-vs-local switch:
  - *Locked to Timeline* — resets when the local timeline loops; deterministic per pass.
  - *Locked to Global* — follows the Beat CHOP whose "Update Global" flag is on.
  - *Local Sequential* — continuous output ignoring timeline start/end; "more appropriate for long improvised playing." (Beat CHOP — https://docs.derivative.ca/Beat_CHOP)
- Beat CHOP timing is defined by the **Component Time of its Reference Node** (defaults to `/local/time`). Phase is controllable via its Reset params. (Beat CHOP — https://docs.derivative.ca/Beat_CHOP)
- Multiples / Shift Offset / Shift Step let one Beat CHOP emit N staggered ramps (e.g. 8 objects each delayed one beat) — directly useful for `sg_divide`'s offset/swing intent. (Beat CHOP — https://docs.derivative.ca/Beat_CHOP)

### Timer CHOP — the heavyweight cue/state-machine engine
- The **Timer CHOP** runs timed processes set in seconds/frames/samples; outputs `timer_fraction`, counters, pulses, on/off and a `done` channel; and fires Python callbacks (`onStart`, `onCycleStart`, `onDone`, etc.). It is a state-machine engine — playlists, cues, timelines. (Timer CHOP — https://docs.derivative.ca/Timer_CHOP)
- It can be **Locked to Timeline (deterministic)** or run in Sequential mode where you can `goTo()` exact positions, jump cycles, change speed. To loop after the last segment set On Done → Re-Start. (Timer CHOP — https://docs.derivative.ca/Timer_CHOP)
- Tradeoff: Timer CHOP is callback/Python-heavy and oriented at *cue sequencing*, not at a continuously-running musical phase clock. For aart-clock's always-running phase/beat/bar/phrase outputs, **Beat CHOP riding a Time COMP is the more idiomatic spine**; reserve Timer CHOP for one-shot/cue behaviors (it pairs naturally with `sg_env`'s gate logic).

### Frame-rate independence is a first-class TD feature: Time Slicing
- **Time Slicing** keeps CHOP channels smooth/accurate even when the frame rate drops and frames are skipped. A time slice = the samples between the last cook frame and the current cook frame; if TD skips frames the slice is multiple samples (e.g. 2/60s). (Time Slicing — https://docs.derivative.ca/Time_Slicing)
- "With Time Slicing, samples do not get lost or un-processed when TouchDesigner cannot keep up… All frames get processed, albeit in batches." This is the mechanism that makes pulses accurate across frame drops. (Time Slicing — https://docs.derivative.ca/Time_Slicing)
- Time Slice is a Common-page parameter, auto-set on most CHOPs. LFO/Beat/Speed/Noise/Filter are time-sliced; Constant CHOP is **not** (always 1 sample). (Time Slicing — https://docs.derivative.ca/Time_Slicing; Constant note in Time Slicing page)
- **Implication for the plan:** "frame-rate-independent timing" is achieved by building on time-sliced CHOPs and reading time in seconds/beats, *not* by counting `me.time.frame`. Per-frame integer counting (e.g. a Python "increment a counter every frame") breaks under frame drops; integrate rate over the time slice instead (see Speed CHOP, §3).

---

## 2. Single-frame triggers in a continuously-cooking runtime

- A "pulse" in CHOP-land is a value that is on for **one sample only**. Two native producers:
  - **LFO CHOP `Pulse` type**: "Produces a 1 for one sample, 0 otherwise." (LFO CHOP — https://docs.derivative.ca/LFO_CHOP)
  - **Logic CHOP edge detection**: `Channel Pre OP` → **Rising Edge** ("On for one sample only, at each place where a channel goes from off to on") and **Falling Edge** (one sample at on→off). This is the canonical gate→trigger and wrap-detect primitive. (Logic CHOP — https://docs.derivative.ca/Logic_CHOP)
- **Gotcha — missed frames vs. Time Slicing:** because edges are detected within the cooked time slice, a one-sample pulse is preserved across frame drops *as long as the producing chain is time-sliced* (the slice carries the in-between samples). A non-time-sliced single-sample pulse can be missed if a downstream consumer cooks on a different frame. Prefer the Trigger CHOP / time-sliced Logic chain over hand-rolled per-frame Python booleans.
- **Cook order gotcha:** the Logic CHOP doc explicitly says it is "superceded by more convenient operators like the CHOP Execute DAT or the Text DAT which will run their scripts when CHOP channels change." (Logic CHOP — https://docs.derivative.ca/Logic_CHOP) For *acting on* a trigger (firing Python), use a **CHOP Execute DAT** watching the channel; for *propagating* a trigger as signal, keep it in CHOP-land with Logic edge detection.
- `sg_logic`'s spec (AND/OR/XOR/NOT/Toggle/Latch/Edge-Detect) maps almost 1:1 onto the **Logic CHOP**: Combine Channels has And/Or/Xor/Nand/Nor/Eqv; Channel Pre OP has Invert (NOT), **Toggle** ("each 0→1 transition switches state"), Radio (latch-like), Rising/Falling Edge. (Logic CHOP — https://docs.derivative.ca/Logic_CHOP) Latch may need a small Logic+Speed/Hold combo; toggle is native.

---

## 3. Phase / ramp generation

- **Beat CHOP** is the beat-synced ramp source (§1). For *free-running* phase decoupled from beats, the **LFO CHOP `Ramp` type (0→1)** is the direct producer; it's time-sliced and has Frequency, Phase offset, and a Reset input — covering `sg_lfo`/`sg_phase`'s Free mode, phase offset, and reset needs. (LFO CHOP — https://docs.derivative.ca/LFO_CHOP)
- LFO CHOP wave types cover the `sg_lfo` menu directly: `sin` (−1..1), `tri` (−1..1, Bias moves the peak), `ramp` (0..1 = saw), `square` (−1..1, Bias = pulse width), plus `normal`/Gaussian and `pulse`. Offset/Amplitude/Bias/Phase params do shaping. (LFO CHOP — https://docs.derivative.ca/LFO_CHOP)
- The LFO CHOP **Octave Control** input multiplies frequency exponentially (per unit doubles), and **Source Wave** input replaces the wavetype with an arbitrary curve — that's the "custom curve" path for `sg_function` (phase in → value out) without writing Python. (LFO CHOP — https://docs.derivative.ca/LFO_CHOP)
- **Wrap detection** for `sg_phase` (and `sg_clock` beat/bar/phrase triggers): feed the 0→1 ramp into a **Logic CHOP Falling Edge** (the ramp drops 1→0 at wrap) or compare consecutive samples. Native, time-sliced, no Python. (Logic CHOP — https://docs.derivative.ca/Logic_CHOP)
- Pattern/Wave CHOPs generate *static* waveforms over a frame range (good as Source Wave tables or for `sg_function` lookup curves), but they are not the realtime stepping engine — the LFO CHOP "generates its waveform as it goes… unlike the Wave CHOP." (LFO CHOP — https://docs.derivative.ca/LFO_CHOP)

---

## 4. Componentization & reuse (.tox, COMP, params, ext, presets)

### Module shell: Base COMP
- A **Base COMP** is "the most basic shell of a component… used when a new network is required" — no panel/object gadgets. This is the correct container for headless signal modules (`sg_*`). (Component — https://docs.derivative.ca/Component)
- Components with **In/Out CHOPs** inside them expose left/right connectors so signal flows in and out; inputs left, outputs right, ordered alphanumerically by the In/Out op names. This is the in/out CHOP convention the `in/out` standard structure should follow. (Component — https://docs.derivative.ca/Component)

### .tox files
- A COMP saves to a **`.tox`** via RMB → Save Component; `.toe`/`.tox` are the hierarchical network file format (a `.toe` is the whole project, a `.tox` is one component subtree). To embed assets (images, help) into a `.tox` use the **Virtual File System (VFS)**. (Component — https://docs.derivative.ca/Component; TOX/Tox wiki pages are stubs with no body)
- An **Engine COMP** runs a `.tox` in a separate process — relevant later for offloading heavy signal graphs, not for MVP. (Component — https://docs.derivative.ca/Component)

### Custom parameters — hard naming constraints
- Custom params live on user-defined **Parameter Pages**; easiest via RMB → Customize…. (Custom Parameters — https://docs.derivative.ca/Custom_Parameters)
- **Constraints that bind the plan's param names:**
  - First letter **must be uppercase**, remaining lowercase; creation *fails with an error* otherwise. (Custom Parameters — https://docs.derivative.ca/Custom_Parameters)
  - **No underscores** allowed in parameter names. (Custom Parameters — https://docs.derivative.ca/Custom_Parameters)
  - Keep names **under ~12 chars (preferably 10)** or they're unreadable in the expanded UI. (Custom Parameters — https://docs.derivative.ca/Custom_Parameters)
- **Implication:** the plan's `BeatsPerBar` / `BarsPerPhrase` are valid casing but exceed the readable-length guidance (11 and 13 chars; `BarsPerPhrase` is 13). Consider shorter internal names with friendly *labels* (labels are free-form, e.g. "Bars Per Phrase"). Built-in TD params are all lowercase — your `BPM`/`Play`/`Stop`/`Reset` as *custom* params will read as `Bpm` etc. unless you reuse the component's built-in `play`. Flag for the plan.

### Extensions (the `ext` pattern)
- Python **Extensions** add data/functionality to a COMP — a list of Python objects on the Extensions page; accessed via the `.ext` member or, if **Promoted**, directly at the component level (`n.SomeFunction` vs `n.ext.SomeFunction`). Convention: capitalize the class name and suffix `Ext`. Up to 4 extensions per COMP, normally one class instantiated with `me` as arg, defined in a same-named DAT inside the COMP. (Extensions — https://docs.derivative.ca/Extensions; Time COMP Extensions page mirrors the param surface)
- Known gotchas the plan should design around: "Cannot use an extension during its initialization" (use `extensionsReady`/`onInitTD`), and extensions lingering in memory (use `onDestroyTD`). (Extensions — https://docs.derivative.ca/Extensions)

### Presets
- The Beat CHOP and many ops have built-in **parameter preset** machinery; for module-level presets the idiomatic options are TD parameter presets, the **`storage`** dict on a COMP (Extensions doc covers Storage Manager), and the Palette's preset patterns. (Extensions/Storage Manager — https://docs.derivative.ca/Extensions) — *(Palette preset specifics under-documented in the pages fetched; see Open Questions.)*

---

## 5. CHOP vs Python boundary

- **Default to CHOP networks for per-frame signal math.** CHOPs are native/compiled and time-sliced; they're the performance path. Python that runs per frame (Execute DAT, CHOP Execute DAT) is the documented escape hatch but the Logic CHOP page itself nudges you toward CHOP Execute DAT only for *event reactions*, not for streaming math. (Logic CHOP — https://docs.derivative.ca/Logic_CHOP; CHOP Execute DAT — https://docs.derivative.ca/CHOP_Execute_DAT)
- **Use Python (extensions / Script CHOP / Execute DATs) for:** state machines and cue logic (Timer CHOP callbacks), parameter orchestration, presets/storage, and module API surface — not for the hot per-sample loop.
- **Rule of thumb the evidence supports:** if it produces a continuous channel, express it as a CHOP chain; if it makes a *decision* or *changes parameters/state* on an event, put it in a CHOP Execute DAT or extension. `sg_*` modules should be CHOP-graph-first with a thin extension for API/preset/help.

---

## 6. Deterministic randomness / seeding

- **`tdu.rand(seed)`** returns a value in [0,1) and "for a given seed, it will always return the same random number." Seed can be a number, a string, or an OP (resolved to its constant path) — so `tdu.rand(me)` gives a stable per-op value across reloads, `tdu.rand(absTime.frame)` gives a new value each frame. This is the deterministic-seeding primitive for `sg_random`. (tdu module — https://docs.derivative.ca/Tdu_Module)
- **Noise CHOP** has a **`Seed`** param (any number → a different but characteristically-similar pattern) and explicit types covering the plan's `sg_random` menu: **Random** (= white noise; "every sample is random and unrelated"), **Brownian** ("like a bug in random flight," with Num of Integrals controlling acceleration randomization — this is the random-walk/brownian path), plus Sparse/Hermite/Harmonic Summation for smooth noise. Noise functions "continue uninterrupted" when the timeline wraps. (Noise CHOP — https://docs.derivative.ca/Noise_CHOP)
- **Caveat the plan must note:** Noise CHOP says Brownian and Harmonic Summation "cannot be limited to 1 [sample] in Time Slice mode" — i.e. exact reproducibility of brownian/harmonic across different frame-rate slicing is not guaranteed. White-noise/Sparse are clean under time slicing. For *strict* reproducibility (chaos/deterministic walk), drive a Python walk seeded with `tdu.rand` over a known time base rather than relying on time-sliced Brownian. (Noise CHOP — https://docs.derivative.ca/Noise_CHOP)
- "Chaos" has no native CHOP — it's a Python/expression implementation (e.g. logistic map) seeded deterministically; flag as build-it-yourself.

---

## 7. Envelopes (AR/AD/ADSR/looping)

- **The Trigger CHOP IS the envelope generator.** It "starts an audio-style attack/decay/sustain/release (ADSR) envelope" on every trigger pulse; the envelope has six sections (delay, attack, peak, decay, sustain, release). A trigger occurs when the input crosses the trigger threshold (default 0→1); release begins when the input drops below the release threshold. This directly implements `sg_env`'s gate+trigger→envelope contract. (Trigger CHOP — https://docs.derivative.ca/Trigger_CHOP)
- AR/AD/ADSR are achieved by zeroing the unused sections (AR = attack+release, no sustain hold); **looping** envelopes are achievable via re-trigger (Re-Trigger Delay param) or by feeding a periodic gate. The `Complete Envelope` param forces a full envelope per trigger regardless of early release. There are also instant `Trigger`/`Release` pulse params for manual firing. (Trigger CHOP — https://docs.derivative.ca/Trigger_CHOP)
- **Naming collision to flag:** TD's "Trigger CHOP" is an *envelope generator*, while aart-clock's "Trigger" signal type is a one-frame pulse. `sg_env` will be built *on* the Trigger CHOP; `sg_*` Trigger signals are produced by LFO-pulse/Logic-edge (§2). Document this so users aren't confused.
- For non-time-sliced full-curve preview, turn off Time Slice and disconnect input (per the Trigger CHOP note) — useful for the module's `demo`/`docs` waveform display.

---

## 8. Module standard / library structure (prior art)

- TD's own **Palette** is the canonical prior-art library: a browser of reusable Components shipped as `.tox`, plus user palettes. (Palette — https://docs.derivative.ca/Palette; page fetched but thin) The `sg_*` family should be distributable as a palette folder of `.tox` files.
- The In/Out CHOP convention (§4) is the de-facto module I/O standard; Info CHOP is the introspection standard (§9).
- Standard extension convention: `XxxExt` class in a same-named DAT, instantiated with `me`, optionally Promoted (§4). The plan's `internal` substructure + extension maps onto this cleanly.
- Versioning a `.tox`: TD has no built-in semver; convention is a custom string param (e.g. `Version`) plus VFS-embedded help text. (Inferred from Custom Parameters + Component VFS; no single doc page prescribes module versioning — see Open Questions.)

---

## 9. Testing / validation in TD

- There is no Jest equivalent. Observability primitives:
  - **Info CHOP** — attach to any op to read its state/Info channels (cook times, frame range, time-sliced flag, op-specific channels). The Timer/Beat/LFO/Noise pages all enumerate Info CHOP channels. (Info CHOP — https://docs.derivative.ca/Info_CHOP; per-op "Info CHOP Channels" sections)
  - **Trail CHOP** — the docs repeatedly recommend it to *watch a signal over time* ("attach a Trail CHOP to its output and alter the Frequency"; "Use a Trail CHOP to see its results"). This is the scope for visual signal verification. (LFO CHOP, Speed CHOP — https://docs.derivative.ca/LFO_CHOP, https://docs.derivative.ca/Speed_CHOP)
  - **Perform CHOP → Trail** to watch cook + time-slice-step channels and confirm frame-rate behavior. (Time Slicing — https://docs.derivative.ca/Time_Slicing)
- **Automated/headless testing is feasible but unidiomatic:** TD can run headless and Python can read CHOP values, so a Python-driven test that loads a `.tox`, steps frames, and asserts on channel values is buildable (Execute DATs + assertions). No first-party CI harness is documented in the pages fetched; treat CI as a build-it effort. (Inferred; see Open Questions.)
- **OP Snippets** (Help → Operator Snippets) are the canonical worked examples per operator and double as a validation pattern — referenced by Timer/Trigger/Time Slice pages. (Timer CHOP, Trigger CHOP — https://docs.derivative.ca)

---

## 10. Project / repo conventions

- `.toe` = whole project file; `.tox` = one saved component subtree. Both are binary by default. (Component — https://docs.derivative.ca/Component)
- **Current repo state (observed):** `/Users/krambuhl/Sites/aart-clock/.gitignore` ignores TD *backups* (`Backup/`, `*.toe.*.toe`, `*.tox.*.tox`, `*.toeBackup`, `*.toxBackup`), `local/`, dumps/logs, and OS cruft — but does **not** ignore `.toe`/`.tox` themselves. So the intent is to commit the binary `.tox`/`.toe` to git. (Observed: repo `.gitignore`)
- **Diffability problem:** committed `.tox`/`.toe` are binary blobs — opaque to PR review and merge-conflict-prone, which fights this repo's review-driven workflow. TD's mitigation is **externalizing DATs to text files** (scripts/extensions live as `.py`/`.txt` next to the `.tox`) so the *code* is diffable even if the network topology isn't. (Externalize wiki pages are stubs, but VFS/Externalize is the documented mechanism — Component VFS note; see Open Questions for the exact externalize workflow.)
- **Recommendation:** keep all `sg_*` Python in **externalized DATs** committed as text; commit `.tox` as the binary artifact; rely on Trail/Info-CHOP screenshots or a small Python "expand to text" dump for review context. This matches TD community practice (git + externalized scripts) even though Derivative's own "Working with Git" wiki page is an empty stub.

---

## Key decisions this implies for the plan

1. **Build `sg_clock` on a Time COMP + Beat CHOP, not Timer CHOP.** The Time COMP already owns BPM/Play/Signature; Beat CHOP turns it into beat/bar/phrase ramps + counters + pulses with global/local/sequential modes. Timer CHOP is for cues/one-shots inside `sg_env`-style logic. (Time COMP, Beat CHOP)
2. **Frame-rate independence = build on time-sliced CHOPs + read seconds/beats.** Do not count `me.time.frame` for timing; integrate rate over the time slice (Speed CHOP) so frame drops don't lose pulses. (Time Slicing, Speed CHOP)
3. **Triggers = LFO `Pulse` or Logic `Rising/Falling Edge`, kept in time-sliced CHOP-land.** Use CHOP Execute DAT only to *react* to a trigger in Python, never to stream it. (LFO, Logic)
4. **`sg_env` wraps the Trigger CHOP** (the native ADSR engine). AR/AD/ADSR = zeroed sections; looping = re-trigger / periodic gate. Document the name clash with the aart-clock "Trigger" signal type. (Trigger CHOP)
5. **`sg_random` = Noise CHOP (Seed param) + `tdu.rand` for deterministic seeding.** Strict-reproducibility walks/chaos go through seeded Python over a known time base, because Brownian/Harmonic can't be 1-sample-limited under time slicing. (Noise CHOP, tdu)
6. **Modules = Base COMP, In/Out CHOPs for I/O, `XxxExt` extension class, custom param pages.** CHOP-graph-first, thin Python extension for API/preset/help. (Component, Extensions, Custom Parameters)
7. **Custom param naming is constrained:** uppercase-first, no underscores, ≤~10–12 chars. Several plan param names (`BarsPerPhrase`=13) exceed the readable guidance — use short names + friendly labels, and reuse the COMP's built-in `play` where possible. (Custom Parameters)
8. **Commit `.tox` binaries but externalize all Python to text DATs** for review/diff sanity; the gitignore already commits `.tox`, so add an externalize step to the module build standard. (Observed gitignore; VFS/Externalize)
9. **Validation = Trail CHOP scopes + Info CHOP + OP Snippets**, with optional build-it-yourself headless Python frame-stepping tests. No native test runner exists. (Info CHOP, Time Slicing, per-op docs)
10. **Reconcile the six core signal types.** README lists Phase/Gate/Trigger/Value/Vector/**Color**; the plan brief lists Phase/Gate/Trigger/Value/**Bipolar**/Vector. These disagree — pick one before module APIs lock. (Observed README vs. plan brief)

---

## Open questions / unknowns

- **Exact externalize-to-text workflow** for `.tox` (Externalize All DATs / Save Backup as text): the relevant Derivative wiki pages (`Tox`, `TOX`, `Externalize_All_DATs`, `Working_with_Git`, `Best_Practices_for_Project_Organization`) are all empty stubs. Need the precise menu/CLI path and whether network topology (not just DAT code) can be expanded to text. Community tooling (e.g. git-friendly TD setups) likely exists but wasn't reachable via the docs wiki under current search constraints.
- **Module versioning convention** — no first-party prescription found; assumed a custom `Version` string param + VFS help. Confirm against the Palette component conventions.
- **Palette preset machinery specifics** — the Palette and preset patterns are under-documented in the fetched pages; confirm whether to use parameter presets, `storage`, or a Preset CHOP/palette component for `sg_*` preset support.
- **Headless/CI feasibility detail** — TD can run headless and Python can assert on CHOP values, but no documented first-party CI harness was found; the cost/shape of a real CI gate for `.tox` is unproven.
- **`sg_logic` Latch** — Logic CHOP has Toggle and Radio natively but not an explicit S-R latch; whether Latch needs a Speed/Hold helper chain is unconfirmed.
- **Swing/offset for `sg_divide`** — Beat CHOP Shift Offset/Shift Step cover staggering, but musical *swing* (uneven subdivision) may need a custom curve/lookup; not confirmed as a native one-param feature.
- **Search/forum coverage gap:** WebSearch and WebFetch were denied in this environment; findings rely on direct `curl` of `docs.derivative.ca` operator/Python pages. TD forum threads and third-party tutorials were not consulted, so community-idiom claims (git externalize practice, CI) are inferred rather than directly cited.
