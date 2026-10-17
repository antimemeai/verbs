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
