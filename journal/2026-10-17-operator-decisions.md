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

## Second round (after the research lanes)

- No daemon. Feedback is pushed at Blackbird's edit boundary by a stateless
  command with an on-disk cache.
- All C++ code is C++26. Upstream Clang (trunk included) lacks P2996 and
  P2900; GCC 16 has both, but verbs' analyses are Clang-only. Reflection lives
  in bloomberg/clang-p2996, contracts in efcs/llvm-project branches. A lane is
  measuring what building and owning a C++26-capable Clang costs here.
- Toolchain: upgrade to what it should be rather than lowering pins. Pinned
  Homebrew llvm (23.1.2) so nothing upgrades by accident: blackbird's preset
  hard-codes Cellar/llvm/23.1.2. The CLT update (MacOSX26.sdk) needs sudo;
  the operator runs it.
- Rust corpus: Oxcart (bow_shock) and rhizome. C++ corpus: blackbird, BRepGPU.
- Invariants carry the properties they are supposed to have, not every
  property. Checkers judge declared aspects only; an absent aspect is not a gap.
- No part of verbs may depend terminally on an LLM. LLMs are first-class users
  and may propose invariants, but the operator cannot guarantee GPU capacity,
  so every function must work with no model available. Owned generators
  (usage-based kind inference, candidate-driven observation,
  generate-and-refute) are the baseline; model proposals enter the same
  refuter and ledger as one more source.
- Old values: C++26 postconditions cannot refer to entry values (P3098R2,
  "Postcondition captures", May 2026, proposes it post-C++26; PDF in papers/).
  Design direction under discussion: old values exist only inside the
  mechanism judging a transformation, never as state in user objects.
