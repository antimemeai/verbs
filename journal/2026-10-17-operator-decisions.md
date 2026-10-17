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

## Scope of invariant claims

Outcome of discussion on multi-object relations, re-entrancy, and concurrency.
Guiding stance: prefer a smaller domain with honest claims over contortions
for flexibility nobody has asked for. Programs outside the domain are
reported as "outside the claim", distinct from "unknown"; the subset is
neither hidden nor celebrated.

- Ownership: every invariant has exactly one owning subject and mentions only
  state that subject owns exclusively (value members, unique ownership).
  Mutation happens only through the owner's own operations, or through
  owner-issued handles whose operations are the owner's. A handle like that is
  a delegated transformation, not a leak. A raw mutable reference or pointer to
  invariant state is a leak. Relations without a single owner, of any arity
  including peer pairs, are refused with a structural suggestion (move both
  sides under one owner) or recorded as open_domain with rationale.
  `shared_ptr` co-ownership cannot host an invariant.
- Re-entrancy: no calls out to unowned code while the owner's invariant is
  temporarily broken. Restore first, then call out. This replaces modelling
  callback re-entry as a transformation kind.
- Concurrency: an invariant claim requires that the owner's transformations
  are serialized in a way the checker sees: thread confinement, or a
  capability held for every mutation (TSA GUARDED_BY, scope "while holding
  C"). Lock-free shared mutable state gets no invariant claim. No
  rely/guarantee machinery. Memory-ordering correctness is outside verbs'
  claims.

## Principle: basics first

Early verbs development defers complex cases of invariance. Not forever, and
possibly not for long, but the basics must be nailed absolutely before any
long side quest. When a design question only matters for a complex case, write
it down as deferred and move on; do not build machinery for it. The rules
above (ownership, re-entrancy, concurrency) already mark where the deferred
territory begins.

## Early-claim assumptions and tracking

The operator accepted that early claims assume no exception unwinds
mid-mutation and no moved-from object is used, provided this is very clear.
README.md now carries a claim boundary listing every assumption early claims
rest on; verbs must state them with each claim.

Tracking moved to bd (beads), prefix `verbs-`, at the operator's request.
AGENTS.md's GitHub-issues line and bd's injected boilerplate were replaced by
a pointer to ~/AGENTS.md. Every deferred or simplified case is a bead under
epic verbs-de3 (17 children), plus verbs-4ox (Rust phase) and verbs-b4x (Mull
on the pinned C++26 Clang). Labels: `deferred`, `simplification` (children
inherit `deferred` from the epic). The Dolt database has no remote; the
tracked .beads/backup/ JSONL export is the off-machine copy, refreshed with
`bd backup` before each commit. GitHub issue #1 (registry publications)
remains open and parked with utils/.

## First lint, fuzzing, and spec form

- First discovery lint: enum candidates (values compared or assigned against a
  small literal set across functions). Kind discovery follows once its
  precision problem is designed for.
- Fuzz testing is part of the verification strategy, purely for test-suite
  quality: libFuzzer with ASan/UBSan, structure-aware fuzzing of anything that
  parses, differential fuzzing of vlib arithmetic against a wide-integer model.
- The operator struck "often of the literate quint form" from the workspace
  BLACKBIRD.md. Designs are concrete prose and code; literate specification
  belongs to the future Becoming project.
- Design phase begins: design/SPEC.md for the basics, then an adversarial
  tribunal, then the plan.
