# External review: ChatGPT (codex exec, gpt-6.1-sol, xhigh), SPEC revision 2 + Jev fixes

2026-10-17. Read-only sandbox over a bundle of SPEC.md, BLACKBIRD.md, the tribunal reports, the escape paper, toolchain papers, the operator decisions, the prototypes and a blackbird snapshot. Prompt: context/reviews/prompt.md. Section 5 excluded. Report verbatim below.

---

Revision 2 still has soundness holes. The escape prototype misses four representation bypasses that compile on the pinned Clang, and the specified cache can retain `holds` after the checked source changes.

I worked read-only and excluded section 5. Compiler probes used Homebrew Clang 23.1.2 with `-std=c++2c`; inputs and LLVM output went through pipes. The production `verbs check` implementation is absent, so pipeline findings below are deductions from the specified algorithms.

**F01 — BLOCKER — §2.1 rule 3; §4, lines 307–312: the boundary assumes the condition the escape check must establish.**

The boundary assumes that “mutation goes only through that type’s operations,” while §4 promises to detect mutations that bypass those operations. Read literally, this excludes every representation-write counterexample before the checker examines it, making escape soundness circular.

**Counterexample:** §1.1 names “writes that bypass the representation” as detectable defects, but §2.1 excludes those same executions by assumption.

**Smallest fix:** distinguish exclusive ownership, which is assumed, from permitted mutation paths, which the escape check must establish. The following bypass findings use that intended interpretation; they involve one owner and no memory-safety violation.

**F02 — BLOCKER — §4.1 rule 1, lines 330–336: a const byte pointer is not a read-only capability.**

The exception permits a const byte view to escape, after which removing constness mentions no vlib type. Writing through that pointer is legal when the original object is mutable.

For this and subsequent enum examples, assume a verbs enum `E` with underlying type `unsigned char` and named values `{0, 1}`:

```cpp
E e = E::a;
const auto* p = reinterpret_cast<const unsigned char*>(&e);
*const_cast<unsigned char*>(p) = 7;
return std::to_underlying(e);
```

The prototype reports zero escapes. With ASan and UBSan enabled at `-O2`, Clang reduces this function to returning 7. This does not rely on an invalid C++ enum representation: a fixed-underlying enum has the values and representation of its underlying type. [C++ draft, enumeration declarations](https://eel.is/c++draft/dcl.enum#8)

**Smallest fix:** remove the unrestricted exception. Permit erased const pointers only in uses established to be read-only and non-escaping, such as direct arguments to known read-only sinks. Otherwise report the escape.

**F03 — BLOCKER — §4.5, lines 401–403: trusting libc++ internals leaves a writable-byte API unchecked.**

The specification says library internals are judged at their typed API, but supplies no rule for a typed API that returns writable representation access. `std::as_writable_bytes` performs its dangerous cast inside the excluded library implementation.

```cpp
E e = E::a;
auto bytes = std::as_writable_bytes(std::span{&e, 1});
bytes[0] = std::byte{7};
return std::to_underlying(e);
```

The prototype reports zero escapes; sanitized optimized LLVM returns 7. The installed libc++ implementation contains the writable reinterpretation in `span::__as_writable_bytes`, and the standard specifies that effect. [C++ draft, views of object representation](https://eel.is/c++draft/span.objectrep)

**Smallest fix:** explicitly reject typed library operations that expose writable representations of vlib objects. Excluding a function’s implementation must not imply trusting its effect.

**F04 — BLOCKER — §4 introduction and §4.1 rules 1–3, lines 314–318 and 330–343: pointer representations can lose their type through values.**

The rules cover pointer-to-pointer erasure, but omit pointer-to-integer erasure; the transitive definition also deliberately stops at pointers, so pointer-valued `bit_cast` escapes its stated filter.

```cpp
E e = E::a;
auto address = reinterpret_cast<std::uintptr_t>(&e);
*reinterpret_cast<unsigned char*>(address) = 7;
```

A second spelling on the pinned target is:

```cpp
E e = E::a;
*std::bit_cast<unsigned char*>(&e) = 7;
```

Both compile, both produce zero prototype findings, and both sanitized optimized functions return 7. A direct `E{7}` positive control in the same prototype invocation is caught.

**Smallest fix:** include conversions of pointers to vlib-containing objects into integers and pointer-valued bit reinterpretations. Match those operations explicitly; they do not reduce to the claimed single pointer-cast AST case.

**F05 — BLOCKER — §4.3 rule 9, lines 366–370: macro names are treated as authority.**

The `VERBS_*` exemption does not require the expansion to originate from a trusted vlib macro definition. User code can put a forbidden specialization behind such a name.

```cpp
#define VERBS_FORGE()                                      \
namespace verbs {                                          \
template<> class Bounded<0, 5> {                            \
    int value_;                                            \
public:                                                    \
    explicit Bounded(int v) : value_(v) {}                  \
    int get() const { return value_; }                     \
};                                                         \
}

VERBS_FORGE()

void f() {
    verbs::Bounded<0, 5> value{7};
}
```

This variant produces zero prototype findings. Its `fromVerbsMacro` implementation checks only whether the immediate macro name starts with `VERBS_`. Redefining an actual exported macro is another route.

**Smallest fix:** exempt only expansions originating from identified vlib macro definitions. Detect replacement or undefinition of those definitions; never grant trust by prefix.

**F06 — BLOCKER — §4.8, lines 433–437: exact-type invalidation does not cover nested claims.**

The escape definition is transitive, but attribution only says to invalidate declarations of the affected type. Corrupting a containing object also corrupts claims on its component types and copies subsequently made from them.

```cpp
struct Packet { E kind; };

Packet packet{E::a};
std::memset(&packet, 7, sizeof packet);  // affected static type: Packet
E copy = packet.kind;                   // copy now contains 7
```

Invalidating only `Packet` declarations leaves `Packet::kind` and `copy`, both of type `E`, eligible for `holds`. This is a literal consequence of the attribution rule; the prototype does not implement claim attribution.

**Smallest fix:** invalidate every affected leaf vlib type, then every claim containing one of those leaves. Specify this closure explicitly rather than leaving “affected type” to implementation judgment.

**F07 — BLOCKER — §6.2 step 2, lines 523–526: size and mtime are not a content identity.**

The stored content hash is not checked when size and mtime remain unchanged. A same-length edit with a restored timestamp therefore preserves obsolete facts.

**Counterexample sequence:**

1. Check a function containing `E e = E::a;`; its claim holds.
2. Replace `E::a` with `E{7}`. These spellings have equal length.
3. Restore the file’s previous mtime.
4. Run `verbs check`.

The specified algorithm reuses the old facts; a fresh scan finds enum ingress. Restoring timestamps requires no undefined C++ behavior and is not excluded by the boundary.

**Smallest fix:** validate input content on every run. Treat size and timestamps as optimization hints only when backed by a stronger change-detection guarantee.

**F08 — BLOCKER — §6.2 compile errors; §6.6 pending units; §10.2 incremental oracle: historical facts can remain current claims.**

Retaining old facts without revoking their current `holds` state conflicts with the four-state claim model and program-wide escape attribution. A pending unit can contain an escape affecting declarations in already refreshed units.

**Counterexample sequence:**

1. Establish `holds` for an enum used across several units.
2. Make enough units stale to exceed ten seconds; put an enum-ingress escape in a unit processed after the cutoff.
3. Run `verbs check`, then make no further edits.

The escape is never examined, because pending work only resumes on another invocation. Meanwhile, the report retains old facts. Separately, after a compile-breaking edit, an incremental run retains historical facts that a genuinely fresh scan cannot possess, so the equality oracle cannot hold as written.

**Smallest fix:** keep historical facts solely for historical delta presentation. Current claims depending on incomplete analysis must lose `holds`. For the stateless basics, the smallest completion rule is to finish the required analysis and use ten seconds as an activation criterion, rather than a correctness cutoff.

**F09 — BLOCKER — §10.3, lines 749–755: mandatory Jev labeling introduces a terminal model dependency.**

The required second label has no model-free alternative, yet the precision gate depends on the labeling process. This contradicts the binding decision that every function must work with no model available.

**Quoted contradiction:**

> “Jev gives an independent second label.”

versus the operator’s decision:

> “No part of verbs may depend terminally on an LLM.”

**Counterexample:** the operator supplies all primary labels, but Jev is unavailable. The specified validation process cannot finish.

**Smallest fix:** make Jev optional, with operator review sufficient to complete the gate.

**F10 — BLOCKER — §1.1, lines 56–84: the kill criterion still lacks a reproducible pass/fail experiment.**

Naming a migration and defect classes improves the original draft, but “meaningfully” and “measurable effect” still have no operational definition. The spec does not define the baseline, detection event, edit count, handling of undetected faults, or success threshold.

**Counterexample:** one evaluator counts compiler diagnostics as detection; another counts only `verbs` output. Both follow §1.1, but can reach opposite conclusions because much of vlib’s benefit arrives through compilation. “An enumerator added without matching ingress” also needs a concrete post-migration seed, since generated ingress normally updates automatically.

**Smallest fix:** add a short experiment definition: paired baseline/treatment, named equivalent seeds, independent fault oracle, precise detection event and edit-count rule, treatment of censored runs, and a predeclared success threshold. A bead does not supply those definitions.

**F11 — MAJOR — §4.7, lines 422–429: weakening detection can be bypassed in two edits.**

The baseline tracks only previous `holds` claims. Once an escape changes a declaration to `finding`, the next edit can remove its invariant without producing another lost-claim finding.

**Counterexample sequence:**

```cpp
// Run 1: holds
E e = E::a;

// Run 2: finding; no longer in the holds baseline
E e = E{7};

// Run 3: old escape resolves; no previous holds claim to lose
unsigned char e = 7;
```

**Smallest fix:** compare declared predicates across reports regardless of whether their previous state was `holds`, `finding`, or `outside`. Proof failure must not erase the declaration’s weakening baseline.

**F12 — MAJOR — §4.1 rules 1 and 4, lines 330–347: the same-type byte-copy exception is both unsafe and inconsistent.**

Same source and destination types do not establish a valid whole-object copy; a partial copy can combine two valid representations into an unnamed enum value. Meanwhile, rule 1 independently flags the destination conversion even for a legitimate complete copy.

For a verbs enum `W : std::uint16_t` with values `{0, 1, 256}`:

```cpp
W destination = W::b;  // 256
W source = W::a;       // 1
std::memcpy(&destination, &source, 1);
```

On this little-endian target, the result is 257; sanitized optimized LLVM confirms that return value. The standard’s same-value copying guarantee concerns copying the object’s underlying bytes, not arbitrary partial transfers. [C++ draft, trivially copyable types](https://eel.is/c++draft/basic.types.trivial#4)

The prototype currently catches this through type erasure, but also catches complete same-type copies that rule 4 says are exempt.

**Smallest fix:** either remove the user-code byte-copy exception, or require a proven complete-object transfer and make its relationship with rule 1 explicit.

**F13 — MAJOR — §4.4, lines 385–393: ordinary overloads are classified as cross-unit mismatches.**

Qualified name is not function identity. Multiple legitimate overloads have different canonical signatures under the same name.

```cpp
E select(E value) { return value; }
int select(int value) { return value; }
```

The prototype emits:

```text
FACT fn|select|enum E (enum E)|1
FACT fn|select|int (int)|0
```

The supplied comparator consequently satisfies its mismatch condition. Putting the definitions in separate units does not make them conflicting declarations.

**Smallest fix:** group functions by linkage identity, preserving overload distinctions, and compare signatures only within that identity. Alternatively, defer general ODR checking under the existing no-UB boundary.

**F14 — MAJOR — §10.2 audit oracle, line 738: the independent escape oracle does not observe enum-domain violations.**

Enums have no vlib `get()` accessor, and ASan/UBSan do not enforce membership in a list of enumerators for fixed-underlying enums. Thus the oracle misses the first increment’s principal fault class.

**Counterexample:** execute any of F02–F04 and inspect the result with `std::to_underlying`. The audit accessor is never called, and the sanitized optimized probes return 7 without a domain check.

**Smallest fix:** add explicit enum-domain observations to the audit fixtures and migrated decoder tests, using independently written expected sets. State the remaining observational limits; sanitizer execution alone is not an enum escape oracle.

**F15 — MAJOR — §1.1 migration, lines 64–78: the proposed common decoding seam is not common, and some guards encode narrower domains.**

The named `Fields` class is local to `token_usage.cpp`; journal decoding uses free byte-reading functions, and retained-event decoding uses a separate `Decoder`. A universal replacement also cannot discard guards that express a subset of an enum’s domain.

**Checked counterexamples:**

- `blackbird/src/token_usage.cpp:25–59` defines anonymous-namespace `Fields`.
- `blackbird/src/journal.cpp:278–279` returns `unsupported` for an unknown frame kind; the proposed helper throws `corrupt`.
- `blackbird/src/retained_events.cpp:548–549` admits only `{2,3,4,14}` for an identity-conflict subject. `RetainedKind::retry` is 7, so `verbs::to<RetainedKind>(7)` succeeds while the existing field guard rejects it.

**Smallest fix:** specify migration per actual seam, preserving byte widths, error behavior, and narrower field guards. Shared enum membership checking can operate on the already decoded integer; it need not replace the readers.

**F16 — MAJOR — §6.4 keys, lines 559–570: internal overloads collide, and local declarations have no defined key.**

Path plus qualified name does not distinguish overloaded internal functions. Automatic locals generally have no linkage, so neither linkage row defines their identity.

```cpp
static E convert(int)    { E value = E::a; return value; }
static E convert(double) { E value = E::a; return value; }
```

Both functions receive the same specified internal key. Corresponding escapes also collide when their construct class and ordinal match; shadowed locals introduce another unresolved identity case.

**Smallest fix:** include the function signature in internal-function keys. Define local and field identities through their enclosing entity and scope, and limit stability promises where ordinal identities necessarily change.

**F17 — MAJOR — §3.3 `upto`, lines 281–283: the zero-maximum case requires an invalid value type.**

The helper accepts `Bounded<L,N>` whenever `L >= 0`, including `Bounded<0,0>`, but promises elements of type `Bounded<0,N-1>`.

```cpp
for (auto i : verbs::upto(verbs::k<0>)) {
    // Must compile and execute zero iterations.
}
```

Its specified element type is `Bounded<0,-1>`, which the same section requires to fail compilation.

**Smallest fix:** define the zero-maximum case explicitly as an empty range with a valid element type. Add this case to the helper’s direct oracle.

**F18 — MAJOR — §6.1 exit codes and §7 gate: simultaneous conditions have no precedence.**

An edit can introduce both an escape requiring exit 1 and a decision requiring exit 3. Since the caller acts only on exit status, choosing exit 1 bypasses the mandatory decision-approval path.

**Counterexample:** one valid edit adds a `VERBS_OPEN_DOMAIN` annotation and, elsewhere, `E bad{7};`. Both exit conditions apply.

**Smallest fix:** specify that decision additions or changes take exit-code precedence, while all findings remain in stdout. Also define precedence for analysis failure.

**F19 — MINOR — §2, lines 90–98: predicates for containing objects are undefined.**

A containing declaration can hold several different leaf predicates, but the claim grammar supplies only one range or one enum set.

```cpp
struct Pair {
    verbs::Bounded<0, 5> count;
    E mode;
};
```

What predicate belongs to a declaration of `Pair`, or to an empty `optional<Pair>`?

**Smallest fix:** define claims on leaf projections, with element-wise and engaged-alternative conditions, or restrict claim subjects to leaf declarations while retaining transitive types for escape detection.

**F20 — MINOR — §6.5 example, lines 576–578: the output teaches the retired zero policy.**

The example reports value-initialized `PhaseKind` as an escape because zero is not a value. Section 3.2 now guarantees that zero is named and included in the claim.

**Counterexample:** `PhaseKind phase{};` is sound under the adopted zero-state rule, but the sample diagnoses precisely that construction.

**Smallest fix:** replace the sample with an actual remaining escape.

**F21 — MINOR — §3.3 ingress and §10.1, lines 248–249 and 729: the accepted integral source set needs one definition.**

“Any integral” includes types the test table says must be rejected. “Character types” is also too broad without qualification: on this target, `std::uint8_t` is `unsigned char`, which is used at the proposed decoding seam.

**Counterexample:** the API description admits `verbs::to<Bounded<0,1>>(true)`, while the test table requires compile-time rejection.

**Smallest fix:** list the accepted source types once and make both API requirements and rejection tests refer to that definition.

The earlier blockers not fully retired are:

- **Soundness B1/B2 and checks B3:** the listed original examples are caught, but representation access remains open through F02–F04; transitive attribution remains incomplete in F06.
- **Soundness B4/B5:** ordinary specializations and theft are addressed, but macro-origin trust reopens specialization injection in F05.
- **Checks B1:** `--changed` is now only a hint, but cache validation and incomplete runs still defeat current analysis in F07–F08.
- **Doctrine D1:** the migration is now named, but the kill criterion still lacks a reproducible experiment in F10, and its migration description needs the corrections in F15.

Deferring `Refined` removes soundness B7 from the basics. The original enum list-initialization and zero-initialization holes have direct rules now. The `upto` direction addresses ergonomics B1’s terminal increment, subject to F17.

The basics also retain machinery they do not yet need: the full `Bounded` arithmetic surface before a consumer is named; general cross-unit ODR checking despite the no-UB boundary; and mandatory model labeling. Requiring `constinit` indiscriminately also adds ceremony for enums whose zero state is already valid and for objects Clang can establish are constant-initialized.

| ID | Severity | Section | One-line summary |
|---|---|---|---|
| F01 | BLOCKER | §2.1, §4 | The boundary assumes permitted mutation paths instead of requiring the check to establish them. |
| F02 | BLOCKER | §4.1(1) | Const byte views can be legally converted back to writable views. |
| F03 | BLOCKER | §4.5 | `std::as_writable_bytes` hides representation access in excluded library code. |
| F04 | BLOCKER | §4.1 | Pointer-to-integer and pointer-valued bit reinterpretation bypass the proposed cases. |
| F05 | BLOCKER | §4.3(9) | A `VERBS_*` name grants untrusted macro expansions an exemption. |
| F06 | BLOCKER | §4.8 | Exact-type invalidation misses affected component and containing claims. |
| F07 | BLOCKER | §6.2 | Same-size, same-mtime edits preserve obsolete claims. |
| F08 | BLOCKER | §6.2, §6.6, §10.2 | Incomplete runs retain historical claims and may never examine the final edit. |
| F09 | BLOCKER | §10.3 | Mandatory Jev labeling contradicts the model-free requirement. |
| F10 | BLOCKER | §1.1 | The kill criterion lacks defined measurement and pass/fail conditions. |
| F11 | MAJOR | §4.7 | Introducing a finding before downgrading a type defeats weakening detection. |
| F12 | MAJOR | §4.1(1,4) | Same-type partial copies are unsafe; complete copies conflict with type-erasure rules. |
| F13 | MAJOR | §4.4 | Qualified-name grouping mistakes legitimate overloads for mismatches. |
| F14 | MAJOR | §10.2 | The audit oracle cannot observe ordinary enum-domain violations. |
| F15 | MAJOR | §1.1 | The migration conflates distinct readers, error policies, and field domains. |
| F16 | MAJOR | §6.4 | Internal overload keys collide and local declaration keys are undefined. |
| F17 | MAJOR | §3.3 | `upto(k<0>)` requires the forbidden type `Bounded<0,-1>`. |
| F18 | MAJOR | §6.1, §7 | Exit-code precedence does not protect the decision gate. |
| F19 | MINOR | §2 | Claims on aggregates and optional values lack predicate semantics. |
| F20 | MINOR | §6.5 | The output example diagnoses the zero initialization now explicitly allowed. |
| F21 | MINOR | §3.3, §10.1 | Integral source acceptance differs between the API and its tests. |