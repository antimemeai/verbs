# verbs basics: design specification

Status: revision 2, 2026-10-17, after the first tribunal. Scope: the basics
only, per the basics-first principle (journal/2026-10-17-operator-decisions.md).
Everything outside the basics is a bead and is named here only to mark the
edge (§14).

**Inputs:**
- design/verbs-design-brief.md (orientation, not settled);
- the lane reports papers/2026-10-17-{literature-core, literature-agent-feedback,
  reference-implementations, cpp-toolchain-burdens, cpp26-clang-toolchain}.md;
- the tribunal reports papers/2026-10-17-tribunal-{soundness, checks,
  doctrine, ergonomics}.md;
- the operator's decisions in journal/.

Findings are cited by report and ID: soundness B1, checks M7, doctrine D3,
ergonomics S2.

Marked **[lane]**: text that the enum-candidate lane
(papers/2026-10-17-enum-candidate-redesign.md) replaces when it returns. The
escape-allowlist lane has returned and §4 is its rule.

---

## 1. What the basics are, and what they are for

verbs makes invariants of C++ values explicit in their types, so that the
compiler rejects violations or one checked entry point refuses them. It then
reports to an agent, at each edit, what changed about those claims. The
basics have three parts:

1. **vlib**, a header library with two families of closed value types:
   finite enums with checked ingress (§3.2), and `Bounded` integers (§3.3).
   Each carries one invariant in its representation.
2. **The escape check** (§4). It finds code that bypasses vlib, weakens a
   vlib type, or silences the warnings vlib relies on. Every claim in (1)
   rests on it.
3. **`verbs check`** (§6), a stateless command run after each edit. It prints
   what the edit added, resolved, weakened or decided.

There is also one discovery check, enum candidates (§5). It proposes and
never gates.

There is no daemon, no database and no LLM dependency. There is no
annotation syntax for invariants either: the vlib type of a declaration *is*
its invariant declaration.

**Annotations clarify; they never encumber.** Where the meaning is evident
from the code, there is no annotation. verbs asks for one only to record what
the code cannot say: a decision's rationale (§7). If a finding could only be
silenced by an annotation that states the obvious, the check is wrong. Fix the
check; don't ask for the annotation.

### 1.1 How the basics reach the kill criterion

The kill criterion: verbs must meaningfully reduce edits-to-detection for a
coding agent. The basics detect almost nothing in code that does not use vlib,
so the treatment is a **migration** (doctrine D1).

- **Corpus:** blackbird only. BRepGPU is C++17 with an `extern "C"` interface
  and a CUDA backend (doctrine D1, ergonomics B-excerpt). It cannot hold vlib
  types without raising its standard and changing its ABI. It is outside the
  basics, except as input for measuring the enum-candidate check's precision.
- **First migration:** blackbird's decoding seam.
  - `Fields::get_enum<E>()` wraps `verbs::to<E>` and throws blackbird's
    `Error{ErrorCode::corrupt}`.
  - It replaces the hand-guarded integer-to-enum casts, for example
    src/journal.cpp:278-281, src/retained_events.cpp:525-531 and :580-586.
  - `PhaseKind` replaces the raw `std::uint8_t kind` passed at 31 call sites
    (ergonomics, Adoption).
- **The migration is blackbird's work and the operator's call.**
  Blackbird's edit hook does not exist yet (doctrine Q6.6); adding it is
  blackbird work too.
- **Defect classes the basics can detect in migrated code:**
  - an ingress guard removed, or drifting from the enum definition
    (journal.cpp:278 hard-codes `{1,2,4,65535}` apart from `FrameKind`);
  - an enumerator added without a matching ingress;
  - a raw integer-to-enum cast added beside `verbs::to`;
  - a vlib type downgraded to a raw integer (§4.7);
  - writes that bypass the representation (§4.1).
- **Expected result, stated before the experiment:** a measurable effect on
  those seeded classes and on agent-introduced faults at migrated seams, and
  none on generic mutants. If the effect on seeded classes is not meaningful,
  stop and rethink (brief §10). The experiment is bead verbs-de3.30.

## 2. The claim

verbs states claims in one form:

> Every value of declaration D satisfies predicate P, under the claim boundary.

- **D** is a field, a variable with static, thread or automatic storage, or
  a function return, whose type is **vlib-containing**. A vlib-containing
  type is a vlib type, or an array, class (by member or base), or standard
  wrapper (`optional`, `pair`, `tuple`, `array`, `variant`, `expected`) of a
  vlib-containing type. This is transitive (soundness B2).
- **P** is `range(lo, hi)` for `Bounded<lo, hi>`, or `in{v1..vn}` for a
  verbs enum.

`kind`, `refined` and `const` are not in the basics vocabulary. `Id` and
`Refined` have no consumer in the corpus (ergonomics M5, doctrine D12), and
`const` has no check behind it (doctrine D16). See §14.

Each examined declaration is in exactly one state:

| State | Meaning |
|---|---|
| `holds` | D's type carries P, its translation unit meets the claim boundary, and no escape affects D's type (§4.8). |
| `finding` | An escape, a weakening or a silencing affects D, with evidence. |
| `decided` | A decision (§7) covers a finding on D. |
| `outside` | D is outside the claim boundary. The report names the rule that excludes it. |

There is no `unknown` state. Mechanism sets and runtime-check counts are not
kept, because nothing reads them (doctrine D7). The set of `holds` claims is
kept only as the baseline that detects lost claims (§4.7).

### 2.1 Claim boundary

Every claim holds only under these rules.
- `verbs scan` prints all of them with every claim listing.
- A delta prints them whenever it reports a claim change (§6.5).
- README.md carries them.
- Rules marked **(read)** are checked from the compile command; a translation
  unit that fails one has all its claims `outside`.

1. **No exception unwinds mid-mutation of user code.** vlib's own operations
   check before they store, so they give the strong guarantee (§3.1). Bead
   verbs-de3.11.
2. **No moved-from object is used.** Bead verbs-de3.12.
3. **Single owner.** An invariant belongs to one declaration and its type,
   and mutation goes only through that type's operations.
4. **One thread at a time.** Lock-scoped and lock-free cases are outside the
   claim, and memory ordering is never claimed.
5. **No call to unowned code happens while an invariant is temporarily
   broken.** vlib never leaves one broken.
6. **Single-state predicates only.**
7. **The analyzed code is the preprocessed code of exactly the units in the
   named compilation database, under their exact flags.** Code outside that
   set is `outside`, not `holds`: a unit, header configuration, module or
   command-line macro, or platform-guarded code not compiled here. The report
   names the database. A change to any unit's compile command prints as a
   silencing `!` line (§4.6).
8. **No undefined behaviour outside vlib**: no out-of-bounds or
   out-of-lifetime access, and no read of an uninitialized or moved-from
   object. verbs does not check this (soundness M1). The mechanisms that
   check it are rules 9–10, and the sanitizer runs of §10 (ASan, UBSan,
   `-fsanitize=bounds`).
9. **(read) Library hardening is at least FAST**
   (`_LIBCPP_HARDENING_MODE_FAST`), so `*` on an empty `std::optional`
   traps rather than producing an unchecked value (soundness M2, doctrine D13).
10. **(read) `-Werror=switch-enum` and `-Werror=uninitialized` are in effect**
    (soundness M3).
A vlib-containing object with static or thread storage that is not
`constinit` is an escape (§4.3 rule 12), not a boundary assumption.

## 3. vlib

vlib is header-only, compiled as C++26 (`-std=c++2c`) on the pinned Clang
(§8), in namespace `verbs`. The type rules are the specification; code
fragments show shape only.

### 3.1 Rules common to every vlib type

- **One ingress verb.** `verbs::to<T>(x)` returns `std::optional<T>`. It is
  the only runtime path from an unchecked value into a vlib type
  (ergonomics S5). Rule 9 makes `*` on an empty result trap.
- **Violations throw.** `verbs::to` never throws. The checked compound
  operations (§3.3) throw `verbs::violation`, which derives from
  `std::logic_error`, before anything is stored. The object is unchanged
  (strong guarantee).
  - In a `noexcept` function this terminates.
  - There is no user hook and no build knob, so a handler cannot return
    (doctrine D23, checks m8).
  - `verbs::violation` carries the type and predicate in its message,
    never the value.
- **No default constructor** on any vlib type. A declaration must say its
  value.
  - Consequence (ergonomics M4): `vector(n)`, `resize`, `map::operator[]` and
    value-initialized aggregates are unavailable.
  - Idioms: `try_emplace(key, value)`, construction from a full value,
    `std::optional<T>` where "unset" is a real state.
- **Deleted conversions carry their reason** (C++26 `= delete("…")`).
  Each common mistake gives one error and one note naming the right spelling,
  and `-verify` pins each message (§10.1, ergonomics M2).
- **vlib's stored members are private**, and vlib declares no friends outside
  `namespace verbs::detail`.

### 3.2 Verbs enums

A **verbs enum** is an enumeration declared with `VERBS_ENUM`. Plain
`enum class` declarations are not verbs enums, so blackbird's 109 enums and 27
guarded casts are not findings on day one (checks M3, doctrine D22).

```cpp
VERBS_ENUM(PhaseKind, std::uint8_t, VERBS_UNSET(none),
    assembly = 1, retry_group, attempt, retry_wait, adapter, decode,
    preview_feed, presentation, receipt, acceptance, colleague_prepare,
    colleague_transport, sse_event, preview_event)
```

- **Explicit values, gaps, aliases and negative values are allowed.** The
  macro emits the `enum class` verbatim and the exact value and name arrays.
  It uses a bounded FOR_EACH of up to 64 enumerators (doctrine D6, ergonomics
  M6).
- **Ingress:** `verbs::to<PhaseKind>(raw)` accepts exactly the listed
  values. `verbs::to<PhaseKind>(std::string_view)` accepts exactly the names.
- **Egress:** `std::to_underlying`, and `verbs::name(e)`.
- **The zero state is named.** Value- and zero-initialization (`E{}`,
  `Node{}`, `map::operator[]`, `vector(n)`, static storage) always produce 0,
  and no check can see every such site (soundness M4, ergonomics M7). So every
  verbs enum names its 0:
  - either 0 is a real domain value (`idle = 0`), which `verbs::to` accepts;
  - or the author writes `VERBS_UNSET(none)`, an enumerator equal to 0 that
    `verbs::to` rejects.

  `VERBS_ENUM` without a 0 enumerator is a compile error naming
  `VERBS_UNSET`. A value-initialized enum therefore always holds a named
  state, so the `in{}` claim includes `none`. `-Werror=switch-enum` makes
  every switch handle it, and wire input can never produce it. This keeps the
  domain honest: the escape-allowlist lane's alternative (require any 0
  enumerator) would make `verbs::to` accept 0 as valid input.
- **Bit-fields** of a verbs enum narrower than its value range are an escape
  (soundness M4).
- **Exhaustiveness** comes from rule 10 (`-Werror=switch-enum`).
- **Reflection** (`std::meta::enumerators_of`) will replace the macro's
  arrays when the pinned Clang has P2996. The macro's syntax does not change
  (bead verbs-de3.27).

### 3.3 `Bounded<Lo, Hi>`

An integer whose value is always in `[Lo, Hi]`.

**Bounds and storage.**
- Bounds are `std::int64_t`; wider bounds are bead verbs-de3.18.
- Storage is the smallest signed or unsigned type that holds `[Lo, Hi]`
  (ergonomics S7).
- `Lo > Hi` is a compile error.
- Every bound computation, constraint and runtime check is done in
  `__int128`. A result bound outside `int64_t` fails a named `static_assert`.
  This includes the `+=` constraint (soundness M6, ergonomics m2) and `%` and
  `/` (soundness M5: `INT64_MIN % -1`).

**Constants.** `verbs::k<V>` is a `Bounded<V, V>`. It widens to any range
containing `V`, so `Count total = verbs::k<0>;` and `i += verbs::k<1>;` work,
while `Bounded<0, 5> x = verbs::k<7>;` is a compile error that names the
constant (ergonomics S1, m4).

**Ingress.** `verbs::to<Bounded<L, H>>(x)` from any integral or any
`Bounded`. No constructor takes a raw integer.

**Widening is implicit and narrowing is never implicit.** `Bounded<A, B>`
converts to `Bounded<C, D>` exactly when `C <= A && B <= D`. Narrowing goes
through `verbs::to`, or through a checked compound operation.

**Egress is implicit.** `Bounded<Lo, Hi>` converts implicitly to any
non-`bool` integral type that holds `[Lo, Hi]` (ergonomics S3, B2).
Subscripts, stores into `uint32_t` and `switch` therefore need no cast under
`-Wconversion -Wsign-conversion`. `get()` returns the stored value and carries
`[[assume(Lo <= v && v <= Hi)]]`; `get()` is vlib's only `[[assume]]`.

**Arithmetic widens.**
- `+`, `-`, `*` and unary `-` follow interval arithmetic.
- `/` and `%` exist only when the divisor's range excludes 0, and they are
  computed in `__int128`.
- Result bounds are named constants, so diagnostics print `hi aka 10` rather
  than the expression (ergonomics M2).
- Operators are free templates.

**Checked compound assignment.**
- `x += y` and `x -= y` accept a `Bounded` or a raw integral `y`
  (ergonomics S4, M3).
- The constraint is that the intervals can overlap; for a raw `y`, its
  type's range.
- The result is computed in `__int128` and checked against `[Lo, Hi]` before
  the store. Out of range, it throws `verbs::violation` and the object is
  unchanged.
- This is the accumulator rule (core literature §7, Wuffs): plain
  `x = x + y` does not compile, and its deleted conversion names `+=` and
  `verbs::to`.

**No `++` or `--`.** Loops use `verbs::upto(n)` (ergonomics S2, B1). For `n`
of type `Bounded<L, N>` with `L >= 0`, it yields `Bounded<0, N-1>` values.
The past-the-end value lives inside the iterator, never in the loop variable.

```cpp
Count total = verbs::k<0>;
for (auto e : verbs::upto(edge_count)) {   // e : Bounded<0, MAX - 1>
    offsets[e] = total;                    // implicit egress
    total += counts[e];                    // checked: never exceeds MAX
}
```

**Mixed ranges.** `c ? a : b` and `std::max(a, b)` over different ranges
need one side widened to the common range explicitly (ergonomics m1). There
is no `common_type` specialization until the corpus asks for one.

**Consumers.** None is named in blackbird yet (doctrine D12). Enums are the
first migration. `Bounded` lands when a named blackbird declaration needs it:
candidates are the limit and count fields such as `limits_.max_causal_depth`.
If the plan finds none, `Bounded` moves to a bead.

## 4. The escape check

Every `holds` claim rests on one closed guarantee (papers/2026-10-17-escape-allowlist.md,
replacing the first draft's deny-list, which two tribunals broke):

> **The object representation of a vlib-containing object (§2) is written or
> created only by (a) vlib's own members and factories (`verbs::to`,
> `verbs::k`, vlib arithmetic), or (b) a copy or move from a valid object of
> the same type.** Every other write or creation of those bytes, and every
> loss of the static type of a pointer or reference to such an object, is an
> **escape**.

This is an allowlist, matched on Clang's AST with full type information.
Every spelling of a construct reduces to the same AST node, so the spelling
an agent chooses does not matter. For example, `T*`→`void*` is
`ImplicitCastExpr <BitCast>`, and every enum-ingress spelling is one
`CK_IntegralCast` (OperationKinds.def:61, :199; the lane's §2).

In a uninstantiated template the check cannot judge the code, so it is "not
analyzed; no claim depends on it" (checks m1). It is never a false escape and
never a false `holds`.

The vlib types in the basics are `Bounded` specializations and verbs enums
(§3.2). Recursion through vlib-containing types stops at pointers and
references.

### 4.1 Representation and type erasure

1. **Type erasure.** Converting a pointer or reference to a vlib-containing
   object to `void*`, `char*`, `unsigned char*`, `std::byte*`, or any
   unrelated pointer type, by any spelling, implicit included. This covers
   `fread`, `read`, `recv`, the destination of `memcpy`, and user `void*`
   helpers.
   **Read-only exception:** a conversion whose target pointee is `const` is a
   read. That admits hashing, printing, `fwrite` and `write`.
2. **Re-typing.** Converting `void*` or a byte pointer back to a pointer to a
   vlib-containing type. This includes `std::launder`,
   `std::start_lifetime_as`, `std::construct_at`, and placement `new` over
   storage that holds a vlib object.
3. **Bit reinterpretation.** `std::bit_cast`, `__builtin_bit_cast`, and
   `reinterpret_cast` of references, whose source or result is
   vlib-containing.
4. **Raw byte writes.** `memcpy`, `memmove`, `memset` and their builtins into
   a vlib-containing destination. The exception is a `memcpy` or `memmove`
   whose source is an object of the same type; trivially copyable relocation
   is a copy.
5. **Unions.** A user-declared union with a vlib-containing member, at any
   depth.
6. **`asm`.** An `asm` statement with a vlib-containing operand, or any
   `"memory"` clobber.

### 4.2 Enums

7. **Enum ingress.** Any integral-to-enum or floating-to-enum conversion into
   a verbs enum, outside `verbs::to`. This covers `static_cast`, C-style,
   functional and list-initialization spellings, including `Mode m{raw}`.
8. **Narrow bit-field.** A bit-field of verbs-enum type too narrow to hold
   every enumerator value.

Value- and zero-initialization need no check. The named zero state (§3.2)
makes them sound by construction.

### 4.3 Encapsulation and the build

9. **verbs specializations.** Any of the following whose spelling location is
   outside vlib's headers, except `VERBS_*` macro expansions:
   - any declaration in `namespace verbs`;
   - any explicit or partial specialization, or explicit instantiation, of a
     `verbs::` template (class, member or variable).
10. **Private-member theft.** An explicit instantiation whose template
    arguments name a private or protected vlib member. Explicit
    instantiation is exempt from access checking ([temp.spec.general]/6).
    Naming such a member anywhere else is already a compile error.
11. **Keyword macros.** A `#define` or `#undef` of `private`, `protected`,
    `public`, `class`, `struct`, `const` or `noexcept`, in source, through
    `-D`, or in an `-include` forced header. The `-D` form is read from the
    unit's recorded compile command (§6.2), not the AST.
12. **Non-`constinit` statics.** A vlib-containing object with static or
    thread storage that is not `constinit`. Static zero-initialization is
    observable before dynamic initialization (soundness M3).

### 4.4 Cross-unit mismatch

13. **What is recorded.** Per unit, for every external-linkage variable and
    function, verbs records its qualified name, canonical type, and whether
    it is vlib-containing. For every external-linkage class definition, it
    records the qualified name, the concatenated canonical field-type
    signature, and the flag.
14. **What is flagged.** The cross-unit step groups these by kind and name.
    It reports a name with two or more signatures where any one is
    vlib-containing: `extern` type confusion, or an ODR violation (soundness
    B6).

### 4.5 Scope

Scope is decided by repository path through verbs' path rule (§6.3), never by
Clang's system-header flag.
- A repository file marked `#pragma clang system_header`, or reached through
  `-isystem`, cannot hide an escape.
- libc++ and SDK internals are out of scope and never reported. Examples are
  `optional`'s union storage and `vector`'s relocation `memcpy`, which are
  judged at their typed API.

### 4.6 Silencing

verbs honours no suppression comment; only a decision (§7) silences a finding
(checks M2). These are silencing findings, printed `!`:
- **Warnings the boundary needs.** A change to the diagnostic state of a
  warning in rules 9–10, by any pragma spelling (`clang`, `GCC`, `_Pragma`).
- **Hiding files.** `#pragma clang system_header`, or a line marker, in a
  repository file.
- **Compile commands.** Any change to a unit's `-D`, `-U`, `-std`, `-W`,
  `-w`, `-isystem`, `-include` or hardening arguments. verbs records each
  unit's full argument vector and diffs it per run.
- **Assumptions.** `[[assume]]`, `__builtin_assume` or `__builtin_unreachable`
  outside vlib.
- **Scope.** A change to verbs' path rule.

### 4.7 Weakening

A declaration that had a `holds` claim in the previous report and now has
none is a **lost claim** (doctrine D2, checks M2). For example:
- its type changed to a raw integer;
- its `Bounded` range widened;
- its verbs enum gained a value.

A lost claim prints `!` even when the change is intended, so that a reader
sees it.

### 4.8 Attribution

An escape voids the claims of every declaration of the affected
vlib-containing type, program-wide. When the sink's type is erased, it voids
every claim in the unit. Finding the exact declaration needs points-to
analysis (soundness M7; bead verbs-de3.33). The coarse rule never yields a
false `holds`; it costs only precision, and escapes are rare.

### 4.9 Evidence

The lane's prototype is a 689-line LibTooling tool, preserved in
context/prototypes/escape-lane/. Results:
- **Bypasses caught:** every first-tribunal bypass that belongs to the escape
  check, including fread, launder, all five enum list-init spellings,
  specializations, private-member theft, keyword macros, asm, union and
  bit-cast nesting, and cross-unit mismatch.
- **False positives:** zero, on seven legitimate programs that compile and
  run, covering `optional`, `vector` with `sort`, `map`, byte hashing through
  a `const` view, serialization through `verbs::to` and `fwrite`, and
  `constinit` statics.
- **Routed elsewhere:** the remaining counterexamples (self-initialization,
  unchecked `*`, arithmetic edge cases) go to vlib rules and the boundary.

The prototype is evidence for the rule, not the implementation. The
implementation is written red-first against §10.2.

## 5. Enum candidates **[lane]**

> **[lane] enum-candidate redesign.** The lane's precise rule, its measured
> precision and recall, and its output recommendation replace this section.

Settled regardless of the lane's numbers:
- **It proposes and never gates.** A candidate is not a correctness
  finding, so it never sets a non-zero exit (doctrine D5).
- **At most one candidate per delta,** labelled `proposal`.
- **Observed values are a lower bound on the domain.** A finding says
  "values observed include …", gives the explicit values it saw, and asks
  for the domain and the names. It never proposes `verbs::to` over the
  observed set (checks B2, ergonomics M8).
- **Subjects** are fields, globals and function returns, not parameters or
  locals (doctrine D21).
- **Recognized evidence:** literal-initialized `constexpr` constants and
  existing enumerators count as literals (doctrine D4). Writing a value out
  (egress) does not disqualify; only reading it back in is ingress
  (ergonomics M8).
- **Disappearance prints `!`.** A candidate that disappears because a
  disqualifying use appeared prints `!`, not `-` (doctrine D4).
- **Excluded or `outside`:** subjects in `extern "C"` types, in translation
  units below C++26, or in code the path rule excludes are `outside`.
  `volatile`, atomic and `sig_atomic_t` subjects are excluded (checks M5).
- **Test code supplies no evidence.**

## 6. `verbs check`

### 6.1 Interface

```
verbs scan  -p <build-dir> [--hypotheses]      # full analysis; lists claims with the boundary
verbs check -p <build-dir> [--changed <path>...]
```

`--changed` is a hint for scheduling, never the authority on what changed
(checks B1).

The caller appends stdout verbatim to the edit's tool result and acts only on
the exit status (doctrine D18). The output text is not a versioned contract.

| Exit | Meaning | Expected caller behaviour |
|---|---|---|
| 0 | Nothing new that gates | continue |
| 1 | A new escape, silencing or lost claim | the agent addresses it |
| 3 | A decision was added or changed | Blackbird reverts the edit unless the operator approves (doctrine D3) |
| 2 | No check ran; the reason is printed | the agent must not read silence as a pass (doctrine D25) |

Proposals never affect exit status. The `--hypotheses` listing exists for the
precision calibration of §10.3; that is its only consumer (doctrine D27).

### 6.2 Verifying traces: what decides that a unit is re-checked

Each run decides for itself which units changed. For each unit, verbs records
a **trace** (core literature §9; checks B1, M7). The trace holds:
- the hash of the unit's compile command;
- every input file Clang read: SourceManager file entries, `#embed`
  resources, and the PCH's input-file list, each with size, mtime and content
  hash;
- every negative probe: include-path lookups that missed, and
  `__has_include` results.

On every run:
1. **Compilation database.** Diff it per entry by command hash. Drop facts
   for removed entries. For a changed source that is not in the database,
   print `! outside: not in compilation database`.
2. **Traces.** Stat every recorded input. Hash it only when its size or mtime
   moved. On blackbird, 257 units touch 1,641 files, which takes
   milliseconds. A unit whose trace mismatches, or whose negative probe now
   finds a file, is stale.
3. **Re-extract** every stale unit. `--changed` only orders the work.
4. **Cross-unit evaluation:** declaration and definition mismatches (§4.4),
   and enum candidates (§5).
5. **Delta** against the previous report (§6.5).

Other cases:
- **PCH:** the prefix header is parsed with `-include` and the PCH flags are
  stripped.
- **Modules:** a unit that imports a module is `outside` (bead
  verbs-de3.31).
- **Compile errors:** a unit that fails to compile keeps its previous facts.
  It is listed `not refreshed (compile errors)`, and evidence that depends on
  it prints no `-` lines (checks M10).
- **Unincluded headers:** a header in `--changed` that no unit includes prints
  `! unanalyzed: no unit includes <path>` (checks m3).
- **Paths** are canonicalized with `realpath` on both sides (checks m4).

### 6.3 Files, locking, path rule

- **Location:** traces, facts and the report live in `<build-dir>/verbs/`.
  They are owned binary formats, versioned; a mismatch deletes and rebuilds.
- **Writes:** every file is written to a temporary name and renamed into
  place. Any read failure deletes and rebuilds (doctrine D28).
- **Locking:** one exclusive lock covers `<build-dir>/verbs/`. Concurrent
  `verbs check` processes wait for it (checks M10).
- **Path rule:** the repository declares which paths are generated, vendored
  or otherwise outside, in a small owned text file at the repository root
  (format in the plan; not JSON). Changing it is a silencing finding (checks
  m5).

### 6.4 Keys

Keys never contain line numbers or byte offsets (checks M8).

| Entity | Key |
|---|---|
| External linkage | USR |
| Internal linkage, including anonymous namespaces | repository-relative path plus qualified name |
| Lambdas and unnamed types | enclosing key plus ordinal among siblings of that kind |
| Escape | enclosing function's key, construct class, ordinal within the function |

Renaming a subject retires its old key; that is correct, because the subject
changed. Functions defined in headers are counted once by identity, not once
per unit (checks m7).

### 6.5 Output

```
verbs · 3 units re-checked · 1.8 s · build/debug
+ escape  PhaseKind value-initialized; 0 is not a value   src/token_usage.cpp:337
    std::map::operator[] creates Node{} with kind == 0
    fix: try_emplace(key, Node{...}) with an explicit kind
! lost claim  Header::version  Bounded<1,5> -> std::uint8_t   include/x/header.hpp:12
! decision added  Packet::kind  open_domain "producers own the domain"   src/packet.hpp:14
~ proposal  Resource::ending_ (std::uint8_t): values observed include 0x00, 0x01, 0x02
    this looks like a closed domain; if it is, declare it with VERBS_ENUM and give the full domain and names
claims assume: no unwind mid-mutation · no moved-from use · single owner · one thread ·
  no call-out while broken · single-state · analyzed code is this database's units ·
  no UB outside vlib · hardening ≥ FAST · switch-enum and uninitialized are errors
```

| Prefix | Meaning |
|---|---|
| `+` | new finding |
| `-` | resolved finding |
| `~` | changed evidence under an unchanged key, or a proposal |
| `!` | lost claim, decision change, silencing, or something not analyzed |

Rules:
- **Order:** escapes, then lost claims, then silencing, then decisions, then
  one proposal.
- **Caps:** at most N findings per file and M in total. Withheld findings stay
  marked *unshown* and carry into the next delta until printed (checks M9).
- **The boundary line** is printed whenever the delta reports a claim
  change. A delta of proposals alone omits it.
- Each finding gives its evidence and one concrete fix. A fix never invents
  enumerator names or values.

### 6.6 Latency

- **Budget:** p95 of at most 10 s per edit on the operator's machine at
  normal load.
- **Cost model**, measured on blackbird (checks M11): about 3.1 CPU-s per
  unit. A `.cpp` edit costs one unit. A header edit costs its fanout:
  `foundation.hpp` reaches 243 of 257 units, and the touch-weighted mean
  fanout is 72.5 units, about 14 s on 16 idle cores.
- **Over budget:** verbs prints the delta for the units finished within
  budget, plus `~ N units pending (claims for them not refreshed)`. Pending
  units stay stale and finish on the next run. Nothing pending is reported
  as resolved.
- **Gate:** enabling the check in Blackbird's hook is gated on this budget,
  measured on blackbird (bead verbs-de3.14), alongside the precision gate
  (§10.3).

## 7. Decisions

A decision records a verdict the code cannot express. The basics have one
verdict:

```cpp
VERBS_OPEN_DOMAIN("producers own the domain; see provider_original.cpp:443")
std::uint8_t kind = 0;
```

It means that this subject is deliberately not a closed domain, for the
stated reason.

**Placement (operator decision, 2026-10-17).** The decision goes on the
declaration it concerns. Nearly every reader will be an LLM agent, and an
agent about to change a declaration reads the file that holds it. A decision
there is in view when it matters; a sidecar helps only an agent that already
knows to look.

**Spelling.** The macro expands to `[[clang::annotate("verbs:open_domain",
why)]]`. It switches to a C++26 annotation when the pinned Clang supports
P3394.

**What was cut, and why:**
- **The `seen(...)` list** repeated in source what verbs computes, and made
  "append the new value" the cheapest way to silence a resurfacing
  (ergonomics M9).
- **`accepted_pending`** is planned work, which belongs in bd (doctrine
  D15).
- **`rejected`**: an obvious rejection signals a check defect. A non-obvious
  one is an `open_domain` with a reason.

**Gate.** Adding or changing a decision gives exit 3 (§6.1). Detecting the
edit is not enough; the gate must prevent it. Blackbird reverts the edit
unless the operator approves (doctrine D3). Commit authorship does not
identify the author: every commit here is authored by the operator.

**Lifecycle.** A decided subject is reported `decided`. A change to or
removal of the decision prints `!`. Nothing else resurfaces it.

**Not covered:** code the team cannot edit, such as vendored or generated
code. That is the path rule's `outside`; a decision sidecar is bead
verbs-de3.20.

## 8. Toolchain

**Pin: Homebrew LLVM 23.1.2, compiled with `-std=c++2c`.** This meets the
operator's C++26 decision with every C++26 feature upstream Clang has. It is
the compiler blackbird already uses, so blackbird's move to C++26 is a flag
change, not a compiler change.

**What upstream Clang lacks:**
- **Reflection (P2996).** The Bloomberg clang-p2996 fork has it. It was
  built and probed (papers/2026-10-17-cpp26-clang-toolchain.md). But it is
  based on LLVM 21, experimental (85 open issues, crashes), and has no
  contracts. It stays in `context/toolchain-cpp26/` for experiments; nothing
  in the basics depends on it.
- **Contracts (P2900).** The operator ranks contracts above reflection for
  verbs' purpose. Contracts are the standard vocabulary for function-boundary
  obligations, which vlib types can discharge. Two beads cover this:
  evaluating the contracts branch, and that next phase (verbs-de3.26).
  Contracts never carry vlib's own representation invariants, because a build
  may select the `ignore` semantic (§3.1).

**Rules for the pin:**
1. One Clang builds vlib, its tests, the verbs tools, and the blackbird code
   verbs analyzes.
2. The tools link that Clang's libraries with matching settings:
   `-fvisibility-inlines-hidden`, RTTI on, no exceptions across LLVM frames,
   C enabled in CMake, and the resource directory baked in
   (cpp-toolchain-burdens §5–7).
3. CMake presets set `CMAKE_OSX_SYSROOT` from `xcrun --show-sdk-path`.
4. `llvm` stays pinned in Homebrew. Any toolchain change rebuilds every verbs
   binary.
5. Mull 0.34.2 supports macOS LLVM 16–21, so mutation runs need it ported to
   23 or a fleet profile (bead verbs-b4x).

## 9. Layout

```
cpp/CMakeLists.txt, cpp/CMakePresets.json
cpp/include/verbs/       vlib: enum.hpp bounded.hpp to.hpp violation.hpp
cpp/lib/                 matchers, traces, facts, rules, report, delta
cpp/tools/verbs/         the verbs binary
cpp/tests/vlib/          enumeration oracles, concept rejections, -verify cases, fuzzers
cpp/tests/checks/        case files, metamorphic tests
cpp/tests/e2e/           fixture repositories and edit generators
```

The placeholder `packages/cpp` header retires when vlib lands. The Rust crate
stays at the repository root until the Rust phase (verbs-4ox).

## 10. Verification

Oracles are chosen by fault class and must be independent of the code they
check (doctrine Q3). Expected results are written from this spec before the
code exists (red first; doctrine D26).

### 10.1 vlib

| Fault class | Oracle |
|---|---|
| Wrong result range | **Enumeration model.** For every pair of intervals inside [-4, 4] (45 per operand, about 2,000 pairs per operation), enumerate all operand values and compute the true result interval. It must equal the result type's bounds. Independent of the implementation's interval formulas (doctrine D11a). Hand-written rows cover `int64_t` extremes, including `INT64_MIN % -1`, `INT64_MAX` accumulators, and the `+=` constraint at the limits. |
| Wrong runtime value | Differential fuzzing (libFuzzer) against an `__int128` model, over a **named pre-instantiated grid** of bound pairs; the fuzzer varies the values (doctrine D11b). |
| Forbidden operation accepted | Concept-form rejection tests: `template<class B> concept raw_ok = requires { B{3}; }; static_assert(!raw_ok<Bounded<0,5>>);`. They cover raw ingress, narrowing, default construction, `++`, and `k<V>` out of range (doctrine D11d). |
| Wrong diagnostic | `-verify` only where the message is the product: each `= delete("…")` reason (doctrine D20). |
| Wrong enum domain | `verbs::to<E>` tested against literal expected sets written in the test: gaps, aliases, negative values, with and without 0, and names. Never derived from the macro's own arrays (doctrine D11c). |
| Checked operation fails open | `+=` and `-=` past each bound, including `INT64_MAX` accumulators, throw and leave the object unchanged. |
| Wrong ingress | Property tests for `verbs::to` over edge values of every integral source type: signed and unsigned, narrower and wider, `uint64_t` above `INT64_MAX`, and `bool` and character types, which are rejected at compile time (soundness m5). |
| Undefined behaviour | Every runtime test and fuzzer runs under ASan and UBSan. |
| Compile-time logic wrong | A dozen scripted source mutants of vlib's headers, each killed by the suites above, for example a flipped `requires`, swapped min and max, or a storage off-by-one. Mull covers runtime paths only (doctrine D10). |

### 10.2 Checks and pipeline

| Fault class | Oracle |
|---|---|
| Missed or spurious escape | One case file per §4 rule clause, with expected findings in source comments, compared exactly (the IWYU style). Each clause has a case that trips it and one that just misses it. Every tribunal counterexample is a case. |
| Escape the rule does not know | **Audit build** (checks M3). vlib's `get()` checks its invariant at runtime instead of assuming it. Migrated blackbird's test suite runs under ASan and UBSan. Any runtime violation without an escape finding is a missed escape. This is an independent oracle on a different fault class. |
| Key instability | Metamorphic tests: reordering declarations, moving a function between units, and reformatting leave findings and keys unchanged. |
| Incremental differs from scratch | After every generated sequence of changes, `verbs check` equals a fresh `verbs scan`. The generator includes out-of-band writes, created and deleted files, database changes, generated headers, and non-compiling intermediate states (checks M10). |
| Wrong delta | Delta tested as a pure function over report pairs: applying `delta(a, b)` to `a` gives `b`, and unshown findings persist until shown (doctrine D19). |
| Corrupt facts | libFuzzer on every reader; a write-then-read round trip; a torn write leads to rebuild. |

### 10.3 Precision on real code

- **Escapes** are measured on a branch of blackbird with the migration
  applied, plus seeded escapes (doctrine D9, checks M3).
- **"True"** means the operator would accept the edit the finding asks for.
- **The reviewer** is the operator, or an agent with no access to the
  check's source. Jev gives an independent second label. Disagreements are
  re-read and their resolution recorded. Every count includes n.
- **Rules are tuned on one corpus and reported on another** (checks M6).
- **Enum-candidate precision** comes from its lane (§5).
- **Gate:** the hook is enabled only when escapes are 100% true on the seeded
  migration and the latency budget holds (§6.6).

### 10.4 Mutation testing

Runs on the fleet, never on the laptop. Mull covers runtime paths once it
supports the pinned Clang (verbs-b4x). Source mutants cover compile-time logic
(§10.1).

## 11. Departures from the brief

| Brief | Basics | Why |
|---|---|---|
| Delta daemon with clangd tiers | Stateless `verbs check` with verifying traces | Operator; push needs no residency; traces make it correct |
| `.verbs/decisions.jsonl` | `VERBS_OPEN_DOMAIN("why")` on the declaration, gated | JSON rule; in view for the agent; gate prevents rather than detects |
| Annotations declare invariants | The vlib type is the declaration | No second declaration to drift |
| `Bounded` widening only | Widening, checked `+=`/`-=`, `k`, `upto`, implicit egress | Loops and indices must read naturally |
| UB in constant evaluation for bound overflow | `__int128` everywhere, with `static_assert` | Clear diagnostics; `%` and `+=` edge cases |
| `VERBS_ENUM` positional | `name = value`, zero rule, reflection later | Wire domains |
| `Refined`, `Id`, typestate, capabilities | Deferred (beads) | No corpus consumer; blackbird's `Id` is stronger |
| Deny-list of escape constructs | Allowlist by AST meaning | Soundness tribunal |
| Lint suppression honoured | No suppression comment honoured | Decisions are the only silencer |
| SQLite cache, preservation verdicts | Per-unit traces and facts | Nothing else to cache |
| Visible-state class invariants | Value invariants in types | Reentrancy; claim-scope decisions |
| Four lints | Escape check plus one advisory proposal | Basics first; precision |
| C++23 | C++26 (`-std=c++2c`) on the pinned Clang | Operator decision |

## 12. Open questions for the second tribunal

1. Is the allowlist (§4) complete? Find a write to vlib bytes, or a creation
   of a vlib value, that none of rules 1-14 matches and the boundary does not
   exclude.
2. Do verifying traces (§6.2) make incremental equal from-scratch under the
   generator's out-of-band changes?
3. Is exit 3 (decision gate) enforceable in Blackbird without blocking
   legitimate work?
4. Is the over-budget behaviour (§6.6) honest, or can pending units hide an
   escape indefinitely?
5. Does anything left in the basics lack a named consumer?

## 13. Increments

The plan sequences these; listed here so the spec states what "done" means.

1. **E: enums.** `VERBS_ENUM` and `verbs::to<E>`. The escape rules that
   concern enums. `verbs check` with traces, keys, delta and exit codes. The
   §10 oracles for all of these. Lands with blackbird's decoding-seam
   migration (§1.1).
2. **B: `Bounded`**, once a blackbird declaration is named (§3.3). Otherwise
   it moves to a bead.
3. **P: enum-candidate proposals**, if the lane's precision justifies them.

## 14. Deferred beads named in this spec

| Topic | Bead |
|---|---|
| Two-state predicates and old values | verbs-de3.1 |
| FSM checking; trace validation | verbs-de3.2, verbs-de3.3 |
| Unwind preservation; moved-from weakening | verbs-de3.11, verbs-de3.12 |
| Edit-keyed cache; latency including header fanout | verbs-de3.13, verbs-de3.14 |
| Cross-field invariants on mutable owners | verbs-de3.17 |
| Bounded beyond int64 | verbs-de3.18 |
| Kinds and strong types (Id), recognizing existing ones | verbs-de3.19 |
| Decision sidecar for uneditable code | verbs-de3.20 |
| Kind discovery | verbs-de3.21 |
| Typestate; TSA authority capabilities | verbs-de3.22, verbs-de3.23 |
| bool-cluster, repeated-guard | verbs-de3.24 |
| Editor-time verbs | verbs-de3.25 |
| Contracts as the obligation vocabulary; contracts-branch evaluation | verbs-de3.26 |
| Reflection replaces VERBS_ENUM arrays | verbs-de3.27 |
| Refined over deep value types | verbs-de3.28 |
| Pointer-equality string comparison check | verbs-de3.29 |
| Kill-criterion experiment | verbs-de3.30 |
| C++ modules in analyzed units | verbs-de3.31 |
| Facts shared across worktrees (constructive traces) | verbs-de3.32 |
| Points-to narrowing of escape attribution | verbs-de3.33 |
| Mull on the pinned Clang | verbs-b4x |
| Rust phase | verbs-4ox |
