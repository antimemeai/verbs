# The closed representation rule: provenance as type

Date: 2026-10-17. Lane: escape-v2 (replaces SPEC §4.1, §4.5, §4.8). Inputs:
design/SPEC.md rev 3 §2–§4; papers/2026-10-17-escape-allowlist.md (v1); the
ChatGPT review (F02–F06, F12) and the MiMo `const void*` variant. Toolchain:
Homebrew LLVM 23.1.2 (`/opt/homebrew/Cellar/llvm/23.1.2`), `-std=c++2c`,
sysroot from `xcrun --show-sdk-path`. Artifacts copied to
context/prototypes/escape-v2/ (detector `src/verbs_escape2.cpp`, 725 lines;
`cases/`, `legit/`, `break/`, `vlib/`, `build.sh`). Nothing committed; nothing
written into blackbird.

v1's §4 was an allowlist *in name* but still enumerated bad spellings per AST
node, and two external reviewers broke it: a `const` byte view could be
`const_cast` and written (F02); `std::as_writable_bytes` did the reinterpret
inside libc++, which §4.5 trusted (F03); a pointer could lose its type through
an integer or a pointer-valued `bit_cast` because the recursion stopped at
pointers (F04); a `VERBS_*`-named user macro was trusted by prefix (F05);
attribution voided only the exact type, not its leaves or copies (F06); and a
same-type partial `memcpy` forged an out-of-domain value (F12).

This lane states one closed rule, **pointer provenance as type**, grounds every
clause in a Clang 23 AST node, and measures it: every v1/v2 counterexample
(48 cases), eight fresh self-attacks, and a 15-program legitimate corpus that
stresses libc++ with vlib types.

---

## 1. The rule

A **vlib type** is a `verbs::Bounded` specialization or a verbs enum (§3.2).
Two reachability notions, both transitive:

- **vlib-containing** (the object-representation notion, unchanged from §4):
  a vlib type, or an array / class-by-member-or-base / standard wrapper of one.
  Recursion **stops at pointers**: `E*` is not vlib-containing.
- **vlib-pointer value (vpr)** (new): a pointer, reference, or
  pointer-to-member to a vlib-containing type, or any aggregate/wrapper that
  transitively **holds** such a pointer (`shared_ptr<E>`, `span<E>`,
  `initializer_list<E>`). Recursion here does **not** stop at pointers. A plain
  vlib *value* (`E`, `B5`) is not vpr; only something that *reaches* a vlib
  object by indirection is.

> **Provenance as type.** A vpr expression — anything through which a vlib
> object's storage is reachable by pointer or reference — may be converted only
> to the same pointer/reference type, its cv-added form, or a base subobject.
> Every other conversion loses provenance and is an **escape**: to `void*`, to
> a byte type, to an integer, to a different vlib type, by `bit_cast`, by a
> reference reinterpret, by a pointer-to-member reinterpret, or by rewrapping
> into a type-erased wrapper (`shared_ptr<void>`). Because the rule is on *vpr*,
> reading a value out of a vlib object (`get()`, `to_underlying`, the egress
> operator) is never a conversion of a vpr and is never touched.

> **One narrow exception (read-only sink).** An erased *const* pointer that is
> the **direct argument expression** of a call to a function declared outside
> the repository, whose matching parameter is pointer/reference-to-`const` and
> whose return type is not a pointer, is a read, not an escape. That admits
> `fwrite(&b,…)`, `write`, `memcmp`, a `(const void*, len)` hasher, and
> `ostream << &e`. It admits nothing a user can write through: the moment the
> erased pointer is bound to a named variable (`const unsigned char* p = …`)
> it is no longer a pure argument, so F02 and hand-rolled byte hashing are
> escapes.

> **Raw writes.** `memcpy`/`memmove`/`memset` and their builtins into
> vlib-containing storage, **except** a `memcpy`/`memmove` whose source and
> destination pointee are the *same* vlib type **and** whose length is a
> constant whole multiple of that type's size. A partial copy (F12), a
> non-constant length, or a source that carries a vpr value into a mismatched
> slot is an escape. The implicit `T*→void*` of the `memcpy` arguments is
> judged here, not twice by the provenance rule, so a legitimate whole-object
> copy is clean and a partial one is caught exactly once.

> **Library entry points that expose representation.** A small, closed list of
> standard APIs returns writable (or `const_cast`-able) representation of their
> argument without any cast in user code, because the reinterpret is inside
> libc++: `as_writable_bytes`, `as_bytes` ([span.objectrep]),
> `bit_cast` ([bit.cast]), `start_lifetime_as`/`_array` ([obj.lifetime]),
> `reinterpret_pointer_cast`/`static_pointer_cast` to a different element
> ([util.smartptr.*.cast]), `__builtin_assume_aligned`, and the writing atomic
> builtins (`__atomic_store`, `__builtin_arm_str*`). A call to one whose
> argument is vpr or vlib-containing is an escape. This list is **closable from
> the standard's text** (see §4): it is exactly the functions whose *specified
> effect* is to hand back a differently-typed view of an object's bytes.

Enum ingress, unions, `asm`, verbs specializations, private-member theft,
keyword macros, non-`constinit` statics, and the narrow bit-field are as in
SPEC §4.2–§4.3 (rev 3 already adopts macro trust by definition location,
closing F05). This paper changes §4.1 (the two reachability notions and the
provenance rule), §4.5 (the entry-point list replaces wholesale trust of
libc++), and §4.8 (attribution closure, below).

### Attribution closure (§4.8)

An escape whose sink has a known vlib-containing static type `T` voids every
**leaf vlib type** contained in `T`, then every claim whose type contains one
of those leaves, program-wide. An escape whose sink type is **erased**
(`void*`, a byte type, an integer, an opaque wrapper) voids every vlib claim in
the unit. Measured on F06: `memset(&packet, …)` on `struct Packet{E kind;}`
voids `E`, `Packet::kind`, `packet`, and the later `E copy` — and leaves a
sibling `F other` and `B5 bounded` holding (6 claims, 4 voided).

---

## 2. AST grounding

Every clause is a node the compiler already built; the spelling an agent
chooses collapses to it. Confirmed by `-ast-dump` on the pinned Clang:

| Clause | AST | note |
|---|---|---|
| `T*→void*`, `T*→byte*` (implicit or explicit) | `CastExpr` kind `CK_BitCast` | one node for `fread`, `void*` args, `static_cast`, C-style |
| `T&→byte&` | `CK_LValueBitCast` | reference reinterpret (F02 strips the const later) |
| `T*→uintptr_t` | `CK_PointerToIntegral` | **F04**: v1 had no rule; here it is `fromVpr && !toVpr` |
| `E Packet::*` → `uchar Packet::*` | `CK_ReinterpretMemberPointer` | n07 |
| `dynamic_cast<void*>` | `CK_Dynamic` | n18 |
| `__builtin_bit_cast` | `BuiltinBitCastExpr` `CK_LValueToRValueBitCast` | source/result vpr or vlib |
| `std::bit_cast<uchar*>(&e)` | `CallExpr` to `bit_cast`; **arg** `&e` is vpr | **F04b**: judged on the argument's vpr-ness, not the result |
| `std::bit_cast<uintptr_t>(H{&e})` | arg `H` is vpr (holds `E*`) | n16: the vpr walk does not stop at the stored pointer |
| integral→enum, any spelling | `CK_IntegralCast` to the enum | one node for `E{raw}`, `E(raw)`, `static_cast`, designated init |
| `shared_ptr<E>→shared_ptr<void>` | `CXXConstructExpr`, no cast node | leaf set `{E}`→`{}` = erasure |
| `as_writable_bytes(span<E>)` | `CallExpr`; reinterpret is in libc++ | **F03**: judged at the named entry point |
| `scanf("%hhu",&e)` | `CallExpr`, `FD->isVariadic()`, `&e` past fixed params | no conversion node; judged as a variadic vpr write |

The provenance test is four lines: `fromVpr && !toVpr` → erase (unless the
read-only sink or a `memcpy` arg); `!fromVpr && toVpr` → re-type; both vpr with
different pointee vlib type → re-type; same type → allowed.

---

## 3. Results

Detector `verbs_escape2`, a `ClangTool` + `RecursiveASTVisitor` (register verbs
enums by the `verbs_enum_info(E)` hook, then detect) + `PPCallbacks` for keyword
and vlib-macro redefinition + an attribution pass. Each case carries its
expected verdict as a comment written before the detector ran, and each bypass
was first compiled and run under ASan/UBSan at `-O2` to confirm it forges the
value (7, or 257 for F12) with the detector reporting nothing — i.e. the attack
is real, not hypothetical.

**Counterexamples — all caught (clean cases stay clean):**

| Group | Cases | Result |
|---|---|---|
| ChatGPT/MiMo review | F02 (const view + const_cast; const void*+memset), F03 (`as_writable_bytes`; `as_bytes`+const_cast), F04 (uintptr; `bit_cast<uchar*>`), F05 (`VERBS_FORGE`; redefine `VERBS_ENUM`), F06 (`memset` of a container), F12 (partial `memcpy`) | 10/10 caught |
| v1 tribunal ports (enum-domain) | fread, malloc+launder, 5 enum list-init spellings, enum bit-field, non-constinit static, specialize class/member, private-member theft, `#define private`, asm, union+bitcast+retype nest, placement/construct_at, writable-vs-readonly view, void* probe | 20/20 caught |
| fresh self-attacks | sscanf/va_arg (variadic), `shared_ptr<void>`, `reinterpret_pointer_cast`, pointer-`memcpy`, pointer-union, member-pointer, `__atomic_store`, `__builtin_memcpy_inline`, `__builtin_assume_aligned`, `string_view`+const_cast, reference/C-style/char8_t casts, `bit_cast` of a struct-of-pointer, user-template cast, `dynamic_cast<void*>`, container-of offset, macro-hidden cast, `vector::data`, `bit_cast`-into-enum, span-const-elem + const_cast | 25/25 caught |
| boundary-excluded (correctly not an escape) | function-pointer reinterpret + call (UB), `ostream<<&e` (read-only sink), pmr buffer memset (see §5) | as expected |

**Legitimate corpus — zero false escapes on 13 programs, all compiled and run:**

`optional<B5>`/`optional<E>` (emplace, value_or); `vector<Rec>` with push/
insert/erase/`sort`/`stable_sort`/`ranges::sort`/`find`/`reverse`/`rotate`/
`unique`/reserve/swap; `map`/`set`/`unordered_map`/`unordered_set` with vlib
keys and values and a user `std::hash<B5>`; `variant`/`expected`/`tuple`/`pair`
+ `visit` + structured bindings; `std::array`/C-array + `fill` + `span<const E>`
+ `ranges` + typed `copy`; `std::format` with `verbs::name` and a user
`formatter<E>`; `atomic<E>` load/store/exchange/CAS; `shared_ptr`/`unique_ptr`/
`weak_ptr`/`std::function` of vlib; `deque`/`list`/`forward_list`/`vector<E>(n)`;
`constinit` statics + value-serialization round-trip; typed pointer/reference/
base/`launder`/`addressof` controls; same-type whole-object `memcpy`;
`std::any` of E and of a vlib struct. **Reported escapes: 0.**

**The price of dropping v1's broad read-only exception (measured):** exactly one
legitimate v1 idiom flips to a finding — hashing by binding a `const unsigned
char*` to a named variable and looping (`p01`). The narrow exception keeps
`fwrite(&b,…)`, `write`, `memcmp`, address-printing, and any `(const void*,len)`
hasher clean (`p02`, the `ostream` case). So dropping the *broad* exception
(any const pointee target) costs one byte-loop idiom; keeping the *narrow* one
(const pointer as a direct system-sink argument) buys every real read sink and
cannot be abused, because the admitted pointer is never materialized. The
migration replaces the byte loop with a value hash (`to_underlying`/`get`) or a
direct hasher call.

**Build cost.** On an identical libc++-heavy TU (`unordered_map`+`vector`+
`sort`+`optional`), user CPU per unit: plain `clang -fsyntax-only` ≈ 0.55 s;
v1 prototype ≈ 1.02 s; **v2 ≈ 1.02 s**. The closed rule costs nothing over v1
despite `getParents` lookups and leaf-set computation — AST traversal dominates
equally, and the analysis roughly doubles the parse. (The `verbs check`
implementation shares one parse with the compile, so the real per-unit delta is
the ~0.5 s of traversal, not a second parse.)

---

## 4. Why the entry-point list is closed, not open

The reviewers' recurring win was an *open* deny-list. Three candidates were
evaluated by measurement, not argument:

- **Scan all libc++ instantiations + allowlist the safe ops** (principle 2).
  Rejected: it lights up on every benign internal reinterpret — `vector`
  relocation `memcpy`, `optional`/`variant` union storage, `construct_at`'s
  placement `new` — so it needs an allowlist of *safe* internals that is itself
  open and large, and attribution to the outer call site is fragile. The seven
  legitimate libc++ programs would each need bespoke exemptions.
- **Judge libc++ at its typed API, plus a closed list of APIs that expose
  representation** (principle 3, adopted). The dangerous set is the functions
  whose *specified effect* is to return a differently-typed view of an object's
  bytes. The standard names them in a handful of clauses:
  [span.objectrep] (`as_bytes`, `as_writable_bytes`), [bit.cast] (`bit_cast`),
  [obj.lifetime] (`start_lifetime_as`), [util.smartptr.shared.cast]
  (`reinterpret_pointer_cast`, `static_pointer_cast`), plus the compiler
  builtins that do the same (`__builtin_assume_aligned`, writing atomics).
  Every *other* libc++ operation either stays typed (`sort`, `find`, container
  insert/erase move or copy whole valid objects) or constructs from a valid
  same-type value (`optional`, `variant`, `construct_at` with a value arg) —
  none hands raw bytes back. The list is short because the language gives few
  ways to *name* a reinterpretation, and provenance-as-type already covers
  every reinterpretation a user writes directly. `launder` and `addressof` are
  **not** on the list: they return the *same* type, so they lose no provenance;
  the `void*→T*` they are usually paired with is the escape, caught by the
  provenance rule.

The closure argument: a library function can expose vlib bytes only by (a)
returning a pointer/reference/span of a different type aliasing the argument —
these are the listed clauses — or (b) doing a reinterpret in a body the user
can reach, which the provenance rule catches wherever that body is in scope.
Code defined in no analyzed unit is `outside` by SPEC §4.4, not `holds`.

---

## 5. Remaining holes, and whether the boundary excludes them

1. **Function-pointer reinterpret + call** (n08). `reinterpret_cast<void(*)(E*)>`
   then calling it is UB ([expr.call] — the function type must match). Covered
   by claim-boundary rule 8 (no UB outside vlib; UBSan flags it, as it did
   here). Not an escape-check matter: no vlib pointer loses its type; the `E*`
   is passed correctly-typed.
2. **Allocator aliasing / pmr over a user byte buffer** (n12). The user places a
   `monotonic_buffer_resource` over their own `unsigned char buf[]`, pushes a
   vlib object into a `pmr::vector`, then `memset`s `buf`. No vlib-typed
   operation and no vlib-pointer conversion appears in user code — the
   corruption is a write through the *original* byte array to storage now
   occupied by a live object. This is exactly the single-owner violation the
   boundary forbids (two live, writable views of the same storage: the byte
   array and the vlib object), and writing the array lvalue over a live object
   of another type is out-of-lifetime access ([basic.life]) — boundary rule 8.
   It is a genuine residual: the escape check does not see it, and the boundary
   excludes it only if "single owner" is read to forbid a user-retained writable
   alias of allocator storage. Worth a SPEC sentence making that explicit.
3. **Coroutine-frame address** (`coroutine_handle::address()` → `void*` to a
   frame holding a vlib promise/local). No vlib-pointer is converted in user
   code; the frame pointer is `void*` from the ABI. Reaching the vlib bytes
   needs offset arithmetic over an unspecified frame layout — UB / unspecified,
   boundary rule 8. Not reachable without leaving the boundary, but noted.
4. **`start_lifetime_as`** is specified and handled, but libc++ 23.1.2 does not
   yet provide it, so it is unreachable on the pinned toolchain today. The rule
   is in place for when it lands.
5. **`memset(&e, 0, 1)`** to the named-zero value is reported as a raw write.
   This is not a false escape in the soundness sense — the bytes were written by
   non-vlib code — but it is conservative where the result is in-domain. Left as
   a finding; a decision can cover a deliberate zeroing if the corpus ever needs
   one.
6. **Coarse attribution** when the sink type is erased: the whole unit's vlib
   claims are voided (not one declaration). Conservative — never a false
   `holds` — and a points-to analysis narrows it later (bead verbs-de3.33).

The standard's note that a fixed-underlying enum may hold any value of its
underlying type is respected throughout: a raw write to `E` is not UB, so the
escape check — not the sanitizers — is the only mechanism that catches F02–F04,
and it does.

## 6. SPEC-ready text

§4.1, §4.5 and §4.8 are replaced by §1 of this paper (the two reachability
notions, the provenance rule, the narrow read-only sink, the raw-write rule
with the whole-object-multiple exception, the closed entry-point list, and the
attribution closure). §4.2–§4.3 are unchanged except that rev 3 already adopts
macro trust by definition location (F05). Add one boundary sentence to §2.1
rule 3: *a single owner keeps no second writable view of a vlib object's
storage — including a byte array or allocator buffer that also backs it.*
