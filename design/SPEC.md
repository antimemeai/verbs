# verbs basics: design specification

Status: revision 4, 2026-10-18. It follows the first tribunal, the Jev
coverage audit, two rounds each of ChatGPT and MiMo review
(papers/2026-10-1[78]-review-*.md), and the enum-candidate lane, whose
evidence removed discovery and decisions from the basics (§5, §7).
Deterministic corpus runs replace the agent experiment (§1.1).
Scope: the basics
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

No section is waiting on a lane. §4.1, §4.5 and §4.8 come from the
escape-v2 lane (papers/2026-10-17-escape-allowlist-v2.md), written after
ChatGPT F02–F06 and F12 broke v1.

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
   what the edit added, resolved or weakened.

The basics have no discovery check and no decisions (§5, §7).

There is no daemon, no database and no LLM dependency. There is no
annotation syntax either: the vlib type of a declaration *is* its invariant
declaration, and every finding is fixed in code.

**Annotations clarify; they never encumber.** Where the meaning is evident
from the code, there is no annotation. If a finding could only be silenced by
an annotation that states the obvious, the check is wrong. Fix the check;
don't ask for the annotation.

### 1.1 How we know the basics work

verbs is deterministic: the same code always gives the same findings. It is
tested the way a compiler is tested, with no rates and no thresholds. A
seeded fault that verbs misses is a bug, and so is a finding on correct
code. Each one is fixed before the next increment. The basics find almost
nothing in code that does not use vlib, so every test runs on **migrated**
code (doctrine D1).

- **First migration:** blackbird's enum ingress, seam by seam. The seams
  differ (ChatGPT review F15), so there is no universal helper:
  - token_usage.cpp has its own anonymous-namespace `Fields` reader (lines
    25–59);
  - journal.cpp decodes with free byte-reading functions, and an unknown
    frame kind is `ErrorCode::unsupported` (:278-281);
  - retained_events.cpp has a separate `Decoder`, and an unknown kind is
    `ErrorCode::corrupt`.

  At each seam, `verbs::to<E>` replaces the membership test on the
  already-decoded integer. The seam keeps its byte width and its error
  code. A guard narrower than the enum stays as code after `verbs::to`: for
  example, retained_events.cpp:548 admits only `{2,3,4,14}` of
  `RetainedKind`, but `verbs::to` admits `retry = 7`. Such a guard can also
  become its own verbs enum. `PhaseKind` replaces the raw `std::uint8_t
  kind` passed at 31 call sites (ergonomics, Adoption).
- **The migration is blackbird's work and the operator's call.**
  Blackbird's edit hook does not exist yet (doctrine Q6.6); adding it is
  blackbird work too.
- **Defect classes, split by mechanism** (MiMo F8):
  - *Removed by construction.* After the migration there is no separate
    ingress to drift, because `verbs::to` follows the enum:
    - an ingress guard drifting from the enum (journal.cpp:278 hard-codes
      `{1,2,4,65535}` apart from `FrameKind`);
    - an enumerator added without a matching ingress.
  - *Prevented* by the compiler at the edit that would introduce it:
    - an unhandled new enumerator in a `switch` (rule 10).
  - *Detected* by `verbs check`:
    - a raw integer-to-enum cast beside `verbs::to` (§4.2);
    - a vlib type downgraded to a raw integer (§4.7);
    - writes that bypass the representation (§4.1).

**Corpus.** Blackbird, plus open-source C++ at scale. Any project qualifies
that builds with the pinned Clang at `-std=c++2c` and has a compile database.
A corpus script migrates each scoped enum that has a fixed underlying type
and already names 0 to `VERBS_ENUM`, and it skips and counts the rest. The
plan names the projects. BRepGPU is C++17 behind an `extern "C"` interface,
so it cannot hold vlib types and is not in the corpus.

**What each corpus run checks.** The seeding script records every site it
seeds, so it is the oracle, independent of verbs:
1. **Removed by construction.** After each seeded enum change (an added,
   removed or renumbered enumerator), `verbs::to` accepts exactly the
   expected set, which the seeder writes down independently of the macro.
   Accepting a new value is the correct result here, not a missed fault
   (ChatGPT R3-09).
2. **Prevention.** Each seeded fault of a prevented class fails the build at
   the seeded line.
3. **Detection.** `verbs check` reports each seeded fault of a detected class
   at the seeded line.
4. **No false findings.** Every finding on the migrated, unseeded code is
   read by the operator, or by an agent with no access to the check's source.
   A finding is true when the operator would accept the edit it asks for.
   Escapes already present in the project are expected, and they are true.
5. **What verbs adds.** For each seeded fault, the run records whether the
   compiler and the project's own tests catch it without verbs. If verbs
   catches no fault that they miss, it adds nothing, and we stop and rethink
   (brief §10).

An earlier draft measured an agent with and without verbs, and then needed
medians, censoring and a pass threshold. All of its variance came from the
agent, not from verbs. Whether verbs catches a fault at the edit that
introduces it is a property of the check, so the corpus runs test it
directly, and no agent runs in the loop.

## 2. The claim

verbs states claims in one form:

> Every value of declaration D satisfies predicate P, under the claim boundary.

- **D** is a field, a variable with static, thread or automatic storage, or
  a function return, whose type is a vlib type, or an array or standard
  wrapper (`optional`, `array`, `expected`) of one.
- **P** is `range(lo, hi)` for `Bounded<lo, hi>`, or `in{v1..vn}` for a
  verbs enum. It applies to every contained value: every element, and the
  engaged value when there is one.
- **Classes** are not subjects. A class's vlib members are, so for
  `struct Pair { Bounded<0,5> n; E mode; }` the claims are on `Pair::n` and
  `Pair::mode` (ChatGPT F19).

**Vlib-containing** is the wider notion that the escape check uses. A
vlib-containing type is a vlib type, or an array, class (by member or base),
or standard wrapper (`optional`, `pair`, `tuple`, `array`, `variant`,
`expected`) of a vlib-containing type. It is transitive (soundness B2).

`kind`, `refined` and `const` are not in the basics vocabulary. `Id` and
`Refined` have no consumer in the corpus (ergonomics M5, doctrine D12), and
`const` has no check behind it (doctrine D16). See §14.

Each examined declaration is in exactly one state:

| State | Meaning |
|---|---|
| `holds` | D's type carries P, its translation unit meets the claim boundary, and no escape affects D's type (§4.8). |
| `finding` | An escape or a silencing affects D, with evidence. |
| `outside` | D is outside the claim boundary. The report names the rule that excludes it. |

There is no `decided` state. Every escape is fixable in code, so it is
fixed; nothing waives it (MiMo F7).

There is no `unknown` state either. A claim that depends on code that could
not be analyzed is not reported at all while the report is suspended
(§6.2). Mechanism sets and runtime-check counts are not kept, because nothing
reads them (doctrine D7).

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
3. **Single owner.** An invariant belongs to one declaration and its type.
   The owner keeps no second writable view of the object's storage. That
   includes a byte array or allocator buffer that also backs it (escape-v2
   §5). That mutation goes only through the type's operations is not
   assumed; the escape check establishes it (ChatGPT F01).
4. **One thread at a time.** Lock-scoped and lock-free cases are outside the
   claim, and memory ordering is never claimed. This deliberately narrows
   the operator's concurrency principle, which admits claims under a lock
   that TSA sees. The lock-scoped case is deferred until the basics hold
   (MiMo F11).
5. **No call to unowned code happens while an invariant is temporarily
   broken.** vlib never leaves one broken.
6. **Single-state predicates only.**
7. **The analyzed code is the preprocessed code of exactly the units in the
   named compilation database, under their exact flags.** Code outside that
   set is `outside`, not `holds`: a unit, header configuration, module or
   command-line macro, or platform-guarded code not compiled here. The report
   names the database. A change to any unit's compile command prints as a
   silencing `!` line (§4.6).
   - Code linked into the program from outside the database is assumed to
     touch vlib-containing objects only through functions that the analyzed
     code declares. No erased pointer reaches it, because every erasure
     is an escape (§4.1).
   - §4.4 checks those functions: a type that reaches one defined in no
     analyzed unit is `outside`.
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
Static zero-initialization before dynamic initialization is handled by an
escape rule (§4.3 rule 12), not by a boundary assumption.

## 3. vlib

vlib is header-only, compiled as C++26 (`-std=c++2c`) on the pinned Clang
(§8), in namespace `verbs`. The type rules are the specification; code
fragments show shape only.

### 3.1 Rules common to every vlib type

- **One ingress verb.** `verbs::to<T>(x)` returns `std::optional<T>`. It is
  the only runtime path from an unchecked value into a vlib type
  (ergonomics S5). Rule 9 makes `*` on an empty result trap.
- **Checked operations throw; ingress does not.** `verbs::to` never throws.
  The checked compound operations (§3.3) throw `verbs::violation`, which derives from
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

**Ingress.** `verbs::to<Bounded<L, H>>(x)` from any `Bounded`, or from
exactly the types `std::in_range` accepts: the standard and extended signed
and unsigned integer types. That set includes `signed char` and `unsigned
char`, and so `std::uint8_t`, which the decoding seams read. It excludes
`bool`, `char`, `wchar_t` and `char8_t`/`char16_t`/`char32_t`, which are
rejected at compile time. Verbs-enum ingress takes the same set (ChatGPT
F21). No constructor takes a raw integer.

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
  `x = x + y` does not compile. The deleted narrowing conversion has one
  message for every context (assignment, initialization, `return`), naming
  both `verbs::to<B>(x)` and `+=`/`-=` on an accumulator (ergonomics m4).

**No `++` or `--`.** Loops use `verbs::upto(n)` (ergonomics S2, B1). For `n`
of type `Bounded<L, N>` with `L >= 0` and `N >= 1`, it yields `Bounded<0, N-1>`
values. The past-the-end value lives inside the iterator, never in the loop
variable. `N == 0` means the loop can never run; `upto` rejects it with a
deleted overload that says so, rather than needing `Bounded<0, -1>`
(ChatGPT F17).

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

Every `holds` claim rests on one closed guarantee
(papers/2026-10-17-escape-allowlist.md and -v2.md). It replaces the first
draft's deny-list, which two tribunals broke, and v1's construct list, which
two external reviewers broke:

> **The object representation of a vlib-containing object (§2) is written or
> created only by (a) vlib's own members and factories (`verbs::to`,
> `verbs::k`, vlib arithmetic), or (b) a typed copy or move (construction or
> assignment) from a valid object of the same type.** Every other write or creation of those bytes, and every
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
(§3.2).

### 4.1 Representation: provenance as type

Two transitive notions (papers/2026-10-17-escape-allowlist-v2.md):
- **vlib-containing** (§2): the object representation holds vlib bytes.
  Recursion stops at pointers.
- **vlib-reachable class:** a vlib-containing class, or a base of one
  anywhere in the analyzed program. A `Base*` can point into a `Derived`
  that holds vlib bytes. Derived classes may be defined in other units, so
  the set is final only in the cross-unit step (MiMo R2-01).
- **vlib-pointer (vpr):** a pointer, reference or pointer-to-member whose
  pointee is one of these:
  - a vlib-containing type;
  - a vlib-reachable class;
  - itself a vpr (so `E**` is a vpr, MiMo R2-04).

  A class or wrapper that holds a vpr is also a vpr (`span<E>`,
  `shared_ptr<E>`, `initializer_list<E>`). Recursion does not stop at
  pointers.

Reading a value out (`get()`, implicit egress, `std::to_underlying`) never
converts a vpr, so it is never touched.

1. **Provenance.** A vpr may be converted only to these:
   - the same type;
   - its cv-added form;
   - a class in the same hierarchy (`static_cast` or `dynamic_cast`; a wrong
     downcast is UB, rule 8). The result is still a vpr, because its class
     is vlib-reachable, so a later erasure of the `Base*` is an escape.
     Each unit records its erasures of class pointers, and the cross-unit
     step re-judges them against the final vlib-reachable set.

   Every other conversion out of a vpr is an escape, implicit included:
   - to `void*` or a byte pointer (this covers `fread`, `recv` and `scanf`
     destinations);
   - to an integer;
   - to a pointer to a different vlib type;
   - by `bit_cast`, reference or member-pointer reinterpretation;
   - into a type-erased wrapper (`shared_ptr<void>`), or by
     `dynamic_cast<void*>`.

   So is every conversion *into* a vpr from anything else (re-typing):
   - `void*` or bytes to `E*`;
   - placement `new` or `construct_at` over erased storage.

   `std::launder` returns its argument's type, so it loses nothing. The
   cast it is paired with is the escape.

   **No exceptions, const included.** An earlier revision exempted an
   erased const pointer passed straight to a read-only library function.
   Every round broke that exemption: `const_cast` (ChatGPT F02, MiMo F2), a
   returned reference (MiMo R2-03), `strtol`'s `endptr` handing the alias
   back (ChatGPT R3-01). It also contradicted its own example, since `os <<
   &e` returns `ostream&` (R3-08). A signature cannot show what a function
   does with the alias, so the exemption is gone. `fwrite(&e, …)`,
   `memcmp`, raw-byte hashing and `os << &e` are escapes. The fix in code
   writes, compares or hashes `std::to_underlying(e)`, or `verbs::name(e)`.
2. **Library functions that change a pointer's type.** libc++ internals
   are not scanned (§4.5), so a library function that takes a vpr and
   returns or writes a differently typed alias performs the conversion
   where rule 1 cannot see it (ChatGPT F03). Each call to such a function
   is judged at the call site as the conversion it performs, by rule 1's
   hierarchy rules: `static_pointer_cast` to a base is fine, and
   `dynamic_pointer_cast<void>` is an escape (ChatGPT R3-04). Known
   members:
   - `as_bytes`, `as_writable_bytes`, `bit_cast`, `start_lifetime_as`,
     `start_lifetime_as_array`;
   - `static_pointer_cast`, `dynamic_pointer_cast`, `const_pointer_cast`,
     `reinterpret_pointer_cast`;
   - `__builtin_assume_aligned`, and the writing atomic builtins.

   **The list is derived, not argued.** An earlier revision claimed the list
   was closed by the standard's text, and `dynamic_pointer_cast<void>`
   refuted that. A script reads the pinned libc++'s declarations and lists
   every public function whose pointer-like output can have a different
   pointee type from its pointer-like input. The table it produces is
   reviewed and committed. A test re-derives it on every toolchain change
   and fails on any difference (§8 rule 4). The derivation lives in
   context/prototypes/libcxx-alias-scan/ until the plan adopts it.
3. **Bit reinterpretation.** `__builtin_bit_cast` whose source or result is
   vlib-containing or a vpr.
4. **Raw byte writes and copies.** `memcpy`, `memmove`, `memset` and their
   builtins, matched by exact name or builtin ID, never by substring. A call
   is an escape when its destination or its source is vlib-containing
   storage or a vpr object. Copying an `E*` into a `void*` slot is an escape
   (MiMo R2-04). The arguments' implicit `void*` conversions are judged
   here, once, not again by rule 1.

   **No exceptions.** An earlier revision exempted a same-type copy whose
   length was a multiple of the type's size. It was broken three ways:
   - `memcpy` returns the erased destination (ChatGPT R3-02);
   - a multiple of `sizeof(E)` from `&s.head` spans sibling fields of other
     types (R3-03);
   - `sizeof(Base)` copies a derived member stored in the base's tail
     padding (R3-03).

   Whole-object copies are fixed in code by assignment, and `memset` to an
   in-domain value is fixed by assigning that value.
5. **Unions.** A user-declared union with a vlib-containing or vpr member,
   at any depth.
6. **`asm`.** An `asm` statement with a vlib-containing or vpr operand, or
   any `"memory"` clobber.

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
   outside vlib's headers, except expansions of macros whose *definition*
   is in vlib's headers. A macro name grants nothing: a user-defined
   `VERBS_FORGE` is user code (ChatGPT F05). Defining or undefining a
   macro that vlib defines is also an escape.
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
12. **Dynamically initialized statics with an invalid zero.** Static
    zero-initialization is observable before dynamic initialization
    (soundness M3). The escape is a vlib-containing object with static or
    thread storage when both hold:
    - Clang does not find it constant-initialized;
    - some contained vlib type has an all-zero representation outside its
      domain: a `Bounded` whose range excludes 0.

    Verbs enums always have a valid zero (§3.2), so they need no
    `constinit` (ChatGPT, overbuild).

### 4.4 Cross-unit mismatch

13. **What is recorded.** Per unit, for every external-linkage variable and
    function, verbs records its qualified name, canonical type, and whether
    it is vlib-containing. For every external-linkage class definition, it
    records the qualified name, the concatenated canonical field-type
    signature, and the flag.
14. **What is flagged.** The cross-unit step groups these by linkage
    identity: the mangled name for functions and variables, the qualified
    name for classes. Overloads have different mangled names, so they never
    group (ChatGPT F13). It reports an identity with two or more canonical
    types or field signatures, where any one is vlib-containing. A function
    mangling omits its return type, so this catches return-type confusion
    as well as `extern` type confusion and ODR violations (soundness B6).

**Unanalyzed definitions.** The same records say which functions and
variables some analyzed unit defines. Code defined in no analyzed unit can
write anything it can reach, so rule 7 is checked here, not assumed
(soundness m3). A vlib type has all its claims `outside` when one of these is declared in
analyzed code, defined in no analyzed unit, and mentions the type:
- a function that takes or returns a vpr to it, including a const one.
  `const_cast` makes a const pointer writable, and `span<E>` is a vpr (MiMo
  R2-02);
- a function that returns a value containing it: `E`, `optional<E>`, a
  struct holding an `E` (ChatGPT R3-05);
- a variable whose type contains it or is a vpr to it.

Library declarations are judged at their typed API (§4.5), and are not
unanalyzed definitions.

The report names the declaration. A template instantiated only in unanalyzed
units is the same case.

### 4.5 Scope

Scope is decided by repository path through verbs' path rule (§6.3), never by
Clang's system-header flag.
- A repository file marked `#pragma clang system_header`, or reached through
  `-isystem`, cannot hide an escape.
- libc++ and SDK code is judged at its typed API. Its internals are not
  scanned, and are never reported: `optional`'s union storage, `vector`'s
  relocation `memcpy`. Rule 2's derived table covers the library functions
  that change a pointer's type.

### 4.6 Silencing

verbs honours no suppression comment, and nothing silences a finding
(checks M2). These are silencing findings, printed `!`:
- **Warnings the boundary needs.** A change to the diagnostic state of a
  warning in rules 9–10, by any pragma spelling (`clang`, `GCC`, `_Pragma`).
- **Hiding files.** `#pragma clang system_header`, or a line marker, in a
  repository file.
- **Compile commands.** Any change to a unit's `-D`, `-U`, `-std`, `-W`,
  `-w`, `-isystem`, `-include` or hardening arguments, judged on the
  resolved invocation (§6.2). verbs records it for each unit and diffs it
  per run. A change of the resolved invocation with no change in the
  database's command line comes from the environment, a response file or a
  Clang config file (ChatGPT R3-07). It prints `!` and names the
  difference.
- **Assumptions.** `[[assume]]`, `__builtin_assume` or `__builtin_unreachable`
  outside vlib.
- **Scope.** A change to verbs' path rule.

### 4.7 Weakening

The baseline is every subject's **declared predicate**: the P its type
carries, whatever its state was (`holds`, `finding` or `outside`). A subject
whose declared predicate disappears or widens is a **lost claim** (doctrine
D2, checks M2). Basing it on the declared predicate means an escape cannot
first move a subject out of `holds` and then let its type be downgraded
silently (ChatGPT F11). For example:
- its type changed to a raw integer;
- its `Bounded` range widened;
- its verbs enum gained a value.

A lost claim prints `!` even when the change is intended, so that a reader
sees it.

### 4.8 Attribution

Every escape is a conversion or write at a point where the static types
involved are known. Its **affected types** are these (MiMo R2-05):
- the source's pointee type, for an erasure;
- the destination's, for a re-typing (`void*` to `E*`) or a raw write;
- both, when both are vlib-containing or vlib-reachable;
- the named type, for rules 7, 9, 10 and 12–14;
- for a vlib-reachable base, every analyzed class derived from it.

It voids claims in two steps (ChatGPT F06, MiMo F5):
1. It voids every **leaf vlib type reachable** from an affected type:
   contained in it, or reached through its pointers, references and vpr
   wrappers, recursively. Erasing `&p` where `p` is an `E*` voids `E`
   (ChatGPT R3-06). Containment, which stops at pointers, stays the notion
   for representation (§2).
2. It voids every claim, program-wide, whose type contains one of those
   leaves.

`memset(&packet, …)` on `struct Packet { E kind; }` voids every claim on `E`:
`Packet::kind`, and a later `E copy = packet.kind`. A sibling `F other`
keeps its claim.
- An escape with no affected type voids every claim program-wide. Two cases
  have none:
  - an `asm` `"memory"` clobber with no vlib operand;
  - a keyword macro (rule 11).
- The escape-v2 lane proposed voiding only the unit for an erased sink. That
  is weaker than the type closure when one object is reached from several
  units, and it was not adopted.

Narrowing to the exact declaration needs points-to analysis (soundness M7;
bead verbs-de3.33). The coarse rule never yields a false `holds`; it costs
only precision.

### 4.9 Evidence

There are two prototypes, both LibTooling on the pinned Clang, preserved in
context/prototypes/:
- **escape-lane/**, 689 lines: rule v1;
- **escape-v2/**, 725 lines: this rule.

Results for v2:
- **Counterexamples:** 48 of 48 resolved; 43 caught and 5 correctly clean.
  - They cover all first-tribunal escape cases, ChatGPT F02–F06 and F12, the
    MiMo `const void*` variant, and 25 of the lane's own attacks.
  - The attacks include `uintptr_t`, pointer `bit_cast`, member pointers,
    `shared_ptr<void>`, `sscanf`/`va_arg` destinations and
    `__builtin_assume_aligned`.
  - Each bypass was first confirmed to forge its value under ASan and UBSan
    at `-O2`.
- **False escapes:** zero, on 13 legitimate programs that compile and run.
  They cover `optional`, `variant`, `expected`, `tuple`, `vector` with `sort`
  and ranges, the ordered and unordered containers with vlib keys and
  `std::hash`, `array`, `span` of const, `std::format`, `atomic<E>`, smart
  pointers, `std::function`, `deque`, `list` and `any`. The whole-object
  `memcpy` case is an escape since round 3 (rule 4). A polymorphic
  `dynamic_cast` downcast into a vlib-containing class is not yet a case;
  the plan adds it.
- **Cost:** the same as v1, about 1.0 s user time per libc++-heavy unit,
  against 0.55 s for `clang -fsyntax-only`.
- **Holes the boundary excludes** (lane §5):
  - a call through a reinterpreted function pointer (UB, rule 8);
  - coroutine-frame offset arithmetic (rule 8);
  - an allocator or pmr byte buffer written while it backs a live vlib
    object. Rule 3 now forbids keeping that writable alias.
- **`start_lifetime_as`** is in rule 2, but it is not yet in libc++ 23.1.2.
  The implementation does not match it until the pinned libc++ declares it.
- **Where the prototype differs from this text** (MiMo R2-08, R2-11):
  - it flags every non-`constinit` vlib static, where rule 12 is narrower,
    so its tally counts o05 as caught;
  - it does not handle `#undef` of vlib macros;
  - it matches the memory functions by substring;
  - it voids the whole unit for an erasure;
  - it has no cross-unit step (v1 had one);
  - it does not treat a pointer to a vpr as a vpr, so it misses the `E**`
    erasure of R3-06;
  - it implements the exemptions round 3 removed, so it misses R3-01 to
    R3-03.

  The implementation follows this text, not the prototype. The round-2
  review confirmed R2-01 and R2-03 against it (prototype in
  context/prototypes/escape-v2/, cases r2_01–r2_04). Round 3's eight
  cases are r3_01–r3_08. Each reaches 7 under ASan and UBSan at `-O2`,
  except r3_08, which is a contradiction in the spec text. The prototype
  catches only r3_04.

The prototypes are evidence for the rule, not the implementation. The
implementation is written red-first against §10.2, and every case above
becomes a case file.

## 5. Discovery: not in the basics

The enum-candidate check is removed from the basics
(papers/2026-10-17-enum-candidate-redesign.md). The rule was redesigned with
every term defined and the false classes turned into clauses. It was tuned
on blackbird and measured on BRepGPU as held-out data:
- **Edit-boundary tiers on BRepGPU:** 46% precise frozen, and 62% after a
  fact-loader fix. The bar is no effective false positives.
- **Remaining false findings:** a version number, a count and a bit mask.
  Each is used exactly as an enum would be, so only a name rule would
  separate them, and a name rule is a guess.
- **Recall at the edit boundary:** 6.6% on blackbird.
- **Jev's second label:** it agreed at chance (κ 0.17 and −0.01), so it
  certified nothing.

It is not a correctness check (doctrine D5). The rule, its settled points
(never gate; observed values are a lower bound), and the cheapest precise
follow-up are in bead verbs-de3.35. That follow-up reports only subjects fed
from an existing enum, which was 3 of 3 true on blackbird.

## 6. `verbs check`

### 6.1 Interface

```
verbs scan  -p <build-dir>                     # full analysis; lists claims with the boundary
verbs check -p <build-dir> [--changed <path>...]
```

`--changed` is a hint for scheduling, never the authority on what changed
(checks B1).

The caller appends stdout verbatim to the edit's tool result and acts only on
the exit status (doctrine D18). The output text is not a versioned contract.

| Exit | Meaning | Expected caller behaviour |
|---|---|---|
| 0 | Nothing gates | continue |
| 1 | An escape or in-source silencing is present, or this edit lost a claim or changed a compile command or the path rule | the agent addresses it |
| 2 | No complete check: none ran, or compile errors suspended the report (§6.2). The reason is printed, and so are escapes found in the units that compiled. | the agent must not read silence as a pass (doctrine D25) |

- **Findings gate by state, events once.** An escape, or a silencing
  construct in source, keeps exit 1 on every run until it is fixed. It is
  printed in full once, then as one `N unresolved` line (MiMo F6). Lost
  claims and compile-command or path-rule changes are events: they gate the
  run that sees them.
- **Precedence: 2, then 1, then 0.** All findings still print. Exit 3 left
  with decisions (§7), which also settles ChatGPT F18.

### 6.2 Verifying traces: what decides that a unit is re-checked

Each run decides for itself which units changed. For each unit, verbs records
a **trace** (core literature §9; checks B1, M7). The trace holds:
- the hash of the unit's **resolved invocation**: the `-cc1` command line
  that the pinned driver prints for the database entry under `-###`, plus
  the working directory. The driver folds `CPATH` and the other include
  variables, response files, `SOURCE_DATE_EPOCH`, `SDKROOT` and Clang
  config files into that line. Measured: changing any one of them changes
  the line (ChatGPT R3-07). verbs then runs the `-cc1` line it hashed, so
  the analysis sees the inputs the trace recorded;
- every input file Clang read: SourceManager file entries, `#embed`
  resources, and the PCH's input-file list, each with size, mtime and content
  hash;
- every negative probe: include-path lookups that missed, and
  `__has_include` results.

On every run:
1. **Compilation database.** Diff it per entry by resolved-invocation hash. Drop facts
   for removed entries. For a changed source that is not in the database,
   print `! outside: not in compilation database`.
2. **Traces.** Hash the content of every recorded input on every run. Size
   and mtime are not identity: a same-length edit with a restored mtime must
   not reuse facts (ChatGPT F07). Measured: blackbird's sources plus the
   libc++ headers, 1,898 files and 19 MB, hash in 0.34 s wall. A unit whose
   trace mismatches, or whose negative probe now finds a file, is stale.
3. **Re-extract** every stale unit. `--changed` only orders the work.
4. **Cross-unit evaluation:** declaration and definition mismatches and
   unanalyzed definitions (§4.4).
5. **Delta** against the previous report (§6.5).

Other cases:
- **PCH:** the prefix header is parsed with `-include` and the PCH flags are
  stripped.
- **Modules:** a unit that imports a module is `outside` (bead
  verbs-de3.31).
- **Compile errors suspend the report** (ChatGPT F08, MiMo F3). A unit
  that compiled before and now fails may hold an escape, and an escape
  voids claims in every unit (§4.8). So no claim is current. The run then does three things:
  - it prints `+` lines for escapes found in the units that did compile,
    since those are real;
  - it prints one `! claims suspended: N units do not compile` line, with
    no claim lines, no `-` lines and no lost claims;
  - it exits 2, because the caller acts only on the exit status, and a
    suspended run is not a pass (MiMo R2-06).

  The next run in which every unit compiles is complete, and it computes
  its delta against the last complete report. Facts from a failed unit are
  history, never current claims, so incremental equals from-scratch again
  once the code compiles.
- **Units the pinned Clang cannot compile at all,** such as CUDA units, are
  listed in the path rule (§6.3). They are code outside the analyzed set
  (rule 7) and never suspend the report (doctrine D25). Every other unit
  that fails to compile suspends it. That includes a new unit an agent is
  still writing, so no unanalyzed code is quietly treated as outside
  (Jev re-audit of ChatGPT F08).
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
  or otherwise outside, in `.verbs-outside` at the repository root. Each line
  is a repository-relative glob, a space, and the reason. `#` starts a
  comment. Changing it is a silencing event (checks m5).

### 6.4 Keys

Keys never contain line numbers or byte offsets (checks M8).

| Entity | Key |
|---|---|
| External linkage | USR |
| Internal linkage, including anonymous namespaces | repository-relative path plus qualified name; for functions, plus the canonical signature, so internal overloads differ (ChatGPT F16) |
| Local variables | enclosing function's key, name, ordinal among same-named locals in that function |
| Lambdas and unnamed types | enclosing key plus ordinal among siblings of that kind |
| Escape | enclosing function's key, construct class, ordinal within the function |

Ordinal keys change when a sibling is inserted before them. That shows as
one `-` and one `+` line, which is honest about what verbs can identify.

Renaming a subject retires its old key; that is correct, because the subject
changed. Functions defined in headers are counted once by identity, not once
per unit (checks m7).

### 6.5 Output

```
verbs · 3 units re-checked · 1.8 s · build/debug
+ escape  FrameKind enum ingress outside verbs::to   src/journal.cpp:281
    static_cast<FrameKind>(raw_kind)
    fix: verbs::to<FrameKind>(raw_kind), keeping ErrorCode::unsupported on failure
! lost claim  Header::version  Bounded<1,5> -> std::uint8_t   include/x/header.hpp:12
claims assume: no unwind mid-mutation · no moved-from use · single owner · one thread ·
  no call-out while broken · single-state · analyzed code is this database's units ·
  no UB outside vlib · hardening ≥ FAST · switch-enum and uninitialized are errors
```

| Prefix | Meaning |
|---|---|
| `+` | new finding |
| `-` | resolved finding |
| `~` | changed evidence under an unchanged key |
| `!` | lost claim, silencing, or something not analyzed |

Rules:
- **Order:** escapes, then lost claims, then silencing.
- **Caps:** at most 3 findings per file and 10 in total; the plan may
  re-tune both against agent transcripts. Withheld findings stay marked
  *unshown* and carry into the next delta until printed (checks M9).
- **The boundary line** is printed whenever the delta reports a claim
  change.
- Each finding gives its evidence and one concrete fix. A fix never invents
  enumerator names or values.

### 6.6 Latency

- **Budget:** p95 of at most 10 s per edit on the operator's machine at
  normal load.
- **Cost model**, measured on blackbird (checks M11): about 3.1 CPU-s per
  unit. A `.cpp` edit costs one unit. A header edit costs its fanout:
  `foundation.hpp` reaches 243 of 257 units, and the touch-weighted mean
  fanout is 72.5 units, about 14 s on 16 idle cores.
- **Over budget, verbs still finishes.** The budget is a criterion for
  enabling the hook, never a correctness cutoff (ChatGPT F08, MiMo F10). A
  partial run would leave stale units whose escapes nobody examines, so
  every run analyzes every stale unit.
- **First runs:** the first check in a new build directory, and any run
  after a facts-format change, is a full scan, about 46 s on 16 idle cores.
  It prints a progress line first, so the wait is visible.
- **Concurrency:** verbs processes in different build directories do not
  share job slots, so several agents on a loaded host slow each other (bead
  verbs-de3.34).
- **Gate:** enabling the check in Blackbird's hook is gated on this budget,
  measured on blackbird (bead verbs-de3.14), alongside the precision gate
  (§10.3).

## 7. Decisions: not in the basics

Decisions recorded verdicts on proposal subjects. With discovery removed
(§5), nothing in the basics takes a decision, so `VERBS_OPEN_DOMAIN`, the
exit-3 gate and the decision lifecycle leave with it (bead verbs-de3.35).
Two results carry over to that bead:
- **Placement** (operator decision, 2026-10-17): on the declaration.
- **The gate must prevent, not merely detect** (doctrine D3).

Escapes, silencings and lost claims are never waived; they are fixed in
code (§2).

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
| Missed or spurious escape | One case file per §4 rule clause, with expected findings in source comments, compared exactly (the IWYU style). Each clause has a case that trips it and one that just misses it. Every counterexample from the tribunals, the external reviews and escape-v2 is a case. Round 2 named four that confirm only with the cross-unit step or the revised rule text. Each forged 7 under ASan/UBSan at `-O2` with zero prototype findings, except where noted: an upcast to a non-vlib base, then a `char*` store; an unanalyzed callee taking `const E*` or `span<E>`; a `std::move` reference through the read-only sink, then `memset`; and `memcpy(&void_slot, &e_ptr)`, then `memset`, which the prototype caught and the spec text had dropped (MiMo R2-09). Their just-miss partners: a non-vlib upcast never erased; `fwrite` of `std::to_underlying(e)`. A polymorphic `dynamic_cast` downcast is a just-miss (legitimate). Round 3 added eight more (r3_01–r3_08): `strtol`'s `endptr`, `memcpy`'s returned pointer, a size multiple that spans sibling fields, a base copy over tail padding, `dynamic_pointer_cast<void>`, an unanalyzed function returning `E` by value, an `E**` erasure, and `os << &e`. Their just-miss partners: typed assignment in place of each copy; `static_pointer_cast` to a base. Each case asserts claim states, not only findings. |
| Escape the rule does not know | **Audit build** (checks M3). vlib's `get()` checks its invariant at runtime instead of assuming it. For enums, which have no accessor, `verbs::name`, `std::to_underlying` through a vlib wrapper, and every migrated seam's re-encode check membership against expected sets written independently in the tests (ChatGPT F14). Migrated blackbird's test suite and the corpus projects' suites run under ASan and UBSan. A runtime violation of a value whose claim the report shows as `holds` is a missed escape, whether or not some escape was reported elsewhere. A misattributed escape is still a miss (ChatGPT R3-06). **Limit:** sanitizers never check enum membership for fixed-underlying enums, so an enum read no audit point observes goes unseen; the case files (row above) carry that class. |
| Key instability | Metamorphic tests: reordering declarations, moving a function between units, and reformatting leave findings and keys unchanged. |
| Incremental differs from scratch | After every generated sequence of changes, `verbs check` equals a fresh `verbs scan`. The generator includes environment-only and response-file-only changes (ChatGPT R3-07), out-of-band writes, created and deleted files, database changes, generated headers, and non-compiling intermediate states (checks M10). It runs over corpus projects (§1.1) as well as small fixtures. Only complete runs are compared; a suspended run must print no claim (§6.2). |
| Wrong delta | Delta tested as a pure function over report pairs: applying `delta(a, b)` to `a` gives `b`, and unshown findings persist until shown (doctrine D19). |
| Corrupt facts | libFuzzer on every reader; a write-then-read round trip; a torn write leads to rebuild. |

### 10.3 Real code

- **The corpus runs of §1.1** (doctrine D9, checks M3). A missed seed or a
  false finding is a bug. Each one becomes a case file (§10.2) and is fixed.
- **The reviewer** is the operator, or an agent with no access to the
  check's source. The operator's reading alone completes the gate. Jev, when
  available, gives a second reading, and each disagreement is re-read and its
  resolution recorded. No step depends on a model being available (ChatGPT
  F09).
- **A fix is checked on projects it was not made against** (checks M6). A
  new false finding there is another bug.
- **Gate:** the hook is enabled only after a corpus run with no missed seed
  and no false finding, with the latency budget holding (§6.6).

### 10.4 Mutation testing

Runs on the fleet, never on the laptop. Mull covers runtime paths once it
supports the pinned Clang (verbs-b4x). Source mutants cover compile-time logic
(§10.1).

## 11. Departures from the brief

| Brief | Basics | Why |
|---|---|---|
| Delta daemon with clangd tiers | Stateless `verbs check` with verifying traces | Operator; push needs no residency; traces make it correct |
| Agent run with and without verbs; edits-to-detection | Deterministic corpus runs (§1.1) | verbs is deterministic; the variance came from the agent |
| `.verbs/decisions.jsonl` | No decisions in the basics | Nothing takes one once discovery is out (§5, §7) |
| Annotations declare invariants | The vlib type is the declaration | No second declaration to drift |
| `Bounded` widening only | Widening, checked `+=`/`-=`, `k`, `upto`, implicit egress | Loops and indices must read naturally |
| UB in constant evaluation for bound overflow | `__int128` everywhere, with `static_assert` | Clear diagnostics; `%` and `+=` edge cases |
| `VERBS_ENUM` positional | `name = value`, zero rule, reflection later | Wire domains |
| `Refined`, `Id`, typestate, capabilities | Deferred (beads) | No corpus consumer; blackbird's `Id` is stronger |
| Deny-list of escape constructs | Allowlist by AST meaning | Soundness tribunal |
| Lint suppression honoured | Nothing silences a finding | Escapes are fixed in code |
| SQLite cache, preservation verdicts | Per-unit traces and facts | Nothing else to cache |
| Visible-state class invariants | Value invariants in types | Reentrancy; claim-scope decisions |
| Four lints | The escape check only | Basics first; the enum-candidate check was measured and missed the bar (§5) |
| C++23 | C++26 (`-std=c++2c`) on the pinned Clang | Operator decision |

## 12. Open questions for the second tribunal

1. Is the allowlist (§4) complete? Find a write to vlib bytes, or a creation
   of a vlib value, that none of rules 1-14 matches and the boundary does not
   exclude.
2. Do verifying traces (§6.2) make incremental equal from-scratch under the
   generator's out-of-band changes?
3. Does suspending the report on compile errors (§6.2) leave any path in
   which a stale fact reads as a current claim?
4. Does anything left in the basics lack a named consumer?

## 13. Increments

The plan sequences these; listed here so the spec states what "done" means.

1. **E: enums.** `VERBS_ENUM` and `verbs::to<E>`. The escape rules that
   concern enums. `verbs check` with traces, keys, delta and exit codes. The
   §10 oracles for all of these. Lands with blackbird's decoding-seam
   migration (§1.1).
2. **B: `Bounded`**, once a blackbird declaration is named (§3.3). Otherwise
   it moves to a bead.

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
| C++ modules in analyzed units | verbs-de3.31 |
| Facts shared across worktrees (constructive traces) | verbs-de3.32 |
| Points-to narrowing of escape attribution | verbs-de3.33 |
| Shared job slots across concurrent verbs processes | verbs-de3.34 |
| Enum-domain discovery (scan-only) and decisions | verbs-de3.35 |
| Mull on the pinned Clang | verbs-b4x |
| Rust phase | verbs-4ox |
