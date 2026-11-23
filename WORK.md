# Work

Open work for verbs. Beads was retired on 2026-11-23
(journal/2026-11-23-retire-beads.md); this file replaced it. The old bead
names are kept as labels so references in SPEC.md, journal/ and papers/
still resolve. They are labels, not keys.

Edit this file directly: add an entry when work is found, delete it when the
work is done, and record the outcome in journal/.

## Active

### verbs-2or: Corpus runs: enum migration script, fault seeder, project list

*P1 · task*

SPEC §1.1 and §10.3. Migrate scoped fixed-underlying enums that name 0 to VERBS_ENUM in open-source C++ projects that build with the pinned Clang at -std=c++2c; seed every prevented and detected class at recorded sites; any missed seed or false finding is a bug. Also feed real commit histories to the incremental-equals-scratch oracle (§10.2). Part of increment E.

**Notes.**
2026-10-18: 318 of 755 fetched (12 GB); 437 listed in context/corpus/unfetched.tsv, fetch paused for disk. probe.py now deletes each extracted tree after probing (tarballs are the source of truth). Probe running over the 318.

### verbs-b4x: Mull mutation testing on the pinned C++26 Clang

*P2 · task*

Mull 0.34.2 supports LLVM 16-21 (macOS) and up to 22 (Ubuntu); mutants must compile with the same Clang major as the build (papers/2026-10-17-cpp-toolchain-burdens.md). Operator: upgrade rather than lower pins, so port Mull to whatever Clang the C++26 lane selects. Needed for the kill-criterion experiment.

### verbs-g5w: Escape rule for conversions libc++ performs for the caller (substituted template parameters)

*P1 · task*

SPEC §4.1 rule 2 and §12 Q5. Eight programs convert E* to void* inside libc++ generic code with no cast in the analyzed code: vector<void*>::emplace_back(&e), std::copy into void**, function<void*()>, optional<void*> from optional<E*>, out_ptr<void*>, atomic_ref::address, invoke_r<void*>, and pair conversion. Each writes 7 into a {0,1} enum. Evidence: context/prototypes/libcxx-alias-scan/REPORT.md §2b.

Candidate rule R: inside a libc++ instantiation reached from an analyzed call site, a cast is a finding when either (a) its source is a vpr and its destination's outermost SubstTemplateTypeParmType replacement is a pointer-like to a different pointee, or (b) the reverse direction holds (q05 needs b). Verbs enums count as vlib-carrying. Attribution follows calls, constructors, temporary destructors, address-taken functions and virtual methods out of application code.

To test: all of q01-q08, p12, p16, p18 and p24 fire; the same-type controls (benign internal hits: allocation, construct_at, relocation, ASan annotations, any's small buffer) and escape-v2 legit/ stay at zero; coverage cases through decltype/auto chains, any/function, ranges, tuple_cat, bind, variant, apply and make_from_tuple.

A subagent's two attempts at this test were stopped by a safety classifier, so the operator decides how it runs.

## Deferred

Cases the basics leave out on purpose (SPEC §14, README claim boundary).
Each carries the `deferred` or `simplification` label.

The former umbrella, verbs-de3, read: cases deferred under the basics-first
principle (journal/2026-10-17-operator-decisions.md). Each records what early
claims assume in its absence.

### verbs-4ox: Rust phase: native realizations on Oxcart and rhizome

*P3 · epic · deferred*

C++ first (journal/2026-10-17-operator-decisions.md). Rust gets its best native realization, not parity: ownership instead of Consumed, zero-sized tokens instead of TSA, Flux (liquid types) considered over waiting for generic_const_exprs (papers/2026-10-17-literature-core.md). Rust corpus: Oxcart (~/projects/bow_shock) and rhizome. Rust refimpls (Stateright, Kani, Dylint, bolero, loom, shuttle, salsa) were deferred by the refimpl lane.

### verbs-de3.1: Two-state predicates and old values (nondecreasing, increasing, grow_only, transitions)

*P3 · feature · deferred*

Basics cover single-state invariants plus const for unchanged. Deferred: named two-state predicates (no general old()), with the old value supplied by (1) vlib types whose operations preserve the relation, e.g. Monotonic<T>; (2) the static checker treating old as entry state of the judged transformation; (3) test builds where reflection snapshots annotated fields at mutator boundaries (Daikon orig()). Never shadow state in user objects. C++26 postconditions cannot name entry values; P3098R2 proposes captures post-C++26 (papers/wg21-p3098r2-postcondition-captures.pdf). Early claims: no relational claims across a mutation except const.

### verbs-de3.2: FSM checking: declared constexpr tables, consteval exploration, runtime counterexample

*P3 · feature · deferred*

Brief §4.7. consteval BFS tops out near 7.5k states at default constexpr limits; 100k states take 5-22 s with limits lifted (papers/2026-10-17-cpp-toolchain-burdens.md). Needs a decision on dedicated TUs and the TLC export threshold. Boost.MSM is prior art for compile-time structural checks (papers/2026-10-17-reference-implementations.md). Early claims: no FSM safety claims.

### verbs-de3.3: Trace validation of implementations against declared FSM tables

*P3 · feature · deferred · blocked by verbs-de3.2*

Implementation emits (from, event, to) events under test; the checker compares observed traces to the declared table. Works when code is driven by the table (CCF succeeded; MongoDB's attempt failed, papers/2026-10-17-literature-core.md). etcd-raft's build-tagged trace emission is the reference pattern.

### verbs-de3.4: Dynamic observation: candidate-driven test-build instrumentation

*P3 · feature · deferred*

Daikon-style value observation of fields flagged by static lints, in test builds only, to raise lint confidence. The brief's Clang Rewriter approach may be replaced by C++26 reflection over annotated fields. Early claims: static evidence only.

### verbs-de3.5: Lock-scoped invariants (holds while holding capability C)

*P3 · feature · deferred*

Concurrency rule (journal/2026-10-17-operator-decisions.md): claims need serialized transformations, either thread confinement or a capability held for every mutation (TSA GUARDED_BY). Basics cover confinement only; checking the lock-scoped case is deferred. Early claims: invariant-bearing owners are used from one thread at a time.

### verbs-de3.6: Lock-free shared mutable state is outside the claim; memory ordering never claimed

*P4 · task · deferred · simplification*

Simplification (journal/2026-10-17-operator-decisions.md): no rely/guarantee machinery. verbs reports lock-free shared state as outside the claim (distinct from unknown). Revisit only if a real use demands it.

### verbs-de3.7: Owner-issued handles delegating a subset of owner operations

*P3 · feature · deferred*

Ownership rule (journal/2026-10-17-operator-decisions.md): a handle whose only operations are the owner's is a delegated transformation, not a leak. Basics treat any mutable path out of the owner as a leak; distinguishing handles is deferred. Early claims: the leak lint may flag legitimate handles.

### verbs-de3.8: Ownership beyond value members (unique_ptr graphs, containers owning nodes)

*P3 · feature · deferred*

Basics: an invariant mentions only the owner's own value members. Deferred: exclusive ownership through unique_ptr and owning containers. Early claims: invariants cannot mention state reached through owning pointers.

### verbs-de3.9: Relations without a single exclusive owner are refused (peer pairs, shared_ptr)

*P4 · task · deferred · simplification*

Simplification (journal/2026-10-17-operator-decisions.md): any arity, peer pairs included. verbs emits a structural suggestion (move both sides under one owner) or records open_domain with a rationale. Revisit only with a concrete need.

### verbs-de3.10: No calls to unowned code while the owner's invariant is broken

*P3 · task · deferred · simplification*

Simplification (journal/2026-10-17-operator-decisions.md): re-entrancy is banned, not modelled. Basics need a check for the rule (call-outs during a mutation of invariant state). The brief's callback/re-entry transformation kind is not built.

### verbs-de3.11: Exception unwinding preservation (basic/strong guarantees)

*P2 · feature · deferred*

Brief §2, lint verbs-unwind-preservation. Abrahams/Arnold exhaustive throw injection is the dynamic oracle (papers/2026-10-17-literature-core.md). EARLY CLAIMS ASSUME NO EXCEPTION UNWINDS MID-MUTATION; every claim must state this visibly.

### verbs-de3.12: Moved-from state as a declared weakening

*P2 · feature · deferred*

Brief §2: model valid-but-unspecified moved-from objects as invariants with scope moved_from. EARLY CLAIMS ASSUME NO USE OF MOVED-FROM OBJECTS; every claim must state this visibly. Phantom typestate cannot prevent moved-from use in C++ (brief §4.5).

### verbs-de3.13: Edit-keyed incremental cache (verifying traces, preservation_dep)

*P3 · feature · deferred · blocked by verbs-de3.14*

Brief §7-8. Build-systems theory (verifying traces with early cutoff) works from a one-shot command with an on-disk store (papers/2026-10-17-literature-core.md). Basics: stateless verbs check recomputes.

### verbs-de3.14: Measure verbs check latency including header-fanout edits on the corpus

*P3 · task · deferred*

Blackbird numbers exist for main-file edits (papers/2026-10-17-cpp-toolchain-burdens.md). Header edits that touch many TUs are unmeasured. BRepGPU needs a compile_commands.json generated first. Decides whether the cache or anything resident is needed.

### verbs-de3.15: Daemon: revisit only if measured latency exceeds the per-edit budget

*P4 · decision · deferred · simplification*

Decision (journal/2026-10-17-operator-decisions.md): no daemon. Feedback is pushed at Blackbird's edit boundary by a stateless command. Revisit only on measured evidence.

### verbs-de3.16: Optional LLM-proposed invariants as one more candidate source

*P3 · feature · deferred*

Rule (journal/2026-10-17-operator-decisions.md): no terminal LLM dependency. Model proposals enter the same refuter and ledger as owned generators; everything works with no model available. ClassInvGen and Lemur are prior art.

### verbs-de3.17: Cross-field invariants on mutable owners (static checking of each mutator)

*P3 · feature · deferred*

Basics express cross-field invariants only as whole-value Refined aggregates, replaced wholesale (design/SPEC.md §2.1). Mutable owners need each mutator judged against the invariant. Early claims: no cross-field claim on a mutable object.

### verbs-de3.18: Bounded beyond int64: 128-bit bounds and unsigned values above INT64_MAX

*P3 · feature · deferred · simplification*

Basics bound Bounded to std::int64_t (design/SPEC.md §3.1). bounded::integer supports up to 128-bit signed and unsigned bounds (quarantine/bounded-integer).

### verbs-de3.19: Kinds with arithmetic: point/difference pairs (timestamp/duration, index/offset)

*P3 · feature · deferred*

Basics Id<Tag,Rep> has equality and ordering only (design/SPEC.md §3.3). strong_type affine_point/difference is the prior art; kind discovery should be able to propose the split.

**Notes.**
Basics dropped vlib Id: blackbird's own Id (foundation.hpp:87) is stronger, with checked from_bytes and a private constructor (tribunal ergonomics M5). Kind work must recognize existing strong types.

### verbs-de3.20: Decision sidecar for code the team cannot edit (vendored, generated)

*P4 · feature · deferred*

Basics record decisions in source on the declaration (design/SPEC.md §7). Add a sidecar format only when a corpus repo needs it. Not JSON (BLACKBIRD.md).

### verbs-de3.21: Kind-discovery check (usage-based inference with an explicit interaction definition)

*P2 · feature · deferred*

Highest-value lint in the brief, deferred behind enum-candidate. Lackwit merged ~65% of integer queries via arithmetic chains; Guo et al.'s units-mode interaction definition and DynComp are the known fixes (papers/2026-10-17-literature-core.md §1).

### verbs-de3.22: Typestate: Clang Consumed analysis and phantom-state templates

*P3 · feature · deferred*

Brief §4.5. Consumed tracks only unknown/consumed/unconsumed. Phantom typestate cannot prevent moved-from use in C++. Not in basics vlib (design/SPEC.md §3.5).

### verbs-de3.23: Authority capabilities via Clang Thread Safety Analysis

*P3 · feature · deferred*

Brief §4.6. Probed working on non-mutex types (papers/2026-10-17-cpp-toolchain-burdens.md). Capabilities must be named expressions; conditional holding is inexpressible (Hutchins 2014).

### verbs-de3.24: Remaining first-wave lints: bool-cluster and repeated-guard

*P3 · feature · deferred*

Brief §6 lints 3-4. Basics ship escape and enum-candidate only (design/SPEC.md §4-5).

### verbs-de3.25: Editor-time verbs: clang-tidy module adapter and custom verbs-clangd

*P4 · feature · deferred*

Basics ship one verbs binary (design/SPEC.md §6). A custom clangd is cheap to build but needs FastCheckFilter: Loose (papers/2026-10-17-cpp-toolchain-burdens.md burden 4).

### verbs-de3.26: Contracts as the obligation vocabulary; evaluate the contracts branch

*P2 · feature · deferred*

Operator ranks contracts above reflection for verbs' purpose. Next phase: report which pre/post checks vlib types discharge (e.g. pre(n >= 1) on a Bounded<1,5> parameter is discharged by the type). Evaluate efcs/llvm-project contracts-review-20261009 (LLVM 24-dev) or upstream #221139 by building it in context/ and probing pre/post/contract_assert through LibTooling. Contracts never carry vlib representation invariants (ignore semantic). design/SPEC.md §8.

### verbs-de3.27: Reflection replaces VERBS_ENUM arrays

*P3 · task · deferred*

When the pinned Clang has P2996, enumerators_of generates VERBS_ENUM's value and name arrays; macro syntax unchanged. clang-p2996 probe in papers/2026-10-17-cpp26-clang-toolchain.md. design/SPEC.md §3.2.

### verbs-de3.28: Refined over deep value types

*P3 · feature · deferred*

Deferred from basics: no corpus consumer (tribunal doctrine D12). Requirements recorded by the tribunal: T must be a deep value type (no views, pointers, reference semantics, mutable members; soundness B7, doctrine D8); predicates must not read mutable static state (soundness M8); Pred::id mandatory, static lambdas otherwise pass the shape (doctrine D24); ingress via verbs::to returning optional (ergonomics m3).

### verbs-de3.29: Pointer-equality string comparison check (const char* == literal)

*P3 · feature · deferred*

Correctness check found by the checks tribunal (M5): const char* compared to a string literal with == compares pointers. Separate from enum candidates.

### verbs-de3.31: C++ modules in analyzed units

*P4 · feature · deferred*

Units importing modules are outside in the basics (checks tribunal M7); needs the build's BMIs.

### verbs-de3.32: Facts shared across worktrees (constructive traces)

*P4 · feature · deferred*

Key facts by input hashes so a new worktree or build directory reuses them instead of paying a full scan (checks tribunal M11).

### verbs-de3.33: Points-to narrowing of escape attribution

*P4 · feature · deferred*

Basics attribute an escape to every declaration of the affected type program-wide (soundness M7, design/SPEC.md §4.4). Narrow with a points-to analysis when one exists.

### verbs-de3.34: Shared job slots across concurrent verbs processes

*P3 · task · deferred · simplification*

Concurrent verbs check runs in different build directories or worktrees each start their own extraction jobs; on a loaded host (load ~95 observed) they multiply. Basics: each process takes its own jobs; per-build-dir lock only. Later: a machine-wide job semaphore. From checks tribunal M11, confirmed open by the Jev coverage audit 2026-10-17.

### verbs-de3.35: Enum-domain discovery (scan-only)

*P3 · feature · deferred*

Redesigned enum-candidate rule from papers/2026-10-17-enum-candidate-redesign.md (paste-ready text in its 'The rule, as spec text' section). Removed from the basics 2026-10-17: held-out precision of the edit-boundary tiers was 46% frozen and 62% after the loader fix on BRepGPU, against a bar of no effective false positives; Jev agreement was at chance (kappa 0.17 / -0.01). Settled points carried over from SPEC rev 3 §5: never gates; at most one per delta; observed values are a lower bound, so never propose verbs::to over the observed set; tier E (subjects fed from an existing enum) is the cheapest precise follow-up. Revisit with runtime observation (DynComp/Daikon-style) and a corpus that uses vlib. Decisions (VERBS_OPEN_DOMAIN, the exit-3 gate, in-source placement per the operator decision) return with this bead, since they apply only to proposals. Artifacts: context/prototypes/enum-lane/.
