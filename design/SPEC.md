# verbs basics: design specification

Status: draft for tribunal, 2026-10-17. Scope: the basics only, per the
basics-first principle (journal/2026-10-17-operator-decisions.md). Everything
outside this scope is a bead under `verbs-de3` and is named here only to mark
the edge. Inputs: design/verbs-design-brief.md (orientation, not settled), the
four lane reports in papers/2026-10-17-*.md, and the operator's decisions in
the journal. Where this spec departs from the brief, it says so and why.

Marked **[decide]**: choices that need the operator. Marked **[toolchain]**:
choices that depend on the C++26 Clang lane
(papers/2026-10-17-cpp26-clang-toolchain.md, pending).

---

## 1. What verbs does in the basics

verbs makes invariants of C++ values explicit in their types, so that
violations are rejected by the compiler or at one checked entry point. It
then tells an agent, at each edit, what changed about those claims. It has
four parts:

1. **vlib**, a header library of closed value types: `Bounded`, `Refined`,
   `Id`, and finite enums with checked ingress. Each carries one invariant in
   its representation, so no operation outside the type can break it.
2. **The escape check**, which finds code that bypasses vlib encapsulation or
   silences verbs. Every claim in (1) rests on it.
3. **The enum-candidate check**, the first discovery check. It finds integers
   and strings used as small finite domains and proposes an enum with checked
   ingress.
4. **`verbs check`**, a stateless command that Blackbird's edit hook calls
   with the changed paths. It prints what the edit added, resolved, or
   decided, and the assumptions under which every claim holds.

There is no daemon, no database, no LLM dependency, and no annotation syntax
for invariants in the basics: the vlib type of a declaration *is* its
invariant declaration.

**Annotations clarify; they never encumber.** Where the meaning is
self-evident from the code, there is no annotation. verbs asks for one only
to record something the code cannot say, such as the rationale of a decision
(§7). Corollary: if a finding could only be silenced by an annotation that
states the obvious, the check is wrong. Fix the check; don't ask for the
annotation.

## 2. The claim

verbs states claims in one form:

> Every value of declaration D satisfies predicate P, by mechanism M, under
> the claim boundary.

- **D** is a declaration: a field, variable, parameter, or function return.
- **P** is one of the basics vocabulary (§2.1).
- **M** is one of `representation`, `typecheck`, `construction` (§2.2).

verbs reports each declaration it examines in exactly one state:

| State | Meaning |
|---|---|
| `holds` | D's type carries P, and no escape in the analyzed code touches D's values. |
| `finding` | A check found a concrete defect or candidate, with its evidence. |
| `decided` | A recorded decision covers the finding (§7). |
| `outside` | D is outside the claim boundary, with the reason. |

There is no `unknown` state for declarations verbs examined. A case it cannot
judge falls outside the claim, and the report names the boundary rule that
excludes it.

### 2.1 Basics predicate vocabulary

| Predicate | Carried by | Example |
|---|---|---|
| `range(lo, hi)` | `Bounded<lo, hi>` | retries in 0..5 |
| `in{v1..vn}` | `enum class` with checked ingress | mode in {Idle, Armed, Firing} |
| `kind(Tag)` | `Id<Tag, Rep>` | a UserId is never an OrderId |
| `refined(pred-id)` | `Refined<T, Pred>` | a non-empty, sorted span |
| `const` | `const` declaration | owner never changes after construction |

`refined` is the one open-ended entry. Its predicate is an opaque named C++
function, checked once at construction. verbs records its identity, not its
logic. Richer predicate logic belongs to the future Becoming project and is
not part of verbs.

A cross-field invariant within one object is expressed in the basics only as
a whole-value refinement: an immutable aggregate wrapped in `Refined`, which
is replaced wholesale rather than mutated field by field. Mutable owners with
cross-field invariants need static checking of each mutator, which is
deferred (bead).

### 2.2 Mechanisms

| Mechanism | What enforces P | When a violation is caught |
|---|---|---|
| `representation` | The type cannot hold a value violating P | Never representable |
| `typecheck` | The compiler rejects code that could produce a violating value | Compile time |
| `construction` | The single entry point checks P and refuses violating input | Runtime, at ingress only |

These are not ranked by an integer. A report shows the set of mechanisms
behind each claim. Consumers decide what is strong enough. The brief's
`[[assume]]` rule holds: vlib emits `[[assume(P)]]` only inside its own
accessors, where every path into the representation was checked.

### 2.3 Claim boundary

Every claim holds only under these assumptions. `verbs check` prints them in
the footer of every report (§6.4).

1. No exception unwinds mid-mutation (bead: unwind preservation).
2. No moved-from object is used (bead: moved-from weakening).
3. An invariant belongs to exactly one declaration and its type. Mutation
   goes only through that type's operations.
4. The owner is used from one thread at a time. Lock-scoped and lock-free
   cases are outside the claim, and memory ordering is never claimed.
5. No call to unowned code happens while an invariant is temporarily broken.
   vlib types never break theirs mid-operation.
6. Single-state predicates only: nothing relates the value before a mutation
   to the value after, except `const`.
7. The analyzed code is all the code. A translation unit outside the
   compilation database can hold escapes verbs never saw. The report names
   the database it used.

## 3. vlib

vlib is header-only C++26 in namespace `verbs`. The type rules below are the
specification. The code fragments show shape, not final source.

### 3.1 `Bounded<Lo, Hi>`

An integer whose value is always in `[Lo, Hi]`.

**Bounds.** `std::int64_t` in the basics. Larger bounds and unsigned values
above `INT64_MAX` are deferred (bead). Storage is the smallest signed type
that holds `[Lo, Hi]`. An empty domain (`Lo > Hi`) is a compile error.

**Ingress.** There is no constructor from a raw integer. Values enter only
two ways:
- `Bounded::lit<V>()`, which is consteval and rejects out-of-range `V` at
  compile time (`typecheck`);
- `Bounded::make(v)`, which returns `std::optional<Bounded>` and checks
  at runtime (`construction`).

**No default constructor.** A declaration must be initialized explicitly.
Defaulting to `Lo` or to 0 would invent a value the author never chose.

**Widening is implicit, narrowing never.** `Bounded<A, B>` converts to
`Bounded<C, D>` exactly when `C <= A && B <= D`.

**Arithmetic widens.** `x + y` for `Bounded<a, b>` and `Bounded<c, d>` has
type `Bounded<a + c, b + d>`. Subtraction, multiplication and negation follow
interval arithmetic. Division and remainder exist only when the divisor's
range excludes 0. Result bounds are computed in `__int128` with an explicit
`static_assert` when they leave `int64_t`. Unlike the brief's sketch, this
does not rely on undefined behaviour making constant evaluation fail
(bounded::integer's approach, `quarantine/bounded-integer/source/bounded/arithmetic/plus.cpp`).
The runtime computation cannot overflow, because the result type's range
holds every possible result.

**The accumulator problem, and its rule.** Pure widening cannot type
`sum = sum + x` in a loop: the right side has a wider type than `sum`
(core literature §7, Wuffs). The basics add one rule:
- **Compound assignment narrows with an unconditional check.** `sum += x`
  compiles whenever the intervals overlap. It checks that the result fits
  and calls the verbs violation handler if not. The handler never returns.
- Plain `sum = sum + x` does not compile. The diagnostic names `+=` and
  `verbs::narrow`.
- `verbs::narrow<B>(x)` returns `std::optional<B>` for code that handles
  the failure.
- `verbs::clamp<B>(x)` saturates explicitly.

A compound assignment is a `construction` point. The report counts it as a
runtime check, not as typecheck.

**Why not C++26 contracts for this check:** P2900 lets the build select the
`ignore` evaluation semantic. An ignored check would store an out-of-range
value, which breaks the representation invariant and makes the accessor's
`[[assume]]` undefined behaviour. Representation invariants therefore use
vlib's own always-on check. Contracts are reserved for preconditions where
`ignore` is an acceptable build choice.

**Access.** `get()` returns `std::int64_t` and carries
`[[assume(Lo <= v && v <= Hi)]]`. The stored member is private.
bounded::integer makes it public for use as a non-type template parameter.
vlib chooses encapsulation; `lit<V>` covers compile-time use.

**Comparison** with any `Bounded` and with raw integers. Comparison is not
ingress.

```cpp
template <std::int64_t Lo, std::int64_t Hi>
class Bounded {
public:
    template <std::int64_t V> requires (Lo <= V && V <= Hi)
    static consteval Bounded lit() noexcept;
    static constexpr std::optional<Bounded> make(std::integral auto v) noexcept;
    template <std::int64_t C, std::int64_t D> requires (C <= Lo && Hi <= D)
    constexpr operator Bounded<C, D>() const noexcept;
    constexpr std::int64_t get() const noexcept;
    template <std::int64_t A, std::int64_t B>
        requires (Lo <= Hi + B && Lo + A <= Hi)   // the result range can overlap [Lo, Hi]
    constexpr Bounded& operator+=(Bounded<A, B> y) noexcept;   // checked narrowing
    Bounded() = delete;
    Bounded(std::integral auto) = delete;
private:
    rep v_;
};
```

### 3.2 `Refined<T, Pred>`

A `T` that satisfied `Pred` at construction and cannot be mutated afterwards.

- `Refined::make(T v)` returns `std::expected<Refined, Violation>`.
- `get()` returns `const T&`. There is no mutable access, and replacement is
  by assignment from another `Refined`.
- `Pred` must satisfy `verbs::named_predicate`: an empty, default-constructible
  type with a `static constexpr bool operator()(const T&) noexcept` and a
  stable identity. Lambda closure types fail the concept, so the brief's ban
  on lambda predicates is enforced by the type system rather than by review.
- **Identity.** **[toolchain]** With reflection, the identity is the
  predicate's fully qualified name (`std::meta::display_string_of`).
  Without it, `Pred::id` is a required `static constexpr std::string_view`.
- `Violation` carries the predicate identity and never the value. This keeps
  the property of the existing `check()` placeholder that values never leak
  into errors.

### 3.3 `Id<Tag, Rep>`

A strong typedef: an `Id<A>` is never an `Id<B>`. It has explicit
construction from `Rep`, `get()`, equality and ordering, and no arithmetic.
Kinds with arithmetic, such as point and difference pairs
(strong_type's `affine_point`/`difference`, timestamp and duration), are
deferred (bead).

### 3.4 Finite enums with checked ingress

The invariant `in{...}` needs two things C++ does not supply together: an
exact list of the domain, and a checked path from raw values into it.
`static_cast<Mode>(7)` creates a `Mode` outside the declared enumerators, so
an `enum class` alone does not carry the invariant.

- **Domain.** **[toolchain]** With reflection, a plain `enum class` is
  enough, and `verbs::enumerators<E>` comes from
  `std::meta::enumerators_of`. Without it, `VERBS_ENUM(Mode, std::uint8_t,
  Idle, Armed, Firing)` declares the enum and its value and name arrays. That
  is the brief's macro, needed only until reflection is available.
- **Ingress.** `verbs::to_enum<E>(raw)` returns `std::optional<E>` after a
  membership check (`construction`). `verbs::from_string<E>(sv)` does the
  same for names.
- **Exhaustiveness.** Consumers build with `-Werror=switch-enum`.
- **Escapes.** The escape check flags `static_cast`, C-style casts and
  `std::bit_cast` from integers to a verbs-domain enum outside `to_enum`.

### 3.5 What vlib does not have in the basics

The brief's Consumed-analysis typestate, phantom typestate, TSA authority
capabilities, FSM tables and two-state predicates are all deferred (beads).
vlib in the basics is exactly §3.1–3.4 and the violation handler.

## 4. The escape check

Every `holds` claim in §2 is true only if nothing bypasses vlib's
encapsulation. The escape check finds code that does. A `finding` from it
names the construct, the declaration whose claim it voids, and the location.

**Bypasses of representation:**
- `const_cast`, `reinterpret_cast`, C-style casts or `std::bit_cast` whose
  source or target involves a vlib type or a verbs-domain enum;
- `memcpy`, `memmove`, `memset` or a `std::byte` view writing into a vlib
  object;
- a union member of vlib type;
- integer-to-enum casts outside `verbs::to_enum` (§3.4).

**Silencing:**
- `NOLINT` comments naming verbs, and `#pragma clang diagnostic` that
  disables `-Wswitch-enum`, `-Wconversion` or verbs-related warnings;
- `[[assume]]` written outside vlib;
- changes to verbs configuration or decision records (§7).

These come from the agent-feedback lane: push feedback raises gaming
pressure, and suppressions are the common gaming move. Silencing findings are
reported in every delta, whoever added them.

**Precision bar.** The escape check must have zero effective false positives
on vlib-using code, because an agent acts on every finding (Sadowski et al.;
core literature §9). It matches syntax with full type information, so it can
reach that bar. A construct that cannot be judged, such as a cast through
`void*` in a template that is never instantiated, is not reported as an
escape. It is reported as `outside`, with the reason.

## 5. The enum-candidate check

The first discovery check. Kind discovery follows once its interaction
definition is designed (bead; core literature §1, Lackwit's 65% collapse).

**Subject:** a declaration (field, variable, parameter, or function return)
of integer type, or of `std::string`, `std::string_view` or `const char*`.

**Evidence collected per subject, across all analyzed translation units:**
- the set of literal constants it is compared against (`==`, `!=`, `case`
  labels);
- the set of literal constants assigned or initialized into it;
- the set of functions containing those sites;
- **uses that disqualify it** ("escapes" in the brief):
  - arithmetic other than comparison;
  - passing it to a function outside the analyzed code;
  - taking its address or a non-const reference to it;
  - streaming or serialization calls;
  - comparison against a non-literal value.

**Rule.** The subject is a candidate when:
1. the union of literal sets has between 2 and 16 values;
2. the sites span at least 2 functions;
3. no disqualifying use exists.

**Output policy.** Only candidates meeting all three conditions are
`finding`s. A subject with disqualifying uses is never shown at the edit
boundary. `verbs scan --hypotheses` lists those subjects for a human or
agent who asks.

This applies the compiler-check bar from the literature: an agent acts on
everything it is shown, so the edit-boundary feed carries only what is very
likely right. The thresholds are parameters to calibrate on the corpus (§9.3).

**Suggestion.** A finding carries its evidence and the concrete
encoding:
- an `enum class` with the observed values;
- `verbs::to_enum` at the ingress sites it found (the assignments from
  non-literal sources, if any; otherwise the declaration's initializer);
- `-Werror=switch-enum`.

verbs cannot name the enumerators. The finding asks for names rather than
inventing them.

**Resurfacing a decided candidate.** A decision (§7) records the values seen
when it was made. A decided candidate resurfaces as a finding when new
literal values appear outside that set, or when every disqualifying use that
justified an `open_domain` decision disappears.

## 6. `verbs check`

### 6.1 Interface

```
verbs scan  -p <build-dir> [--hypotheses]          # full analysis; writes facts and report
verbs check -p <build-dir> --changed <path>...     # incremental; prints the delta
```

The only caller contract is that Blackbird's edit hook runs `verbs check`
with the paths the edit touched, and appends stdout to the edit's tool
result. How Blackbird does that belongs to Blackbird.

Exit status:
- 0 when the delta has no new findings;
- 1 when it has new findings;
- 2 on a tool failure. A failure prints what failed, and the report says the
  claims for that translation unit were not refreshed.

### 6.2 Pipeline

1. **Affected translation units.** These are the changed sources plus every
   translation unit whose recorded include set contains a changed file.
   Include sets come from verbs' own preprocessor callbacks during fact
   extraction, stored per unit. This needs no build-system integration and no
   Ninja dependency.
2. **Extraction.** For each affected unit, verbs parses it with the
   compilation database's arguments and runs the matchers. It writes:
   - a facts file per unit, holding evidence for cross-unit checks and the
     include set;
   - that unit's local findings (escapes).

   Units run in parallel across cores.
3. **Cross-unit evaluation.** The enum-candidate rule runs over the facts
   files of every unit.
4. **Delta.** verbs compares the new findings with the previous report,
   using stable keys (§6.3). It prints the delta and writes the new report.

The first `verbs check` without facts files runs `verbs scan`. Facts files
and reports live in `<build-dir>/verbs/` and are disposable. Their format is
an owned, versioned binary format; a version mismatch deletes and rebuilds.

The brief's preservation verdicts and `preservation_dep` hashes are not
built: the basics have no preservation verdicts to cache, because vlib
invariants are preserved by construction. The edit-keyed cache is deferred
(bead), pending the latency measurement (bead).

### 6.3 Stable keys

A finding is keyed by its check name, the subject's qualified name, and the
evidence class. Line numbers are never part of the key. They appear only as
the location shown. Renaming a subject retires its old finding and adds a new
one. That is correct, because renaming changes the subject.

### 6.4 Output

Short, ranked, and scoped to the change, as the agent-feedback evidence asks.
Each finding gives the evidence and one concrete encoding.

```
verbs · 3 TUs · 1.2 s · build/debug
+ enum-candidate  Door::mode (int)  src/door.cpp:41
    values {0, 1, 3}: compared or assigned in 4 functions; no disqualifying use
    encode: enum class Door::Mode with verbs::to_enum at src/net.cpp:88; name the values
- escape  Ledger::balance  const_cast removed  src/ledger.cpp:120
! decision added  Packet::kind  open_domain "wire protocol reserves 3-7"  src/packet.hpp:14
claims assume: no unwind mid-mutation · no moved-from use · single owner · one thread
```

- `+` is a new finding, `-` a resolved one, and `!` a decision or silencing
  change.
- New findings are ordered escapes first, then candidates. At most N findings
  per file and M in total are printed, with a count of those withheld.
- The footer line is always printed.

This output goes to Blackbird, so it is an external boundary. Its format is a
contract versioned with verbs.

## 7. Decisions

A decision records a human or agent verdict on a finding that the code cannot
express itself. The brief's verdicts carry over:
- `rejected`: the hypothesis is false;
- `open_domain`: deliberately unconstrained, with a rationale;
- `accepted_pending`: true, and encoding is planned.

The brief puts decisions in `.verbs/decisions.jsonl`. JSON persistence
violates BLACKBIRD.md, and the operator asked for something that sucks less.
**Decided (operator, 2026-10-17): the decision goes on the declaration it
concerns.** The deciding reason: nearly every reader will be an LLM agent, and
an agent about to change a declaration reads the file that holds it. A
decision on the declaration is in view when it matters; a sidecar file
helps only an agent that already knows to look for it.

```cpp
VERBS_OPEN_DOMAIN("wire protocol reserves 3-7 for future modes", seen(0, 1, 3))
std::uint8_t kind;
```

The macro expands to `[[clang::annotate("verbs:open_domain", ...)]]` today,
and to a C++26 annotation (`[[=verbs::open_domain{...}]]`) when the Clang in
use supports P3394. **[toolchain]**

What this buys over a separate file:
- The decision moves with the code through renames, moves and refactors.
  The brief's USR-plus-qualified-name keying and its orphan handling are no
  longer needed.
- The repository documents itself: the rationale sits next to the field it
  explains, which is the operator's stated preference.
- It shows up in every diff and code review with no extra machinery.
  `verbs check` reports every added or changed decision as a `!` line, which
  is the Goodhart defence without an author field. `git blame` names the
  author.
- There is no file format to design, parse or fuzz. The compiler parses it.

A decision is the one annotation the basics ask for, because its rationale
is exactly what the code cannot say (§1). A `rejected` verdict whose reason
is obvious from the code is evidence of a check defect, not a decision to
record.

What it cannot cover: subjects in code the team cannot edit (vendored,
generated). A sidecar file for those is deferred (bead) until a corpus repo
needs it.

## 8. Toolchain

**[toolchain]** The operator chose C++26 for all C++ code. Upstream Clang,
trunk included, lacks P2996 reflection and P2900 contracts. verbs' analyses
are Clang-only, and the Clang that analyzes code must parse every construct
vlib uses. A lane is measuring what owning a merged C++26 Clang costs.

Requirements on whatever it selects:
1. One Clang builds vlib, its tests, the verbs tools, and the corpus code
   verbs analyzes.
2. The verbs tools link that Clang's libraries, built with matching settings:
   `-fvisibility-inlines-hidden`, RTTI on, no exceptions across LLVM frames,
   C enabled in CMake, and the resource directory baked in
   (cpp-toolchain-burdens §5-7).
3. CMake presets set `CMAKE_OSX_SYSROOT` from `xcrun --show-sdk-path`.
4. Any change to the toolchain rebuilds every verbs binary.

**Design rule:** vlib's basics must not depend on fork-only features without
a fallback. Reflection replaces `VERBS_ENUM` and `Pred::id`, and annotations
replace `clang::annotate` spellings. Each has a macro fallback that works on
Clang 23 with `-std=c++2c`. If the fork proves too costly, the basics still
ship.

## 9. Verification

Per BLACKBIRD.md: choose oracles by fault class, aim for tiers 4-7, and
never trust a test by default.

### 9.1 vlib

| Fault class | Oracle | Tier |
|---|---|---|
| Wrong result range from an operation | Compile-time tables: `static_assert` of result bounds for operand range pairs, hand-derived from interval arithmetic, covering signs, zero crossings, and `int64_t` extremes | 7 (spec) |
| Wrong runtime value | Differential fuzzing (libFuzzer) against an `__int128` model. For random bounds and values: the result equals the model's result, and lies within the result type's bounds | 6 (model) |
| Same table, two execution paths | The spec tables run at runtime and under `constexpr`, as Boost.SafeNumerics does | 7 |
| API admits a forbidden operation | Concept-rejection tests: `static_assert(!requires { Bounded<0,5>{3}; })` for raw ingress, narrowing assignment, default construction, lambda predicates | 7 |
| Wrong diagnostic for a rejected program | Clang `-verify` with `expected-error` comments, which pins the exact diagnostic at the exact line. Stronger than "build fails" (sml) or untested `#ifdef`s (GSL) | 7 |
| Checked ingress accepts out-of-range input | Property tests: `make(v)` succeeds iff `Lo <= v <= Hi`, for all `int64_t` edge values and fuzzed values. `to_enum` succeeds iff the value is an enumerator | 5 |
| Narrowing check bypassed | Death tests: `+=` past a bound reaches the handler | 5 |
| Undefined behaviour | All runtime tests and fuzzers under ASan and UBSan | 2, on every run |

### 9.2 Checks

| Fault class | Oracle |
|---|---|
| Missed or spurious finding on known code | Case files with expected findings written as source comments (`// verbs: enum-candidate Door::mode {0,1,3}`), compared exactly, as IWYU's tests do. Every rule clause has a case that trips it and one that just misses it |
| Key instability | Metamorphic tests: renaming locals, reordering declarations, moving a function to another unit, or reformatting leaves the findings and keys unchanged |
| Cross-unit evidence lost | The same subject's uses split across 1, 2 and 3 units give the same finding |
| Facts file reader crashes or misreads | libFuzzer on the reader; round-trip property (write, read, compare) |

### 9.3 Precision on real code

Run `verbs scan` on blackbird and BRepGPU, and hand-review every finding.
Record each as true or false in papers/. Escape findings must be 100%
true; enum-candidate thresholds are tuned until the findings are. This is
the measured form of the zero-effective-false-positive bar, and it gates
turning the check on in Blackbird's edit hook.

### 9.4 `verbs check`

End-to-end: fixture repositories with scripted edit sequences and expected
deltas written from this spec. Two properties also hold:
- applying an edit and then its inverse gives an empty net delta;
- `verbs check` after any sequence of edits reports the same findings as a
  fresh `verbs scan` (incremental equals from-scratch).

### 9.5 Mutation testing

Mull over vlib, the checks, and `verbs check`, on the fleet, never on the
laptop. It needs Mull on the selected Clang (bead `verbs-b4x`). Surviving
mutants are triaged into missing oracles or equivalent mutants.

## 10. Layout

```
cpp/CMakeLists.txt, cpp/CMakePresets.json
cpp/include/verbs/       vlib: bounded.hpp refined.hpp id.hpp enum.hpp handler.hpp
cpp/lib/                 matchers, facts format, rules, report
cpp/tools/verbs/         the verbs binary
cpp/tests/vlib/          spec tables, concept rejections, -verify cases, fuzzers
cpp/tests/checks/        case files, metamorphic tests
cpp/tests/e2e/           fixture repositories and edit scripts
```

The placeholder `packages/cpp` header retires when vlib lands. The Rust crate
stays at the repository root until the Rust phase (bead `verbs-4ox`).

## 11. Departures from the brief

| Brief | Basics | Why |
|---|---|---|
| Delta daemon with clangd tiers | Stateless `verbs check` | Operator decision; push needs no residency (agent-feedback lane) |
| `.verbs/decisions.jsonl` | Decisions on the declaration | JSON persistence rule; in view for the agent editing the declaration; no keying or orphans |
| `[[clang::annotate("verbs:inv ...")]]` for invariants | The vlib type is the declaration | No second declaration to drift from the type |
| Widening-only `Bounded` | Widening plus checked compound assignment | Loop accumulators must type (Wuffs) |
| Bound overflow by UB in constant evaluation | Explicit `__int128` check with `static_assert` | Clear diagnostics (bounded::integer) |
| `VERBS_ENUM` permanent | Fallback until reflection | C++26 `enumerators_of` |
| Lambda ban by rule | Lambda ban by concept | Enforced by the compiler |
| SQLite cache, preservation verdicts | Per-unit facts files only | Nothing to cache in the basics |
| Visible-state class invariants | Value invariants in types; whole-value refinement | Claim-scope decisions; reentrancy (Boogie) |
| Four first-wave lints | Escape plus enum-candidate | Basics first; Lackwit's precision trap |
| C++23 | C++26 with fallbacks | Operator decision |

## 12. Open questions for the tribunal

1. Is the claim of §2 true as stated for every vlib type, given the escape
   check of §4? Find a program that violates a `holds` claim without an
   escape finding.
2. Does checked compound assignment (§3.1) break any `typecheck` claim the
   report makes?
3. Are the enum-candidate disqualifiers (§5) complete enough for zero
   effective false positives? Which C++ uses of an integer are neither
   counted nor disqualifying?
4. Can include-set tracking (§6.2) miss an affected unit, for example
   through `__has_include`, macros that change inclusion, or the compilation
   database changing?
5. Is in-source decision recording (§7) gameable in a way a separate file
   is not?
6. Is anything in the basics a disguised complex case that should be a bead?

## 13. Deferred beads named in this spec

| Topic | Bead |
|---|---|
| Two-state predicates and old values | verbs-de3.1 |
| FSM checking; trace validation | verbs-de3.2, verbs-de3.3 |
| Unwind preservation; moved-from weakening | verbs-de3.11, verbs-de3.12 |
| Edit-keyed cache; latency including header fanout | verbs-de3.13, verbs-de3.14 |
| Cross-field invariants on mutable owners | verbs-de3.17 |
| Bounded beyond int64 | verbs-de3.18 |
| Kinds with arithmetic | verbs-de3.19 |
| Decision sidecar for uneditable code | verbs-de3.20 |
| Kind discovery | verbs-de3.21 |
| Typestate; TSA authority capabilities | verbs-de3.22, verbs-de3.23 |
| bool-cluster, repeated-guard | verbs-de3.24 |
| Editor-time verbs (tidy adapter, custom clangd) | verbs-de3.25 |
| Mull on the selected Clang | verbs-b4x |
| Rust phase | verbs-4ox |
