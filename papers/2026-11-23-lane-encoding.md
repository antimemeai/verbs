# Lane: encoding mechanisms in the field — 2026-11-23

Question: how do existing ecosystems let people encode rules about code, with
fixes and reasoned suppressions, and how do they test those rules? Which owned
mechanism would let verbs declare a habit once (construct, stops, nudges, a way
past with a reason, seeded tests) and realize it natively in C++ and Rust?

Toolchains probed: Homebrew LLVM 23.1.2 (`/opt/homebrew/Cellar/llvm/23.1.2`,
`-std=c++2c`, `-isysroot $(xcrun --show-sdk-path)`), Rust 1.99.0 (`b940084d7`)
with clippy 0.1.99, and nightly-2026-08-21 for unstable features. Note that
`/usr/bin/clang++` on this host is Apple clang 17. One early probe ran against
it by mistake and reported `clang::no_specializations` as unknown. Every
result below comes from the pinned binary, called by full path.

Probe sources are in `context/scratch-encoding/probes/` (ignored):
`cpp/`, `tidy/`, `plugin/`, `tidyplugin/`, `rust/` and `rt/`. Line references
into LLVM are to `quarantine/llvm-project/` (23.1.2). Line references into
clippy, Dylint, Error Prone and rustc are to the new quarantine copies listed
under "Acquisitions".

## Summary

- **Rust already has the way past verbs wants.**
  - `#[expect(lint, reason = "...")]` has been stable since 1.81
    (`rustc_feature/src/accepted.rs:288`). It reports
    `unfulfilled_lint_expectations` when the lint no longer fires.
  - Clippy's restriction lints `allow_attributes` and
    `allow_attributes_without_reason` force every outer suppression to be an
    `expect` with a reason.
  - Probed: a stale `#[expect]` printed "this lint expectation is unfulfilled
    … note: was four bools once".
  - Two gaps:
    - a module-level `#![allow(lint, reason = "...")]` silences a whole module
      and is never checked for staleness;
    - unfulfilled tool-lint expectations are reported only when that tool
      runs.
- **C++ has no native way past with a reason, so verbs must own one.**
  - clang-tidy's NOLINT stores no reason. The parser stops at `)`
    (`NoLintDirectiveHandler.cpp:139`).
  - Nothing reports a NOLINT that no longer suppresses anything.
  - NOLINT cannot suppress a check's error-level diagnostics
    (`NoLintDirectiveHandler.cpp:270`).
  - `#pragma clang diagnostic` carries no reason either.
  - A plugin-free marker, `[[clang::annotate("verbs.expect", habit, reason)]]`
    behind a macro, survives into the AST for clang, clang-tidy and clangd
    (probe `cpp/ann.cpp`). A verbs check can require its reason and report a
    stale marker. The plugin probe did exactly that.
- **In-language stops already cover misuse of a construct, in both
  languages, with good messages and no extra tooling.**
  - C++: `= delete("…")`, `static_assert` with a constexpr message, concept
    failure notes, `diagnose_if(…, "error")`,
    `[[clang::no_specializations("…")]]`, `[[nodiscard("…")]]`.
  - Rust: private constructors, sealed traits,
    `#[diagnostic::on_unimplemented]`, `#[must_use = "…"]`, `#[deprecated]`.
  - All of these travel with the library header or crate.
- **Code that bypasses or avoids the construct needs a semantic lint pass.**
  - C++: one `ClangTidyCheck` source ran unchanged in three hosts: clang-tidy
    (`-load`), the compiler (`-fplugin` with Homebrew's shipped
    `libclangTidyPlugin.a`), and, from the earlier lane, a custom clangd.
    Probed.
  - Rust: stable Rust offers no way for a library to ship such a lint. Clippy
    and Dylint both work as rustc drivers on `rustc_private` with a pinned
    nightly.
- **No ecosystem declares one semantic rule and realizes it in several
  languages.**
  - Semgrep and CodeQL are multi-language only in that they host many
    per-language rule sets.
  - Neither runs inside the compiler or linter loop agents already use.
- **Testing conventions converge on expectations written beside the code.**
  - Annotations next to the code: Clang `-verify`, clippy and rustc ui tests
    (`//~`), Semgrep `ruleid:`/`ok:`, Error Prone `// BUG: Diagnostic
    contains:`, CodeQL `// $ tag`.
  - Expected-output files for fixes.
  - A corpus diff over pinned projects: clippy `lintcheck`, Clang `SATest`.
  - Only CodeQL and Semgrep record known false findings and misses in the test
    file itself (`$ SPURIOUS:`/`$ MISSING:`, `todoruleid:`/`todook:`). That
    is the bookkeeping verbs' "false findings are defects" policy needs.

---

## 1. Rust: rustc's own lint and diagnostic machinery

### 1.1 Lint levels, `reason`, `#[expect]`

**What it is.**
- Lint levels are `allow`, `expect`, `warn`, `deny` and `forbid`. Each takes
  `reason = "…"`.
  - "This reason will be displayed as part of the lint message if the lint is
    emitted at the defined level" (Rust Reference, Diagnostics attributes,
    https://doc.rust-lang.org/reference/attributes/diagnostics.html, accessed
    2026-11-23).
- `#[expect(C)]` creates an expectation. If lint `C` would not have fired
  there, rustc emits `unfulfilled_lint_expectations` at the attribute (same
  page). Stabilized in 1.81 (`lint_reasons`, `accepted.rs:288`).
- Mechanics: `check_expectations` (`rustc_lint/src/expect.rs:28-58`)
  1. collects every expectation;
  2. steals the set of fulfilled expectation IDs from the diagnostic context;
  3. emits a lint for each unfulfilled one, carrying the reason as a note.
  - An `#[expect(clippy::x)]` is judged only when clippy runs, but not
    because of the tool filter. When clippy's lints are not registered,
    `check_lint_name` returns `MissingTool` and the level builder skips the
    attribute with `continue` (`rustc_lint/src/levels.rs:801-806`: "To
    detect this is the responsibility of the lint tool"). No expectation is
    ever recorded, so there is nothing to find unfulfilled. The tool filter at
    `expect.rs:52` serves rustdoc: rustc calls `check_expectations(None)`
    (`rustc_interface/src/passes.rs:1254`) and rustdoc calls
    `check_expectations(Some(sym::rustdoc))` (`src/librustdoc/core.rs:462`,
    both at `b940084d7`, fetched 2026-11-23). A side effect: a misspelled
    tool lint inside `expect` is also silent without the tool.
- Levels can also live in `Cargo.toml` `[lints]` / `[workspace.lints]`. The
  probe workspace set `clippy::struct_excessive_bools = "deny"` there.

**How it carries a habit.** This is the way past, complete, in Rust:
- a reason at the site;
- staleness noticed;
- the reason echoed in the diagnostic.

It applies to every lint verbs emits, whatever the host (rustc, clippy, or a
verbs driver).

**Evidence (probe `rust/`).**
- `#[expect(clippy::struct_excessive_bools, reason = "C ABI mirror of vendor
  struct")]` on a four-bool struct is silent.
- On a struct with no bools, the same attribute gives `warning: this lint
  expectation is unfulfilled … = note: was four bools once`.
- Plain `cargo build` does not report the unfulfilled clippy expectation. The
  tool filter is why.
- Precision and agent ergonomics: no measurement found.

**Costs and failure modes.**
- `reason` is optional unless a lint requires it (§1.3).
- An inner `#![allow(lint, reason = "...")]` on a module silences every item
  in it.
  - Clippy's `allow_attributes` deliberately ignores inner attributes
    ("This lint only warns outer attributes", `rust-clippy/clippy_lints/src/
    attrs/mod.rs:30-33`).
  - Probe: `pub mod quiet { #![allow(clippy::struct_excessive_bools, reason =
    "module-wide escape")] … }` silenced two structs with no finding.
- Other levers bypass all attributes: `RUSTFLAGS=-A…`, `--cap-lints`, and
  edits to `[lints]`.

### 1.2 Diagnostic attributes a library ships with its types

**What it is.**
- `#[must_use = "…"]` and `#[deprecated(note = "…")]`.
- `#[diagnostic::on_unimplemented(message, label, note)]` on a trait, with
  `{Self}` and generic-parameter interpolation. The diagnostic namespace has
  been stable since 1.78 (`accepted.rs:191`).
- `#[diagnostic::do_not_recommend]` on an impl, stable since 1.85
  (`accepted.rs:193`).
- Unknown `diagnostic::` attributes are accepted with at most a warning
  (Reference, same page). New ones can therefore be adopted without breaking
  older compilers.
- Unstable in 1.99 (`rustc_feature/src/unstable.rs:513-521`):
  `diagnostic_on_const`, `diagnostic_on_move`, `diagnostic_on_type_error`,
  `diagnostic_on_unknown`, `diagnostic_on_unmatched_args`.
  - `on_move` customizes the E0382 use-after-move error and shows in
    downstream crates (`tests/ui/diagnostic_namespace/on_move/
    error_is_shown_in_downstream_crates.stderr`).
- Sealed traits (a supertrait in a private module) and private fields are
  language idioms, not attributes. They stop outside code from implementing a
  trait or building a value without the checked constructor.

**How it carries a habit.** These are construct-level stops, shipped by the
library, on stable Rust:
- a sealed `State` trait with `on_unimplemented` turns "used a raw `u8` where
  a closed state set is required" into a type error the library words itself;
- `#[must_use]` turns "dropped a refinement result" into a warning;
- `#[deprecated(note)]` is a library-shipped nudge on stable. Downstream code
  sees a warning, and the way past is `#[expect(deprecated, reason = …)]`.
  This repurposes the attribute: it marks a discouraged API, not a removed
  one.

**Evidence (probe `rust/habitlib`, `rust/user`).**
- `transition(3u8)` printed:
  - `error[E0277]: `u8` is not a verbs state type`;
  - `= note: declare an enum and derive it with `verbs::states!`, do not
    implement State by hand`.
- `parse_mode("idle");` printed `unused return value … = note: a refinement
  failure must be handled`.
- The deprecated function printed its note.
- No study measures how agents respond to these messages. RustAssistant
  reports that an LLM–rustc loop fixes about 74% of real compile errors
  (papers/2026-10-17-literature-agent-feedback.md §2). That is about rustc
  errors in general, not these attributes.
- Checker: the nearest measured evidence on models answering static-analysis
  findings is already summarized in the same file.
  - Blyth et al. 2025: Bandit and Pylint findings fed back to GPT-4o. Over
    10 rounds, security issues fell from over 40% to 13%.
  - Dolcetti et al. 2024: with Infer's report, the best model fixed 39 of 44
    vulnerabilities.
  - CORE (FSE 2024): fixes that cleared the warning often changed behavior,
    so a ranker was needed.
  - None of these measures custom library diagnostics or how often agents
    choose suppression over a fix.
  - A 2026-11-23 search over the AIDev agentic-PR work (arXiv:2602.09185,
    MSR 2026) found no study of agents adding `#[allow]`, `NOLINT`, `noqa`
    or `eslint-disable`. Only anecdotes exist.

**Costs.**
- A type error stops compilation before late lint passes run. In the probe the
  E0277 hid every clippy finding until it was fixed. Stops and lints arrive in
  waves, not together.
- `on_unimplemented` works only on traits. The message can be gamed by an
  agent implementing the trait by hand; sealing prevents that.

### 1.3 Clippy

**What it is.**
- **Declaration.** `declare_clippy_lint!` (`declare_clippy_lint/src/
  lib.rs:153`) takes:
  - doc comments in a fixed shape ("What it does", "Why is this bad",
    "Example", "Use instead"), which become the lint website;
  - `#[clippy::version]`;
  - a name;
  - a category;
  - a one-line description.

  It expands to rustc's `declare_tool_lint!` (`rustc_lint_defs/src/
  lib.rs:734-771`), which builds a `&'static Lint` named `clippy::NAME` with a
  default level, plus a `LintInfo` record (category, explanation,
  `file!()#L`, version).
- **Default levels.** Category sets the default level: `correctness` is Deny;
  `suspicious`, `style`, `complexity` and `perf` are Warn; `pedantic`,
  `restriction`, `nursery` and `cargo` are Allow.
  `LintListBuilder::register` (`lib.rs:49`) registers the groups
  `clippy::all`, `clippy::pedantic` and so on.
- **Counts.** The 1.99 tree has about 830 `declare_clippy_lint!` uses:
  - 159 style, 145 pedantic, 144 complexity, 135 restriction;
  - 85 suspicious, 67 correctness, 52 nursery, 38 perf, 5 cargo.
- **Checking.** A lint is a `LateLintPass` (typed HIR) or `EarlyLintPass`
  (AST). Example: `ExcessiveBools::check_item`
  (`clippy_lints/src/excessive_bools.rs:148-170`) counts `bool` fields and
  exempts `#[repr]` structs and macro expansions (`:155-156`). Its threshold
  is the config value `max-struct-bools = 3` (`clippy_config/src/conf.rs:609`).
  It fires on *more than* three bools, so the three-bool struct in its own ui
  test is silent.
- **Fixes.** `span_lint_and_sugg` (`clippy_utils/src/diagnostics.rs:382`)
  attaches a suggestion with an `Applicability`
  (`rustc_lint_defs/src/lib.rs:62-82`):
  - `MachineApplicable`: applied by `cargo clippy --fix`;
  - `MaybeIncorrect`;
  - `HasPlaceholders`;
  - `Unspecified`.
- **Lints that are only configuration.**
  - `disallowed-methods`, `disallowed-types` and `disallowed-macros` in
    `clippy.toml` take `{ path, reason, replacement, allow-invalid }`
    (`clippy_config/src/types.rs:127-186`).
  - Probe: `String::len` banned with a reason and a replacement printed
    ``help: verbs probe: count graphemes, not bytes: `unicode_len` `` as a
    suggestion.
- **Lints about suppression.**
  - `allow_attributes` (restriction, `attrs/mod.rs:57`) reports outer
    `#[allow]` and pushes toward `#[expect]`.
  - `allow_attributes_without_reason` (restriction, `:80`) reports `allow`
    and `expect` without `reason`, inner and outer alike. In the probe a
    reasonless `#![allow]` was reported at `lib.rs:26`.
- **Tests: ui tests through the `ui_test` crate** (`tests/compile-test.rs:
  146-218`).
  - Each `tests/ui/X.rs` carries `//~ lint_name` or `//~^` annotations.
  - Expected output lives in `X.stderr`; rustfix output in `X.fixed`
    (`RustfixMode::Everything`, `:218`).
  - `require_annotations` makes every emitted diagnostic need an annotation
    (`:212-213`). It is on for the `ui`, `ui-internal` and `ui-toml` suites
    and off for `ui-cargo` (`:267, 286, 303, 332`).
  - `cargo uibless` rewrites the expected files.
  - There are 985 `.rs` files directly in `tests/ui/`, and 1,203 counting
    subdirectories (excluding `auxiliary/`).
- **Corpus testing: `lintcheck`** (`lintcheck/README.md`).
  - Runs clippy over pinned crate versions or git hashes and saves the warning
    log to diff between clippy versions.
  - `--fix` applies suggestions and reports any that leave the crate
    unbuildable.

**How it carries a habit.**
- Every part except the construct: stop (deny-level lint), nudge (warn-level
  lint), fix (suggestion with applicability), way past (rustc `expect` plus
  the two allow-attribute lints) and testing (ui tests, lintcheck).
- Config-only lints (`disallowed-*`) are a habit with no code at all: a path
  ban with a reason and a replacement.

**Evidence on precision.**
- These are issue counts, not rates.
  - GitHub search on 2026-11-23: `label:I-false-positive` returns 1,927
    issues, 552 open, out of 8,747 clippy issues.
  - `label:I-suggestion-causes-error` returns 954.
- The category system is itself a precision policy:
  - correctness lints, which deny by default, are meant to be "outright wrong"
    code;
  - pedantic and restriction lints are opt-in.
- Checker's addition: Li et al., "Unleashing the Power of Clippy in
  Real-World Rust Projects" (arXiv:2310.11738v1, 2023, ICSE 2024 poster;
  `papers/li-2023-unleashing-clippy-real-world-rust-arxiv.pdf`).
  - Clippy warnings average 21/KLOC across crates.io projects. The top lint
    accounts for over 50% of warnings and the top five for over 80% (§3.2).
  - Survey of 31 developers (§4): 68% configure lints at `warn` and 16% at
    `deny`. Respondents correctly identified what a warning meant 64% of the
    time overall, and 18% for `complexity` lints.
  - The authors say Clippy is often not made a CI gate "due to the high
    false positives and limited automated fixes" (§1).
  - It is a small survey with no measured precision.
- No agent-facing study.

**Costs.**
- Clippy is built in the rust-lang/rust tree and released with the toolchain.
  New lints go upstream or into a fork. There is no supported way to load
  third-party lints into clippy.

### 1.4 Dylint (out-of-tree Rust lints)

**What it is.** Trail of Bits' loader for lint libraries (README, quarantine
`dylint/` v6.4.0).
- **Library.** A Dylint library is a `cdylib` named
  `lib<NAME>@<TOOLCHAIN>.so`. It exports `dylint_version` and
  `register_lints(sess, lint_store)` and links `rustc_driver`
  (`docs/how_dylint_works.md`, "Library requirements").
- **Declaring lints.** Lints use `declare_late_lint!` / `impl_late_lint!`
  (`utils/linting/src/lib.rs:463,511`) and are written as `LateLintPass`,
  like clippy's.
- **Toolchain pin.** Each library pins a nightly with `rustc-dev`. The
  examples use `nightly-2026-08-20` with
  `components = ["llvm-tools-preview", "rustc-dev"]`
  (`examples/general/rust-toolchain.toml`). Dylint builds a driver per
  toolchain and runs the target crate with that toolchain ("Limitations").
- **Finding libraries.** A workspace names its lint libraries under
  `[workspace.metadata.dylint] libraries = [{ git/path, pattern }]`. Dylint
  fetches and builds them like dependencies. Per-library settings live in
  `dylint.toml`.
- **Unknown-lint warnings.** Lint names are unscoped. When Dylint runs, it
  passes `--cfg=dylint_lib="NAME"`, so code writes
  `#[cfg_attr(dylint_lib = "NAME", allow(LINT))]` to avoid `unknown_lints`
  warnings when Dylint is absent (README, "Conditional compilation").
  - Pre-expansion lints need `#[allow(unknown_lints)]`.
  - Cargo's check-cfg needs `cfg(dylint_lib, values(any()))`.
- **Tests.** `dylint_testing::ui_test` runs `compiletest_rs` over a `ui/`
  directory with `.stderr` files (`utils/testing/Cargo.toml:13`,
  `utils/testing/README.md`).

**How it carries a habit.** It is the only existing way for verbs to ship
Rust bypass and nudge lints without forking clippy. It is also the reference
design for an owned driver.

**Evidence.**
- Probe (`rt/c.rs`): `#[expect(three_bools, reason = …)]` on stable without
  Dylint gives `warning: unknown lint: three_bools`. The
  `cfg_attr(dylint_lib = …)` form is silent.
- No precision data.

**Costs.**
- A nightly plus `rustc-dev` per library. Neither is installed here:
  `rustup component list` shows no `rustc-dev` on any of the three local
  nightlies, and adding it is a host change.
- Rebuilds on each nightly bump. `rustc_private` APIs churn without notice.
- The expectation spelling `cfg_attr(dylint_lib = …, expect(…))` is clumsy
  for agents to write.
- Adopting Dylint means adopting a dependency: discuss with the operator
  first. Studying it is fine.

### 1.5 Tool names, `register_tool`, proc macros, Marker

- **Scoped lint names are reserved for predefined tools.** rustc predefines
  the tools `clippy`, `rustfmt`, `diagnostic`, `miri` and `rust_analyzer`
  (`rustc_resolve/src/macros.rs:123-124` at `b940084d7`, fetched 2026-11-23).
  - Probe (`rt/b.rs`): `#[expect(verbs::three_bools)]` on stable 1.99 is a
    hard error, `error[E0710]: unknown tool name `verbs` found in scoped
    lint` (`rustc_lint/src/diagnostics.rs:85`).
  - `#![feature(register_tool)] #![register_tool(verbs)]` is unstable
    (`unstable.rs:714`, tracking #66079). With it, `#[verbs::…]` attributes
    and `#[expect(verbs::…)]` compile silently on nightly (probe `rt/a.rs`).
  - So an owned driver's lints must use unscoped names, as Dylint's do.
    Otherwise every crate needs the nightly feature.
  - **Checker's addition: a driver can inject the tool itself.** Since the
    driver already runs on nightly, it can pass
    `-Zcrate-attr=feature(register_tool) -Zcrate-attr=register_tool(verbs)`
    together with `--cfg verbs`. Source then writes
    `#[cfg_attr(verbs, verbs::state_machine)]` and
    `#[cfg_attr(verbs, expect(verbs::three_bools, reason = "…"))]`.
    Probe (checker, `rustc` directly, no Cargo):
    - stable 1.99.0 without the cfg compiles silently;
    - stable with `--cfg verbs` gives E0433 and E0710;
    - nightly-2026-08-21 with the two `-Zcrate-attr` flags compiles
      silently.

    That keeps scoped `verbs::` names, and plain builds stay quiet. Two
    caveats:
    - Cargo passes `--check-cfg`, so crates must declare `cfg(verbs)` under
      `[lints.rust] unexpected_cfgs`, as Dylint documents for `dylint_lib`.
    - With the tool registered but no lint named `three_bools` registered,
      the expectation is silently dropped. `check_lint_name` returns
      `MissingTool` when no lint with that tool prefix is registered
      (`rustc_lint/src/context.rs:366-382`). Once the driver registers any
      `verbs::` lint, a misspelled name gets the unknown-lint suggestion
      instead. Only the driver that registers the lint can judge it.
- **Proc-macro attributes** (`#[verbs::state_machine] enum …`) run on stable.
  - They can reject the annotated item with `compile_error!`.
  - They see tokens only: no types, no other items.
  - Custom warnings from proc macros need `proc_macro::Diagnostic`, unstable
    as `proc_macro_diagnostic` (#54140, `library/proc_macro/src/
    diagnostic.rs:53` in installed rust-src).
  - So stable proc macros can stop but cannot nudge. They help only where the
    agent already chose the construct.
- **Marker** (rust-marker, a planned stable linting API) has been inactive
  since its last push on 2023-12-31 (https://github.com/rust-marker/marker,
  ecosystem index; accessed 2026-11-23). Do not plan on it.

### 1.6 Added by the checker: crate-author attributes, driver hook-up, editor surface

- **Clippy's "Attributes for Crate Authors"** (`rust-clippy/book/src/
  attribs.md`) are the stable Rust precedent for a library tagging its own
  items so an external linter treats them specially.
  - `#[clippy::has_significant_drop]` (since 1.60) marks a type whose `Drop`
    matters. `significant_drop_tightening` reads it
    (`clippy_lints/src/significant_drop_tightening.rs:139-175`).
  - `#[clippy::format_args]` (since 1.85) makes a library macro linted like
    `format!`.
  - Both compile on stable without clippy because `clippy` is a predefined
    tool. Clippy validates its own attribute names (`clippy_utils/src/
    attrs.rs:36-42`).
  - A `verbs::` marker gets the same treatment only through the
    `-Zcrate-attr` route in §1.5.
- **How a driver hooks into Cargo.** `cargo clippy` sets
  `RUSTC_WORKSPACE_WRAPPER` to `clippy-driver` (`rust-clippy/src/
  main.rs:118`). Dylint does the same (`dylint/dylint/src/lib.rs`). An owned
  verbs driver would take this route, so only workspace crates are linted,
  not dependencies.
- **Editor surface.** Dylint points rust-analyzer's
  `rust-analyzer.check.overrideCommand` at
  `cargo dylint --all -- --all-targets --message-format=json` (Dylint
  README, "VS Code integration", `:173-186`).
  - This replaces rust-analyzer's default check command, so clippy's
    findings drop out unless the driver also runs them.
  - This is the Rust counterpart of verbs-clangd and costs less: no custom
    language-server build.
  - Not probed.

---

## 2. C++: language and Clang mechanisms

### 2.1 In-language stops (no tool beyond the compiler)

All probed in `cpp/lang.cpp` and `cpp/bypass.cpp` on clang 23.1.2:

| Mechanism | Status | Probe output (abridged) | Can it be silenced? |
|---|---|---|---|
| `= delete("reason")` (P2573) | Clang 19 (`cxx_status.html:315`) | `call to deleted constructor of 'Bounded': raw int ingress is a bypass: use Bounded::make(v)…` | No |
| `static_assert(cond, constexpr-msg)` (P2741) | Clang 17 (`:254`) | `static assertion failed due to requirement '7 < 4': habit: use verbs::Mode` | No |
| Concept-constrained template | yes | `note: because 'NoKind' does not satisfy 'HasKind'` / `because 't.kind()' would be invalid` | No; the text is Clang's, not the library's |
| `[[nodiscard("reason")]]` | C++20 | `ignoring return value … : a refinement failure must be handled [-Wunused-result]` | Yes: `(void)` cast or `-Wno-unused-result`, no reason recorded |
| `[[deprecated("msg")]]` | C++14 | warning in `-Wdeprecated-declarations` | Yes: pragma or flag, no reason recorded |
| `__attribute__((diagnose_if(cond, msg, "error")))` | Clang | `error: value outside Bounded<0,100>` plus `note: from 'diagnose_if' attribute` | **No.** A plain error, `err_diagnose_if_succeeded` (`DiagnosticSemaKinds.td:5302`), in no group. `-Weverything` pragmas did not touch it |
| `diagnose_if(…, "warning")` | Clang | `warning: … [-Wuser-defined-warnings]` | Yes: `#pragma clang diagnostic ignored "-Wuser-defined-warnings"` silenced it |
| `diagnose_if(…, "error", "<group>")` | Clang 23 (4th arg, `Attr.td:3763-3778`) | error in that group | Yes, by group; the group must already exist in Clang (`SemaDeclAttr.cpp:922-933`, `err_diagnose_if_unknown_warning`) |
| `[[clang::no_specializations("msg")]]` | Clang (`Attr.td:3784`) | `error: 'is_habit' cannot be specialized: … [-Winvalid-specialization]` | Yes: `-Wno-invalid-specialization` or pragma (probe) |
| `[[clang::enforce_tcb("name")]]` | Clang (`Attr.td:5001`) | `warning: calling 'untrusted' is a violation of trusted computing base 'ingress' [-Wtcb-enforcement]` (printed twice) | Yes, by group |
| P2996 reflection, P3394 annotations | **No** in Clang 23 (`cxx_status.html:404-409`). Checker: GCC 16 lists P2996R13 (behind `-std=c++26 -freflection`), P3394R4 and P2900R14 contracts (https://gcc.gnu.org/gcc-16/changes.html, accessed 2026-11-23). Clang 23 also lacks P2900 contracts (`cxx_status.html:382-384`) | n/a | n/a |

**How it carries a habit.**
- These are the construct's own stops: misuse of the construct, ingress that
  bypasses the checked path, specializing a closed registry, dropping a
  result.
- They ship in the header and fire in every Clang-based host: compiler,
  clangd, clang-tidy.
- `diagnose_if` fires only when its condition is a constant at the call site.
  "If the condition provided to `diagnose_if` cannot be evaluated, no
  diagnostic will be emitted" (`AttrDocs.td:1404-1462`). It catches literal
  misuse, such as `set_mode("idle")`, not data-dependent misuse.

**Way past.**
- The error forms have none, which suits construct misuse.
- The grouped forms are silenced by pragma or flag, with no reason and no
  staleness check.
- A library cannot invent its own warning group: `diagnose_if`'s group must
  name an existing Clang group. So a library-shipped C++ diagnostic cannot be
  addressed by its own name.

**Precision.** These fire on exact language events, so a false finding means
the construct itself is wrong. No agent study.

**Costs.**
- Clang-only (GNU spelling for `diagnose_if`).
- Messages are fixed strings, but `static_assert`'s constexpr message can be
  computed.
- Concept failure notes are verbose and not under the library's control.

### 2.2 A precedent: `-Wunsafe-buffer-usage`

Clang's Safe Buffers model (`clang/docs/SafeBuffers.md:296-345`) has the same
shape as a verbs habit:
- a safe construct (`std::span`, hardened libc++);
- a warning on code that avoids it;
- `[[clang::unsafe_buffer_usage]]` to mark new sources of unsafety;
- a dedicated opt-out region, `#pragma clang unsafe_buffer_usage begin/end`.

The docs argue for that pragma over `#pragma clang diagnostic` because the
generic pragma "offers ways to suppress warnings without mentioning them by
name (such as `-Weverything`), which can make it difficult to determine at a
glance whether the warning is suppressed". The pragma still takes no reason.

### 2.3 clang-tidy

**What it is.**
- **Check API.** A check subclasses `ClangTidyCheck` (`ClangTidyCheck.h`) and
  overrides:
  - `registerMatchers(MatchFinder*)` (`:108`);
  - `check(const MatchResult&)` (`:112`);
  - optionally `registerPPCallbacks` (`:90`), `isLanguageVersionSupported`
    (`:68`) and `storeOptions` (`:132`).
- **Emitting.** It emits with `diag(Loc, "msg %0", Level)` (`:115`) and
  attaches `FixItHint`s.
- **Registration.** A module registers checks with
  `Factories.registerCheck<T>("name")` (`ClangTidyModule.h:59`) and is found
  through `llvm::Registry<ClangTidyModule>` (`:99`).
  - In 23.1.2, `ClangTidyModuleRegistry.h` is a deprecated stub that
    `#warning`s it will be removed in LLVM 24. Plugin source must follow
    header moves on each major release.
- **Declarative rewrite rules.** `TransformerClangTidyCheck`
  (`utils/TransformerClangTidyCheck.h:38`) takes a
  `RewriteRuleWith<std::string>` built from
  `makeRule(matcher, changeTo(cat(...)), cat("message"))`. Example:
  `abseil/StringFindStrContainsCheck.cpp:64-72`. A rule plus its fix plus its
  message is one expression.
- **Fixes.** `-fix`, `-fix-errors`, `-fix-notes` and `-export-fixes`
  (`tool/ClangTidyMain.cpp:186-306`). clangd offers fix-its as code actions.
- **Configuration.** `.clang-tidy` keys (`ClangTidyOptions.h`): `Checks`,
  `WarningsAsErrors` (`:74`), `HeaderFilterRegex` (`:86`), `SystemHeaders`
  (`:93`), `CheckOptions` (`:131`), `CustomChecks` (`:144`),
  `InheritParentConfig` (`:164`).
- **System headers.** In 23.1.2 the finder skips them unless `SystemHeaders`
  is set (`ClangTidy.cpp:451-452`).
- **NOLINT** (`NoLintDirectiveHandler.cpp`):
  - `NOLINT`, `NOLINTNEXTLINE`, `NOLINTBEGIN` and `NOLINTEND`, with an
    optional `(check-glob,…)`.
  - The scanner reads the check list up to `)` and ignores the rest of the
    line (`:139-145`). A reason after the parenthesis is allowed but never
    captured. The docs show `// NOLINT: Allow implicit conversion from
    `char`, because <some valid reason>` as plain text
    (`docs/clang-tidy/index.rst:541`).
  - Bare `NOLINT` suppresses every check (`:85`, `value_or("*")`).
  - Unmatched BEGIN/END pairs produce a `clang-tidy-nolint` error
    (`:181-197`).
  - Nothing reports a NOLINT that suppresses nothing. This has been
    requested upstream and remains open. llvm/llvm-project#69674 ("warn on
    unnecessary `NOLINT`", opened 2023-10-20) cites Rust's `#[expect]` as
    the precedent. #184034 ("Add `suspicious-nolint` check", opened
    2026-03-01, label check-request) asks for three options: forbid
    catch-all NOLINT, require explanatory text after it, and report a NOLINT
    that matches no diagnostic. An earlier patch, D41326, was never accepted.
    A clangd code action that inserts NOLINT (PR #188796) was closed without
    merging. Source: `gh api` on 2026-11-23.
  - `shouldSuppress` returns false for any diagnostic at Error level or above
    (`:270-271`).
- **Query-based custom checks** (`custom/QueryCheck.cpp`,
  `docs/clang-tidy/QueryBasedCustomChecks.rst`).
  - `.clang-tidy` `CustomChecks:` entries hold a clang-query `match …`
    string and per-binding messages at level `Warning` or `Note`.
  - They are registered as `custom-<name>`.
  - The docs list as non-goals "complex checks, performance, fix-its".
  - Experimental: the feature needs `--experimental-custom-checks`
    (`ClangTidyMain.cpp:351`).
- **Plugin loading.** `clang-tidy -load lib.so` (`ClangTidyMain.cpp:25`,
  `PluginLoader.h`). Tested upstream by `test/clang-tidy/CTTestTidyModule.cpp`.
- **Compiler plugin mode.** `plugin/ClangTidyPlugin.cpp` registers a frontend
  action named `clang-tidy` that runs the checks inside the compiler.
  - It reads `.clang-tidy` files through `FileOptionsProvider`.
  - It parses only `-checks=` from its own arguments (`:60-68`, "very
    limited").
  - Homebrew ships it as `lib/libclangTidyPlugin.a`.
- **Tests.**
  - `test/clang-tidy/check_clang_tidy.py` runs clang-tidy in fix mode, then
    FileCheck over `CHECK-MESSAGES`, `CHECK-FIXES` and `CHECK-NOTES` lines
    (`:108-110`). Its suffix options run variants.
  - FileCheck, `not`, `count` and `split-file` ship in Homebrew's `bin/`.
    `check_clang_tidy.py` and `lit` do not.

**Probes (`tidy/`, `tidyplugin/`).**
1. **Query custom checks.** A three-bool rule and a string-compare rule,
   written as `CustomChecks`, fired with `--experimental-custom-checks`.
   - `WarningsAsErrors: custom-three-bools` turned the first into
     `error: … [custom-three-bools,-warnings-as-errors]`.
   - **Without the flag, clang-tidy printed nothing and exited 0.** The
     configured checks vanish silently.
2. **NOLINT on promoted warnings.**
   - `// NOLINT(custom-three-bools): reason text…`, bare `// NOLINT`, and
     `// NOLINTNEXTLINE(...) because…` all suppressed a check listed in
     `WarningsAsErrors`. Suppression happens before promotion
     ("Suppressed 3 warnings (3 NOLINT)").
   - A NOLINT on a struct with no finding was silently accepted.
3. **One check, three hosts.** One `ClangTidyCheck` source
   (`tidyplugin/VerbsTidy.cpp`) built two ways:
   - **`-load` module** (`-undefined dynamic_lookup`, 210 KB). It ran under
     `clang-tidy -load` with its fix-it note.
   - **Compiler plugin.** The same source plus `-force_load
     libclangTidyPlugin.a`, `libclangTidy.a`, `libclangTidyUtils.a` and every
     `libclangTidy*Module.a` (736 KB, 3 s build). It ran via
     `clang++ -fplugin=… -Xclang -add-plugin -Xclang clang-tidy`.
   - In plugin mode the check's warnings print as compiler warnings, with the
     fix-it shown inline, and NOLINT is honored.
   - In plugin mode **`.clang-tidy` `WarningsAsErrors` is not applied, and
     `-Werror` does not promote the tidy warning.** The compile exited 0.
     (Reproduced by the checker. Cause, from source: in plugin mode the
     consumer forwards each diagnostic to the compiler's engine through
     `forwardDiagnostic`, which re-creates it with the legacy
     `getCustomDiagID(Level, fmt)` (`ClangTidyDiagnosticConsumer.cpp:457-
     460, 503-512`). The `IsWarningAsError` flag computed at `:451-452` is
     never consulted on that path. And a custom diagnostic with no group is
     mapped with `NoWarningAsError` set (`clang/lib/Basic/
     DiagnosticIDs.cpp:357-360`), so `-Werror` cannot promote it.)
   - Emitting at `DiagnosticIDs::Error` made the compile fail (exit 1), and
     NOLINT no longer suppressed it.
   - The earlier lane already showed the clangd host
     (papers/2026-10-17-cpp-toolchain-burdens.md §4): a 29 MB `verbs-clangd`
     with `FastCheckFilter: Loose`.
4. **Compile cost.** On a TU that includes `<vector> <string> <map>
   <algorithm> <memory> <variant>`:
   - plain compile: 0.26–0.27 s;
   - with the tidy plugin: 0.26–0.27 s;
   - standalone clang-tidy: 0.25–0.26 s;
   - a raw `RecursiveASTVisitor` plugin that walks system headers:
     0.33–0.34 s.

   This is one small TU. The earlier lane measured 1.4–3.8 s cold clang-tidy
   per unit on blackbird.

**How it carries a habit.**
- clang-tidy is the native C++ realization of bypass detection and nudges,
  with fixes. One check source serves the agent's three feedback points.
- Library-keyed checks exist upstream (the `abseil-*` module, for example),
  but they live in clang-tidy's tree, not the library's.
- Qt's clazy is the precedent for a library ecosystem shipping its own Clang
  plugin.
  - Invoked as
    `clang++ -Xclang -load -Xclang ClazyPlugin.so -Xclang -add-plugin -Xclang clazy`
    or as `clazy-standalone` over a compilation database.
  - Check levels 0–2; suppression via `// clazy:exclude=check` and
    `NOLINT(clazy-…)`; fixes exported as YAML
    (https://github.com/KDE/clazy README, accessed 2026-11-23).

**Precision evidence.**
- GitHub search on 2026-11-23: `label:clang-tidy label:false-positive`
  returns 390 issues, 154 open, of 2,716 clang-tidy issues.
- The 23.1.2 check list has 568 entries (including aliases); 237 offer fixes
  (`docs/clang-tidy/checks/list.rst`).
- No rates.

**Costs and failure modes.**
- Plugins carry no ABI promise and must be rebuilt for each LLVM (earlier
  lane).
- Headers move between majors (the registry header).
- Plugin mode ignores `WarningsAsErrors`.
- NOLINT can't be required to carry a reason, and verbs can't see it from
  inside a check. Suppression happens in the diagnostic consumer after
  `diag()` returns.
- Error-level check diagnostics escape NOLINT. That gives a stop no comment
  can silence, which is also a stop with no way past unless verbs provides
  one.

### 2.4 Clang plugins and custom attributes

**What it is.**
- **Tablegen attributes.** Built-in attributes are declared in
  `include/clang/Basic/Attr.td` and generated by tablegen. Adding one means
  rebuilding Clang.
- **Plugin attributes.** A plugin can add attributes through
  `ParsedAttrInfo` (`include/clang/Basic/ParsedAttrInfo.h:36-173`):
  - spellings;
  - `diagAppertainsToDecl` / `diagAppertainsToStmt`;
  - `handleDeclAttribute` / `handleStmtAttribute`.

  It registers with `ParsedAttrInfoRegistry::Add<…>`. By convention the
  handler attaches an `AnnotateAttr` (`clang/examples/Attribute/
  Attribute.cpp`).
- **Frontend actions.** A plugin can add a frontend action
  (`PluginASTAction`, `FrontendPluginRegistry::Add`) that runs before or after
  the main action (`getActionType()`, `docs/ClangPlugins.rst:198-205`).
- **Plugin diagnostics.** `getCustomDiagID(Level, fmt)` creates them. A
  `CustomDiagDesc` can name a group, but only one of Clang's existing groups
  (`DiagnosticIDs.h:202-214`).
- **Annotate.** `[[clang::annotate("str", args…)]]` (`Attr.td:1025`)
  attaches to declarations and, since it is
  `InheritableParamOrStmtAttr`, to statements (as `AttributedStmt`). Probe
  `cpp/ann.cpp`: `VERBS_EXPECT("three-bools", "C ABI mirror")` on a struct
  and on an `if` statement both appear as `AnnotateAttr "verbs.expect"` in
  `-ast-dump`, with no warnings and no plugin.
- **Suppress.** `[[clang::suppress]]` / `[[gsl::suppress("…")]]`
  (`Attr.td:3496`) exists, but "cannot be used to suppress traditional Clang
  warnings" (`AttrDocs.td:6632-6645`). Only the static analyzer honors it;
  clang-tidy has no reference to it.

**Probe (`plugin/VerbsPlugin.cpp`).** One dylib (2.9 MB, 3 s build against
`libclang-cpp`/`libLLVM`) holds:
1. a `[[verbs::expect(habit, reason)]]` attribute that rejects a reason
   shorter than 8 characters;
2. an after-main AST pass that stops on records with three or more bools;
3. a check that the expectation is used.

Run with `-fplugin=`:
- `Flags` gave `error: 3 bool fields move together; use a state enum or
  verbs::Flags [verbs-three-bools]`.
- `Wire`, marked with a reason, gave
  `note: accepted with reason: C ABI struct mirrored from vendor header`.
- `Lean`, marked but with nothing firing, gave
  `warning: unfulfilled [[verbs::expect("three-bools", ...)]]: nothing fires here any more; remove it`.
- `Short`, with reason "ok", gave an attribute error, and the struct's error
  still fired.
- A file-level `#pragma clang diagnostic ignored "-Weverything"` left all six
  errors in place: custom error IDs are in no group.

This is Rust's `#[expect(reason)]` built for C++, in about 90 lines.

**Two defects found along the way.**
1. **Scoped plugin attributes lose their arguments.**
   - `hasAttribute()` checks plugins with
     `Ptr->hasSpelling(Syntax, Name)` using the *unscoped* name
     (`lib/Basic/Attributes.cpp:72-77`).
   - A plugin spelling registered as `"verbs::expect"` therefore never
     matches. The parser then skips the argument list of an "unknown"
     attribute (`lib/Parse/ParseDeclCXX.cpp:4489-4497`), and the handler
     receives 0 arguments.
   - Upstream's own test uses arguments only with the GNU spelling and
     `[[plugin::example]]` only without arguments
     (`test/Frontend/plugin-attribute.cpp`).
   - Workaround in the probe: also register the unscoped spelling `"expect"`.
     That also makes `[[expect(...)]]` legal, an unwanted side effect.
2. **Hosts that do not load the plugin.**
   - Without the plugin the same file compiles with three
     `warning: unknown attribute 'verbs::expect' ignored`.
   - clangd strips every plugin from its compile
     (`clangd/Compiler.cpp:79-81`), so plugin attributes always warn there.
   - `[[clang::annotate]]` behind a macro avoids both problems.

**How it carries a habit.**
- A plugin can make a stop a true compiler error, beyond the reach of
  `-Wno-`, pragmas and NOLINT.
- It can own the way past, with a required reason and stale detection.
- It cannot reach clangd. A habit's checks are better written as tidy checks
  hosted by the plugin (§2.3 probe 3) than as a bespoke AST visitor.

**Costs.**
- The same ABI coupling as tidy plugins.
- Error IDs cannot be grouped or controlled by `-W` flags, so every policy
  knob is verbs' own.
- Ungrouped custom *warnings* also escape the usual flags. `-Werror` does not
  promote them (`NoWarningAsError` is set, `DiagnosticIDs.cpp:357-360`), and
  `-w` does not silence them (`:590-596`, with the FIXME "Should -w be
  ignored for custom warnings without a group?"). Checker probe: the plugin's
  `unfulfilled` warning printed unchanged under `-w`, `-Werror` and no
  flag. A plugin nudge at warning level therefore cannot fail a `-Werror`
  build. A nudge that must be answered has to be emitted as an error, or
  enforced by a separate verbs gate.
- Agents see unfamiliar plugin flags in build files, which are easy to
  delete. Removal of the plugin from the compile line has to be detected (the
  old tribunal's M2 list, papers/2026-10-17-tribunal-checks.md).

### 2.5 Clang `-verify` tests

- `clang -Xclang -verify` matches `// expected-error {{substring}}`,
  `expected-warning`, `expected-note`, `-re` variants, `@+N` offsets and
  `expected-no-diagnostics` against the diagnostics actually produced.
- `-verify=prefix` gives each run configuration its own comment prefix
  (`docs/InternalsManual.rst:3560-3600`).
- Probe (`cpp/verify.cpp`): a mislabeled seed reports both
  "expected but not seen" and "seen but not expected", with exit 1. Notes must
  be annotated too.
- This is the exact, compiler-native harness for in-language stops and for
  plugin diagnostics. Tidy checks run through `check_clang_tidy.py` /
  FileCheck instead. In plugin mode they are compiler diagnostics, so
  `-verify` covers them too. Not probed.
- Corpus harness precedent: the static analyzer's
  `clang/utils/analyzer/SATest*.py` with `projects/projects.json` (pinned git
  commits) and `CmpRuns.py`. It diffs reports against stored reference
  results.

### 2.6 Added by the checker: annotation-driven analyses built into Clang

The lane missed two Clang analyses that work like a habit's construct plus
stop. A library annotates its types, and the compiler checks every use with
no plugin.

**Thread Safety Analysis (`-Wthread-safety`).**
- Attributes: `capability`, `guarded_by`, `requires_capability`,
  `acquire_capability`, `release_capability` and others (`Attr.td:4102-
  4214`).
- Way past: `no_thread_safety_analysis` on a function (`Attr.td:4207`). It
  takes no reason.
- Checker probe (`-Wthread-safety`, 23.1.2): `++counter` without the lock
  printed `warning: writing variable 'counter' requires holding mutex 'm'
  exclusively [-Wthread-safety-analysis]`.
- **Precision evidence.** Hutchins, Ballman, Sutherland, "C/C++ Thread
  Safety Analysis", SCAM 2014, §VI
  (`papers/hutchins-2014-clang-thread-safety-analysis-scam.pdf`):
  - on by default for every C++ build at Google;
  - over 20,000 files carried more than 140,000 annotations, and adoption
    was voluntary;
  - "about 50% of the warnings produced by the analysis are caused not by
    incorrect code but rather by incorrect or missing annotations";
  - "Excluding cases in which the annotations were clearly wrong, the false
    positive rate is otherwise quite low: less than 5%". Most false
    positives come from aliasing, conditionally acquired mutexes, or
    initialization code.
  - The analysis is intraprocedural, so callers' requirements must be
    annotated (§II).
- Bearing on verbs: this is the strongest published precision evidence for
  a library-annotation-driven compile-time check. It also shows a
  construct's own annotations can be the main source of findings.

**Typestate (`-Wconsumed`).**
- Attributes: `consumable`, `callable_when`, `set_typestate`,
  `return_typestate`, `param_typestate` and `test_typestate`
  (`Attr.td:4292-4373`).
- Limit: the state set is fixed at `unknown`, `consumed` and `unconsumed`
  (`:4298-4300`, `:4332`).
- Checker probe on a `Conn` with `open`, `send` and `close`, with
  `-Wconsumed`:
  - `send` before `open` and `send` after `close` both printed `invalid
    invocation of method 'send' on object 'c' while it is in the 'consumed'
    state [-Wconsumed]`;
  - after `if (b) c.open();` it printed "… in the 'unknown' state";
  - without the flag nothing printed.
- Bearing on verbs: this is a native, if tiny, state-machine habit for
  open/closed or moved-from protocols. It cannot express a protocol with
  more than two named states. No precision data found.

**A header can switch these on.** Checker probe: `conn.h` began with an
unpopped `#pragma clang diagnostic error "-Wconsumed"`.
- A misuse in the including file became
  `error: … [-Werror,-Wconsumed]`, exit 1, with no build-flag change.
- The includer can turn it off again with `#pragma clang diagnostic ignored
  "-Wconsumed"`, which carries no reason.
- The pragma also leaks to every line after the include.
- So a library can ship "this analysis is on, as an error" in its header.
  verbs would have to treat the opposing pragma as a finding (§2.3 already
  says this of `#pragma clang diagnostic`).

---

## 3. Error Prone (Java)

**What it is.**
- **Declaration.** A check is a class annotated `@BugPattern`
  (`annotation/src/main/java/com/google/errorprone/BugPattern.java`) with:
  - `name` (`:100`, used in `@SuppressWarnings` and messages);
  - `summary` (`:140`), `explanation`, `severity` (ERROR/WARNING/SUGGESTION,
    `:150`), `tags`, `linkType`;
  - `disableable` (`:161`);
  - `suppressionAnnotations` (`:172`; default `SuppressWarnings`, empty means
    unsuppressible);
  - `documentSuppression` (`:181`).
- **Checking.** The class extends `BugChecker` and implements matcher
  interfaces, e.g. `MethodInvocationTreeMatcher`, over javac trees. It
  returns a `Description` with a `SuggestedFix`: `replace`, `prefixWith`,
  `addImport` and so on (`check_api/.../fixes/SuggestedFix.java:182-338`).
- **Running.** Errors are javac errors. Google ran checks in "patch mode"
  over the whole codebase to apply fixes *before* turning a check on as an
  error (Aftandilian & Sauciuc, SCAM 2012, §IV-C;
  `papers/aftandilian-2012-error-prone-extensible-java-compiler-scam.pdf`).
- **Refaster** expresses a rewrite as two Java methods, `@BeforeTemplate`
  and `@AfterTemplate` (`core/.../refaster/annotation/BeforeTemplate.java`).
- **Plugins** are found via `ServiceLoader.load(BugChecker.class)` on the
  processor path (`check_api/.../ErrorPronePlugins.java:45`).
- **Library-shipped rules.** The annotations jar (`annotations/`) lets a
  library mark its own API, and Error Prone's built-in checks enforce the
  marks: `@MustBeClosed`, `@CheckReturnValue`, `@DoNotCall`, `@Immutable`,
  `@InlineMe`, `@RestrictedApi` and others.
  - `@RestrictedApi(explanation, link, allowedOnPath,
    allowlistAnnotations, allowlistWithWarningAnnotations)`
    (`RestrictedApi.java:102-133`) makes every call an error unless the
    caller carries an allowlist annotation that the *library* defines.
  - The Javadoc example's allowlist annotation has `reviewer()` and
    `comments()` fields. So the way past is a typed annotation with a reason
    field, specific to one API. A second, "with warning" annotation is meant
    to "allow existing call sites until they are refactored, while
    prohibiting new call-sites" (`RestrictedApi.java` Javadoc).
  - Checker's caveats. The fields belong to the library's annotation type.
    The checker only tests whether the annotation is present and never reads
    `reviewer` or `comments`. Grandfathering is policy, not mechanism:
    nothing stops new code from carrying the legacy annotation. It only
    downgrades the error to a warning, and the Javadoc itself warns that
    "Too many warnings will lead to ALL warnings being ignored". v2.53.0
    also has `allowedPaths` (exact files or directory prefixes) next to the
    regex `allowedOnPath`.
- **Suppression with reasons.** `@SuppressWarnings` carries no reason. The
  check `SuppressWarningsWithoutExplanation`
  (`core/.../bugpatterns/SuppressWarningsWithoutExplanation.java`) asks for a
  comment within ±1 line of the suppression.
  - It is off by default (`DISABLED_CHECKS`,
    `BuiltInCheckerSuppliers.java:1239,1353`).
  - It covers only `deprecation`, `rawtypes` and `unchecked`, and says the
    Google style guide "mandates this for all suppressions; we're matching on
    a subset to start".
- **Tests.**
  - `CompilationTestHelper.addSourceLines(...)` with
    `// BUG: Diagnostic contains: <text>` on the line before the expected
    finding (`DiagnosticTestHelper.java:187-189`), or `expectNoDiagnostics()`.
  - `BugCheckerRefactoringTestHelper.addInputLines(...).addOutputLines(...)`
    with `TEXT_MATCH` / `AST_MATCH` for fixes (`:89-124, 235-300`).

**How it carries a habit.** Error Prone has the cleanest split between
library and checker:
- the library carries cheap marker annotations;
- one checker enforces them;
- the way past is a library-defined annotation that can require a reviewer
  and a comment.

The C++ analogue is `[[clang::annotate("verbs.restricted", …)]]` on the API,
plus an allowlist macro at call sites. The Rust analogue is a marker
attribute or trait read by a driver.

**Evidence.**
- Tricorder (Sadowski et al., ICSE 2015,
  `papers/sadowski-2015-tricorder-program-analysis-ecosystem-icse.pdf`):
  - compiler-error analyses must have essentially zero effective false
    positives (§II-C);
  - code-review analyses must stay under 10%. At ≥10% "not useful" an
    analyzer goes on probation; at >25% it may be turned off (§IV-E);
  - overall not-useful rate about 5%, under 4% without probationary
    analyzers (§V).
  - Effective false positive: "any report from the tool where a user chooses
    not to take action". "If an analysis incorrectly reports a bug, but
    making the suggested fix would improve code readability, this is not
    considered a false positive" (§II-A).
- Sadowski et al. 2018 (already in papers/) repeats these bars.
- No agent study.

**Costs.**
- Java only; ties to javac internals.
- Not a candidate host. It is a model for how to declare a check and how a
  library ships rules.

---

## 4. Semgrep

**What it is.**
- **Rules.** YAML rules (`id`, `pattern`/`patterns`, `pattern-not`,
  `pattern-inside`, `metavariable-*`, `message`, `severity`, `fix`) matched
  against a parsed syntax tree.
- **Tests.** `semgrep --test` reads annotation comments placed on the line
  before the target line:
  - `ruleid: <id>`: must fire;
  - `ok: <id>`: must not fire;
  - `todoruleid:` / `todook:`: known misses and false findings that do not
    fail the run.

  Autofix tests compare against `rule.fixed.<ext>`
  (https://docs.semgrep.dev/writing-rules/testing-rules, accessed
  2026-11-23).
- **Suppression.** `// nosemgrep` or `// nosemgrep: rule-id[, …]` on the
  first line of the match or the line before. The page documents no reason
  field; its examples show only rule ids. (This is the lane's reading, not a
  quotation; an earlier draft put it in quotation marks.) In the AppSec
  Platform a suppressed finding is still generated and set to "Ignored"
  (https://docs.semgrep.dev/ignoring-files-folders-code, accessed
  2026-11-23).
- **Reasons live in the platform, not the code.** Pull-request comment
  commands `/fp <REASON>`, `/ar <REASON>` and `/other <REASON>` triage a
  finding as Ignored with a reason category. `/other` needs no reason
  (https://docs.semgrep.dev/for-developers/resolve-findings-through-comments,
  accessed 2026-11-23).
- **Language support.** C/C++ and Rust are listed as "Generally available"
  for Semgrep Code, the commercial tier
  (https://docs.semgrep.dev/supported-languages, accessed 2026-11-23). The
  page says nothing about the open-source engine.

**How it carries a habit.**
- A cheap way to express syntactic nudges, such as "string compared against a
  literal", in both languages with one rule language.
- It runs outside the compiler and linter loop: a separate binary and a
  separate output channel.
- It does not instantiate templates or resolve overloads the way Clang does.

**Evidence.** No precision data for these languages was found.

**Costs.**
- An external engine (OCaml binary) would be a dependency, and the agent does
  not see its output unless verbs relays it.
- The test-annotation scheme, especially `todoruleid`/`todook`, is worth
  copying.

### 4b. Added by the checker: ast-grep

- **What it is.** An open-source structural matcher, MIT-licensed and written
  in Rust. It parses with tree-sitter and supports C, C++ and Rust among
  others. Rules are YAML with severity `error`, `warning`, `info`, `hint` or
  `off`. An `error` rule fails `ast-grep scan`.
- **Suppression.**
  - `// ast-grep-ignore` or `// ast-grep-ignore: rule-a, rule-b`, on the
    same line or the line before. No reason field.
  - **Unlike Semgrep, it reports unused suppressions**: "`unused-suppression`
    itself behaves like a `hint` rule with auto-fix". It is on by default
    only when all rules are enabled
    (https://ast-grep.github.io/guide/project/severity.html, accessed
    2026-11-23).
- **Tests.** `valid:` and `invalid:` lists per rule id, plus
  `__snapshots__` of the output. There is no known-false-positive marker
  like `todook` (https://ast-grep.github.io/guide/test-rule.html, accessed
  2026-11-23).
- **Bearing on verbs.** Same verdict as Semgrep: syntax only, outside the
  compile loop, an external binary. It shows that stale-suppression
  detection is cheap to add to a comment-based scheme. Not acquired.

## 5. CodeQL

**What it is.**
- **Queries.** QL queries with metadata in the header comment:
  - `@kind problem`, `@id`, `@problem.severity`;
  - `@precision` (very-high/high/medium/low; 21/109/91/36 of the C++ queries
    in the quarantined tree);
  - `@tags`.

  Example: `cpp/ql/src/Best Practices/Likely Errors/CommaBeforeMisleadingIndentation.ql:1-14`.
- **Suppression.** `AlertSuppression.ql` recognizes `// lgtm[...]` and
  `// codeql[query-id]` comments
  (`shared/util/codeql/util/suppression/AlertSuppression.qll:61-107`). No
  reason field.
- **Tests.**
  - A directory holds a `.qlref` naming the query, source files, and a
    `.expected` result table.
  - With `postprocess: utils/test/InlineExpectationsTestQuery.ql`, the
    expectations sit in the source as `// $ tag=value`.
  - Inline expectations support `$ SPURIOUS: tag` (a known false finding) and
    `$ MISSING: tag` (a known miss). When the analysis improves, they flip to
    "Fixed spurious result" / "Fixed missing result"
    (`shared/util/codeql/util/test/InlineExpectationsTest.qll:50-80`).
- **Library-keyed rules.** Libraries are modelled with "models as data"
  extension packs: library summaries added without changing queries (not
  examined this lane).

**How it carries a habit.** A powerful query language over a separate
extracted database. Too heavy and too far from the compile loop to host
verbs. Its known-defect markers are the best precedent for recording known
misses and false findings next to seeded faults.

**Costs.**
- Requires building the project under the CodeQL extractor.
- The CLI's licence restricts use outside open source and research (not
  re-verified this lane).
- A runtime dependency.

---

## 6. How a library ships its own checks: comparison

| Ecosystem | In-band (travels with the type) | Out-of-band (separate tool the user enables) | Way past the library can shape |
|---|---|---|---|
| C++/Clang | `= delete("…")`, `static_assert` message, concepts, `diagnose_if`, `no_specializations`, `nodiscard("…")`, `[[clang::annotate]]` markers for a checker to read; thread-safety and typestate attributes, which a header can switch on as errors by pragma (§2.6) | clang-tidy module (`-load`), compiler plugin (`-fplugin`), custom clangd; clazy is the precedent | Only through an owned checker that reads its own annotation; NOLINT and pragmas carry no reason |
| Rust | private ctors, sealed traits, `diagnostic::on_unimplemented`/`do_not_recommend`, `must_use`, `deprecated`, `const` asserts, proc-macro `compile_error!`, clippy crate-author attributes (`clippy::has_significant_drop`, `clippy::format_args`, §1.6) | clippy config (`disallowed-*` with reason/replacement), Dylint library via workspace metadata, owned rustc driver | `#[expect(lint, reason)]` natively; library-specific allowlist attributes need a driver |
| Java/Error Prone | annotations jar (`@RestrictedApi`, `@MustBeClosed`, `@CheckReturnValue`, …) | plugin checks via ServiceLoader | `@RestrictedApi` allowlist annotations defined by the library, with reviewer/comment fields |
| Semgrep | none | rule packs | `nosemgrep` without reason |
| CodeQL | models-as-data packs | query packs | `codeql[...]` without reason |

## 7. Testing conventions compared

| Harness | Expectation syntax | Fix check | Known false/missed findings | Corpus diff |
|---|---|---|---|---|
| Clang `-verify` | `// expected-error {{…}}`, `@+N`, `-re`, prefixes | n/a | none | SATest/CmpRuns (analyzer) |
| check_clang_tidy.py | `// CHECK-MESSAGES:`, `// CHECK-FIXES:` (FileCheck) | runs `-fix`, FileChecks result | none | none upstream (`run-clang-tidy` only) |
| ui_test (clippy) / compiletest_rs (Dylint, rustc) | `//~ lint`, `//~^`, `.stderr` | `.fixed` via rustfix | none | `lintcheck`, `lintcheck --fix` |
| Error Prone | `// BUG: Diagnostic contains:` | input/output lines | none | patch mode over the codebase (SCAM 2012 §IV-C) |
| Semgrep | `ruleid:`, `ok:` | `.fixed.<ext>` | `todoruleid:`, `todook:` | none |
| CodeQL | `// $ tag=value` | n/a | `$ SPURIOUS:`, `$ MISSING:` | none |

None of these seeds faults into real code. They all test on hand-written
cases. For seeded faults, Mull (quarantine) mutates code, not rules. A verbs
seed means "insert this bypass at a recorded site of a real corpus file and
expect finding X". That needs:
- an exact, located expectation, like `-verify` or ui_test;
- a known-defect marker, like `SPURIOUS`/`MISSING`;
- a corpus diff, like lintcheck or SATest.

No surveyed tool combines the three.

---

## What this means for verbs

Ranked options this lane opens. These are options, not the design.

1. **A habit as one declaration plus hand-written native parts, behind a
   shared contract.**
   - **The declaration** is data, not matchers. It holds:
     - the habit id and each finding's id;
     - tier (stop or nudge);
     - message and rationale, in clippy's "What / Why / Example / Use
       instead" shape;
     - the way-past rule (reason required; stale reported);
     - fix applicability, in Rust's four levels;
     - seed descriptions.

     It can generate diagnostic IDs and names, docs, test skeletons and the
     seed list.
   - **The native parts** are written per language:
     - C++: the construct with its in-language stops (§2.1); a clang-tidy
       check per finding (Transformer rules where a rewrite fits); hosted in
       clang-tidy, a compiler plugin and verbs-clangd.
     - Rust: the crate with sealed traits, `on_unimplemented` and
       `must_use`; lints in an owned driver or a Dylint library; clippy
       `disallowed-*` entries for plain path bans.
     - Checker's additions:
       - In C++, a construct can also lean on Clang's annotation analyses
         (thread safety, typestate; §2.6), switched on from its header.
       - In Rust, an owned nightly driver can register the `verbs` tool
         itself with `-Zcrate-attr`, so markers and expectations keep
         `verbs::` names behind `cfg_attr(verbs, …)` (§1.5). It surfaces
         in rust-analyzer through `check.overrideCommand` (§1.6).
   - **Why first:**
     - every host already exists and was probed;
     - adding a habit is one record plus checks and tests in each language,
       with no new machinery;
     - generating the matchers themselves from a shared language would be the
       parity layer the brief rules out (nothing in the field does it with
       semantic precision).
2. **A way past owned by verbs in C++, matching Rust's `expect`.**
   - The marker is `[[clang::annotate("verbs.expect", habit, reason)]]` behind
     a macro. It needs no plugin and is visible to every host. Statements and
     declarations can carry it; expressions cannot.
   - The checks consult it, require a reason, and report unfulfilled markers
     (the plugin probe shows the logic).
   - verbs also has to treat NOLINT, `#pragma clang diagnostic`, `-Wno-` and
     a removed plugin flag that touch verbs checks as findings of their own.
     clang-tidy gives no hook to see a NOLINT from inside the check.
   - Upstream has asked for the same since 2023 (llvm#69674, llvm#184034;
     §2.3), and neither request has been implemented. If one lands, NOLINT
     with a required reason and stale detection could replace part of the
     owned marker. Today it cannot.
   - In Rust, the native `#[expect(…, reason)]` plus `allow_attributes` and
     `allow_attributes_without_reason` cover the site. Inner `#![allow]` and
     `[lints]` edits need the same extra scrutiny.
3. **Library-defined allowlist markers for "this API is the bypass"**, on
   Error Prone's `@RestrictedApi` model.
   - The construct's escape hatches (raw ingress, unchecked casts) carry a
     marker.
   - Callers must carry a reasoned allowlist marker, or a "with warning"
     grandfather marker for existing code.
   - This fits stops on bypass better than per-lint expectations.
4. **Configuration-only habits for the cheap cases.**
   - clippy `disallowed-*` with reason and replacement, on stable today.
   - clang-tidy `CustomChecks`: experimental, warning or note only, no fixes,
     and silently a no-op without the flag. Usable only if verbs owns the
     invocation.
   - `diagnose_if` on construct APIs for literal misuse.
   - These lower the cost of a new nudge but cannot carry a fix or a reasoned
     way past by themselves.
5. **Opt-in construct macros that check themselves.** Rust proc-macro
   attributes and C++ `consteval`/`static_assert` over declared tables can
   stop on a malformed state machine or enum declaration on stable
   toolchains. They see only what the agent already marked, so they do
   nothing about the main failure: not using the construct at all.
6. **External rule engines (Semgrep, CodeQL): do not host verbs on them.**
   They sit outside the feedback loop, carry no reasoned suppression, and
   would add a dependency. Copy their test markers (`todoruleid`/`todook`,
   `SPURIOUS`/`MISSING`) and CodeQL's `@precision` field.

Testing, on the evidence above:
- `-verify` is the exact C++ oracle for compiler-hosted findings, ui_test
  for Rust.
- Corpus runs need a lintcheck/SATest-style pinned project list with stored
  results, plus a `--fix` pass that checks every machine-applicable fix still
  builds.
- Known misses and false findings should be recorded next to the seed as
  markers that flip when fixed. They should be treated as open defects, not
  tolerated.

## Open questions the design must settle

1. **Rust host.**
   - An owned rustc driver (nightly plus `rustc-dev`, a host change not yet
     made here) or Dylint (a dependency to discuss)?
   - Either way, lint names must be unscoped (E0710 on stable for `verbs::`).
     How will expectations avoid `unknown_lints` noise when the driver is not
     running: `cfg_attr(dylint_lib…)`-style gating, or always running the
     driver?
2. **What separates a stop from a nudge in a loop the agent cannot ignore.**
   - If nudges must be answered, both fail the agent's build until the code
     changes or a reason is recorded. The difference is then evidence and
     wording.
   - Does the difference also lie in what way past is accepted: any reason,
     a stronger reason, or an allowlist marker as in option 3?
3. **C++ stop channel.**
   - Error-level tidy diagnostics escape NOLINT, and plugin mode ignores
     `WarningsAsErrors`. Should stops be emitted at error level from the
     check, with verbs' annotation as the only way past?
   - What about plain clang-tidy runs and clangd, where they surface as tidy
     errors?
4. **Where the declaration lives and what it generates.** Docs, IDs, test
   skeletons and seeds are clearly generatable. Should fix templates be too?
   And how is the C++ check's message kept identical to the Rust lint's
   without a parity layer?
5. **Detecting changes to configuration and the command line.**
   - Changes that silence habits: `.clang-tidy`, `clippy.toml`, `[lints]`,
     `-fplugin` removed from flags, `RUSTFLAGS`, `--cap-lints`.
   - Is this a verbs check, a build-file diff, or both?
6. **Reason quality.** A length floor (the probe used 8 characters) is
   trivially gamed. Is the reason free text, a reference to a recorded
   decision, or a typed field (Error Prone's reviewer/comments)?
7. **Plugin attribute defect.** Report the `hasAttribute` unscoped-name
   mismatch upstream, or stay on `clang::annotate` and never depend on plugin
   attributes?
8. **Stale-reason scope.** Rust checks a tool's expectations only when that
   tool runs. C++ markers can be checked only by the verbs check. When is
   "stale" judged: every compile, or a dedicated pass?
9. **Construct-level type errors arrive before lint passes in Rust.** That
   ordering also exists in C++, where Sema errors come before tidy. Does
   feedback ordering matter for agents? No evidence either way.
10. **(Checker) Nudge channel in C++.** Ungrouped plugin warnings ignore
    `-Werror` and `-w` (§2.4), and tidy-in-plugin warnings ignore
    `WarningsAsErrors`. If a nudge must block until answered, is it emitted
    as an error, or does a verbs gate count warnings?
11. **(Checker) Library-enabled Clang analyses.** Should a construct header
    switch on `-Wconsumed` or `-Wthread-safety` as errors with an unpopped
    pragma? The pragma leaks to all following code, and its counter-pragma
    carries no reason.
12. **(Checker) Rust markers.** Use `cfg_attr(verbs, verbs::…)` plus
    `-Zcrate-attr=register_tool(verbs)` injected by the driver, or unscoped
    names gated on a cfg as in Dylint?

## Acquisitions

### Quarantine (new, `.git` and symlinks removed)

| Dir | Source | Version / commit | Licence | Size | Files |
|---|---|---|---|---|---|
| `quarantine/rust-clippy/` | https://github.com/rust-lang/rust-clippy | tag `rust-1.99.0`, `49e2f89a2605a9a340e04955fdbefa9803e6027a` | MIT OR Apache-2.0 | 26 MB | 4,595 (2 license symlinks in `rustc_tools_util/` deleted) |
| `quarantine/dylint/` | https://github.com/trailofbits/dylint | tag `v6.4.0`, `703f588db3e50ca3519bc9abea2eac2a9308a70d` | MIT OR Apache-2.0 | 5.5 MB | 471 |
| `quarantine/error-prone/` | https://github.com/google/error-prone | tag `v2.53.0`, commit `5c3574f9d796d44b95154b865d268f102104a015` | Apache-2.0 | 22 MB | 2,597 |
| `quarantine/rust-compiler-subset/` | https://github.com/rust-lang/rust | tag `1.99.0`, `b940084d7eb6a299eb4bfeb8e34901bc051e7ac4` (matches the installed rustc); sparse paths `compiler/rustc_lint`, `rustc_lint_defs`, `rustc_passes`, `rustc_attr_parsing`, `rustc_trait_selection/src/error_reporting/traits`, `rustc_feature`, `tests/ui/diagnostic_namespace`, `tests/ui/lint/rfc-2383-lint-reason`, `tests/ui/tool-attributes`, `src/doc/unstable-book/src/language-features` | MIT OR Apache-2.0 | 9.5 MB | 1,221 |

Restore commands:

```sh
cd quarantine
git -c advice.detachedHead=false clone -q --depth 1 --branch rust-1.99.0 https://github.com/rust-lang/rust-clippy rust-clippy && rm -rf rust-clippy/.git && find rust-clippy -type l -delete
git -c advice.detachedHead=false clone -q --depth 1 --branch v6.4.0 https://github.com/trailofbits/dylint dylint && rm -rf dylint/.git
git -c advice.detachedHead=false clone -q --depth 1 --branch v2.53.0 https://github.com/google/error-prone error-prone && rm -rf error-prone/.git
git -c advice.detachedHead=false clone -q --depth 1 --filter=blob:none --sparse --branch 1.99.0 https://github.com/rust-lang/rust rust-compiler-subset \
  && (cd rust-compiler-subset && git sparse-checkout set compiler/rustc_lint compiler/rustc_lint_defs compiler/rustc_passes compiler/rustc_attr_parsing compiler/rustc_trait_selection/src/error_reporting/traits compiler/rustc_feature tests/ui/diagnostic_namespace tests/ui/lint/rfc-2383-lint-reason tests/ui/tool-attributes src/doc/unstable-book/src/language-features) \
  && rm -rf rust-compiler-subset/.git
```

Also read, not kept: `compiler/rustc_resolve/src/macros.rs` at `b940084d7`
(raw.githubusercontent.com, 2026-11-23).

### Papers (gitignored PDFs)

- `papers/sadowski-2015-tricorder-program-analysis-ecosystem-icse.pdf`
  - Sadowski, van Gogh, Jaspan, Söderberg, Winter, "Tricorder: Building a
    Program Analysis Ecosystem", ICSE 2015.
  - Source: https://research.google.com/pubs/archive/43322.pdf.
  - SHA-256 `6dd64721e7174d9d8818dd32135290e82e83f407ad3ea49e2694bfe37f92c3c1`.
  - Read: §II, §IV-E, §V.
- `papers/aftandilian-2012-error-prone-extensible-java-compiler-scam.pdf`
  - Aftandilian & Sauciuc, "Building Useful Program Analysis Tools Using an
    Extensible Java Compiler", SCAM 2012.
  - Source: https://research.google.com/pubs/archive/38275.pdf.
  - SHA-256 `2c1e403686d9763eed4096717b37b8aff4f7f5e259f495ffebb72d5a36926b96`.
  - Read: §IV.
- `papers/hutchins-2014-clang-thread-safety-analysis-scam.pdf` (added by
  the checker)
  - Hutchins, Ballman, Sutherland, "C/C++ Thread Safety Analysis",
    SCAM 2014, DOI 10.1109/SCAM.2014.34.
  - Source: https://research.google.com/pubs/archive/42958.pdf.
  - SHA-256 `52363803cf635e981d6d3ad2b970cceddf1d701d12106b17a2a10b29275cfce3`.
  - Read: abstract, §II, §VI.
- `papers/li-2023-unleashing-clippy-real-world-rust-arxiv.pdf` (added by the
  checker)
  - Li, Yu, Wu, Carlig, Nie, Jiang, "Unleashing the Power of Clippy in
    Real-World Rust Projects", arXiv:2310.11738v1.
  - Source: https://arxiv.org/pdf/2310.11738v1.
  - SHA-256 `150b34d7f796f0e5dc380d6befd41cb3712761bd394b653aa6d101f85e535c0b`.
  - Read: abstract, §1, §3.2, §4.

### Not acquired (shopping list)

- RFC 2383, "Lint reasons": now read by the checker (see "Check").
- **The Semgrep open-source engine.** Not cloned: large OCaml tree, and
  syntax-only matching ruled it out as a host. Only its docs were read.
- **clazy source** (https://invent.kde.org/sdk/clazy), for how a library
  ecosystem's Clang plugin handles ABI pinning and suppression comments. Only
  the README was read.
- **`ui_test` crate source** (https://github.com/oli-obk/ui_test), the
  harness clippy uses. Only clippy's use of it was read.
- **Empirical studies of LLM agents responding to custom compiler
  diagnostics** (`on_unimplemented`, `= delete("…")`, `diagnose_if`). None
  found.

## Check (2026-11-23)

The checker opened the cited sources (quarantine trees at the versions
listed above, the pinned LLVM 23.1.2 tree, two downloaded PDFs, and web pages
dated below). Probes were rebuilt from `context/scratch-encoding/probes/`
in the checker's scratch directory and deleted afterwards.

### Verified

- **NOLINT.** The check-list parse stops at `)` (`NoLintDirectiveHandler.cpp:
  138-145`). Bare NOLINT means `*` (`:85-87`). Unmatched BEGIN/END gives
  `clang-tidy-nolint` (`:181-197`). `shouldSuppress` returns false at Error
  level and above (`:268-273`).
- **clang-tidy API and options.** The `ClangTidyCheck.h` hooks and `diag`
  default level, `registerCheck` (`ClangTidyModule.h:59`), the registry
  alias (`:99`), and the deprecated `ClangTidyModuleRegistry.h` stub with
  its LLVM 24 `#warning`. Also the `ClangTidyOptions.h` fields, the plugin's
  `-checks=`-only parsing (`ClangTidyPlugin.cpp:60-68`), the
  `--experimental-custom-checks` flag (`ClangTidyMain.cpp:351`),
  `SystemHeaders` (`ClangTidy.cpp:451-452`), and the Transformer example
  (`StringFindStrContainsCheck.cpp:64-72`).
- **Check counts.** 568 checks and 237 with fixes (`list.rst`).
- **Plugin attribute defect.** `hasAttribute` passes only the unscoped
  `Name` to `ParsedAttrInfo::hasSpelling` (`Attributes.cpp:72-77`). That
  compares against `NormalizedFullName` (`ParsedAttrInfo.h:102-105`),
  while Sema matches on the full scoped name (`ParsedAttr.cpp:119-126`).
  The parser skips the arguments of an "unknown" attribute
  (`ParseDeclCXX.cpp:4489-4497`). clangd clears plugins
  (`Compiler.cpp:79-81`). No upstream issue was found
  (`gh search issues`, 2026-11-23).
- **Attribute and status table.** The `Attr.td` lines for `diagnose_if`
  (4th argument), `no_specializations`, `enforce_tcb`, `annotate` (an
  `InheritableParamOrStmtAttr`) and `suppress`. Also
  `err_diagnose_if_succeeded` with no group, the existing-group check for
  `diagnose_if` (`SemaDeclAttr.cpp:922-933`), and the `diagnose_if` docs
  sentence (`AttrDocs.td:1432`). `cxx_status.html`: P2741 Clang 17, P2573
  Clang 19, P2996/P3394 "No". `clang::suppress` is honored only by the
  static analyzer (`BugSuppression.cpp`); clang-tidy has no reference to it.
- **Rust.** `accepted.rs` (lint_reasons 1.81, diagnostic_namespace 1.78,
  do_not_recommend 1.85), the unstable `diagnostic_on_*` features and
  `register_tool` (#66079), E0710 (`diagnostics.rs:85`), the predefined
  tools (`rustc_resolve/src/macros.rs:123-124`), and the `on_move`
  downstream test.
- **Clippy.** `allow_attributes` outer-only, `allow_attributes_without_reason`,
  `ExcessiveBools` (`:150-156`, `max-struct-bools = 3`), the
  three-bool struct silent in its own ui test, `span_lint_and_sugg`
  (`:382`), `DisallowedPath` fields, and the `lintcheck --fix` README.
  The category counts were recounted: 830 lints with the same split.
- **Dylint.** The toolchain pin, the `declare_late_lint!` and
  `impl_late_lint!` lines, the `cfg_attr(dylint_lib…)` and check-cfg advice,
  and `compiletest_rs`. v6.4.0 is the latest release (2026-11-10).
- **Error Prone.** The `BugPattern` members, the `RestrictedApi` members and
  Javadoc, `SuppressWarningsWithoutExplanation` (three warning names,
  disabled set), and the "mandates this for all suppressions" comment.
- **CodeQL.** The `SPURIOUS`/`MISSING` "Fixed …" messages, the `lgtm`/`codeql`
  suppression regexes, and `@precision` counts 21/109/91/36.
- **Tricorder (2015).** §II-A effective false positive and the readability
  exception. Build-breaking analyses need "essentially zero" effective false
  positives and less than 5% overhead (§II-C). Code-review analyses must
  stay under 10%, with probation at 10% or more and possible shutdown above
  25% (§IV-E). About 5% overall, under 4% without probation (§V).
- **Counts and project status.** `I-false-positive` 1,927 (552 open) and
  clang-tidy `false-positive` 390, rechecked with `gh api`. Marker's last
  push was 2023-12-31.
- **Probes reproduced.**
  - tidy plugin mode: `WarningsAsErrors` and `-Werror` were ignored (exit
    0). An error-level emission failed the compile and escaped NOLINT.
  - `CustomChecks` without `--experimental-custom-checks`: no output,
    exit 0.
  - VerbsPlugin: the stop, the reason note, the unfulfilled warning and the
    short-reason error.

### Corrected (old claim -> new claim, source)

1. "It filters by tool (`expect.rs:52`) … So an `#[expect(clippy::x)]` is
   judged only when clippy runs" -> the effect is right but the cause was
   wrong. Without clippy, `clippy::x` resolves to `MissingTool` and the
   attribute is skipped, so no expectation exists
   (`rustc_lint/src/levels.rs:801-806`, `context.rs:366-382`). The tool
   filter serves rustdoc (`rustc_interface/src/passes.rs:1254` passes
   `None`; `librustdoc/core.rs:462` passes `Some(rustdoc)`). (§1.1)
2. "There are 985 ui test files" -> 985 directly in `tests/ui/`, 1,203
   including subdirectories. `require_annotations` is on for ui, ui-internal
   and ui-toml and off for ui-cargo (`compile-test.rs:267-332`). (§1.3)
3. Semgrep: a sentence in quotation marks ("The doc does not describe a way
   to add a reason") read as a quotation of the docs -> marked as the lane's
   own reading. Added that reasons are captured only by PR-comment triage
   commands in the platform (`/fp <REASON>` etc.). (§4)
4. `@RestrictedApi` "grandfathers old call sites while blocking new ones" ->
   that is the Javadoc's intent. Mechanically the checker only tests whether
   the annotation is present, never reads `reviewer`/`comments`, and does
   not stop new code from carrying the legacy annotation. `allowedPaths`
   also exists. (§3)
5. Plugin-mode `-Werror` result: unexplained -> explained. Ungrouped custom
   diagnostics get `NoWarningAsError` (`DiagnosticIDs.cpp:357-360`), and
   the plugin path re-creates every tidy diagnostic as one
   (`ClangTidyDiagnosticConsumer.cpp:457-460, 503-512`). The same holds for
   any plugin warning, and `-w` cannot silence them either (`:590-596`).
   Probed. (§2.3, §2.4)

No other load-bearing claim was found wrong.

### Added

- **Rust: registering the tool from the driver.** An owned nightly driver
  can register `verbs` with `-Zcrate-attr`, so `cfg_attr(verbs, verbs::…)`
  markers and scoped expectations work while stable builds stay silent.
  Probed on 1.99.0 and nightly-2026-08-21. (§1.5)
- **Rust: crate authors, Cargo and the editor.** Clippy's "Attributes for
  Crate Authors" (`has_significant_drop`, `format_args`) as the stable
  precedent for library-tagged items. `RUSTC_WORKSPACE_WRAPPER` as the
  driver hook. rust-analyzer `check.overrideCommand` as the Rust editor
  surface. (§1.6)
- **C++ annotation analyses.** Clang Thread Safety Analysis and typestate
  (`-Wconsumed`), both probed, with Hutchins et al. 2014's deployment and
  precision figures: under 5% false positives excluding wrong annotations,
  and about 50% of warnings caused by wrong or missing annotations. A header
  can switch either analysis on as an error with an unpopped pragma
  (probed). (§2.6)
- **Upstream status of reasoned or stale NOLINT.** llvm#69674 and #184034
  are both open, D41326 was never accepted, and clangd PR #188796 was
  closed. (§2.3, option 2)
- **Reflection and contracts outside Clang.** GCC 16 ships P2996 (behind
  `-freflection`), P3394 and P2900; Clang 23 has none of the three.
  (§2.1 table)
- **ast-grep.** Reports unused suppressions, unlike Semgrep. (§4b)
- **Evidence.**
  - Li et al. 2023: Clippy survey and warning density (§1.3).
  - Agent-feedback studies already in `papers/` (§1.2).
  - No study of agents choosing suppression over a fix was found
    (AIDev/MSR 2026 search).
- **clang-tidy `--verify-config` does not cover custom checks.** In a
  checker probe it reported "check glob 'custom-*' doesn't match any known
  check" and exited 1, even with `--experimental-custom-checks`. It cannot
  guard query-based checks.
- **RFC 2383** (https://rust-lang.github.io/rfcs/2383-lint-reasons.html,
  accessed 2026-11-23).
  - Motivation: "the decisions are worth storing in the project directly
    with the settings they affect".
  - `expect` came from wanting "to know when safe to remove".
  - The RFC does not propose requiring reasons. Filling the `reason`
    parameter is explicitly out of scope.
  - So mandatory reasons in Rust come only from clippy's restriction lints.
- Three new open questions (10-12 above).
