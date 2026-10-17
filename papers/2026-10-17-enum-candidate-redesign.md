# Enum-candidate redesign: rule, measurements, recommendation

Date: 2026-10-17. Lane: redesign SPEC §5 so its output meets the agent-facing
bar (no effective false positives at the edit boundary), and measure it.
Inputs read:
- BLACKBIRD.md;
- design/SPEC.md §5;
- papers/2026-10-17-tribunal-checks.md (B2, M4, M5, M6, m6, m7);
- tribunal-ergonomics M8;
- tribunal-doctrine D4, D5, D21, D22, D27;
- literature-core §1-2, plus the Daikon TSE 2001 text for the small-value-set
  template and its statistical test.

Nothing was written into blackbird or BRepGPU, and neither was built. Both
were read through `git archive HEAD` snapshots in the session scratchpad:
- blackbird `1180d2b`: 257 TUs, using its `build/debug` compilation database
  with paths rewritten to the snapshot;
- BRepGPU `2280db1`: 187 sources, using the tribunal's approximated flags
  `-std=c++20 -I include -I native -I native/mesher -I native/mesher/cuda`.

Every clang command line carried an explicit `-isysroot`. Extraction
finished at 15:51 (blackbird) and 15:55 (BRepGPU) local, before the 16:38
change to the Homebrew clang config.

## Verdict

1. **The redesigned rule does not meet the edit-boundary bar on held-out
   code.**
   - On blackbird, the development corpus, its edit-boundary tiers (A and E
     below) were **8/8 true**.
   - On BRepGPU, the held-out corpus, they were **6/13 (46%)**.
   - The held-out run exposed a fact-loader bug: increments and compound
     assignments were dropped as writes. With that fixed, the BRepGPU A tier
     was **5/8 (62%)**. The blackbird results did not change.
   - The remaining false findings are a version number
     (`Api::version ∈ {1,2}`), a count (`DomainIssue::segment_count`) and a
     bit mask (`radial_pending_mask ∈ {0,3}`). Each is written and compared
     only against literals, so it uses the code exactly as an enum does.
   - No use-based clause separates these from true domains. Only the
     declaration's name does, and a name rule is a guess.
2. **Recall at the edit boundary is low.**
   - blackbird: 8 of the 122 true domains that reading identified (6.6%).
   - BRepGPU: 6/18 frozen, 5/18 after the fix.
   - Most true domains in blackbird are producer-only trace codes, and the
     strict tier cannot see them by construction.
   - Across every tier, recall is 112/122 on blackbird and 12/18 on BRepGPU.
     That recall comes from tiers that are not precise enough to show an
     agent unasked: the producer tier is 96% on blackbird and 80% on BRepGPU.
3. **The independent label is weak.**
   - Jev answered "closed domain" for 108 of 119 blackbird findings and 23 of
     26 BRepGPU findings.
   - Raw agreement with my labels was 88% on blackbird and 46% on BRepGPU.
   - Cohen's κ was 0.17 and −0.01. Agreement is at chance, so Jev did not
     certify the labels.
   - Its disagreements were still worth re-reading, and one class of my
     labels changed because of them (below).
4. **Recommendation: take the enum-candidate check out of the basics.**
   - Nothing goes to the edit boundary, and nothing sets exit status.
   - The rule text below belongs in a deferred bead for discovery work, not
     in SPEC §5.
   - If the operator wants to keep it at all, the most it should be is a
     `verbs scan --hypotheses` report that always exits 0.
   - It is not a correctness check (Sadowski's second half, doctrine D5).
   - It missed the bar on held-out code after six rounds of clause work on
     the development corpus.

## What was built (scratchpad `enum-lane/`, throwaway)

**`facts.cpp`** is a LibTooling extractor of about 1,000 lines, built against
Homebrew LLVM 23.1.2. It starts from the checks tribunal's `probe/probe.cpp`
and adds:
- **Slots.** Fields, globals, locals, parameters (keyed by function and
  index) and returns (keyed by function). Internal-linkage keys are
  qualified by file (tribunal M8).
- **Copy edges.** These are recorded for:
  - initialization, assignment and argument passing;
  - returns, member initializers and aggregate initialization;
  - `std::move`/`std::forward`;
  - string-to-`string_view` conversion.
- **Write facts.** Each write is classified as one of:
  - a constant, tagged by class: literal, named `constexpr`/`const`
    constant, enumerator, repository macro, system macro, computed
    constant expression, character, or bool;
  - a slot copy;
  - an enum-to-integer conversion;
  - a zero or value initialization;
  - opaque ingress.
- **Use classification, fail-closed.** Every read is one of:
  - `dispatch` (`==`, `!=`, `case` against a constant);
  - `cmpslot`, `rel`/`relconst`, `arith`, `bitop` or `index`;
  - `addr` or `addrconst`, `alias` (non-const reference), or `store`;
  - `egress` (a closed list of std formatting and byte-view functions, and
    `<<`);
  - `extern` (any other callee without repository source);
  - `copy`, `toenum`, `bool` or `neutral`;
  - `other`, which covers anything not in this list.
- **Switch summaries.** Each switch records its default branch's first
  statement.
- **Also recorded:**
  - a "guard" flag on relational comparisons;
  - functions referenced other than as direct callees;
  - member names used in dependent (generic-lambda) code;
  - functions that return an enum;
  - template instantiations.

The remaining scripts:
- `rule2.py` is the rule engine over all units' facts. It computes directed
  backward and forward closures per subject and applies the clauses below.
  It was frozen as `rule_frozen.py`; `rule_fixed.py` is that file with the
  loader fix.
- `excerpt.py` groups findings and prints code excerpts.
- `jev_label.py` poses one Jev Choice per finding.
- `agree.py` and `metrics.py` compute agreement, precision and recall.
- `pool.py` and `poolrest.py` build the recall pool.

Known approximations:
- A write through `memcpy`, `read()` or a byte copy of a whole struct is seen
  only as an address-taken use, and so as ingress.
- Calls through function pointers are seen only through the
  referenced-function fact.
- Generic lambdas are seen only by member name, which disqualifies
  conservatively.
- The 32 BRepGPU sources that do not parse under the approximated flags are
  excluded rather than read from error-recovered ASTs. These are mostly
  `main.cpp` tools, OCCT and Linux sources, and fixtures. The tribunal lost
  31 sources the same way.

## Why §5 as written fails

§5 makes four choices:
- it treats the observed literal set as the domain;
- it pools evidence across declarations;
- it disqualifies on a handful of named uses;
- it gates on thresholds (2-16 values, ≥2 functions).

Daikon is the closest prior art. It reports a small value set only after a
null-hypothesis test on runtime samples (Ernst 2001 §3.1). Its own
evaluation counts differences between small value sets as uninteresting
(§8, Figs. 12-13). A static literal set is not a sample, so that
justification does not carry over.

The static analogue is Houdini: guess candidates, refute any candidate that
a write contradicts, and keep the survivors. The closure clause below is
that loop. DynComp names the choice §5 never made, the interaction
definition. Here, dataflow propagates a value and an equality comparison
relates two slots, while arithmetic disqualifies.

Unifying slots over copy edges, Lackwit style, collapsed blackbird into one
class of 2,553 slots, among them site codes, counts and IDs. That is Lackwit's
65% result (literature-core §1). The rule therefore uses directed closures:
- **B(S)**, everything that flows into S;
- **F(S)**, everything S flows into.

## The rule, as spec text

This text replaces SPEC §5 if the operator keeps the check. Under the
recommendation it belongs in a deferred bead instead. Every clause was
exercised on the corpus; the tallies are in the measurements section.

> ## 5. The enum-candidate check (discovery; scan only)
>
> **Purpose.** Find an integer or string declaration whose values form a
> finite set that the code produces and distinguishes, and propose an
> `enum class` for it. This is a design proposal, not a correctness finding.
>
> **Terms.**
> - *Slot*: a field, a namespace-scope or static data member variable, a
>   local, a parameter (keyed by its function and position), or a function's
>   return (keyed by its function).
>   - Functions are keyed by USR.
>   - A slot with internal linkage, or in an anonymous namespace, a lambda or
>     a local class, is keyed by USR plus its repository-relative file.
> - *Subject*: a slot that is a field, a global, a parameter or a return,
>   that has one of the subject types, and whose declaration is program code
>   (C2).
>   - Locals and lambda parameters are slots that carry flow. They are never
>     subjects.
> - *Subject types*:
>   - an integer type other than `bool`, the character types (`char`,
>     `wchar_t`, `char8_t`, `char16_t`, `char32_t`) and enumerations;
>   - `std::string` and `std::string_view`.
>   - `const char*` is outside: `==` on it compares pointers, and `strcmp`
>     is an external call.
> - *Program code*: a file under the repository root that matches neither
>   the test path rule (`tests/`, `test/`, `*_test.*`) nor the generated or
>   vendored path rule (`third_party/`, `vendor/`, `external/`, `generated/`,
>   `*.pb.*`, plus a per-repository list). A change to either rule is a `!`
>   line.
>   - Evidence from code that is not program code is ignored entirely. It
>     neither counts nor disqualifies.
> - *Constant*: an integral or string constant expression whose spelling is
>   one of the following:
>   - an integer or string literal, possibly negated;
>   - a `constexpr` variable, or a `const` variable with a constant
>     initializer;
>   - an enumerator, possibly cast to an integer;
>   - a macro defined in program code that expands to one of the above.
>
>   The finding shows the constant's spelling. Two constants are equal when
>   their values are equal. Naming a constant therefore never changes a
>   finding (doctrine D4).
> - *Write* into slot T:
>   - an initializer, an assignment, or a member or aggregate initializer;
>   - a call argument bound to parameter T;
>   - a default argument of T;
>   - a `return` from T's function.
>
>   Each write is classified as exactly one of: a constant; a *copy* from
>   slot U (directly, or through parentheses, implicit conversions,
>   integral casts, `std::move`, or a string/`string_view` conversion); an
>   *enum write* (a cast from an enumeration type E); a *zero write*
>   (value-initialization, or static zero-initialization); or *ingress*
>   (anything else).
>   - These are also ingress: a compound assignment or `++`/`--` on T; any
>     non-const address or reference to T; a parameter whose function is
>     virtual, `main`, `extern "C"`, a lambda, or referenced other than as a
>     direct callee; a local, field or global in B(S) other than S itself
>     that has no recorded write.
> - *Flow*: B(S) is S plus every slot whose value reaches S through copies.
>   F(S) is S plus every slot S's value reaches through copies.
> - *Use* of a slot's value, classified by its parent expression. The list
>   is closed; a use not listed is unclassified.
>   - *Dispatch*: `==`, `!=` or `case` against a constant.
>     `s.empty()` is dispatch against `""`.
>   - *Neutral*: a copy into another slot; a contextual `bool` test, which is
>     a test against zero; `(void)x`; an unevaluated operand.
>   - *Egress*:
>     - `<<` into a stream;
>     - an argument to `std::to_string`, `std::to_chars`, the `std::format`
>       and `std::print` families, or the `printf` family;
>     - `std::as_bytes`;
>     - a `const` address;
>     - string concatenation.
>   - *Enum conversion*: a cast to an enumeration type, or a comparison with
>     an enumeration-typed value.
>   - *Quantity*:
>     - arithmetic, bitwise and shift operators;
>     - relational and three-way comparison;
>     - use as an array or container index;
>     - conversion to floating point;
>     - any member call on a string other than `empty()`.
>   - *Unclassified*:
>     - a call to a function without program source, other than the egress
>       list;
>     - an indirect call;
>     - a non-const reference or address;
>     - a store into an array or `std::array`;
>     - a comparison against a non-constant that is not a slot;
>     - a slot-to-slot comparison;
>     - any reference in dependent template code, including a member of the
>       same name used in a generic lambda in a file where the subject
>       appears;
>     - everything else.
>
> **Clauses.** Evaluate each subject S over the whole compilation database.
> Each clause either excludes S or contributes to its tier.
> - **C1 kinds.** S has a subject type.
> - **C2 declaration.**
>   - S is excluded when:
>     - it is in test or generated code;
>     - it is `volatile` or `sig_atomic_t`;
>     - it is a lambda parameter or capture;
>     - it is a union member;
>     - it is in an `extern "C"` context;
>     - it is declared in a `.h`, `.cu` or `.cuh` file.
>   - Those headers are the C/CUDA/ctypes ABI boundary, where an
>     `enum class` cannot go. Such declarations are `outside` with the
>     reason "ABI boundary".
> - **C4 uses.** No slot in F(S) has a quantity or unclassified use. This
>   is fail-closed: an unknown use excludes S.
> - **C5 dispatch.**
>   - S needs at least one dispatch, by a slot in F(S) that S *owns*, on a
>     value other than the zero value (`0`, `""`, `-1`) and other than a
>     sentinel. S owns a slot when every source of that slot lies in
>     B(S) ∪ F(S).
>   - Dispatch in a shared helper is not evidence for S.
>   - Without such dispatch, S can only be a producer candidate (tier P).
>   - A string subject without dispatch is excluded: produced-only strings
>     are text.
> - **C6 values.**
>   - The observed set V is every constant written into B(S), plus every
>     constant dispatched on in owned F(S).
>   - A *sentinel* is a value whose every write is a declaration-scope
>     initializer (a default member initializer, a static initializer or a
>     default argument), or a zero value that is compared but never
>     written.
>   - V minus the sentinels has at least two values, and for integers it is
>     not a subset of {0, 1}. A two-valued integer set {0, 1} is a bool
>     candidate (verbs-de3.24).
> - **C7 constants.**
>   - A system-header macro or constant in V (for example `EAGAIN`) makes S
>     a platform domain, excluded.
>   - A character literal makes S a character value, excluded.
>   - A bool literal makes S bool-shaped, excluded.
>   - A value written only as a computed constant expression (sizes, sums,
>     shifts) is a quantity, excluded.
> - **C11 wider domain.**
>   - If a slot T receives values from S's sources, T has sources outside
>     S's flow, and T has any use that is not egress, then S's values are
>     a view of T's wider domain. S is excluded.
>   - Site and trace-ID registries fall here.
> - **C12 hand-written ingress.** If every owned dispatch on S lies in a
>   function that returns an enumeration E, the code already converts S to E
>   by hand. S is excluded.
> - **C13 merged declarations.** If B(S) contains two or more other fields
>   or globals, S is a shared helper or serializer parameter, not a domain.
>   S is excluded.
>
> **Tiers.**
> - **A (closed)**: C1-C13 hold, there is owned dispatch, and B(S) has no
>   ingress and no enum write. Every value S can hold is in V, for the
>   analyzed code (claim boundary item 7).
> - **E (enum-fed)**: C1-C13 hold, and every non-constant write into B(S)
>   is an enum write from one program enumeration E. Here `std::byte` does
>   not count.
> - **H (open)**: C1-C13 hold and there is owned dispatch, but B(S) has
>   ingress. V is only a lower bound.
> - **P (producer)**: C1-C13 hold except C5. B(S) is closed, S is an
>   integer, and S has no owned dispatch.
>
> **The finding.** It names S and its tier, and shows:
> - **values observed**, worded as "values observed include {…}", with each
>   constant's spelling;
> - the sentinels separately, worded as "also written only as an initializer:
>   {…}; is that a member or an unset marker?";
> - the dispatch sites;
> - the ingress sites for tier H;
> - the source enum for tier E;
> - any value that is compared but never written ("never produced").
>
> **The suggestion never proposes `to_enum` over the observed set.**
> - **A**: "every write in the analyzed code is one of {…}. Name these
>   values. Is the domain meant to admit others?" The writes become
>   enumerators; there is no ingress, so no `to_enum` is needed.
> - **E**: "every non-literal write comes from E; consider declaring S as E."
>   If V also holds literals that are not E's enumerators, the suggestion
>   lists them and says E does not cover them.
> - **H**: "values observed include {…}; the values arrive at {ingress
>   sites}; what is the full domain?" `to_enum` at the ingress is proposed
>   only for an E whose enumerators the answer supplies. If the code already
>   rejects at that ingress (a `default:` that throws, or a guard that
>   exits), the finding cites that guard as the evidence of the bound.
> - **Below C++26** (both corpora today), the encoding is a plain
>   `enum class` plus the hand-written check. The finding says that
>   `verbs::to_enum` needs vlib, which is C++26.
>
> **Output and exit.**
> - Candidates appear only in `verbs scan --hypotheses`, ranked
>   A, E, H, P.
> - They never appear at the edit boundary and never set exit status 1.
> - A decided candidate (§7) is keyed by S's slot key and resurfaces only
>   when V gains a value outside the decided set.

Notes on the terms the brief asked to define:
- **Subjects.**
  - Parameters are subjects, because their writes are the call sites
    (D21's objection applied to the non-dataflow §5).
  - Returns are subjects, because their writes are the `return` statements.
  - Locals are not subjects, but they carry flow.
- **Producer and consumer.**
  - The two sides combine through flow. A setter
    `void set_mode(int m) { mode_ = m; }` puts `m`'s call-site literals
    into `mode_`, through B(`mode_`).
  - A consumer inside a generic helper is not evidence (C5 owned dispatch).
  - Serialization on egress is neutral (ergonomics M8): an argument to a
    byte-view template such as `raw_native_field(const T&)` reaches only a
    `const` address.
- **Sentinels.** These are structural, not by value: a value written only
  at declaration scope, or a zero value compared but never written.
- **Bit flags** are excluded by `bitop` (quantity). **Bool** is excluded by
  C1, and the int-as-bool set {0, 1} by C6.
- **String comparisons**: `==` and `!=` against a literal or a named string
  constant are dispatch. Any other member call is quantity. `const char*` is
  outside.
- **C ABI and generated code**: C2. The generated-code rule is a path rule
  and missed one generated file on held-out data; see below.
- **Below C++26**: the check still runs. The encoding text changes.

## How the clauses were found (blackbird only)

Each step below was a false class read in the corpus and written as a clause.
No step tuned a threshold.

1. **Undirected classes collapsed** into a 2,553-slot class (Lackwit). The
   classes became directed closures.
2. **Site codes** (`error_site_` {4002…4121} and about 60 `…#site`
   parameters) were compared against literal site numbers. They are views of
   the global site registry that every emitter forwards to. That gave C11.
3. **Presence tests.** `ViewDescription::binding` ("Ctrl-O"…) was compared
   only with `.empty()`, and site parameters only with `0`. Zero-value
   dispatch alone became non-evidence (C5).
4. **Sentinels.** A local's `= 1 : 2` initializer had been taken for a
   declaration-time sentinel. Sentinels became declaration-scope writes only.
5. **Hidden ingress.** `Node::kind` had looked closed because its source,
   the `T value; memcpy(&value, …)` local in `Fields::get<T>`, had no
   visible write. A non-const address and a missing write became ingress.
   `Node::kind` moved to tier H, which is the tribunal's B2 case.
6. **Hidden quantity.** `Body::rank` had looked closed because
   `left.rank > right.rank` sat in a generic sort lambda that was never
   resolved. Dependent member names became disqualifiers.
7. **Hand-written parsers.** `delivery_signal("kill"…)` and `ink("success"…)`
   map strings to enums. That gave C12.
8. **Shared sinks.** `RawEmission::finish#stage` merges the stage fields of
   several traces. That gave C13.
9. **Computed constants.** `ProviderOriginalReference::record_offset` was
   written as `raw_envelope_size + ref_bytes + 1 + …`. That gave the
   computed-constant part of C7.
10. **A wrong clause, removed.** An "identifier registry" clause excluded
    subjects whose every value is written exactly once. It removed 42 slots
    on blackbird, and every one of them was a true trace code table: branch,
    method, kind, role, stage. C11 already handled the real registries.
11. **Enum-fed subjects.** `NativeFrame::begin#operation`
    (`static_cast<int>(op)`) and `RawAuthTrace::stage_` (`RawAuthField`
    plus 100 and 109) are fed from an enum. Tier E was widened so that it
    no longer needs dispatch.

Final clause tallies on blackbird, counting distinct (name, location)
subjects:

| Clause outcome | Count |
|---|---|
| C1 not a subject (local, bool, enum, cstr, char) | 7122 / 2441 / 702 / 379 / 161 |
| C2 test or generated declaration | 1599 |
| C2 extern "C" / volatile or signal | 7 / 6 |
| C4 quantity use / unclassified use | 1560 / 513 |
| C5 produced-only string / open producer | 12 / 9 |
| C6 fewer than two non-sentinel values / bool-shaped | 325 / 6 |
| C7 platform constant / computed constant | 19 / 2 |
| C11 view of a wider domain | 193 |
| C12 hand-written ingress | 3 |
| C13 merges several declarations | 38 |
| **A / E / H / P** | **8 / 3 / 6 / 136** |

BRepGPU, held out, with the fixed loader:

| Clause outcome | Count |
|---|---|
| C1 local / bool / enum / cstr / char | 4157 / 627 / 232 / 220 / 4 |
| C2 test or generated / extern "C" / C or CUDA header | 752 / 426 / 87 |
| C4 quantity / unclassified | 1548 / 185 |
| C6 too few values / bool-shaped | 191 / 4 |
| C7 platform / computed | 4 / 3 |
| C11 / C13 | 22 / 15 |
| C5 string text / open producer | 1 / 1 |
| **A / E / H / P** | **10 / 0 / 15 / 6** |

## Measurements

Findings are grouped: declarations connected by flow (one in the other's B)
form one finding. Labels use three classes:
- **T**: a finite closed domain the code relies on, not already carried by
  an enum at that boundary;
- **O**: an open or extensible domain;
- **N**: not a domain (count, index, size, version, mask, sentinel, text,
  test value).

Every finding was labelled by reading the code, and each label has a
one-line reason in the appendix. A label that cites documentation cites the
descriptor string it read, for example `provider_original.cpp:443` for
phase kinds 1..14.

### Precision

| Corpus | Tier | Findings | T | O | N | Precision |
|---|---|---|---|---|---|---|
| blackbird (development) | A | 5 | 5 | 0 | 0 | 100% |
| | E | 3 | 3 | 0 | 0 | 100% |
| | H | 6 | 3 | 2 | 1 | 50% |
| | P | 105 | 101 | 4 | 0 | 96% |
| | **A+E (edit-boundary candidates)** | **8** | **8** | | | **100%** |
| BRepGPU held out, frozen rule | A | 13 | 6 | 0 | 7 | 46% |
| | H | 8 | 2 | 1 | 5 | 25% |
| | P | 5 | 4 | 0 | 1 | 80% |
| | **A+E** | **13** | **6** | | | **46%** |
| BRepGPU, loader fixed (no longer held out) | A | 8 | 5 | 0 | 3 | 62% |
| | H | 13 | 3 | 1 | 9 | 23% |
| | P | 5 | 4 | 0 | 1 | 80% |

**The loader bug.**
- The extractor writes compound-assignment, `++`/`--` and string-append
  writes with seven columns. The rule's loader required eight and silently
  dropped them.
- Loop counters that flow into parameters therefore looked closed. The
  frozen rule reported `direction(n, k)` (from `for (k = 0; k < 3; ++k)`),
  `decode_row#section` and `matrix_norm#free` as tier A.
- With the fix, those moved to H. blackbird's output did not change: no
  blackbird subject had depended on it.
- I report both runs. Only the frozen numbers are held-out evidence.

**False classes seen only on held-out code:**
- **Version numbers.** `bgom10::Api::version`: writes `{1, sizeof(Api), …}`
  and `{2, …}`; comparisons `version != 2` and `version == (… ? 2u : 1u)`.
- **Counts.** `DomainIssue::segment_count`: written 1 and 2 in aggregates,
  compared `!= 2`.
- **Bit masks used only with `==`.** `radial_pending_mask`:
  `angular ? 0U : 3U`, compared `!= 0 && != 3`. The checks tribunal looked
  for this class and found none in blackbird ("Attacks that failed").
- **Generated tables.** `adaptive_rn_tables.hpp` starts with "// Generated
  from owned P128 tables" and holds four switch-indexed constant tables
  (tier H). The path-based generated rule cannot see that marker.
- **Numeric constants passed as fields.** `AtanRequest::divisor ∈ {5, 239}`
  (Machin's formula), tier P.

The first three are uses an `enum class` would serve equally well. Nothing
in the code's structure says "count" or "version"; only the name does. That
is why I do not propose another clause. A name rule is a guess, and the next
corpus would bring the next name.

### Recall

There is no complete list of true domains, so recall is measured against a
list built by reading. The pool behind it is every subject that shows any
domain-shaped evidence, collected independently of the rule's clauses:
- **R1**: an enum conversion in or out;
- **R2**: a switch with two or more cases;
- **R3**: two or more distinct non-zero dispatch constants;
- **R4**: every write a constant, with three or more distinct values.

That pool held 437 subjects on blackbird and 103 on BRepGPU. I read the
subjects the rule did not report and listed the true domains among them
(misses below). Truth is then the findings labelled T plus those misses.
Subjects with no domain-shaped evidence at all, such as domains known only
from documentation, are not in the pool, so recall is an upper bound.

| Corpus | Truth domains | A+E | A+E+H | All tiers |
|---|---|---|---|---|
| blackbird | 122 (112 found T + 10 missed) | 8 (6.6%) | 11 (9.0%) | 112 (92%) |
| BRepGPU frozen | 18 (12 + 6) | 6 (33%) | 8 (44%) | 12 (67%) |
| BRepGPU fixed | 18 | 5 (28%) | 8 (44%) | 12 (67%) |

Misses on blackbird, with the clause that excluded each:

| Subject | Excluded by |
|---|---|
| `SessionSettings::effort` (also `CodingEngine::effort#value`, `validate_anthropic_route#effort`): low/medium/high/xhigh/max | C4: `.size()`/`.find()` in session.cpp:45; flows into `Value` (std::make_shared) |
| `ProviderAuth::add_provider#protocol` | C4: `.size()`; stored into `std::array<string_view,4>` |
| `ProviderHttpRequest::method` GET/POST | C4: flows into `raw_string_field` (`.data()`/`.size()` byte view) |
| `LocalTools::run#name` (tool names) | C11: flows into `CodingEngine::call#name`, itself excluded |
| `CodingEngine::call#name` / `operation#name` | C4 |
| `Manager::perform#cmd` (candidate subcommands) | C4: `raw_string_field`, `Value` |
| `TaskStore::operator_command#command` | C4: `raw_string_field` |
| `Observations::sample#status` | C4: `Value` construction |
| `target#kind` task/command/participant | C4; its only comparison sits in a shared helper |
| `ProviderOriginalRequest::label` | C4 |

Misses on BRepGPU:
- `bgom10::Carrier::tag`, a true domain per the checks tribunal (C4);
- the `bg_status` code family (`Operation::status`, `error#code`,
  `diagnostic#code`): C11, because the wider holder is the C-ABI
  `bg_diagnostic`, which C2 excludes;
- `ProjectionCandidate::status` and `DiscoveryCandidate::status` (C4);
- the file `Section::tag` strings "APPEAR__", "CELLS___", … (C4);
- `TimingRow::stage` names (C5, produced-only string).

Most string misses have one cause: blackbird serializes strings through two
shared helpers. `raw_string_field` takes `.data()`/`.size()` for a byte view,
and `Value{std::string}` goes through `std::make_shared`. The fail-closed
classifier cannot tell either from a quantity use without knowing those
helpers' meaning.

### Jev agreement

Setup:
- Model `jev-1.13.0`, one Choice per finding, independent calls.
- The state was the finding's declaration, type, observed values, and the
  same excerpt I started from (declaration line and up to twelve compare,
  switch, write and ingress lines each).
- The criteria were the brief's four, worded neutrally with no
  corpus-specific examples:
  - "Finite closed domain the code relies on";
  - "Open or extensible domain";
  - "Not a domain: a sentinel, a flag, a count, or a test value";
  - "Cannot tell from the excerpt".

| Corpus | Findings | Jev "closed" | Raw agreement | κ (3-class) |
|---|---|---|---|---|
| blackbird, first pass (87 findings, before the C10 removal) | 87 | 80 | 70/87 (80.5%) | 0.27 |
| blackbird, final (119) | 119 | 108 | 105/119 (88.2%) | 0.17 |
| BRepGPU, frozen (26) | 26 | 23 | 12/26 (46.2%) | −0.01 |

Jev's self-agreement across the two blackbird passes, on the 82 findings
present in both, was 80/82.

**Resolution of the first-pass blackbird disagreements (17).**
- Re-reading them **changed my labels** on 9 stage fields (for example
  `RawBeadsTrace::stage`, `RawBridgeTrace::stage_`, `spawn#stage`,
  `RawUiTrace::stage_`, `failure#stage`) from O to T.
  - I had called numbered progress checkpoints "extensible".
  - Every one of their values is written in the analyzed code, and nothing
    outside produces one. By the definition (open means other values can
    occur), they are closed.
  - For consistency I also relabelled two stage fields where Jev had agreed
    with O (`RawCallerTrace::stage_`, `RawProgramCall::stage_`).
- I **kept** 8:
  - `run_session#ret` and `trace_archive run#ret`: process exit statuses,
    and callers treat other values as failure;
  - `Node::site`: global site registry;
  - `RawProviderPhase::start#kind`: T, from the documented table at
    `provider_original.cpp:443`, which Jev's excerpt did not show;
  - `scalar#stage`: checkpoint numbers shared with a 50-value cross-subsystem
    numbering;
  - `record_offset`: a byte offset, now excluded by C7;
  - `RawAuthSource::value`: its meaning depends on the paired site;
  - `RawContextTrace::branch_`: branch codes 0..2.

**Final blackbird disagreements (14).** I kept all of mine:
- five O items that Jev called closed: two exit statuses, `Node::site`,
  `scalar#stage`, `RawAuthSource::value`;
- `start#kind`;
- seven stage, branch and channel fields that Jev called open with
  confidence 0.20-0.45. Jev itself flipped `RawTaskTrace::stage_` between
  passes, which marks these as genuinely ambiguous.
- `NativeFrame::begin#operation`, which Jev called cannot-tell. Its excerpt
  shows `static_cast<int>(op)` but not enum `Op`.

**BRepGPU disagreements (14).** All 14 kept, after re-reading:
- Jev called loop counters and table indices closed (`direction#n`/`#k`,
  `decode_row#section`, the four generated table indices,
  `alternative#index`). They are iterated by `for` loops or computed from a
  tag.
- Jev called the version number, the count, the mask, `matrix_norm#free`
  and Machin's constants closed.
- Jev called the device status codes closed.
- Jev called `run_test_hook` event codes not-a-domain at confidence 0.24.
  I kept T: they are two hook-point codes.

**Conclusion on Jev.** Under this question it behaves as a "closed" prior,
with κ near zero. It is not a usable second oracle for this classification.
The disagreements it raised were cheap and worth re-reading, and one of
them fixed a labelling principle. Whether a better-posed question
(separate Nouls for "is it a count", "is it an index", "is it a version")
would discriminate better is unmeasured.

## Recommendation

1. **Edit boundary: nothing.**
   - Held-out precision of the strictest tier was 46% frozen and 62%
     fixed. The bar is no effective false positives.
   - The surviving false classes are not separable by uses.
   - The finding is a design proposal, not a correctness defect (D5). It
     would invite scope creep mid-task, the Fan et al. and ImpossibleBench
     pressure the doctrine tribunal cites.
2. **`verbs scan`: at most a `--hypotheses` section, exit 0.**
   - Order it A, E, H, P, with the wording above ("values observed
     include …").
   - Tier E is the most actionable. All three blackbird E findings were
     true, and each names an enum that already exists. A narrower rule that
     reports only E would be a cheap, precise follow-up for whoever picks
     up discovery. It saw 3 findings on blackbird and 0 on BRepGPU, too few
     to claim a precision.
3. **Exit status: candidates never set it.** That holds in every mode.
4. **Should the rule exist in the basics? No.**
   - The basics' stated claim is about vlib types and escapes (§1-§4).
     Discovery is a separate concern, already split out as kind discovery
     (verbs-de3.21).
   - The check costs a dataflow extractor several times the size of the
     escape check's needs.
   - It meets its own bar only on the corpus it was tuned on.
   - Move this report's rule to a deferred bead (suggested title
     "enum-domain discovery (scan-only)", label `deferred`). There it can
     be revisited with:
     - runtime evidence: DynComp/Daikon-style observation of the values at
       ingress, which would also settle tier H's lower-bound problem;
     - a C++26 corpus that actually uses vlib.
   - SPEC §1 item 3, §5, §9.3's tuning paragraph and §6.4's
     `+ enum-candidate` line would go with it.

## Limits

- One labeller (me) plus Jev, whose agreement was at chance. No third
  label.
- The BRepGPU flags are approximate, and 32 of 187 sources are not
  analyzed. BRepGPU's CMake says C++17; the sources were parsed as C++20.
- Recall truth comes from a pool built with this extractor's facts, so
  domains with no extractable evidence are missing. Recall is an upper
  bound.
- The extractor is a probe. Unvisited constructs, such as structured
  bindings, writes through `memcpy` into whole structs, and coroutines,
  could hide ingress. A hidden ingress makes a subject look closed, which
  is a precision risk.
- Latency was not measured: extraction was about 13 minutes for blackbird's
  257 TUs at ten jobs on a loaded host, comparable to the tribunal's probe.

## Artifacts (scratchpad, not tracked)

All paths below are under
`/private/tmp/claude-501/-Users-patrickbeam-projects-verbs/31609136-8b04-4690-baf8-5705774fb9e7/scratchpad/enum-lane/`:
- `facts.cpp` and the `facts` binary;
- `rule_frozen.py` and `rule_fixed.py`;
- `excerpt_frozen.py` and `excerpt_fixed.py`;
- `jev_label.py`;
- `labels_bb_mine.tsv`, `labels_bb_mine_initial.tsv` and
  `labels_bg_mine.tsv`;
- `jev/bb.tsv`, `jev/bb3.tsv` and `jev/bg.tsv`, the raw choices and
  probabilities;
- `ex_bb_all.txt` and `ex_bg_all.txt`, the excerpts Jev saw;
- `out/bb/`, `out/bg_ok/`, the per-TU facts.

## Appendix A: blackbird findings (final rule), my label, Jev label

Tiers: A closed, E enum-fed, H open, P producer. Labels: T finite closed domain, O open, N not a domain. Jev: T closed, O open, N not_domain, ? cannot_tell (confidence).

| # | Tier | Primary declaration | Location | Mine | Jev | Reason |
|---|---|---|---|---|---|---|
| 1 | A | `blackbird::ProviderAuth::request#route` | `include/blackbird/provider_auth.hpp:88:55` | T | T (0.56) | API route set; request() validates route against exactly responses/chat/completions/messages/models and throws otherwise |
| 2 | A | `blackbird::detail::RawChildTrace::read#channel` | `include/blackbird/raw_provider.hpp:69:73` | T | T (0.85) | child output channel 1=stdout 2=stderr; enum RawReadChannel already exists for it |
| 3 | A | `blackbird::CodingEngine::Runtime::Preparation::mode` | `src/coding.cpp:1523:18` | T | T (0.83) | preparation mode 0 value/1 message/2 array selects three behaviours in prepare_native |
| 4 | A | `blackbird::CodingEngine::CommandTaskActivity::emit#branch` | `src/coding.cpp:422:26` | T | T (0.89) | task activity branch 0 running/1 finished/2 failed/3 unknown, mapped to phase text |
| 5 | A | `blackbird::CodingEngine::Runtime::ArgumentFrame::phase` | `src/coding.cpp:916:18` | T | T (0.93) | argument-frame phase 0 capture/1 restore/2 release dispatched in transfer_arguments |
| 6 | E | `blackbird::RawAuthTrace::stage_` | `include/blackbird/raw_auth.hpp:117:16` | T | T (0.40) | auth terminal stage: RawAuthField values plus 100 entered and 109 returned (raw_auth.cpp:422); closed, but RawAuthField alone does not cover it |
| 7 | E | `blackbird::detail::RawChildTrace::captures#channel` | `include/blackbird/raw_provider.hpp:60:30` | T | T (0.87) | same stdout/stderr channel; fed from RawReadChannel, so the enum exists |
| 8 | E | `blackbird::CodingEngine::Runtime::NativeFrame::begin#operation` | `src/coding.cpp:1469:34` | T | ? (0.56) | native-frame operation, every write is static_cast<int>(op) from enum Op |
| 9 | H | `blackbird::RetainedState::lookup#family` | `include/blackbird/retained_state.hpp:297:78` | T | T (0.80) | recovery-key family 1-4 selects four lookup branches; fixed key layout |
| 10 | H | `run_session#ret` | `src/main.cpp:76:5` | O | T (0.68) | process exit status (0, 1, 75=EX_TEMPFAIL restart); callers treat any other value as failure |
| 11 | H | `blackbird::(anonymous)::Decoder::string#tag` | `src/packet.cpp:240:36` | T | T (0.39) | packet string tag text/identity/word, a fixed wire tag table with named constants |
| 12 | H | `blackbird::(anonymous)::header_read#ret` | `src/raw_auth.cpp:549:3` | N | N (0.24) | generic header decoder; 1 and 40 are a version and a size checked as magic values |
| 13 | H | `blackbird::(anonymous)::Node::site` | `src/token_usage.cpp:61:17` | O | T (0.79) | trace site codes from the global site registry (1300,1320,3600,...) |
| 14 | H | `blackbird::(anonymous)::Node::kind` | `src/token_usage.cpp:62:16` | T | T (0.80) | phase kind, documented 1..14 at provider_original.cpp:443; observed set is a strict subset |
| 15 | P | `blackbird::RawProviderPhase::start#kind` | `include/blackbird/provider_original.hpp:169:27` | T | O (0.43) | phase kind 1..14, documented table at provider_original.cpp:443 |
| 16 | P | `blackbird::RawProviderPhase::scalar#stage` | `include/blackbird/provider_original.hpp:174:28` | O | T (0.36) | numbered acquisition checkpoints (15..64) shared across providers, undocumented names |
| 17 | P | `blackbird::RawProviderPhase::scalar#variant` | `include/blackbird/provider_original.hpp:174:48` | T | O (0.41) | scalar variant: documented field-shape table 0..8 at provider_original.cpp:455 |
| 18 | P | `blackbird::RawProviderPhase::finish#branch` | `include/blackbird/provider_original.hpp:176:28` | T | T (0.47) | semantic terminal branch 1..6, documented at provider_original.cpp:448 |
| 19 | P | `blackbird::RawProviderPhase::stage_` | `include/blackbird/provider_original.hpp:207:16` | O | O (0.56) | 50 stage checkpoint numbers grouped by subsystem (10s coding, 40s openai, 70s colleague) |
| 20 | P | `blackbird::RawProviderAcquisition::finish#branch` | `include/blackbird/provider_original.hpp:218:28` | T | T (0.76) | acquisition branch 1..6 (returned/Error/allocation/length/unknown/unresolved) |
| 21 | P | `blackbird::RawAuthTrace::boolean#field` | `include/blackbird/raw_auth.hpp:100:29` | T | T (0.20) | auth boolean field selector 1/2 naming which flag is recorded |
| 22 | P | `blackbird::RawAuthTrace::callback#operation` | `include/blackbird/raw_auth.hpp:102:30` | T | T (0.57) | auth callback operation codes 1..5 |
| 23 | P | `blackbird::RawAuthTrace::callback#boundary` | `include/blackbird/raw_auth.hpp:102:54` | T | T (0.51) | callback boundary 1 before body, 2 returned, 3 threw (auth_callback, provider_oauth.cpp:250) |
| 24 | P | `blackbird::RawAuthTrace::finish#branch` | `include/blackbird/raw_auth.hpp:107:28` | T | T (0.32) | auth terminal branch 1..6, same documented branch table |
| 25 | P | `blackbird::RawAuthExchange::start#operation` | `include/blackbird/raw_auth.hpp:130:27` | T | T (0.45) | auth exchange operation 1..5 |
| 26 | P | `blackbird::RawAuthExchange::finish#branch` | `include/blackbird/raw_auth.hpp:132:28` | T | T (0.48) | exchange terminal branch 2..6 |
| 27 | P | `blackbird::RawAuthSave::finish#branch` | `include/blackbird/raw_auth.hpp:152:28` | T | T (0.60) | auth save terminal branch 1..6, the shared branch table |
| 28 | P | `blackbird::RawAuthSave::stage_` | `include/blackbird/raw_auth.hpp:158:16` | T | T (0.35) | auth save stage 1..8 of one routine, all written here |
| 29 | P | `blackbird::RawAuthSource::value` | `include/blackbird/raw_auth.hpp:70:16` | O | T (0.27) | branch value whose meaning depends on the paired site code; several small tables share one field |
| 30 | P | `blackbird::RawBeadsTrace::assignment#` | `include/blackbird/raw_beads.hpp:75:45` | T | T (0.69) | beads assignment selector 1..4 (which flag and direction) |
| 31 | P | `blackbird::RawBeadsTrace::status#` | `include/blackbird/raw_beads.hpp:77:52` | T | T (0.61) | beads status class 1..3 attached to a status string |
| 32 | P | `blackbird::RawBeadsTrace::stage` | `include/blackbird/raw_beads.hpp:81:16` | T | T (0.41) | progress stage 1..10 of one beads operation; every value is written here and nothing else produces one, so the set is closed (relabelled after Jev disagreement) |
| 33 | P | `blackbird::RawBridgeTrace::stage_` | `include/blackbird/raw_bridge.hpp:33:16` | T | T (0.45) | progress stage 1..8 of one bridge operation, all written in the analyzed code (relabelled after Jev disagreement) |
| 34 | P | `blackbird::RawModuleToken::finish#reason` | `include/blackbird/raw_bridge.hpp:68:28` | T | T (0.75) | module finish reason 0..4 |
| 35 | P | `blackbird::RawCallerTrace::stage_` | `include/blackbird/raw_caller.hpp:139:16` | T | O (0.39) | progress stage 1..18 of one caller operation, all written in the analyzed code (relabelled for consistency with the stage resolution) |
| 36 | P | `blackbird::RawContextTrace::protection_return#branch` | `include/blackbird/raw_context.hpp:127:60` | T | T (0.80) | protection return branch 0..3 |
| 37 | P | `blackbird::RawContextTrace::branch_` | `include/blackbird/raw_context.hpp:133:16` | T | O (0.32) | context trace branch 0..2 |
| 38 | P | `blackbird::RawContextTrace::stage_` | `include/blackbird/raw_context.hpp:133:29` | T | T (0.47) | context stage 1..3, all written in the analyzed code (relabelled after Jev disagreement) |
| 39 | P | `blackbird::RawContextSource::purpose` | `include/blackbird/raw_context.hpp:137:16` | T | T (0.83) | context source purpose 0..3 |
| 40 | P | `blackbird::RawContextPair::finish#branch` | `include/blackbird/raw_context.hpp:155:28` | T | T (0.61) | context pair branch 0..3 |
| 41 | P | `blackbird::RawContextTrace::rows#variant` | `include/blackbird/raw_context.hpp:91:26` | T | T (0.77) | context rows variant 0..4 naming the row source |
| 42 | P | `blackbird::RawContextTrace::label#kind` | `include/blackbird/raw_context.hpp:98:27` | T | T (0.53) | context label kind 0..5 |
| 43 | P | `blackbird::RawFileToolTrace::argument#kind` | `include/blackbird/raw_file.hpp:38:30` | T | T (0.81) | file tool argument kind 0 path, 1 old, 2 replacement (tools.cpp:255-271) |
| 44 | P | `blackbird::RawFileToolTrace::range#mode` | `include/blackbird/raw_file.hpp:39:27` | T | T (0.79) | range mode, 2 when counting lines and 1 otherwise (tools.cpp:154) |
| 45 | P | `blackbird::RawFileToolTrace::selection#step` | `include/blackbird/raw_file.hpp:40:31` | T | T (0.49) | selection step 1..5 naming which body was selected |
| 46 | P | `blackbird::raw_main_control#kind` | `include/blackbird/raw_input.hpp:10:63` | T | T (0.80) | main control kind 1 quit/2 line/3/4 |
| 47 | P | `blackbird::raw_main_branch#branch` | `include/blackbird/raw_input.hpp:9:53` | T | O (0.35) | main dispatch branch codes 1..39, one per dispatch arm |
| 48 | P | `blackbird::RawOperationTrace::stage_` | `include/blackbird/raw_operation.hpp:131:16` | T | T (0.24) | operation stage 1..9 of one routine |
| 49 | P | `blackbird::RawOperationTrace::identity#kind` | `include/blackbird/raw_operation.hpp:47:30` | T | T (0.81) | identity kind 0 decision/1 invocation/2 attempt/3 generation/4 context |
| 50 | P | `blackbird::RawOperationTrace::callback_return#kind` | `include/blackbird/raw_operation.hpp:54:37` | T | T (0.72) | callback kind 0..6 naming the callback |
| 51 | P | `blackbird::RawParticipantTrace::finish#branch` | `include/blackbird/raw_participants.hpp:56:28` | T | T (0.81) | participant terminal branch codes |
| 52 | P | `blackbird::RawParticipantTrace::stage_` | `include/blackbird/raw_participants.hpp:62:16` | T | T (0.39) | participant stage 1..3 |
| 53 | P | `blackbird::RawProgramCall::RawProgramCall#method` | `include/blackbird/raw_program.hpp:12:31` | T | T (0.67) | program call method codes |
| 54 | P | `blackbird::RawProgramCall::encoded#kind` | `include/blackbird/raw_program.hpp:29:29` | T | T (0.33) | encoded kind 0..2 (proposal and others) |
| 55 | P | `blackbird::RawProgramCall::revision#kind` | `include/blackbird/raw_program.hpp:31:30` | T | T (0.65) | revision kind 0 program/1 tools/2 workflow |
| 56 | P | `blackbird::RawProgramCall::validation#kind` | `include/blackbird/raw_program.hpp:32:32` | T | T (0.57) | validation kind 0 modules/1 definitions/3 properties |
| 57 | P | `blackbird::RawProgramCall::stage_` | `include/blackbird/raw_program.hpp:44:16` | T | T (0.29) | program-call stage 1..8, all written in the analyzed code (relabelled for consistency) |
| 58 | P | `blackbird::RawProgramLifetime::finish#reason` | `include/blackbird/raw_program.hpp:70:28` | T | T (0.80) | program lifetime finish reason 0..4 |
| 59 | P | `blackbird::RawProviderTrace::finish#branch` | `include/blackbird/raw_provider.hpp:31:28` | T | T (0.55) | provider trace branch 1..6, documented at raw_provider.cpp:343 |
| 60 | P | `blackbird::detail::RawChildTrace::poll#channel` | `include/blackbird/raw_provider.hpp:65:51` | T | O (0.20) | poll channel 0 input/1/2 by descriptor |
| 61 | P | `blackbird::detail::RawChildTrace::close#channel` | `include/blackbird/raw_provider.hpp:76:27` | T | T (0.56) | closed-descriptor channel codes 0..3 (error_output closes as 2) |
| 62 | P | `blackbird::detail::RawChildTrace::refuse#operation` | `include/blackbird/raw_provider.hpp:79:28` | T | T (0.79) | refuse operation 1..4 |
| 63 | P | `blackbird::RawQueryPacket::RawQueryPacket#method` | `include/blackbird/raw_query.hpp:105:31` | T | T (0.32) | query packet method 1/2, documented method(read_packet1,decode_packet2) |
| 64 | P | `blackbird::RawQueryPacket::finish#branch` | `include/blackbird/raw_query.hpp:113:28` | T | T (0.69) | query packet branch 0..3 |
| 65 | P | `blackbird::RawQueryPacket::stage_` | `include/blackbird/raw_query.hpp:132:16` | T | T (0.47) | query packet stage, documented stage(size_check0,read1,decode2) |
| 66 | P | `blackbird::RawQueryTrace::returned#shape` | `include/blackbird/raw_query.hpp:44:30` | T | T (0.52) | query returned shape 1..4 |
| 67 | P | `blackbird::RawQueryTrace::failure#branch` | `include/blackbird/raw_query.hpp:45:29` | T | T (0.79) | query failure branch 1..3 |
| 68 | P | `blackbird::RawQueryTrace::stage_` | `include/blackbird/raw_query.hpp:66:16` | T | T (0.48) | query trace stage 1..4 (relabelled after Jev disagreement) |
| 69 | P | `blackbird::RawQueryLookup::filter#branch` | `include/blackbird/raw_query.hpp:80:28` | T | T (0.64) | fact-read filter branch, documented (selected1,skip_variable2,skip_attempt3) |
| 70 | P | `blackbird::RawQueryLookup::failure#branch` | `include/blackbird/raw_query.hpp:81:29` | T | T (0.79) | lookup failure branch 1..3 |
| 71 | P | `blackbird::raw_restart_source#kind` | `include/blackbird/raw_restart.hpp:28:63` | T | O (0.35) | restart source kind codes |
| 72 | P | `blackbird::RawSuccessorHandoff::retire#` | `include/blackbird/raw_restart.hpp:48:35` | T | T (0.29) | successor retire reason 1 consume/2/3 |
| 73 | P | `blackbird::raw_restart_call#method` | `include/blackbird/raw_restart.hpp:6:63` | T | T (0.72) | restart call method, documented method(schedule1,resume2,restore3) |
| 74 | P | `blackbird::RawRetainedPair::finish#branch` | `include/blackbird/raw_retained.hpp:201:28` | T | T (0.55) | retained pair branch 0..5 |
| 75 | P | `blackbird::RawStorageAction::operand#kind` | `include/blackbird/raw_storage.hpp:215:29` | T | T (0.61) | storage operand kind 1 name/2 |
| 76 | P | `blackbird::RawTaskTrace::finish#branch` | `include/blackbird/raw_tasks.hpp:36:28` | T | T (0.35) | task branch, documented (returned0,duplicate1,conflict2,Error3,allocation4,unknown5) |
| 77 | P | `blackbird::RawTaskTrace::stage_` | `include/blackbird/raw_tasks.hpp:61:16` | T | O (0.32) | task trace stage 1..8 (relabelled after Jev disagreement) |
| 78 | P | `blackbird::RawTurnTrace::activation#kind` | `include/blackbird/raw_turn.hpp:113:39` | T | T (0.60) | activation kind 0 program/1 tools/2 budget |
| 79 | P | `blackbird::RawTurnTrace::source_return#branch` | `include/blackbird/raw_turn.hpp:116:56` | T | T (0.79) | source return branch 0..3 |
| 80 | P | `blackbird::RawTaskActivityTrace::activity#branch` | `include/blackbird/raw_turn.hpp:28:37` | T | T (0.55) | task activity binding branch, documented (running0,finished1,failed2,unknown3) |
| 81 | P | `blackbird::RawTaskActivityTrace::notified#branch` | `include/blackbird/raw_turn.hpp:30:56` | T | T (0.69) | activity notification branch 0..4 |
| 82 | P | `blackbird::RawPolicyTrace::RawPolicyTrace#method` | `include/blackbird/raw_turn.hpp:39:31` | T | T (0.63) | policy method, documented (read0,propose1,observe2,restore3) |
| 83 | P | `blackbird::RawPolicyTrace::finish#branch` | `include/blackbird/raw_turn.hpp:51:28` | T | T (0.49) | policy finish branch 0..4 |
| 84 | P | `blackbird::RawProtocolTrace::finish#branch` | `include/blackbird/raw_turn.hpp:80:28` | T | T (0.73) | protocol branch 0..3 |
| 85 | P | `blackbird::RawUiTrace::stage_` | `include/blackbird/raw_ui.hpp:105:16` | T | T (0.49) | UI trace stage 1..5 (relabelled after Jev disagreement) |
| 86 | P | `blackbird::RawUiValueOrigin::kind` | `include/blackbird/raw_ui.hpp:26:16` | T | T (0.60) | UI value origin kind 0..4 |
| 87 | P | `blackbird::(anonymous)::source#kind` | `src/backstop.cpp:17:56` | T | T (0.63) | backstop source kind codes |
| 88 | P | `blackbird::(anonymous)::mutation#kind` | `src/backstop.cpp:27:51` | T | T (0.71) | backstop mutation kind codes |
| 89 | P | `blackbird::(anonymous)::encoded#role` | `src/backstop.cpp:36:57` | T | T (0.69) | backstop encoded role codes |
| 90 | P | `(anonymous)::Descriptor::observed#kind` | `src/candidate.cpp:261:30` | T | T (0.24) | descriptor observed kind 1..5 |
| 91 | P | `(anonymous)::predicate#kind` | `src/candidate.cpp:76:63` | T | T (0.72) | candidate predicate kind 1..8 |
| 92 | P | `blackbird::CodingEngine::Runtime::NativeFrame::original#role` | `src/coding.cpp:1506:32` | T | T (0.51) | bridge original role 1..4 naming the bridged string |
| 93 | P | `blackbird::CodingEngine::Runtime::Trace::finish#branch` | `src/coding.cpp:507:30` | T | T (0.77) | runtime trace branch 1..3 |
| 94 | P | `blackbird::CodingEngine::turn(TurnInput)::Terminal::branch` | `src/coding.cpp:5742:19` | T | T (0.81) | turn terminal branch, documented (returned0,refused1,Error2,allocation3,unknown4) |
| 95 | P | `blackbird::CodingEngine::turn(TurnInput)::Terminal::stage` | `src/coding.cpp:5742:28` | T | T (0.75) | turn stage, documented stage(reset0,begin1,evaluate2,settle3,cancel_clear4,closed5) |
| 96 | P | `blackbird::(anonymous)::ControlTrace::finish#branch` | `src/command_jobs.cpp:293:28` | T | T (0.68) | control trace branch 1..5 |
| 97 | P | `blackbird::CommandJobs::Impl::caller_stop#source` | `src/command_jobs.cpp:395:43` | T | T (0.43) | job stop source codes 5..7 |
| 98 | P | `blackbird::detail::Child::native_stage` | `src/native_process.hpp:432:16` | T | T (0.59) | native spawn stage 0..14 of one spawn routine, all written here |
| 99 | P | `blackbird::Participants::Impl::state#branch` | `src/participants.cpp:266:63` | T | T (0.84) | participant state branch 1..3 |
| 100 | P | `blackbird::Participants::Impl::stop#source` | `src/participants.cpp:321:26` | T | T (0.25) | participant stop source 1..5 |
| 101 | P | `blackbird::(anonymous)::close_native#reason` | `src/participants.cpp:96:32` | T | T (0.85) | native close reason 1..3 |
| 102 | P | `blackbird::(anonymous)::Schema::kind` | `src/raw_authored.cpp:16:16` | T | T (0.85) | authored schema kind 1..4 paired one-to-one with event codes |
| 103 | P | `blackbird::(anonymous)::wake_terminal#branch` | `src/raw_command.cpp:192:54` | T | T (0.91) | wake terminal branch 1 returned/2 failed |
| 104 | P | `blackbird::(anonymous)::Call::body#role` | `src/raw_file.cpp:259:33` | T | T (0.77) | file body role 1..4 |
| 105 | P | `blackbird::(anonymous)::Resource::ending_` | `src/raw_file.cpp:428:16` | T | T (0.44) | resource ending 1..3 (initializer 1 is also a member) |
| 106 | P | `blackbird::(anonymous)::failure#stage` | `src/raw_runtime.cpp:682:28` | T | T (0.69) | recorder failure stage 1..8 of one routine (relabelled after Jev disagreement) |
| 107 | P | `blackbird::RawStorageCall::prefix#method` | `src/raw_storage.cpp:1190:37` | T | T (0.76) | storage method 1/2 (positioned or full) |
| 108 | P | `blackbird::(anonymous)::outcome#success` | `src/raw_storage.cpp:70:52` | T | T (0.59) | storage outcome branch (0 returned, 2 ...; 1 chosen for Error inside) |
| 109 | P | `blackbird::(anonymous)::ui_branch#ret` | `src/raw_ui.cpp:13:24` | T | T (0.83) | UI branch wire code mapped from RawOperationBranch, documented branch table |
| 110 | P | `blackbird::(anonymous)::ordinal_key#family` | `src/retained_state.cpp:85:39` | T | T (0.56) | recovery-key family byte from a fixed key layout |
| 111 | P | `blackbird::(anonymous)::session_call#action` | `src/session.cpp:50:57` | T | T (0.71) | session call action 1..3 |
| 112 | P | `blackbird::(anonymous)::borrow#kind` | `src/station.cpp:19:62` | T | T (0.68) | station borrow kind codes 1..9 |
| 113 | P | `blackbird::(anonymous)::decision#kind` | `src/station.cpp:61:50` | T | T (0.95) | station decision kind 1..4 |
| 114 | P | `blackbird::(anonymous)::enqueue_ui_prompt#kind` | `src/terminal.cpp:1415:83` | T | T (0.73) | UI prompt kind 1 queued/2 recovered |
| 115 | P | `blackbird::(anonymous)::custody#method` | `src/terminal_custody.cpp:104:47` | T | T (0.55) | terminal custody method codes 1..4 |
| 116 | P | `blackbird::(anonymous)::descriptor#method` | `src/terminal_custody.cpp:155:50` | T | T (0.56) | descriptor method codes 1,2,3,4,10 |
| 117 | P | `blackbird::(anonymous)::editor_request#method` | `src/terminal_custody.cpp:570:61` | T | T (0.65) | editor request method 1..12 |
| 118 | P | `blackbird::(anonymous)::editor_source#role` | `src/terminal_custody.cpp:578:60` | T | T (0.73) | editor source role 1..10 |
| 119 | P | `(anonymous)::run#ret` | `src/trace_archive_main.cpp:711:5` | O | T (0.52) | process exit status 0/2 |

## Appendix B: BRepGPU findings (held out), my label, Jev label

Tier is frozen rule → loader-fixed rule.

| # | Tier | Primary declaration | Location | Mine | Jev | Reason |
|---|---|---|---|---|---|---|
| 1 | A→H | `brepgpu::discovery_detail::direction#n` | `native/discovery_math.hpp:117:39` | N | T (0.55) | index into a fixed table of nine normals; callers iterate it with for(n=0;n<10;++n) |
| 2 | A→H | `brepgpu::discovery_detail::direction#k` | `native/discovery_math.hpp:117:50` | N | T (0.75) | coordinate axis index from for(k=0;k<3;++k) |
| 3 | A→H | `bgfd::Engine::winding#ret` | `native/face_domain/face_domain.cpp:315:21` | T | T (0.53) | point classification 0 outside, 1 inside, 2 on boundary |
| 4 | A→A | `bgom10::Api::version` | `native/mesher/../om10/types.hpp:116:12` | N | T (0.85) | API struct version number 1/2 |
| 5 | A→A | `bgmesh_filter::classify#ret` | `native/mesher/bound_filter.hpp:115:25` | T | T (0.96) | interval decision 0 below, 1 above, 2 unresolved (bound_filter.hpp:115-124) |
| 6 | A→A | `bgmesh::FacetBVH::Impl::Entry::state` | `native/mesher/contact.cpp:592:13` | T | T (0.93) | open-addressing slot state 0 empty, 1 occupied, 2 tombstone (contact.cpp:670) |
| 7 | A→A | `bgmesh::DomainIssue::segment_count` | `native/mesher/domain.hpp:27:12` | N | N (0.36) | a segment count |
| 8 | A→A | `bgmesh::PoleCutHistory::radial_pending_mask` | `native/mesher/pole_seed.hpp:60:12` | N | T (0.87) | bit mask (0 or both radial bits) |
| 9 | A→H | `bgmesh::(anonymous)::decode_row#section` | `native/mesher/source.cpp:189:29` | N | T (0.81) | section index passed from a loop variable at source.cpp:746 |
| 10 | A→H | `brepgpu::projection_detail::matrix_norm#free` | `native/projection_solver.hpp:70:59` | N | T (0.87) | number of free variables 1..3 |
| 11 | A→A | `(anonymous)::Plugin::pair_state` | `native/runtime.cpp:90:14` | T | T (0.89) | plugin probe state 0 unprobed, 1 valid, 2 unsupported (comment at runtime.cpp:92) |
| 12 | A→A | `(anonymous)::Plugin::discovery_state` | `native/runtime.cpp:91:14` | T | T (0.96) | plugin probe state, same three states |
| 13 | A→A | `(anonymous)::Plugin::projection_state` | `native/runtime.cpp:92:14` | T | T (0.96) | plugin probe state, documented in the declaration comment |
| 14 | H→H | `brepgpu::discovery_detail::node_lower#mode` | `native/discovery_math.hpp:181:35` | T | T (0.76) | bound mode BG_BOUND_DOP26 / BG_BOUND_BERNSTEIN from the C API |
| 15 | H→H | `bgmesh::adaptive::detail::device_check#status` | `native/mesher/adaptive_device_owner.hpp:66:34` | O | T (0.64) | device API status codes |
| 16 | H→H | `bgmesh::adaptive::numeric::sine_anchor#i` | `native/mesher/adaptive_rn_tables.hpp:18:46` | N | T (0.53) | index into a constant interval table |
| 17 | H→H | `bgmesh::adaptive::numeric::cosine_coefficient#i` | `native/mesher/adaptive_rn_tables.hpp:54:53` | N | T (0.55) | series coefficient index |
| 18 | H→H | `bgmesh::adaptive::numeric::cosine_anchor#i` | `native/mesher/adaptive_rn_tables.hpp:66:48` | N | T (0.49) | index into a constant interval table |
| 19 | H→H | `bgmesh::adaptive::numeric::sine_coefficient#i` | `native/mesher/adaptive_rn_tables.hpp:7:51` | N | T (0.73) | series coefficient index |
| 20 | H→H | `bgmesh::(anonymous)::Decode::alternative#index` | `native/mesher/mesh_io.cpp:375:93` | N | T (0.40) | std::variant alternative index computed from a tag |
| 21 | H→H | `bgmesh::point_detail::(anonymous)::coefficients#bits` | `native/mesher/point_trig.cpp:26:40` | T | T (0.92) | supported precision 128/192/256 selecting one of three tables |
| 22 | P→P | `bgmesh::(anonymous)::AtanRequest::divisor` | `native/mesher/geometry_analytic.cpp:78:11` | N | T (0.65) | numeric constants 5 and 239 of Machin's formula |
| 23 | P→P | `bgmesh::point_detail::TrigTable::bits` | `native/mesher/point_trig_tables.hpp:13:12` | T | T (0.53) | table precision 128/192/256, the same three-value set |
| 24 | P→P | `run_test_hook#` | `native/runtime.cpp:33:35` | T | N (0.24) | test-hook event code 1/2 |
| 25 | P→P | `(anonymous)::diagnostic#stage` | `native/runtime.cpp:54:81` | T | T (0.43) | diagnostic stage from the BG_STAGE_* table of the C API |
| 26 | P→P | `brepgpu_topology::Operation::error#stage` | `native/topology_internal.hpp:21:40` | T | T (0.57) | operation error stage from the BG_STAGE_* table |
