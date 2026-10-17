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

## Design draft

design/SPEC.md drafts the basics from the brief, the four lane reports, and
the operator's decisions. Main choices, each argued in the spec and offered
to the tribunal:

- The vlib type of a declaration is its invariant declaration; no invariant
  annotation syntax. Operator principle, added mid-draft: annotations clarify
  and never encumber. If a finding could only be silenced by an annotation
  stating the obvious, fix the check.
- Report states are holds / finding / decided / outside; no "unknown" for
  examined declarations.
- Bounded widens on binary ops and narrows on compound assignment with an
  always-on check. C++26 contracts are unsuitable here because the `ignore`
  semantic would let an out-of-range value break the representation
  invariant and the accessor's [[assume]].
- Enum ingress must be checked (to_enum); integer-to-enum casts are escapes.
- Decisions live on the declaration (clang::annotate now, P3394 later) instead
  of a file. This retires USR keying and orphans. [operator to decide]
- verbs check tracks affected units through its own recorded include sets
  and keeps per-unit facts files only; no preservation cache in the basics.
- vlib basics keep macro fallbacks so they ship even if the C++26 Clang fork
  proves too costly.

Filed beads verbs-de3.17 to .25 for the cases the spec defers (§13).

## C++26 Clang lane (returned)

papers/2026-10-17-cpp26-clang-toolchain.md. Recommendation: bloomberg/clang-p2996
at f17c8d6c7bfe (2026-09-24) for all verbs C++, built locally by
context/toolchain-cpp26/build-p2996.sh. Measured: 83 min full Release build,
about 5 GiB total, 77 s incremental after a Sema change. Probed on it:
reflection-generated enum domains (finds Reserved = 200), annotations read by
reflection, a generic before/after check over annotated fields, LibTooling, a
-load tidy plugin, a custom clangd, TSA and Consumed.

No contracts: merging the efcs contracts branch (LLVM 24-dev) into the fork
(LLVM 21.0.0git, 59,939 commits behind main) conflicts in 106 files and 263
hunks. That is compiler maintenance, not setup; revisit when upstream lands
contracts (#221139) or reflection (#232074). The basics already avoid
contracts for representation checks (SPEC §3.1). The fork rejects some valid
code GCC 16.2 accepts, has 85 open issues including crashes, and its API names
predate the standard, so vlib uses a small shim. Mull's macOS range (LLVM
16-21) covers the fork's base, so Mull likely needs a path change rather than
a port.

## Tribunal (three of four returned)

Doctrine/value, soundness, and ergonomics reports are in papers/. Headline:
the escape check as a deny-list of spellings is unsound (17 compiled
counterexamples, e.g. fread into a vlib object, Mode m{raw}, template
specialization access); Bounded is not ready for index/loop code; Id adds
nothing over blackbird's own; seen() on decisions is shadow accounting; the
spec has no stated path to the kill criterion. Revision waits on the checks
and pipeline report.

## Spec revision 2 (tribunal fixes; two sections await research lanes)

All four tribunal reports read in full. design/SPEC.md rewritten as revision
2. Calls made (each cites its finding in the spec):

- Kill path stated (doctrine D1): treatment is blackbird migrated at its
  decoding seam; BRepGPU outside the basics; experiment bead verbs-de3.30.
- Vocabulary cut to range and in{}: Id dropped (blackbird's is stronger),
  Refined deferred to verbs-de3.28 with the tribunal's deep-value
  requirements, const and mechanism sets cut (no consumer).
- One ingress verb verbs::to<T> returning optional; libc++ hardening >= FAST
  joins the claim boundary so `*` on empty traps. Boundary gains no-UB-
  outside-vlib, -Werror=switch-enum/uninitialized (read from the compile
  command), constinit statics.
- Violations throw verbs::violation before store (strong guarantee); no hook.
- Verbs enum = VERBS_ENUM only, with name = value support; zero rule; narrow
  bit-fields are escapes.
- Bounded: k<V>, upto(n), implicit egress, raw-operand +=/-=, all bound math
  and checks in __int128, smallest signed-or-unsigned storage, deleted
  conversions with reasons. Lands only when a blackbird declaration is named.
- Escape check: allowlist direction recorded; rule text awaits the
  escape-allowlist lane. Silencing list by effect; lost claims print `!`;
  attribution coarse (type-wide).
- Enum candidates: advisory, never gate, observed values are a lower bound;
  rule text awaits the enum-candidate lane.
- verbs check: verifying traces (command hash, inputs, negative probes) make
  `--changed` a hint; USR/path keys; lock and atomic writes; compile-error
  units keep facts; latency budget p95 <= 10 s with an honest pending line.
- Decisions: VERBS_OPEN_DOMAIN("why") only; exit 3 gates additions on
  operator approval.
- Toolchain: Homebrew LLVM 23.1.2 with -std=c++2c (C++26 as far as upstream
  goes; blackbird's move is a flag change). clang-p2996 kept for experiments;
  contracts evaluation is verbs-de3.26.
- Verification: enumeration-model bound oracle, named fuzz grid, literal enum
  expectations, concept-form rejections, -verify for messages only, source
  mutants for compile-time logic, audit build as an independent escape
  oracle, generator with out-of-band changes.

Beads verbs-de3.26 to .33 filed; verbs-de3.19 annotated.

Incident: bd failed with "database verbs not found". Cause: verbs' Dolt
server had stopped, and antimeme_site's bd server took the shared default
port 3307, serving its own data directory. verbs' data was intact in
.beads/dolt/verbs. Fix: dedicated `dolt.port: 13309` in .beads/config.yaml
(blackbird and arconaut use 13308). Other repos on the default port remain
exposed to the same collision.

## Escape-allowlist lane (returned)

papers/2026-10-17-escape-allowlist.md. Rule: vlib bytes are written or created
only by vlib members and factories or by same-type copy/move; everything else
(type erasure, re-typing, bit reinterpretation, raw writes, unions, asm,
enum IntegralCast, narrow bit-fields, verbs specializations, explicit-
instantiation theft, keyword macros, non-constinit statics, cross-unit
mismatch) is an escape, matched on AST nodes (T*->void* is one BitCast node;
every enum-ingress spelling is one IntegralCast). Prototype caught every
escape-class counterexample with zero false positives on seven legitimate
programs. Prototype and tribunal probes preserved in context/prototypes/.

Spliced into SPEC §4, adapted to the basics (no Refined/Id). One divergence
from the lane: it required every verbs enum to have a 0 enumerator, which
would make verbs::to accept 0 from the wire. Instead VERBS_UNSET(name) names
the zero state while excluding it from ingress; VERBS_ENUM without a 0 is a
compile error. Non-constinit statics moved from boundary assumption to
escape; compile-command argument changes are silencing lines.

## Jev coverage audit of revision 2

papers/2026-10-17-jev-coverage-audit.md. One Jev Choice per tribunal finding
(92). Spec as state; ~1.16M input tokens. Jev said 73 resolved or removed,
6 pending §5, 13 partial/open. Re-read by hand. Most `partial` calls were
multi-part findings answered across several sections; three were real:
- D25: no exit status for compile errors, no rule for never-compiled units.
  Fixed in §6.2.
- soundness m3: `&D` passed to a function defined in no analyzed unit left a
  false `holds`. §4.4 now marks the type `outside`, naming the declaration.
- checks M11: the first-run full scan and cross-process job slots were
  unstated. Fixed in §6.6, plus bead verbs-de3.34.
Lesson: the probability mass off `resolved` was the signal (m3 was labelled
`resolved` at confidence 0.29), not the selected key.

Sysroot note from the blackbird session: an autonomous test agent repointed
/opt/homebrew/etc/clang/arm64-apple-darwin25.cfg to the Xcode SDK from about
16:38 until it was restored (mtime 16:39:34). No verbs probe ran in that
window. The enum lane's clang extraction finished by 15:51, and the earlier
lanes before that.

## External reviews: ChatGPT and MiMo (revision 3)

papers/2026-10-17-review-chatgpt.md (gpt-6.1-sol, xhigh, read-only sandbox;
21 findings, compiled on the pinned Clang) and papers/2026-10-17-review-mimo.md
(mimo-v2.6-pro plan agent, 14 findings; it stopped at its own plan-approval
step, so the plan file is the report). Both ran on a bundle copy.
- **MiMo copy:** a guard watched /opt/homebrew/etc/clang during its run. The
  config was unchanged.
- **Overlap:** the two reviews agree on the stale-facts hole, the kill
  criterion, the §6.5 example, the read-only exception, and type-erased
  attribution.

Verified against blackbird before adopting F15: `Fields` is local to
token_usage.cpp; journal.cpp returns `unsupported`; retained_events.cpp:548
admits only {2,3,4,14} while `RetainedKind::retry = 7`.

Dispositions:
- **To the escape-v2 research lane** (papers/2026-10-17-escape-allowlist-v2.md
  pending): ChatGPT F02 (const view then const_cast; same as MiMo F2), F03
  (`std::as_writable_bytes` inside libc++), F04 (pointer to uintptr_t,
  pointer bit_cast), F06 (attribution closure; with MiMo F5, program-wide on
  erasure), F12 (partial same-type memcpy). Each bypasses a list of
  constructs, so the lane is asked for a principled closed rule, measured.
  §4.1, §4.5 and §4.8 are marked [lane].
- **Fixed in the spec:**

| Finding | Fix | Section |
|---|---|---|
| ChatGPT F01 | Rule 3 no longer assumes "mutation only through the type's operations"; the escape check establishes it | §2.1 |
| ChatGPT F05 | The macro exemption is by definition location, not the `VERBS_` prefix | §4.3 rule 9 |
| ChatGPT F07 | Hash every input on every run; 0.34 s measured | §6.2 |
| ChatGPT F08, MiMo F3, MiMo F10 | A compile error suspends the report: real `+` lines only, no claims. Over budget, verbs still finishes; the budget gates the hook, it is not a cutoff | §6.2, §6.6 |
| ChatGPT F09 | Jev is optional; the operator's labels complete the gate | §10.3 |
| ChatGPT F10, MiMo F4 | Experiment defined: arms, seeds, fault oracle, detection event, censoring, proposed threshold | §1.1 |
| ChatGPT F11 | The weakening baseline is the declared predicate, whatever the state | §4.7 |
| ChatGPT F13 | Cross-unit grouping is by mangled name | §4.4 |
| ChatGPT F14 | Enum audit points; the sanitizer limit is stated | §10.2 |
| ChatGPT F15, MiMo F8 | Migration per seam: error codes and narrower guards kept; defect classes split into prevented and detected | §1.1 |
| ChatGPT F16 | Internal keys carry the signature; locals have keys | §6.4 |
| ChatGPT F17 | `upto` requires N ≥ 1 | §3.3 |
| ChatGPT F18 | Exit precedence 2 > 3 > 1 > 0 | §6.1 |
| ChatGPT F19 | Subjects are leaf vlib declarations and their wrappers; classes are not subjects | §2 |
| ChatGPT F20, MiMo F1 | The §6.5 example is now a real escape | §6.5 |
| ChatGPT F21 | Ingress takes exactly the types `std::in_range` accepts | §3.3 |
| ChatGPT, constinit overbuild | Rule 12 fires only on non-constant-initialized statics whose zero is invalid | §4.3 |
| MiMo F6 | Escapes gate by state (exit 1 until fixed); lost claims gate once, as events | §6.1 |
| MiMo F7 | No `decided` state; decisions cover only proposal subjects; escapes are always fixed in code | §2, §7 |
| MiMo F9 | Caps are 3 per file, 10 total | §6.5 |
| MiMo F11 | The concurrency narrowing is stated as deliberate | §2.1 |
| MiMo F12 | Wording: checked operations throw, ingress does not | §3.1 |
| MiMo F14 | Path-rule format: `.verbs-outside`, one glob and reason per line | §6.3 |

- **Not adopted:**
  - MiMo's call to cut negative probes. Checks M7 measured the need: an
    `__has_include` result or a shadowing include changes the parse.
  - MiMo's call to cut the §4.4 signature database. Soundness B6 is a real
    false `holds`, and the facts are recorded anyway.
  - Bounded's full arithmetic. It is already gated on a named consumer
    (increment B).
