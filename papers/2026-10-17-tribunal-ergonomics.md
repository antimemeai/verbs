# Tribunal: ergonomics, readability and adoption of vlib

Lens: design/SPEC.md §3 (vlib), §7 (decisions), §10 (layout), as of commit
d03a6fe. Method: I sketched vlib exactly as §3 declares it, rewrote three real
excerpts from blackbird and BRepGPU with it, compiled common mistakes, and
measured compile cost. Everything was built with Homebrew clang 23.1.2,
`-std=c++2c -isysroot $(xcrun --show-sdk-path)`, using blackbird's own warning
set (CMakeLists.txt:46: `-Wall -Wextra -Wpedantic -Werror -Wconversion
-Wsign-conversion -Wshadow`). Load average was about 90 during the timing runs,
so the timings are CPU time (user+sys), minimum of 3 runs.

Scratch files: `/private/tmp/claude-501/-Users-patrickbeam-projects-verbs/31609136-8b04-4690-baf8-5705774fb9e7/scratchpad/tribunal-ergonomics/`
(`vlib/` holds the sketch, `mistakes/out0` the diagnostics for the spec as
written, `mistakes/out1` the diagnostics with deleted-with-message overloads,
`excerpts/` the before and after code, `cost/` the generators).

## Verdict in one paragraph

The enum half of vlib is a clear win. On real code it turns `node.kind == 3`
into `node.kind == PhaseKind::attempt` and writes down a 14-value domain that
today exists only inside a description string. `Bounded` as specified is not
ready for index or loop code. The natural loop compiles and then traps, every
index needs a cast under blackbird's `-Werror -Wsign-conversion`, constants are
spelled `Bounded<1, 1>::lit<1>()`, and the spec's promised diagnostic for
`x = x + y` does not appear. Four small API changes fix most of that, and with
them the BRepGPU excerpt reads almost exactly like the original (§S below).
`Id` is weaker than the `Id` blackbird already owns, and it protects nothing at
a C ABI. `seen(0, 1, 3)` on the decision macro is shadow accounting and should
go. The rationale on the declaration reads well. vlib's basics do not need
C++26: the sketch builds under blackbird's C++23 flags, except for one
diagnostic feature that the header can suppress locally.

---

## Findings

### B1. The natural index loop compiles and then traps. There is no `++`. — blocker, §3.1

There is no `operator++`. `++i` is rejected (`cannot increment value of type
'Bounded<0, 9>'`), so the loop has to be spelled with `+=`. If the counter has
the index type, the loop aborts on its last step, because a half-open loop
needs the one-past-end value:

```cpp
using Index = verbs::Bounded<0, 9>;   // an index into std::array<int, 10>
for (auto i = Index::lit<0>(); i < 10; i += verbs::Bounded<1, 1>::lit<1>()) { ... }
```
```
$ ./loop_trap ; echo rc=$?
i=8
i=9
rc=133            # SIGTRAP: the += from 9 to 10 reached the violation handler
```

It compiles with no warning. The alternative is to type the counter one wider
(`Bounded<0, 10>`), but then the body's `i` is not an index, and the type
proves nothing about `a[i]`. That is the whole point of `Bounded` in loops, and
it is lost. bounded::integer has the same issue and needs `integer_range` from
its containers library to solve it (quarantine/bounded-integer/source/containers/integer_range.cpp).

**Smallest spec change.** Add one range helper: `verbs::upto(n)` for
`n : Bounded<L, N>` with `L >= 0` yields `Bounded<0, N-1>`. The iterator holds
the past-end value internally, so it never sits in the user's variable. State
that `Bounded` has no `++`/`--`. I measured this at about 20 lines
(`vlib/simpler.hpp`):

```cpp
for (auto e : verbs::upto(edge_count)) a.offsets[e] = total;   // e : Bounded<0, MAX-1>
```

### B2. `get()` returns `int64_t`, so every index and store needs a cast under `-Werror`. — blocker for adoption, §3.1

The type proves that the value fits, and then `get()` throws that proof away:

```
m06: int f(const std::vector<int>& v, Bounded<0, 9> i) { return v[i.get()]; }
error: implicit conversion changes signedness: 'std::int64_t' (aka 'long long')
       to 'size_type' (aka 'unsigned long') [-Werror,-Wsign-conversion]
```

The spec-faithful BRepGPU rewrite (excerpts/a_after.cpp) needed a local
`at()` helper on every subscript, plus `static_cast<std::uint32_t>(total.get())`
on every store into the ABI arrays. Every adopter will write that helper.

**Smallest spec change.** Allow implicit conversion to any non-`bool`
integral `T` with `std::in_range<T>(Lo) && std::in_range<T>(Hi)`, and keep
`get()`. Egress cannot break the invariant, so this changes no claim. Tested
under the blackbird flags (`egress_test.cpp`): `v[i]`, `*out32 = count` and
`i < n` (with `n` a `size_t`) all compile cleanly. `*out8 = Bounded<0, 300>` is
rejected. `switch (b)` then works too (m16 currently needs `.get()`). One side
effect: `i + 1` becomes "ambiguous overloaded operator" instead of "invalid
operands". That is still an error, which is fine with `k<1>` (M1).

### M1. Constants are noisy, and there is no literal operand. — major, §3.1

- `i += verbs::Bounded<1, 1>::lit<1>();` is the spelling of increment (m19).
- In a template, `B::lit<0>()` fails with `missing 'template' keyword prior to
  dependent template name 'lit'` (m18). The fix is `B::template lit<0>()`.
- `i + 1`: `invalid operands to binary expression ('Bounded<0, 9>' and 'int')` (m07).

**Smallest spec change.** Replace `lit<V>()` with one variable template,
`verbs::k<V>`, a `Bounded<V, V>`. Widening already does the range check:
`Count total = k<0>;`, `i += k<1>;`, `offsets[e + k<1>]`. That is one name
instead of a static member template on every instantiation. An out-of-range
`Bounded<0, 5> x = k<7>;` stays a compile error (`k_bad.cpp`). Its deleted
message should name the constant rather than `+=` (see m4 below).

### M2. The promised diagnostic for `x = x + y` does not exist as declared. — major, §3.1

The spec says the diagnostic for plain `sum = sum + x` "names `+=` and
`verbs::narrow`". With exactly the members §3.1 declares:

```
m01: error: no viable overloaded '='
note: candidate function (the implicit copy assignment operator) not viable: no known
  conversion from 'Bounded<[...], detail::bound(detail::i128{4194304LL} + 4194304LL)
  aka 8388608>' to 'const Bounded<[...], 4194304>' for 1st argument
note: candidate function (the implicit move assignment operator) not viable: ...
```

Narrowing initialization and `return a - b;` (m04, m17) each give 1 error and
7 notes, and the notes walk through `std::integral` and libc++'s
`__concepts/arithmetic.h`. None of them is actionable. With one added deleted
converting constructor using C++26 `= delete("reason")`:

```
m01: error: conversion function from 'Bounded<[...], ... aka 8388608>' to
  'Bounded<[...], 4194304>' invokes a deleted function: narrowing Bounded conversion:
  use += / -= (checked), verbs::narrow<B>(x) (optional) or verbs::clamp<B>(x)
note: 'Bounded<0LL, 8388608LL>' has been explicitly marked deleted here
```

That is 1 error and 1 note, and it is actionable. The raw-integer constructor
likewise becomes `... invokes a deleted function: verbs::Bounded has no
constructor from a raw integer: use ...` (m02). Concept-rejection tests
(§9.1) still work, because deleted functions keep `requires { ... }` false.

Two further costs:
- The computed bound leaks into type names as
  `detail::bound(detail::i128{4194304LL} + 4194304LL) aka 8388608`. Computing
  into a named constant shortens it to `hi aka 10` (`aka2.cpp`). Clang always
  prints the written argument, so this is the best available.
- `= delete("…")` is an error under blackbird's C++23 `-Wpedantic -Werror`
  (`'= delete' with a message is a C++2c extension [-Werror,-Wc++26-extensions]`).
  The header must suppress that one warning locally, or select the message form
  only under `__cplusplus > 202302L`.

Things that read well already: an out-of-range `lit<7>` and a disjoint `+=`
both print the failing inequality (`because '0LL + 10LL <= 5LL' (10 <= 5)
evaluated to false`). Those are good diagnostics.

**Smallest spec change.** Declare
`template <C, D> requires(!(Lo <= C && D <= Hi)) Bounded(Bounded<C, D>) = delete("…")`
and `Bounded(std::integral auto) = delete("…")` with the messages, as part of
the specification, and pin each message with `-verify` (§9.1 already plans
this). Compute result bounds into named constants.

### M3. No checked ingress for "I know it fits", and the accumulator check costs. — major, §3.1

BRepGPU's scan accumulates raw `uint32_t` counts from the C ABI. `total +=
counts[e]` is rejected (`could not match 'Bounded<A, B>' against
'std::uint32_t'`, m10). The spec's only runtime ingress is `make`, which
returns `optional`. The realistic spellings are `*Count::make(x)`, which is
silent UB when the value does not fit (worse than the original code), or
`.value()` (throws `bad_optional_access`, and BRepGPU's functions are
`noexcept`). Otherwise the author hand-writes the handler call, as in
excerpts/a_after.cpp:

```cpp
auto c = Count::make(counts[at(e)]);
if (!c) verbs::violation("degree count above MAX");   // spec gives no checked ingress
total += *c;
```

At `-O2` the spec-faithful `scan` loop is 25 instructions with three checks
per iteration (make, `+=`, and the counter's `+=`). The original is 13
instructions with none, and none of the three checks can fire, because
admission already bounds the input.

**Smallest spec change.** Let `+=`/`-=` accept a raw integral operand with the
same unconditional check. It is already a `construction` point (§3.1), so no
claim changes. With it, `total += counts[e];` is identical to the original
line (excerpts/a_simpler.cpp, run under ASan/UBSan). Say in the spec that
`*` on a vlib `optional` is unchecked, and that `.value()` is the checked form.

### M4. No default constructor breaks common container idioms. — major, §3.1

The rule is right: it avoids inventing a value. The interop cost should be
stated, though, because it hits real code:
- `std::vector<Bounded<0, 9>> v(10);` gives 22 lines ending in `call to
  deleted constructor` (m14).
- `std::map<int, Node>::operator[]`, where `Node` has a `Bounded` field, gives
  46 lines of libc++ template backtrace (m15). blackbird's token_usage decoder
  builds its graph exactly this way (`auto &node = nodes_[own];`,
  src/token_usage.cpp:337).

**Smallest spec change.** Keep the rule. Name the consequence in §3.1
(`resize`, `operator[]` and value-initialized aggregates are unavailable) and
the idioms that replace them (`try_emplace(key, value)`, construction from a
full value).

### M5. `Id` is weaker than blackbird's own, and protects nothing at a C ABI. — major, §3.3

blackbird already owns `template <typename Tag> class Id`
(include/blackbird/foundation.hpp:87-101) with 12 tags. It has a private
constructor, and `from_bytes` refuses an all-zero identity and returns
`Result`. vlib's `Id` has a public explicit constructor and no ingress check,
so adopting it would be a downgrade. Rebuilding blackbird's type from vlib
parts gives `Refined<Id<AttemptTag, IdentityBytes>, NonZeroIdentity>`, read
with `a.get().get()`, plus a hand-maintained `id` string
(excerpts/c_refined.cpp).

In BRepGPU, coedge and face slots are where an `Id` should pay off:
`a.mates[left] = right` versus `a.neighbors[left] = a.faces[right]`. But the
storage is caller-owned `uint32_t*`, so every store goes back through
`.get()`, and `a.mates[at(left)] = rf.get();` compiles. Reinterpreting the
arrays as typed arrays would be an escape (§4). The tag protects nothing where
the bug would be.

`kind(Tag)` is enforced by C++ for any distinct class type. vlib's `Id` adds
no invariant that blackbird's type, NamedType or strong_type do not already
carry.

**Smallest spec change.** Drop `Id` from the vlib basics. Bring `kind(Tag)`
claims back with kind discovery (verbs-de3.21), which will have to recognize
existing strong types such as blackbird's anyway.

### M6. Positional `VERBS_ENUM` cannot express wire values. — major, §3.4

Real small domains carry explicit values: phase kinds 1..14
(src/provider_original.cpp:443), sites 1300/1320/2403/3600, orientation signs
-1/1 (BRepGPU). The spec's `VERBS_ENUM(Mode, std::uint8_t, Idle, Armed,
Firing)` is positional. To start at 1, excerpts/b_after.cpp needs a
placeholder `none_` enumerator, and then `to_enum` accepts 0, a value the
protocol does not define. That is a false domain created by the macro. The
sites cannot be written as a positional macro at all. Supporting `name = value`
needs a FOR_EACH preprocessor machine inside vlib, and macro-declared enums
lose clangd navigation and per-enumerator attributes.

I measured a macro-free alternative on Clang 23: read a plain `enum class`'s
enumerators from `__PRETTY_FUNCTION__` by probing all 256 values of an 8-bit
underlying type (magic_enum's technique; `vlib/enum_probe.hpp`, about 30
lines). It handles `assembly = 1, ...` and `negative = -1, positive = 1`
correctly (`probe_test.cpp`). Cost: 20 such enums take 3.54 s CPU to parse,
against 0.45 s for 20 `VERBS_ENUM`s, about 0.15 s per enum in each translation
unit that instantiates `to_enum`. It only covers 8-bit types.

**Smallest spec change.** State that `VERBS_ENUM` accepts `name = value`, and
that `to_enum` accepts exactly the listed values. Record the probe as the
measured alternative, rejected on cost, until reflection lands.

### M7. Value-initialization makes an out-of-domain enum with no cast. — major, §3.4 / §4 (outside my lens, found while probing)

```cpp
enum class PhaseKind : std::uint8_t { assembly = 1, attempt = 3, colleague_transport = 12 };
struct Node { PhaseKind kind; };
auto& n = nodes[7];      // std::map value-initializes: n.kind == PhaseKind{0}
// to_enum<PhaseKind>(to_underlying(n.kind)) is empty -> rc=42
```

`E{}`, `Node{}` and `map::operator[]` produce 0 with no cast for §4 to see.
Any verbs-domain enum whose enumerators exclude 0 can hold a non-member.

**Smallest spec change.** Add to §4: value-initialization or zero-
initialization of a verbs-domain enum that has no zero enumerator, including
through an aggregate or container.

### M8. The enum-candidate fix-it is wrong on the typical decoder, and the serialization disqualifier hides the right one. — major, §5 (adoption)

This is the best enum candidate in blackbird, and it shows both problems:
- **Consumer** `Node::kind` (src/token_usage.cpp:62) is compared against `3`
  and `12` in two functions, with no disqualifying use. It is a candidate with
  values {3, 12}. The suggested encoding, an enum with the observed values and
  `to_enum` at the ingress `node.kind = input.get<std::uint8_t>()`, would
  reject the legitimate kinds 1, 2, 4–11, 13 and 14. The observed set is a
  lower bound on the domain, not the domain.
- **Producer** `RawProviderPhase::start(std::uint8_t kind, ...)`
  (src/provider_original.cpp:58) receives every literal from 1 to 14 at 31 call
  sites in 8 files (coding, colleague, openai, openrouter, anthropic_provider,
  provider_auth, responses_provider, provider_original). This is the correct full
  domain. But `kind` goes straight into `raw_native_field(kind)`, a
  serialization call, so §5's "streaming or serialization calls" disqualifier
  drops it from the edit-boundary feed. Writing an enum out through
  `to_underlying` is fine; only reading it back in needs `to_enum`.

**Smallest spec change.** (a) Serialization on egress does not disqualify; only
deserialization into the subject is ingress. (b) When a candidate's ingress is
decoded bytes, the finding says the observed values are a lower bound and asks
for the full domain and the names. It never proposes `to_enum` over the
observed set alone.

### M9. `seen(0, 1, 3)` is shadow accounting, and two verdicts duplicate other things. — major, §7

The placement on the declaration is decided, and it reads well: the
rationale sits in view, the way a doc comment would. The macro compiles to
`[[clang::annotate("verbs:open_domain", why, 0, 1, 3)]]` on a field, and the
AST keeps the arguments (`decision.cpp`). The `seen(...)` list is the problem:
- It repeats in source the literal set that verbs computes from the code. That
  is exactly the obvious-stating annotation §1 forbids. Because a new value
  resurfaces the finding, the agent's cheapest move becomes "append the new
  value to `seen()`". The decision becomes a hand-kept ledger that grows with
  each resurfacing, and that move is the gaming pattern §4 warns about.
- It does not fit its own verdict. `open_domain` means new values are
  expected, so resurfacing on a new value fights the decision. The spec's
  example already disagrees with itself: "reserves 3-7 for future modes" next
  to `seen(0, 1, 3)`.
- §5's second resurfacing trigger, "every disqualifying use that justified an
  `open_domain` decision disappears", cannot fire. A subject with
  disqualifying uses is never a finding, so it never gets a decision.
- `accepted_pending` is a planned-work marker in source. Planned work belongs
  in bd. §7 itself says an obvious `rejected` points to a check defect, which
  leaves `rejected` with almost no proper use apart from `open_domain`.

Reads well:

```cpp
VERBS_OPEN_DOMAIN("1320 phase kind; producers own the domain (provider_original.cpp:443)")
std::uint8_t kind = 0;
```

Encumbers:

```cpp
VERBS_OPEN_DOMAIN("wire protocol reserves 3-7 for future modes", seen(0, 1, 3))
std::uint8_t kind;
```

**Smallest spec change.** One form, `VERBS_OPEN_DOMAIN("why")`, with no
`seen`. A decided subject resurfaces only when the decision text changes or is
removed (each a `!` line). Drop `accepted_pending` (file a bead instead), and
drop the dead resurfacing clause in §5. Keep `rejected` only if the tribunal
finds a non-obvious case for it.

### m1. Mixed-range expressions need casts that the spec does not provide. — minor, §3.1

`c ? a : b` with `Bounded<0, 3>` and `Bounded<2, 5>` fails with `incompatible
operand types` (m12). `std::max(a, b)` fails with `deduced conflicting types`
(m13). Both are common in classification code. **Change:** name the idiom
(widen one side explicitly to a common type). Do not add a `common_type`
specialization unless the corpus asks for one.

### m2. The `+=` constraint overflows `int64` at extreme bounds. — minor, §3.1

The sketch in §3.1 writes `requires (Lo <= Hi + B && Lo + A <= Hi)` in
`int64_t`. For `Bounded<0, INT64_MAX> += Bounded<0, 1>` this gives `error:
substitution into constraint expression resulted in a non-constant expression
... value 9223372036854775808 is outside the range` (`ovf.cpp`). **Change:**
compute the constraint in `__int128`, as the prose already says for result
bounds.

### m3. `Refined` uses a second error channel, and its `id` string is hand-kept. — minor, §3.2

`Refined::make` returns `std::expected<Refined, Violation>` while `make`,
`narrow` and `to_enum` return `optional`. `Violation` carries only the
predicate identity, which the type already names, so the `expected` carries
nothing extra, and in excerpts/c_refined.cpp it was simply dropped. `Pred::id`
is a string the author must keep in step with the type name. **Change:**
return `optional` everywhere. On Clang, take the identity from the type name
(`__PRETTY_FUNCTION__`, the same owned technique as M6) instead of a
hand-written `id`. Reflection replaces it later.

### m4. One deleted message cannot fit every context. — minor, §3.1

The narrowing message suggests `+=`, which is wrong for `return a - b;` (m17)
and for `Bounded<0, 5> x = k<7>;`. **Change:** keep the message generic
("narrowing: use narrow<B>, clamp<B>, or a checked compound assignment") and
give the constant case its own wording.

### m5. "Smallest signed type" doubles small unsigned fields. — minor, §3.1

`Bounded<0, 255>` is stored as `int16_t`, so a `uint8_t` field such as
`Node::kind` doubles in size. **Change:** use the smallest type, signed or
unsigned, that holds `[Lo, Hi]`.

### m6. Compile-time cost is fine for named types and real for varied shapes. — minor, §3.1 / §9

The generated TUs have 200 functions, each with 6 binary operations and one
`+=` (1,400 operations). CPU time is the minimum of 3 runs. Instantiation
counts come from `-ftime-trace` with granularity 0, taken from the `-O2`
compile (shared by all three rows).

| TU | parse CPU | -O2 CPU | InstantiateClass | InstantiateFunction |
|---|---|---|---|---|
| `int64_t` baseline | 0.21 s | 0.31 s | 33 | 20 |
| Bounded, few shared types | 0.24 s | 0.67 s | 51 | 41 |
| Bounded, fresh bounds per function (worst case) | 1.72 s | 4.40 s | 1,643 | 4,021 |

The worst case is about 3 function and 1.2 class instantiations per
operation, and about 1 ms of parse and 3 ms of `-O2` per operation. Real code
sits between the rows: a few named types, with distinct intermediate types per
expression shape. This does not block adoption. **Change:** none beyond
keeping the operators as free templates that compute bounds once.

---

## The three excerpts

### Counter and index loop: BRepGPU `cpu_adjacency` (native/topology.cpp:85-121)

Before (serial scan):
```cpp
std::uint32_t total = 0;
for (std::uint64_t e = 0; e < edge_count; ++e) {
    a.offsets[e] = total;
    total += counts[e];
    counts[e] = 0;
}
a.offsets[edge_count] = total;
```
After, vlib exactly as specified (compiles under `-Werror`):
```cpp
inline std::size_t at(Count i) { return static_cast<std::size_t>(i.get()); }
auto total = Count::lit<0>();
for (auto e = Count::lit<0>(); e < edge_count; e += One::lit<1>()) {
    a.offsets[at(e)] = static_cast<std::uint32_t>(total.get());
    auto c = Count::make(counts[at(e)]);
    if (!c) verbs::violation("degree count above MAX");
    total += *c;
    counts[at(e)] = 0;
}
a.offsets[at(edge_count)] = static_cast<std::uint32_t>(total.get());
```
After, with the proposed simplifications (S1–S4 below):
```cpp
Count total = verbs::k<0>;
for (auto e : verbs::upto(edge_count)) {
    a.offsets[e] = total;
    total += counts[e];          // checked: cannot pass MAX
    counts[e] = 0;
}
a.offsets[edge_count] = total;
```

Judgment: the spec-faithful version is clearly uglier and claims nothing the
reader can use. The simplified version reads like the original and states
that `total` never exceeds `BG_TOPOLOGY_MAX_COUNT`. Where `Bounded` really
earns its place in BRepGPU is the descriptor: `threads` in `Bounded<1, 24>`
and counts in `Bounded<0, MAX>`. Then `count*worker/threads` in `parallel()`
is proven free of overflow at compile time, which the current code only
implies. BRepGPU is C++17 with CUDA kernels, so vlib would also need
`__host__ __device__` on every member before it could reach the kernels. That
is out of the basics.

### Mode or state field: blackbird `Node::kind` (src/token_usage.cpp:62, 344-347, 591-595)

Before:
```cpp
struct Node { std::uint32_t site = 0; std::uint8_t kind = 0; /* ... */ };
node.kind = input.get<std::uint8_t>();
observation.actor = node.site == 3600 ? UsageActor::decision
                  : node.kind == 3    ? UsageActor::main
                  : node.kind == 12 || refusal ? UsageActor::colleague : UsageActor::unknown;
```
After (`enum class` with checked ingress; written with explicit values, which
the positional macro cannot take, M6):
```cpp
enum class PhaseKind : std::uint8_t { assembly = 1, retry_group, attempt, retry_wait, adapter,
    decode, preview_feed, presentation, receipt, acceptance, colleague_prepare,
    colleague_transport, sse_event, preview_event };
node.kind = need(verbs::to_enum<PhaseKind>(input.get<std::uint8_t>()));   // throws corrupt
observation.actor = node.site == 3600 ? UsageActor::decision
                  : node.kind == PhaseKind::attempt ? UsageActor::main
                  : node.kind == PhaseKind::colleague_transport || refusal ? UsageActor::colleague
                                                                         : UsageActor::unknown;
```

Judgment: clearer, without qualification. The domain moves from a
description string into the type, and a malformed trace becomes `corrupt`
instead of an unnamed byte. Two places hurt. The positional macro (M6). And
`Node` needs a default for `map::operator[]`, which with this enum silently
yields 0 (M7). `Node::site` (1300, 1320, 2403, 3600, ...) stays raw under the
macro.

### ID passed between functions: blackbird attempt, invocation and generation (src/token_usage.cpp:64, 352-391)

Before: `std::optional<IdentityBytes> attempt, invocation, generation;` with
site 2403 choosing the field by a raw `kind` 1, 2 or 3. After:
`std::optional<AttemptId>` and so on, with `node.invocation = InvocationId{id}`
selected by `IdentityRole::invocation`. The role enum is the real gain. The
`Id` wrap happens at the same line where a swap bug would be written, so it
protects only the readers downstream. blackbird's existing
`InvocationId::from_bytes` already does better (M5).

---

## Adoption: the smallest step into blackbird

1. **vlib basics do not need C++26.** The spec-faithful sketch, the excerpts
   and the probe all build with `-std=c++23` and blackbird's full warning set.
   The only error is the `= delete("…")` message (M2), which the header can
   guard. §3 says "header-only C++26". It should say the basics compile as
   C++23 on Clang 23, and C++26 adds reflection and annotations later. That
   removes the standard bump from blackbird's path.
2. **The first adoption is an enum, not `Bounded`.** Put one header with
   `PhaseKind` in place. Change the producer to `start(PhaseKind, ...)`: 31
   call sites in 8 files change a literal to an enumerator. Add one consumer
   ingress at blackbird's existing decoding seam,
   `template <class E> E Fields::get_enum()` (wrapping `to_enum` and
   `throw Error{ErrorCode::corrupt}`). That one function then serves every
   decoder. blackbird already does this checking by hand, for example
   `reason > static_cast<std::uint8_t>(ErrorCode::provider_rate_limit)` before
   `static_cast<ErrorCode>(reason)` (src/retained_events.cpp:580-586). That
   is exactly what `to_enum` replaces.
3. **The enum-candidate fix-it is a realistic first step only after M8.** As
   specified, it gives the wrong fix on the consumer (a subset domain) and
   hides the correct producer candidate behind the serialization
   disqualifier. With M8 fixed, the `start` candidate is the finding that
   leads to step 2.
4. **`Bounded` comes later,** at descriptor and limit fields
   (`limits_.max_causal_depth`, counts), and in loops only once S1–S4 exist.
   `Id`: none, because blackbird's own is better.

## Simplifications (they keep every invariant)

- **S1.** Replace `lit<V>()` with `verbs::k<V>` (`Bounded<V, V>`), which
  widens. One name, no `template` keyword, and it doubles as the literal
  operand.
- **S2.** Add `verbs::upto(n)`, the half-open range yielding
  `Bounded<0, N-1>`. No `++`.
- **S3.** Allow implicit egress to integral types that hold `[Lo, Hi]`.
- **S4.** Let `+=`/`-=` take raw integral operands with the same check. With
  S1–S4, `make` is needed only where the caller handles failure.
- **S5.** Return `optional` from every ingress (`Refined::make` too). Consider
  one name for all of them (`verbs::to<T>(x)` covering `make`, `narrow` and
  `to_enum`), because a reader then learns one verb.
- **S6.** Specify the deleted-with-message overloads that make the promised
  diagnostics real.
- **S7.** Store in the smallest signed or unsigned type.

Flexibility nobody needs:
- **`Id`** as a vlib type (M5).
- **`seen(...)`**, **`accepted_pending`**, and probably **`rejected`** (M9).
- **`std::expected` / `Violation`** on `Refined` (m3).
- **`verbs::clamp`**: neither corpus excerpt wanted saturation. Keep it only if
  a corpus site does.
- **`lit` and `make` as two ingress spellings on every instantiation**, once
  `k` exists.

## What reads well, and should stay

- `enum class` with `to_enum` at decode sites. This is the strongest,
  cheapest value in the basics.
- No raw-integer constructor and no default constructor: both are sound and,
  with S6, clearly diagnosed.
- Widening arithmetic on descriptor-scale values: it proves overflow freedom
  for free (`count*worker/threads`).
- The current diagnostics for an out-of-range constant and a disjoint `+=`,
  which print the failing inequality.
- The decision rationale on the declaration, as a plain sentence.
