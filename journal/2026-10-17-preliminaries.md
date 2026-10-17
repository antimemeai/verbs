# Preliminaries: research lanes

Four lanes, each writing its report to papers/: C++ toolchain burdens, core
literature, agent-feedback/evaluation literature, reference implementations.

## Agent-feedback and evaluation lane (returned)

papers/2026-10-17-literature-agent-feedback.md; 43 PDFs plus one web post.
Bearing on open questions:

- The evidence favours pushing feedback at the edit boundary over an
  agent-invoked tool: pull tools go unused (3-22% of Kiro conversations; 0-6%
  of localization tasks used LSP).
- Push does not imply residency. The lane recommends a stateless
  `verbs check --changed` called from Blackbird's edit hook first, with a daemon
  only if measured cold per-TU latency on the corpus exceeds the per-edit
  budget. The daemon decision stays open until that measurement exists.
- Feedback loops raise gaming (ImpossibleBench). Suppressions, new escape
  hatches, and edits to verbs configuration should themselves be diagnostics.
- Experiment design: paired per-task arms plus a pull-versus-push arm; three
  defect classes (structural seeds, generic Mull mutants as a control,
  agent-introduced faults); oracles independent of verbs.

## Reference implementation lane (returned)

papers/2026-10-17-reference-implementations.md; 21 references in quarantine/,
intact ZIPs in quarantine/_archives/refimpls-2026-10-17/. All 21 archive
SHA-256 values in the report were rechecked against the files on disk. The
extractor is now scripts/extract-reference.py; re-extracting NamedType from its
archive reproduced the clean copy byte for byte. Merged the catalog and restore
procedure into quarantine-manifest.md.

Findings needing decisions: bounded::integer is close prior art for Bounded
and differs on bound-overflow handling, overlapping-range assignment (unchecked
UB), and a public value member. Mull's support matrix stops at LLVM 21 (macOS)
and 22 (Ubuntu), which conflicts with an LLVM 23 pin for mutation runs. These
went to the toolchain lane for verification, along with whether Clang 23
supports P2996 reflection, which magic_enum now uses.

## Core literature lane (returned)

papers/2026-10-17-literature-core.md; 44 PDFs. Read depth is marked per entry
(7 read in full, about 15 by method and results, the rest by abstract plus
targeted search). Unacquired items are in SHOPPING_LIST.md.

Findings that change the brief's footing:

- Visible-state semantics breaks under reentrancy (the reason Boogie
  introduced pack/unpack). Needs a callback/reentrancy transformation kind and
  an explicit statement of whose invariants a visible state assumes.
- Single-state predicates cannot state transition or monotonicity invariants;
  the vocabulary needs `old(.)`.
- The preservation-gap query silently assumes stability (an invariant breaks
  only when its own object is modified). Multi-object invariants need
  ownership or explicit dependency sets, or the core metric under-counts.
- Lackwit-style kind discovery collapses under arithmetic; Guo et al.'s
  interaction selection and DynComp are the known fixes.
- LLM invariant generation (ClassInvGen, Lemur) now beats Daikon. verbs' own
  role may be the refuter and the record, with Blackbird as generator.
- Parametricity does not carry over to C++ templates; the cache rests on
  build-systems theory (verifying traces with early cutoff), which works from a
  one-shot command with an on-disk store. Second lane pointing away from a
  mandatory daemon.
- `Bounded` widens on every operation, so loop accumulators cannot be typed;
  Wuffs-style fixed types with interval facts are the alternative.
- C++26 (approved 2026-03-28) has Contracts and Reflection. Homebrew Clang
  23.1.2 supports neither (lane probed -fcontracts, pre(), <meta>). Choosing
  Clang + C++23 is now an explicit tradeoff against GCC 16 or a reflection fork.
- Also reported: Homebrew Clang 23's default sysroot names a missing
  MacOSX26.sdk (toolchain lane).

## C++ toolchain lane (returned)

papers/2026-10-17-cpp-toolchain-burdens.md, with source-line citations and
probe output. Archive SHA-256 rechecked; manifest entry merged. Summary:

- No LLVM source build is needed. The Homebrew bottle ships the LibTooling
  CMake config, clang-tidy headers, and the static clangd libraries. A probe
  LibTooling tool, tidy plugin, and custom clangd built together in 10.5 s.
- Homebrew clang 23 cannot compile here as installed: its config names a
  missing MacOSX26.sdk. Presets must set CMAKE_OSX_SYSROOT from xcrun
  (Blackbird already does).
- Pin hygiene: `llvm@23` currently aliases `llvm`, nothing is pinned, and
  23.1.3 is pending. Plugins carry no ABI promise; rebuild on any LLVM change.
- clangd cannot load tidy modules at runtime; a custom clangd is cheap but
  needs `FastCheckFilter: Loose` or unknown checks are silently dropped.
  clangd sends `version` in publishDiagnostics unconditionally.
- Mull 0.34.2 stops at LLVM 21 (macOS) / 22 (Ubuntu). Mutants need the same
  Clang major as the build: port Mull to 23 on the fleet, else an LLVM 22
  mutation profile.
- Clang 23 has no P2996 reflection; VERBS_ENUM must generate its own arrays.
  The installed GCC 16.2 supports enumerators_of.
- consteval BFS tops out near 7.5k states at default limits; 100k states
  take 5-22 s with limits lifted.
- Corpus: blackbird matches the pin (clang 23.1.2, C++23). Oxcart is mostly
  Rust plus Apple-clang C++20/ObjC++. BRepGPU is C++17, clang 18, libstdc++,
  Linux. vlib's C++23 types cannot land in the latter two without a standard
  bump; lints can still parse them.
- Disk: 70 GiB free (97% used) is the binding local constraint.
- Latency on blackbird (257 TUs): warm clangd edit 0.55-3.0 s; cold clang-tidy
  with a trivial check 1.4-3.8 s; the repo's own clang-analyzer config 2.4-76 s.
  Warm clangd wins by 1.5-2.5x, and main-file reparse dominates, not tidy.
  Header-fanout edits are unmeasured; Oxcart and BRepGPU need their own
  configure runs to produce compile_commands.json, which the lane did not do.
