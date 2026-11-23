# Post-mortem: the verbs basics design (SPEC revisions 1–4)

Written 2026-11-23 when the operator scrapped design/SPEC.md and kept the
idea. Sources: design/SPEC.md, journal/2026-10-17-*.md, and the October
papers cited below. Facts come with sources. Points marked *(reading)* are my
interpretation.

## What it was

Three parts, scoped to "the basics":
- **vlib.** Closed C++ value types: `VERBS_ENUM` with checked ingress
  `verbs::to<E>`, and `Bounded<Lo, Hi>`.
- **An escape check.** It established that nothing bypassed vlib.
- **`verbs check`.** A stateless command run at each edit. It reported each
  declaration as `holds`, `finding` or `outside`.

The claim was soundness: "every value of D satisfies P, under the claim
boundary."

## Why it stalled *(reading)*

- **The guarantee rested on proving that nothing bypasses a type.** In C++
  that proof never closes.
  - The first tribunal produced 17 compiled counterexamples against a
    deny-list of spellings (papers/2026-10-17-tribunal-soundness.md).
  - The allowlist (escape-allowlist.md) and provenance-as-type
    (escape-allowlist-v2.md) caught every case then known.
  - Each later review round still produced new ones:
    - MiMo round 2: 4 cases;
    - ChatGPT round 2: 8 blockers, all through exemptions or lists "closed
      by argument";
    - the libc++ scan: 8 programs that convert `E*` to `void*` inside the
      library, with no cast in the user's code.
  - Every fix added machinery: cross-unit signatures, attribution closures,
    a mechanically derived libc++ table and a re-derivation test.
- **The payload was small next to the machinery.** The guarantee covered
  closed enums and bounded integers. Strict switch warnings, checked
  decoding seams and UBSan already cover much of that.
- **There was no habit-level guidance.** The basics deliberately had no
  discovery and no annotations. That leaves the agent's most common failure
  unaddressed: not using the construct in the first place.
- **There was no way to add a habit.** Each new kind of invariant would have
  meant a new spec section and new checker machinery.

## Facts that carry over

**Toolchain** (papers/2026-10-17-cpp-toolchain-burdens.md,
cpp26-clang-toolchain.md):
- The Homebrew LLVM 23.1.2 bottle ships the LibTooling CMake config, the
  clang-tidy headers and the static clangd libraries. A LibTooling tool, a
  `-load` tidy plugin and a custom clangd built together in 10.5 s. No LLVM
  source build is needed.
- Plugins carry no ABI promise and must be rebuilt on any LLVM change.
- clangd cannot load tidy modules at runtime. A custom clangd is cheap, but
  it needs `FastCheckFilter: Loose` or unknown checks are dropped silently.
- Homebrew's clang config names a missing MacOSX26.sdk. Builds pass the
  Xcode SDK explicitly.
- Clang 23 has neither P2996 reflection nor contracts.
  - The bloomberg/clang-p2996 fork costs an 83-minute build and about 5 GiB.
    It has 85 open issues and rejects some valid code.
  - Merging contracts into it conflicts in 106 files.
  - GCC 16.2 has both features, but every analysis verbs runs is
    Clang-only.
- Mull 0.34.2 stops at LLVM 21 on macOS and 22 on Ubuntu.
- Latency on blackbird's 257 units:
  - warm clangd edit: 0.55–3.0 s;
  - cold clang-tidy with a trivial check: 1.4–3.8 s;
  - main-file reparse dominates the cost.

**Agents and feedback** (papers/2026-10-17-literature-agent-feedback.md):
- Tools an agent has to choose to call go mostly unused:
  - 3–22% of Kiro conversations;
  - 0–6% of localization tasks used LSP.
  Feedback pushed into the agent's existing loop is what gets used. The new
  design's compiler/linter channel is exactly that.
- Feedback loops invite gaming (ImpossibleBench). Suppressions, new escape
  hatches and edits to the checker's configuration should themselves raise
  diagnostics. This bears directly on "a way past, with a reason".

**Detection precision** (papers/2026-10-17-enum-candidate-redesign.md):
- The "should be an enum" rule was tuned on blackbird and measured on
  held-out BRepGPU:
  - edit-boundary tiers: 6/13 precision, and 5/8 after a loader fix;
  - recall: 6.6%.
- The surviving false findings (a version number, a count, a bit mask)
  could not be told apart by how the value was used.
- Jev labelling was at chance (κ 0.17 and −0.01).
- Lesson for nudges: usage patterns alone may not separate true from false.
  A nudge has to be cheap to dismiss, and its rule must be one an agent can
  argue with.

**Bounded types** (papers/2026-10-17-literature-core.md, SPEC §3.3):
- `Bounded` widens its range on every operation, so loop accumulators can't
  be typed. Wuffs-style fixed types with interval facts are the known
  alternative.
- C++26 contracts' `ignore` semantic lets a value break a representation
  invariant, so contracts can't be what enforces a bounded type.

**Ownership and scope** (journal/2026-10-17-operator-decisions.md): the
operator's stance still reads well for habits that carry state. Prefer a
smaller domain with honest limits. Invariants have one owner. No calls out
while an invariant is broken. Concurrency only where the checker can see the
serialization.

**Corpus** (context/corpus/, quarantine-manifest.md):
- 755 projects selected; 318 fetched as tarballs.
- 131 probed: 32 configure, 50 fail to configure, 49 have no CMake.
- Fetching paused for disk space.

## Process lessons

- **Tribunal rounds found real holes every time.** Each round compiled its
  counterexamples and ran them under sanitizers. Keep that practice of
  running counterexamples rather than arguing them.
- **Lists "closed by argument" failed every time.** Derive lists
  mechanically or don't claim they are closed.
- **Safety classifiers stopped subagents** under both adversarial and
  correctness framings of the libc++ rule test (journal, 2026-10-18).
  Prompts for checker testing must stay plain.

## What the new design should take *(reading)*

1. Stops grade evidence; they don't claim soundness.
   - A misused construct, or an obvious bypass spelling such as a cast to
     an enum or a `reinterpret_cast` into a construct, is a stop.
   - Proving that no path at all bypasses a type is not the goal.
2. Every finding has a way past it with a reason. Adding or editing one is
   itself visible, which answers the gaming risk.
3. A habit is a unit that can be added without redesign: a construct,
   stops, nudges, ways past and seeded faults, declared once and realized
   per language.
4. Feedback goes through the compiler and linter the agent already runs.
   The toolchain facts above say a clang-tidy plugin plus a custom clangd
   is cheap on the pin.
