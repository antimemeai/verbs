# External review: MiMo (mimo-v2.6-pro, plan agent, variant high), SPEC revision 2

2026-10-17. Same bundle and prompt as the ChatGPT review, on a disposable copy. The plan agent stopped at its approval step and never emitted the final report; the findings below are its plan file verbatim (~/.local/share/mimocode/plans/1792269824597-clever-circuit.md). Its exploration transcript is in context/reviews/mimo-transcript.md.

---

# Plan: Adversarial review of SPEC.md (verbs basics, revision 2)

## Goal

Emit a Markdown adversarial review report on standard output (read-only; no files modified). The report ranks defects by BLOCKER / MAJOR / MINOR, gives counterexamples and smallest fixes, notes which first-tribunal blockers revision 2 did not truly fix, names machinery the basics do not need, and ends with a findings table.

## Sources checked

- `SPEC.md` (rev 2, 831 lines) — subject
- `BLACKBIRD.md`, `journal/2026-10-17-operator-decisions.md` — binding doctrine
- Four tribunal reports + `papers/2026-10-17-escape-allowlist.md`
- `blackbird/include/blackbird/journal.hpp:28-33`, `src/journal.cpp:278-281` (corpus claims)
- `prototypes/escape-lane/`, ergonomics mistakes/excerpts, toolchain papers (via explore)

## Report structure (to emit)

1. Header (what was reviewed, method)
2. Ranked findings (id, severity, section, defect, counterexample, smallest fix; say guess vs check)
3. Earlier tribunal blockers not truly fixed
4. Machinery the basics do not need
5. Findings table

---

## Findings to report (draft)

### BLOCKER

**F1 — §6.5 example contradicts §3.2 / §4.2 zero-state rule.**
SPEC:576 prints `+ escape PhaseKind value-initialized; 0 is not a value` and `map::operator[] creates Node{}`. SPEC:208-221 requires every verbs enum to name 0 (`idle = 0` or `VERBS_UNSET(none)`) and says "the `in{}` claim includes `none`". SPEC:361-362: "Value- and zero-initialization need no check."
Counterexample: `VERBS_ENUM(PhaseKind, uint8_t, VERBS_UNSET(none), assembly = 1, …)`; `map<int,Node> m; m[0];` → `kind == none`, which is in the claim; tool must not emit an escape. Or with `idle = 0`, 0 is a real value and the example's "0 is not a value" is false.
Fix: delete the `+ escape … value-initialized` example (or replace with a real escape). Keep §4.2. **Checked.**

**F2 — §4.1 read-only exception opens an undetyped write hole.**
SPEC:335-336: "a conversion whose target pointee is `const` is a read." After `const void* cvp = &x;` (allowed), `const_cast<void*>(cvp)` is not rule 1 (source is `void*`, not vlib-containing), `memset`/`memcpy` into that `void*` is not rule 4 (destination not typed vlib-containing), and a write through `void*`/`char*` is not rule 2 (not re-typed *to* vlib).
```cpp
verbs::Bounded<1,5> x = verbs::k<1>;
const void* cvp = &x;                 // rule 1 read-only exception — allowed
void* vp = const_cast<void*>(cvp);
std::memset(vp, 9, sizeof x);         // no rule matches; x holds 9; claim stays `holds`
```
The escape-allowlist's own guarantee (only vlib members or same-type copy may write those bytes) is violated. Soundness B1 originally allowed const only "passed straight to a known read-only sink"; the adopted exception is broader.
Fix (smallest): treat `const_cast` whose source is a const pointer to `void*`/byte/vlib-containing and whose result is non-const as an escape; and treat raw writes through `void*`/byte pointers as escapes when the destination is not a same-type vlib copy. **Checked against C++/rules text; AST behaviour of const_cast is ordinary.**

**F3 — Stale facts under compile errors / over-budget keep false `holds`.**
SPEC:537-539 (compile errors: keep previous facts) and SPEC:613-615 (over-budget: pending units stale). There is no `unknown` state (SPEC:113). An edit that both breaks a unit *or* pushes it past the 10 s budget and introduces an escape leaves the previous `holds` in the report; the escape is never printed; the claim is still `holds`.
```text
edit 1: verbs check  → holds PhaseKind on Node::kind   (exit 0)
edit 2: add fwrite(&node, …) in foundation.hpp; also touch a .so the unit includes
        unit stale or compile-errors → not refreshed → still "holds"
```
SPEC:615 "Nothing pending is reported as resolved" only suppresses `-` lines; it does not revoke `holds`. This is exactly open Q12.4 and it is still open.
Fix: while a unit is stale/not-refreshed, every claim from that unit leaves `holds` and becomes `outside` with reason `not refreshed`, or the run prints exit 2. Never report `holds` from facts older than the latest edit that could affect them. **Checked.**

**F4 — Kill criterion is not testable as written.**
SPEC:56 "meaningfully reduce edits-to-detection"; SPEC:81-84 "a measurable effect… if… not meaningful, stop"; experiment is bead verbs-de3.30 (deferred). No threshold, n, or definition of edits-to-detection. A 1% effect and a 10× effect both satisfy "measurable".
Fix: define the metric (e.g. median edits from first faulty edit to first non-zero `verbs check` / compile rejection on seeded classes) and a numeric gate before the experiment is allowed to pass or fail the criterion. **Checked.**

**F5 — §4.8 type-erased attribution is weaker than the adopted research.**
Escape-allowlist §4.8: type-erased sink voids "every vlib declaration" (program-wide). SPEC:435-436: "voids every claim in the unit." A type-erased write in unit A can corrupt a `PhaseKind` that unit B later copies; B's claim is not voided under the SPEC wording.
```cpp
// a.cpp
Node* leak() { static Node n{PhaseKind::assembly}; void* p = &n; std::memset(p, 9, sizeof n); return &n; }
// b.cpp
Node local = *leak();   // local.kind == 9; SPEC voids only a.cpp claims
```
First sentence (type program-wide) may be read as also applying; the paper's parenthetical is explicit and SPEC dropped it.
Fix: restore "or every vlib-containing claim program-wide when the sink's type is erased." **Checked against both texts.**

### MAJOR

**F6 — Unresolved findings exit 0 forever after the first print.**
SPEC:498-503 exit 1 only for "new" escape/silencing/lost claim. Agent that ignores `+ escape` and keeps editing gets exit 0; contract is "acts only on the exit status" (SPEC:495-496).
Fix: exit 1 while any escape/silencing/lost claim is unresolved, or print a sticky summary and keep a non-zero code until resolved or decided. **Checked.**

**F7 — `decided` / `VERBS_OPEN_DOMAIN` do not meet.**
§2: D is vlib-containing (closed by type). §7's only verdict is "deliberately not a closed domain." That verdict is for raw/candidate subjects (§5), which are not claimed declarations. So `decided` never applies to any finding the basics can produce on D, or the example `! decision added Packet::kind` refers to a non-claim subject.
Fix: either let decisions attach to enum-candidate subjects and state so, or replace `open_domain` with a verdict that can cover an escape/lost-claim on a vlib declaration. **Checked.**

**F8 — Seeded defect classes in §1.1 are not mapped to mechanisms.**
"Ingress guard removed or drifting" and "enumerator added without matching ingress" are *prevented* by `verbs::to` after migration (to accepts exactly the enumerators); they are not *detected* by §4. "Matching ingress" is undefined once to() is the ingress. journal.cpp:278's hard-coded `{1,2,4,65535}` vs `FrameKind` (journal.hpp:28-33) is real drift today, but after migration the class disappears rather than becomes a finding.
Fix: split seeded classes into (a) compiler/vlib prevention (measure rejection latency) and (b) escape-check detections (measure findings). Define "matching ingress." **Checked against blackbird.**

**F9 — Output caps N and M are unspecified.**
SPEC:598-599 "at most N findings per file and M in total" with carry-over of unshown findings. Unbuildable output contract.
Fix: pick concrete N, M in the spec (or say "plan sets them before implementation"). **Checked.**

**F10 — Over-budget can starve stale units under sustained header edits.**
SPEC:607-614 budget p95 10 s vs measured mean header fanout 72.5 TUs × ~3 s ≈ 14 s on 16 cores; foundation.hpp = 243 TUs. Pending backlog can grow; escapes in never-refreshed units stay invisible (stacks with F3).
Fix: require the next run to drain stale units before any new work, or fail closed (exit 2) when stale set is non-empty. **Checked (cost figures from checks M11 / SPEC:610-612).**

### MINOR

**F11 — Concurrency rule is narrower than the operator decision.** Operator (journal:83-88) admits lock-scoped / TSA capability claims; SPEC:132-133 puts all lock-scoped outside. Fine as basics-first, but say it is an intentional narrowing. **Checked.**

**F12 — "Violations throw" (§3.1) oversells.** `verbs::to` never throws; only compound ops throw. **Checked.**

**F13 — `std::start_lifetime_as` named in rule 2** is absent from Clang 23 libc++ (soundness B1 note). Prospective matcher is fine; say so. **Checked against soundness paper / toolchain.**

**F14 — Path-rule format "in the plan; not JSON"** (SPEC:554) leaves a load-bearing file format unsettled. **Checked.**

---

## Earlier tribunal blockers — not truly fixed

| Blocker | Status in rev 2 |
|---|---|
| Soundness B1 (void* fread/launder) | Rule text fixed, but read-only exception reopens a write hole (F2). |
| Checks B1 (--changed) | Verifying traces added; compile-error/over-budget staleness still false `holds` (F3, F10). |
| Doctrine D1 (path to kill criterion) | Migration story added (§1.1) but criterion unquantified and experiment still a bead (F4). |
| Doctrine D3 (decision gate) | Exit 3 specified; prevention is Blackbird hook that "does not exist yet" (SPEC:72-73). |
| Doctrine D13 (optional ingress) | Hardening ≥ FAST is a boundary assumption, not a safer ingress type. |
| Soundness M7 / attribution | Coarse rule kept; SPEC weakens type-erased case vs research (F5). |

## Machinery the basics do not need (overbuild)

1. **Full `Bounded` arithmetic** (`+ - * / %` interval widening, `__int128` edges) — no named blackbird consumer; SPEC:297-300 already says enums migrate first; D12. Keep `k`, `to`, `get`, implicit egress, checked `+=`/`-=`, `upto` only if a limit field is named.
2. **Cross-unit signature database (§4.4)** — ODR/type-confusion is real (soundness B6) but the first migration is a single decoding seam; a simpler "vlib type appears in two incompatible external decls" check or a deferred bead is enough for increment E.
3. **Negative probes / `__has_include` in traces** — needed only after include-set bugs show up; size/mtime/hash of SourceManager inputs is the verifying-trace core (checks B1).
4. **`verbs::upto` / `k` if `Bounded` is deferred** with the type.

## Execution step (after plan approval)

Write the full Markdown report to standard output only (no file writes). Structure as above; include concrete C++ counterexamples and blackbird file:line citations; mark guesses.

## Verification

Report is prose; verification is that every finding cites SPEC section/line, survives the counterexample, and that corpus claims match `blackbird/include/blackbird/journal.hpp:28-33` and `src/journal.cpp:278-281`.
