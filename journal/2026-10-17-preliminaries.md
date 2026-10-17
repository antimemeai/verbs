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
