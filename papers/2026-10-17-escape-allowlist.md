# A sound, precise escape rule: the vlib-write allowlist

Date: 2026-10-17. Lane: escape-rule redesign. Inputs: design/SPEC.md §2-§4,
papers/2026-10-17-tribunal-soundness.md, papers/2026-10-17-tribunal-checks.md,
the probe sources in the session scratchpad
(`.../escape-lane/`, `.../tribunal-soundness/`). Toolchain: Homebrew LLVM
23.1.2 (`/opt/homebrew/opt/llvm`), `-std=c++2c`, sysroot from `xcrun
--show-sdk-path`, resource dir baked in (cpp-toolchain-burdens §5). LLVM source
read under `quarantine/llvm-project/`. Nothing was written into blackbird or
BRepGPU; nothing in the project tree was built.

The deny-list of §4 was shown unsound by two tribunals (17+ compiled
counterexamples that falsify a `holds` claim with no listed construct, plus
three legitimate patterns the list falsely flags). This lane replaces it with
an **allowlist judged on meaning**, grounds every detection rule in the Clang
23 AST and the C++26 standard, builds a 689-line LibTooling prototype
(`verbs_escape.cpp`) plus a 22-line cross-unit comparator (`compare_facts.py`),
and runs them over every counterexample and a corpus of legitimate
vlib-using programs. Result: every bypass that is an escape-check concern is
caught; zero false positives on the legitimate corpus, including the three
patterns the deny-list wrongly flagged.

---

## 1. The rule, as spec text for SPEC §4

> ## 4. The escape check
>
> Every `holds` claim rests on one closed guarantee:
>
> > **The object representation of a vlib-containing object is written or
> > created only by (a) vlib's own members and factories, or (b) a copy or
> > move from a valid object of the same type.** Every other write or creation
> > of those bytes, and every loss of the static type of a pointer or
> > reference to such an object, is an **escape**.
>
> This is an allowlist. The check does not enumerate bad spellings; it permits
> the two allowed origins and reports everything else, matched by Clang AST
> semantics with full type information. A construct the check cannot judge
> (e.g. a cast in an uninstantiated template) is reported `outside` with the
> reason, never `holds` and never a false escape.
>
> ### 4.1 vlib-holding types
>
> A **vlib type** is a specialization of `verbs::Bounded`, `verbs::Refined` or
> `verbs::Id`, or a **verbs-domain enum**. A verbs-domain enum is one declared
> by `VERBS_ENUM`, or (reflection path) one named in a `verbs::enumerators<E>`
> registration; not every `enum class`.
>
> A type is **vlib-containing** iff, recursively, it is a vlib type, an array
> of a vlib-containing type, a class with a base or non-static data member of a
> vlib-containing type, or a standard wrapper (`optional`, `expected`, `pair`,
> `tuple`, `array`, `variant`) of one. Recursion stops at pointers and
> references: a pointer *to* a vlib object is not itself vlib-containing. "Involves
> a vlib type" (old §4) is replaced by this transitive definition, closing the
> nesting hole (soundness B2).
>
> ### 4.2 Escapes — representation and type erasure
>
> 1. **Type erasure.** Converting a pointer or reference to a vlib-containing
>    object to `void*`, `char*`, `unsigned char*`, `std::byte*`, or any
>    unrelated pointer type. This covers the implicit `T*`→`void*` of every
>    `void*` API (`fread`, `read`, `recv`, `memcpy` destination, user `void*`
>    helpers), `static_cast`, C-style and functional casts alike, because all
>    reduce to one AST node (§2 below). **Exception (read-only):** a conversion
>    whose target pointee is `const`-qualified is a read, not an escape — this
>    admits `const char*`/`const std::byte*` views for hashing, printing,
>    `fwrite`, and `write`.
> 2. **Re-typing.** Converting `void*`/byte-pointer back to a pointer to a
>    vlib-containing type, including `std::launder`, `std::start_lifetime_as`,
>    `std::construct_at`, and placement-`new` over storage that already holds a
>    vlib object.
> 3. **Bit reinterpretation.** `std::bit_cast` / `__builtin_bit_cast` and
>    `reinterpret_cast` of references whose source or result is vlib-containing.
> 4. **Raw byte writes.** `memcpy`/`memmove`/`memset` and builtins thereof whose
>    destination is vlib-containing, **except** a `memcpy`/`memmove` whose source
>    is an object of the same vlib type (trivially-copyable relocation is a
>    copy — allowed).
> 5. **Unions.** A user-declared union with a (transitively) vlib-containing
>    member.
> 6. **asm.** An `asm` statement with an output or input operand that is
>    vlib-containing, or any `"memory"` clobber, in analyzed code.
>
> ### 4.3 Escapes — enums
>
> 7. **Enum ingress.** Any integral-to-enum or floating-to-enum conversion
>    whose destination is a verbs-domain enum, outside `verbs::to_enum` /
>    `verbs::from_string`. One rule covers `static_cast`, C-style, functional
>    and list-initialization spellings (`Mode m{raw}`), because all reduce to a
>    cast node with `CK_IntegralCast` to the enum (§2).
> 8. **Enum bit-field.** A bit-field of verbs-domain enum type too narrow to
>    hold every enumerator value.
> 9. Value- and zero-initialization are handled at the vlib boundary, not here:
>    a verbs-domain enum must declare an enumerator equal to `0` (`VERBS_ENUM`
>    emits it; reflected enums are required to have it), so `E{}`, `E e;` at
>    static scope, `std::vector<E>(n)` and `map[k]` all yield the `0`
>    enumerator rather than an out-of-domain value.
>
> ### 4.4 Escapes — encapsulation and the build
>
> 10. **verbs specializations.** Any declaration in `namespace verbs`, or any
>     explicit/partial specialization or explicit instantiation of a
>     `verbs::` template — class, member function, or variable (`enumerators`,
>     `to_enum`) — whose spelling location is outside vlib's headers, except
>     `VERBS_*` macro expansions.
> 11. **Private-member theft.** An explicit instantiation whose template
>     arguments name a `private`/`protected` member of a vlib class (the
>     access-check exemption of [temp.spec.general]/6). Directly naming such a
>     member elsewhere is already a compiler error.
> 12. **Keyword macros.** A `#define`/`#undef` of `private`, `protected`,
>     `public`, `class`, `struct`, `const` or `noexcept`, including `-D` on the
>     compile-database command line and `-include` forced headers.
> 13. **Non-`constinit` statics.** A vlib-containing object with static or
>     thread storage duration that is not `constinit` (static zero-init reads a
>     non-enumerator / out-of-range value before dynamic init; soundness M3).
>
> ### 4.5 Cross-translation-unit mismatch
>
> 14. verbs records per unit, for every external-linkage variable and function
>     and every external-linkage class definition, its qualified name, a
>     canonical type/field signature, and a vlib-containing flag. The cross-unit
>     step reports a qualified name carrying two incompatible signatures where
>     either is vlib-containing (ODR / `extern` type confusion; soundness B6).
>
> ### 4.6 Refined is restricted to deep value types
>
> 15. `Refined<T, Pred>` requires `T` to be a **deep value type**: arithmetic,
>     enum, a vlib type, `std::string`, or an array / owning container /
>     aggregate of deep value types with no `mutable` members and no pointer,
>     reference, or view (`span`, `string_view`, `reference_wrapper`,
>     `shared_ptr`, `function`) member. Any other `T` is a compile error in
>     vlib and an escape (`refined-shallow`) at the use site. The §2.1 example
>     "a non-empty, sorted span" becomes an owning sorted vector. This closes
>     the shallow-const and mutable-member holes (soundness B7).
>
> ### 4.7 Scope and silencing
>
> Scope is decided by **repository path**, never by Clang's system-header flag
> (`SrcMgr::C_System`): a repo file marked `#pragma clang system_header`, or
> reached through `-isystem` into the tree, cannot hide an escape, and
> libc++/SDK internals (optional's union, vector's relocation `memcpy`) are out
> of scope and never reported. verbs honors no suppression comment; only a
> recorded decision (§7) silences a finding, and every added or changed
> decision prints as a `!` line.
>
> ### 4.8 Attribution
>
> An escape voids the `holds` claim for every declaration whose type is the
> affected vlib-containing type, program-wide (or for every vlib declaration
> when the sink's type is erased). Escapes are rare and zero-false-positive, so
> coarse attribution costs nothing; a points-to analysis can narrow it later
> (bead).

---

## 2. AST grounding

Every rule matches a node the compiler already built, so the spelling an agent
chooses does not matter. Citations are to `quarantine/llvm-project/` (LLVM
23.1.2) and to AST dumps I took with Homebrew clang 23.1.2 (probe sources in
`.../escape-lane/probe_*.cpp`).

### Casts (`clang/include/clang/AST/OperationKinds.def`)

The one load-bearing fact: C++ has many *syntaxes* for a type pun but few
*cast kinds*. `CastExpr::getCastKind()` collapses them.

- **`CK_BitCast`** (line 61): "a bit pattern of one type reinterpreted as
  another… a conversion from any pointer type to a C pointer type is a
  bitcast." A pointer→`void*` conversion is `CK_BitCast`. **Confirmed by AST
  dump:** in `probe_voidptr.cpp`, both `std::fread(&h, …)` and `void* p =
  &h.version` produce `ImplicitCastExpr <BitCast>` from `Header *`/`B *` to
  `void *`. This is why rule 4.2/1 catches the implicit `T*`→`void*` of every
  `void*` API with no cast written by hand. (`CK_ToVoid`, line 183, is a
  different thing — the value discard in `(void)expr` — so `(void)b` is not an
  escape, confirmed by `ctrl_typed.cpp` reporting 0.)
- **`CK_LValueBitCast`** (line 67): `reinterpret_cast` of an lvalue to a
  reference type.
- **`CK_LValueToRValueBitCast`** (line 72): "created by `__builtin_bit_cast`."
  **Confirmed:** `probe_misc.cpp`'s `__builtin_bit_cast(B, …)` dumps as
  `BuiltinBitCastExpr <LValueToRValueBitCast>` (node class at
  `AST/ExprCXX.h:5474`). `std::bit_cast<B>` dumps as a `CallExpr` to the
  `bit_cast` function template, so the check matches both the builtin node and
  the `bit_cast` callee.
- **`CK_IntegralCast`** (line 199) and **`CK_FloatingToIntegral`** (line 236):
  integer/float → integer, the representation of an enum. **Confirmed:** in
  `probe_enum.cpp`, all of `Mode a{7}`, `Mode b{r}`, `Mode{r}`, the designated
  initializer `Door{.mode = Mode{r}}`, and `static_cast<Mode>(r)` reduce to an
  `ImplicitCastExpr <IntegralCast>` whose target type is `Mode` — the
  list-init forms wrapped in an `InitListExpr` (`AST/Expr.h:5314`), the
  functional forms in a `CXXFunctionalCastExpr <NoOp>`. One matcher — "a cast
  of kind `IntegralCast`/`*ToIntegral` whose target is a verbs-domain enum,
  outside `to_enum`" — covers every enum-ingress spelling, closing soundness B3
  with no per-syntax enumeration.
- `CK_ToUnion` (line 110), `CK_IntegralToPointer` (line 169): adjacent reinterpreting
  kinds, matched the same way.

### Non-cast nodes

- **`CXXNewExpr`** (`AST/ExprCXX.h:2357`): placement-new is a `CXXNewExpr` with
  `getNumPlacementArgs() > 0`; its placement argument `&obj` is itself a
  `CK_BitCast` to `void*`, so re-typing over vlib storage is caught by rule
  4.2/1 as well as by the explicit placement check. **Confirmed:**
  `ctrl_place.cpp`.
- **`std::launder` / `std::construct_at` / `std::start_lifetime_as`**: ordinary
  `CallExpr`s to named function templates; the check matches callee name plus a
  vlib-containing pointee. **Confirmed:** `a02_malloc.cpp`'s
  `std::launder(static_cast<B5*>(m))` fires both `lifetime-launder` (the
  launder call) and `re-type` (the `void*`→`B5*` static_cast).
- **`GCCAsmStmt`** (`AST/Stmt.h:3456`): operands and clobbers are reachable via
  `getOutputExpr`/`getInputExpr`/`getClobber`. **Confirmed:** `a16_asm.cpp`.
- **`FieldDecl::isBitField()`** with a verbs-domain-enum type: rule 4.3/8.
  **Confirmed:** `ctrl_bitfield.cpp` flags the 1-bit field, not the full-width
  one.
- **`VarDecl`** with `hasGlobalStorage()` and no `ConstInitAttr`: rule 4.4/13.
  **Confirmed:** `a13_a.cpp`'s `copy_of_limit`.
- **`RecordDecl::isUnion()`** with a transitively vlib-containing member: rule
  4.2/5. **Confirmed:** `a17_nested.cpp`'s `Frame`.

### Decl-level attacks

- **`ClassTemplateSpecializationDecl::getSpecializationKind()`** against
  `TemplateSpecializationKind` (`clang/Basic/Specifiers.h:189`;
  `TSK_ExplicitSpecialization` at :199). A user specialization of
  `verbs::Bounded<7,7>` dumps as a `ClassTemplateSpecializationDecl …
  explicit_specialization` whose source location is the **user** file
  (`a06`), while the macro's `enumerators<Mode>` specialization carries a
  `VERBS_*` macro expansion location and is exempt. Member-function
  specializations (`a07`) are `FunctionDecl`s with
  `getTemplateSpecializationKind() == TSK_ExplicitSpecialization` whose
  `DeclContext` chain passes through `namespace verbs`.
- **Private-member theft** ([temp.spec.general]/6; `AST/DeclTemplate.h:535`):
  the explicit instantiation `template struct thief<v_tag, &B5::v_>` is a
  `ClassTemplateSpecializationDecl` with a `TemplateArgument::Declaration`
  naming a `FieldDecl` whose `getAccess()` is `AS_private` in a vlib record.
  **Confirmed:** directly writing `&B::v_` in a function is rejected by the
  compiler as a private-access error (`probe_decl.cpp`), so the *only* path is
  the explicit-instantiation argument, which rule 4.4/11 matches.
- **Keyword macros**: a `PPCallbacks::MacroDefined`/`MacroUndefined` whose macro
  name is a C++ keyword. **Confirmed:** `a09`'s `#define private public`.
- **Cross-TU** (soundness B6): per-unit facts. The Itanium mangling of a
  namespace-scope variable omits its type and `fill(Pkt&)` mangles identically
  in both units, so the linker cannot see the conflict. The facts emitted for
  `a12_main.cpp` / `a12_other.cpp` show `g` as `verbs::Bounded<1,5>` (vlib=1)
  vs `int` (vlib=0) and `Pkt` with a vlib field vs `int` — the comparator
  flags both.

---

## 3. Prototype and results

`verbs_escape.cpp` is a `ClangTool` running a `RecursiveASTVisitor` (two
passes: register verbs-domain enums, then detect) plus `PPCallbacks` for
keyword macros, built against Homebrew LLVM 23 exactly as
cpp-toolchain-burdens §5-7 prescribes (`-resource-dir`,
`-fvisibility-inlines-hidden`, C enabled). `compare_facts.py` is the cross-unit
step over `--facts` output. Build and run scripts: `build.sh`, `run.sh`.

### Confusion matrix — counterexamples (should be caught)

| Probe | Attack | Escape-check verdict | Rule fired |
|---|---|---|---|
| a01 | `fread(&h,…)` implicit `T*`→`void*` | **caught** | type-erase |
| a02 | malloc + memcpy + `launder(static_cast<B5*>)` | **caught** | lifetime-launder, re-type |
| a03 | `Mode m{raw}`, functional, designated list-init | **caught** (5) | enum-ingress |
| a06 | user specialization `verbs::Bounded<7,7>` | **caught** | verbs-specialization |
| a07 | explicit spec. of member `B5::make<int>` | **caught** | verbs-specialization |
| a08 | explicit-instantiation private-member theft | **caught** | private-member-theft |
| a09 | `#define private public` | **caught** | keyword-macro |
| a10 | `Refined<span>` shallow const; mutable member | **caught** (2) | refined-shallow |
| a13 | non-`constinit` static `Bounded` | **caught** | nonconstinit-static |
| a16 | inline `asm` output operand | **caught** | asm |
| a17 | union nesting, `bit_cast`, `__builtin_bit_cast`, functional `P(vp)` | **caught** (6) | union, bit-reinterpret, type-erase, re-type |
| a12 | cross-TU `extern`/ODR type mismatch | **caught** (2) | xtu-mismatch (facts) |

Controls confirming the rule is a real distinction, not luck:
`ctrl_place.cpp` (placement-new/`construct_at` over vlib storage → caught),
`ctrl_writable.cpp` (writable byte view → caught; `const` view on the next line
→ not), `ctrl_bitfield.cpp` (narrow enum bit-field → caught; full-width → not).

### Confusion matrix — legitimate corpus (should be clean)

All programs compile and run with Homebrew clang 23 before being checked
(strong oracle: valid, exercised code, not hypotheticals).

| Program | Legitimate pattern (tribunal risk) | Escapes reported |
|---|---|---|
| l1_optional | `optional<Bounded>` from factory — optional's **union** storage (M1) | **0** |
| l2_vector_sort | `vector<Bounded>`, `std::sort` — relocation **memcpy** (M1) | **0** |
| l3_map | `map<uint64,Bounded>`, `Id` keys | **0** |
| l4_hash_print | FNV hash over bytes via **`const unsigned char*`** view (M1) | **0** |
| l5_serialize | `to_enum` ingress; `fwrite(&b,…)` `const void*` egress; enum→int read | **0** |
| l6_refined | `Refined<vector<int>>`, `Refined<string>` — deep value types | **0** |
| l7_enum_const_static | `constinit Bounded`, `to_enum` round-trip | **0** |
| ctrl_typed | `B*`/`const B&` passed to functions; `(void)b`; `b.get()` | **0** |

**Every bypass that is an escape-check concern is caught. Zero false positives
on legitimate vlib code, including the three patterns the deny-list wrongly
flagged (optional union, vector memcpy, read-only casts).** The read-only
exception (const-qualified target pointee) is what admits hashing, printing and
`fwrite` while still catching the writable-view attack.

### What the allowlist deliberately leaves to other mechanisms

These tribunal counterexamples are *not* escape-check matters; the allowlist
does not and should not fire on them. They are closed at the vlib boundary or
by the claim boundary, and are named here so the division is explicit:

- a04/a05 (enum bit-field / value-init on a **plain** enum): the plain enum is
  not a verbs-domain enum under the macro-fallback model, so it carries no
  `in{}` claim. For a *registered* enum, rule 4.3/8 catches the narrow
  bit-field (`ctrl_bitfield`) and the 0-enumerator requirement (4.3/9) makes
  value-init sound — a vlib definition rule, not a check.
- a11 moved-from Refined and a predicate reading a mutable global: claim
  boundary rule 2 (moved-from) and a `named_predicate` constraint (soundness
  M8 — make it an escape for a predicate body to read a non-`const` static).
  `refined-shallow` catches the mutable-*member* half; the global-reading half
  is a predicate-purity rule for vlib.
- a14 self-init `B5 x = x;`: undefined behaviour (reading indeterminate value);
  claim-boundary rule 8 + `-Werror=uninitialized` in the build contract.
- a15 unchecked `*make(v)`: `optional`/`expected` misuse; closed by library
  hardening at FAST in the claim boundary, or a vlib-owned checked optional
  (soundness M2).
- a18 `%`, a19 `+=` at the extremes: vlib arithmetic correctness, not escapes
  (soundness M5/M6); fixed in `Bounded`'s `__int128` paths.

---

## 4. Non-expression attacks, answered

- **User specializations / explicit instantiations of `verbs::` templates**
  (soundness B4): rule 4.4/10, matched by `TemplateSpecializationKind` plus an
  `ownedByVerbs` walk of the `DeclContext` chain, with `VERBS_*` macro
  expansions exempt by expansion location. Caught: a06 (class), a07 (member
  function). A hand-written `verbs::enumerators<Mode>` specialization outside a
  macro is the same rule on the variable template.
- **Keyword macros** (soundness B5): rule 4.4/12 via `PPCallbacks`. The
  command-line `-D private=public` form must be read from the compile-database
  entry (the preprocessor sees it as a predefined macro); the prototype catches
  the in-source `#define`. Recording and diffing per-unit compile flags (checks
  M2/M7) closes the `-D` and `-Wno-*`/`-isystem` variants; specified as "record
  the command hash and the full argument vector per unit, and treat any change
  to a `-D`, `-std`, `-W`, `-isystem` or `-include` argument as a silencing
  `!` line."
- **Cross-TU type confusion** (soundness B6): rule 4.5/14. **Exactly what to
  record, per unit:** for each external-linkage `VarDecl` and `FunctionDecl`,
  the qualified name, the canonical type string, and a vlib-containing flag;
  for each external-linkage class definition, the qualified name, the
  concatenated canonical field-type signature, and a vlib-containing flag.
  The cross-unit step groups by (kind, qualified name) and reports any group
  with more than one distinct signature where any member is vlib-containing.
  Demonstrated on a12.
- **Refined over reference-semantics or mutable-member types** (soundness B7):
  rule 4.6/15.
  - **Without reflection:** a C++ concept in vlib can reject the easy cases —
    `!is_pointer`, `!is_reference`, not one of a denied view-type allowlist,
    and `is_trivially_copyable` or membership in an owning-container allowlist.
    It **cannot** generically walk an arbitrary aggregate's members to find a
    `mutable` field or a buried pointer; that needs introspection. The
    prototype's `isDeepValueType` does that walk *in the checker* (AST field
    recursion), which is the backstop: a10's `span` and mutable-`cache`
    `Positive` are caught, l6's `vector<int>`/`string` are clean. So without
    reflection the guarantee is split: a conservative `verbs::deep_value<T>`
    concept in vlib (allowlist + trivially-copyable) rejects most, and the
    escape check's AST walk is the sound completion.
  - **With reflection (P2996, bloomberg/clang-p2996 under
    context/toolchain-cpp26/):** a complete compile-time `deep_value<T>` is
    writable — `std::meta::nonstatic_data_members_of` with `template for`,
    rejecting any member that `is_mutable`, is a pointer/reference, or whose
    type is not itself `deep_value`, recursing through bases. This moves the
    whole guarantee into vlib as a `static_assert`, and the escape check's walk
    becomes a redundant second oracle rather than the primary. Per
    cpp26-clang-toolchain §5, wrap the member iteration in a `consteval`
    helper to dodge the fork's transient-allocation bug in `if constexpr`.

---

## 5. Residual unsoundness and the claim-boundary wording

The allowlist is sound for writes and type-erasure of vlib bytes *within the
analyzed, well-defined program*. What remains outside it, and the exact
boundary text to add to SPEC §2.3:

1. **UB outside vlib** (soundness M1). An out-of-bounds or out-of-lifetime
   write anywhere — `buf[i]` overrunning into an adjacent `Bounded` field, a
   dangling `const B5&` after `vector` reallocation, the self-init `B5 x = x;`
   — can store any byte into a vlib object with no cast and no listed
   construct. ASan does not see intra-object overflow. This is all of C++, not
   one escape.
   > **Boundary rule 8.** *The program has no undefined behaviour outside
   > vlib — in particular, no out-of-bounds or out-of-lifetime access, and no
   > use of an uninitialized or moved-from object. verbs does not check this;
   > `-fsanitize=address,undefined,bounds`, library hardening at FAST or above,
   > and `-Werror=uninitialized` are the mechanisms, and the build must enable
   > them for the claim to hold.*
2. **Code outside the compilation database** (SPEC §2.3 rule 7, kept and
   sharpened). A translation unit not in the database, a `-D`/flag that selects
   different code, a PCH or `import std;` module, or platform-guarded code not
   compiled on this host, can hold escapes verbs never parsed.
   > **Boundary rule 7 (amended).** *The analyzed code is the preprocessed code
   > of exactly the translation units in the named compilation database, under
   > its exact flags. A unit, header configuration, module, or command-line
   > macro outside that set is `outside`, not `holds`. The report names the
   > database and prints a change to any unit's compile command as a silencing
   > `!` line.*
3. **The `-D private=public` command-line form** is detectable only from the
   compile-command record (rule 4.4/12 + the flag-diff of boundary 7), not from
   the AST; until flag recording lands it is a known gap, closed by the facts
   record specified in §4 above.
4. **Coarse attribution.** An escape voids the claim for the whole
   vlib-containing type, not one declaration, until a points-to analysis exists
   (soundness M7, bead). This is conservative (never a false `holds`), so it is
   a precision limit, not unsoundness.

Everything else the two tribunals raised against §4 is closed by §1's rules and
demonstrated in §3.

---

## 6. Artifacts

- Prototype: `.../escape-lane/verbs_escape.cpp` (689 lines), `compare_facts.py`,
  `build.sh`, `run.sh`.
- Legitimate corpus: `.../escape-lane/legit/l1..l7` plus `ctrl_*` controls.
- Counterexamples: `.../tribunal-soundness/a01..a19`, `.../tribunal-soundness/xtu/`.
- AST-grounding probes: `.../escape-lane/probe_voidptr.cpp`,
  `probe_enum.cpp`, `probe_misc.cpp`, `probe_decl.cpp`.

These live in the session scratchpad, not the repo. Folding the prototype into
`cpp/lib/` and `cpp/tools/verbs/` with case-file tests (SPEC §9.2) is the
implementation step, gated on the selected C++26 Clang.
