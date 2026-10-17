# Operator decisions after first review

Responses to the first review of design/verbs-design-brief.md against
BLACKBIRD.md. They supersede the brief where they conflict.

- Nothing in the brief is settled, including its §1. The brief helps us get
  organized and oriented; it is not a directive. Its claims face research and a
  tribunal like any other input.
- Decisions ledger: not JSONL. Design a format that is more efficient and
  sucks less.
- Python is acceptable for shop tooling but is being phased out, including as
  a helper to main processes. Whether a persistent daemon is needed at all is
  reviewed after the preliminaries. If there is one, it is C++.
- SQLite, asyncio, serde and similar established libraries are acceptable
  after an explicit architecture choice. Preference: the repository documents
  itself rather than needing SQLite to be understood.
- Toolchain: take one stance and keep it. Building everywhere, or even
  conveniently, is not a goal. Investigate what the C++ toolchain actually
  forces on us.
- The published 0.1.0 packages stay up as placeholders.
- Registry notes and release tooling go into a utils/ junk drawer, addressed
  when they come up.
- The brief moves into the repository (design/).
- Evaluation corpus: blackbird, Oxcart (~/projects/bow_shock), BRepGPU.

Actions: moved scripts/publish.py, scripts/check-registries.py, REGISTRIES.md
and packaging/ (Conan/vcpkg drafts for the placeholder header) into utils/.
publish.py still resolves the repository root as its parent's parent. Moved the
brief to design/ and prefaced it with the not-settled note. Rewrote README.md
for the current state.

Preliminaries launched as four research lanes, each writing its report to
papers/: C++ toolchain burdens (acquiring llvm-project source), core
literature, agent-feedback/evaluation literature, and reference
implementations. Manifest and shopping-list entries merge on their return.
