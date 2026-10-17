# Tribunal: the checks and the `verbs check` pipeline

Date: 2026-10-17. Spec under review: design/SPEC.md at d03a6fe (sections
§2.3, §4, §5, §6, §9.2-§9.4). Lens: the escape check, the enum-candidate
check, affected-unit tracking, stable keys and deltas, incremental equals
from-scratch, and per-edit latency.

Nothing was written into blackbird or BRepGPU. Neither was built. All probe
code and output lived in the session scratchpad.

## What was measured

**Enum-candidate probe.** A throwaway LibTooling visitor, about 400 lines,
linked against Homebrew LLVM 23.1.2. For every integer and string
declaration (field, global, local, parameter) it emitted the §5 evidence:
- `==`/`!=`/`case` against literals;
- literal assignments, initializers and call arguments;
- the disqualifiers;
- every use that is neither counted nor disqualifying.

It ran over all 257 blackbird TUs (`build/debug`), and a Python script
applied the §5 rule. For BRepGPU, which has no compilation database, it ran
on 156 of 187 `native/` and `tests/` sources. Those sources were parsed with
`-std=c++20 -Iinclude -Inative -Inative/mesher`. The mesher needs C++20
(`std::span`, `operator<=>`). The other 31 sources need Linux, OCCT or
Parasolid headers.

The probe's approximations:
- It does not detect non-const reference binding.
- It flags serialization by callee name only.
- It skips template instantiations.
- It treats every std-library callee except operators as "outside the
  analyzed code".

It is an estimate of the rule's behaviour, not of a finished verbs.

**Latency.** These ran on blackbird, with host load average 88-97
throughout (other work on the machine). Wall times are therefore inflated.
CPU seconds are the usable figures.
- `clang-scan-deps -j 16`: include sets for all 257 TUs.
- `clang++ -fsyntax-only`: every TU, 16 at a time.
- The probe itself, which approximates extraction cost.

## Findings, ranked

### B1. Blocker: `verbs check` trusts `--changed` as the complete change set (§6.1, §6.2, §9.4)

The pipeline re-extracts only the changed paths and their recorded includers.
These changes never reach `--changed`:
- edits through Blackbird's shell tool (`sed -i`, scripts, formatters);
- `git checkout`, `stash`, `rebase` and `pull`;
- headers the build regenerates;
- `cmake` rewriting `compile_commands.json`;
- other agents working in the same tree.

Each one leaves stale facts. Two consequences:
1. §9.4's "after any sequence of edits" property is false by construction.
2. The escape check has a silencing channel. An agent that writes
   `const_cast<...>` with `sed -i` through the shell tool gets no `+ escape`
   line, ever. The stale facts keep reporting `holds` until a full
   `verbs scan`.

The spec cites build-systems theory (core literature §9: verifying traces)
but then doesn't use it.

**Fix.** Make `--changed` a scheduling hint, not the authority:
- Per unit, record the compile-command hash and every input file with its
  size, mtime and content hash. Record the negative probes too (B1 and M7
  share this record).
- On every check, stat every recorded input. Blackbird's 257 TUs touch
  1,641 unique files, so this costs milliseconds.
- Re-extract every unit whose trace mismatches.

### B2. Blocker: the observed literal set is an under-approximation, and the suggested `to_enum` turns it into a behaviour change (§5)

§5 gathers literals per declaration and suggests `verbs::to_enum` "at the
ingress sites it found". When values arrive from a non-literal source, the
literal set is only a lower bound on the domain. The suggested encoding then
rejects valid inputs.

Corpus examples, both produced by the probe as findings under every reading
of §5:
- `blackbird::(anonymous)::Node::kind` (`src/token_usage.cpp:62`).
  - Observed values {0, 3, 12}, in three functions, with no disqualifier.
  - It is written from the wire at `:346`
    (`node.kind = input.get<std::uint8_t>()`).
  - The documented domain is 1..14 (`src/provider_original.cpp:443`). 0 is
    the "unset" initializer.
  - `to_enum` at `:346` with {0, 3, 12} rejects 11 valid kinds.
- `Node::site` (`:61`).
  - Observed values {0, 1300, 1320, 3600}.
  - It is assigned from the local `site` (`:340`). That local is compared
    against about 25 site codes in `record()` (`:344-519`).
  - The field never sees those literals.
- The setter pattern has the same shape:
  `void set_mode(int m) { mode_ = m; }` called as `set_mode(4)`. `mode_`
  never sees 4.

An agent acts on what it is shown (§4's own premise). These findings produce
wrong edits, and no threshold separates them from true ones.

**Fix.**
1. Merge literal sets along copy edges inside the analyzed code: assignment,
   initialization and argument passing from one subject into another.
2. When any ingress comes from outside the analyzed code (deserialization,
   an unanalyzed callee's return), show the subject at the edit boundary only
   if the code already rejects values outside the set at that ingress (an
   `else`/`default` that errors). Otherwise it is a hypothesis
   (`verbs scan --hypotheses`).
3. A default-initializer value, or a moved-from reset value, is marked as a
   sentinel rather than counted as a domain member.

### B3. Blocker: `holds` claims fall to ordinary code that matches nothing in §4's list (§4, with §3.2 and §3.4)

§4 enumerates constructs. Each of the following violates a `holds` claim and
produces no escape finding. The first four were compiled and run with
Homebrew clang 23.1.2 `-std=c++2c -Wall -Wextra`, with no warnings.

1. **Shallow const in `Refined`.** This is the spec's own §2.1 example, "a
   non-empty, sorted span". `get()` returns `const std::span<int>&`, and
   `r.get()[0] = 42` compiles and writes through it, because span's
   `operator[]` is const and returns `int&`. The owner of the underlying
   vector can also write to it directly. Neither involves a cast. A
   `const_cast` on `r.get()` also escapes §4's filter, because the cast's
   operand type is `T`, not a vlib type.
2. **`Mode m{7};` and `Mode{9}`.** Direct-list-initialization of a scoped
   enum with a fixed underlying type is legal since C++17. The AST holds only
   an `InitListExpr` with an implicit `IntegralCast`, and no cast node.
3. **Implicit conversion to `void*`.**
   - `void* p = &b; *static_cast<std::int8_t*>(p) = 99;` uses
     `static_cast`, which is not in the list.
   - `fread(&b, sizeof b, 1, f)`, `::read(fd, &b, n)` and
     `new (&b) std::int8_t(99)` involve no cast at all.
4. **Explicit-instantiation access.** `template struct Rob<&B::v_>;` with a
   friend-injected accessor wrote 99 into a `Bounded<0, 5>` through a
   pointer to member. Explicit instantiation is exempt from access checking.
5. **User specializations.** User code can declare
   `template <> class verbs::Bounded<0, 5> { public: std::int8_t v_; };`, or
   specialize `verbs::enum_traits<Mode>` to lie about the domain.
6. **`#define private public`** before including vlib.
7. **Undefined behaviour.** An out-of-bounds write that lands in a
   `Bounded`. §2.3 does not list "no undefined behaviour" among the
   assumptions.

**Fix.**
- §3.2: `Refined<T, Pred>` requires `T` to be deep-const. Reject pointer,
  span, reference_wrapper and view types, and types with mutable or pointer
  members.
- §4: define an escape by effect, then enumerate it as a closed construct
  list that §9.2 tests clause by clause. The effect: "an expression that
  writes vlib-owned storage, or yields a vlib value or a verbs-domain enum
  value, other than through vlib's own operations". The list adds:
  - any implicit or explicit conversion of a pointer to vlib storage into a
    non-const `void*`, `char*`, `unsigned char*` or `std::byte*`;
  - brace-initialization of a verbs-domain enum from an integer;
  - user-written specializations and explicit instantiations naming a
    `verbs::` template or its members;
  - macro definitions of `private`, `protected` and `class`;
  - `std::start_lifetime_as` and `std::construct_at` over vlib storage.
- §2.3: add "the program has no undefined behaviour".

### M1. Major: the escape check as written flags vlib's own API and read-only uses (§4)

These are false findings under the literal text:
- **Unions.** `Bounded::make` returns `std::optional<Bounded>`. libc++
  stores the value in a union (`libcxx/include/optional:378-381`), so that
  is "a union member of vlib type" on every use of `make`. The same holds
  for `std::expected<Refined, ...>` (§3.2) and `std::variant`.
- **`memcpy` into vlib objects.** `std::vector<Bounded<...>>` relocation
  calls `__builtin_memcpy(static_cast<void*>(...))` writing into vlib
  objects (`libcxx/include/__memory/uninitialized_algorithms.h:428`). So does
  `std::copy`, lowered to `__constexpr_memmove`
  (`__algorithm/copy_move_common.h:61`).
- **Reads.** "Source or target involves a vlib type" flags reads:
  - `(void)b;`, a C-style cast used to silence unused warnings;
  - `(int)mode`;
  - `std::bit_cast<std::uint8_t>(mode)`;
  - `reinterpret_cast<const char*>(&s)` in generic hashing or
    serialization of trivially copyable types.

The obvious repair is to skip system headers by Clang's system flag. That
opens a silencing channel (see M2).

**Fix.** Judge writes and value creation, not mentions:
- A copy whose source is an object of the same vlib type is not an escape.
- A cast to a `const` byte view, or to a non-vlib value type, is a read and
  not an escape.
- Decide whether a file is outside verbs' scope by verbs' own path rule
  (outside the repository root), never by `SrcMgr::C_System`.

### M2. Major: silencing gaps (§4 "Silencing", §6.4)

Missed:
- bare `// NOLINT`, `NOLINTNEXTLINE` and `NOLINTBEGIN` without a check list,
  or with a glob;
- `#pragma GCC diagnostic ignored "-Wswitch-enum"`, which Clang honours;
- `_Pragma("clang diagnostic ...")` inside macros;
- `#pragma clang system_header`, which also hides the file from any
  system-header filter;
- moving an include directory from `-I` to `-isystem`;
- removing `-Werror=switch-enum`, or adding `-Wno-switch-enum`, in
  CMakeLists. This is a compile-database change, not "verbs configuration";
- `__builtin_assume`, and `if (!c) __builtin_unreachable();`;
- **weakening a vlib type to a raw integer.** The agent-feedback lane lists
  it as a gaming move (`papers/2026-10-17-literature-agent-feedback.md`,
  daemon section). The delta compares findings, so a `holds` claim that
  silently disappears prints nothing.

The spec is also internally inconsistent. If verbs honours `NOLINT` at all,
that contradicts §1/§7: decisions are the only annotation. If it doesn't,
the `NOLINT` item is noise.

**Fix.**
- verbs honours no suppression comment; only decisions silence it.
- List the pragma and flag forms above.
- Diff compile flags per unit (M7).
- Print a `!` line whenever a `holds` claim present in the previous report
  is absent from the new one.

### M3. Major: the §9.3 escape gate is vacuous, and the escape check has no completeness oracle (§9.2, §9.3)

Neither blackbird nor BRepGPU uses vlib, so the escape check emits zero
findings on both, and "100% true" is a statement about zero findings.

§3.4's reflection path ("a plain enum class is enough") also leaves "verbs-
domain enum" undefined. If every `enum class` counts, blackbird has 27
integer-to-enum `static_cast`s, most of them hand-guarded, that become
findings on day one.
Examples: `src/retained_events.cpp:304`, `:530-531`; `src/coding.cpp:1584`
casts a Lua integer to `Op` with no check.

§9.2's case files test only constructs the spec already listed. Nothing
would reveal a bypass like the ones in B3.

**Fix.**
- Measure escapes on a seeded corpus: a branch of blackbird with accepted
  encodings applied.
- Define a verbs-domain enum: a `VERBS_ENUM` declaration, or an enum named in
  a vlib trait. Not every enum class.
- Add an independent oracle that attacks a different fault class. In an
  audit build, vlib's accessors check the invariant at runtime where they
  would `[[assume]]` it. Run the corpus test suites under ASan/UBSan. Every
  runtime violation with no escape finding is a missed escape.

### M4. Major: §5 is underspecified, and the readings differ ten-fold on the corpus (§5)

On blackbird, with subjects declared in `src/` or `include/` and evidence
from all 257 TUs:

| Reading | int findings | string findings |
|---|---|---|
| Call-argument literals initialize parameters | 218 (199 of them parameters) | 84 |
| Call arguments not counted | 19 | 12 |
| ... and no evidence from `tests/` TUs | 10 | 6 |
| `bool` treated as an integer type (Clang's `isIntegerType()` includes it) | +146 `bool` | |

On BRepGPU (`native/`, `include/`), the same readings give 45, 20 and 7 int
findings and 52, 0 and 0 string findings. Treating `bool` as an integer type
adds 42 `bool` findings.

The undefined points, each of which moves these numbers:
1. Whether a call argument "initializes" a parameter.
2. Whether test TUs supply evidence. 143 of blackbird's 257 TUs are tests.
3. Whether `bool`, plain `char` and unscoped enums are "integer type".
   Clang's `isIntegerType()` includes `bool` (`BuiltinType::isInteger`,
   `TypeBase.h:3289-3291`) and complete unscoped enums (`TypeBase.h:
   9094-9101`). Bool clusters are a deferred bead (`verbs-de3.24`).
4. Whether a literal is a token, a macro expansion, an enumerator or a
   `constexpr` constant.
   - If it is only a literal token, comparing against a named constant is
     "against a non-literal" and disqualifies, which punishes the better
     code.
   - If macro expansions count, the printed values are platform numbers:
     `EAGAIN` is 35 on macOS and 11 on Linux.
5. Relational comparisons (`<`, `>=`, `<=>`), contextual bool (`if (x)`),
   `.empty()`, `.compare()`, `starts_with`, `find`. None of these is counted
   or disqualifying.
6. What "a function outside the analyzed code" means for strings.
   `s == "x"` calls libc++'s `operator==`, so a strict reading disqualifies
   every string subject.
7. What "serialization calls" means. Blackbird's encoders are its own
   analyzed functions: `Fields::native` (`src/raw_file.cpp:31`, which
   receives `ending_` at `:326`) and `RawRetainedFields::native`. A
   name-based rule cannot decide this.
8. Whether a lambda body is a separate "function". If it is, single-function
   locals become candidates: `op` (`src/beads.cpp:223`), `stage`
   (`src/raw_runtime.cpp:816`).
9. How a subject is identified across units. See M8.

**Fix.** State each point in §5. The minimum consistent set:
- literals are integral constant expressions, rendered with their spelling;
- call-argument literals count only when the parameter does not reach a
  disqualifying use in the callee;
- no evidence from test TUs;
- `bool`, plain `char` and enums are excluded;
- relational comparison against a non-literal disqualifies;
- `starts_with`, `find` and `compare` disqualify (they mark an open domain);
- "outside the analyzed code" means a callee without a definition in the
  database, excluding comparison operators;
- serialization means any function that receives the subject's value and
  writes it to bytes or text, found through the analyzed call graph.

### M5. Major: measured false-finding classes (§5)

Hand review of the narrowest blackbird reading (10 int fields and locals)
found two or three true candidates. True: `RawBeadsTrace::stage`, and
possibly `Resource::ending_` and the `raw_runtime.cpp` `stage`, which are
serialized. The rest were false. BRepGPU's narrowest set had about four true
out of seven: `bgom10::Carrier::tag`, the two `state` fields, and
`CurveData::kind`.

False classes, with examples:
- **Test assertions read as enum comparisons.**
  `ChatFrameGeometry::cursor_column` (`include/blackbird/chat_view.hpp:134`):
  values {0, 1, 3, 7, 8}, every comparison in `tests/ui_raw_test.cpp` and
  `tests/chat_view_test.cpp`.
- **Limits set by tests.** `EnvironmentBounds::max_history_entries`
  (`retained_environment.hpp:11`): values {1, 3, 5, 6, 9, 10}, all from test
  assignments, with relational uses in src.
  `WorkflowJoinDescriptor::max_observations` and `collect_limit`
  (`workflow_join.hpp:51,53`).
- **Open ID domains.** `RawUiTrace::error_site_` {4009, 4084}
  (`raw_ui.hpp:104`). `RawBridgeTrace::terminal_` {0, 4825}
  (`raw_bridge.hpp:32`), where 0 is the moved-from reset at
  `src/raw_bridge.cpp:20`.
- **Message strings.** `TuiInstrument::State::notice` (`src/tui_instrument.cpp`):
  seven user-facing sentences assigned in different functions. BRepGPU's
  per-file `fail(const char* message)` helpers become 52 parameter
  "candidates" when call arguments count.
- **Quantities passed as literal arguments.** `bytes`, `offset`,
  `max_bytes`, `width`, `amount` (for example `include/blackbird/retained_proposal.hpp:16`
  `max_bytes` {48, 64, 74, 75, 1024, 32768}).
- **Signal flags.** `volatile std::sig_atomic_t auth_interrupted`
  (`src/provider_oauth.cpp:26`) {0, 1}. Changing its type breaks async-signal
  safety.
- **C ABI structs.** BRepGPU's `bg_*_desc` fields in C headers
  (`include/brepgpu.h:49-54`, consumed by Python ctypes) cannot hold an
  `enum class`. `adaptive_curve_types.h:52` `image_available` {0, 1} is an
  int-as-bool in a `.h` shared with CUDA.
- **`const char* == "lit"`.** This compares pointers, so it is a bug, not an
  enum use. The real string comparison, `strcmp`, is an external call and
  disqualifies. For `const char*` subjects, §5 therefore counts only bugs.
- **Code that cannot hold vlib types.** In C++17/20 code (BRepGPU, Oxcart),
  the encoding `verbs::to_enum` cannot be applied without a standard bump.

**Fix.** Encode the classes as rule clauses:
- evidence from tests does not count;
- relational use against a non-literal disqualifies;
- `volatile`, `std::atomic` and `sig_atomic_t` subjects are excluded;
- subjects in `extern "C"` structs or C headers are `outside` (ABI
  boundary);
- `const char* ==` literal is a separate bug finding;
- a subject whose literals are all string literals assigned (never
  compared) is not a candidate;
- in a TU below C++26 the finding carries a plain `enum class` encoding, or
  is `outside`.

### M6. Major: §9.3 tunes on the corpus it measures, with no recall floor (§9.3)

"Thresholds are tuned until the findings are [true]" is satisfied by zero
findings. It also overfits the two repos.

The thresholds cannot reach the false classes. `error_site_` (2 values, 2
functions) and `Resource::ending_` (3 values, 3 functions) sit inside the
same thresholds. What separates them is ingress, value sparsity, sentinels
and relational use, which are rule clauses.

**Fix.**
- Change rules, not thresholds.
- Develop the rule on blackbird and measure it on a held-out repo: Oxcart's
  C++, or another C++ repo the operator names.
- Keep a recall set of known true candidates (for example the 27
  `static_cast`-to-enum sites in blackbird, whose sources are integers with
  a known domain) and report recall next to precision.

### M7. Major: include-set tracking misses affected units even with a complete change list (§6.2)

1. **Negative dependencies.** `__has_include(<x.h>)` becoming true, or a new
   `include/a/x.h` shadowing `include/b/x.h` earlier on the `-I` path. The
   new file is in no include set.
2. **Compile-database changes.** Changed flags, `-D` macros that select
   includes, `-std`, new or removed entries. `CMakeLists.txt` is in no include
   set, and the database is rewritten by `cmake`, not by the edit tool.
3. **Generated headers.** They change when the build runs, not when their
   input is edited.
4. **New `.cpp` not yet in the database.** It cannot be parsed. The spec is
   silent, and the file's code is unanalyzed without notice.
5. **Deleted TUs.** Their facts files stay and keep contributing evidence
   and disqualifiers to §5's cross-unit evaluation.
6. **PCH.** With `-include-pch`, headers inside the PCH fire no inclusion
   callbacks, so edits to them affect nothing. A PCH built by a different
   Clang than verbs links is a hard parse error.
7. **Modules (C++26 `import std;`).** Imports are not includes, and parsing
   needs the build's BMIs.
8. **`#embed`** (C++26). It has its own callback, not `InclusionDirective`.
9. **Platform-selected code.** A header included only under
   `#if defined(__linux__)` is never in a macOS unit's set. Blackbird has
   about 50 `#if defined(__linux__)` blocks.

**Fix.** Add a step 0 to §6.2:
- Diff the compilation database per entry (command hash), every check.
- Record each include lookup's probed paths and each `__has_include` query
  and result.
- Take inputs from the `SourceManager` file entries plus the PCH's
  input-file list, not from directives.
- On any created or deleted file, or any database change, rerun Clang's
  dependency scanner over all units to get exact include sets. Measured:
  4.9 s wall, 7.7 s CPU for all 257 blackbird TUs under load.
- Drop facts for removed entries.
- Print `! outside` for a changed source that is not in the database.
- Strip PCH flags and parse the prefix header as `-include`.
- Declare modules outside the basics.

### M8. Major: stable keys collide and hide real changes (§6.3, also §5 subject identity)

**Anonymous namespaces.** 57 field or global qualified names in blackbird
name more than one entity. `(anonymous namespace)::Record::site` names 17
distinct fields, one per test TU. `blackbird::(anonymous namespace)::
ErrnoGuard::saved` names 12. With these keys:
- Two findings collapse into one.
- If §5 merges evidence by qualified name, unrelated fields pool their
  literals.

**Parameters.** Clang's `getQualifiedNameAsString` returns a parameter's bare
name. 311 of blackbird's 522 parameter names are shared by more than one
parameter. Overloads collide even with function qualification:
`raw_authored_emit` has four overloads, each with `std::int64_t site`
(`include/blackbird/raw_authored.hpp:18-24`). Parameter names also differ
between declaration and definition.

**Unnamed structs and lambdas.** Two unnamed structs in one class both give
`H::(unnamed struct)::mode`. Two lambdas in one function give the same
qualified names for their parameters and locals. USRs separate them only by
byte offsets (`c:@S@H@S@u2.cpp@11@FI@mode`), which put line-like positions
back into the key: every edit above them churns the key.

**Escapes.** An escape is keyed by subject and construct class. Adding a
second `const_cast` on `Ledger::balance` creates no new key, so it is never
reported. Removing one of two prints nothing.

**Changed evidence.** A candidate's values growing from {0, 1, 3} to
{0, 1, 3, 4} changes the suggested encoding under the same key, and no line
is printed.

**Fix.**
- Key externally visible entities by USR.
- Key internal-linkage entities by repository-relative file path plus
  qualified name.
- Key parameters by (function key, index).
- Key lambdas and unnamed types by (enclosing key, ordinal among siblings of
  that kind).
- Escapes add the enclosing function's key, the construct, and an ordinal
  within that function.
- Print a `~` line when a finding's evidence or encoding changes under an
  unchanged key.

### M9. Major: withheld findings are never shown (§6.4)

§6.4 caps output at N per file and M in total. Withheld findings go into the
new report, so on the next check they are not new and are never printed. One
large edit can therefore bury escapes permanently.

**Fix.** The report marks each finding shown or unshown. Unshown findings
carry into the next delta until they are printed.

### M10. Major: other breakers of incremental equals from-scratch (§9.4, §6.2)

Beyond B1 and M7:
- **Concurrent runs.** Parallel edit calls, or several Blackbird agents in
  one build directory, start concurrent `verbs check` processes. They race
  on facts files and the report.
- **Broken intermediate states.** Mid-refactor states that do not compile
  (an agent changes a header signature, then fixes callers over several
  edits) yield partial facts from error-recovered ASTs. Findings resolve and
  re-add as callers break and heal.
- **Narrow test generator.** §9.4's "any sequence of edits" will be tested
  with edits the generator knows how to make. If the generator only scripts
  in-hook edits, the property passes while B1 and M7 stay broken.

**Fix.**
- An exclusive lock on `<build-dir>/verbs/`, with write-then-rename for every
  facts and report file.
- A unit with compile errors keeps its previous facts. It is listed as
  `not refreshed (compile errors)`, and no `-` line is printed for evidence
  that depends on it.
- The §9.4 edit generator includes out-of-band writes, file creation and
  deletion, database changes, generated headers, and non-compiling
  intermediate states.

With B1, M7 and this fix, the property is achievable. Each check then is a
verifying-trace rebuild over a complete dependency record, and from-scratch
differs only in work done.

### M11. Major: latency is unbudgeted, and header fanout makes many edits slow (§6.2, §13 verbs-de3.14)

Measured on blackbird (257 TUs, `build/debug`):

| Quantity | Value |
|---|---|
| CPU per TU, extraction probe | p50 3.1 s, p90 3.8 s, max 5.2 s (`src/coding.cpp`) |
| CPU for all TUs, `-fsyntax-only` / probe | 704 s / 737 s |
| Full scan on 16 idle cores (lower bound) | about 46 s; at load 95 it took 6.9 min wall |
| Fanout of `include/blackbird/foundation.hpp` | 243 of 257 TUs |
| Headers with fanout ≥ 200 / ≥ 100 / ≥ 50 | 9 / 22 / 50 of 106 |
| Header fanout, median / mean | 30.5 / 63.7 TUs |
| Header touches in the last 30 days of commits | 364 of 1,329 C++ file touches (27%) |
| Fanout weighted by those touches, mean / median | 72.5 / 59 TUs; 25% of touches hit ≥ 100 TUs |

A `.cpp` edit costs one TU: 1.2-5.2 CPU-s on one thread, which is plausible
per edit. A header edit costs fanout × about 3 CPU-s. On 16 idle cores that
is about 14 s for the touch-weighted mean and about 47 s for `foundation.hpp`.
The host is seldom idle: load was about 95 while these numbers were taken,
and several agents each running 16 extraction jobs multiply that.

A first check in a new worktree or build directory pays a full scan. So does
any facts-format version bump.

The toolchain lane found main-file reparse dominant (warm clangd only
1.5-2.5× faster), so preambles do not rescue header edits.

The spec defers this measurement (verbs-de3.14) while its stateless design
depends on the result.

**Fix.** §6 states:
- **A budget,** for example p95 under 10 s per edit.
- **The cost model above.**
- **One over-budget behaviour.** Either block, or print the delta for the
  units finished within budget plus a `~ N units pending` line. Pending
  units are recorded as stale and finished by the next check.
- **Shared job slots** across concurrent verbs processes (a semaphore file in
  `<build-dir>/verbs/`).
- **Facts shareable across worktrees,** keyed by input hashes (constructive
  traces).

Turning the check on in Blackbird's hook is gated on the budget, measured on
the fleet.

### m1. Minor: uninstantiated templates as `outside` (§4)

An uninstantiated template has no declaration to attribute an escape to, so
`outside` (a per-declaration state, §2) cannot be filed against anything.
Such code affects no claim in the analyzed code.

**Fix.** Say "not analyzed; no claim depends on it".

### m2. Minor: the footer example is incomplete (§6.4)

The footer example prints 4 of the 7 assumptions that §2.3 says every footer
carries.

**Fix.** Print all seven, or make §2.3 name the abbreviated set.

### m3. Minor: unanalyzed headers pass silently (§6.2, §2.3 item 7)

`--changed` on a header that no unit includes, or that is included only under
an inactive `#if`, prints nothing.

**Fix.** Print `! unanalyzed: no unit includes <path>`. Item 7 should say
"the analyzed code is the preprocessed code under this database's
configuration".

### m4. Minor: path canonicalization (§6.2)

The hook's paths may be relative or reached through symlinks (blackbird and
verbs both track symlinked `BLACKBIRD.md`), so they can miss recorded paths.

**Fix.** Canonicalize both sides with `realpath`.

### m5. Minor: generated and vendored code (§4, §5, §7)

The checks report findings in code no one edits by hand, such as the Unicode
tables in `src/unicode_emoji.hpp`.

**Fix.** A repository path rule marks such code `outside`. A change to that
rule is a `!` silencing line.

### m6. Minor: sentinels counted as domain members (§5)

Default-initializer zeros, moved-from resets and `-1` sentinels enter the
literal set (`Node::kind` 0, `terminal_` 0).

**Fix.** The encoding then names `std::optional<E>` or an explicit `unset`
enumerator. This overlaps B2 item 3.

### m7. Minor: header-defined functions counted once per TU (§5)

An inline function in a header appears in every TU that includes it. Rule 2's
"at least 2 functions" must count functions by identity, not by occurrences.
The probe did this by USR.

**Fix.** Say so in §5.

### m8. Minor: a replaceable violation handler (§3.1, §4)

If the violation handler is user-replaceable, a definition that returns
breaks `+=` narrowing.

**Fix.** Make it non-replaceable, or make a user definition an escape.

### m9. Minor: BRepGPU parse settings (§9.3)

BRepGPU's mesher sources need `-std=c++20`, although its top-level CMake says
`cxx_std_17`. 31 of 187 sources need Linux, OCCT or Parasolid headers. §9.3
on BRepGPU therefore needs a configured database on the fleet.

**Fix.** Name that database in the §9.3 procedure.

## Attacks that failed

- **Macro-dependent includes** whose macro comes from an included header.
  The defining header is in the include set, so edits to it re-extract the
  unit. This only fails when the macro comes from the command line (M7 item
  2).
- **Bit flags.** `&`, `|` and `|=` count as arithmetic and disqualify. No
  corpus subject was found that is used as a flag set only through `==`.
- **`errno`-style values.** `errno` is not a declaration. Copies of it are
  one-function locals that rule 2 excludes. `blackbird::Error::detail` mixes
  errno, HTTP and curl codes (`src/coding.cpp:4653-4659`), but it has more
  than 16 values and is excluded.
- **`-1` file-descriptor sentinels.** Passing the descriptor to `::close` or
  `::read` disqualifies it.
- **`std::map` keys and lookup tables.** The subject goes to a std lookup
  and is disqualified. This loses recall but produces no false finding.
- **Large code domains.** `Scan::record`'s local `site`, with about 25 codes,
  is a single-function local over the 16-value cap. The field it feeds is B2.
- **`mutable` on a vlib member.** Mutation still goes only through vlib's
  operations, so it is correctly not an escape. The brief listed it.
- **Inheriting from `Bounded` to reach `v_`.** The member is private, so
  access fails.
- **Assigning a valid `Bounded` through `const_cast`.** The range invariant
  holds. Only the `const` predicate is voided, and §4 reports that cast
  anyway.
- **Include-guard and `#pragma once` re-inclusion.** The first entry is
  recorded.
- **Header-only code with templates.** It matters only when some unit
  instantiates it, and that unit's include set covers the header. The
  remainder is m3.
- **Cross-unit evaluation cost.** Reading per-unit facts for 257 units is
  negligible next to parsing.
- **Line numbers in Clang 23 qualified names.** Lambda and unnamed-type
  qualified names print as `(lambda)` and `(unnamed struct)` with no
  location. The real problem is collision and USR offsets (M8), not printed
  lines.
