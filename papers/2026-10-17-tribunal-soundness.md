# Tribunal: soundness of the claims (design/SPEC.md draft of 2026-10-17)

Lens: does a `holds` claim (§2) on a vlib-typed declaration ever describe a
value that violates its predicate, without any construct in §4's escape list?

Method: a sketch of vlib built to §3's shapes (private `rep v_`, private raw
constructor, cross-instantiation construction through
`template <std::int64_t, std::int64_t> friend class Bounded;`, `[[assume]]` in
`get()`, `make` via `std::cmp_*`, `+=` with the §3.1 constraint, a
`VERBS_ENUM` that specialises `verbs::enumerators<E>`). Probes compiled with
Homebrew clang 23.1.2, `-std=c++2c -isysroot $(xcrun --show-sdk-path)`, and
libc++ at its default hardening mode (`NONE`, from `__config_site`). Probe
sources: `/private/tmp/claude-501/-Users-patrickbeam-projects-verbs/31609136-8b04-4690-baf8-5705774fb9e7/scratchpad/tribunal-soundness/`
(`vlib.hpp` is the sketch; `aNN_*.cpp` are the attacks). The probes check a
violation by reading the stored byte with `memcpy` and not with `get()`, so the
observation itself does not depend on the `[[assume]]` UB.

Answer to §12 Q1: **no.** The claim is false as stated. §4 lists bad
*spellings*. The language has many more spellings, and several attacks need no
cast at all. Findings 1-7 are blockers.

---

## Blockers

### B1. Byte-level writes that never cast: the implicit `T*` → `void*` conversion

§4 "Bypasses of representation" (memcpy/memmove/memset/std::byte view) and §2.3 rule 3.

```cpp
struct Header { verbs::Bounded<1,5> version; std::uint32_t len; };
Header h{B5::lit<1>(), 0};
std::fread(&h, sizeof h, 1, f);          // Header* -> void*, implicit. h.version == 9
```

```cpp
void* m = std::malloc(sizeof(B5));
std::memcpy(m, &v, 1);                   // destination is void*, not "a vlib object"
B5* p = std::launder(static_cast<B5*>(m));   // static_cast from void*, std::launder: not listed
B5 copy = *p;                            // copy holds 9
```

Confirmed (a01, a02, `-O2 -Wall -Wextra`, no warnings). The second program is
close to well-defined C++20: `Bounded` is implicit-lifetime
(`std::is_implicit_lifetime_v` holds), and `malloc`/`memcpy` implicitly create
objects. `read`, `recv`, `pread`, `mmap` and any `void*` API work the same way,
and so does a user helper `void zap(void* p, size_t n)` that hides the memset
behind an untyped pointer. Clang 23's libc++ has no `std::start_lifetime_as`
yet. When it does, it is a further spelling.

Fix: define the representation escape by AST semantics, not by function
name. (a) Converting a pointer or reference to a *vlib-containing* type (see
B2) to `void*`, `char*`, `unsigned char*` or `std::byte*` is an escape. That
covers implicit conversions, `static_cast` and every other spelling. The one
exception is a `const` pointer passed straight to a known read-only sink
(`memcpy` source, `fwrite`, `write`, hashing). (b) Any cast *from* `void*` or
a byte pointer *to* a pointer to a vlib-containing type is an escape, and so
are `std::launder`, `std::start_lifetime_as` and placement-new over storage
that holds a vlib object. The common callback round trip (`void* ctx` back to
`State*`) should be reported `outside` with that reason, not as a finding.
That keeps the zero-false-positive bar without lying.

### B2. "Involves a vlib type" and "union member of vlib type" are not transitive

§4, items 1 and 3.

```cpp
struct Wire { B5 kind; std::int8_t pad; };
union Frame { Wire w; std::int8_t raw[2]; };       // no member has vlib type
f.raw[0] = 9;                                       // f.w.kind == 9
Wire w2 = std::bit_cast<Wire>(std::array<std::int8_t,2>{9,0});           // target is Wire
auto o  = std::bit_cast<std::optional<B5>>(std::array<std::int8_t,2>{9,1}); // engaged, holds 9
auto b3 = __builtin_bit_cast(B5, std::int8_t{9});   // builtin spelling
using P = B5*; B5* fp = P(vp);                      // functional-notation cast, not "C-style"
```

Confirmed (a17). Every case stores 9 with no diagnostic. Each one escapes a
literal reading of §4: the vlib type sits one level down, or the spelling
isn't named (`__builtin_bit_cast`, the functional cast `P(vp)`).

Fix: define a *vlib-containing* type as one that is, recursively, a vlib type,
a verbs-domain enum, or an array of, class with a member or base of, or
standard wrapper (`optional`, `pair`, `tuple`, `array`, `expected`) of, such a
type. Every §4 rule applies to vlib-containing types. Match Clang
`CastExpr` kinds (`BitCast`, `LValueBitCast`, `BuiltinBitCastExpr`,
`IntegralCast` to an enum) whatever the syntax node.

### B3. Enum ingress without a cast: list-initialisation of a fixed-underlying enum

§3.4 "Escapes" and §4 item 4.

```cpp
VERBS_ENUM(Mode, std::uint8_t, Idle, Armed, Firing)
std::uint8_t raw = wire();        // 7 at runtime
Mode b{raw};                      // [dcl.init.list]: legal since C++17, no narrowing
Door d{.mode = Mode{raw}};
```

Confirmed (a03): every one prints 7, while `to_enum<Mode>(7)` is empty. No
warning under `-Wall -Wextra`. The Clang AST shows exactly what to match:
`InitListExpr` → `ImplicitCastExpr <IntegralCast>` to `Mode`, wrapped in a
`CXXFunctionalCastExpr` for `Mode{raw}`. This is the simplest way to break the
`in{}` claim, and it is the idiomatic C++17 spelling an agent would reach for.

Fix: the enum rule is "any `IntegralCast` (or float-to-integral) whose
destination is a verbs-domain enum, outside `to_enum`/`from_string`", whatever
the syntax. That one rule covers `static_cast`, C-style casts, functional
casts and list-init.

### B4. User specialisations of vlib templates get private access

§3 (encapsulation), §4 (no rule). §2.3 rule 3 is assumed, not checked.

```cpp
template <> class verbs::Bounded<7,7> {             // befriended by every Bounded
public: static verbs::Bounded<1,5> forge(std::int8_t v) { return verbs::Bounded<1,5>(v); }
};
// or: specialise a member, which is a member and so has private access
template <> template <>
constexpr std::optional<B5> B5::make<int>(int v) noexcept { return B5(static_cast<rep>(v)); }
B5 b = *B5::make(9);                                // reads like checked ingress
```

Confirmed (a06, a07). Both store 9. Specialising `verbs::enumerators<Mode>`
(or `to_enum<Mode>`) the same way forges enum ingress. Note that the
`VERBS_ENUM` fallback itself expands to a specialisation of a verbs template
in user code. The rule therefore has to exempt the macro's expansion by
expansion location.

Fix: escape = any declaration in `namespace verbs`, or any explicit or partial
specialisation of a verbs template (class, member, variable, function), whose
spelling location is outside vlib's headers, except `VERBS_*` macro
expansions.

### B5. Private-member theft through explicit instantiation, and keyword macros

§3.1 "The stored member is private", §4 (no rule).

```cpp
template <class Tag> struct stolen { static inline typename Tag::type ptr; };
template <class Tag, typename Tag::type M> struct thief {
    static inline const bool done = (stolen<Tag>::ptr = M, true); };
struct v_tag { using type = B5::rep B5::*; };
template struct thief<v_tag, &B5::v_>;     // access is not checked in explicit instantiations
b.*stolen<v_tag>::ptr = 9;
```

```cpp
#define private public                     // before the header; then b.v_ = 9
```

Confirmed (a08, a09). Both store 9, with no warning under `-Wall -Wextra`. The
first is fully standard C++.

Fix: escape = any expression or template argument outside vlib's headers that
names a private or protected member of a vlib class (`MemberExpr`, a
`DeclRefExpr` to the field, or a pointer-to-member constant). Also an escape:
any `#define`/`#undef` of a C++ keyword, including `-D` on the
compile-database command line and `-include` forced headers.

### B6. Cross-TU type confusion between two clean, analysed units

§4 is per-unit. §6.2 step 3 runs only the enum-candidate rule across units. §2.3 rule 7 does not apply, because both units are in the database.

```cpp
// a.cpp                                   // b.cpp (never names a vlib type)
extern verbs::Bounded<1,5> g;              std::int8_t g = 9;
struct Pkt { verbs::Bounded<1,5> kind; };  struct Pkt { std::int8_t kind; };
void fill(Pkt&);                           void fill(Pkt& p) { p.kind = 9; }
```

Confirmed (a12, linked together): `g holds 9, p.kind holds 9`. `nm` shows `_g`
with no type in the Itanium name. `fill(Pkt&)` mangles the same in both units.
Neither unit has a §4 construct. The program has an ODR violation (no
diagnostic required) and incompatible declarations of `g`, and nothing
reports either.

Fix: per-unit facts record, for every external-linkage variable and function
and every class definition, the type or definition hash. The cross-unit step
flags a qualified name with two different types or definitions where either
one is vlib-containing. That is exactly what the facts files are for.

### B7. Refined is only sound for deep value types, and the spec's own example is not one

§2.1 example "a non-empty, sorted span", §3.2, §2.3 rule 3.

```cpp
auto r = Refined<std::span<int>, Sorted>::make(std::span<int>(v)).value();
r.get()[0] = 100;        // const span& still yields int&
v[1] = -5;               // or the owner of the elements writes directly
struct Positive { int x; mutable int cache; };
q.get().cache = -1;      // mutable member through const T&
```

Confirmed (a10): both predicates read false afterwards, with no escape. The
same holds for any `T` with pointer, reference, view or `shared_ptr` members,
and for `T` whose copy or move does not preserve the value. A Refined copy
runs `T`'s copy constructor, which the predicate never re-checks.

Fix: `Refined<T, Pred>` requires `T` to be a *deep value type*: arithmetic,
enum, vlib type, `std::string`, or `std::array`/`vector`/`optional`/`pair`/`tuple`/aggregate
of deep value types, with no `mutable` members (reflection can check
aggregates; without reflection, an allowlist). Any other `T` is a compile
error or an `outside` report. Change the §2.1 example to an owning sorted
vector.

---

## Major

### M1. The claim boundary omits memory safety and UB in non-vlib code

§2.3. Any out-of-bounds or out-of-lifetime write anywhere (a
`buf[i]` next to a Bounded field, use-after-free via a dangling
`const B5&` after `vector` reallocation) can store any byte into a vlib
object. ASan does not detect intra-object overflow. This isn't one escape; it
is all of C++. The boundary already assumes away rarer things (unwind,
moved-from), so it must say this. Not compiled: this is UB by construction and
a probe would prove nothing new.

Fix: rule 8: "The program has no undefined behaviour outside vlib. In
particular, no out-of-bounds or out-of-lifetime access. verbs does not check
this. Sanitizers, `-fsanitize=bounds` and library hardening are the mechanisms."
Print it in the footer.

### M2. Unchecked dereference of `make`'s result

§3.1 "Ingress", §3.2, §2.3.

```cpp
B5 b = *B5::make(input());   // input() == 9 at runtime; b holds 0
```

Confirmed (a15). Under libc++'s default hardening (`NONE`), `b` holds 0. With
`-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_FAST` the same program traps
(exit 133). `*Refined::make(x)` on an `unexpected` is the same hole. This is
the most likely agent mistake on the whole ingress surface, and the report
would say `construction` holds.

Fix (pick one): have `make` return a vlib-owned optional whose `operator*`
and `->` always check and call the handler. Or add "library hardening at FAST
or above" to the claim boundary, read it from the compile command, and report
`outside` when it is absent.

### M3. Initialisation order: static zero-init and self- or out-of-order initialisation

§3.1 "No default constructor", §3.4, §4.

```cpp
// a.cpp: extern Bounded<1,5> limit;  Bounded<1,5> copy_of_limit = limit;
// b.cpp: Bounded<1,5> limit = *Bounded<1,5>::make(env_limit());
```

Confirmed (a13): `copy_of_limit holds 0`. Static storage is zero-initialised
before any constructor, whether or not the default constructor is deleted. The
read happens before `limit`'s dynamic initialisation. Formally that is an
out-of-lifetime access, but in practice it is silently 0. Also confirmed
(a14): `B5 x = x;` and a member-initialiser list that reads a later member
both compile. Clang emits only a non-error `-Wuninitialized` warning. They
hold 0, or 0xAA (-86) under `-ftrivial-auto-var-init=pattern`. Enums suffer
the same: zero-initialisation gives 0 whether or not 0 is an enumerator.

Fix: a vlib-containing object with static or thread storage duration must be
`constinit`, or it is an escape (`outside` at minimum). `-Werror=uninitialized`
is part of the claim boundary and is read from the compile command.

### M4. Enums: bit-fields and value-initialisation produce out-of-domain values

§3.4.

```cpp
enum class Mode { Idle, Armed, Firing };         // reflection path: underlying int (signed)
struct Packed { Mode m : 2; };  p.m = Mode::Firing;   // reads back -2
enum class Level : unsigned char { Low = 1, Mid, High };
Level a{}; Cfg c{}; std::vector<Level> v(2); m[42];   // all 0, not an enumerator
```

Confirmed (a04, a05). The bit-field case raised no warning under
`-Wbitfield-enum-conversion`, nor under `-Weverything`, whose only enum-related
warning was a portability note about the Microsoft ABI. The reflection path
explicitly allows a plain `enum class`, whose underlying type is `int` and
which may lack a 0 enumerator.

Fix: (a) a bit-field of verbs-domain enum type narrower than the enum's
enumerator range is an escape. (b) A verbs-domain enum must have an enumerator
equal to 0, or every value-initialisation and zero-initialisation of it is an
escape. The first is simpler: `VERBS_ENUM` gets it for free. Require it of
reflected enums too.

### M5. `%` breaks §3.1's "the runtime computation cannot overflow"

§3.1 "Arithmetic widens".

```cpp
using Num = Bounded<INT64_MIN, INT64_MAX>; using Den = Bounded<-1,-1>;   // excludes 0
auto r = n % Den::lit<-1>();      // n == INT64_MIN
```

Confirmed (a18). The result range fits `int64_t`, so no `static_assert`
fires, but `INT64_MIN % -1` is undefined behaviour ([expr.mul]/4). UBSan
reports it, constant evaluation rejects it, and x86-64 raises SIGFPE. The
argument "the result type holds every result, so nothing overflows" does not
cover `%`.

Fix: compute `%` (and `/`) in `__int128`, or constrain `%` out when
`Lo == INT64_MIN && A <= -1 && -1 <= B`. Add this pair to the §9.1 spec
tables.

### M6. `+=`: the shown constraint hard-errors at the extremes, and the natural fix miscompiles

§3.1 accumulator rule, §12 Q2.

As written, `requires (Lo <= Hi + B && Lo + A <= Hi)` is evaluated in
`int64_t`. `Bounded<0, INT64_MAX> s; s += Bounded<0,10>` is the natural
accumulator, and it fails with "substitution into constraint expression
resulted in a non-constant expression" (a19). Widening only the constraint to
`__int128` (a19b) leaves the natural runtime check

```cpp
std::int64_t r = std::int64_t{v_} + y.get();  if (r < Lo || r > Hi) violation();
```

At `-O2`, clang deletes this check: the overflow is UB, and the `[[assume]]`
in `get()` says both operands are ≥ 0. The program prints
`s = -9223372036854775804`: a `Bounded<0, INT64_MAX>` holding a negative
number, with the handler never called. Confirmed (`VERBS_NAIVE_PLUS_EQ`). With
the sum in `__int128`, it aborts correctly. The spec says only "checks that
the result fits".

Fix: state that the `+=` constraint and check are both computed in `__int128`
(the same as result bounds), and that the check happens before the store. Make
the handler `[[noreturn]]` and owned by vlib: if a user hook returns, vlib
calls `std::abort()` itself. Add `INT64_MAX` accumulators to the death tests.

### M7. Escapes are attributed to "the declaration whose claim it voids", but finding that declaration needs alias analysis

§2 table (`holds`: "no escape in the analyzed code touches D's values"), §4.

`memcpy(p, src, n)` with `p` from a parameter, a container or a `void*`
helper names no declaration. Per-declaration attribution needs points-to
analysis, and the basics don't have it. Any attribution that is less than
sound produces false `holds`.

Fix: an escape voids the claim for every declaration whose type is the
affected vlib-containing type, program-wide (or for every vlib declaration
when the type is unknown, as with a `void*` sink). Escapes are rare and must
be zero-FP, so coarse attribution costs nothing in practice. Narrow it when a
points-to analysis exists (bead).

### M8. Refined predicates can read mutable state

§3.2 `named_predicate`.

```cpp
inline int g_limit = 10;
struct UnderLimit { static constexpr std::string_view id = "under_limit";
  static constexpr bool operator()(const int& x) noexcept { return x < g_limit; } };
auto u = Refined<int, UnderLimit>::make(7).value();  g_limit = 5;   // u no longer satisfies it
```

Confirmed (a11). It satisfies the concept: since C++23, `constexpr` does not
imply constant-evaluable. Fix: either require the predicate to be usable in
constant evaluation over some witness value (a weak guard), or make it an
escape for a predicate body to read a non-`const` object with static or thread
storage duration, or to call a function that does. The second is matchable
with full type information.

### M9. System-header status and diagnostic pragmas are silencing paths §4 doesn't name

§4 "Silencing". (Partly reasoned, not compiled.)

The spec doesn't say how escapes inside system headers are treated. If they
are reported, libc++'s own `memmove` inside `std::copy`/`vector` of trivially
copyable vlib types floods the report with false positives. If they are
ignored, then `#pragma clang system_header`, `-isystem` pointing into the
repository, and GNU line markers (`# 1 "x.h" 3`) let user code hide escapes.
`#pragma GCC diagnostic` (Clang honours that spelling), `_Pragma(...)` from
macros, `-Weverything`/`-w`, and `-Wno-*` in the compile database also
silence warnings without matching a literal "`#pragma clang diagnostic` that
disables `-Wswitch-enum`".

Fix: judge std-library internals at the typed API boundary (copying `B5`
objects with `std::copy` is fine), and never inside the library. Treat
system-header markers on repository files, and compile-database flags that
change verbs-relevant warnings, as silencing findings. Match pragmas by their
effect on diagnostic state, not by spelling.

### M10. Inline assembly

§4 (no rule).

```cpp
asm volatile("strb %w1, %0" : "=m"(b) : "r"(nine));    // b holds 9
```

Confirmed (a16, arm64, `-O2 -Wall`). Fix: an `asm` statement with an output
or memory operand that is vlib-containing, or any `"memory"` clobber in
analysed code, is an escape (or `outside`).

---

## Minor

- **m1. Moved-from Refined (§2.3 rule 2).** `auto b = std::move(a);` leaves `a`
  holding an empty vector under `non_empty` (a11, confirmed). The boundary
  covers this, but vlib could remove the assumption for its own types
  cheaply: make `Refined`'s move copy (or leave the source unchanged), and
  make copy-assignment copy-and-swap, which also discharges rule 1 for
  Refined.
- **m2. The footer is inconsistent with §2.3.** The §6.4 example prints only
  rules 1-4. §2.3 says every rule, and rule 7 says the report names the
  database. Print all of them, plus M1's rule 8.
- **m3. Rule 7 is honest, but cheaper to check than to assume.** A
  declaration whose address or non-const reference reaches a function with no
  definition in the analysed code can be reported `outside` (rule 7) instead
  of `holds`. The enum-candidate check already computes "passing it to a
  function outside the analyzed code". Templates instantiated only in
  unanalysed units fall under the same rule.
- **m4. Mechanism attribution for derived values (§12 Q2).** `Bounded<0,10> z = x;`
  after `x += y`: is `z`'s mechanism `typecheck`, or does it inherit
  `construction`? Define the mechanism set as the set over D's own writes, or
  propagate along assignments. Either is fine. Leaving it undefined lets the
  report call a value whose path can reach the handler "typecheck".
- **m5. `make` property tests (§9.1) cover only `int64_t` edge values.** `make`
  takes any `std::integral`. Test `uint64_t` values above `INT64_MAX`, every
  narrower signed and unsigned type, `bool` and the character types (which
  `std::cmp_less` rejects at compile time; the spec should say whether that is
  intended).
- **m6. Id kind laundering (§3.3).** `UserId{order.get()}` is explicit
  construction, so it is allowed. It is the one way `kind(Tag)` goes wrong
  in practice. Flag an `Id<A>` constructed from `Id<B>::get()` with `A != B`.
- **m7. Predicate identity collisions without reflection.** Two predicates
  with the same `Pred::id` string make `refined(pred-id)` ambiguous. The
  cross-unit step should reject duplicate ids that belong to different
  types.

---

## Attacks that failed (what holds)

Confirmed by compilation (p00, p00b):
- Raw-integer ingress is rejected: `std::is_constructible_v<Bounded<1,5>, int>` is false.
- Narrowing conversion is rejected: `Bounded<0,10>` → `Bounded<1,5>` is not convertible.
- Default construction is rejected, so `Bounded<1,5> b;`, `b{}` and `std::array`/`vector::resize` of it do not compile.
- `lit<9>()` on `Bounded<1,5>` fails its constraint.
- Hidden-friend `operator+` across two instantiations is unambiguous. Both
  argument orders pick the exact candidate (`Bounded<1,5> + Bounded<0,10>`
  and the reverse are both `Bounded<1,15>`). The other candidate, reachable
  only through widening, would be wider and therefore still sound, so no
  selection is unsound.
- Widening `Bounded<1,5>` → `Bounded<0,10>` preserves the value.
- The `+=` handler is reached (and nothing is stored) when the sum is
  computed in `__int128` (a19b without `VERBS_NAIVE_PLUS_EQ`, exit 134).
- `Refined` without mutable members or reference semantics, such as
  `Refined<std::vector<int>, NonEmpty>`, cannot be mutated through `get()`.
- Library hardening at FAST catches M2.

By reading the rules, not compiled (the probe file for these didn't complete):
- An aggregate holding a Bounded with the field omitted (`Agg{.x = 1}`)
  value-initialises it from `{}`, which hits the deleted default constructor,
  so it is rejected.
- `volatile Bounded` cannot call `get()`, and there is no volatile write
  path.
- Structured bindings cannot decompose `Bounded` (private member, no tuple
  protocol). Binding a struct that contains one yields an ordinary lvalue.
- `std::atomic<Bounded>` and `std::atomic_ref` store only whole, valid values.
- consteval and constexpr paths: a false `[[assume]]` in constant evaluation
  is ill-formed, so the compiler rejects it and it never reaches runtime.
- Coroutines, `std::optional`/`std::expected` holding valid vlib values,
  `std::variant`: copy and move only.
- Bound overflow in `+ - *` and negation is caught by the `__int128`
  `static_assert` design (this matches `detail::fit` in the sketch).
- `Violation` carries only the id. Of everything vlib emits, only the
  violation handler's message is unspecified. State that it carries no value.

---

## Smallest spec change that closes the blockers

Replace §4's list of bad spellings with an allowlist: *the only operations
that may produce or overwrite the bytes of a vlib-containing object are vlib's
own members, and copy/move from another object of the same type.* Then
enumerate the detection rules by Clang AST semantics: pointer conversions to
or from untyped pointers, every cast kind into a verbs enum, specialisations
and declarations in `namespace verbs`, naming private members, keyword macros,
`asm`, non-`constinit` statics, and cross-unit declaration and definition
mismatches. Add rule 8 (no UB outside vlib) to the boundary, and restrict
`Refined` to deep value types.
