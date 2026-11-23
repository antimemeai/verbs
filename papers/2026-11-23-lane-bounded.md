# Lane: bounded and refined types — 2026-11-23

Habit under study: **use bounded types** — integers and quantities whose valid
range is carried by the type. This lane covers (a) constructs that carry the
habit in C++ and Rust, (b) refinement systems used as references (SPARK,
Liquid Haskell, Flux, Rust pattern types, C++26 contracts), (c) detectors for
values that *should* have been bounded, and (d) what misuse of a bounded type
looks like and which misuse can be stopped on strong evidence. It does not
write the design.

Toolchain probes used Homebrew LLVM 23.1.2 (`/opt/homebrew/Cellar/llvm/23.1.2`,
`-std=c++2c`, Xcode SDK sysroot) and Rust 1.99.0 / clippy 0.1.99 (b940084d7e
2026-09-28) from the repo's `rust-toolchain.toml`. Probe sources lived in the
session scratchpad and are reproduced where load-bearing. Corpus measurements
extracted six projects into `context/scratch-bounded/` and deleted them after.
Quarantine paths are relative to `quarantine/`, at the commits recorded in
`quarantine-manifest.md` and `papers/2026-10-17-reference-implementations.md`
(bounded-integer 32f8c2b, safe_numerics be8f647, type_safe 292e8c1, mp-units
9ffaf3e, strong_type aa02c52, NamedType 76668ab; llvm-project 23.1.2).

## Summary of findings

1. **Rust can carry this habit with stops that need no new checker.** A
   bounded value whose field is private and whose only unchecked door is an
   `unsafe fn` cannot be forged without `unsafe` or code inside the defining
   module. deranged, bounded-integer (Kestrer) and nutype all use exactly that
   shape (§2). The bypass surface is closed by the language. That is the
   opposite of the C++ escape-check experience (§5.3).
2. **C++ can put most stops into the compiler itself.** Probing a 40-line
   C++26 `Bounded<Lo,Hi>` on Clang 23.1.2: an out-of-range literal, a raw-int
   assignment, an implicit range narrowing and a widened sum stored back all
   fail to compile. The diagnostics name the reason when the construct is
   written for it (`= delete("…")`, a reason-named non-constexpr function, a
   concept whose failing clause is printed) (§1.8). What C++ cannot do cheaply
   is stop *representation* bypasses (memcpy, casts, unions). Three review
   rounds of the old escape check show that becomes an open-ended chase (§5.3).
3. **Arithmetic semantics is the unsettled design point.** Every library picks
   differently: bounded-integer widens the result type and makes an
   overlapping assignment UB (`std::unreachable`). safe_numerics throws or
   traps by policy. type_safe checks and aborts in every build mode by
   default, and a configuration switch turns the check off (corrected in
   the check, §1.3).
   deranged offers no operators at all, only named `checked_`/`saturating_`/
   `wrapping_`. Kestrer's crate panics on every out-of-range operator. Wuffs
   and SPARK keep the declared type and discharge a proof. Loop accumulators
   break widen-on-every-op designs (literature-core §7, finding 11).
4. **Detecting "should have been bounded" sits near the old enum heuristic's
   precision.** A regex census of six real projects (§4.1) found names
   range-guarded at three or more sites. Only about 20% of those were genuine
   fixed-domain values. With constant bounds that repeat exactly, 13 of 29
   (45%) were. Five more (17%) were enum-range checks belonging to the
   enum habit. The main false class is dispatch over several sub-ranges of
   one value: character classes, opcode classes, widget ids. This can be a
   nudge, never a stop.
5. **Narrowing-conversion lints are the demand signal, and bounded types
   are what quiet them.** On 35 JoltPhysics files, `bugprone-narrowing-
   conversions` reported 13 findings, none of them a bug. Every one was safe
   only because of a range the author knew but the type did not carry
   (e.g. a trailing-zero count ≤ 32 returned as `int`) (§4.2). The kernel
   and LLVM experience is the same in the other direction. Overflow checks on
   plain integers drown in intentional wraparound (Dietz et al. 2012; Clang's
   overflow-idiom exclusions; Torvalds 2024) (§4.4). The stop belongs on the
   bounded construct, not on plain integers.
6. **Way-past-with-reason exists natively in two of the three ecosystems
   studied.** Rust `#[expect(lint, reason = "…")]` warns when the expectation
   goes unfulfilled (probed). GNATprove's `pragma Annotate (GNATprove,
   False_Positive|Intentional, pattern, reason)` warns on a justification that
   matches nothing. clang-tidy `NOLINT(check)` has no required reason and no
   stale detection, so verbs would have to own that for C++ (§3.1, §4.3).
7. **Two native C++ mechanisms were found in the pinned toolchain that the
   earlier lanes did not record.** Clang 23 ships experimental overflow
   behavior types (`__ob_trap`, `__ob_wrap`, behind `-cc1
   -fexperimental-overflow-behavior-types`; probed: overflow traps with
   SIGTRAP). It also has `-fsanitize-undefined-ignore-overflow-pattern=`
   for known idioms (§1.7). Neither carries an arbitrary range. Both are
   useful as runtime oracles in seeded-fault testing.
8. **Refinement checkers are references, not candidates, this round.** Flux
   needs nightly rustc, liquid-fixpoint and z3, and checks no overflow by
   default. Pattern types are internal-only with no RFC. P2900 contracts are
   "No" in Clang (cxx_status, read 2026-11-23) and unknown to 23.1.2
   (`-fcontracts` rejected). LiquidHaskell's users report nine usability
   barriers, led by error messages (Gamboa et al., PLDI 2025) (§3).

---

## 1. C++ constructs

### 1.1 bounded::integer (davidstone/bounded-integer)

**What it is.** `bounded::integer<auto minimum, auto maximum>`, written as
C++20 modules. Storage is the smallest builtin that holds the range
(`source/bounded/underlying_type_t.cpp`).
- **Arithmetic widens.** `operator+` returns
  `integer<safer_add<lhs_min,rhs_min>(), safer_add<lhs_max,rhs_max>()>`. Bound
  overflow is a `static_assert("Overflow in calculation of bounds.")`
  (`source/bounded/arithmetic/plus.cpp:29-58`).
- **Ingress.** Three doors:
  - `check_in_range` throws `std::range_error` with the value and range in
    the message (`check_in_range.cpp:47-53`);
  - `assume_in_range` calls `std::unreachable()` when out of range
    (`integer.cpp:88-92`);
  - `clamp` (`clamp.cpp:17`).
- **Assignment from an overlapping type** goes through `assume_in_range`,
  so it is UB when out of range (`integer.cpp:191-193`). `++x` is
  `x += constant<1>` (`arithmetic/increment_decrement.cpp:41`). The
  compound assignment comes from a separate `operators` library
  (`<operators/compound_assignment.hpp>`) that is not in quarantine, so
  "increment past `maximum` is UB" is inferred (`x = x + 1`, then the
  overlapping assignment), not read in source.
- **`value()`** carries `[[assume(minimum <= m_value and m_value <=
  maximum)]]` (`integer.cpp:169`).
- **`m_value` is public**: "Do not access this directly. This must be public
  to be usable as a non-type template parameter in C++20"
  (`integer.cpp:205-208`).
- **`BOUNDED_ASSERT`** is an `assert` in debug builds. Under `NDEBUG` or
  `BOUNDED_NDEBUG` it checks only during constant evaluation and does
  nothing at run time; the sibling `BOUNDED_ASSERT_OR_ASSUME` becomes
  `[[assume]]` (`include/bounded/assert.hpp:25-29`).

**How it would carry the habit.**
- *Construct:* yes, and it is the most complete C++ range-propagating
  design studied.
- *Stops:* the compiler rejects any mix that would widen without a declared
  door.
- *Not usable as-is for verbs:*
  - the UB-on-overlap assignment turns a would-be stop into silent UB;
  - the public `m_value` is a bypass by name. A lint could flag the name
    as a stop, because the field's own comment forbids touching it.

**Evidence.** 485 inline `static_assert`s act as specification oracles
(reference-implementations §1). No precision or agent-ergonomics data
exists.

**Costs.**
- Modules-only: the README requires Clang 22+, so the pinned toolchain
  suffices.
- Each distinct range is a distinct type, so instantiation count grows
  with the arithmetic.
- The widening design cannot type a loop accumulator (literature-core
  finding 11).

### 1.2 Boost.SafeNumerics

**What it is.** `safe<T, PromotionPolicy, ExceptionPolicy>`, plus
`safe_signed_range<Min,Max>` / `safe_unsigned_range<Min,Max>`
(`include/boost/safe_numerics/safe_integer_range.hpp:32,49`). Interval
arithmetic (`interval.hpp`) computes each result's possible range.
- **Exception policy.** Each class of error — arithmetic, implementation-
  defined, undefined, uninitialized — maps to `ignore_exception`,
  `throw_exception` or `trap_exception`
  (`exception_policies.hpp:23-48, 52-80`).
- **`trap_exception`** is deliberately undefined: an operation whose
  interval *could* fail becomes a compile error ("emit compile time error if
  this is invoked", `:62-67`).
- **Presets.** `strict_trap_policy` traps all four classes; "requires code to
  be written in such a way as to make it impossible for errors to occur"
  (`:156-166`). The default is `strict_exception_policy` (throw, `:171`).
- **`automatic` promotion** widens result types (`automatic.hpp:29`).

**How it would carry the habit.**
- *Stop:* `trap_exception` is the strongest stop studied. It refuses to
  compile any arithmetic that is not provably in range. That is Wuffs' "keep
  the type, prove the fit" done with intervals instead of facts.
- *Way past:* swap the policy per type — coarse, and with no per-site
  reason.

**Evidence.**
- The library tests each operator with result matrices run at runtime and
  under `constexpr` (`test/test_add_native_results.hpp`,
  `test_*_constexpr.cpp`).
- No field data on how often `strict_trap_policy` code compiles without
  contortions.
- Its own comment calls the trap policy "extra coding effort … justified for
  embedded and/or safety critical systems" (`:154-156`).

**Costs.**
- Boost dependency.
- Diagnostics: a trap is a call to an undefined `operator()`. The agent sees
  "no matching function" deep in an instantiation, not a range message.
- Heavy templates; compile time not measured here.

### 1.3 type_safe (foonathan)

**What it is.**
- **`constrained_type<T, Constraint, Verifier>`** (`constrained_type.hpp:106`).
  Verifiers:
  - `assertion_verifier` checks when precondition checks are enabled and
    otherwise passes the value through unchanged (`:30-44`);
  - `throwing_verifier` always checks (`:62`).
- **`modify()`** returns an RAII modifier that re-verifies on destruction
  (`:205`).
- **Bounded aliases.** `bounded_type` is `constrained_type` over
  `closed_interval`/`open_interval` (`bounded_type.hpp:265-271, 362`).
  `clamped_type` uses `clamping_verifier` (`:508, 547`).
- **`ts::integer<T>`** forbids narrowing conversions. It "checks against
  unsigned under/overflow in debug mode and marks it as undefined for the
  optimizer otherwise" (`integer.hpp:79-93`).
- **`narrow_cast`** (`narrow_cast.hpp:81`).

**How it would carry the habit.**
- *Construct:* yes, with a pluggable verifier.
- *Stop:* none at compile time for ranges; violation is an assert or a
  throw.
- *What to study:* the `modify()` window is the only design studied that
  lets a value leave its range temporarily and checks it on exit. It is
  relevant to loop accumulators.

**Evidence.** Catch tests only. No precision or ergonomics data.

**Costs.**
- The default `assertion_verifier` checks in release builds too:
  `TYPE_SAFE_ENABLE_PRECONDITION_CHECKS` defaults to 1 with no `NDEBUG`
  test (`config.hpp:22-27`; CMake option default `ON`,
  `CMakeLists.txt:25`), and a failure aborts through debug_assert's
  default handler. If the user sets it to 0, the verifier passes the value
  through unchecked. Only `DEBUG_ASSERT_DISABLE` turns the failure into
  `__builtin_unreachable()` (`external/debug_assert/debug_assert.hpp:364-367`).
  So the stop is a runtime abort that one macro can switch off, not a
  debug-only assertion. `ts::integer`'s "debug mode" in its doc comment
  means the same precondition-check switch.
- Exception safety of the `modify()` destructor check is unexamined.

### 1.4 mp-units

**What it is.** Quantities whose unit and quantity kind are types.
- **Value-preserving conversions** are enforced by concepts. Each failing
  branch calls a `consteval bool unsatisfied<"fmt">(args…)`. With
  `MP_UNITS_API_THROWING_CONSTRAINTS` that throws a formatted message
  during constant evaluation, so the reason appears in the diagnostic
  (`bits/unsatisfied.h`; uses in `framework/quantity.h:82-120`, e.g.
  "Conversion from '{}' as '{}' to '{}' as '{}' is truncating").
- **Deleted overloads** carry C++26 `= delete("Conversion is truncating")`
  (`quantity.h:714`).
- **The stored value is public** for structural-type reasons. It is named
  `numerical_value_is_an_implementation_detail_`, declared at
  `quantity.h:662` with the comment "needs to be public for a structural
  type" (line 292 is a use), and the sanctioned egress is
  `numerical_value_in(unit)`.
- **Range policies** attach to quantity-point origins:
  - `check_in_range`, `clamp_to_range`, `wrap_to_range`,
    `reflect_in_range` (`overflow_policies.h:315, 346, 381, 425`);
  - `check_non_negative` / `clamp_non_negative` (`:534, 559`).
- **`utility/constrained.h`** and **`utility/safe_int.h`** add policy-carrying
  wrappers. `safe_int` reports "safe_int: narrowing conversion overflow" and
  "addition overflow" through a policy (`safe_int.h:293, 363`).

**How it would carry the habit.**
- *Construct:* units and range together, the most complete realization of
  "quantities whose valid range is carried by the type".
- *Stops:* truncating conversions and kind mismatches are compile errors
  that name the reason. This is the best diagnostics practice found in any
  reference, and it is reusable as a technique without the library.
- *Way past by naming:* the escape is spelled so that any use of it is
  self-incriminating and greppable. A stop rule on the identifier
  `numerical_value_is_an_implementation_detail_` outside the library has
  near-certain precision.

**Evidence.** A large `test/static/` compile-time suite, including
`requires !requires` negative tests (reference-implementations §2). No field
data.

**Costs.**
- Large: 4.99 MB of source at the pinned commit.
- Template-heavy diagnostics when the `unsatisfied` path is off.
- For verbs it is a reference for technique, not a dependency candidate.
  It would be a library adoption needing operator discussion.

### 1.5 strong_type, NamedType, and strong typedefs in the field

**What they are.**
- `strong::type<T, Tag, modifiers…>`'s `value_of()` returns `T&`
  (`strong_type/include/strong_type/type.hpp:152-168`). strong_type's
  `range` is an iterator-range modifier (`range.hpp:128`), not a numeric
  range.
- `fluent::NamedType::get()` returns `T&`
  (`NamedType/include/NamedType/named_type_impl.hpp:76`).

**How they bear on the habit.** They carry *kind* (meters vs seconds, lat
vs lon), not range. Mutable access means no invariant can live in them.
- The corpus shows the consequence. OSRM declares `using FloatLatitude =
  Alias<double, tag::latitude>;` under the comment "Internal lon/lat types -
  assumed to be range safe" (`include/util/coordinate.hpp:62-66`, osrm-backend
  f2147ea).
- The [-90, 90] / [-180, 180] check is then repeated by hand:
  `src/util/coordinate.cpp:20`, `src/util/coordinate_calculation.cpp:247`,
  `include/nodejs/node_osrm_support.hpp:434`, and 14 test sites.
- "Assumed" in a comment is the prose doctrine verbs replaces.

**Implication.** A strong typedef is a natural *nudge target*: "this
alias is range-checked at N sites; make it bounded". It is not a construct
for this habit.

### 1.6 GSL `narrow` / `narrow_cast`

- `gsl::narrow_cast` is "a searchable way to do narrowing casts of values"
  (`GSL/include/gsl/util:177-179`).
- `gsl::narrow` throws `narrowing_error` if the cast changed the value
  (`include/gsl/narrow:55-67`).
- The C++ Core Guidelines tie `cppcoreguidelines-narrowing-conversions` to
  these. The clang-tidy docs suggest them as resolutions
  (`clang-tools-extra/docs/clang-tidy/checks/bugprone/narrowing-
  conversions.rst`).
- **Habit role:** a named, countable way past a narrowing nudge. Its
  greppable name is the same idea as mp-units' self-incriminating field.

### 1.7 Clang overflow behavior types and overflow-idiom exclusions (pinned toolchain)

**What it is.** `__attribute__((overflow_behavior(trap|wrap)))`, with
keyword spellings `__ob_trap` / `__ob_wrap`. It applies to a typedef, a
variable or an integer type.
- `trap` checks arithmetic on that type even under `-fwrapv`.
- `wrap` defines wraparound and suppresses UBSan's overflow and truncation
  checks for the type.
- It "wholly overrides global flags (-ftrapv, -fwrapv, sanitizers, and
  Sanitizer Special Case Lists)".
- It is experimental, behind `-cc1 -fexperimental-overflow-behavior-types`.

Sources: `llvm-project/clang/include/clang/Basic/AttrDocs.td:10343-10385`,
`clang/docs/OverflowBehaviorTypes.md`.

**Probe.** `typedef std::uint8_t __ob_trap small; small add(small a, small b)
{ return a + b; }` with `250 + 10`. Compiled with
`-Xclang -fexperimental-overflow-behavior-types` on 23.1.2, it exits 133
(SIGTRAP) at `-O0`, with and without `-fsanitize=undefined`.

**Related flag.** `-fsanitize-undefined-ignore-overflow-pattern=` removes
instrumentation from three idioms that "produce a lot of noise":
`negated-unsigned-const` (`-1UL`), `unsigned-post-decr-while`
(`while (count--)`), and `add-(un)signed-overflow-test` (`a + b < a`)
(`clang/docs/UndefinedBehaviorSanitizer.md:286-320`).

**Compile-time diagnostics (added in the check).** OBTs also carry
type-level guards, not only runtime traps
(`clang/docs/OverflowBehaviorTypes.md` "Conversion Semantics" and
"Diagnostics"):
- assigning between `__ob_trap` and `__ob_wrap` types is a compile
  *error* ("incompatible overflow behavior types");
- converting an OBT to a plain integer warns,
  `-Wimplicit-overflow-behavior-conversion` and its `-assignment` /
  `-function-boundary` variants, grouped under
  `-Woverflow-behavior-conversion`, which `-Wconversion` implies;
- truncation involving a `trap` type gets instrumented.

Probe on 23.1.2: `small r = add(250, argc+9); int i = r;` warned
`implicit conversion from 'small' (aka '__ob_trap std::uint8_t') to 'int'
during assignment discards overflow behavior
[-Wimplicit-overflow-behavior-conversion-assignment]` and the binary
exited 133. The compiler's own vendor has therefore shipped a "this
value just left its discipline" warning for a type-level integer
discipline. That is the same shape as a verbs escape stop, but it covers
only implicit conversions. An explicit cast is the sanctioned way out.

**Field adoption.** Kees Cook posted "[PATCH 0/5] Introduce Overflow
Behavior Types" to LKML on 2026-03-31, with patches by Justin Stitt. It
calls the series "the spiritual successor to the 'Mitigating unexpected
arithmetic overflow' thread from 2024", and it adopts OBTs *per type*:
"we can start converting variables (and types) that are never supposed
to overflow/underflow to these new types"
(https://lkml.iu.edu/hypermail/linux/kernel/2603.3/15602.html;
https://lwn.net/Articles/1065628/; both accessed 2026-11-23). Merge
status was not confirmed. The kernel's answer to Torvalds' objection
(§4.4) is the one this lane reached: put the stop on a declared type,
not on all integers.

**Habit role.**
- *Seeded-fault oracle:* compile seeded code with `__ob_trap` typedefs or
  `-fsanitize=integer,implicit-conversion` and confirm the fault fires at
  runtime.
- *Not a construct for this habit:* the bound is the representation's
  bound, not a declared range, and it is an experimental `-cc1` flag. The
  idiom list is itself evidence: LLVM had to carve idioms out of an overflow
  checker because plain-integer overflow findings are noisy (§4.4).

### 1.8 A minimal owned C++26 bounded integer: what the agent sees (probe)

**What was probed.** A 40-line `Bounded<Lo,Hi>`, compiled `-fsyntax-only`
against the pinned Clang and libc++. It has:
- a `consteval` constructor from `int64_t`;
- `static make(v) -> std::optional<Bounded>`;
- `template<std::integral I> operator=(I) = delete("assign a Bounded, or use
  Bounded::make(raw) and handle nullopt")`;
- a widening conversion constrained by `requires(L2 <= Lo && Hi <= H2)`;
- `operator+` returning `Bounded<A+C, B+D>`.

| Case | Code | Diagnostic (first lines) |
|---|---|---|
| 1 | `Percent p = 101;` | `call to consteval function 'Bounded<0, 100>::Bounded' is not a constant expression` / `note: subexpression not valid in a constant expression` |
| 1′ | same, with the check calling a non-constexpr function named `literal_is_outside_the_declared_range` | `note: non-constexpr function 'literal_is_outside_the_declared_range' cannot be used in a constant expression` / `note: in call to 'Bounded(101)'` |
| 2 | `p = argc;` | `overload resolution selected deleted operator '=': assign a Bounded, or use Bounded::make(raw) and handle nullopt` |
| 3 | `Bounded<0,50> h = p;` | `no viable conversion from 'Bounded<[...], 100>' to 'Bounded<[...], 50>'` … `note: because '100LL <= 50LL' (100 <= 50) evaluated to false` |
| 4 | `Percent q = p + p;` | `no viable conversion from 'Bounded<[...], 200>' to 'Bounded<[...], 100>'` … `because '200LL <= 100LL'` |
| 5 | `*Percent::make(argc)`; `Bounded<0,200> s = p + p;` | compiles; 0.18 s user for the TU |

**Findings.**
- A `throw "message"` in a consteval constructor does *not* surface its
  text (case 1). A reason-named non-constexpr function does (case 1′).
- `= delete("reason")` (P2573, Clang 19+) puts the fix in the error line.
- Case 4 is the loop-accumulator problem in miniature. The agent must write
  `Percent::make((p+p).get())` and handle `nullopt`, or the construct must
  offer named `checked_add`/`saturating_add` that keep the type.

### 1.9 C++26 contracts (P2900R14)

**What it is.** `pre(…)`, `post(r: …)` and `contract_assert(…)`. There are
four evaluation semantics: ignore, observe, enforce and quick-enforce. "It is
implementation-defined which evaluation semantic is used for any given
evaluation" (P2900R14, 2025-02-13, proposed wording [basic.contract.eval]
paragraph 2; the prose equivalent is §3.5.5 "Selection of Semantics"; file
`papers/wg21-p2900r14-contracts-for-cpp.pdf`). A range is therefore a
statement about one call boundary, which may be unchecked, and is not
carried by the value.

**Status.**
- **Clang:** "Contracts P2900R14 — No" (https://clang.llvm.org/cxx_status.html,
  accessed 2026-11-23). Pinned 23.1.2: `clang++: error: unknown argument:
  '-fcontracts'`. `__cpp_contracts` is undefined.
- **GCC:** 16 lists P2900R14 as supported, with `__cpp_contracts >= 202502L`
  (https://gcc.gnu.org/projects/cxx-status.html, accessed 2026-11-23).
- **Clang branch:** a contracts branch exists
  (efcs `contracts-review-20261009`) but cannot be merged with the
  reflection fork (cpp26-clang-toolchain §2-§3).

**Habit role.**
- *Today:* none on the pinned toolchain.
- *Later:* a `pre(x >= 0 && x < N)` is machine-readable evidence that the
  parameter should have been a bounded type. That would make it a nudge
  input, and possibly the way an agent states a range before adopting the
  construct.
- Contracts cannot be a stop for this habit, because `ignore` is a
  conforming semantic.

### 1.10 Chromium `base/numerics` (added in the check)

**What it is.** It describes itself as "a dependency-free, header-only
library of templates"
(https://chromium.googlesource.com/chromium/src/+/HEAD/base/numerics/README.md,
accessed 2026-11-23). It is the most widely deployed C++ example of
named numeric semantics:
- `CheckedNumeric<T>` keeps a sticky invalid state. "Attempting to extract
  the value from a variable in an invalid state will trigger a check/trap
  condition" (`ValueOrDie()`). `AssignIfValid()` and `ValueOrDefault()`
  are the handled exits.
- `ClampedNumeric<T>` saturates on every operation.
- `StrictNumeric<T>` / `strict_cast<>()` make a narrowing that cannot hold
  the source's full range a compile error.
- `checked_cast<>()` crashes at runtime on loss, and gives a compile error
  when that is detectable at compile time. `saturated_cast<>()` clamps.

**How it bears on the habit.** Every semantic has a name at the call
site, so "silently saturates where a stop is expected" becomes an
owned-name match (`saturated_cast`, `ClampedNumeric`). Like KINT's NaN
integers (§4.5), the sticky-invalid design is an arithmetic option the
lane's open question 1 did not list: allow out-of-range intermediates and
stop at extraction. The ranges are representation ranges only, not
declared `[Lo, Hi]`.

**Evidence.** No precision or ergonomics study was found. Its scale of use
inside Chromium was not measured here.

**Costs.** It is a reference for technique; adopting it would need
operator discussion.

### 1.11 Named saturating and checked arithmetic in the pinned toolchain (added in the check)

- **C++26 saturation arithmetic.** P0543R3 has been "Complete" in libc++
  since 18. P4052R0 (2026-03, Croydon) renamed the functions, and that
  rename is complete in 23
  (`libcxx/docs/Status/Cxx26Papers.csv:30, 211`). The pinned names are
  `std::saturating_add/sub/mul/div` and `std::saturating_cast`
  (`libcxx/include/__numeric/saturation_arithmetic.h:124-145`;
  `__cpp_lib_saturation_arithmetic 202603L`). Probe:
  `static_assert(std::saturating_add<std::uint8_t>(250,10)==255)`
  compiles on 23.1.2.
- **C23 checked arithmetic.** `<stdckdint.h>` `ckd_add` compiles in C++
  mode with Clang's own header (`clang/lib/Headers/stdckdint.h`; probed).
  The libc++ entry for P3370R1 (C23 headers in C++26) is still blank
  (`Cxx26Papers.csv:92`).

**Habit role.** These are standard, dependency-free primitives a verbs
C++ construct can build its named `checked_`/`saturating_` methods on.
`saturating_*` is a fixed set of standard names, so a stop or nudge that
says "saturation where the construct declared stop semantics" can be an
exact name match.

---

## 2. Rust constructs

### 2.1 deranged (jhpratt; 0.5.9, 2026-10-13, aeb03a4)

**What it is.** `RangedU8<const MIN: u8, const MAX: u8>` and siblings for
every integer width. Source: https://docs.rs/deranged/latest/deranged/struct.RangedU8.html,
accessed 2026-11-23.
- **Ingress:**
  - `new(v) -> Option<Self>`;
  - `new_static::<V>()`, range-checked at compile time;
  - `new_saturating(v)`;
  - `unsafe fn new_unchecked`.
- **Range changes:** `expand::<A,B>()` fails to compile unless the new range
  is a superset. `narrow::<A,B>() -> Option<_>` fails to compile unless it
  is a subset.
- **Arithmetic** is named methods only: `checked_*`, `saturating_*`,
  `wrapping_*`, `unsafe unchecked_*`, and `rem` with a const divisor
  returning `RangedU8<0, RHS>`. No `Add`/`Sub`/`Mul` impls are listed.
- **Egress:** `get()` emits an optimizer range hint.
- **Source check (aeb03a4, `deranged/src/lib.rs`, read in the check).**
  No `core::ops` trait is implemented; apart from formatting and derives,
  the trait impls are `FromStr` on the ranged types and `Default` on the
  optional type. `MIN > MAX` is rejected by `const { assert!(MIN <= MAX); }`
  inside every method (e.g. lines 305, 322). So a bad range fails when the
  first call is monomorphized, not at the type's declaration. The field is
  wrapped in `Unsafe<T>` (`deranged/src/unsafe_wrapper.rs:4-18`, a
  `pub(crate) const unsafe fn new`), so even code inside the crate needs
  `unsafe` to construct one. The arithmetic methods take a raw `$internal`
  right-hand side (`checked_add(self, rhs: $internal)`, line 509). The
  unsafe doors are `new_unchecked`, `narrow_unchecked` and the
  `unchecked_*` arithmetic methods.

**Habit role.**
- *Stops:* the compiler gives them: private field, `unsafe` door,
  compile-time `expand`/`narrow` checks.
- *Arithmetic:* the semantic is chosen at every call site by name. That is
  the clearest "no silent wrap or saturate" design studied. The cost is
  verbosity.

**Evidence of use.**
- crates.io, 2026-11-23: 789,779,153 downloads, but only 26 reverse
  dependencies.
- The main one is `time` 0.3.x (`deranged ^0.5.2`).
- So a bounded-integer crate can be mature and ubiquitous through one
  dependent while almost nobody adopts it directly. No ergonomics study
  exists.

### 2.2 bounded-integer (Kestrer; 0.6.2, cbf716e)

**What it is.**
- `BoundedU8<MIN, MAX>` const-generic types, plus a `bounded_integer!` macro
  that emits a struct or an *enum* with niche optimization
  (https://docs.rs/bounded-integer/latest/bounded_integer/, accessed
  2026-11-23).
- `new -> Option`, `unsafe new_unchecked`, `new_saturating`, `checked_*`,
  `saturating_*`.
- **Operators are implemented and panic when out of range:**
  `.expect(concat!("Attempted to ", $desc, " out of range"))`
  (`src/unsafe_api.rs` ≈ line 1592 at cbf716e; also `pow`, `abs`,
  `div_euclid` at lines 379-409).

**Habit role.** This is the "stop at runtime, always" semantic. It works in
release builds too, unlike Rust's own `overflow-checks`.
- *Fuzzing:* an `arbitrary1` feature generates in-range values, which fits
  seeded-fault testing.

**Evidence.** 1.56 M downloads. No precision or ergonomics data.

### 2.3 ranged_integers (0.12.0)

**What it is.** `Ranged<MIN, MAX>` with result ranges computed by interval
arithmetic (`[1,6] + [1,6] = [2,12]`). Storage is the smallest layout, and
zero bytes when `MIN == MAX`. Division is rejected at compile time if the
divisor range includes 0. Source: https://docs.rs/ranged_integers, accessed
2026-11-23.

**Status.** It requires nightly `adt_const_params` and `generic_const_exprs`,
pinned to nightly-2026-08-17. In its own words it "causes ICEs on some Rust
toolchains and may once stop working". 15,829 downloads.

**Habit role.** It shows that bounded-integer's widening design is
reachable in Rust only on unstable features. It is not a candidate.

### 2.4 nutype (0.8.0, a3e70e2)

**What it is.** A proc macro: `#[nutype(sanitize(...), validate(greater_or_equal
= 18, less = 100, predicate = …), derive(...))] pub struct Age(u8);`.
- It generates `try_new` and a per-type error enum (`LessViolated`, …).
- "The generated code makes it impossible to instantiate a value without
  passing the checks. It works this way even with serde deserialization."
  Verified in source in the check: the macro emits the struct inside a
  generated `#[doc(hidden)] mod __nutype_<Name>__` and re-exports it with
  `use` (`nutype_macros/src/common/generate/mod.rs:97-111, 509-522` at
  a3e70e2). The tuple field is private to that generated module, so the
  user's defining module cannot touch it either.
- `new_unchecked` exists only behind a crate feature and is `unsafe`.
- Constructor visibility can be restricted.

Source: https://github.com/greyblake/nutype README, accessed 2026-11-23.

**Habit role.** Declarative refinement for *any* inner type, string
included. It is the Rust analogue of the old `Refined`. Its sanitizers
(`with = |raw| raw.clamp(0, 100)`) make clamping an explicit, declared
policy rather than a scattered call. 7.5 M downloads.

### 2.5 Rust pattern types (`u32 is 1..`)

**What it is.**
- `core::pat::pattern_type!(i32 is 1..)`, unstable feature `pattern_types`
  (`library/core/src/pat.rs`, rust-lang/rust master, accessed 2026-11-23).
- Core already uses it internally: the niche types behind `NonZero` are
  `struct $name(pattern_type!($int is $pat))`
  (`library/core/src/num/niche_types.rs:11-21`).

**Status.** Tracking issue #123646 is open (updated 2026-08-08). Only
"Implementation (#120131)" is checked. Still to do: "BLOCKER FOR ALL OF THE
BELOW: write a proposal to T-types and implement a subtyping experiment",
non-macro syntax, an RFC, and stabilization. The test suite constructs
values via `transmute`.

**Habit role.** None this round. If stabilized, it would be the strongest
native Rust realization (a range in the type, a layout niche, no wrapper). A
verbs Rust backend should keep its construct's surface close enough to swap
in later.

### 2.6 Flux (liquid types for Rust; flux-rs/flux 828d608, 2026-11-21)

**What it is.** Refinement types checked by an SMT-backed fixpoint solver.
Source: book in the repo, `book/src/tutorial/01-refinements.md`,
`book/src/guide/install.md`, `book/src/reference/manifest.md`, accessed
2026-11-23.
- **Syntax:** `#[spec(fn(n: i32) -> i32{v: 0 <= v && n <= v})]`, with
  indexed types like `i32[10]`.
- **Install:** "The only way to use Flux is to build it from source" with
  pinned nightly rustc. It requires the `liquid-fixpoint` binary and z3
  4.15+ (or cvc5) on `PATH`.
- **Manifest:** the `check-overflow` key defaults to `none` (other values:
  `lazy`, `strict-under`, `strict`). A `trusted` table and `ignore` table
  exempt files.
- **Config:** per-query fixpoint timeouts, default 30 s.

**Evidence.** Lehmann et al. (PLDI 2023, `papers/lehmann-2023-flux-liquid-
types-rust-pldi.pdf`): specifications half as long as Prusti, about 10×
faster, and no loop annotations (literature-core §7).

**Costs.** Three external binaries plus a nightly compiler. The verdict is
solver-dependent and has timeouts. Overflow is unchecked by default.

**Habit role.** A possible *optional* proof backend that could discharge
"this narrowing is in range" obligations. It is not a stop mechanism verbs
can own, and the no-hard-LLM-dependency rule is not the issue — the SMT and
toolchain burden is.

### 2.7 What the Rust language already gives the habit

- **Privacy plus `unsafe`** make the bypass set closed: `unsafe`
  constructors, `transmute`, and code in the defining module. The other
  half of a stop is `#![forbid(unsafe_code)]` or a lint that flags calls
  to `*_unchecked`.
- **Integer overflow** panics in debug and wraps in release unless the
  profile sets `overflow-checks = true`. Plain-integer overflow is therefore
  a configuration choice, not a type property.
- **`#[expect(clippy::lint, reason = "…")]`** reports `this lint expectation
  is unfulfilled` when the finding goes away (probed; the
  `unfulfilled_lint_expectations` lint is on by default). This is the
  stale-reason mechanism the brief names.
- **The reason is optional in rustc. Clippy can require it (added in the
  check).** `clippy::allow_attributes_without_reason` (restriction, since
  1.61) and `clippy::allow_attributes` (restriction, since 1.70; it flags
  `#[allow]` so that `#[expect]` is used instead) are in
  `clippy_lints/src/attrs/mod.rs:57, 80`. Probe output: "`expect`
  attribute without specifying a reason", "#[allow] attribute found",
  "`allow` attribute without specifying a reason". Together with
  `unfulfilled_lint_expectations`, that gives all of part (c) in stock
  Rust tooling: a required reason, no reasonless allow, and stale
  detection.
- **Stable std range types.** `std::num::NonZero<T>` is the only stable
  range-restricted integer in std (its niche is the pattern type of §2.5).
  `std::num::Wrapping<T>` and `Saturating<T>` name a semantics in the
  type.

---

## 3. Reference systems

### 3.1 Ada range subtypes and SPARK

**What it is.**
- `subtype Percent is Integer range 0 .. 100;`. Every assignment, conversion
  and parameter pass into the subtype carries a range check. Ada raises
  `Constraint_Error` at run time ("range check failed", "overflow check
  failed", "index check failed").
- GNATprove turns each check into a proof obligation. It reports
  `info: range check proved`, or `medium: range check might fail` with a
  counterexample ("C = 0 and X = 10 and X'Old = 0").

Sources: https://learn.adacore.com/courses/intro-to-spark/chapters/03_Proof_Of_Program_Integrity.html,
accessed 2026-11-23. At **Silver level**, the program "does not raise an
unexpected exception at run time". Proof "requires using sufficiently
precise types of variables", and code then compiles with `-gnatp` (checks
off) (https://docs.adacore.com/spark2014-docs/html/ug/en/source/silver_level.html,
accessed 2026-11-23).

**Way past with reason.** `pragma Annotate (GNATprove, False_Positive |
Intentional, "pattern", "reason")`.
- `False_Positive` means "the check cannot fail"; `Intentional` means "the
  check can fail but … is not … a bug".
- Exception to stale detection: "No such warning is emitted for a
  justification placed on a generic declaration, as the checks it
  justifies may arise in instances located in other units". A C++ reason
  placed in a template would face the same gap.
- The pattern matches the message text.
- Pragmas that "do not justify any check message are useless and result in
  a warning", an error under `--warnings=error`
  (https://docs.adacore.com/spark2014-docs/html/ug/en/source/how_to_use_gnatprove_in_a_team.html,
  accessed 2026-11-23).

This is the exact four-part shape verbs wants: finding, category, reason,
and stale detection.

**Evidence.** AdaCore says the first pass "may require a substantial effort
to resolve all false alarms, depending on the coding style". Provers'
limits "mostly show up on non-linear integer arithmetic … and floating-point
arithmetic". No vendor-neutral figure for the share of checks proved
automatically was found. A vendor post (AdaLang Analyzer 1.15.0) claims
76% of 15,043 checks on five SPARK projects for a different tool; it is not
used here.

**Lesson for verbs.** SPARK's split is the one verbs needs:
- the *type* states the range;
- the *dynamic semantics* checks it;
- a *prover* is optional extra strength.

The habit works in Ada without GNATprove, because the range check is the
language's default behaviour.

### 3.2 Liquid types and LiquidHaskell

**What it is.**
- Liquid Types (Rondon, Kawaguchi, Jhala, PLDI 2008; `papers/rondon-2008-
  liquid-types-pldi.pdf`) infer refinements as conjunctions from a *fixed
  qualifier set*, Houdini-style. Annotation fell from 31% of program text
  to under 1% (literature-core §7).
- LiquidHaskell writes `{-@ type Nat = {v:Int | v >= 0} @-}` in comments
  and checks with an SMT solver (Jhala & Vazou tutorial,
  `papers/jhala-vazou-2020-refinement-types-tutorial.pdf`).

**Agent and human ergonomics evidence.**
- Gamboa, Reese, Fonseca, Aldrich, "Usability Barriers for Liquid Types",
  PLDI 2025, doi:10.1145/3729327; file
  `papers/gamboa-2025-usability-barriers-liquid-types-pldi.pdf`. The study
  ran 19 participants and found nine barriers in three groups:
  - developer experience: unhelpful error messages, limited IDE support,
    thin learning resources, complex installation;
  - scalability;
  - understanding verification.
- "All of our Experienced Users reported challenges with LiquidHaskell
  error messages" (§4.7). Typing errors inside predicates were
  indistinguishable from verification failures, and messages showed
  internal variables.
- One practitioner reported that colleagues use liquid types only "as a
  lightweight verification tool with pre- and post-conditions" (§5).
- For LLM-written refinements, XO (Sakkas, Sahu, Ong, Jhala, ICSE 2025)
  had a fine-tuned 3B StarCoder generate LiquidHaskell refinement types
  "for up to 94% of the functions" in three packages, with the checker as
  oracle
  (https://conf.researchr.org/details/icse-2025/icse-2025-research-track/115/Neurosymbolic-Modular-Refinement-Type-Inference,
  accessed 2026-11-23). This is evidence that a checker-in-the-loop lets
  models write refinements. It says nothing about the precision of nudges.

**Lesson for verbs.** A fixed, small vocabulary (ranges, non-zero,
non-empty) is what makes refinements inferable and their messages legible.
The verbs construct should expose ranges only, not arbitrary predicates,
for this habit.

---

## 4. Detecting values that should have been bounded

### 4.1 Corpus census (six projects, regex, non-test, non-vendored)

**Method.** Six tarballs from `quarantine/_archives/corpus-2026-10-18/` were
extracted to `context/scratch-bounded/` and deleted afterwards:
- bitcoin 924f4c4, rocksdb 54732b0, fprime 1d70340, JoltPhysics 01adafb,
  OpenTTD 364d9b1, osrm-backend f2147ea. (Check note: the rocksdb line
  citations below resolve in the corpus's other snapshot,
  `facebook__rocksdb-6a4361504171`, not in 54732b0, which is the one
  `context/corpus/fetched.tsv` lists. Which snapshot the rocksdb counts
  came from is therefore uncertain; the other five projects' cited lines
  were spot-checked and match.)
- vendored directories excluded; comments stripped;
- test paths split out (imperfectly: OSRM's `unit_tests/` slipped through
  the first pass).

The counts are first-order. Regex cannot tell types apart.

| project | kLOC | clamp calls | nested min/max | assert with two range compares | range guards (named) | `static_cast` to ≤16-bit | to 32-bit/int/float | numeric_limits compares | unit-suffixed scalar decls | deg↔rad conv | ×/÷ 1e3/1e6/1e9 | `std::chrono::` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bitcoin | 220 | 2 | 0 | 33 | 107 | 31 | 75 | 46 | 100 | 0 | 31 | 498 |
| rocksdb | 368 | 0 | 2 | 92 | 102 | 159 | 835 | 25 | 410 | 0 | 143 | 145 |
| JoltPhysics | 137 | 2 | 17 | 56 | 94 | 0 | 10 | 0 | 37 | 24 | 1 | 17 |
| fprime | 117 | 0 | 0 | 37 | 41 | 4 | 24 | 76 | 0 | 0 | 27 | 5 |
| OpenTTD | 385 | 5 | 9 | 70 | 164 | 165 | 182 | 3 | 15 | 0 | 20 | 197 |
| osrm-backend | 113 | 9 | 4 | 21 | 83 | 40 | 198 | 22 | 15 | 12 | 7 | 39 |

**Observations.**
- `std::clamp` is rare (0-9 per project), so a clamp nudge would seldom
  fire.
- Range guards and range asserts are common (41-164 per project).
- Narrowing `static_cast`s are very common in rocksdb (994) and OpenTTD
  (347).

**Repeated-guard nudge, hand-judged.** First pass: the same variable or
member name range-guarded (`x <op> A &&/|| x <op> B`) at ≥3 non-test sites.
That gave 44 names. Each was judged:

| class | count | examples |
|---|---|---|
| A. genuine fixed-domain value (bounded-type candidate) | 9 (20%) | fprime `portNum`/`queueIndex`/`queueNum`/`addr`/`index` (`FW_ASSERT(portNum >= 0 && portNum < COM_PORT_COUNT…)`, `Svc/ComQueue/ComQueue.cpp:234`); OSRM `latitude`/`longitude`; Jolt `fraction` (`JPH_ASSERT(fraction >= 0.0f && fraction <= 1.0f)`, `Jolt/Skeleton/SkeletalAnimation.cpp:101`) |
| D. enum range check (enum habit, not this one) | 5 (11%) | rocksdb `pri` (`assert(pri >= Priority::BOTTOM && pri <= Priority::HIGH)` ×14: ×7 in `env/env_posix.cc`, ×7 in `port/win/env_win.cc`; first at `env_posix.cc:350` in 6a4361504171, `:365` at 54732b0) |
| C. dispatch over sub-ranges of one value | 9 (20%) | OpenTTD `key`, `widget`, `variable`; bitcoin `opcode`; OSRM `angle` buckets (`turn_instruction.hpp:217-221`) |
| B. dynamic bound (container size, rectangle, scroll window) | 14 (32%) | rocksdb `ret >= sz`; OpenTTD `pt.y >= wi_rect.top`; Jolt `strand_idx` |
| mixed or name collision | 6 (14%) | rocksdb `value` (different flags); `lat`/`lon` (bbox and domain) |
| regex false (`e << "K"_mst`) | 1 | bitcoin miniscript |

Second pass: both bounds compile-time constants (literal, ALL_CAPS,
`kName`, `Ns::Name`), and the *same* (name, low, high) at ≥2 sites. That
gave 29 groups:
- **A: 13 (45%).** fprime ×3; OSRM `bearing` 0..360 and `range` 0..180;
  bitcoin `nbits` 0..64 and `opcode` OP_1..OP_16; rocksdb `value`
  0..kMaxValue; Jolt `fraction`; OpenTTD `prod_level`, `uniqueid`
  0..UINT16_MAX, `num_platforms`/`platform_length` 0..0xFF.
- **D: 5 (17%).**
- **C: 11 (38%).** Mostly OpenTTD character and NewGRF-variable classes.

Precision for this habit is about 45%, and about 62% if enum-range hits
are routed to the enum habit. That sits in the 46-62% band the enum
heuristic reached (`papers/2026-10-17-enum-candidate-redesign.md`).

**What an AST version would add.**
- Match the same *declaration* (field, parameter) rather than the same
  name, which removes collisions.
- Exclude a value tested against ≥2 *different* constant sub-ranges in one
  function. That is dispatch: OpenTTD `variable` 0x60..0x65 and 0x8C..0xEC
  at `newgrf_station.cpp:443,467`.

Neither was built or measured here.

**Units in plain scalars.** rocksdb declares 410 unit-suffixed scalars
(`_micros`, `_ms`, `_sec`). It has 26 non-test files that use ≥2 time
units and a hand-written ×1000/×1e6, e.g.:
- `delete_obsolete_files_period_micros(6ULL * 60 * 60 * 1000000)`
  (`options/db_options.cc:973` in rocksdb 6a4361504171; at the stated
  54732b0 the constant is at `include/rocksdb/options.h:917`);
- `uint64_t{FLAGS_gather_stats_sleep_ms} * 1000`
  (`cache/cache_bench_tool.cc:449` in 6a4361504171; `:620` at 54732b0).

This is despite 112 `std::chrono` uses in the same tree. Jolt and OSRM
convert degrees↔radians by hand (24 and 12 sites). A suffix-plus-scale-
factor nudge toward `std::chrono` for time is cheap. Its precision was not
measured.

### 4.2 clang-tidy on real code (JoltPhysics, 35 files plus headers)

**Run.** `clang-tidy` 23.1.2 with `bugprone-narrowing-conversions`,
`bugprone-implicit-widening-of-multiplication-result`,
`bugprone-too-small-loop-variable`, `readability-magic-numbers`,
`readability-use-std-min-max` and `bugprone-misplaced-widening-cast`, over
`Jolt/Physics/{Constraints,Character,Vehicle}/*.cpp` (`-I<root> -std=c++20`).
It took 15.1 s wall and gave 477 warnings.

- **`bugprone-narrowing-conversions`: 13 findings, 0 bugs.** Every one is a
  value the author knows is small:
  - `CountTrailingZeros(…)` ≤ 32 returned as `int` (`Math/Vec4.inl:939`);
  - a sign-bit count ≤ 4 (`Math/UVec4.inl:619`);
  - three findings in `Color::operator*(float)` (`Core/Color.h:41`). The
    flagged conversion is the `uint8` channel, promoted to `int`, then
    converted to `float` ("narrowing conversion from 'int' to 'float'"),
    which is exact for every value 0..255. Here the source type (`uint8`)
    already carried the range and the check still fired, because integer
    promotion discarded it. (The earlier text tied these findings to the
    "[0, 1]" intensity comment, which concerns the other operand.);
  - a track index < 2 (`Vehicle/TrackedVehicleController.cpp:178`);
  - tooth counts converted to `float` (`RackAndPinionConstraint.h:32`).

  A bounded type on the source would let the checker prove each one
  lossless and stay silent. That is the link between the two halves of
  this lane.
- **`bugprone-implicit-widening-of-multiplication-result`: 9.** Most are SIMD
  gather offsets (`Math/UVec4.inl:148-151`). One is a plausible true
  overflow on large matrices: `mElements.resize(inRows * inCols)` with
  `uint` operands (`Math/DynMatrix.h:15`).
- **`readability-magic-numbers`: 455** (0.5f ×43, 2.0f ×40, 1.0e-6f ×24).
  These are noise for this habit. A "magic-number limit" signal must be
  narrower: a constant that appears as a *bound in a range guard* (§4.1),
  not any literal.

**The compiler's own range awareness (added in the check).** Clang's
`-Wimplicit-int-conversion` (in `-Wconversion`) computes an
`IntRange` for each expression. That is a bit width plus a
non-negative flag, not an interval (`clang/lib/Sema/SemaChecking.cpp:11645`,
`TryGetExprRange` at :11875). Probe on 23.1.2, each function returning
`std::uint8_t` from `unsigned x`:

| body | warns? |
|---|---|
| `return x & 0xFF;` | no |
| `return x % 200;` | no |
| `return x;` | yes |
| `[[assume(x < 256)]]; return x;` | yes |
| `if (x < 256) return x;` | yes |

`bool g(uint8_t v) { return v > 300; }` gets
`-Wtautological-constant-out-of-range-compare` ("always false"), which
uses the type's range. So the compiler already proves narrowings lossless
from the shape of a single expression. It ignores dominating guards and
`[[assume]]`, and it knows nothing of a user type's declared bounds. A
range-aware narrowing check (open question 4) would extend this
machinery; it would not start from nothing.

**clang-tidy option evidence.** `narrowing-conversions`' own docs suggest
ignoring `size_t;ptrdiff_t;size_type;difference_type` "for a legacy
codebase", and its `WarnWithinTemplateInstantiation` defaults to false
(`narrowing-conversions.rst`, Options). The check's authors expected
precision trouble on index types.

### 4.3 clippy

Probed on a 12-function crate with the repo toolchain:

| lint | group (default level) | fires on |
|---|---|---|
| `cast_possible_truncation`, `cast_sign_loss`, `cast_possible_wrap` | pedantic (allow) | `x as u32` from u64; i32→u32; u32→i32 |
| `manual_clamp` | default (warn) | `if x<0 {0} else if x>100 {100} else {x}` and `x.max(0).min(100)` |
| `manual_range_contains` | default (warn) | `x >= 3 && x < 8` |
| `arithmetic_side_effects` | restriction | `x + y` on `u8` |
| `indexing_slicing` | restriction | `v[i]` |
| `as_conversions` | restriction | every `as` |
| `unfulfilled_lint_expectations` | rustc default (warn) | a stale `#[expect(clippy::cast_possible_truncation, reason=…)]` |

- `cast_possible_truncation`'s documentation calls truncation "expected
  behavior, so the cast is `Allow` by default" and says the lint "can be
  activated to help assess where additional checks could be beneficial".
  `cast_sign_loss`'s says to activate it "as a one-time check"
  (`clippy_lints/src/casts/mod.rs:269-276, 403-404`, quarantine
  rust-clippy 0.1.99). The clippy maintainers treat these as audit lints,
  not everyday ones.
- `manual_clamp` (complexity group) documents two hazards of its own
  suggestion: NaN propagation, and `clamp` panicking if `max < min`
  (`manual_clamp.rs:35-40`; the probe prints "clamp will panic if max <
  min"). It fires only when both bounds are compile-time constants.
- `struct_excessive_bools` (pedantic) is the brief's model of an exact rule.
  No cast lint is that exact.
- **`checked_conversions` (pedantic, added in the check)** flags a
  hand-written bounds check before a cast and suggests `try_from`
  (`clippy_lints/src/checked_conversions.rs:12-35`). Probe: `if x <=
  u32::MAX as u64 { Some(x as u32) }` gives "checked cast can be
  simplified". This is the clippy instance of "validated by hand". It only
  recognizes checks against the target type's `MIN`/`MAX`, so it finds
  representation-range validation, never a domain range such as 0..=100.

### 4.4 UBSan and the plain-integer overflow evidence

**The checks.** `-fsanitize=integer` enables signed and unsigned overflow,
shift, divide-by-zero, implicit signed/unsigned truncation and implicit
sign change. `-fsanitize=implicit-conversion` adds bit-field conversions
(`UndefinedBehaviorSanitizer.md:222-243`).

**Evidence that plain-integer overflow findings are mostly not bugs.**
- Dietz, Li, Regehr, Adve, "Understanding Integer Overflow in C/C++", ICSE
  2012 (`papers/dietz-2012-understanding-integer-overflow-icse.pdf`):
  "intentional uses of wraparound behaviors are more common than is widely
  believed; for example, there are over 200 distinct locations in the SPEC
  CINT2000 benchmarks where overflow occurs". Intentional cases include
  hashing, RNGs and computing maxima (Table III).
- Clang's overflow-pattern exclusions exist because those idioms are
  "accepted and pervasive" (§1.7).
- Dietz et al.'s own summary (§IV-C): 219 static overflow sources in eight
  of the 12 SPEC CINT2000 benchmarks, most commonly hashing (128), overflow
  checks that need `-fwrapv` (37), bit manipulation (25) and random number
  generation (6); "the vast majority of overflows found (both unsigned and
  signed) were not bugs".
- Linux kernel, 2024: "False positive warnings make real warnings worthless."
  "Wrap-around is not only well-defined, it's *useful*, and it's *used*." "I
  do think implicit integer casts are dangerous. Often *more* dangerous than
  arithmetic overflow" (Linus Torvalds, 2024-05-08, LKML "[RFC] Mitigating
  unexpected arithmetic overflow",
  https://lkml.iu.edu/hypermail/linux/kernel/2405.1/01278.html, accessed
  2026-11-23). See also LWN https://lwn.net/Articles/959189 (Jan 2024).

**Implications.**
- A stop on *plain-integer* overflow would be wrong often.
- A stop on overflow *inside a declared bounded type* is a different claim:
  the author declared that wraparound is not the semantics.
- Implicit truncation is the higher-value plain-integer signal, per the
  kernel maintainer and per the Jolt finding that truncations are where
  range knowledge is missing.

### 4.5 KINT: range annotations as the way to quiet an integer checker (added in the check)

Wang, Chen, Jia, Zeldovich, Kaashoek, "Improving Integer Security for
Systems with KINT", OSDI 2012
(`papers/wang-2012-kint-integer-security-osdi.pdf`, from
https://css.csail.mit.edu/6.566/2018/readings/kint.pdf, accessed
2026-11-23). This is the closest published precedent for the claim that
*declared ranges are what silence integer findings*.
- **Mechanism.** LLVM-based static analysis: per-function constraints,
  then whole-program range analysis and taint analysis, then an SMT
  solver. Programmers add `__range(min, max)` annotations on variables,
  fields, arguments and returns, and `kint_assume(...)` for relations
  (§5.2, §6.3), e.g. `static u32 ordernum = 1 __range(0, 0xFFFFF);`.
- **Precision without declared ranges.** The whole Linux kernel gave
  125,172 warnings. Sink filtering left 741 allocation-size reports from
  untrusted input; five hours of review found 11 exploitable bugs (§6.2).
  On one mature module (Unix domain sockets), 42 of 43 reports were false
  (§6.3).
- **Precision with declared ranges.** 23 annotations removed every false
  report in that module, and "about half of them apply to common Linux
  headers, and thus are reusable" (§6.3).
- **Loop accumulators again.** Of 37 known kernel CVEs it missed one,
  "an addition overflow that happens in an accumulation loop", because
  it unrolls loops once (§6.2).
- **NaN integers (§7).** The paper proposes an overflow-checked integer
  family whose out-of-range value "enters and stays in a special NaN
  state", at 1-3 cycles per check. This is the same sticky-invalid
  semantics as Chromium's `CheckedNumeric` (§1.10).

**For verbs.** KINT measured the trade this lane proposes. A range-blind
integer checker is mostly false findings (42/43). A small set of declared
ranges, many of them shared, removes them. In verbs the declared range
lives in the bounded type, not in a checker-only annotation.

### 4.6 CodeQL's own precision labels for "should have been bounded" queries (added in the check)

The CodeQL C++ queries in quarantine carry author-assigned `@precision`
metadata. These are labels, not measurements, but they show where the
authors expect noise:

| query | what it flags | `@precision` |
|---|---|---|
| `Security/CWE/CWE-129/ImproperArrayIndexValidation.ql` | "Unclear validation of array index" (index validated by hand, or not) | low |
| `Security/CWE/CWE-190/ArithmeticTainted.ql` | user-controlled data in arithmetic | low |
| `Security/CWE/CWE-190/IntegerOverflowTainted.ql` | potential overflow on user-controlled data | low |
| `Security/CWE/CWE-190/ArithmeticUncontrolled.ql` | uncontrolled (e.g. random) data in arithmetic | high |
| `Security/CWE/CWE-190/ComparisonWithWiderType.ql` | narrow loop variable compared with wider bound | high |

(`codeql/cpp/ql/src/…`, quarantine.) The high-precision one is a type
mismatch, the same shape as clang-tidy's `bugprone-too-small-loop-variable`.
The hand-validated-index query is labelled low. CodeQL also ships a C++
interval range analysis library (`cpp/ql/lib/semmle/code/cpp/rangeanalysis/`)
as a reference for a range-aware check.

---

## 5. Misuse of a bounded type, and what can be stopped on strong evidence

### 5.1 Misuse catalogue

| misuse | C++ | Rust | evidence strength |
|---|---|---|---|
| out-of-range literal | consteval ctor rejects (§1.8) | `new_static`/`const_new` rejects | compile error, exact |
| raw runtime int into the type | deleted `operator=` / no implicit ctor | no `From<u8>`; only `new -> Option` | compile error, exact |
| narrowing between ranges without a check | constrained conversion absent | `narrow` returns `Option`; `expand` checked | compile error, exact |
| calling the unchecked door | named function (`assume_in_range`, `unsafe_from`) | `unsafe { new_unchecked }` | exact by name; a stop with reason, like `unsafe` review |
| touching the public storage field | `m_value`, `numerical_value_is_an_implementation_detail_` | impossible outside the defining module | exact by name in C++ |
| `get()` then narrowing `static_cast`/`as` then re-`make` | expressible | expressible | the cast is already a narrowing finding; the re-`make` is fallible, so not a bypass |
| arithmetic that silently wraps or saturates where a stop is expected | a policy choice in the construct (§1.1-1.3) | `wrapping_*`/`saturating_*` named, or operators panic (Kestrer) | exact *if* the construct offers no unnamed wrapping |
| `get()` arithmetic on raw values, then `make(...).value()` / `*make(...)` | expressible; unchecked `optional` deref is UB unless hardened | `.unwrap()` panics, so it is a stop at runtime | nudge at most; `*make(x)` in C++ is the a15 case from the tribunals (escape-allowlist §3) |
| memcpy / reinterpret / union / bit_cast over the object | the escape-check domain | needs `unsafe` | C++: open-ended (§5.3); Rust: closed |

**Strong-evidence stops for this habit.**
- In both languages:
  - out-of-range literals;
  - raw-int ingress;
  - unchecked inter-range narrowing;
  - named unchecked doors;
  - touching the storage field by name.
- In Rust, also any `unsafe` that produces the type.

Every one is either a compile error the construct produces itself, or a
match on a name the construct owns. No heuristics are involved.

### 5.2 Ingress patterns that look like bypasses but are fine

- `get()` for egress (printing, hashing, passing to C APIs) is not a
  bypass.
- `make(x)` with a handled `nullopt` is the intended door.
- A reviewed `unsafe`/unchecked call with a recorded reason is the way
  past.

### 5.3 The escape-check lesson (C++)

The old design tried to make a soundness claim about `Bounded`. It needed a
checker for every way C++ can write an object's bytes.
- v1 was an AST allowlist: zero false escapes on seven programs, and every
  known counterexample caught (`papers/2026-10-17-escape-allowlist.md` §3).
- External reviewers then broke it six ways (F02-F06, F12): `const_cast` of
  a const byte view, `as_writable_bytes` inside libc++, pointer→integer,
  macro-name trust, attribution, and partial `memcpy`.
- v2 (provenance-as-type) closed those, and its list was "closable from the
  standard's text" (`2026-10-17-escape-allowlist-v2.md` §4).
- Round 2 found four more misses. Round 3 found nine, each confirmed by a
  forge to 7: `strtol` `endptr`, an exempted `memcpy`, a size multiple
  spanning siblings, `dynamic_pointer_cast<void>` missing from the "closed"
  list (`journal/2026-10-17-preliminaries.md`, 2026-10-18 table).
- The journal's own diagnosis: "In three rounds every confirmed miss …
  came through one of the two exemptions or through a list declared closed
  by argument."
- The libc++ scan then found "a class that no list closes": generic code
  converting `E*` to `void*` for the caller (`vector<void*>::emplace_back(&e)`).
  Eight programs forged 7 with zero findings (bead verbs-g5w, now in
  WORK.md).
- The prototype had also been parsing the wrong libc++.

**For this habit.** Bypass detection by representation in C++ does not
converge at a cost verbs should pay. The stops worth owning are the ones
in §5.1 that are compile errors or owned-name matches. Representation
attacks go to the UB boundary: sanitizers, hardening,
`-Werror=uninitialized`. In Rust the same boundary is `unsafe`, which the
language already marks.

---

## 6. Seeded faults for this habit (what the corpus can test)

These are fault shapes, not a design. Each was checked against the
mechanisms that would catch it.
- **Remove the construct.** Replace a bounded parameter or field with its
  raw integer, then delete one of the guard sites. Expected: the
  repeated-guard nudge or narrowing nudge fires at the remaining sites.
  Measurable on fprime `portNum` and OSRM `latitude`.
- **Off-by-one on a declared bound** (`Bounded<0,100>` → `<0,101>`). This is
  caught only by a runtime oracle or a test, not by a type check.
- **Swap the arithmetic semantic** (`checked_add` → `wrapping_add`, or a
  saturate policy where a stop was declared). Expected: an owned-name stop
  if wrapping requires a named, reasoned call.
- **Insert a narrowing `static_cast`/`as` of `get()`.** Expected:
  narrowing nudge.
- **Insert `*make(raw)` / `.unwrap()` without handling.** Expected: a
  nudge in C++; in Rust, `clippy::unwrap_used` (restriction).
- **Runtime confirmation.** Compile seeded TUs with `__ob_trap` typedefs or
  `-fsanitize=integer,implicit-conversion` to confirm a seeded overflow or
  truncation is real (§1.7). This mirrors how the escape lane confirmed
  forges at 7 before scoring the detector.

---

## What this means for verbs

Options this lane opens, ranked.

1. **A Rust bounded construct whose stops are the language's own.**
   - Use a const-generic `Bounded<MIN, MAX>` shaped like deranged:
     - `new -> Option`;
     - compile-time literal construction;
     - compile-checked `expand`/`narrow`;
     - named `checked_`/`saturating_`/`wrapping_` arithmetic;
     - an `unsafe` unchecked door.
   - Stops come from privacy and `unsafe`. The way past is
     `#[expect(…, reason)]`, whose staleness rustc already reports.
   - *Reason:* the bypass set is closed by the language, so the stop rate
     is exact. It is little machinery to own, with no nightly needed. It
     can later be re-based on pattern types without changing call sites.
   - *Cost:* verbose arithmetic, and nobody adopts such crates directly
     (deranged has 26 reverse dependencies).
2. **A C++ bounded construct that puts its stops in the compiler and its
   reasons in the diagnostics.**
   - Use `consteval` literal ingress with a reason-named failure, fallible
     `make`, `= delete("reason")` for raw ingress, and concept-constrained
     widening (§1.8).
   - Use mp-units' `unsatisfied<"…">` technique for multi-clause reasons.
   - Make bypass doors owned names that a lint matches exactly.
   - Make no representation-soundness claim.
   - *Reason:* every stop is a compile error the agent already reads, the
     machinery is small, and it avoids the escape-check chase.
   - *Cost:* the arithmetic semantic must be chosen (open question 1), and
     diagnostics for template failures stay long.
3. **Narrowing-conversion findings as the main "should be bounded" nudge,
   and the bounded type as what silences them.**
   - Use clang-tidy `bugprone-narrowing-conversions` and clippy `cast_*`.
   - When the source is a bounded type whose range fits the target, the
     finding should not fire. This needs verbs-owned logic or a wrapper
     check; neither existing lint knows about ranges.
   - *Reason:* the Jolt run shows narrowing findings are exactly where
     range knowledge is missing. The kernel maintainers call truncation the
     higher-risk plain-integer event.
   - *Cost:* the raw lints are audit-grade (pedantic in clippy). As nudges
     they need the reason-at-site way past, or agents will drown.
4. **A repeated-constant-range-guard nudge (AST-based).** Same declaration,
   same constant bounds, ≥2 sites, excluding dispatch over multiple
   sub-ranges.
   - *Reason:* it finds the fprime/OSRM/Jolt cases that are the habit's
     target.
   - *Cost:* measured regex precision is about 45%, so it can only ever be
     a nudge. Enum-range hits must route to the enum habit. It shares the
     precision ceiling the enum heuristic hit.
5. **Time-unit nudge toward `std::chrono` / `std::time::Duration`.**
   Trigger: suffix-named scalars plus a literal ×1e3/1e6 in the same
   expression.
   - *Reason:* cheap, and the replacement already exists in the standard
     library. rocksdb shows the pattern at scale.
   - *Cost:* precision unmeasured. Full units à la mp-units are a separate,
     larger habit.
6. **Runtime oracles for seeded-fault testing:** Clang `__ob_trap`,
   `-fsanitize=integer,implicit-conversion`, and Rust `overflow-checks`.
   - *Reason:* they confirm that a seeded fault is real before scoring a
     guard.
   - *Cost:* `__ob_trap` is an experimental `-cc1` flag.
7. **Proof backends (Flux, a SPARK-like prover, contracts): defer.**
   - *Reason:* SMT and nightly toolchain burden, overflow unchecked by
     default in Flux, contracts absent from Clang, pattern types without an
     RFC.
   - Revisit contracts when one Clang carries contracts and reflection.
     A `pre` range on a parameter is then a natural nudge input.

## Open questions

1. **Arithmetic semantics of the construct.** Pick one or offer named
   variants:
   - widen the result type (bounded-integer; breaks accumulators);
   - keep the type and check (Kestrer: panic; safe_numerics: throw or
     compile-time trap);
   - named methods only (deranged);
   - keep the type and require a proof (Wuffs/SPARK);
   - allow out-of-range intermediates with a sticky invalid state and
     stop at extraction (KINT NaN integers, Chromium `CheckedNumeric`;
     added in the check).

   Which is the default, and is a silent saturate ever allowed without a
   named call?
2. **Loop accumulators and temporary out-of-range states.** Is type_safe's
   `modify()` window, a wider accumulator type, or `checked_add` in the
   loop the sanctioned pattern?
3. **Dynamic bounds** (`i < v.size()`) were the largest class in the census
   (32%). Static ranges cannot express them. Are they out of scope for this
   habit, or a separate "branded index" habit?
4. **Where the narrowing nudge's range knowledge comes from.** Teaching a
   verbs-owned check that `Bounded<0,32>` → `int` is lossless means owning
   a narrowing check, not configuring clang-tidy's. Is that acceptable
   machinery?
5. **Recorded reasons in C++.** `NOLINT(check)` has no required reason and
   clang-tidy reports no unused NOLINT (only unmatched BEGIN/END,
   `NoLintDirectiveHandler.cpp:190`). Verbs must own reason syntax and
   stale detection for C++, as rustc and GNATprove already do. Where does
   that live: a clang-tidy plugin, or a post-pass over diagnostics?
6. **Escape names in C++.** Is matching owned names (unchecked doors,
   storage fields) enough of a stop for the habit's claim, given that
   representation bypasses go unchecked? The claim has to say so in plain
   words.
7. **Enum-range overlap.** About 17% of the repeated-guard hits were
   `x >= E::First && x <= E::Last`. Does the bounded habit defer these to
   the enum habit, or treat an enum range as a bounded integer?
8. **Units scope.** Are units part of "bounded types" this round, or their
   own habit with time-via-chrono as the only nudge?
9. **Precision target for the nudges.** The corpus says 45% for the
   refined regex. What precision makes a nudge tolerable when every finding
   demands an edit or a reason? Is an AST version worth building to find
   out?

---

## Sources acquired this lane

| file | origin | SHA-256 |
|---|---|---|
| `papers/gamboa-2025-usability-barriers-liquid-types-pldi.pdf` | https://catarinagamboa.github.io/papers/pre_print_barriers_liquid_types.pdf (2026-11-23) | `b492443fa7d1f54485163563b3583861873be5495af1e5668a248c8398995108` |
| `papers/dietz-2012-understanding-integer-overflow-icse.pdf` | https://www.cs.utah.edu/~regehr/papers/overflow12.pdf (2026-11-23) | `1938bb339678875ad55dd17a3c8a8d20e8db094c9d91f7d18d821fb8460d91cc` |
| `papers/wg21-p2900r14-contracts-for-cpp.pdf` | https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2025/p2900r14.pdf (2026-11-23) | `ca04bee75383a6a51c147af1b62fe8bd746cd4e3ab77025f7ce4267b73ee4168` |
| `papers/wang-2012-kint-integer-security-osdi.pdf` (added in the check) | https://css.csail.mit.edu/6.566/2018/readings/kint.pdf (2026-11-23) | `7864c206bec037e6090c246111a9412baba79e8d6b2de27d391df7db57040dd3` |

No new quarantine references were added. The Rust crates and Flux were read
through docs.rs, crates.io and the GitHub API at the commits named above.

Web pages read (all accessed 2026-11-23):
- Rust pattern types: https://github.com/rust-lang/rust/issues/123646;
  https://raw.githubusercontent.com/rust-lang/rust/master/library/core/src/pat.rs
  and `num/niche_types.rs`.
- Rust crates:
  - https://docs.rs/deranged/latest/deranged/struct.RangedU8.html
  - https://docs.rs/bounded-integer/latest/bounded_integer/
  - https://github.com/Kestrer/bounded-integer `src/unsafe_api.rs`
  - https://docs.rs/ranged_integers
  - https://github.com/greyblake/nutype README
  - crates.io API for download and reverse-dependency counts
- Flux: https://github.com/flux-rs/flux, `book/src/…`.
- SPARK:
  - https://learn.adacore.com/courses/intro-to-spark/chapters/03_Proof_Of_Program_Integrity.html
  - https://docs.adacore.com/spark2014-docs/html/ug/en/source/silver_level.html
  - https://docs.adacore.com/spark2014-docs/html/ug/en/source/how_to_use_gnatprove_in_a_team.html
- Compiler status: https://clang.llvm.org/cxx_status.html;
  https://gcc.gnu.org/projects/cxx-status.html.
- Kernel overflow discussion:
  https://lkml.iu.edu/hypermail/linux/kernel/2405.1/01278.html;
  https://lwn.net/Articles/959189.
- XO:
  https://conf.researchr.org/details/icse-2025/icse-2025-research-track/115/Neurosymbolic-Modular-Refinement-Type-Inference

---

## Check (2026-11-23)

The checker reopened the cited sources: quarantine refimpls at the
manifest commits, the three acquired PDFs (pdftotext), web pages and
GitHub sources by URL, and the cited corpus files extracted from
`quarantine/_archives/corpus-2026-10-18/` into the session scratchpad,
not the project. Probes were re-run on Clang 23.1.2 and Rust 1.99.0 /
clippy 0.1.99.

### Verified (source opened, claim holds)

- bounded-integer: `operator+` widening and the "Overflow in calculation of
  bounds." static_assert (`plus.cpp:29-58`); `check_in_range` throw message
  (`check_in_range.cpp:52`); `assume_in_range` → `std::unreachable`
  (`integer.cpp:88-92`); overlapping assignment through `assume_in_range`
  (`:191-193`); `[[assume]]` in `value()` (`:169`); public `m_value`
  with its "Do not access this directly" comment (`:205-208`); `clamp`
  (`clamp.cpp:17`); "Build with clang 22+" (README:23); 485
  `static_assert` lines under `source/bounded`.
- safe_numerics: range aliases (`safe_integer_range.hpp:32,49`);
  `trap_exception` has no call operator, "emit compile time error if this
  is invoked" (`exception_policies.hpp:62-67`); `strict_trap_policy`
  comment (`:156-166`); default = `strict_exception_policy` (`:171`). Note:
  that policy throws on three classes and *ignores* uninitialized values.
- type_safe: verifier semantics as documented (`constrained_type.hpp:25-62`),
  `modify()` (`:205`), modifier destructor re-check (`:366`),
  `bounded_type`/`clamping_verifier` lines, `ts::integer` doc comment.
- mp-units: `unsatisfied<"…">` throwing under
  `MP_UNITS_API_THROWING_CONSTRAINTS` (`bits/unsatisfied.h`); the
  truncation messages in `quantity.h:82-120`; `= delete ("Conversion is
  truncating")` (`:714`); overflow-policy struct lines 315/346/381/425/534/559;
  `safe_int.h:293, 363` messages; size 4,990,478 bytes (manifest).
- strong_type `value_of()` returns `T&` (`type.hpp:152-168`); NamedType
  `get()` returns `T&` (`named_type_impl.hpp:76`); GSL `narrow_cast` /
  `narrow` text.
- Clang: overflow-behavior attribute docs (`AttrDocs.td:10343-10385`,
  "wholly overrides global flags", experimental `-cc1` flag);
  UBSan `-fsanitize=integer` contents and the three ignore-overflow
  patterns (`UndefinedBehaviorSanitizer.md`); NOLINT handler emits only
  unmatched BEGIN/END errors (`NoLintDirectiveHandler.cpp:181-198`), and
  no clang-tidy check or option reports unused NOLINTs or requires a
  reason (docs searched; `index.rst:541` shows the reason is free text);
  `narrowing-conversions.rst` options as quoted.
- Probes reproduced: `__ob_trap` add exits 133 (SIGTRAP); `-fcontracts` is
  "unknown argument" and `__cpp_contracts` is undefined; all five §1.8
  cases give the stated diagnostics, including the printed concept clause
  `because '100LL <= 50LL'` (line 16 of 19 diagnostic lines) and the
  silent `throw "…"`; `#[expect]` staleness warning; clippy groups for
  `manual_clamp`, `manual_range_contains`, cast lints, restriction lints.
- Jolt clang-tidy run reproduced exactly: 35 files, 13
  `bugprone-narrowing-conversions`, 9 implicit-widening, 455 magic numbers,
  about 16 s.
- Corpus spot checks: fprime `ComQueue.cpp:234`, OSRM `coordinate.hpp:62-66`,
  `coordinate.cpp:20`, `coordinate_calculation.cpp:247`,
  `node_osrm_support.hpp:434`, Jolt `SkeletalAnimation.cpp:101`,
  `Vec4.inl:939`, `UVec4.inl:619`, `TrackedVehicleController.cpp:178`,
  `RackAndPinionConstraint.h:32`, `DynMatrix.h:15`, OpenTTD
  `newgrf_station.cpp:443,467`.
- Rust: Kestrer `unsafe_api.rs:1592` panic text and `abs`/`pow`/
  `div_euclid` at 379-409; deranged has no ops impls; crates.io counts
  (deranged 789,779,153 / 26 reverse deps; bounded-integer 1,559,150;
  ranged_integers 15,829; nutype 7,511,673); pattern types issue #123646
  checklist and `niche_types.rs` using `pattern_type!`; Flux
  `check-overflow` default `none`, build-from-source with nightly,
  liquid-fixpoint and z3 ≥ 4.15.
- Papers: Gamboa et al. (19 participants; nine barriers in three
  categories; "all of our Experienced Users reported challenges with
  LiquidHaskell error messages" §4.7; CR1's "lightweight verification" §5);
  Dietz et al. ("over 200 distinct locations"); P2900R14 quote.
- Web: Clang cxx_status (P2900R14 "No", P2573R2 Clang 19, P2996 "No"); GCC
  16 contracts; AdaCore team-use page (Annotate categories, useless-pragma
  warning) and Silver-level page; Torvalds LKML 2024-05-08 quotes.
- Escape-check history: v1 zero false positives on `legit/l1..l7`
  (escape-allowlist §3); round-2/3 forge tables and the "In three rounds
  every confirmed miss" diagnosis (journal 2026-10-17-preliminaries,
  lines 378-498); WORK.md verbs-g5w eight programs.

### Corrected (old → new, with source)

1. Summary item 3 and §1.3: "type_safe asserts in debug and assumes in
   release" / "default `assertion_verifier` makes release builds trust the
   value" → it checks and aborts in all build modes by default
   (`TYPE_SAFE_ENABLE_PRECONDITION_CHECKS` = 1 with no `NDEBUG` test,
   `config.hpp:22-27`, `CMakeLists.txt:25`). Turning it off passes the value
   through unchecked. Only `DEBUG_ASSERT_DISABLE` makes it
   `__builtin_unreachable` (`debug_assert.hpp:364-367`). The lane summary's
   key finding 3 carries the same error.
2. §1.1 "`BOUNDED_ASSERT` becomes `[[assume]]` or `assert`" →
   `BOUNDED_ASSERT` is `assert` in debug and constant-evaluation-only under
   `NDEBUG`; `BOUNDED_ASSERT_OR_ASSUME` is the one that becomes
   `[[assume]]` (`assert.hpp:25-29`).
3. §1.1 "a loop counter's increment past `maximum` is UB" → inferred, not
   read: `+=` comes from the external `operators` library, which is not in
   quarantine.
4. §1.4 field location `quantity.h:292` → declared at `quantity.h:662`;
   292 is a use.
5. §1.9 P2900 quote "§3.5.4" → proposed wording [basic.contract.eval] p2;
   prose equivalent §3.5.5.
6. §4.1 rocksdb citations (`db_options.cc:973`, `cache_bench_tool.cc:449`,
   `env_posix.cc:350` ×14) → these lines exist in snapshot 6a4361504171,
   not in the stated 54732b0. At 54732b0 they are `include/rocksdb/options.h:917`,
   `cache_bench_tool.cc:620`, and `env_posix.cc:365`; the ×14 is 7 in
   `env_posix.cc` plus 7 in `port/win/env_win.cc`. The rocksdb counts'
   snapshot is uncertain.
7. §4.2 Jolt `Color.h` findings "`uint8 * float`, whose comment says
   intensity in [0, 1]" → the flagged conversion is the promoted `uint8`
   channel `int`→`float`, which is exact for 0..255. The point is
   stronger: the check fires even where a builtin source type carried the
   range.
8. §4.3 "`--explain` for the cast lints … 'as a one-time check'" → that
   phrase is `cast_sign_loss`'s. `cast_possible_truncation` says it "can be
   activated to help assess where additional checks could be beneficial".
   `manual_clamp` documents panic-on-`max < min` as well as NaN.
9. §2.4 nutype "field hiding not verified" → verified: a generated private
   module `__nutype_<Name>__` plus a re-export (`generate/mod.rs:97-111,
   509-522`). The shopping-list item for nutype is answered.
10. §2.1 deranged: how `MIN > MAX` is rejected → `const { assert!(MIN <=
    MAX) }` in each method (post-monomorphization), and the field is an
    `Unsafe<T>` wrapper, so even the defining crate needs `unsafe`. The
    shopping-list question is answered.

No correction changes the lane's ranking or main conclusions.

### Added

- §1.7: OBT compile-time diagnostics. trap↔wrap mixing is an error;
  `-Wimplicit-overflow-behavior-conversion` fires when an OBT escapes to a
  plain integer (probed). Also the 2026-03-31 kernel series adopting OBTs
  per type as the successor to the 2024 thread.
- §1.10 Chromium `base/numerics` (CheckedNumeric sticky invalid state,
  ClampedNumeric, StrictNumeric/strict_cast compile error, checked_cast,
  saturated_cast).
- §1.11 C++26 `std::saturating_*` (libc++ 23, renamed by P4052R0) and
  `<stdckdint.h>` `ckd_add`, both probed on the pinned toolchain.
- §2.7 `clippy::allow_attributes_without_reason` and
  `clippy::allow_attributes` make the reason mandatory (probed); `NonZero`,
  `Wrapping`, `Saturating`.
- §4.2 Clang's own `IntRange` analysis behind `-Wimplicit-int-conversion`:
  silent on `x & 0xFF` and `x % 200`, warns despite a guard or
  `[[assume]]` (probed); `-Wtautological-constant-out-of-range-compare`.
- §4.3 `clippy::checked_conversions` (hand range check before a cast,
  probed).
- §4.5 KINT (OSDI 2012). 42/43 false reports on one kernel module were
  removed by 23 `__range` annotations; 125,172 whole-kernel warnings; 741
  reviewed → 11 exploitable; missed an accumulation-loop overflow; NaN
  integers.
- §4.6 CodeQL `@precision` labels: hand-validated array index is "low";
  narrow-vs-wide loop comparison is "high".
- Open question 1: the sticky-invalid arithmetic option.

### Still open after the check

- No measured precision exists for any of the nudges proposed here (the
  repeated-guard regex estimate stands as the only number).
- No agent-ergonomics evidence specific to bounded types was found;
  Gamboa et al. (humans, LiquidHaskell) and XO (LLM-written refinements)
  remain the nearest.
- The XO PDF (Sakkas et al., ICSE 2025) was not acquired.
- Whether the kernel OBT series merged was not confirmed.
