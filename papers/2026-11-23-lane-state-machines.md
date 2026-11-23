# Lane: state machines and typestate

Date: 2026-11-23. Habit under study: "use explicit state machines, and typestate
where it fits." This lane covers the constructs that could carry the habit, the
guards that could fire, and the evidence on detecting ad-hoc machines in existing
code. It does not design verbs.

Toolchains used for every probe:
- Homebrew clang 23.1.2 (`/opt/homebrew/Cellar/llvm/23.1.2/bin/clang++`, `-std=c++2c`,
  explicit `-isysroot`). Its clang-tidy and clang-query are the same build.
- rustc 1.99.0 (b940084d7, 2026-09-28), clippy 0.1.99.

Probe sources, matcher scripts and raw outputs are in the session scratchpad
(`.../scratchpad/sm/`, `.../scratchpad/rs/`, `.../scratchpad/ast/`,
`.../scratchpad/scan/`). The two corpus trees extracted for the AST measurement
(`context/scratch-state-machines/`) were deleted after the run.

## Headline findings

1. **Nobody in the corpus uses the existing typestate and FSM constructs.** A
   streaming scan of 1,340 corpus tarballs (1,002 distinct repositories, 887,757
   C/C++ files) found:
   - Clang Consumed attributes: zero production uses. The only hits were Clang's
     own tests, vendored copies of those tests, and one comment in mediapipe.
   - Boost.SML: zero includes.
   - Boost.MSM: used only by the MSM repository itself.
   - Boost.Statechart: Ceph is the one real user (its `PeeringState.h` mentions
     `boost::statechart` 379 times).
   - Ad-hoc patterns are everywhere by the same lexical scan (§B3). A
     `state`/`status`/`phase` field assigned a constant appears in 51% of
     repositories. A `switch` on such a field appears in 37%.
2. **Clang's Consumed analysis is too narrow to carry the habit.** Probes and a
   reading of `Consumed.cpp` (§A1) show:
   - It tracks only local variables, parameters and temporaries. It misses
     objects that are class members, reached through pointers, heap-allocated or
     captured by a lambda.
   - It has three fixed states.
   - Passing an object by non-const reference makes its state "unknown", so the
     next `callable_when("unconsumed")` call warns, whether or not the callee
     changed anything. Inside the callee, an unannotated `T&` parameter also
     starts "unknown", so every `callable_when("unconsumed")` call on it warns
     unless the parameter carries `param_typestate` (checker probe, see Check).
   - Since 2014 upstream has made refactors, NFC changes and crash fixes, plus
     two behavior changes: by-value arguments consume (2019) and consteval
     conditions are skipped (2024) (corrected in Check).
   - In leveldb, the one real protocol that fits Consumed's model exactly
     (`TableBuilder`: `Finish` or `Abandon` must be called, asserted in five
     methods) is held through raw pointers and struct members, where Consumed
     cannot see it.
3. **Every C++ FSM library examined handles "event not handled in this state" at
   run time.**
   - Boost.SML compiles `process_event` with an event that is not in the table at
     all, and returns `false` (probe and `sml.hpp:2493-2500`).
   - Boost.MSM's default `no_transition` is `BOOST_ASSERT(false)`.
   - All of them leave totality of the table unchecked.
4. **Totality can be a compile-time stop with a readable message.**
   - **C++ (pinned Clang 23.1.2):** a transition table declared as constexpr data,
     checked by a consteval function. A `static_assert` with a generated message
     prints "no row for state Closed on event Write; …" naming every missing pair
     (§A6).
   - **Rust:** an exhaustive `match (state, event)` gives E0004 listing the
     missing pairs.
   - **C++ `std::visit`:** stops too, but the missing pair is buried in a 72-line
     libc++ instantiation trace.
   - **C++ nested enum `switch`** (added by the checker, §A5b): stops under
     `-Werror=switch`, naming the missing events ("enumeration values 'Open'
     and 'Write' not handled in switch"). `-Wswitch-enum` also stops a
     `default:` catch-all. Neither needs owned code.
5. **A real gap in clippy: `wildcard_enum_match_arm` does not fire on the
   idiomatic `match (state, event) { …, _ => … }`.** It fires only when the
   scrutinee is a single enum (probe, §A8). The lint's source returns early for
   any scrutinee that is not an enum ADT, and nested matches are covered. The catch-all arm is exactly how a
   machine silently stops being total. C++ has the same hole with a generic
   `[](auto, auto)` handler in `std::visit`.
6. **Detecting ad-hoc machines has never been precise.** Published and measured
   numbers sit between 22% and about 60%:
   - Beckman et al.'s ProtocolFinder (an if-condition reads a receiver field and a
     branch throws) had 22.2% precision on 2,920 candidates in Java.
   - Grosche et al.'s candidate pattern (a global or static-local variable
     compared against a constant in an `if` or `switch`, with a constant
     assigned to it under that comparison) gave 100 true machines among 165
     candidates (61%) in automotive C.
   - My small prototype on leveldb and ninja: 6 of 11 distinct flagged fields true
     (55%), with my labels only and no held-out set (§B3).
   - The best single signal I saw was "an enum/bool field guarded (if-return,
     if-throw or assert) in two or more methods and written outside the
     constructor": 5 of 6. That sample is far too small to set a stop on.
7. **No evidence exists on agent ergonomics for typestate or FSM constructs.**
   The nearest human evidence: in Sunshine et al., six professional programmers
   spent 71% of protocol-task time on "state search" (what state am I in, which
   methods are legal now). The checker added two more human studies (B1):
   - state-organized documentation cut state-task time to 46% (Sunshine et al.
     2014);
   - in Obsidian, every participant reached for a dynamic state check instead
     of typestate, and every one who finished the open task misused the escape
     hatch (Coblenz et al. 2020).

---

## Part A. Constructs and analyses that can carry the habit

### A1. Clang Consumed analysis (`-Wconsumed`)

**What it is and how it works.** Source: `quarantine/llvm-project` 23.1.2,
`clang/lib/Analysis/Consumed.cpp` (1,412 lines) and
`clang/include/clang/Basic/Attr.td:4290-4383`.

- **Attributes.**
  - `consumable(state)` on a class.
  - `callable_when("…")` on a method.
  - `set_typestate(s)` on a method.
  - `return_typestate(s)` on a function, constructor or parameter.
  - `param_typestate(s)` on a parameter.
  - `test_typestate(s)` on a bool-returning method.
  - Two undocumented class attributes, `consumable_auto_cast_state` and
    `consumable_set_state_on_read` (`Attr.td:4304-4320`).
- **States are fixed** at `unknown`, `consumed` and `unconsumed`
  (`Attr.td:4298-4300`). A user cannot name more.
- **What it runs over.** It is an intraprocedural dataflow over the CFG. It is run
  from Sema (`AnalysisBasedWarnings.cpp:3183-3187`) for every function body when
  the `consumed` group is on.
- **Diagnostics.** All 8 are warnings in group `-Wconsumed` and are
  `DefaultIgnore` (`DiagnosticSemaKinds.td:4505-4529`).
  - The group is not in `-Wall` or `-Wextra`. It is defined standalone
    (`DiagnosticGroups.td:1513`) and appears in no umbrella group.
  - The main message is "invalid invocation of method '%0' on object '%1' while it
    is in the '%2' state".
- **What it tracks.** The state map is keyed by `VarDecl` and by temporary
  (`ConsumedStateMap::VarMap`/`TmpMap`). `VisitDeclRefExpr` only creates info for
  `VarDecl`s (`Consumed.cpp:825-828`). A `FieldDecl` is never a key, so member
  objects are never tracked.
- **Pointers and references.** `isConsumableType` returns false for any pointer or
  reference type (`:140-147`). A pointer to a consumable object is not tracked.
  Reference *parameters* are tracked, though, because the parameter is itself a
  `VarDecl`: `VisitParmVarDecl` (`:850-866`) gives a `T&&` parameter the class's
  default state, a `T&` parameter `unknown`, and an annotated parameter its
  `param_typestate` (corrected in Check).
- **Calls.** Only direct callees are handled (`:734-735`, `:807-808`). Virtual
  calls through a base pointer and calls through function pointers are ignored.
- **Arguments.**
  - An rvalue-reference or by-value consumable argument becomes `consumed`
    (`:642-643`).
  - A non-const lvalue reference or pointer argument becomes `unknown`
    (`:644-647`).
- **`std::move`** marks the source `consumed` (`:740-742`).
- **A default-constructed consumable object starts `consumed`** (`:777-779`).
- **Branches and loops.**
  - At a join, differing states merge to `unknown` (`intersect`,
    `:1125-1141`).
  - At a loop back edge, a mismatch warns "state of variable must match at the
    entry and exit of loop" (`:1158-1160`).
- **Path splitting.** Only `if` conditions and `&&`/`||` built from
  `test_typestate` calls split state (`splitState`, `:1221-1307`). The source's
  own TODOs say loops and other branching are not handled with precision
  (`:1372-1373`, `:36-49`). Two tests are `#if 0` with "FIXME: Get this test to
  pass" (`clang/test/SemaCXX/warn-consumed-analysis.cpp:280`, `:386`).
- **Maintenance.** Upstream history (GitHub API, path filter, fetched
  2026-11-23): 93 commits from 2013-08 to 2025-12. Since 2014 they are refactors,
  NFC changes and crash fixes, for example "Handle null dtor decl during consumed
  analysis" (#170180, 2025-12-01). Two changed behavior: "[Consumed] Treat
  by-value class arguments as consuming by default, like rvalue refs"
  (2019-09-19) and "skip consumed analysis for consteval conditions in
  control-flow terminators" (#117403, 2024-11-27). No paper exists. The attribute docs
  (`AttrDocs.td:3810-3866`) are a few sentences each.

**Probe** (`scratchpad/sm/consumed_probe.cpp`, clang 23.1.2 `-Wconsumed`). The
class has `consumable(unconsumed)`, `write` is `callable_when("unconsumed")` and
`close` is `set_typestate(consumed)`.

| Case | Warns? | Note |
|---|---|---|
| local: `close(); write()` | yes | the intended use |
| local: `g = std::move(f); f.write()` | yes | |
| member field: `f.close(); f.write()` in a method | **no** | fields not tracked |
| `touch(File&)` then `write()` | **yes, "unknown"** | false finding whenever `touch` leaves it open |
| `closer(File&)` that closes, then `write()` | yes, "unknown" | true, but for the reason above, not by understanding `closer` |
| `if (b) f.close(); f.write();` | yes, "unknown" | |
| `if (f.is_open()) f.write();` after the same branch | no | `test_typestate` refines |
| close inside a loop body | yes, loop mismatch | |
| template instantiation | yes | runs on instantiations |
| `File* p = &f; p->close(); f.write()` | **no** | pointer aliases are invisible |
| lambda capture closes | **no** | |
| `new File` then `close`, `write` via pointer | **no** | heap is invisible |

Checker probe (`scratchpad/chk/consumed_ref.cpp`, same compiler and flags):

| Case | Warns? | Note |
|---|---|---|
| `void r1(File& f) { f.write(1); }`, no annotation | **yes, "unknown"** | callee-side false finding on every unannotated `T&` parameter |
| same with `param_typestate(unconsumed)` on `f` | no | the annotation is the contract |
| caller closes `f`, then passes it to that annotated parameter | yes, "argument not in expected state; expected 'unconsumed', observed 'consumed'" | the one interprocedural check Consumed has |
| `File&& f`: `write`, `close`, `write` | yes, on the second `write` | rvalue-ref parameters are tracked |
| by-value `File f`: `close`, `write` | yes | |

So the "non-const reference" false-finding source cuts both ways: at the call
site (state becomes unknown) and in every callee that takes `T&` without
`param_typestate`. Adopting Consumed means annotating every such parameter.

**How it would carry the habit.**
- It only fits a two-state lifecycle (open/closed, valid/moved-from) on local
  values in C++. It is a stop-capable compiler warning (`-Werror=consumed`).
- It cannot carry a machine with more than two named states, and cannot carry a
  protocol held in a member.
- Most real protocol objects are members or pointers. In leveldb, `TableBuilder`
  is held as `TableBuilder* builder = new TableBuilder(...)` (`db/builder.cc:31`)
  and as `CompactionState::builder` (`db/db_impl.cc:83`, `:826`).

**Precision and ergonomics evidence.**
- None published.
- The probe shows a structural false-finding source: any non-const reference
  pass. The workaround, `callable_when("unconsumed", "unknown")`, also turns off
  the branch-merge and helper-closes detections above.
- Zero production adopters were found in 1,002 corpus repositories (§B3).

**Costs and failure modes.**
- No toolchain burden: it ships in Clang.
- Suppression is only by `#pragma clang diagnostic`. There is no reason field and
  no staleness check, because these are Sema warnings, which `[[clang::suppress]]`
  explicitly cannot silence (`AttrDocs.td:6632-6643`).
- The analysis is effectively unmaintained.

### A2. Phantom-type typestate in C++, plus `bugprone-use-after-move`

**What it is.** The state is a template parameter. Each transition is an
`&&`-qualified member constrained by `requires std::same_as<S, From>` that
returns `T<To>`.

Probe (`scratchpad/sm/ts_err.cpp`, `ts.cpp`):
- **Wrong-state call** is a hard error: "invalid reference to function 'fire':
  constraints not satisfied … because 'std::same_as<Idle, Armed>' evaluated to
  false". The note chain then runs through libc++'s `same_as.h`.
- **Calling a transition on an lvalue** is a hard error: "'this' argument to
  member function 'arm' is an lvalue, but function has rvalue ref-qualifier".
- **Reusing the moved-from handle** (`std::move(d).arm()` twice, or
  `d.inspect()` after the move) compiles. The brief already notes this gap
  (`design/verbs-design-brief.md:105`).

**The moved-from gap is partly closed by an existing tool.** clang-tidy
`bugprone-use-after-move` (23.1.2) flags both reuses ("'d' used after it was
moved"). Its `InvalidationFunctions` option also turns any named method into a
consuming one:
- `{bugprone-use-after-move.InvalidationFunctions: '::Conn::close'}` produced
  "'c' used after it was invalidated by 'close'" on a local `Conn`.
- Docs: `clang-tools-extra/docs/clang-tidy/checks/bugprone/use-after-move.rst:265-281`.
- Release note on including the invalidating function's name:
  `clang-tools-extra/docs/ReleaseNotes.rst:575-583`.
- Like Consumed, it **missed the member-field case** (`Holder::m`).
- Checker probe (`scratchpad/chk/uam.cpp`, `uam2.cpp`, same option): it is keyed
  on the variable, not the object. It also flagged `p->close(); p->send()` on a
  pointer parameter, `r.close(); r.send()` on a reference parameter, and a heap
  object held in a local pointer (`Conn* p = new Conn`). It missed an alias
  (`Conn* q = p; p->close(); q->send()`), a close inside a helper that takes
  `Conn&`, and `std::move` of a member as well as `close` on one.
- It is control-flow aware, documents its conservative choices (rvalue-ref
  parameters always count as moves, `try_emplace` exempt) and is maintained.

**How it would carry the habit.**
- Construct: typestate types for linear protocols such as builders, handles and
  sessions.
- Stop: the compile errors above.
- Bypass stop: use-after-move, or an owned equivalent, on the handle.
- Language: C++ only. Rust gets this from the borrow checker (A7).

**Evidence.** No precision data. clang-tidy's use-after-move documentation
lists its false-finding classes explicitly (mutually exclusive branches it cannot
prove, `use-after-move.rst:53-66`).

**Costs and failure modes.**
- The typestate value must be threaded through every call (`x = std::move(x).f()`
  does not type-check when the state changes). Loops need a sum type over the
  states, which is the same limitation Duarte and Ravara report for Rust (§A7).
- Each state is a distinct type, which multiplies template instantiations.
- Diagnostic quality is acceptable for constraint failures. It degrades when
  states are deduced through several layers.

### A3. Boost.SML (`quarantine/sml`, commit bc13fcbb, BSL-1.0)

**What it is.**
- A header-only (3,693-line `include/boost/sml.hpp`), C++14 library with no std
  includes.
- A machine is a callable returning `make_transition_table(...)`: rows of
  `src + event<E> [guard] / action = dst`.
- The table is a type, so tools can visit it at compile time
  (`example/plant_uml.cpp` reads `T::src_state`, `T::event`, `T::dst_state`,
  around line 280).
- **Policies:**
  - `sml::logger<T>` calls `log_process_event`, `log_guard`, `log_action` and
    `log_state_change` (`sml.hpp:1835-1893`). This is a ready trace-emission
    hook.
  - `sml::testing` enables `set_current_states` (`sml.hpp:2567-2580`).
  - `thread_safe` and `dispatch` are the others.
- **Compile-fail tests** are CMake targets with `WILL_FAIL TRUE`
  (`test/ft/errors/CMakeLists.txt`). They cover only table-shape errors
  (`not_transitional.cpp`, `not_dispatchable.cpp`, …), not semantic ones.

**What it does with misuse** (probe `scratchpad/sm/sml_probe.cpp`):
- An event that **is** in the table but has no row in the current state: compiles,
  and `process_event` returns `false`.
- An event that is **not in the table at all**: compiles, and returns `false`. The
  overload at `sml.hpp:2497-2500` wraps it into `unexpected_event<_, E>`.
- A false guard returns `false`.
- Output was `0 0 0 open=1`.
- State mutation from outside is impossible except under the testing policy,
  because `current_state_` is private to `sm_impl`.
- Table totality and reachability are never checked.

**How it would carry the habit.**
- As a construct it carries "the machine is explicit and the state is
  encapsulated".
- It does not stop unhandled events.
- A verbs check could visit the table type and assert totality, but guards are
  opaque callables, so totality can only be "modulo guards"
  (`papers/2026-10-17-reference-implementations.md:183-184`).

**Evidence.**
- No precision data applies.
- Compile cost was 0.05 s for `-fsyntax-only` on the 3-state probe.
- The MSM project's benchmark (`quarantine/msm/doc/modules/ROOT/pages/backmp11-back-end.adoc`)
  reports SML at 4 s / 254 MB for a "large" machine and 13 s / 612 MB for a
  "large hierarchical" one.
- Adoption in the corpus: zero.

**Costs.**
- Adopting it is a library adoption and needs discussion with the operator.
- Its error messages for table mistakes are template traces.
- Unhandled events fail silently at run time unless the table declares
  `unexpected_event` rows.

### A4. Boost.MSM, Boost.Statechart and other C++ FSM libraries

- **MSM** (`quarantine/msm`, f2d60cb):
  - The table is a list of `Row<>` types.
  - The default `no_transition` handler is `BOOST_ASSERT(false)`
    (`include/boost/msm/front/state_machine_def.hpp:209-212`): an unhandled event
    aborts at run time in debug builds.
  - `back/mpl_graph_fsm_check.hpp` (48 lines) checks orthogonality of regions and
    that every state is reachable, via `BOOST_MPL_ASSERT_RELATION`. That is
    graph structure only, with no totality check.
  - The new `backmp11` back end (C++17, "experimental") cuts compile time from
    10 s to 2 s and RAM from 844 MB to 236 MB on the large benchmark
    (`backmp11-back-end.adoc`, table at top).
  - It depends on the rest of Boost.
- **Boost.Statechart** is the only explicit C++ machine framework found in
  production use in the corpus (Ceph `src/osd/PeeringState.h` and crimson).
  - It is runtime-dispatched (`react` functions, `custom_reaction`).
  - Unhandled events are discarded by default. Verified in the checker pass:
    `state_machine::unconsumed_event` is documented as "Effects: None" and is
    "called by process_event() whenever a dispatched event did not trigger a
    reaction" (`boostorg/statechart` 586445b8, `doc/reference.html`, from the
    corpus tarball). Not probed.
- **Others** (GitHub API, 2026-11-23):

  | Library | Stars | Last push | Character |
  |---|---|---|---|
  | HFSM2 | 649 | 2026-06-27 | hierarchical, runtime dispatch over a compile-time structure |
  | TinyFSM | 1,200 | 2024-06-25 | static polymorphism, runtime dispatch |
  | ETL `etl::fsm` | ETL has 3,173 | 2026-11-22 | embedded, message-router based |
  | erikzenker/hsm | 207 | 2022-12-23 | |
  | afsm | 181 | 2026-03-18 | |

  None stops unhandled events at compile time. The scan found no corpus users of
  TinyFSM or HFSM2.
- **ProtEnc** (nitnelave/ProtEnc, 63 stars, last push 2019-08-20) wraps a class
  so that any call off the declared protocol graph is a compilation error. It is
  phantom typestate with a declared transition list.
- **Coconut** (Alsubhi and Dardha 2024,
  `papers/alsubhi-dardha-2024-coconut-cpp-typestate.pdf`, §2.3-2.4) builds a
  typestate template on Boost.Hana.
  - Invalid transitions are `static_assert` failures when the path is known at
    compile time ("within if-constexpr conditions or loops"). Otherwise runtime
    assertions handle "dynamic behaviours" and aliasing.
  - The authors report it "incurs a higher compile-time overhead compared to
    other benchmarks" (§4).
  - Their evaluation is one PillBox case study, with no bug-finding precision
    numbers.
  - **Coconut v2** (Alsubhi, Dardha, Gay, "Design and Evaluation of Coconut:
    Typestates for C++", Science of Computer Programming 250 (2026) 103398,
    `papers/alsubhi-dardha-gay-2026-coconut-design-evaluation-scp.pdf`, from
    https://www.dcs.gla.ac.uk/~ornela/publications/ADG26.pdf, accessed
    2026-11-23; added by the checker) drops the template design. The paper
    names "long compile times from repeated template instantiations, and
    limited scalability" as v1's two key limitations. v2 is a **GCC plugin** that
    checks the protocol on GIMPLE-SSA, with a runtime fallback where the target
    cannot be resolved. Code: https://github.com/CoLab-Glasgow/Coconut. A GCC
    plugin cannot run under the pinned Clang toolchain. The evaluation reports
    performance and code-complexity figures (PillBox compile time 120 ms to
    200 ms), still with no precision numbers.
  - The same papers list the Java typestate checkers Mungo/StMungo and JaTyC
    and Papaya for Scala as related tools (ADG26 §1). None is for C++ or Rust.

### A5. `std::variant` state with `std::visit` over (state, event)

**Probe** (`scratchpad/sm/var.cpp`): a visitor over
`variant<Closed, Open, Draining>` × `variant<EvOpen, EvWrite, EvClose>` with a
missing pair.

- **It is a stop.** The error comes from libc++ `variant:547`, "no matching
  function for call to '__invoke'", then a 72-line trace. The missing pair shows
  up only in a note: `__alt<0UL, Closed> &, __alt<1UL, EvWrite> &`. Only the first
  missing pair is reported.
- **A generic catch-all `[](auto s, auto) -> State { return s; }` silences it
  completely** (0 lines). That is the C++ form of Rust's `_ =>` arm.

**How it would carry the habit.**
- Construct: state as a sum type, where each state owns only its own data. That
  is DeLine and Fähndrich's "typestates generalize object invariants" in plain
  C++ (`papers/2026-10-17-literature-core.md` §6).
- Stop: exhaustive visit.
- Nudge or stop: a catch-all generic handler in a machine's visitor.

**Costs.** Diagnostics are poor. Code size and compile time grow as states ×
events.

### A5b. Nested `switch` over enum state and enum event, with Clang's switch warnings (added by the checker)

The lane did not probe the plainest C++ form. Here `State` and `Event` are enum
classes, and the step function is `switch (s) { case X: switch (e) { … } }`.

**Probe** (`scratchpad/chk/sw.cpp`, clang 23.1.2 `-std=c++2c -fsyntax-only`):
- `-Wall` (which includes `-Wswitch`, `DiagnosticGroups.td:1518`):
  `sw.cpp:8:13: warning: enumeration value 'Write' not handled in switch [-Wswitch]`
  and `enumeration values 'Open' and 'Write' not handled in switch`. The
  message names the missing events by name with no reflection, macro or name
  table. The state is not named: it is the enclosing `case`, given by the source
  location.
- A `default:` arm in the inner switch silences `-Wswitch`. `-Wswitch-enum`
  still fires: "enumeration value 'Open' not explicitly handled in switch
  [-Wswitch-enum]" (`DiagnosticSemaKinds.td:11316-11321` for `warn_missing_case`).
  That makes it the C++ stop for the catch-all hole, the counterpart of the
  owned Rust lint in A8.
- `-Wcovered-switch-default` (`DiagnosticSemaKinds.td:11343-11345`, "default
  label in switch which covers all enumeration values") flags a `default:` that
  is dead today and would swallow a future enumerator.

**How it would carry the habit.**
- Stop: `-Werror=switch` plus `-Werror=switch-enum`, with no owned machinery.
- Limits:
  - `-Wswitch-enum` applies to every switch in the translation unit, and
    `default:` on an enum switch is common outside machines. Scoping it to
    machine step functions needs `#pragma clang diagnostic` push/pop or an owned
    check.
  - It says nothing about duplicate rows, reachability, or state written
    outside the step function. Those still need A6 or lints.
  - Switching on an `int` state gives no warning at all.
- Corpus (checker scan of build files: CMakeLists, `*.cmake`, Makefiles, meson,
  Bazel, GN, autoconf, over the same 1,002 repositories):
  - `-Wswitch-enum` appears in 30 repositories;
  - `-Werror=switch` in 5;
  - `-Wcovered-switch-default` in 5;
  - `-Wswitch-default` in 13;
  - `-Wconsumed` in 0.
  - C++ sources mention a `#pragma … diagnostic … "-Wswitch-enum"` in 39
    repositories. The scan did not separate enabling from disabling.

**Costs.** None in toolchain or compile time; the warnings ship in Clang. The
reason-carrying way past is weak: only `#pragma clang diagnostic ignored`, with
no reason field and no staleness report (same as A1).

### A6. Table as constexpr data with a consteval totality check (owned-construct probe)

**Probe** (`scratchpad/sm/table.cpp`):
- States and events are enums.
- The table is a `constexpr std::array<Row>`, where each row is
  `{from, on, kind ∈ {Go, Ignore, Illegal}, to}`.
- A consteval function builds a `std::string` describing every (state, event)
  pair with zero rows or more than one row.
- `static_assert(missing_rows().empty(), missing_rows());` uses a C++26
  user-generated `static_assert` message, which the pinned Clang 23.1.2 accepts.

Output:

```
table.cpp:30:15: error: static assertion failed due to requirement
'missing_rows().empty()': no row for state Closed on event Write; no row for
state Open on event Open; no row for state Draining on event Open; no row for
state Draining on event Write;
```

**How it would carry the habit.**
- Construct: one declared table, the single source of truth, readable by tools.
  It can feed the trace check in A12 and diagram generation.
- Stops at compile time:
  - the table is not total (each pair must be `Go`, `Ignore` or `Illegal`,
    explicitly);
  - duplicate rows;
  - unreachable states, by a BFS in the same consteval function;
  - an event type outside the alphabet passed to `fire`, by a constrained
    template.
- State is private to the machine object, so "state mutated outside the machine"
  is impossible by construction.
- What remains is **bypass**, which needs lints:
  - a second, parallel state variable added next to the machine;
  - a `const_cast` or `friend` into it;
  - a catch-all handler.

**Costs.**
- The probe hand-wrote the name tables for messages. Without P2996 reflection,
  which the pinned Clang 23.1.2 lacks
  (`papers/2026-10-17-cpp26-clang-toolchain.md:6`, `:104-107`), enumerator names
  need a macro or a magic_enum-style trick (`quarantine/magic_enum`).
- Guards, as data-dependent conditions on a `Go` row, make the check "total
  modulo guards". A guarded row must name its fallback.
- Compile cost grows as states × events × rows. It was not measured beyond the
  toy.

### A7. Rust typestate: consuming `self` and `PhantomData`

**Probe** (`scratchpad/rs/rprobe/src/lib.rs`):
- `Door<Idle>::arm(self) -> Door<Armed>`.
- **Wrong-state call:** E0599 "no method named `fire` found for struct
  `Door<Idle>`", followed by "the method was found for" pointing at the
  `Door<Armed>` impl.
- **Reuse after transition:** E0382 "use of moved value: `d`". This is the stop
  C++ lacks.
- **`#[must_use]`** on the typestate type warns when a transition result is
  discarded (`Tok::<Idle>::new().arm();`).
- **Silent drop:** `let t = …arm(); drop(t);` is silent. Rust is affine, not
  linear.
- Kokke (`papers/kokke-2019-rusty-variation-session-types-rust-ice.pdf` §2.3):
  dropping without completing "is trickier, as Rust's type system doesn't help us
  here". Rusty Variation turns drop into cancellation through `Drop`.

**Duarte and Ravara, "Retrofitting Typestates into Rust", SBLP 2021**
(`papers/duarte-ravara-2021-retrofitting-typestates-rust-sblp.pdf`; crate
`typestate` 0.8.0):
- A proc-macro reads a `#[typestate]` module.
- It infers transitions from functions that consume `self` and return a state,
  initial states from functions that do not consume `self`, and final states from
  functions that consume `self` and return no state (§3).
- At expansion time it rejects states that are not productive or not useful,
  with a pointed error ("Non-useful state. For a state to be useful it must first
  be productive and a path from initial…", Fig. 5).
- Loops need a generated enum of all states (§3.4), the same limitation as in
  C++.
- Crate adoption is small: 42,979 downloads, last release 2021-09-02 (crates.io
  API, 2026-11-23).

**How it would carry the habit.**
- Rust: construct = typestate types. Stops = E0599 and E0382, native. Nudge =
  none is needed for reuse.
- The remaining hole is drop-before-final-state. A `Drop` impl that panics or
  logs at run time can cover it, or an owned lint.

**Evidence.** No precision data. Duarte and Ravara report no user study.

### A8. Rust enum machine with exhaustive `match (state, event)`

**Probe.**
- **Exhaustive match.** With no wildcard, a missing pair gives "E0004:
  non-exhaustive patterns: `(State::Closed, Event::Write)`, `(State::Open,
  Event::Open)`, `(State::Draining, Event::Open)` and 1 more not covered". That
  is a stop naming the pairs, truncated after three.
- **The clippy gap.** With `_ => None`:
  - `clippy::wildcard_enum_match_arm` (restriction) **did not fire** on the
    tuple match (`lib.rs:27`).
  - It did fire on `match s { State::Closed => 0, _ => 1 }` and on a nested
    `match e { …, _ => 2 }` ("wildcard match will also match any future added
    variants").
  - So the canonical Rust machine idiom escapes the only lint aimed at
    wildcards.
  - Why (checker, from source): `clippy_lints/src/matches/match_wild_enum.rs`
    `check` returns at once unless the scrutinee type is an enum ADT other than
    `Option`/`Result` (lines 15-23; rust-clippy master, last change to the file
    15d082bb, 2026-09-11, fetched 2026-11-23). A tuple scrutinee is
    `ty::Tuple`, so neither `wildcard_enum_match_arm` nor
    `match_wildcard_for_single_variants` looks at it. Open issue #17291
    (2026-06-22) reports the same early exit for `Option<LocalEnum>`. No issue
    for tuples was found.
  - So a machine written as nested matches (`match s { S::Open => match e { …
    } … }`) is covered today. The probe's `nested` function fired twice,
    `lib.rs:43:97` and `:107`.
  - Re-run by the checker: same result with clippy 0.1.99 and with the machine's
    default stable toolchain, clippy 0.1.94. The 1.99.0 pin comes from the
    verbs `rust-toolchain.toml`; scratch crates outside the repository get
    1.94.1 unless run with `+1.99.0`.
- `clippy::match_same_arms` (pedantic) fired on the two arms returning
  `Some(State::Open)`. That is noise for a transition function.

**How it would carry the habit.**
- Construct: `enum State` (with per-state data), `enum Event`, and one
  `fn step(self, Event) -> Result<State, Illegal>`.
- Stop: E0004.
- Bypass: a `_` arm in the machine's step function. That needs an owned lint,
  delivered as a Dylint/rustc driver lint like any other verbs Rust lint.
- Way past: `#[expect(verbs::machine_wildcard, reason = "…")]`. The probe confirms
  `#[expect]` reports "this lint expectation is unfulfilled" when it goes stale.

### A9. Rust FSM crates

Downloads, versions and last-update dates are from the crates.io API
(2026-11-23). Behavior is from each README (`raw.githubusercontent.com/<repo>/HEAD/README.md`,
fetched 2026-11-23).

| Crate | Version / downloads / updated | Table form | Unhandled event |
|---|---|---|---|
| statig | 0.4.1 / 4.7M / 2025-07-05 | per-state handler fns with `match event`; hierarchical superstates | `_ => Super` defers to the parent. A catch-all is the idiom (README lines 67-95). Has `before_dispatch`/`after_dispatch` hooks for tracing (lines 253-277). |
| rust-fsm (+dsl) | 0.8.0 / 1.6M / 2025-07-21 | `state_machine!` DSL; optional Mermaid diagrams | `consume(&input)` returns `Err` at run time (README lines 105-110) |
| smlang | 0.8.0 / 1.2M / 2024-08-09 | Boost.SML-style DSL (`*S1 + E1 [guard] / action = S2`) | runtime error from `process_event`; with overlapping guards, the first enabled wins (README lines 139-142) |
| sm | 0.9.0 / 2.0M / 2019-11-09 | typestate-generating macro | compile-time, via types |
| typestate | 0.8.0 / 43k / 2021-09-02 | see A7 | compile-time; checks productive/useful states |
| state_machine_future | 0.2.0 / 281k / 2018-11-10 | archived-era async machines | n/a |
| typed-builder (checker) | 0.23.2 / 125.1M / 2025-11-19 | derive macro; typestate builder | compile-time: "Compile time verification that all fields are set before calling `.build()`" and "that no field is set more than once" (README lines 49-50) |
| bon (checker) | 3.10.3 / 81.8M / 2026-10-23 | derive/function macro; typestate builder | compile-time: "Builders generated by `bon`'s macros use the typestate pattern … If something is wrong, a compile error will be created" (README line 181) |
| derive_builder (checker, for contrast) | 0.20.2 / 250.3M / 2024-10-08 | derive macro; runtime builder | `build()` returns `Result` at run time |

**Implication.**
- The popular FSM crates (statig, rust-fsm, smlang) treat "not handled here" as
  a runtime outcome or a catch-all.
- Among FSM crates, the ones that stop at compile time are the typestate ones,
  with low recent use.
- Corrected by the checker: typestate itself is not rare in Rust. Two
  typestate *builder* crates have about 207M downloads together (typed-builder
  plus bon; 56M in the last 90 days, crates.io `recent_downloads`, 2026-11-23).
  The most-downloaded builder, derive_builder, still checks at run time. So
  Rust users accept typestate for one narrow, linear protocol (set fields, then
  build) when a macro generates it. That is evidence on adoption, not on
  precision or agent ergonomics.
- The strongest Rust realization is the language's own `match` exhaustiveness
  plus ownership. No crate is required.

### A10. Session types

- **Rust:**
  - `session_types` (Jespersen et al., WGP 2015; crate 0.3.1, last updated 2019).
  - Rusty Variation (Kokke 2019, above).
  - Ferrite (crate 0.3.0, 2022).
  - Multiparty: Rumpsteak (2021) and `mpstthree` (Lagaillardie et al.; 0.1.17,
    2024).
  - `dialectic` (2021) and `par` (0.3.10, 2025).
  - All have under 30k downloads except `mpstthree` at 25.7k. Most are dormant
    (crates.io API).
  - All rely on affine ownership, so a session can be dropped mid-protocol unless
    `Drop` handles it (Kokke §2.3).
- **C++:** no maintained session-type library was found.
  - The Edinburgh collection of session-type implementations
    (https://groups.inf.ed.ac.uk/abcd/session-implementations.html, seen in
    search 2026-11-23) lists none for C++ in the results returned.
  - ProtEnc and Coconut (A4) are the C++ typestate analogues.

**How it would carry the habit.** Only for message protocols between two or more
parties, which is a narrower habit than object state. It is not a candidate for
the first starter habits.

### A11. Clang Static Analyzer typestate-style checkers

The static analyzer in `quarantine/llvm-project` contains path-sensitive,
interprocedural (by inlining) protocol checkers:

- `SimpleStreamChecker.cpp` (the tutorial open/close checker) and
  `StreamChecker.cpp`.
- `PthreadLockChecker.cpp` and `MoveChecker.cpp`.
- `FuchsiaHandleChecker.cpp`.
  - Its header comment (lines 1-80) draws an explicit state diagram: Allocated,
    Released, Escaped, double-release, use-after-release, leak.
  - It is driven by attributes `acquire_handle`, `release_handle` and
    `use_handle` (`Attr.td:4959-4975`) rather than hard-coded names.

The analyzer tracks memory regions, so fields and heap objects are in scope,
unlike Consumed.

**How it would carry the habit.** An annotation-driven typestate checker in this
style could track members and pointers.

**Costs.**
- Analyzer runs are slow: whole-TU path exploration, not edit-time.
- Out-of-tree checker plugins must match the exact Clang build.
- No precision numbers for these checkers were found in the sources read.

This is a later option, not a first one.

### A12. Trace validation against a declared machine

- **etcd-raft** (`quarantine/etcd-raft`, 638f427):
  - Trace points sit at the code's transitions: `traceInitState`,
    `traceBecomeFollower`, `traceBecomeCandidate`, `traceBecomeLeader`,
    `traceCommit` (`raft.go:469`, `:776`, `:899`, `:914`, `:960`).
  - They are compiled in only under build tag `with_tla` (`state_trace.go:15`).
    `state_trace_nop.go` supplies empty bodies otherwise, so production cost is
    zero.
  - Records are NDJSON `TracingEvent`s (`state_trace.go:83-93`) that
    `tla/Traceetcdraft.tla` replays through TLC (`tla/README.md`).
- **trace_validation_tools** (`quarantine/trace_validation_tools`, 7b31b03): a
  Java instrumentation library plus TLA+ templates (`templates/TraceSpec.tla`,
  `TVOperators.tla`), merged and checked by `scripts/tla_trace_validation.py`.
- **Literature already in papers/:**
  - Cirstea et al. 2024 found discrepancies "in every system it was applied to".
  - CCF trace validation found six bugs.
  - Model-based trace checking failed at MongoDB
    (`papers/2026-10-17-literature-core.md:602-640`).

**How it would carry the habit.**
- For a finite declared machine, no TLA+ or TLC is needed. Checking that every
  observed `(from, event, to)` record is a row of the declared table is a set
  membership test.
- The record can come from the construct's own hook:
  - an A6-style `fire` writes it;
  - SML's `logger` policy and statig's `after_dispatch` already provide one.
- This covers what the compile-time check cannot:
  - guards (which row actually fired);
  - code that sets the machine's state through a testing back door;
  - the correspondence between an ad-hoc machine and a table proposed for it.
- It is also a seeded-fault oracle: mutate the code and see whether the trace
  leaves the table.

**Costs.** It needs tests that drive the machine. It proves nothing about
untested paths.

### A13. Accumulation typestate and the Resource Leak Checker (added by the checker)

**What it is.**
- Kellogg, Shadab, Sridharan, Ernst, "Accumulation Analysis", ECOOP 2022,
  LIPIcs 222:10 (`papers/kellogg-2022-accumulation-analysis-ecoop.pdf`).
  - An *accumulation* typestate system is one whose error-inducing call
    sequences stay error-inducing when earlier calls are removed (Definition 7,
    §3.2). Example: "`build()` before `setX()` was called", or "object dies
    before `close()`".
  - The paper proves these are exactly the typestate specifications that can be
    checked soundly **without aliasing information** (§3.3), and gives a
    decision procedure (Algorithm 1).
  - 41% of the typestate specifications it surveyed from the literature are
    accumulation (abstract).
  - "No `write` after `close`" is not accumulation. Removing the `close` makes
    the sequence legal, so checking it soundly needs alias analysis. The paper's
    non-accumulation example is a File that can be reopened.
- Kellogg et al., "Lightweight and Modular Resource Leak Verification",
  ESEC/FSE 2021 (`papers/kellogg-2021-resource-leak-verification-fse.pdf`): the
  Resource Leak Checker, a Checker Framework pluggable type system for Java
  that applies this idea to "must call `close()` before unreachable".
  - Annotations: `@MustCall`, `@CalledMethods`, `@Owning`, `@MustCallAlias`,
    `@CreatesMustCallFor`.
  - It handles **fields**: a final owning field is discharged by the enclosing
    class's own must-call method, and a non-final field write creates a fresh
    obligation (§5).

**Precision and burden** (Table 1, Table 4, §7):
- 427,858 LoC: ZooKeeper, HDFS, HBase, plume-util.
- 49 true leaks and 121 false positives: **29% precision (49/170)**.
- Against a common code subset with 15 known leaks:

  | Tool | Recall | Precision |
  |---|---|---|
  | Resource Leak Checker | 100% | 26% |
  | Eclipse's high-confidence analysis | 13% | 25% |
  | Grapple | 7% | 50% |

- Causes of false positives: 22% a Checker Framework generics-inference bug,
  15% `Optional` taking ownership, 8% nullness reasoning.
- Annotation burden: 286 annotations, about 1 per 1,500 LoC, plus 42 code
  changes.
- An author ran it on his own 10 KLoC library in about two hours. The library
  now runs it in CI.

**How it would carry the habit.**
- It answers part of open question 4 (members and heap objects).
- Split a C++ or Rust protocol into its accumulation part and the rest:
  - "must call `Finish()` or `Abandon()` before destruction" (leveldb
    `TableBuilder`, `assert(rep_->closed)` in the destructor,
    `table/table_builder.cc:73`) is accumulation. An owned flow-sensitive check
    could carry it through fields and pointers without alias analysis.
  - "no `Add()` after `Finish()`" (`assert(!r->closed)` at `:96`, `:127`,
    `:216`, `:272`) is not accumulation. It needs typestate-by-construction
    (A2, A7) or a runtime check.
  - The same split covers Rust's one hole: drop before the final state (A7) is
    an accumulation property.
- Languages: the published tool is Java only. Nothing equivalent exists for
  C++ or Rust; the idea would have to be owned.

**Costs.**
- Precision near 30% is too low for a stop by this repository's standard. It
  would be a nudge, or a stop only on types that opt in.
- Ownership transfer needs annotations, and C++ has more ways to transfer than
  Java.

### A14. Infer Topl (added by the checker)

- Infer's Topl checker takes user-written temporal properties as automata with
  registers. A transition reads
  `sourceState -> targetState: Pattern(Args,Ret) when Condition => Action`
  (https://fbinfer.com/docs/checker-topl, accessed 2026-11-23).
- Status: "C/C++/ObjC: Experimental", activated with `--topl`. It is built on
  Pulse, "which attempts to minimize false positives, at the cost of sometimes
  having false negatives". Analysis time "increases exponentially with the
  number of registers".
- Carrying the habit: a declared protocol checked interprocedurally over
  fields and heap, as a candidate tool to study.
- Costs: Infer is a large external OCaml toolchain with its own clang frontend.
  Using it would be a tool adoption needing operator discussion. No precision
  data for C++ Topl was found.

---

## Part B. Detecting ad-hoc state machines

### B1. Literature

- **Beckman, Kim, Aldrich, "An Empirical Study of Object Protocols in the Wild",
  ECOOP 2011** (`papers/beckman-kim-aldrich-2011-object-protocols-in-the-wild-ecoop.pdf`).
  - **ProtocolFinder.** For every instance method, it flags an `if` whose
    condition reads a receiver field (directly, via a local, or via a getter) and
    one of whose branches throws (§3, pp. 6-7). The flow-sensitive sub-analysis
    tracks field values through locals.
  - **Precision.** On roughly 2 MLOC of Java: **2,920 candidates, 648 confirmed,
    22.2% overall** (JSL 22.8%, PMD 21.9%, Azureus 17.6%, JDT 6.5%; Table 2).
  - **Prevalence.** 7.2% of types define protocols, and 13% of classes are
    clients of one.
  - **Categories** of the 648 (Table 3):

    | Category | Share |
    |---|---|
    | Initialization | 28.1% |
    | Deactivation | 25.8% |
    | Type qualifier | 16.4% |
    | Dynamic preparation | 8.0% |
    | Boundary | 7.9% |
    | Redundant operation | 7.3% |
    | Domain mode | 4.8% |
    | Others | 1.9% |

  - Initialization and deactivation (over 50% together) are the two-state
    lifecycles that Consumed and consuming-`self` typestate fit.
  - A false example: a throw driven by an argument, not the receiver (Fig. 3).
- **Grosche, Igel, Spinczyk, "Transformation- and Pattern-based State Machine
  Mining from Embedded C Code", ICSOFT 2020**
  (`papers/grosche-igel-spinczyk-2020-pattern-state-machine-mining-embedded-c.pdf`, §5).
  - The extraction pattern matches nested-`switch` machines. The precision
    figure below, though, is for a separate, simpler **candidate** pattern used
    to build the ground truth (corrected by the checker, §5):
    - the variable is global or static-local;
    - it is compared with a constant in an `if` or `switch`;
    - at least one constant is assigned to it, directly or indirectly control
      dependent on that comparison.
  - The code was industrial automotive C: 286 handwritten `.c` files, 147,333
    physical lines.
  - Result: **165 state-variable candidates, 100 true state machines after
    manual review (61%)**. The false ones were counters, state "fetched from
    external sources" and pointers to different objects.
  - The ground truth was drawn from the candidates, so recall is not measured.
  - Of the 100, the tool fully extracted 74 and partly extracted 8. 14 were too
    complex to analyze and 4 too large to verify (Table 1).
- **Said, Quante, Koschke, MODELSWARD 2018**
  (`papers/said-2018-interactive-state-machine-mining-modelsward.pdf`): Bosch
  embedded C, concolic testing over state variables. Selecting state variables is
  **interactive**: a person picks the subset. No automatic precision was
  reported.
- **Sunshine, Herbsleb, Aldrich, "Searching the State Space", ICPC 2015**
  (`papers/sunshine-herbsleb-aldrich-2015-searching-state-space-icpc.pdf`): in a
  think-aloud study with six programmers who had at least three years of
  professional Java or C# experience, "82% of the assigned time (or 71% of the
  total time)" went to four kinds of state search (pp. 6-7). It concerns humans,
  not agents.
- **Sunshine, Herbsleb, Aldrich, "Structuring Documentation to Support State
  Search", ECOOP 2014** (added by the checker;
  `papers/sunshine-herbsleb-aldrich-2014-structuring-documentation-state-search-ecoop.pdf`,
  par.nsf.gov purl 10038311).
  - Plaiddoc is Javadoc reorganized by state: methods grouped per state, with
    explicit transitions.
  - Design: 20 participants, between-subjects, 12 of them undergraduates.
  - Result: Plaiddoc participants finished state tasks "in 46% of the time it
    took Javadoc participants", were about equally fast on non-state tasks, and
    were "7.6x less likely to answer questions incorrectly" (§1).
  - Bearing on verbs: a declared table can be rendered per state ("legal here:
    …") in a diagnostic or doc. This is the only controlled evidence that such a
    view helps, and it is human evidence.
- **Coblenz, Aldrich, Myers, Sunshine, "Can Advanced Type Systems Be Usable? An
  Empirical Study of Ownership, Assets, and Typestate in Obsidian", OOPSLA 2020**
  (added by the checker;
  `papers/coblenz-2020-advanced-type-systems-usable-obsidian-oopsla.pdf`, arXiv
  2003.12209).
  - Design: 20 participants, Obsidian (a typestate language) against Solidity.
  - Typestate: in the open-ended Casino task, "All of the participants added
    the dynamic checks" instead of declaring states that would make them
    unnecessary (§10, p. 132:19).
  - Escape hatch: "all of the Obsidian participants who finished the task
    abused the disown keyword, which serves as a caution that escape hatches
    from safety features are easily misused" (§12).
  - Time: Obsidian participants took 64 min on Casino against 37 min for
    Solidity (Table 8; N = 4 and 8).
  - Bearing on verbs: given a choice, people did not reach for typestate
    unprompted, and they routed around a safety feature through its escape
    hatch. A way-past-with-reason mechanism should expect the same and count
    its uses. Agents are unmeasured.
- **Garcia, Tanter, Wolff, Aldrich, "Foundations of Typestate-Oriented
  Programming", TOPLAS 2014**
  (`papers/garcia-2014-foundations-typestate-oriented-programming-toplas.pdf`;
  abstract read). Gradual typestate inserts runtime checks where static checking
  cannot verify. That is the model for "static where possible, a checked boundary
  elsewhere" in C++.
- **Strom and Yemini, IEEE TSE 12(1) 1986** was not obtainable (shopping list).

### B2. Existing lints and analyses

| Tool | Rule | What it catches | Precision evidence |
|---|---|---|---|
| clippy | `struct_excessive_bools` (pedantic, default max 3) | 4+ bools in a struct; message says "consider using a state machine or refactoring bools into two-variant enums" | None measured. Issue #10923 (open, 2023): CLI-argument structs are false. Issue #16409 (open, 2026): settings structs. In dtolnay's crates.io allow census (#7666, 2021) it was suppressed 48 times locally and 21 times globally. My B rule (same threshold) on leveldb and ninja: about 0 of 4 single-machine structs. |
| clippy | `fn_params_excessive_bools` (pedantic) | bool parameters | not about state |
| clippy | `wildcard_enum_match_arm` (restriction), `match_wildcard_for_single_variants` (pedantic) | `_` arms on enum matches | Misses tuple `(state, event)` matches (probe). Allowed 55 local / 20 global (#7666). |
| clang | `-Wswitch` (in `-Wall`), `-Wswitch-enum`, `-Wcovered-switch-default` | unlisted enumerators; `-Wswitch-enum` even with `default:`; a dead `default:` in a covered switch | exact rules, no heuristic. Checker probe on a nested machine switch: §A5b. Build-file mentions in the corpus: 30 / 5 (`-Werror=switch`) / 5 repositories of 1,002 |
| Infer | Topl (`--topl`) | user-declared temporal automata over calls, interprocedural | experimental for C/C++; docs say false negatives are traded for fewer false positives; no numbers (§A14) |
| Checker Framework (Java) | Resource Leak Checker | must-call obligations (accumulation typestate), fields included | 29% precision (49/170), 100% recall on a 15-leak subset (Kellogg et al. 2021; §A13) |
| clang | `-Wconsumed` | §A1 | zero adopters in the corpus |
| clang-tidy | `bugprone-use-after-move` + `InvalidationFunctions` | use after move or after a named invalidating call, on locals | documented conservative cases |
| clang-tidy | `bugprone-unhandled-code-paths` | `if`/`else if` chains without `else`, switches without full coverage | docs say "can be noisy", off by default (`.../bugprone/unhandled-code-paths.rst`) |
| clang-tidy / CodeQL in quarantine | — | **no check detects bool clusters, scattered state writes or repeated state guards** (searched `clang-tools-extra/docs/clang-tidy/checks`, `codeql/cpp/ql/src`) | — |

### B3. Corpus measurements made for this lane

**Lexical scan of the whole archive** (`scratchpad/scan/scan.py`, run with
`python3 -I`):
- It streams every `.tar.gz` in `quarantine/_archives/corpus-2026-10-18/`
  (1,340 tarballs) without extracting.
- It dedupes to 1,002 repositories (largest snapshot per repository) and reads
  887,757 C/C++ files of at most 4 MB.
- These are regexes. They count shapes, not truths.

| Pattern | Hits | Repos | Share |
|---|---|---|---|
| Consumed attributes (`callable_when`, `set_typestate`, …) | 69 | 3 (all are Clang tests or a comment) | 0% |
| `#include <boost/sml.hpp>` or `sml::sm<` | 0 | 0 | 0% |
| `#include <boost/msm/…>` | 633 | 1 (boostorg/msm) | 0% |
| `#include <boost/statechart/…>` | 275 | 3 (statechart, msm docs, Ceph) | 0% |
| TinyFSM / HFSM includes | 0 | 0 | 0% |
| `enum [class] *State/Status/Phase/Mode/Stage` | 21,113 | 459 | 46% |
| `switch ([m_]state/status/phase/stage/mode[_])` | 7,450 | 374 | 37% |
| `[m_]state/status/phase/stage[_] = X;` | 51,252 | 510 | 51% |
| `if (![m_]is_open/initialized/started/… ) return/throw` | 2,990 | 269 | 27% |
| `if ([m_]state/status… != X) return/throw` | 3,434 | 227 | 23% |

**AST-level prototype** (clang-query 23.1.2, matcher text in the appendix).
- Run on leveldb (bb74ef7, 41 TUs; 1 failed on a missing gmock header) and ninja
  (4e29c1c, about 35 TUs). Wall time for leveldb was 6.5 s.
- Field kinds: enum- or bool-typed fields (any access, any object).
- Rules:
  - **SM2**: an enum field written in 3 or more distinct non-constructor
    functions.
  - **SMB**: a bool field written in 3 or more such functions and guarded at
    least once.
  - **G**: an enum or bool field guarded in 2 or more methods by `if (…) return`,
    `if (…) throw` or `assert`, and written outside a constructor.
  - **B**: 4 or more bool fields in one record (clippy's threshold).
- Labels are mine, read from the code.
  - T means the field encodes a lifecycle or mode that gates which operations
    are valid, with transitions in more than one function.
  - N means config, a result code or a cached observation.

| Rule | Field | Label | Why |
|---|---|---|---|
| SM2, G | leveldb `DBIter::direction_` | T | forward/reverse mode, written by 6 methods, asserted |
| SM2 | leveldb `MergingIterator::direction_` | T | same machine shape |
| SMB, G | leveldb `DBIter::valid_` | T | boundary protocol; `assert(valid_)` in `key`, `value`, `Next`, `Prev` |
| G | leveldb `TableBuilder::Rep::closed` | T | deactivation protocol; asserted in 5 methods incl. destructor |
| SMB, G | leveldb `LRUHandle::in_cache` | T | the comment at `util/cache.cc:189-193` describes states over (refs, in_cache) |
| SMB | leveldb `TableBuilder::Rep::pending_index_entry` | debatable | internal sequencing flag with a stated invariant |
| SM2, G | ninja `Edge::mark_` (VisitNone/InStack/Done) | T | written by 3 classes (`Plan`, `DependencyScan`, `State`): state mutated outside its owner |
| SM2 | ninja `Result::status` | N | result code |
| SM2 | ninja `Node::exists_` | N for this habit | cached observation; an optional/sum-type candidate (ADT habit) |
| SM2 | ninja `Jobserver::Config::mode` | N | parsed configuration |
| G | ninja `BuildConfig::verbosity` | N | configuration, written once |
| B | leveldb `VersionEdit` (5 `has_*`) | N for this habit | optional-presence flags (ADT habit) |
| B | leveldb `Options` (4 bools) | N | configuration |
| B | ninja `Edge` (4 bools) | partial | `deps_loaded_`/`deps_missing_` encode one 3-state variable; the others are attributes |
| B | ninja `LinePrinter` (4 bools) | N | 2 config + 2 unrelated state |

**Totals.**

| Rule | True / flagged | Note |
|---|---|---|
| SM2 | 3 / 6 | |
| SMB | 2 / 3 | 1 debatable |
| G | 5 / 6 | |
| B | 0 / 4 | 1 partial |
| SM2 ∪ SMB ∪ G (distinct fields) | 6 / 11 | 7 / 11 if the debatable one counts |

**Known misses.**
- leveldb `BlockBuilder::finished_` is a true Add/Finish protocol. It falls below
  the thresholds (2 writes, 1 assert).
- My first matcher draft excluded public fields and so missed all of ninja's
  public-field machines (`Edge::mark_`).

**Caveats.**
- This is a development sample. Rules were adjusted while looking at it: the
  assert matcher and the public-field fix were added after the first run. Nothing
  here is held out, and one person labeled it.
- clang-query's dynamic matcher language failed silently on
  `qualType(hasCanonicalType(anyOf(enumType(), booleanType())))`. It returned 0
  matches with no error. Adding `isInteger()` "fixed" it but also matched `bool`
  and plain ints. That is a tooling hazard for any matcher-based guard.

---

## Part C. Misuse of an explicit machine: what can be stopped at compile time

| Misuse | C++ (pinned Clang 23.1.2) | Rust 1.99 |
|---|---|---|
| (state, event) pair with no declared handling | **Stop**: an owned consteval totality check over a constexpr table with a generated message (A6). **Stop**: nested enum `switch` with `-Werror=switch`, which names the missing events (A5b). **Stop**: `std::visit`, poor message (A5). SML/MSM/Statechart: runtime only (A3, A4). | **Stop**: E0004 on an exhaustive `match (state, event)` (A8) |
| Catch-all hides future states/events | `default:` in a nested enum switch: **stop** with `-Werror=switch-enum`, but the flag is TU-wide (A5b). Generic `[](auto, auto)` visitor arm: no existing check; needs an owned lint | `_` arm: clippy misses the tuple case (the lint skips non-enum scrutinees); it catches nested matches. Needs an owned lint for the tuple form. |
| Transition target not a declared state | **Stop** by types: an enum or a state type list | **Stop** by types |
| Event type outside the machine's alphabet | **Stop** if `fire<E>` is constrained. SML accepts it silently (A3) | **Stop**: the `Event` enum |
| Unreachable state / no path to final | **Stop**: consteval BFS over the table (A6). MSM checks reachability only (A4) | `typestate` crate checks productive/useful states at macro expansion (A7). Otherwise needs an owned check. |
| State mutated outside the machine | **Stop** by encapsulation: private state, `fire` only. Bypass via `friend`, `const_cast`, a parallel field, or SML's testing policy needs lints. | **Stop** by privacy (module-private field). Bypass by a parallel field. |
| Method called in the wrong state (typestate) | **Stop**: `requires` on the phantom state (A2) | **Stop**: E0599 (A7) |
| Old handle reused after a transition | **Not stopped by the language.** `bugprone-use-after-move` catches reuse through the same local or parameter name, including a local pointer to a heap object. It misses fields, aliases and invalidation inside helpers (A2) | **Stop**: E0382 |
| Object dropped before reaching a final state | No language support. Consumed's destructor `callable_when` covers locals only. This is an accumulation property, checkable without alias analysis (A13), but no C++ tool does it. | No language support (affine). `#[must_use]` catches only a discarded temporary. Same accumulation note. |
| Two-state lifecycle on members, heap or pointers | Not stopped by Consumed or use-after-move. Needs an owned check or a design that keeps such objects local. | Ownership handles it when the protocol is encoded as typestate. A runtime flag otherwise. |
| Guarded row: which branch fires | Runtime only. The trace check (A12) observes it. | Runtime only. Same. |

---

## Part D. Seeded-fault testing for this habit

What exists:
- **Mull** (`quarantine/mull`) mutators are behavior-level:
  - `cxx_remove_void_call` deletes a `close()` call, which produces a protocol
    violation;
  - `negate_mutator` and `cxx_eq_to_ne`/`cxx_ne_to_eq` flip a state guard;
  - all listed in `docs/generated/Mutators.rst`.
- These test the code's tests, not a habit's guards.

Habit seeds are source edits whose expected verdict is known in advance. From
this lane's misuse table:
- **For constructs:**
  - delete a table row (expect a totality stop);
  - duplicate a row (expect a stop);
  - retarget a row to an undeclared state (expect a stop);
  - add a `_` or `auto` catch-all (expect a bypass finding);
  - add a direct write to the machine's state outside `fire` (expect a stop or a
    bypass finding);
  - reuse a moved typestate handle (C++: expect a use-after-move-class finding;
    Rust: E0382).
- **For nudges on ad-hoc code:**
  - insert a new method that writes an existing state field;
  - insert an `if (!open_) return;` guard;
  - add a fourth bool flag that moves with the others.
  - Measured false findings are the nudges on unseeded code.

The corpus barely contains explicit machines (B3). So testing the construct's
stops on "real corpora" first requires migrating ad-hoc machines to the
construct. That is the same dependency the scrapped enum migration had
(`WORK.md`, verbs-2or). Ceph's Statechart code is the one large explicit machine
in the corpus.

The A12 trace check is also a fault oracle: a seeded behavioral fault in a
migrated machine shows up as a trace record outside the table.

---

## What this means for verbs

These are the options this lane opens, ranked.

1. **Rust: the language's own machine, plus one owned lint.**
   - Construct: `enum State` (state data inside variants) and an exhaustive
     `match (state, event)` step function. Use consuming-`self` typestate where
     the protocol is linear (builders, handles).
   - Stops are native: E0004, E0599, E0382.
   - The missing piece is small and measured: a lint against a wildcard or
     catch-all arm in a machine's step match, which clippy's
     `wildcard_enum_match_arm` misses.
   - Way past: `#[expect(…, reason)]` with stale detection, verified.
   - Reasons: strongest guarantees for the least owned machinery, and
     diagnostics are already good.
2. **C++: an owned table-as-data machine with consteval checks.**
   - A6 shows the pinned compiler can stop "no row for (state, event)",
     duplicate rows and unreachable states, with a message that names the pairs.
   - Encapsulated state removes "mutated outside the machine" by construction.
   - Bypass guards needed: a direct or parallel state write, a catch-all visitor,
     `friend`/`const_cast` into the machine.
   - The same table feeds the trace check (option 5) and diagrams.
   - Reasons:
     - library alternatives check none of this at compile time;
     - their adoption is zero in the corpus;
     - adopting one needs operator discussion;
     - the owned construct is small.
   - Cost: enumerator names for messages need macros until reflection is on the
     pinned toolchain.
   - Checker note: a nested enum `switch` step function under
     `-Werror=switch -Werror=switch-enum` (A5b) already stops missing pairs and
     `default:` catch-alls, and names the missing enumerators with no owned
     code. It is a zero-machinery floor beneath this option. It does not check
     duplicates, reachability or outside writes, and `-Wswitch-enum` needs
     scoping to machine functions.
3. **C++ typestate for linear protocols, with an owned use-after-transition
   check.**
   - Phantom-state types give wrong-state stops.
   - The reuse gap is closed for locals by `bugprone-use-after-move`-style
     analysis, which already accepts named invalidating functions.
   - Fields and aliases stay unchecked. A heap object held in one local pointer
     is checked (checker probe, A2). The habit text must say so, or the
     construct must keep such objects local.
   - For the must-finish half of a linear protocol, an owned accumulation check
     (A13) could reach fields without alias analysis. Its published precision
     (29%, Java) makes it a nudge, not a stop.
   - Prefer this over Consumed (A1): Consumed misses members and pointers, has 3
     fixed states, warns on every non-const reference pass, and is unmaintained.
4. **Nudges for ad-hoc machines, never stops.**
   - The best observed signal is the G rule (an enum or bool field guarded in 2 or
     more methods and written outside the constructor), the Beckman pattern
     extended to asserts.
   - Write-scatter on enum fields (SM2) is next. Bool-count alone (clippy's rule)
     is the weakest here, because config and optional-presence structs dominate.
   - Published precision (22%, 61%) and this lane's 55% union say these must ask
     for a reason, not block.
   - Keep the field-type and naming boundary with the ADT habit explicit:
     `exists_` and `has_*` belong there.
5. **Trace check against the declared table.**
   - The machine's `fire` (or SML's logger, or statig's `after_dispatch`) emits
     `(from, event, to)`. A test asserts each record is a declared row.
   - No TLA+ needed for finite machines. It covers guards and back doors that
     compile-time checks cannot.
   - It also serves as a seeded-fault oracle.
6. **Not recommended now.**
   - Adopting Boost.SML or MSM (runtime unhandled events, library adoption).
   - Session types (narrow habit, dormant libraries, no C++ library).
   - A Static Analyzer typestate checker (slow, version-coupled), unless members
     and heap protocols become a demanded case.

## Open questions

1. How does a table declare "ignore" versus "illegal" for a pair, and what does
   `fire` do at run time on an illegal pair? Options: return an error, abort, or
   leave it to the habit's policy. Is that a stop at the definition, the call
   site, or both?
2. Guards: does a guarded row have to name its fallback row, so that totality
   holds "modulo guards"? Or are guards out of the table and inside actions?
3. Hierarchical and orthogonal machines: in scope for the first habit, or a later
   habit? Every library treats them as the hard part. MSM's orthogonality check
   and statig's superstates show the shapes.
4. C++ typestate on members and heap objects: give up and document it, or own an
   analysis? Consumed and use-after-move both stop at locals.
5. Where does this habit end and the ADT/sum-type habit begin? `Node::exists_`,
   the `VersionEdit::has_*` flags and `deps_loaded_`/`deps_missing_` straddle
   both. Nudges from two habits on one field need one owner.
6. Ad-hoc detection identity and thresholds:
   - Which signals combine?
   - What is a held-out corpus and who labels it?
   - The enum lane found independent model labels at chance
     (`papers/2026-10-17-enum-candidate-redesign.md`, verdict 3).
7. Enumerator names in C++ diagnostics without reflection: a macro-declared enum
   (like the scrapped `VERBS_ENUM`), magic_enum-style scanning, or waiting for
   P2996 on the pinned toolchain?
8. Rust lint delivery: a Dylint, a custom rustc driver, or clippy-adjacent?
   Shared with other Rust lanes.
9. Seeding on real corpora requires migrated machines first. Which corpus
   projects get migrated, and is Ceph's Statechart code (the only explicit
   machine found) a target or out of scope?
10. Agent ergonomics are unmeasured. Do agents keep a table total when adding a
    state, or reach for the catch-all? This needs a measurement before the nudge
    and stop wording is fixed. The human evidence (Coblenz et al. 2020) predicts
    dynamic checks and escape-hatch misuse.
11. (Checker) For C++, is the stop a native compiler flag (`-Werror=switch-enum`
    over nested switches, scoped how?), the owned consteval table, or both? The
    two give different diagnostics. The flag names events. The table can name
    (state, event) pairs but needs enumerator names.
12. (Checker) Should "must reach a final state before destruction" be split out
    as an accumulation property and checked separately from "no call after
    the final state"? Only the first can follow fields without alias analysis
    (A13).
13. (Checker) Should verbs count way-past-with-reason uses per habit and site,
    given that Obsidian participants misused the escape hatch?

---

## Appendix 1. clang-query matcher text used in B3

```
set output diag
set bind-root false
let stfield fieldDecl(anyOf(hasType(enumDecl()), hasType(booleanType()))).bind("f")
m binaryOperator(isAssignmentOperator(), hasLHS(ignoringParenImpCasts(memberExpr(member(stfield)))), forFunction(functionDecl(unless(cxxConstructorDecl())).bind("wfn")))
m ifStmt(hasCondition(hasDescendant(memberExpr(member(stfield)))), hasThen(anyOf(returnStmt(), cxxThrowExpr(), compoundStmt(statementCountIs(1), has(returnStmt())), compoundStmt(has(cxxThrowExpr())), compoundStmt(has(exprWithCleanups(has(cxxThrowExpr())))))), forFunction(cxxMethodDecl().bind("gfn")))
m switchStmt(hasCondition(hasDescendant(memberExpr(member(stfield)))), forFunction(functionDecl().bind("sfn")))
m fieldDecl(hasType(qualType(hasCanonicalType(booleanType()))), hasParent(cxxRecordDecl(isDefinition()).bind("brec"))).bind("bf")
m conditionalOperator(hasTrueExpression(ignoringParenImpCasts(callExpr(callee(functionDecl(hasAnyName("__assert_rtn", "__assert_fail", "_wassert")))))), hasCondition(hasDescendant(memberExpr(member(stfield)))), forFunction(cxxMethodDecl(unless(cxxConstructorDecl())).bind("afn")))
```

**Flags.**
- leveldb: `-std=c++17 -I. -Iinclude -DLEVELDB_PLATFORM_POSIX=1`, with a stub
  `port/port_config.h`.
- ninja: `-std=c++17 -Isrc`.

**Output handling.** clang-query prints matches grouped per matcher across all
TUs, each group ending "N matches.". The aggregator dedupes by source location.

## Appendix 2. Sources

**Reference implementations in quarantine** (versions per
`quarantine-manifest.md`):
- llvm-project 23.1.2 (`Consumed.cpp`, `Attr.td`, `DiagnosticSemaKinds.td`,
  `AnalysisBasedWarnings.cpp`, `AttrDocs.td`, `FuchsiaHandleChecker.cpp`,
  clang-tidy `use-after-move.rst`, `ReleaseNotes.rst`)
- sml bc13fcbb
- msm f2d60cb
- etcd-raft 638f427
- trace_validation_tools 7b31b03
- mull (`docs/generated/Mutators.rst`)

**Web, all accessed 2026-11-23:**
- crates.io API `https://crates.io/api/v1/crates/<name>` for the crates in A9
  and A10.
- GitHub API for repository stars and push dates (A4), the clippy issue search
  (#10923, #16409, #7666) and the Consumed.cpp commit history.
- READMEs via `raw.githubusercontent.com` for statig, rust-fsm, smlang,
  typestate-rs, sm, finny.rs and ProtEnc.
- Beckman et al. via figshare (KiltHub article 6621044).
- Garcia et al. via figshare (KiltHub article 6605861).
- Sunshine et al. via https://par.nsf.gov/servlets/purl/10038376.
- Said et al. and Grosche et al. via scitepress.org.
- Alsubhi and Dardha via https://www.dcs.gla.ac.uk/~ornela/publications/AD24.pdf
  and AD22.pdf.
- Kokke via https://arxiv.org/pdf/1909.05970.
- Duarte and Ravara via https://raw.githubusercontent.com/rustype/typestate-rs/HEAD/articles/sblp21.pdf.

**PDFs added to papers/ (SHA-256, bytes):**

| File | SHA-256 | Bytes |
|---|---|---|
| `beckman-kim-aldrich-2011-object-protocols-in-the-wild-ecoop.pdf` | b1cab9aa39881111b4bb743ddc2d823e53c3fde466574de932a245722049702d | 568242 |
| `garcia-2014-foundations-typestate-oriented-programming-toplas.pdf` | ed84f1c05edb1617dc51d4c69047deac8ad9f6f9d081398f8813e71b510b140b | 673652 |
| `sunshine-herbsleb-aldrich-2015-searching-state-space-icpc.pdf` | 10803033a5513834788a9c12eaabb5ccbc30a5b1e0c06656e24c02f6b1dd1647 | 349747 |
| `said-2018-interactive-state-machine-mining-modelsward.pdf` | e471a34863b8f34532be82d22eaeadb571120f77f36360bd6284d523dc778d23 | 396165 |
| `grosche-igel-spinczyk-2020-pattern-state-machine-mining-embedded-c.pdf` | 89940d56d7fcec74786aba896c0902933078f8e7bc189ee663e38612305e2bae | 814905 |
| `duarte-ravara-2021-retrofitting-typestates-rust-sblp.pdf` | 241119568a48c8bfad23ead80853b83ba23835d973a123382b8588e5e24bf566 | 373531 |
| `kokke-2019-rusty-variation-session-types-rust-ice.pdf` | 4a9f9a8dd8527bb086300c022747f6755421cde3be140b4d2ece70efa57b895b | 177565 |
| `alsubhi-dardha-2022-cpp-typestates-library.pdf` | 24abb29a94562300f35922f2dfca877507468067e876e52fe799edae613dcb73 | 206239 |
| `alsubhi-dardha-2024-coconut-cpp-typestate.pdf` | 27ae496f0f9f7f75a51de49085facd37fd63705075cdeafb604cf22a04fb7caf | 3248032 |

**Read depth.**
- Core: Beckman §3, Grosche §5, Kokke §2.3, Duarte §3-4.
- Abstract and evaluation: Sunshine, Said, Coconut.
- Abstract only: Garcia, Alsubhi and Dardha 2022.

---

## Check (2026-11-23)

Second-pass check of this report. Probes were re-run on the same toolchains:
clang 23.1.2 at `/opt/homebrew/Cellar/llvm/23.1.2`, and rustc/clippy 1.99.0
via `+1.99.0`. Checker probe sources are in the session scratchpad under
`chk/`.

### Verified (opened the source or re-ran the probe)

- **Consumed.cpp citations**, llvm-project 23.1.2:
  - `isConsumableType` (`:140-147`);
  - the argument-state rules (`:636-647`);
  - `getDirectCallee` only (`:734-735`);
  - `std::move` (`:740-742`);
  - default constructor → consumed (`:777-779`);
  - `VisitDeclRefExpr` VarDecl only (`:825-828`);
  - `intersect` and the loop-mismatch warning (`:1125-1160`);
  - the file-head TODOs and the "(Deferred)" TODO at `:1372-1373`.
- **Related Clang sources:**
  - `Attr.td` three fixed states and the two undocumented attributes;
  - 8 `DefaultIgnore` diagnostics in `DiagnosticSemaKinds.td:4505-4529`;
  - `Consumed` group defined alone (`DiagnosticGroups.td:1513`) and in no
    umbrella group;
  - Sema hook (`AnalysisBasedWarnings.cpp:3182-3187`);
  - the two `#if 0` FIXME tests (`warn-consumed-analysis.cpp:279-280`,
    `:385-386`);
  - `[[clang::suppress]]` not applying to ordinary warnings
    (`AttrDocs.td:6635-6643`);
  - 93 upstream commits (GitHub API).
- **Consumed probe re-run:** identical 8 warnings and the same misses (member,
  pointer alias, lambda, heap).
- **Boost.SML:**
  - `sml.hpp` is 3,693 lines with no `#include`;
  - both `process_event` overloads, the second wrapping `unexpected_event`
    (`:2493-2500`);
  - logger hooks (`:1835-1893`, call sites from `:2169`);
  - testing-policy `set_current_states` (`:2567-2580`);
  - `plant_uml.cpp` reads `T::src_state`/`T::dst_state` (`:282-291`);
  - `WILL_FAIL` compile-fail tests;
  - probe re-run prints `0 0 0 open=1`.
- **MSM:**
  - `no_transition` → `BOOST_ASSERT(false)` (`state_machine_def.hpp:207-212`);
  - `mpl_graph_fsm_check.hpp` (48 lines; orthogonality and unreachable states
    only);
  - backmp11 benchmark numbers: back 10 s / 844 MB, backmp11 2 s / 236 MB, SML
    4 s / 254 MB and 13 s / 612 MB hierarchical.
- **clang-tidy `bugprone-use-after-move`:**
  - `use-after-move.rst:53-66` (flow-sensitive, not path-sensitive) and
    `:265-281` (`InvalidationFunctions`);
  - the ReleaseNotes entry;
  - probe re-run: the invalidated-by-'close' message on a local, and the
    member-field miss.
- **Rust probe** re-run under clippy 0.1.99 and 0.1.94: no
  `wildcard_enum_match_arm` on the tuple match (`lib.rs:27`); fires at `:42` and
  twice at `:43`; `match_same_arms` at `:23`; `struct_excessive_bools` at `:32`;
  unfulfilled `#[expect]` at `:40`; `#[must_use]` warning at `:47`.
- **Corpus scan:** recomputed from `scratchpad/scan/out.tsv`. 1,002 repositories,
  887,757 files, and every count and percentage in the §B3 table match. The
  Consumed hits are LLVM tests, filament's vendored DXC clang tests and one
  mediapipe comment. Statechart's three repositories are statechart, msm and
  ceph (including crimson).
- **leveldb** (corpus bb74ef7):
  - `db/builder.cc:31`, `db/db_impl.cc:83`, `:826`;
  - `TableBuilder::Rep::closed` asserted at `table_builder.cc:73` (destructor),
    `:96`, `:127`, `:216`, `:272`;
  - the `util/cache.cc:189-193` comment.
- **Papers:**
  - Beckman Table 2: 2,920 candidates, 648 evidence, 22.2% overall; JSL 22.8%,
    PMD 21.9%, Azureus 17.6%, JDT 6.5%. JSL is 2,690 of the 2,920, so the
    overall figure is mostly JSL. Table 3 categories; 7.2% / 13%.
  - Grosche 165/100/74/8.
  - Sunshine 2015 "82% … (or 71% …)".
  - Kokke §2.3 "trickier, as Rust's type system doesn't help us here".
  - Duarte "Non-useful state" message.
  - Coconut 2024 static_assert / runtime-assert split and the "higher
    compile-time overhead".
- **etcd-raft:**
  - `with_tla` build tag (`state_trace.go:15`);
  - trace call sites (`raft.go:469`, `:776`, `:899`, `:914`, `:960`);
  - `TracingEvent` (`state_trace.go:83-93`);
  - `tla/Traceetcdraft.tla`.
- **trace_validation_tools:** template and script paths.
- **FuchsiaHandleChecker:** header state diagram and `acquire_handle` /
  `use_handle` / `release_handle` (`Attr.td:4958-4975`).
- **Clippy issues:** #10923 (open, 2023-06-11), #16409 (open, 2026-01-16), and
  #7666 counts (`struct_excessive_bools` 48 local / 21 global,
  `wildcard_enum_match_arm` 55 / 20).
- **crates.io:** statig, rust-fsm, smlang, sm and typestate figures (crates.io
  API).
- **READMEs:** statig `_ => Super` and `before_dispatch`/`after_dispatch`
  (`:253-254`); rust-fsm `consume` (`:100-110`); smlang first-enabled-guard
  rule (`:139-142`).

### Corrected (old → new, with source)

1. **Consumed and references.** Old: "It tracks only local variables and
   temporaries"; "pointers and references are excluded". New: reference
   *parameters* are tracked as `VarDecl`s. `T&` starts `unknown`, `T&&` starts
   the class default, and `param_typestate` sets either (`Consumed.cpp:850-866`).
   Consequence, by checker probe: every `callable_when("unconsumed")` call on an
   unannotated `T&` parameter warns "unknown". This second false-finding source
   sits in the callee. `param_typestate` also gives a caller-side check
   ("argument not in expected state"). Pointers remain untracked. (§A1.)
2. **Consumed maintenance.** Old: "only crash fixes and NFC changes since
   2013". New: since 2014, refactors, NFC and crash fixes plus two behavior
   changes: by-value class arguments consume (2019-09-19) and consteval
   conditions are skipped (#117403, 2024-11-27). Source: GitHub commits API for
   `clang/lib/Analysis/Consumed.cpp`. (Headline 2, §A1.)
3. **use-after-move scope.** Old: "catches locals only, not fields". New: it is
   keyed by variable name.
   - Caught: local, pointer-parameter, reference-parameter, and
     local-pointer-to-heap cases.
   - Missed: aliases (`q = p`), invalidation inside a helper, and members.
   - Source: checker probes `uam.cpp` and `uam2.cpp` under clang-tidy 23.1.2.
   (§A2, Part C, option 3.)
4. **Grosche et al.** Old: "The pattern is a `switch` on a variable whose case
   bodies assign constants to the same variable", with 100/165 credited to "the
   switch-pattern miner". New: 100/165 is the precision of the simpler
   ground-truth candidate pattern: a global or static-local variable compared
   with a constant in an `if` or `switch`, with a control-dependent constant
   assignment. The ground truth was drawn from those candidates, so recall is
   unmeasured. Corpus: 286 files, 147,333 LOC. Source: Grosche et al. §5,
   p. 113 and Table 1. (Headline 6, §B1.)
5. **Rust typestate adoption.** Old: "The crates that stop at compile time are
   the typestate ones, with low recent use." New: true among FSM crates, but
   the typestate builder crates typed-builder (125.1M downloads) and bon (81.8M)
   check at compile time and are among the most-used derive crates. Source:
   crates.io API and each README, 2026-11-23. (§A9.)
6. **Sunshine 2015 sample.** Added the sample size, 6 programmers (§V-A3), to
   the 71% claim.
7. **Toolchain note.** The lane's Rust probe sits in the scratchpad, outside
   the verbs repository. There `cargo` resolves to the default stable 1.94.1,
   not the 1.99.0 pinned by `verbs/rust-toolchain.toml`. Results are the same
   on both, so no finding changes.

### Added (within the brief)

- **§A5b, native C++ totality.** Nested enum `switch` under
  `-Wswitch`/`-Wswitch-enum`/`-Wcovered-switch-default`: probe, diagnostics
  with enumerator names, limits, and build-file adoption across the corpus.
  `-Wswitch-enum` is in 30 of 1,002 repositories, `-Werror=switch` in 5,
  `-Wconsumed` in 0. Scan: `scratchpad/chk/scan2/scan2.py`, `python3 -I`, 52 s.
  - Same scan, FSM libraries: `QStateMachine`/`QScxmlStateMachine` in 2
    repositories (boostorg/build, renderdoc).
  - `etl::fsm` and any `sml.hpp` include: 0.
- **Clippy root cause.** `match_wild_enum.rs` returns early for non-enum
  scrutinees (rust-clippy 15d082bb). Related open issue #17291. Closed request
  #12465 was answered by pointing to the existing lint. Nested matches are
  covered today. (§A8.)
- **§A13, accumulation typestate.** Kellogg et al. ECOOP 2022 and the Resource
  Leak Checker (FSE 2021).
  - Which protocol properties can be checked without alias analysis (41% of
    surveyed specs).
  - Measured precision of a sound must-call checker: 29%, with 100% recall on a
    15-leak subset, against Eclipse 25% / 13% and Grapple 50% / 7%.
  - Annotation burden of 1 per 1,500 LoC.
  - The finish-versus-use split applied to leveldb `TableBuilder`.
- **§A14, Infer Topl.** User-declared protocol automata, experimental for
  C/C++.
- **§A4, Coconut v2** (SCP 2026). It moved from templates to a GCC GIMPLE
  plugin because of compile time and scalability, so it is unusable under
  pinned Clang. Also Statechart's `unconsumed_event` default ("Effects: None"),
  verified from its reference docs.
- **§B1, ergonomics.**
  - Sunshine et al. ECOOP 2014: state-organized docs cut state-task time to 46%
    and errors 7.6×; n = 20.
  - Coblenz et al. OOPSLA 2020: all Casino participants chose dynamic state
    checks over typestate; all finishers misused the `disown` escape hatch;
    64 vs 37 min.
  - These replace "the only ergonomics evidence found".
- **Ranked options and open questions:** notes added to options 2 and 3; open
  questions 11-13 added.

### Papers added by the checker (papers/, gitignored)

| File | SHA-256 | Bytes | Source (accessed 2026-11-23) |
|---|---|---|---|
| `coblenz-2020-advanced-type-systems-usable-obsidian-oopsla.pdf` | 485c9e0c4d7db9155b5fc63dcb4c25d25f47c24aeb2cf2d69927b19112b91d06 | 1226117 | https://arxiv.org/pdf/2003.12209 |
| `kellogg-2021-resource-leak-verification-fse.pdf` | f1e1b81e95c671dbc315d2f1ab2dc59aab5aee88fa92c2719bf0a57c6cc4f06e | 684486 | https://homes.cs.washington.edu/~mernst/pubs/resource-leak-esecfse2021.pdf |
| `kellogg-2022-accumulation-analysis-ecoop.pdf` | 4a7cea500b8358aa5710c529d48c7942207bc5d5038418b4962ed61f8d5da92b | 998986 | https://homes.cs.washington.edu/~mernst/pubs/accumulation-analysis-ecoop2022.pdf |
| `sunshine-herbsleb-aldrich-2014-structuring-documentation-state-search-ecoop.pdf` | d0095c5a4b0dd34948b8f4c936913558dd2cb09b6517ac20058ce27ad44ef718 | 374318 | https://par.nsf.gov/servlets/purl/10038311 |
| `alsubhi-dardha-gay-2026-coconut-design-evaluation-scp.pdf` | 21d36c1820e8b89257476f547d4fcb7e5e9f81fb67423cf99cc8fdc48178e6fa | 2758541 | https://www.dcs.gla.ac.uk/~ornela/publications/ADG26.pdf |

### Still open after the check

- Strom and Yemini 1986: no free copy found (one search lead returned
  nothing).
- Bierhoff and Aldrich 2007 (Plural): not obtained.
- Infer Topl was not run. Its C++ precision is unknown.
- The resource-leak precision figures are for Java. No C++ or Rust measurement
  of an accumulation check exists.
- The lane's clang-query labels in §B3 were not re-labelled independently. They
  remain a single-labeller development sample.
