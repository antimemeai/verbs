# Tribunal: doctrine compliance and value

Reviewer lens: doctrine compliance (BLACKBIRD.md tenets 1, 2, 5, the testing
section, the JSON rule) and value against the kill criterion. Subject:
design/SPEC.md at commit d03a6fe, which includes the operator's decision to keep
decision records in source (§7).

Read: BLACKBIRD.md, design/SPEC.md, design/verbs-design-brief.md, every file in
journal/, papers/2026-10-17-literature-agent-feedback.md, and the parts of
papers/2026-10-17-literature-core.md and papers/2026-10-17-reference-implementations.md
that the spec cites. I read ~/projects/blackbird and ~/projects/BRepGPU without
changing them. Probes were compiled with Homebrew clang 23.1.2 (`-std=c++2c`) in
the session scratchpad. They are described inline and are not committed.

Severity: **blocker** means the plan cannot start until it is fixed. **Major**
means the spec says something false, builds something with no consumer, or
leaves a gaming path open. **Minor** means a wording fix or a small cut.

---

## What is good

These parts hold up and should stay.

- **The cuts.** The spec drops the daemon, SQLite, preservation verdicts,
  `preservation_dep`, JSONL and the Python prototype. It does not build any
  machinery for the deferred cases; each one is a bead. This is tenet 1
  applied.
- **"Annotations clarify; they never encumber"**, with its corollary: when a
  finding can only be silenced by an annotation that states the obvious, fix
  the check. This is the strongest anti-Goodhart rule in the spec, because it
  removes the reason for most suppressions.
- **Why contracts are not used for representation invariants (§3.1).** The
  `ignore` semantic would store an out-of-range value and make the accessor's
  `[[assume]]` undefined behaviour. The argument is correct and concrete.
- **Checked enum ingress (§3.4), with integer-to-enum casts treated as
  escapes.** This is the one part of the basics with a clear, corpus-backed use
  (see D1).
- **Keys without line numbers (§6.3).** "Renaming retires the old finding" is
  the honest choice.
- **Silencing reported as a finding (§4).** This comes straight from the
  literature.
- **The oracles in §9.2 and §9.4.** IWYU-style expected-finding comments and
  "incremental equals from-scratch" are the right oracles for their fault
  classes. Each is independent of the code it checks.
- **No `unknown` state.** Instead of `unknown`, the report says which boundary
  rule excludes the declaration.

---

## Blocker

### D1. The spec has no path from the basics to the kill criterion, and as written the basics barely touch the corpus [Q2]

**Section:** §1, §9 (missing), §8 requirement 1.

**Evidence.** The kill criterion is edits-to-detection for an agent working
on blackbird and BRepGPU. The basics give `verbs check` two ways to detect
anything: the escape check, and the enum-candidate check.

- **The escape check only covers vlib types and "verbs-domain enums" (§4).**
  The corpus has no vlib today, so the check finds nothing in it.
- **The enum-candidate check does not detect defects.** It proposes a
  refactor. When an edit introduces a fault, a candidate line does not tell
  the agent about that fault.
- **vlib's real detection is the compiler rejecting bad code.** Those
  diagnostics already arrive through the build, not through `verbs check`.

**Blackbird already does by hand most of what the basics would add:**

- `include/blackbird/foundation.hpp:87` defines its own `template <typename Tag>
  class Id`. Ingress is checked (`from_bytes` returns `Result`), the
  constructor is private, and it has 12 tag aliases. A kind swap between two
  of blackbird's IDs is already a compile error.
- `AuditSequence` (foundation.hpp:126) is a checked `uint64_t` wrapper with a
  private constructor.
- The source has 109 `enum class` declarations, and the build uses
  `-Werror -Wconversion -Wsign-conversion -Wold-style-cast`. There are zero
  `NOLINT` comments and zero `#pragma clang diagnostic` lines.
- Its integer-to-enum casts already sit behind hand-written guards:
  - src/journal.cpp:278-281
  - src/workflow_join.cpp:149-151
  - src/retained_events.cpp:525-531
  - src/tasks.cpp:251
- A rough grep for fields compared against two or more integer literals finds
  about five plausible enum candidates in 80k lines (for example `node.site` and
  `node.kind` in src/token_usage.cpp:539-782). Most of the other hits have
  arithmetic uses, which disqualify them.

**BRepGPU cannot adopt vlib at all:**

- It is C++17 (`cxx_std_17` throughout CMakeLists.txt), and its docs build
  it with clang++-18.
- Its public interface is `extern "C"`, with `typedef uint32_t bg_status` and
  anonymous enums (include/brepgpu.h:5-20). An `enum class` with
  `verbs::to_enum` cannot cross a C ABI.
- The CUDA backend is built by `enable_language(CUDA)`.
- §8 requirement 1 ("One Clang builds ... the corpus code verbs analyzes") is
  therefore false for BRepGPU today. The spec never says so.

**Is the spec honest about this?** It is silent. It never says that the
basics have value only after code is migrated to vlib, it does not name that
migration, and it does not say that the BRepGPU arm is out of reach. There is
no bead for the experiment either (`bd list` shows none).

**Fix.** Add a short §9.6, "What the basics are judged on". It should state:

- **The treatment is a migration.** For example: blackbird's guarded decode
  casts move to `verbs::to_enum`, and the two `token_usage` codes become enums.
- **The seeded defect classes the basics can detect in migrated code:**
  - a removed or drifted ingress guard;
  - an enumerator added without its guard;
  - a raw cast added beside `to_enum`.

  `journal.cpp:278` hard-codes `{1,2,4,65535}` separately from the
  `FrameKind` definition in include/blackbird/journal.hpp:28. That is exactly
  the kind of drift `to_enum` removes by construction.
- **BRepGPU is outside the basics** until it raises its language standard.
  The basics are judged on blackbird alone.
- **A bead for the experiment.**

If that experiment is expected to show nothing, the spec should say so now,
before the plan.

---

## Major

### D2. Downgrading a vlib type is the dominant gaming move, and nothing detects it [Q1, Q5]

**Section:** §4 (silencing), §6.4.

**Evidence.** Suppose an agent changes `Bounded<0,5>` to `int`, widens it to
`Bounded<0, INT64_MAX>`, or turns a `VERBS_ENUM` back into `std::uint8_t`.
Then:

- every vlib compile error disappears (narrowing, `sum = sum + x`, raw
  ingress);
- every escape finding on that declaration prints as `-` (resolved);
- `verbs check` exits 0.

The agent-feedback lane lists "weakening a vlib type to a raw integer" as a
suppression to report (literature-agent-feedback.md, Synthesis, Goodhart
corollary). The spec's silencing list leaves it out. AdaTrans found agents
reaching for `unsafe` or raw pointers when the borrow checker blocks them; this
is the C++ equivalent.

**Fix.** Add one silencing bullet to §4: "a declaration loses its vlib type,
or its type widens (bounds, enum domain, `Refined` to `T`)". Print it as `!`.
It is also the only consumer for the `holds` set (see D7).

### D3. The in-source Goodhart defence only detects; it does not prevent, and `!` exits 0 [Q4]

**Section:** §7, §6.1.

**Evidence.**

- **The `!` line goes back to the agent that wrote the decision**, in that
  agent's own tool result. The operator's own reason for keeping decisions in
  source is that "nearly every reader will be an LLM agent"
  (journal/2026-10-17-operator-decisions.md). So no human sees the `!` line
  when it matters.
- **"`git blame` names the author" is false in this workflow.** All 30
  commits in this repository are authored `Patrick Beam <hiya@antimeme.ai>`,
  including the ones agents made. The only agent marker is a
  `Co-Authored-By` trailer, which blame does not show.
- **§6.1 rewards the silencing move.** Exit status is 0 whenever there are no
  *new findings*. An agent that answers a candidate with `VERBS_OPEN_DOMAIN`
  gets a `-` line, a `!` line, and exit 0.
- **A separate file can be made read-only; a line in a source file the agent
  is editing cannot.** ImpossibleBench measured that read-only tests stop test
  modification without hurting legitimate performance. Detecting the edit
  afterwards is weaker than preventing it, and that is the real difference
  between in-source records and a sidecar file.
- **`seen(...)` is written by the agent.** If it writes a superset (for
  example `seen(0,1,2,3,4,5,6,7)`), the decision never resurfaces (§5).
- **The rationale string is unchecked.** EvilGenie and ImpossibleBench both
  document plausible fabricated justifications.

**Fix.** Keep the operator's placement and add a gate.

- `verbs check` exits non-zero when a delta adds or changes a `VERBS_*`
  decision.
- Blackbird's edit tool reverts that edit unless the operator has approved it,
  the way SWE-agent reverts edits that fail its lint filter. This gives
  in-source records the protection a read-only file would have.
- A decision is valid only while `seen(...)` exactly equals the currently
  observed literal set.
- Delete the `git blame` sentence.

### D4. An agent can make an enum candidate vanish without any construct the escape check sees [Q4, Q5]

**Section:** §5 (disqualifiers), §6.4.

**Evidence.** Any one disqualifier makes the subject vanish from the edit
boundary silently, and it prints as `-` (resolved). Each of these is a
one-line edit:

- comparing against a non-literal: `constexpr int kArmed = 1; if (mode == kArmed)`;
- a streaming call (`log << mode`);
- taking the subject's address;
- an arithmetic use (`mode + 0`);
- inlining the sites into one function, which breaks rule 2.

The first is also the most idiomatic C++ improvement an agent could make. So
the rule *penalizes* the move toward clarity: it reads as "resolved" and the
invariant goes unstated.

**Fix.**

- Treat a comparison against a `constexpr` variable or enumerator whose
  initializer is a literal as a literal.
- When a candidate disappears because a disqualifier appeared, print `!`
  rather than `-`.

### D5. Enum candidates do not meet the bar the spec cites, yet they set exit 1 at every edit [Q1, Q5]

**Section:** §4 (precision bar), §5 (output policy), §6.1.

**Evidence.**

- **The cited bar has two halves.** Sadowski's compiler-check bar, as the
  core lane records it (literature-core.md:774-776), is "no effective false
  positives" *and* "must concern correctness only". The spec quotes the first
  half. An enum candidate is a design proposal, not a correctness defect.
- **Exit 1 at the edit boundary invites scope creep.** The agent refactors
  in the middle of an unrelated task. Fan et al. found that strong models
  already spend turns on redundant verification. ImpossibleBench found that
  feedback loops raise cheating from 33% to 38%.

**Fix.**

- Candidate lines do not set exit 1. Only escapes, silencing and weakening do.
- Label candidate lines as proposals.
- Cap them at one per delta.

### D6. The fallback `VERBS_ENUM` cannot encode the spec's own example, and following the encode line silently changes wire values [Q5, Q6]

**Section:** §3.4, §5 (suggestion), §6.4.

**Evidence.**

- **The spec's own example has a gap.** The §6.4 example reports
  `values {0, 1, 3}` and suggests `enum class Door::Mode`.
- **The fallback macro cannot express a gap.** It is "the brief's macro"
  (brief §4.3), which expands to sequential enumerators: `{ Idle, Armed, Firing }`
  is 0, 1, 2. An agent that follows the line therefore turns 3 into 2. On a
  wire protocol, that is silent corruption.
- **The corpus is full of explicit values.** Blackbird's `FrameKind` is
  `{1, 2, 4, 65535}` (include/blackbird/journal.hpp:28-33). BRepGPU's `BG_*`
  constants all carry explicit values.

**Fix.**

- `VERBS_ENUM` takes `Name = value` pairs.
- The encode line prints the explicit values, for example
  `enum class Mode : int { ? = 0, ? = 1, ? = 3 }`.
- §9.1 tests gaps, aliases and negative values.

### D7. Mechanism sets, the `holds` list, `outside` reasons and runtime-check counts have no consumer [Q1]

**Section:** §2, §2.2, §3.1 ("The report counts it as a runtime check"), §6.2.

**Evidence.**

- **Nobody reads the report.** It is an owned binary file in `<build-dir>/verbs/`
  (§6.2), and the delta prints only `+`, `-` and `!`. The only reader of
  `holds`, `outside`, mechanism sets and runtime-check counts is the next
  `verbs check`, and that run uses findings alone.
- **The consumers were dropped.** The brief named consumers for mechanism
  sets: lint suppression, Blackbird trust, and `[[assume]]` eligibility. The
  spec keeps the sets and drops the consumers. `[[assume]]` eligibility is
  fixed inside vlib's own source.
- **M is the same for every vlib claim.** Given no escapes, every vlib
  `holds` claim holds by `representation`; `typecheck` and `construction`
  describe ingress sites, not the declaration. This is a metric for metrics.

**Fix.**

- Cut mechanism sets and runtime-check counting from the basics.
- Keep `holds` only as the stored baseline that D2's weakening line diffs
  against.
- Keep `outside` (an operator decision), and say where it is printed. One line
  is enough: "`verbs scan` prints outside subjects with their rule, as text".

### D8. `Refined`'s claim is false for views and shallow-const types, including the spec's own example [Q6]

**Section:** §2.1 (example "a non-empty, sorted span"), §3.2.

**Evidence.** The probe wraps `std::span<int>` in a `Refined` with a `Sorted`
predicate. The owning vector is then changed with `v[0] = 9`, and the view is
written through `r.get()[1] = -5`, where `get()` is the const accessor. There
is no cast, no memcpy and no escape construct. Afterwards `Sorted(r.get())` is
false. The probe exits 1, so the predicate check failed. `const T&` is shallow
for `span`, `string_view`, pointers, `unique_ptr`, and containers of pointers.

**Fix.**

- Constrain `T` with a concept that rejects views, pointers and
  reference-semantic types in the basics.
- Replace the example, for instance with a sorted `std::array<int, N>`, or a
  non-empty `std::string` held by value.

### D9. The escape precision gate passes vacuously and has a circular oracle; the enum tuning overfits [Q3]

**Section:** §9.3.

**Evidence.**

- **The escape gate passes on nothing.** The corpus has no vlib, so the
  escape check reports nothing on it, and "100% true" is a fraction with
  denominator 0.
- **The judgement is circular.** A syntactic matcher with full type
  information is "true" by its own definition: it did find a `const_cast`
  that involves a vlib type. The question that bears on the claim is whether
  acting on the finding is right.
- **The enum tuning fits a handful of points.** Tuning thresholds "until the
  findings are" true, on roughly five plausible candidates (D1), proves
  nothing about the next edit.
- **The reviewer is unnamed.** If the reviewer is the agent that wrote the
  check, the builder grades its own work.

**Fix.**

- Measure escapes on the migrated code, with seeded escapes (D1).
- Define "true" as "the operator would accept the edit the finding asks for".
- The reviewer is the operator, or an agent with no access to the check's
  source.
- Record n.
- Tune on one repository or seed set, and report on another.

### D10. Mull cannot reach vlib's compile-time logic, so "Mull over vlib" overclaims [Q3]

**Section:** §9.5.

**Evidence.** Mull mutates LLVM IR (Denisov 2018, agent-feedback lane §5).
vlib's most important logic never reaches IR:

- result-bound computation in template arguments;
- `requires` clauses;
- the `named_predicate` concept;
- `consteval lit<V>`;
- `storage_for`.

On top of that, Mull 0.34.2 stops at LLVM 21 on macOS and LLVM 22 on Ubuntu.

**Fix.**

- State that Mull covers the runtime paths only (`make`, `+=`, `to_enum`,
  the checks).
- Add a dozen scripted source mutants of the vlib headers, for example:
  - flip a comparison in `requires`;
  - swap min and max;
  - an off-by-one in `storage_for`;
  - drop the `__int128` overflow `static_assert`.

  Each must be killed by the §9.1 compile-time suite. Run them on the fleet,
  per the doctrine.

### D11. Several §9.1 oracles are not independent, and one test cannot be written as shown [Q3, Q6]

**Section:** §9.1.

**Evidence and fixes, item by item.**

a. **"Hand-derived" bound tables.** The obvious way to derive them is
   min and max over the corners, which is the implementation restated.
   *Fix:* brute-force enumeration over every pair of intervals inside, say,
   [-4, 4]. That is 45 intervals per operand, about 2,000 pairs per operation.
   It is an independent model oracle and cheaper than hand tables. Keep hand
   rows only for the `int64_t` extremes.

b. **"For random bounds and values" cannot run.** Bounds are template
   parameters, and libFuzzer varies runtime bytes only. *Fix:* name the
   pre-instantiated grid that the fuzzer covers. The operator's fuzzing
   decision stands. Note that coverage guidance has little to steer on in
   straight-line arithmetic.

c. **`to_enum` "succeeds iff the value is an enumerator".** The oracle and
   the implementation read the same `VERBS_ENUM` array (or `enumerators_of`),
   so a wrong array fools both. *Fix:* write the expected sets literally in
   the test, including gaps, aliases (`magic_enum`'s own tests use
   `AliasFirst`) and negative values.

d. **`static_assert(!requires { Bounded<0,5>{3}; })` is ill-formed.** At
   namespace scope it is a hard error. Clang 23.1.2 reports "call to deleted
   constructor of 'Bounded<0, 5>'" and does not evaluate to false. Wrapped in
   a concept, `template<class B> concept raw_ok = requires { B{3}; };
   static_assert(!raw_ok<Bounded<0,5>>);`, it compiles and passes. *Fix:* use
   the concept form.

### D12. In the basics only enums have a discovery path; Bounded, Refined and Id have no named consumer [Q1, Q2]

**Section:** §1, §3.1–3.3.

**Evidence.**

- **The brief's reason for vlib does not hold here.** The brief justifies
  vlib as "the vocabulary that the lints' fix-its rewrite toward". In the
  basics the only lint proposes enums; kind discovery and repeated-guard are
  deferred (verbs-de3.21, verbs-de3.24).
- **Most of the machinery has no proposer.** Bounded's arithmetic (interval
  rules, `__int128` bounds, the accumulator rule, `narrow`, `clamp`,
  division) is the largest part of vlib and of §9.1, and no check proposes
  it.
- **No corpus declaration is named for any of them.** Blackbird already owns
  a better `Id` (its ingress is checked; `verbs::Id`'s explicit `Rep`
  constructor is not).

**Fix.** List the blackbird declarations each vlib type would replace. Where
the list is empty, defer that type to a bead. At minimum, defer Bounded
arithmetic and keep `lit`, `make` and `get`. "Basics first" should mean the
basics the corpus will use.

### D13. `std::optional` ingress invites an unchecked dereference that is worse than the hand guard [Q5]

**Section:** §3.1 (`make`), §3.4 (`to_enum`), §6.4 (encode line).

**Evidence.**

- **The likely agent rewrite is undefined on bad input.** When an agent
  replaces a guarded `static_cast` with `verbs::to_enum`, the easiest rewrite
  is `*verbs::to_enum<E>(raw)` or `.value()`. On invalid wire input, `*` is
  undefined behaviour, which is worse than the hand guard it replaced.
- **The escape check does not flag it.**
- **It does not match blackbird's idiom.** Blackbird returns `Result`
  failures with error codes at exactly these sites.

**Fix.** Pick one:

- make ingress return a type without an unchecked dereference, with
  `[[nodiscard]]`;
- or run Clang's `bugprone-unchecked-optional-access` (FlowSensitive) on
  migrated code inside `verbs check`.

### D14. The latency budget is never stated, yet the design pushes on every edit [Q6]

**Section:** §6.1, §6.2, §9.

**Evidence.**

- **There is no number.** The spec states no latency budget. The lane
  report asks for one ("small compared with an agent turn").
- **The measurement is deferred** (verbs-de3.14).
- **Header edits fan out.** Blackbird has 257 TUs and 87 headers that
  include other blackbird headers, and runs on 16 cores here. Cold
  clang-tidy with a trivial check takes 1.4-3.8 s per TU (toolchain lane). A
  `foundation.hpp` edit could plausibly take tens of seconds. That is a guess
  until it is measured.

**Fix.**

- State the budget.
- Make verbs-de3.14 a gate on enabling the hook, next to the §9.3 precision
  gate.

---

## Minor

### D15. `accepted_pending` is a TODO in source and the cheapest silencer [Q1, Q4]

**Section:** §7.

It records "encoding is planned". That duplicates bd, and AGENTS.md says to
track remaining work in bd. It needs no rationale, so it is the easiest way to
make a finding go quiet. **Fix:** cut it. Planned work goes in a bead.

### D16. The `const` predicate has no check behind it, and its `holds` claim can be false [Q1, Q6]

**Section:** §2.1, §2.3 item 6.

No check consumes `const`. §4 flags `const_cast` only when a vlib type is
involved, so `const_cast` on a `const int` declaration does not void a `holds`
claim. **Fix:** remove `const` from the basics vocabulary.

### D17. The footer is constant, incomplete, and attached to no claim [Q1, Q5]

**Section:** §2.3, §6.4.

- §2.3 says the footer prints all seven assumptions; the §6.4 example prints
  four.
- A delta prints no `holds` claim, so the footer qualifies nothing.
- Agents either ignore a line that repeats every turn, or spend turns
  "checking thread confinement".

**Fix:** print the full boundary wherever claims are printed (`verbs scan`).
Leave it out of deltas, or print it once per session. This still satisfies the
operator's rule that claims are stated with their assumptions.

### D18. "Its format is a contract versioned with verbs" freezes text an LLM reads [Q1]

**Section:** §6.4.

**Fix:** Blackbird appends the output verbatim and parses only the exit
status. Say so, and drop the versioned-contract sentence (tenet 1: we don't
freeze things).

### D19. One §9.4 property repeats another of the same kind [Q3]

**Section:** §9.4.

**Evidence.** "Edit then inverse gives an empty net delta" follows from
"incremental equals from-scratch" applied before and after, so the second
property adds nothing.

**Fix:** test the delta function directly as a pure property over report
pairs (`delta(a,b)` inverts `delta(b,a)`; applying `delta(a,b)` to `a` gives
`b`). That needs no fixture repositories.

### D20. `-verify` and the concept-rejection tests cover the same cases twice [Q3]

**Section:** §9.1.

**Fix:** use concept tests to check that code is rejected. Use `-verify` only
where the diagnostic text is itself the product, such as the `+=` and
`verbs::narrow` hint.

### D21. Parameters and locals can never be enum candidates, and the metamorphic test contradicts §6.3 [Q6]

**Section:** §5 (subjects), §6.3, §9.2.

- With no dataflow, a parameter's or local's sites sit in one function, so
  rule 2 can never fire for them.
- Locals in different functions share a qualified name, so their keys
  collide.
- §9.2's "renaming locals leaves keys unchanged" contradicts §6.3's
  "renaming retires" for any local that is a subject.

**Fix:** limit subjects to fields, globals and function returns.

### D22. Undefined terms decide recall and precision [Q6]

**Section:** §4, §5.

Three terms are undefined:

- **"literal constant".** Does it include unscoped enumerators such as
  BRepGPU's `BG_OK`, macros, or `constexpr` variables?
- **"a function outside the analyzed code".** Does `std::string::operator==`
  count? If it does, every string subject is disqualified.
- **"verbs-domain enum".** Does it mean `VERBS_ENUM` only, or every
  `enum class` under reflection? The answer decides whether blackbird's
  guarded casts become findings.

**Fix:** define each term in one line. Treat `extern "C"` declarations as
`outside`.

### D23. The violation handler's behaviour is unspecified [Q2]

**Section:** §3.1.

The spec says only that the handler "never returns". It does not say whether
it aborts or throws. Blackbird is a long-running harness that reports errors
by throwing `Error`; an abort would kill the agent's process. **Fix:**
specify the behaviour.

### D24. The lambda ban is not enforced by the type system [Q6]

**Section:** §3.2.

**Evidence.** A C++23 static lambda (`[](const int& x) static noexcept { return x > 0; }`)
passes every shape requirement in the probe: empty, default-initializable, a
`static` `noexcept` `operator()` returning `bool`, usable in constant
evaluation. Only the required `Pred::id` excludes it. Under reflection,
`display_string_of` produces a string for a closure type too.

**Fix:** require `Pred::id` in both paths and drop reflection-derived
identity. This also removes a [toolchain] dependency.

### D25. Unparseable TUs fail on every edit [Q5]

**Section:** §6.1.

If CUDA TUs, or any TU the pinned Clang cannot parse, return exit 2 on every
edit, the agent learns that verbs is broken and stops reading it. **Fix:**
report such a TU once as `outside`, not as a tool failure.

### D26. Expected findings must be written before the check runs [Q3]

**Section:** §9.2.

Case-file expectations written by running the tool are a regression oracle,
not a specification oracle. **Fix:** add one sentence: expectations are
written from the spec before the check exists (red first).

### D27. `verbs scan --hypotheses` names no consumer except calibration [Q1]

**Section:** §5.

The spec's own evidence says pull tools go unused (Kiro 3-22%, Xu 0-6%).
**Fix:** say that its consumer is the §9.3 calibration.

### D28. The facts files miss the torn-write fault class [Q3]

**Section:** §6.2, §9.2.

The reader fuzz is an operator decision, and its oracle is implicit (no
crash). The torn-write case is missing. **Fix:** write to a temporary file
and rename it; any read failure deletes and rebuilds.

---

## Q3 directly: tests of tests, independence, overclaims, gaps, proportion

**Tests of tests.** No test checks another test. Mutation testing grades the
suite, and the doctrine endorses it (testing form 5). The only same-kind
redundancies are D19 and D20.

**Independence.** Three oracles share code with what they check: D11a (bound
tables), D11c (`to_enum` sets) and D9 (the precision reviewer). The
incremental-versus-scratch oracle shares extraction code with the code it
checks, but its fault class is incrementality, so it is valid.

**Overclaims.**

- §9.5 claims Mull covers vlib (D10).
- §9.1 claims "random bounds" (D11b).
- §9.3 claims 100% precision on zero findings (D9).
- "Tier 7" for the hand tables holds only if they are derived independently.

**Untested.**

- The real claim: no test or experiment checks that the basics change
  edits-to-detection (D1).
- Latency (D14).
- Weakening and type-downgrade detection (D2).

**Proportion.** Tests for vlib justify real effort: a wrong bound becomes
undefined behaviour through `[[assume]]`. Still, §9.1 stacks eight mechanisms
on about 600 lines of headers. D11a's enumeration replaces both the hand
tables and the runtime/constexpr dual table. D20 removes the duplicate
rejection layer. The rest is proportionate.

## Q5 directly: what an agent will most likely do wrongly, line by line

| Line | Most likely wrong response | Evidence | Fix |
|---|---|---|---|
| `+ enum-candidate ... name the values` | Refactors in the middle of the task. Invents enumerator names. Writes sequential values (D6). Unwraps `to_enum` with `*` (D13). Or takes the cheapest exit: names the constants, adds a disqualifier (D4), or adds `VERBS_OPEN_DOMAIN` with a made-up rationale (D3). | ImpossibleBench (feedback raises cheating 33→38%); CORE (warning-clearing fixes change behaviour); Fan et al. (redundant turns) | D3–D6, D13 |
| `- escape ... removed` | Reads it as "fixed". May have removed the write, or dropped the vlib type (D2). | Agent-feedback synthesis 5: a cleared diagnostic is not a fix | D2 |
| `! decision added` | Reads it as approval. Nothing pushes back, and the exit status is 0. | §6.1; operator: readers are agents | D3 |
| footer `claims assume ...` | Ignores it, or uses it to rationalize ("this code is threaded, so it is outside") | Fan et al. | D17 |
| `N withheld` | Ignores it. Pull goes unused. | Kiro, Xu | none needed |
| exit 2 `not refreshed` | Takes silence as a pass, or retries in a loop | SWE-agent: recovery odds fall after a failure | D25; say "no check ran" |

AutoVerus and SWE-agent support the spec's shape: one typed, located line, a
class-specific repair hint, and a small capped payload. The shape is right.
What is wrong is the *content* of the candidate line (D5, D6) and the missing
gates (D2, D3).

## Q6 directly: statements of fact that are guesses or false

1. "Lambda closure types fail the concept" (§3.2). **False on shape** (probe;
   D24).
2. `static_assert(!requires { Bounded<0,5>{3}; })` works as a rejection test
   (§9.1). **False** (probe; D11d).
3. "a non-empty, sorted span" satisfies `refined` with `holds` (§2.1).
   **False** (probe; D8).
4. "`git blame` names the author" (§7). **False** here: all 30 commits are
   authored by Patrick Beam.
5. "It shows up in every diff and code review" (§7). There is no review step
   in autonomous runs, and the operator says readers are agents.
6. "Blackbird's edit hook runs `verbs check`" (§1, §6.1). **No such hook
   exists.** The `edit_file` path in blackbird's src/tools.cpp:236-300 has no
   post-edit diagnostics.
7. "One Clang builds ... the corpus code" (§8.1). **False** for BRepGPU
   (clang++-18, C++17, CUDA).
8. "It matches syntax with full type information, so it can reach that bar"
   (§4). **Unverified.** These are missing from the escape list:
   `fread`/`read`/`recv` into an aggregate that holds a vlib member,
   placement new, `std::start_lifetime_as`, and generic `memcpy<T>`
   serializers. Blackbird decodes binary journals, so these matter.
9. "the identity is the predicate's fully qualified name
   (`std::meta::display_string_of`)" (§3.2). **Unverified** that the result
   is stable and fully qualified. The reflection code in quarantine
   (magic_enum) uses `identifier_of`.
10. "Each has a macro fallback that works on Clang 23 with `-std=c++2c`"
    (§8). **Unverified.** No probe is cited.
11. "This needs no build-system integration" (§6.2). **Unverified.** A change
    to the compilation database, or a generated header, is not covered.
    §12 Q4 already asks.
12. Sadowski's bar is quoted as zero effective false positives (§4). **Half
    the criterion**; the other half, "concern correctness only", is omitted
    (D5).
13. "vlib is header-only C++26" (§3, §8). **Not required by anything in
    §3.1–3.4.** Every construct the fallback uses is C++23. Declaring vlib
    C++26 forces blackbird (`CMAKE_CXX_STANDARD 23`) to change its standard
    for no gain. **Fix:** make vlib basics C++23. That removes an adoption
    barrier at no cost.

---

## Ranked summary

| # | Sev | Section | One line |
|---|---|---|---|
| D1 | blocker | §1, §9, §8 | No path to the kill criterion. On today's corpus the basics detect almost nothing. Blackbird already owns `Id` and its guards; BRepGPU (C++17, C ABI, CUDA) cannot adopt. The spec is silent. |
| D2 | major | §4 | Type downgrade or widening clears every finding as `-` with exit 0 and is not detected. |
| D3 | major | §7, §6.1 | The in-source Goodhart defence only detects; `!` exits 0; blame names the operator; `seen()` can be gamed. Add a gate. |
| D4 | major | §5 | Disqualifiers (named constants, logging, arithmetic) silently retire candidates. |
| D5 | major | §5, §6.1 | Candidates are not correctness findings but set exit 1 every edit. |
| D6 | major | §3.4, §6.4 | `VERBS_ENUM` cannot express explicit values. Following the encode line turns {0,1,3} into {0,1,2}. |
| D7 | major | §2.2 | Mechanism sets, `holds` listing and check counts have no consumer. |
| D8 | major | §3.2 | `Refined<span>`, the spec's own example, is falsified without any escape. |
| D9 | major | §9.3 | Escape precision gate is 100% of 0 and circular; enum tuning fits about 5 points. |
| D10 | major | §9.5 | Mull cannot mutate compile-time vlib logic. |
| D11 | major | §9.1 | Bound tables and `to_enum` oracle share logic with the implementation; "random bounds" impossible; requires-test ill-formed. |
| D12 | major | §1, §3 | Bounded, Refined and Id have no discovery path or named corpus consumer in the basics. |
| D13 | major | §3.4 | `optional` ingress invites `*to_enum(...)`, undefined on bad input. |
| D14 | major | §6 | No latency budget; header fanout unmeasured but push is on every edit. |
| D15 | minor | §7 | Cut `accepted_pending`. |
| D16 | minor | §2.1 | Cut `const` from the vocabulary. |
| D17 | minor | §6.4 | Footer is constant and incomplete; print it where claims are printed. |
| D18 | minor | §6.4 | Do not version the text output. |
| D19 | minor | §9.4 | Inverse-edit property repeats incremental-equals-scratch. |
| D20 | minor | §9.1 | `-verify` and concept rejection overlap. |
| D21 | minor | §5 | Parameter and local subjects can never fire; local keys collide. |
| D22 | minor | §4, §5 | Define "literal", "outside the analyzed code", "verbs-domain enum". |
| D23 | minor | §3.1 | Specify the violation handler. |
| D24 | minor | §3.2 | Static lambdas pass the shape; keep `Pred::id` mandatory. |
| D25 | minor | §6.1 | Unparseable TUs should be `outside`, not exit 2 on every edit. |
| D26 | minor | §9.2 | Write expectations before the check runs. |
| D27 | minor | §5 | `--hypotheses` consumer is calibration only. |
| D28 | minor | §6.2 | Facts files need atomic writes. |
