# C++26-capable Clang: what owning one costs here — 2026-10-17

Question: verbs writes all C++ as C++26, and its analyses (LibTooling,
clang-tidy, TSA, Consumed, clangd) are Clang-only. Clang must therefore parse
every C++26 construct vlib uses. Upstream Clang, trunk included, has neither
P2996 reflection nor P2900 contracts (clang.llvm.org/cxx_status.html, read
2026-10-17). GCC 16 has both, but no Clang-based tool can read code that uses
them. This lane built and probed the candidates on this machine (Apple M4 Max,
16 cores, 128 GiB RAM, macOS 26.6, Xcode 26.2 SDK).

Working tree: `context/toolchain-cpp26/` (ignored). The build script is
`build-p2996.sh`, probes are in `probes/` and `probe-tools/`, and the
merge-conflict listings are `merge-conflicts-*.txt` and `merge-p2996-*.txt`.

## Recommendation

1. **Adopt bloomberg/clang-p2996 at `f17c8d6c7bfe` (2026-09-24) as verbs' only
   C++ compiler and tooling base.** That covers clang, clangd, clang-tidy,
   libc++ and LibTooling, built locally from one source tree with one script.
   - It is the only Clang that implements reflection, annotations, expansion
     statements, `define_aggregate` and consteval blocks.
   - Every verbs tool probed against it works on reflection-using code: a
     LibTooling matcher, a clang-tidy plugin loaded with `-load`, a custom
     clangd with a linked verbs check, `-Wthread-safety` and `-Wconsumed`.
   - Cost: 83 min for a full build, 1.0 GiB build directory, 638 MiB install,
     3.2 GiB sparse source checkout.
2. **Do not merge contracts into it.** Contracts live in efcs/llvm-project
   `contracts-review-20261009`, based on 2026-10-06 main (LLVM 24-dev). The
   fork is based on 2025-07-02 main (LLVM 21.0.0git), 59,939 commits behind.
   - Merging them conflicts in 106 files with 263 hunks, excluding lldb.
   - Four of those are add/add conflicts where upstream now has its own
     reflection and expansion-statement implementation.
   - That is a compiler-engineering project with an open-ended rebase burden,
     not a toolchain setup step.
   - verbs must not depend on P2900 syntax until one Clang carries both
     features. Its own invariant machinery covers that ground in the meantime.
3. **Code against the standard API names through a thin vlib shim.**
   - The fork's `<meta>` has the older two-argument `annotations_of(info,
     info)` and lacks the standard `annotations_of_with_type`; GCC 16.2 has
     only the standard names.
   - The fork also rejects one valid pattern that GCC accepts (below).
   - A shim of a few lines in vlib keeps the code portable to GCC 16 and to
     upstream Clang when they arrive, and lets the second compiler serve as a
     cross-check.
4. **Mull's position improves.** The fork's base, LLVM 21, is in Mull 0.34.2's
   supported macOS set (16–21). Building Mull against the fork is therefore a
   path change in Mull's Bazel LLVM discovery rather than an API port.
   - It still needs Bazel, which is absent here, and Mull's rules_rust
     toolchain download.
   - This lane did not build it.

## Costs

| Item | Measured |
| --- | --- |
| Blobless clone (fork + upstream main + efcs refs) | 2 min 40 s clone, +1 min upstream fetch; `.git` 1.4 GiB |
| Sparse checkout (llvm, clang, clang-tools-extra, libcxx, libcxxabi, libunwind, runtimes, cmake, third-party, libc) | 1 min 55 s; working tree plus `.git` 3.2 GiB |
| Full Release build plus install (Apple clang 17 host, AArch64 only, dylib, no tests) | **4,987 s (83 min)**, `rc=0` |
| Peak build directory (`du`, sampled every 30 s) | 1.0 GiB (1,070,224 KiB); free space 62→61 GiB during the build |
| Install tree | 638 MiB |
| Incremental: touch `clang/lib/Sema/SemaReflect.cpp`, rebuild plus install | 77 s (26 build/link steps) |
| No-op `ninja install` | 32 s |
| Probe tool project (LibTooling + tidy plugin + custom clangd) | 14 s |

Disk is not the constraint it looked like. The whole toolchain uses about
5 GiB. Free space was 57 GiB at the end, with other lanes also writing.

Rebuild cadence:
- The fork receives 1–7 commits a month: 49 since 2025-07-03, 6 in 2026-09.
  It has not merged upstream since 2025-07-02.
- Pulling the fork means an incremental rebuild: about 1–2 min when only `.cpp`
  files changed, up to a full 83 min when core AST headers change.
- No upstream rebase burden exists unless we choose to carry one.

## Evidence

### 1. Merge bases

`git merge-base <branch> upstream/main`. Upstream main tip at the time was
`50d155746d68` (2026-10-17, LLVM 24.0).

| Branch | Tip | Merge base | Commits ahead | Commits behind main | LLVM version |
| --- | --- | --- | --- | --- | --- |
| bloomberg `p2996` | `f17c8d6c7bfe` 2026-09-24 | `b1774222c761` 2025-07-02 | 442 | 59,939 | 21.0 |
| bloomberg `purpose` (default branch) | `2245df6e4a26` 2025-06-29 | itself | 0 | 603,109 | n/a (README branch) |
| efcs `contracts-review-20261009` | `2374ba6c978e` 2026-10-08 | `611f5f38c7e8` 2026-10-06 | 146 | 2,329 | 24.0 |
| efcs `contracts-nightly` | `1634b387b76f` 2026-02-11 | `5710e418c335` 2026-02-11 | 214 | 34,258 | n/a |
| efcs `contracts` | `acd41cd6cd20` 2024-07-06 | 2024-07-06 | 19 | 99,020 | n/a |
| efcs `eric-contracts` | `00aafdc5d7d2` 2024-10-14 | 2024-10-11 | 126 | 88,280 | n/a |
| efcs `contracts-main`, `contracts-base*` | base snapshots | itself | 0 | n/a | n/a |

The right contracts branch is `contracts-review-20261009`. It is the most
recent, based on current main, and is a review snapshot: its tip merges
`eric/r3-mod`. `contracts-nightly` is 8 months stale and the others are 2024
prototypes. Upstream has separate, independent contracts work open in
llvm/llvm-project: #221139 "[C++26] [Contracts] Initial parser support"
(ChuanqiXu9, open) and #229978 "Contracts Design Doc" (open). Upstream
reflection is landing piecemeal: #190356 "support std::meta::info for primitive
types" was merged 2026-10-02, and #232074 "Support reflecting arbitrary types and
aliases" is open.

### 2. What each branch implements

**p2996** (from its `P2996.md`, `clang/include/clang/Driver/Options.td:3594-3627`,
the `libcxx/include/meta` declarations, tests, and the probes below):
- **Reflection:** P2996 (all entities, all metafunctions) with
  `-std=c++26 -freflection`. `-freflection-latest` enables everything.
- **Annotations:** P3394, with `-fannotation-attributes` (in the tests'
  `RUN:` line), or `-freflection-latest`.
  - `<meta>` declares `annotations_of(info)`, `annotations_of(info, info)`,
    `is_annotation` and `annotate` (`meta:359-364`), but not
    `annotations_of_with_type`.
- **Expansion statements:** P1306, with `-fexpansion-statements`. The README
  says "expansions over constexpr ranges are not supported", but the
  `expand-range.cpp` probe (iterating a `static constexpr std::array`) compiled
  and ran correctly.
- **Code generation in the compiler:**
  - `define_aggregate` (`meta:168`), with the probe passing;
  - P3289 consteval blocks;
  - P3491 `define_static_{string,object,array}`.
- **Extensions:** P3096 parameter reflection, P3385 attribute reflection, and
  `define_enum` (P4033).
- **Library:** libc++ `<meta>` is installed with the fork.
- **Stated limits:**
  - "It has been our goal to provide a working compiler capable of building
    executables, but it has not been a non-goal [sic] to support the full
    family of features and tools offered by `clang` (e.g., AST output,
    `clang-tidy`, etc)". The next sentences make clear tooling is not a
    priority;
  - "DO NOT use this project to build any artifacts destined for production";
  - 85 open issues, many of them ICEs, including #275 "My code compiles but
    clangd crashes", #281 "Crash when iterating over annotations of
    ^^std::meta::info", and #262 "Annotations behavior is unstable with
    modules".

**contracts-review-20261009** (`git diff 611f5f38c7e8..2374ba6c978e`: 475
files, +37,335/−450):
- **Flags:**
  - `-fcontracts` (LangOpt `Contracts`, default off);
  - `-fcontract-evaluation-semantic=ignore|enforce|observe|quick_enforce`
    (default `enforce`);
  - a Clang extension, `-fcontract-group-evaluation-semantic=`, which takes
    per-group semantics through `[[clang::contract_group("a.b")]]`;
  - `-f[no-]contract-exceptions` (default on).
- **libc++:** `Cxx26Papers.csv` marks P2900R14 "|Partial|", meaning the
  library parts (`<contracts>`) are implemented.
- **Tooling:** it also touches ASTMatchers (with matchers registered),
  `Analysis/CFG.cpp`, LiveVariables, ReachableCode, and the static analyzer
  `ExprEngine`. This is material for verbs if contracts become available.
- It was not built; see §3.

### 3. Trial merges

Commands: `git merge-tree --write-tree --name-only`, then a real
`git merge efcs/contracts-review-20261009` in a throwaway worktree on
`origin/p2996`, counting `<<<<<<<` markers.

- **p2996 against 2026-10-06 main** (`contracts-base-20261006`): 106
  conflicting files.
- **p2996 against `contracts-review-20261009`:** 110 files, 273 hunks; 106
  files and 263 hunks excluding lldb. Contracts adds only 4 files to the fork's
  own forward-port conflicts: `AST/Stmt.h`, `AST/Decl.cpp`,
  `AST/StmtPrinter.cpp` and `Serialization/ASTWriterStmt.cpp`.
- **Largest hunk counts:** `ExprConstant.cpp` 16, `APValue.h` 11,
  `ItaniumMangle.cpp` 9, `Type.cpp` 8, `NestedNameSpecifier.cpp` 8, `Sema.h` 8,
  `ExprCXX.h` 8.
- **Add/add conflicts:** `clang/include/clang/AST/Reflection.h`,
  `clang/lib/Parse/ParseReflect.cpp`, `clang/lib/Sema/SemaExpand.cpp` and
  `clang/test/SemaCXX/cxx2c-expansion-stmts.cpp`.
  - Upstream created these files itself: `101f57538b5b` on 2026-10-02 for
    reflection, and the 2026-07/09 SemaExpand fixes.
  - So two implementations of the same features meet. That conflict is about
    meaning, not text.

The merge was not resolved. What it would take: forward-port 442 fork commits
across 15 months of upstream Clang AST/Sema churn, reconcile them with
upstream's partial reflection and expansion-statement implementations, then
repeat with every fork or contracts update. That is a standing
compiler-maintenance commitment.

### 4. Build

Script: `context/toolchain-cpp26/build-p2996.sh`.
- **Configuration:**
  - CMake: Release, Ninja, `LLVM_ENABLE_PROJECTS=clang;clang-tools-extra`,
    `LLVM_ENABLE_RUNTIMES=libcxx;libcxxabi;libunwind`,
    `LLVM_TARGETS_TO_BUILD=AArch64`, assertions off, tests, benchmarks and
    examples off, zstd and libxml2 off;
  - libraries: `LLVM_BUILD_LLVM_DYLIB` + `LLVM_LINK_LLVM_DYLIB` +
    `CLANG_LINK_CLANG_DYLIB`, matching Homebrew's layout;
  - sysroot: `CMAKE_OSX_SYSROOT` and `DEFAULT_SYSROOT` set to
    `xcrun --show-sdk-path`. Baking `DEFAULT_SYSROOT` makes the fork's clang
    compile with no `-isysroot` flag, which avoids the stale Command Line Tools
    SDK problem the Homebrew clang has.
- **Result:** `rc=0 wall=4987s`.
- **Installed:**
  - `clang++` reports
    `clang version 21.0.0git (https://github.com/bloomberg/clang-p2996.git f17c8d6c7bfef5e02ccadcf33517fd2a53b51b6e)`;
  - `clangd`, `clang-tidy`, `run-clang-tidy`;
  - `libclang-cpp.dylib`, `libLLVM-21git.dylib`, `libclangDaemon.a`,
    `libclangDaemonTweaks.a`, `libclangdMain.a`, the `include/clang-tidy/`
    headers, and libc++/libc++abi/libunwind with `<meta>`.
- **Settings:** LLVM is built with RTTI and exceptions off
  (`LLVMConfig.cmake:161,168`), unlike Homebrew's RTTI-on build. Out-of-tree
  tools need `-fno-rtti`.

### 5. Probes

Sources are in `context/toolchain-cpp26/probes/`. Language probes compile with
`-std=c++26 -freflection-latest` and link against the fork's own libc++
(`-nostdlib++ -L$I/lib -lc++ -Wl,-rpath,$I/lib`).

- **`enum.cpp`: enumerate a scoped enum with no hand-written list.**
  - Builds value and name arrays from `enumerators_of(^^Mode)` using
    `template for` over `define_static_array`.
  - Asserts at compile time that the size is 4 and that `Reserved = 200` is
    present (outside magic_enum's default range).
  - Run output: `Idle=0 Armed=1 Firing=2 Reserved=200`, exit 0.
- **`annot.cpp`: typed annotations on data members**
  (`[[=verbs::nondecreasing]]`, `[[=verbs::range{0, 100}]]`).
  - Namespace-scope `static_assert`s that count the annotated members and
    `extract` the `range{0,100}` value all pass on the fork.
  - A generic `check_nondecreasing<T>(before, after)` uses `template for` over
    the members and `if constexpr (!annotations_of(m, ^^T).empty())`. The fork
    rejects it: "constexpr if condition is not a constant expression … note:
    allocation performed here was not deallocated".
  - GCC 16.2 (`g++-16 -std=c++26 -freflection --sysroot=$(xcrun
    --show-sdk-path)`) accepts the same code with the standard
    `annotations_of_with_type` and prints `a->b 1, a->c 0`. The fork bug is
    that a temporary `vector` in an `if constexpr` condition is not treated as
    a transient allocation.
  - Workaround (`annot2.cpp`): wrap the test in a `consteval bool
    has_annotation(info, info)`. On the fork it then prints `a->b 1, a->c 0`,
    exit 0.
  - This is the mechanism for snapshotting only the annotated fields of an
    object generically, with no hand-written shadow fields.
- **`expand.cpp`:** a `template for` over an initializer list and over a
  tuple gives `sum=21`, exit 0. **`expand-range.cpp`:** a constexpr
  `std::array` range also works, exit 0, contrary to the README.
- **`define_aggregate.cpp`:** a consteval block defines `S{int x}`; the
  `static_assert` passes and the program runs, exit 0.
- **Analyses** (the previous lane's `tsa.cpp` and `consumed.cpp`, under
  `-std=c++26 -freflection-latest`):
  - `-Wthread-safety` reports "calling function 'post_entry' requires holding
    authority 'ledger_write' exclusively", "still held at the end of function"
    and "writing variable 'bal' requires holding mutex 'a.mu'";
  - `-Wconsumed` reports "invalid invocation of method 'send' on object 'c'
    while it is in the 'consumed' state".
- **Compile cost of `<meta>`:** warm `-fsyntax-only` takes 0.7–1.5 s on the
  fork, versus 0.5–1.1 s for a `<vector>`+`<string>` TU and 0.4–0.7 s for the
  same TU on Homebrew clang 23. Timings were noisy because the machine was
  shared.

**Tooling** (`context/toolchain-cpp26/probe-tools/`, the previous lane's
sources rebuilt with `-DClang_DIR=install-p2996/lib/cmake/clang`, `-fno-rtti`
added because the fork's LLVM has no RTTI, and `-fvisibility-inlines-hidden`):

- **LibTooling** (`verbs-facts-probe`, a `fieldDecl(hasType(isInteger()))`
  matcher):
  - Run through a compilation database (`probes/compile_commands.json`) over
    `annot2.cpp`, `enum.cpp`, `define_aggregate.cpp` and `expand.cpp`: 0
    errors, exit 0.
  - Reports `Ledger::seq/pct/plain` and `verbs::range::lo/hi`, plus `S::x`,
    the member created by `define_aggregate`.
  - Requires `-resource-dir install-p2996/lib/clang/21` in the database, as
    before; without it `stdarg.h` is not found.
  - Quirk: in the reflection-heavy TU, `Ledger`'s fields match about 7 times,
    once per traversal through instantiations and expansions. verbs-facts must
    deduplicate on the canonical declaration.
- **clang-tidy plugin:** `install-p2996/bin/clang-tidy -load
  probe-tools/build/libVerbsTidy.so -checks='-*,verbs-*' -p .` over the same 4
  TUs ran with exit 0 and reported `verbs-int-field` on `lo`, `hi`, `seq`,
  `pct`, `plain` (`annot2.cpp:9,13,14,15`) and on `x`
  (`define_aggregate.cpp:3:13`, the consteval block).
- **Custom clangd** (`verbs-clangd`, the module linked statically, `.clangd`
  with `FastCheckFilter: Loose`, `--resource-dir`):
  - Through `probes/lsp-open.py` it publishes the five `verbs-int-field`
    diagnostics on `annot2.cpp` (6.5 s cold open, `version=1`) and none on
    `enum.cpp`.
  - Discrepancy: on `define_aggregate.cpp` clangd published 0 diagnostics,
    while clang-tidy reported `x`. A field created by reflection is missed in
    clangd's tidy pass. Not root-caused.
  - The stock fork `clangd` reports the `annot.cpp` constant-expression error
    correctly as an LSP diagnostic and did not crash on any probe.

### 6. Contracts combination

Not built, because the merge in §3 is not clean.

### 7. Mull

- **Version fit:** Mull 0.34.2's matrix is macOS 16–21 and Ubuntu 26.04 17–22
  (`quarantine/mull/MODULE.bazel:130-170`). The fork is LLVM 21.0.0git from
  2025-07-02, just before the 21 release branch. Mull's version-specific code
  already handles `>= 21` and `> 21` (`lib/JunkDetection/CXX/ASTStorage.cpp:15,
  235-261`; `tools/mull-ir-frontend/mull-cxx-ir-frontend.cpp:3`).
- **Fork changes outside Clang:** only `llvm/include/llvm/ADT/Hashing.h` and
  `SmallVector.h`, 6 lines.
- **Expected break:** none at the LLVM API level.
- **Required change:** Mull discovers LLVM at a hard-coded
  `/opt/homebrew/opt/llvm@<ver>` with `llvm-config`
  (`mull_available_llvm_versions.bzl:6-9,17-21`). It must be pointed at
  `install-p2996` (`bin/llvm-config` exists).
- **Fit by design:** the mutating frontend has to be built against the fork,
  because Mull loads as a compiler plugin or AST frontend into the same Clang
  that parses the reflection code.
- **Build:** not attempted. Bazel is not installed, Homebrew changes were out
  of scope, and Mull pulls a Rust toolchain via rules_rust. This belongs on the
  fleet.

## Blockers and open items

- **Contracts:** not available in any Clang that also has reflection. Revisit
  when upstream contracts (#221139) or upstream reflection (#232074 and
  follow-ups) land in trunk.
- **Fork quality:** experimental, with 85 open issues and an explicit
  non-goal of supporting tidy or the AST printer. Expect ICEs, and prefer
  workarounds inside vlib, such as the consteval-helper pattern above, over
  patching the fork.
- **clangd gap:** clangd misses a reflection-defined field that clang-tidy
  reports. This needs root-causing before verbs depends on clangd-tier
  feedback for generated members.
- **Corpus repos:** BRepGPU and blackbird would need to build with this
  compiler to share verbs' parse; this lane did not touch them. GCC 16 also
  needs `--sysroot=$(xcrun --show-sdk-path)` here, the same stale-SDK issue.
