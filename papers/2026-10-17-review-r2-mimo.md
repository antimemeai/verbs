# External review round 2: MiMo (mimo-v2.6-pro, plan agent, variant high), SPEC revision 3

2026-10-17. Bundle: SPEC rev 3, doctrine, journals, all papers, both prototypes, blackbird snapshot. Prompt: context/reviews/prompt-r2.md. The first attempt aborted on a permission refusal; the retry ran from inside the copy. The guard on /opt/homebrew/etc/clang saw no change. The final report is verbatim below; the exploration dossiers that preceded it are in context/reviews/mimo-r2-transcript.md.

---

# verbs basics SPEC rev 3 — second-round adversarial review

**Scope and method.** Read-only review of `SPEC.md` (rev 3), `BLACKBIRD.md`, `journal/`, first-round reviews (ChatGPT, MiMo), the four tribunal reports, the Jev coverage audit, escape-allowlist v1/v2 plus the 725-line `verbs_escape2.cpp` matcher and its 48 attack / 13 legitimate cases, and the enum-candidate lane. Homebrew Clang 23.1.2 compile/run probes were not executed in this session (read-only / plan mode); forge values follow the C++ object model, the fixed-underlying-enum rule, and the prototype’s CastKind coverage. Probe-shaped claims are marked.

## 0. Summary

Revision 3 closes most of the first-round surface (F01 circular boundary, F05 macro trust, F07 content hashes, F09 Jev, F10 experiment *definitions*, F11 weakening baseline, F13/F16 keys, F17 `upto`, F20 example, MiMo F6/F7/F8/F9/F11/F12/F14) and correctly drops discovery and decisions. Escape-v2 closes F02–F04/F06/F12 for the shapes it measured.

Four **false `holds`** survive in §4 and §4.4. All forge a fixed-underlying enum without UB. All are shapes the 48 cases never took. Two live in the spec text alone; one is in the read-only sink’s definition of “read”; one is a clause the research paper had and the spec dropped.

---

## 1. BLOCKER — false `holds`

### R2-01 — §4.1 rule 1: hierarchy upcast to a non-vlib base launders provenance

**Defect.** Provenance allows a vpr to convert to “a class in the same hierarchy” (SPEC.md:407–411). The escape-v2 prototype never inspects `CK_DerivedToBase` / `CK_UncheckedDerivedToBase` / `CK_BaseToDerived` (`verbs_escape2.cpp:322–323` tests only `CK_BitCast`, `CK_LValueBitCast`, `CK_Dynamic`, `CK_PointerToIntegral`, `CK_ReinterpretMemberPointer`). A `Derived*` that is a vpr becomes a `Base*` that is **not** a vpr whenever `Base` is not vlib-containing (vlib-containing recursion stops at pointers; `Base` has no vlib member). The later `Base*`→`char*`/`void*` conversion is `!fromVpr && !toVpr` and is ignored. A raw write through that byte pointer is not “into vlib-containing storage” by static type (§4 rule 4; prototype `destVlib` at `verbs_escape2.cpp:466–467`).

The research paper only allowed “a **base subobject**” (`escape-allowlist-v2.md:43–45`). SPEC widened this to “a class in the same hierarchy” and never required the target to remain a vpr.

**Counterexample** (well-defined: writing object representation through `char*` is legal; non-virtual first base at offset 0; a fixed-underlying enum may hold any value of its underlying type — not UB):

```cpp
struct Base { int pad = 0; };              // NOT vlib-containing
struct Derived : Base { E kind = E::a; };  // claim: kind in{a,b}

int main() {
  Derived d;
  Base* bp = &d;                          // hierarchy cast — unexamined
  char* cp = reinterpret_cast<char*>(bp); // Base* not vpr — clean
  cp[sizeof(Base)] = 7;                   // forges d.kind
  return (int)std::to_underlying(d.kind); // 7
}
```

Same forge class as ChatGPT F02–F04. `legit/l11_typed_controls.cpp` uses `struct Base { E kind; }` (Base *is* vlib-containing), so the hole never opened in the 48+13. The journal’s noted “possible false escape” on `dynamic_cast` is the dual error: the prototype flags hierarchy casts the spec allows, and the spec allows a hierarchy cast whose target is not a vpr.

**Smallest fix.** A hierarchy conversion of a vpr must yield a type that is still a vpr to the *complete* object (carry the complete vlib-containing type across the upcast); a later erase/raw write attributes to that complete type’s leaves. Trip case: non-vlib base + `char*` store at `offsetof(kind)`. Just-miss: the l11 shape stays clean.

**Probe:** not run. Expect `7` under ASan/UBSan `-O2` on Clang 23.1.2 `-std=c++2c`, as in F02–F04.

---

### R2-02 — §4.4 unanalyzed definitions: `const` and wrappers still allow unanalyzed writes

**Defect.** §4.4 (SPEC.md:522–529) marks a vlib-containing type `outside` only when an unanalyzed definition takes or returns a **non-const** pointer or reference to the type (or a variable of the type). The same paragraph says: “Code defined in no analyzed unit can write anything it can reach.” A `const` pointer/reference still reaches the object (`const_cast` is legal and not UB). Wrappers (`std::span<E>`, `std::span<const E>`, holders of `E*`) are not “a pointer or reference” and are invisible. vpr (§4.1) exists for this notion; §4.4 does not use it.

Soundness m3 was only half-closed: Jev’s false-`holds` case was `&D` to an undefined function; rev 3 excludes only the non-const spelling.

**Counterexample A (const pointer)** — boundary rule 7 is satisfied (the touch goes through a function analyzed code declares):

```cpp
void external_mutate(const E* p);  // defined in no analyzed unit
void foo() {
  E e = E::a;                      // holds
  external_mutate(&e);             // cv-added — allowed by §4.1
}
// unanalyzed: *const_cast<E*>(p) = static_cast<E>(7);
```

**Counterexample B (wrapper):**

```cpp
void external_fill(std::span<E> s); // by value — not pointer or reference
void foo() {
  E e = E::a;
  external_fill(std::span<E>{&e, 1});
}
// unanalyzed: s[0] = static_cast<E>(7);
```

**Smallest fix.** Use vpr (or “any pointer, reference, or vpr wrapper”, const included): the type is `outside` when an unanalyzed definition takes or returns any vpr to it. Optionally treat a call to an unanalyzed function with a vpr argument as an escape unless that function is a named read-only sink.

**Probe:** rules-text check; no unanalyzed-TU run.

---

### R2-03 — §4.1 read-only sink: reference return admits a laundered write

**Defect.** The sink exception requires “return type is not a **pointer**” (SPEC.md:432). It does not exclude **references**. Standard library templates (`std::move`, `std::forward`, `std::as_const`) are “declared outside the repository”, take a deduced const/ref parameter, and return a reference. Prototype `isReadOnlySinkArg` only tests `isPointerType()` (`verbs_escape2.cpp:248`).

**Counterexample** (no user-defined external function; only `<utility>` + `<cstring>`):

```cpp
E e = E::a;
// reinterpret_cast<const void&>(e) is CK_LValueBitCast, fromVpr && !toVpr.
// Parent call: std::move — outside repo, parameter reference-to-const,
// return type const void&& (a reference, not a pointer) => read-only sink.
const void& r = std::move(reinterpret_cast<const void&>(e));
void& w = const_cast<void&>(r);          // void& is not a vpr — clean
std::memset(&w, 7, 1);                   // dest void* — not vlib-containing by type
return (int)std::to_underlying(e);       // 7
```

The same gap applies to any out-of-repo callee that materializes a writable alias and returns a reference, iterator, or `span` (not a pointer).

**Smallest fix.** Read-only sink: return type must be void, bool, or an integer/enum/`size_t` — not a pointer **and not a reference** (and not `span`/`string_view`/iterator). Stronger: admit only a closed libc sink list (`fwrite`, `write`, `memcmp`, `printf`-family, `ostream::write`), matching rule 2’s discipline. Trip case: `std::move` + `const_cast` + `memset`. Just-miss: `fwrite(&e, …)` stays clean.

**Probe:** not run. Expect forge `7`.

---

### R2-04 — §4 rule 4: spec dropped the paper’s pointer-slot clause (`E**` is not a vpr)

**Defect.** The research paper (`escape-allowlist-v2.md:66–68`) says a memcpy is an escape when “a source that carries a **vpr value** into a mismatched slot”, and the prototype implements it (`verbs_escape2.cpp:492–496`, case `n05_pointer_memcpy.cpp`). SPEC rule 4 (455–460) omits that clause. SPEC’s vpr (399–402) is a pointer *to a vlib-containing type*; `E*` is vpr, but `E**` points at `E*`, and vlib-containing recursion stops at pointers — so `E**` is **not** a vpr. Copying an `E*` through `memcpy` into a `void*` slot is therefore unexamined.

**Counterexample:**

```cpp
E e = E::a;
E* p = &e;
void* slot = nullptr;
std::memcpy(&slot, &p, sizeof p); // dest void* not vlib-containing; E** not vpr
std::memset(slot, 7, 1);          // dest void* not vlib-containing
return (int)std::to_underlying(e); // 7
```

`n05` is in the 48 and is caught by the prototype only because the prototype kept the clause the spec text dropped. A spec-faithful implementation will miss it.

**Smallest fix.** Restore the paper’s clause into rule 4 and/or treat pointer-to-vpr as vpr. Keep `n05` as a §10.2 trip case.

**Probe:** not run. Expect `7`.

---

## 2. Contradictions and spec/evidence drift

### R2-05 — MAJOR — §4.8 attribution: spec vs paper vs prototype

- SPEC.md:589–591 **rejects** unit-wide erased voiding and claims source-type leaf closure.
- Paper (95–97) and prototype (`verbs_escape2.cpp:30`, 631–650): any `erased=true` voids **all** claims in the TU; `report(..., pointeeOf(from), true)` (339–340) never collects leaves.
- Retype escapes (`void*`→`E*`) have an **erased source**: under SPEC’s “voids every leaf vlib type contained in that type”, the source type contributes **no leaves** — nothing voided. The prototype attributes the *destination* (344–345). SPEC-as-written would leave copies falsely `holds` after `o02`-style launder.
- Rule 11 (keyword macro) and some rule 9 escapes have “no named type” for SPEC:588 “voids the named type’s leaves.”

**Smallest fix.** One rule: every escape voids the leaves of the *best* known type (source if vlib-containing/vpr, else destination, else the named type for rules 7/9/10/11/14), program-wide; only a typed-source-free escape (asm `"memory"`) voids all claims. Align the prototype and re-run `f06`.

### R2-06 — MAJOR — §2 state table vs §6.2 suspension

§2 (146–160): each declaration is in **exactly one** of `holds`/`finding`/`outside`; “no `unknown`.” §6.2 (712–719): compile errors suspend the report; claims are “not reported at all”; exit is **1 if any escape in units that compiled, otherwise 0**. §6.1 (665–666): caller “acts only on the exit status.” Exit 2 is “no check ran; must not read silence as a pass” — suspension is not exit 2. Not a printed false `holds`, but a false pass under the caller contract. D25’s Jev note (“compile errors never change the exit”) matches rev 3 and is the bug.

**Smallest fix.** A suspended run exits 2 (or another non-zero) whenever any unit fails to compile, even with no escape found. Name “suspended — not reported” in the state table, or say declarations are examined only in a complete run.

### R2-07 — MINOR — guarantee vs memcpy exception; paper vs spec on memcpy types

Top-level guarantee (374–378) requires a copy from a **valid** object; rule 4’s exception (456–460) does not. Paper says “same **vlib** type”; SPEC says “same **vlib-containing** type” (wider — matches `l12` and the prototype). Prefer the SPEC wording and add source validity.

### R2-08 — MINOR — rule 9 / rule 12 disagree with the prototype and the tally

Rule 9: “Defining or **undefining** a macro that vlib defines is also an escape”; prototype `MacroUndefined` is a no-op (`verbs_escape2.cpp:697–702`). Rule 12: SPEC exempts verbs enums from nonconstinit; prototype flags every nonconstinit vlib static (`o05`). The “43 caught / 5 clean” tally was measured under the broader prototype rule (under SPEC text `o05` is clean).

---

## 3. First-round closure (compact)

| First-round | Rev 3 |
|---|---|
| F01 boundary circularity | Closed (§2.1 rule 3). |
| F02 / MiMo F2 const_cast view | Closed for named-variable path; **R2-03** reference-return sink remains. |
| F03 `as_writable_bytes` | Closed (rule 2). |
| F04 uintptr / pointer bit_cast | Closed. |
| F05 macro prefix trust | Closed (definition location). |
| F06 attribution | Spec direction right; **R2-05** drift; retype leaves empty. |
| F07 size+mtime | Closed (content hash every run). |
| F08 / MiMo F3/F10 stale holds | No stale claims; **R2-06** exit 0 on suspension. |
| F09 mandatory Jev | Closed. |
| F10 / MiMo F4 kill criterion | Definitions added; experiment still bead `verbs-de3.30`; pass “operator’s call; proposed” (**R2-10**). |
| F11 weakening two-step | Closed (declared predicate). |
| F12 partial memcpy | Closed (constant whole-multiple). |
| F13 / F16 keys & overloads | Closed. |
| F14 audit / enum domain | Closed enough (audit points + stated limit). |
| F15 migration seams | Closed. |
| F17 `upto(k<0>)` | Closed. |
| F18 exit 3 | Moot (decisions out). |
| F19/F20/F21 | Closed. |
| MiMo F5 type-erased attribution | Spec rejects unit-wide — **R2-05**. |
| MiMo F6 sticky exit | Closed (state-gated). |
| MiMo F7 `decided` | Closed by removal. |
| Soundness m3 | **Partial** — non-const only (**R2-02**). |
| D25 | Never-compiled closed; compile exit still 0 (**R2-06**). |

---

## 4. §10 oracles and rework risk

### R2-09 — MAJOR — case files can bless R2-01–R2-04 as clean

§10.2 (901) wants a trip and a just-miss case per clause. There is no trip case for a non-vlib base, a `const`/`span` unanalyzed callee, a reference-returning sink, or the pointer-slot memcpy. Just-miss cases (“upcast is clean”, “fwrite is clean”) will be recorded as *clean* if the author follows SPEC text. The audit build sees a forged enum only if a fixture observes at `verbs::name` / `to_underlying` / re-encode (the stated limit already admits unseen reads).

**Fix.** Name four required trip cases in §10.2: (1) non-vlib base + `char*` store; (2) unanalyzed `const E*` and `span<E>`; (3) `std::move` reference sink + `memset`; (4) `memcpy(&void_slot, &e_ptr, sizeof e_ptr)` + `memset`. Treat them like tribunal counterexamples.

### R2-10 — MAJOR — kill criterion defined but not testable as a gate

§1.1 defines arms, seeds, fault oracle, detection event, censoring, and a *proposed* threshold; the run is bead `verbs-de3.30`. Pass is “operator’s call” (115–118). Until the threshold is frozen and the bead runs, “meaningfully reduce edits-to-detection” cannot fail. Not a false `holds`; still an untestable kill criterion after two rounds.

**Fix.** Freeze the proposed threshold in the spec (median edits-to-detection ≤ ½ baseline on seeded classes; no regression on generic mutants; &lt;1 false `verbs check` finding per 20 tasks) and run the bead before claiming the basics meet the kill path.

### R2-11 — MINOR — implementation risks if the prototype is copied rather than the rule

- `isMemFamilyArg` matches `n.contains("memcpy"|"memmove"|"memset")` (`verbs_escape2.cpp:266–267`) while the write rule uses exact names — a user `do_memcpy(void*)` exempts the erasure and never runs the raw-write rule (full forge). Spec must say **exact** names / builtins only.
- `std::any a = &e;` / `std::function f = [p=&e]{…}` are silent: `leavesOf` does not follow pointers (204–219) and `VisitCXXConstructExpr` skips empty leaf sets (364). Paper claims wrapper erasure is an escape; only `shared_ptr<E>` is covered via template-arg leaves.
- `printf("%p", &e)` is flagged as a writable variadic vpr (516–526) though the paper says address-printing stays clean (only `ostream << &e` was tested).
- Cross-unit rules 13–14 have **no v2 prototype evidence** (no `--facts` in escape-v2; that is v1-only).

### R2-12 — MINOR — boundary assumptions and speculative API

Rules 1–2, 4–6 have no violation oracle (acceptable; keep printing the boundary). `start_lifetime_as` is in rule 2 but absent from libc++ 23.1.2 (SPEC:627) — do not implement it on the pin (MiMo F13 had no disposition row). Full `Bounded` arithmetic remains specified while increment B is consumer-gated — keep implementation minimal (`to`/`k`/`get`/egress/`+=`/`-=`/`upto`).

---

## 5. Findings table

| id | severity | section | one-line summary |
|---|---|---|---|
| R2-01 | BLOCKER | §4.1 rule 1 | Hierarchy upcast to a non-vlib base drops vpr; `char*` write forges enum; false `holds`. |
| R2-02 | BLOCKER | §4.4 | Unanalyzed defs only block non-const pointer/ref; `const` and `span` still false `holds`. |
| R2-03 | BLOCKER | §4.1 read-only sink | Sink allows reference returns (`std::move`); launder + `memset` forges. |
| R2-04 | BLOCKER | §4 rule 4 | Paper’s pointer-slot clause dropped; `E**` not vpr; `memcpy` of `E*` into `void*` forges. |
| R2-05 | MAJOR | §4.8 | Attribution three-way split; retype voids no leaves under SPEC wording. |
| R2-06 | MAJOR | §2, §6.1–§6.2 | Suspended report prints no claims but exits 0; caller trusts exit status. |
| R2-07 | MINOR | §4 vs guarantee | Memcpy exception omits source validity; paper/SPEC “vlib” vs “vlib-containing”. |
| R2-08 | MINOR | §4.3, §4.9 | Macro-undef and rule 12 disagree with prototype; tally measured under broader rule. |
| R2-09 | MAJOR | §10.2 | No trip cases for R2-01–R2-04; suite can record them as clean. |
| R2-10 | MAJOR | §1.1, §14 | Kill-criterion experiment still a bead with unset threshold. |
| R2-11 | MINOR | §4.9 evidence | Prototype substring mem-family, `any`/`function` pointer capture, printf %p, no v2 cross-TU proof. |
| R2-12 | MINOR | §2.1, §4.1, §3.3 | Assumption rules unobserved; `start_lifetime_as` not on pin; Bounded arithmetic unconsumed. |

**Bottom line:** do not implement the escape check from rev 3 until R2-01–R2-04 are closed in the rule text and each has a §10.2 trip case. They are the same forge class the first round already paid for (F02–F04/F12), through a CastKind the prototype never visited, a `const` the §4.4 fix still trusts, a reference return the sink rule does not exclude, and a clause the research paper wrote and the spec dropped.
