# verbs: habits as library constructs with compiler and lint guards

Status: draft for builder check and tribunal, 2026-11-23. Replaces
design/SPEC.md (superseded). Inputs:
- the operator's direction (journal/2026-11-23-redesign.md);
- the five lane reports papers/2026-11-23-lane-{encoding, adt,
  state-machines, bounded, agent-faults}.md (cited below as *enc*, *adt*,
  *sm*, *bnd*, *faults*, with section numbers);
- the post-mortem papers/2026-11-23-old-design-postmortem.md.

## 1. Intent

Agents write the code. Today the good habits live in prose doctrine: "favor
algebraic data types", "use state machines", "make illegal states
unrepresentable". Agents follow it unevenly, and nothing checks it.

verbs replaces that prose with mechanism. A habit becomes:
- a library construct that carries the discipline;
- guards that fire where the agent already gets feedback: the compiler and
  the project's lint pass.

When an agent drifts, it gets a diagnostic at the line, naming the construct
that fixes it. The agent does not have to remember doctrine. The operator's
words: "real mechanistic feedback/stops" instead of "a bonus doctrine".

verbs ships two things:
1. **A way to encode a habit.** Adding a habit is ordinary work, because
   habits will be "enumerated in the field" as they occur.
2. **Three starter habits**, in this order:
   - **state machines.** This is the lead habit: the largest class of
     construct-addressable faults in the operator's own reviews, and the
     most severe (*faults* §5.2, §8.1);
   - **algebraic data types;**
   - **bounded types.**

Languages: C++ and Rust. Each gets its strongest native realization; there is
no parity layer. A third language later is a new set of native parts behind
the same habit declarations, not a redesign.

## 2. Goals, non-goals, anti-goals

**Goals**
- An agent that bypasses or avoids a habit's construct is stopped or nudged
  in the same build or lint run it already does, with a message that names
  the construct.
- Every finding has a way past it that records a reason at the site, and a
  stale way past is itself reported.
- A new habit is one directory: a declaration, the native parts and tests.
  No change to verbs' core machinery is needed for one.
- Each guard is tested at an exact location: a hand-written expectation,
  plus seeded faults in real corpus code.

**Non-goals (this round)**
- A soundness claim. verbs does not claim that no path bypasses a
  construct. The old design died proving that in C++ (post-mortem). Each
  habit states plainly what it stops and what it does not.
- Proof backends: Flux, SPARK-style provers, C++26 contracts, Rust pattern
  types (*bnd* §2.5–2.6, §1.9).
- Faults no construct reaches: weak test oracles, domain logic, docs drift.
  That is 48% of the operator's reviewed faults (*faults* §5.2). Mutation
  testing of a project's own tests is a later scope option.
- Hosting on Semgrep or CodeQL, adopting Boost.SML or MSM, Clang's Consumed
  analysis (*enc* §4–5, *sm* A1, A3–A4).

**Anti-goals** (failure even if it works technically)
- **Doctrine in a new costume.** Findings so noisy that agents answer them
  by rote, so reasons become boilerplate.
- **Machinery that outgrows the habits.** That is the old design's failure
  mode.
- **Warning counts as a quality signal** (*faults* §8.2).
- **A hard dependency on an LLM, or on GPU capacity.**

## 3. Constraints

- **Toolchains.**
  - C++: C++26 (`-std=c++2c`) on the pinned Homebrew LLVM/Clang 23.1.2. It
    has no P2996 reflection and no contracts (*adt* §1.6, *bnd* §1.9).
  - Rust: the verbs crate and user code build on stable (repo pin 1.99.0).
  - The Rust lint driver runs on a pinned nightly with `rustc-dev`. The
    operator chose an owned driver over Dylint on 2026-11-23.
- **No runtime dependencies. Owned machinery.** Studying reference
  implementations is fine; adopting a library is discussed with the operator
  first.
- **Data formats.** No JSON or JSONL internally (BLACKBIRD). Persistent data
  is owned text or binary.
- **No LLM in any required path.**
- **False findings.** Zero is impossible, and nothing promises it. A false
  finding found on the corpus is a defect to fix in its rule, or the rule is
  cut. It is not a tolerated rate, and there are no statistical gates.
- **Disk.** About 90 GiB free. The corpus stays as tarballs, and extracted
  trees are swept after every run.

## 4. Approaches considered

1. **Guards discover unencoded constructs, with blocking nudges** (chosen
   by the operator: "(b) as foundation with (c) layers on top").
   - A finding is a *stop* when evidence is strong: misuse of the construct,
     a bypass of it, or an exact rule the operator always accepts.
   - It is a *nudge* when code only looks questionable.
   - Both block until the agent changes the code or records a reason.
2. **Stops only, no discovery.** This is the evidence-safe choice: nudge
   precision measured 22–61% (*adt* §3, *sm* B, *bnd* §4.1). The operator
   chose (1). The design takes the evidence into account by gating which
   nudges ship (§7.4).
3. **One rule language realized in every language** (the Semgrep/CodeQL
   model). Rejected:
   - nothing in the field does it with semantic precision (*enc* §6);
   - it would be the parity layer the brief rules out;
   - it runs outside the compiler loop.

Rust lint host:
- owned driver (chosen);
- Dylint: a dependency, and it pins nightly anyway;
- stable only: leaves the catch-all and nudge lints unbuildable (*enc* §1.4,
  §1.5).

## 5. The habit model

### 5.1 Parts of a habit

| Part | What it is | Where it runs |
|---|---|---|
| **Construct** | A C++ header type or a Rust crate type that carries the discipline | The user's code |
| **Construct stops** | Misuse the construct rejects in the language itself: `= delete("reason")`, `static_assert` with a generated message, constrained templates, sealed traits, `#[diagnostic::on_unimplemented]`, privacy, `unsafe` doors (*enc* §2.1, §1.2) | The compiler, on every build. No verbs tool is needed |
| **Lint findings** | Stops and nudges that need a semantic pass: bypasses of the construct, catch-alls, code that looks like it should use the construct | The verbs pass (§6) |
| **Way past** | A marker at the site naming the finding and a reason (§5.3) | Read by the verbs pass |
| **Tests** | Exact located expectations per finding, plus seeds for the corpus (§8) | The verbs repository and corpus runs |

### 5.2 Stop and nudge

Both tiers fail the agent's build or lint run, and both accept a way past
with a reason. They differ in three ways:
1. **Evidence.**
   - A stop rests on language semantics, explicit intent (an author's
     `assert(false)` at the end of a dispatch chain, *adt* §3.7), use of a
     construct's named bypass door, or an exact rule.
   - A nudge rests on a code shape.
2. **Message form.**
   - A stop says what is wrong and which construct fixes it.
   - A nudge says what the code looks like, which construct would carry it,
     and asks for a reason if the code is not that.
3. **What a wrong finding means.**
   - A wrong stop is a bug in verbs, fixed before anything else.
   - A wrong nudge shows up as a way-past reason on the corpus. It is a
     defect in the rule's shape: the rule is narrowed or cut.

A way past is still written by the agent for both tiers. Neither tier has a
softer channel.

### 5.3 Way past, with a reason

**Rust**
- The native `#[expect(lint, reason = "…")]`. The driver reports
  `unfulfilled_lint_expectations` for verbs lints, which makes a stale
  marker a finding (*enc* §1.1).
- The driver turns on `clippy::allow_attributes` and
  `allow_attributes_without_reason` semantics for verbs lints, so `allow`
  without a reason, and `allow` where `expect` fits, are findings.
- An inner `#![allow]` or `#![expect]` naming a verbs lint at module or
  crate scope is a finding. One reason must not silence a whole module
  (*enc* §1.1 gap a).
- Lint names: the driver registers the `verbs` tool through
  `-Zcrate-attr=register_tool(verbs)`, so markers read
  `#[cfg_attr(verbs, expect(verbs::sm_catch_all, reason = "…"))]`. A
  plain stable build sees nothing (*enc* §1.5). The builder may add a
  `verbs::expect!`-style attribute macro if the `cfg_attr` spelling proves
  too heavy for agents.

**C++**
- An owned marker, `VERBS_EXPECT(finding_id, "reason")`. It expands to
  `[[clang::annotate("verbs.expect", "finding_id", "reason")]]` and goes on
  a declaration or a statement. It reaches the AST in clang, clang-tidy and
  clangd with no plugin attribute (*enc* §2.4, probed).
- The verbs pass:
  - consults the marker;
  - requires a non-empty reason;
  - reports a marker that suppresses nothing.
- **When a C++ marker is judged stale** *(builder check, my call).*
  - A marker in the main file is judged in every compile.
  - A marker in a header, or inside a template, can be needed in one unit
    and idle in another. It is judged by `verbs stale`, an owned command
    that runs the checks over the whole compile database and reports
    markers idle in every unit. Nothing is written to disk.
  - The project's check script runs `verbs stale`. The per-compile channel
    never reports a header marker as stale.
- Plugin-registered attributes are not used: scoped plugin attributes lose
  their arguments, and clangd strips plugins (*enc* §2.4).
- verbs findings are emitted at error level. Error-level diagnostics
  escape NOLINT and pragmas (*enc* §2.3, `NoLintDirectiveHandler.cpp:270`),
  so `VERBS_EXPECT` is the only way past.
- Constructs with an in-language default arm take the reason in the
  construct itself, for example `verbs::otherwise<"reason">(f)`. Staleness
  is then checked at compile time by `static_assert` (*adt* §5, probe
  `o2`).

**Reason quality**
- verbs checks only that a reason is present, plus a minimum length. The
  builder picks the length; the probe used 8 characters. It does not judge
  content.
- Reasons live in source, so every new or removed way past appears in the
  change's diff, where review sees it. That is the answer to "a reason makes
  a bypass reviewable, not right" (*faults* §7.6).
- The verbs pass also ends with a one-line count per unit of ways past it
  honoured. There is no ledger file.

**Silencing outside the marker** is a finding when verbs can see it:
- C++: a `#pragma clang diagnostic` or `-Wno-` naming a verbs diagnostic;
- Rust: `--cap-lints` or a `[lints]` table entry that lowers a verbs lint.

How verbs notices its own absence is in §6.4.

### 5.4 The habit declaration

Each habit is a directory, `habits/<name>/`:

```
habits/state-machine/
  HABIT.md        the declaration (below)
  cpp/            construct header(s), check sources, -verify tests
  rust/           crate module(s), lint sources, ui tests
  seeds/          seed definitions for corpus runs (§8.2)
```

HABIT.md is written for agents and the operator:
- the habit in one paragraph;
- what it stops and does not stop, in plain words;
- a findings table, the one machine-read part. One row per finding:
  - `id`, e.g. `sm-catch-all`;
  - tier;
  - evidence class;
  - per-language realization: `cpp: tidy-check | construct | n/a(reason)`
    and `rust: native(E0004) | lint | n/a(reason)`;
  - message;
  - fix applicability (Rust's four levels);
  - the corpus record (§7.4).

One owned command, `verbs habits check`, cross-checks the findings table
against the code. Every id has its realization in each language, or an
`n/a(reason)`, and every realized id has at least one located test. That is
the only machinery a new habit touches. Messages are written once in the
table, and the native parts copy them. A test asserts that the text
matches.

## 6. Delivery: where findings reach the agent

### 6.1 C++

- **Constructs:** a header library, `verbs/`. It is C++26 on the pin.
  Enumerator names for messages come from a declaring macro, because there
  is no reflection on the pin. The builder decides between a small owned
  macro and a magic_enum-style scan (*sm* open question 7). Reflection
  replaces it when the pinned Clang carries P2996.
- **Checks:** one module of `ClangTidyCheck` classes, `verbs-tidy`, built
  against the pinned LLVM. The same source runs in three hosts (*enc*
  §2.3–2.4, probed):
  1. **In the compiler**, via `-fplugin` with Homebrew's
     `libclangTidyPlugin.a`. This is the primary channel: the agent's
     normal build fails at the line. Probed overhead on a small unit was
     not measurable. The builder measures it on blackbird.
  2. **In clang-tidy**, via `-load`, for projects that gate on clang-tidy.
  3. **In a custom clangd**, for editor surfaces. This is deferred until a
     consumer asks for it.
- **Severity:** findings are emitted at error level. Plugin mode ignores
  `WarningsAsErrors` and `-Werror` (*enc* §2.3 check).
- **Plugins carry no ABI promise.** The checks rebuild on any LLVM change,
  and the pin makes that rare.

### 6.2 Rust

- **Constructs:** the `verbs` crate, on stable. It replaces the 0.1.0
  placeholder `check()`.
- **Lints:** `verbs-driver`, an owned rustc driver on a pinned nightly with
  `rustc-dev`, shaped like clippy-driver (quarantine/rust-clippy), and
  invoked by `cargo verbs`. The driver:
  - registers the `verbs` tool;
  - sets `--cfg verbs`;
  - runs the verbs lints alongside rustc's own;
  - judges verbs expectations.
- **Habit lints are owned, not borrowed from clippy** *(builder check, my
  call).*
  - The driver does not link `clippy_lints`, which would be a library
    adoption.
  - Where a habit needs what a clippy lint does, verbs-driver carries its
    own narrow version, so verbs messages, the way past and staleness apply
    uniformly. Example: a wildcard arm on a verbs-marked enum
    (`adt-default-on-owned-enum`). Clippy's `wildcard_enum_match_arm` would
    hit every enum.
  - Clippy keeps running as the project's own pass, which is outside verbs.
  - HABIT.md may recommend clippy settings, but no verbs finding depends on
    clippy running.

### 6.3 How the agent gets it

- **C++:** every compile is the channel, because the plugin flag is in the
  project's compile flags.
- **Rust:** construct stops arrive in `cargo build`. Lint findings need
  `cargo verbs`. verbs ships a snippet for the project's check script and
  for rust-analyzer's `check.overrideCommand`. Wiring it into Blackbird's
  edit hook is Blackbird's work.

Evidence: pull-only tools go unused (post-mortem), and in blackbird agents
fixed a lint gate's stops by introducing a type (*faults* §4.4).

### 6.4 verbs notices its own absence

- **C++.** A verbs header makes the build fail when the plugin is not
  loaded. The header can test for an attribute that only the plugin
  registers. Clang's `hasAttribute` matches plugin spellings (*enc* §2.4),
  so `__has_cpp_attribute(verbs_plugin)` should become true exactly when
  the plugin is loaded. **This is to be probed by the builder.**
  - If it works, a translation unit that includes verbs without the plugin
    gets `#error`. The only exit is `VERBS_WITHOUT_PLUGIN("reason")`.
  - If it does not work, the builder proposes another mechanism to the
    operator before planning around it.
- **Rust.** Under `--cfg verbs` the crate behaves normally. Without it, a
  plain `cargo build` still gets every construct stop; only lint findings
  are absent. The project's check script is what runs `cargo verbs`. This
  is a stated limit, not a hidden one.

### 6.5 Adoption and users (operator, 2026-11-23)

- **Users this round:** the operator's projects (blackbird, oxcart) and the
  corpus, on the macOS pin.
  - Nothing is published. The 0.1.0 placeholders on the registries stay as
    they are.
  - A Linux build of the plugin and driver happens only when fleet mutation
    testing needs one.
- **Adoption is per habit, stops first.**
  - A project lists the habits it uses in one verbs config file at its
    root: owned line-based text, readable in a diff. The builder picks the
    exact format.
  - For each habit the file says whether its nudges are on.
  - A project turns a habit's nudges on once the existing hits are fixed,
    or carry reasons a reviewer has read.
  - There is no baseline file.
- **What counts as silencing.** Leaving a habit or its nudges out of the
  config file is adoption, not silencing.
  - Narrowing verbs' checks any other way is a silencing finding: a
    `.clang-tidy` `Checks:` line, driver flags, pragmas, `-Wno-`, or
    `--cap-lints`.
  - The §6.4 header probe shows the plugin is loaded. The config file shows
    which habits are on.

## 7. The starter habits

Each section lists the construct, its stops, its lint findings and what it
does not stop. Finding ids are illustrative; HABIT.md fixes them.

### 7.1 State machines (lead habit)

**Construct**
- **C++ `verbs::machine`.** States and events are declared enums. The
  transition table is `constexpr` data. Each row is
  `{from, on, kind ∈ {go, ignore, illegal}, to}` (*sm* A6).
  - **Guards** *(builder check, my call).* A `go` row may carry a guard, a
    `constexpr`-named predicate over the owner's data. A guarded row must
    name its fallback target (`go_if(guard, to, otherwise_to)`), so the
    table stays total, and reachability counts both targets.
    "On Ack go to Done if pending==0, else stay" is one row.
  - **Actions.** A row may name an action, an owner member function that
    `fire` calls after the state changes. Actions may not call `fire` on the
    same machine: re-entry returns an error.
  - **Data per state** stays in the owner object. The machine owns the
    state tag, the generation and the table, and nothing else. Data that
    exists only in one state is an ADT concern: the owner may hold it in a
    `std::variant` matched with `verbs::match`.
  - **The step is `fire`.** There is no user-written step function in C++.
    Code that reads `state()` and branches on it is ordinary code; a
    `default:` in a switch over a machine's state enum is
    `adt-default-on-owned-enum`.

  Then:
  - A `consteval` check rejects, with a message naming every offending
    pair:
    - a non-total table;
    - duplicate rows;
    - states unreachable from the initial state;
    - a `go` row out of a state declared terminal, unless it is listed as
      a declared recovery.
  - State is private. `fire(event)` is the only mutator.
  - `fire` with an event type outside the alphabet fails to compile (a
    constrained template).
  - **Late completions** *(builder check, my call).*
    - The table marks some events as **completions**. `fire` on a
      completion event requires a `ticket` argument. Without one it
      fails to compile, so the check cannot be skipped.
    - `ticket()` captures the current generation. The generation increases
      on every `go` transition that changes state.
    - A completion fired with a ticket from an earlier generation does not
      transition. `fire` returns `stale`, which the caller cannot discard.
    - This targets the record's highest-severity faults:
      - a late acknowledgement overwrites Stop;
      - a queued Close runs after a failure.
      (*faults* §5.2, §7.1.)
  - **On an `illegal` pair**, `fire` returns a result the caller cannot
    ignore (`[[nodiscard("…")]]`). The builder picks between returning an
    error value and aborting (*sm* open question 1). My call: return an
    error value; abort is a policy the table can name per row.
  - **An observer hook** receives `(from, event, to)` for trace checks
    (§8.3).
- **C++ linear protocols** (open/use/close handles): phantom-state types
  with `requires` on the state. Reuse after a transition is checked by a
  verbs check on the `bugprone-use-after-move` model, which already accepts
  named invalidating functions (*sm* A2). Its limit, locals and parameters
  only, is stated in HABIT.md.
- **Rust.** The language's own machine:
  - an `enum State` with data in its variants;
  - an exhaustive `match (state, event)` step function;
  - consuming-`self` typestate for linear protocols.

  The crate adds *(builder check, my call)*:
  - **`Tracked<S>`.** It holds the state value and its generation.
    - `ticket()` issues a `Ticket`.
    - `complete(ticket, |s| …)` runs the transition only when the ticket is
      current, and otherwise returns `Stale`, which is `#[must_use]`.
    - The state field is private to the crate, so a write that skips the
      generation does not compile. This makes the ticket a type-level stop
      on stable, not a lint.
  - **A marker on the state enum.** It declares the initial, terminal and
    recovery states:
    `#[cfg_attr(verbs, verbs::machine(initial = Idle, terminal(Done, Failed), recovery(Failed => Idle)))]`.
    The step function carries `#[cfg_attr(verbs, verbs::step)]`.
  - **The step's arms construct their target variant directly, or return
    the state unchanged.** An arm whose target the lint cannot read is its
    own stop, `sm-opaque-target`, with the usual way past. That keeps the
    Rust lints syntactic: no dataflow.

**Stops**

| Finding | C++ | Rust |
|---|---|---|
| (state, event) pair unhandled | construct (`consteval`) | native E0004 |
| duplicate / unreachable / terminal escape | construct | lint `sm-table` on the marked step (unreachable and terminal escape only) |
| target not readable from an arm | n/a (the table is data) | lint `sm-opaque-target` |
| completion without a current ticket | construct (no ticket overload; `stale` result) | construct (`Tracked::complete`) |
| catch-all arm in the step | n/a (`fire` is the step) | lint `sm-catch-all`; clippy misses the tuple form (*sm* A8) |
| state written outside the step / `fire` | construct (privacy); check for `friend` or `const_cast` into a machine | lint `sm-outside-write` on the marked field |
| method called in the wrong typestate | construct (`requires`) | native E0599 |
| handle reused after a transition | check `sm-use-after-transition` (locals and parameters) | native E0382 |

**Nudges**
- `sm-guarded-field`: an enum or bool member guarded in two or more methods
  (`if (state != X) return/throw/assert`) and written outside the
  constructor. Measured 5/6 on a development sample (*sm* B3). It is the
  one state-machine nudge that ships first (§7.4).
- Write-scatter on enum fields (*sm* B3, SM2) is a candidate, measured
  before it ships.
- **One owner per field.** A field that triggers both a state-machine nudge
  and an ADT nudge reports once, from the state-machine habit. `has_*`
  presence pairs belong to ADTs (*sm* open question 5).

**Does not stop**
- members or heap objects outliving a linear protocol;
- "dropped before reaching a final state" (an accumulation property; *sm*
  A13). This is a later finding;
- hierarchical and orthogonal machines, which are a later habit.

### 7.2 Algebraic data types

**Construct**
- **C++ `verbs::match(v, arms…)`** over `std::variant`. It wraps rather
  than replaces `std::variant`, for interop (*adt* open question 1).
  - It is a compile error when:
    - an alternative has no exact arm;
    - an arm is reached only by implicit conversion;
    - an arm is a generic catch-all.
  - Each error names the alternative (1.7 KB of diagnostic against 10.7 KB
    for `std::visit`; *adt* §1.2).
  - The only default is `verbs::otherwise<"reason">(f)`. It is stale, and
    a compile error, once every alternative has an exact arm.
  - Two cases the prototype does not handle (*adt* §1.2): constrained
    generic arms (`std::integral auto`) and base-class arms. Both are
    errors by default, and either can take the `otherwise` path. Visiting
    several variants at once is later work.
- **Rust.** Native enums and E0004. A marker,
  `#[cfg_attr(verbs, verbs::closed)]`, on an enum makes it owned by the
  habit. The driver then stops `_ =>` and single-variant wildcards on it.
  These are owned lints, narrowed from clippy's
  `wildcard_enum_match_arm` and `match_wildcard_for_single_variants`
  (*adt* §2.2).

**Stops**
- `adt-index-switch`: `switch (v.index())` on a variant (C++).
- `adt-assert-chain`: a `holds_alternative`/`get_if`/`if constexpr` chain,
  or an `if let` chain in Rust, whose final branch asserts, throws or is
  `unreachable!`. The author's own assert is the evidence (*adt* §3.7,
  solidity). The message does not prescribe "add arms", because the right
  fix may be a narrower type.
- `adt-default-on-owned-enum`: `default:` in a switch over an enum declared
  through verbs (C++), or `_ =>` on a `verbs::closed` enum (Rust, owned
  lint).

**Nudges**
- `adt-tagged-union`: a record with an enum field and a union field. It was
  10/10 true on the corpus sample (*adt* §3.2) and ships first. The way
  past is common and legitimate (C ABI, layout), so the message says so.
- **Candidates**, measured before shipping (§7.4):
  - name-paired fields (`has_X`/`X`, `is_Xing`/`is_Xed`);
  - strings compared against three or more literals (about 25–30% raw);
  - a Rust `as_str().unwrap_or("")` on a parse result (*faults* §7.3).
- **Not shipped:** bool count alone. Only about 28% contained a mode
  sub-cluster (*adt* §3.1), and the operator never asked for clippy
  parity.

**Does not stop**
- sentinels and parallel optionals (no usable detector without co-write
  facts; *adt* §3.3–3.4);
- unchecked `*expected` (a dataflow check is later work, *adt* option 2);
- closed hierarchies used through `dynamic_cast` chains, except when a
  chain ends in an assert.

### 7.3 Bounded types

**Construct**
- **C++ `verbs::bounded<Lo, Hi>`** (*bnd* §1.8).
  - `consteval` literal construction; an out-of-range literal fails with a
    reason-named message.
  - Fallible `make(v) -> std::optional`.
  - Raw-integer assignment and implicit narrowing are `= delete("reason")`.
  - Widening to a containing range is implicit and checked by a concept.
- **Rust `verbs::Bounded`**, shaped like deranged (*bnd* §2.1): private
  field, `new -> Option`, `const` construction, compile-checked
  `expand`/`narrow`.
- **Arithmetic, my call.** Named operations only, in both languages:
  - `checked_add` and friends return an optional;
  - `saturating_*` and `wrapping_*` are spelled out.

  No overloaded `+` that can leave the range, and no silent saturation.
  - *Reasons:* widening on every operation breaks accumulators (*bnd*
    §1.1). Throwing or trapping operators hide the failure path from the
    agent. A named call puts the choice in the code, where a reviewer sees
    it.
  - *Accumulators:* use a wider bounded type or the raw integer, then
    `make` at the end.
- **The unchecked door** is one owned name per language: C++
  `bounded::assume_in_range(v)`, Rust `unsafe fn new_unchecked`. Using it
  is the construct's only bypass that verbs matches by name.
- **No representation claim.** `memcpy` into a `bounded`, casts and unions
  are not detected. HABIT.md says so in plain words (*bnd* §5.3).

**Stops**
- construct-level: bad literal, raw assignment, implicit narrowing;
- `bnd-assume`: a call to the unchecked door without a way past. C++: a
  verbs check matching the owned name. Rust: `unsafe` plus a lint;
- `bnd-raw-escape`: in C++, `.raw()` or the value accessor passed straight
  into arithmetic that is stored back into a `bounded`. **The builder
  confirms this is matchable precisely, or drops it.**

**Nudges**
- `bnd-narrowing`: a narrowing conversion (`bugprone-narrowing-conversions`
  shape, clippy `cast_possible_truncation` shape) whose source is not a
  verbs bounded type. When the source is a bounded type whose range fits
  the target, the finding does not fire. That is the payoff for adopting the
  construct (*bnd* option 3).
  - On Jolt, 13 of 13 narrowing findings were "safe because of a range the
    author knew".
  - This is a verbs-owned check, not a configured clang-tidy one.
  - It is a candidate until its corpus run is read (§7.4).
- Repeated constant range guards (about 45%) and time-unit scalars are
  candidates (*bnd* §4.1, option 5).

**Does not stop**
- dynamic bounds such as `i < v.size()` (out of scope; a later "branded
  index" habit);
- units (mp-units-style quantities are a separate habit);
- float finiteness (a candidate refinement from *faults* §7.4).

### 7.4 Which nudges ship

A nudge ships when its rule has been run on the corpus and the operator has
read its findings and the reasons a way past would carry. There is no
precision threshold.
- The findings table records what was run and what was read: projects, the
  count of true and false findings, and the labeller.
- A nudge whose false findings cannot be narrowed away is cut.

This round, `sm-guarded-field` and `adt-tagged-union` ship. Every other
nudge above is a candidate.

## 8. Testing

### 8.1 Located expectations

- **C++.** Clang `-verify` with the plugin loaded: `// expected-error
  {{…}}` at the exact line. Construct stops are checked the same way. Fix-its
  use `check_clang_tidy.py`-style expected output.
- **Rust.** ui tests (`//~` and `.stderr`) through the driver, plus
  `.fixed` files for machine-applicable fixes (*enc* §7).
- **Known defects.** Recorded beside the test as markers in the CodeQL
  style: `// verbs-SPURIOUS: <id>` and `// verbs-MISSING: <id>`.
  - Each is an open defect listed by `verbs habits check`.
  - Fixing the rule flips the marker into a failing test, so it gets
    removed.
- Every way-past path has tests:
  - honoured;
  - missing reason;
  - stale.

### 8.2 Seeded faults on corpora

- **A seed** is a source edit at a recorded site in a pinned corpus project,
  with the finding id it must produce and the line it must appear on. It
  lives in `habits/<name>/seeds/`. A seed that produces nothing, or a
  different id, is a missed seed: a bug.
- **Migration first.** Construct stops can only be seeded in code that uses
  the construct, and the corpus barely uses explicit machines or sum-type
  dispatch (*sm* B3, *adt* §3.0). Each habit therefore names a few corpus
  projects to migrate, by hand or by agent, before seeding:
  - **state machines:** leveldb, ninja (both flat, with data-dependent
    transitions that exercise guarded rows);
  - **ADTs:** solidity's variant dispatch;
  - **bounded types:** fprime, OSRM;
  - **Rust:** copies of oxcart's controller and salib under ignored
    `context/`. The operator approved this on 2026-11-23. The originals are
    never edited.
- **Seed shapes.** They come from the lanes' tables: *faults* §6, *sm* D,
  *adt* §4, *bnd* §6. Examples:
  - a direct state write;
  - a late-completion overwrite;
  - a catch-all arm;
  - an added alternative;
  - an unchecked door;
  - a narrowing out of a bounded type.
- **Unseeded runs.** Every nudge finding on unseeded, migrated code is read
  and labelled. Labels go into the findings table (§7.4).
- **A second oracle for runtime classes.** For bounded types and resources,
  a seeded fault that verbs misses is also run under ASan/UBSan or
  `-fsanitize=integer`. That separates "missed" from "missed and it
  matters" (*faults* §6).
- The existing corpus tooling (context/corpus/) carries over: tarballs as
  the source of truth, sandboxed configure, compile databases kept, and
  trees swept.

### 8.3 Constructs

- **Machine traces.** The machine's observer emits `(from, event, to)`. A
  test helper asserts that each record is a declared `go` row. That doubles
  as the oracle for behavioral seeds in migrated machines (*sm* A12).
- **Bounded arithmetic.** Fuzz against a wide-integer model: libFuzzer with
  ASan/UBSan in C++, a property test in Rust.
- **Mutation testing** of verbs' own checks: Mull, run on the fleet, never
  on the laptop (WORK.md verbs-b4x).

## 9. Layout

```
habits/<name>/            per §5.4
cpp/include/verbs/        shared C++ pieces: expect.hpp, names macro, plugin probe
cpp/tidy/                 the verbs-tidy module (all habits' checks register here)
rust/verbs/               the crate (constructs from every habit)
rust/verbs-driver/        the rustc driver
rust/cargo-verbs/         the cargo subcommand
tools/                    `verbs habits check`, corpus seeding (owned, C++ or Rust)
context/corpus/           corpus scripts and data, as today
```

Habit sources under `habits/<name>/cpp` and `habits/<name>/rust` are
compiled into the shared header tree, tidy module and crate. The builder
decides the build wiring.

Python is not used for new tooling. The October corpus scripts stay until
something replaces them.

## 10. What is left to the builder

- Build wiring: CMake presets that set `CMAKE_OSX_SYSROOT` from xcrun
  (post-mortem toolchain facts), and the cargo workspace layout.
- The nightly pin for the driver. Install `rustc-dev` for it; it is not
  installed yet.
- The probe in §6.4, and the C++ enumerator-name mechanism.
- Exact finding ids, messages, the minimum reason length, and fix
  applicability per finding.
- Measuring plugin overhead on blackbird's 257 units.

## 11. The habit queue (after the starters)

From *faults* §8.1, in order. Each is a WORK.md entry, not part of this
design:
1. **Strong identifiers and captured origin.** This has the field evidence
   that agents comply (*faults* §4.4). The C++ stop exists as
   `bugprone-easily-swappable-parameters`; Rust needs an owned one.
2. **Obligation tokens and owned resources:** a must-consume terminal and a
   child process that kills and reaps on drop.
3. Accumulation ("reaches a final state before drop") for state machines.
4. Sentinels and parallel optionals, once a co-write fact extractor exists.
