# C++ toolchain burdens under one pinned LLVM

Date: 2026-10-17. Host: macOS 26 (Darwin 25.6.0), Apple M4 Max, 16 cores,
128 GB. Toolchain studied: Homebrew `llvm` 23.1.2. Source read: llvm-project
23.1.2 release tarball in `quarantine/llvm-project/`. Every probe source lives
in the session scratchpad and none is in the repo. Line references are to the
quarantined source unless stated otherwise.

The stance under study: verbs builds and runs against one pinned LLVM on this
macOS arm64 host. Building everywhere is not a goal.

## Ranked burdens and recommended stances

1. **Homebrew clang 23 cannot compile a C++ file on this host without an
   explicit sysroot.** Homebrew's config files (`/opt/homebrew/etc/clang/
   arm64-apple-macosx26.cfg`) pass `-isysroot /Library/Developer/
   CommandLineTools/SDKs/MacOSX26.sdk`. The installed Command Line Tools are
   16.4 and contain only the 14.5 and 15.5 SDKs. Every `#include <vector>`
   fails with `mbstate_t` and `wcschr` errors. Passing `-isysroot $(xcrun
   --show-sdk-path)`, the Xcode MacOSX 26.2 SDK, fixes it, and CMake does this
   through `CMAKE_OSX_SYSROOT`. Blackbird already passes it.
   **Stance:** the verbs CMake presets always set `CMAKE_OSX_SYSROOT` to the
   Xcode SDK. Updating the CLT or writing `~/.config/clang/*.cfg` is a host
   change for the operator to decide.

2. **Patch-level drift from `brew upgrade`.** `llvm@23` is currently an alias
   of `llvm` (`brew info llvm`: "Aliases: llvm@23"), so no separate pinned
   formula exists yet. 23.1.3 is pending. Nothing is `brew pin`ned.
   `brew uses --installed llvm` lists rust, so upgrading rust can pull an LLVM
   upgrade. LLVM requires bug-fix releases to "maintain both API and ABI
   compatibility with the X.1.0 release" (`llvm/docs/HowToReleaseLLVM.rst:
   361-363`). The dylibs carry the minor in their names: `libLLVM.23.1.dylib`
   and `libclang-cpp.23.1.dylib`. So our tools, which link through
   `/opt/homebrew/opt/llvm/lib/...` (otool), should survive 23.1.x patch bumps.
   Two caveats:
   - clang-tidy's own docs say plugins carry no ABI or API promise and "must
     be compiled against the version of clang-tidy that will be loading the
     plugin" (`clang-tools-extra/docs/clang-tidy/Contributing.rst:756-757`).
   - Blackbird hard-requires exactly 23.1.2 (`blackbird/CMakeLists.txt:5-20`,
     `VERSION_EQUAL`), and its preset names the Cellar path
     `/opt/homebrew/Cellar/llvm/23.1.2/bin/clang++` (`CMakePresets.json:10`).
     A patch upgrade breaks Blackbird's configure.

   A major bump moves the `llvm` formula to 24 and breaks every plugin and
   tool we build.
   **Stance:** `brew pin llvm` now (operator action); record the exact version
   in the repo; link only through the `opt/llvm` path; rebuild every verbs
   binary after any LLVM change. Move to a real `llvm@23` versioned formula
   when Homebrew splits it out at the 24 release.

3. **Mull does not support LLVM 23, so mutation testing needs a second
   toolchain.** Mull 0.34.2 (CHANGELOG dated 17 Oct 2026) maps macOS to LLVM
   16-21 and Ubuntu 26.04 to 17-22 (`quarantine/mull/MODULE.bazel:132-170`).
   Mull runs as a compiler pass plugin (`-fpass-plugin=/usr/lib/
   mull-ir-frontend-18`, `docs/tutorials/CMakeIntegration.rst:40`). The code
   under mutation must therefore compile with the matching Clang major. On
   macOS it finds LLVM at `/opt/homebrew/opt/llvm@<N>`
   (`mull_available_llvm_versions.bzl`). Homebrew bottles exist for
   `llvm@21` (21.1.8) and `llvm@22` (22.1.8), about 1.6 GB each and not
   installed. Blackbird refuses any compiler but 23.1.2 or 23.1.4, so it
   cannot be mutated with Mull as things stand.
   **Options:**
   - (a) LLVM 22 plus Mull on the Ubuntu 26.04 fleet, with a mutation-only
     compiler profile in each corpus repo.
   - (b) Port Mull to 23. Its source-level LLVM version gates are few
     (`lib/JunkDetection/CXX/ASTStorage.cpp:12,15,85,93`,
     `CompilationDatabase.cpp:86`), but the API break between 22 and 23 is
     unknown until someone attempts a build on the fleet.
   - (c) Lower the verbs pin to 22. Rejected: the main corpus repo is on 23,
     and nothing else asks for 22.

   **Stance:** attempt (b) on the fleet first, because it keeps one compiler
   and Mull's version surface looks small. Fall back to (a). Mutants never run
   here (BLACKBIRD.md).

4. **Fast feedback inside clangd (tier 0) requires a custom clangd, which is
   cheap to build but must be configured.**
   - clangd cannot load modules at runtime. It instantiates whatever is in
     the statically linked `ClangTidyModuleRegistry`
     (`clangd/ParsedAST.cpp:572-574`, `TidyProvider.cpp:309-311`), and its
     tool has no `-load` option. Only clang-tidy pulls in
     `llvm/Support/PluginLoader.h` (`clang-tidy/tool/ClangTidyMain.cpp:25`).
   - Homebrew ships the pieces: `libclangdMain.a`, `libclangDaemon.a`,
     `libclangDaemonTweaks.a`, every `libclangTidy*.a`, the clang-tidy headers
     (452 headers, including `ClangTidyCheck.h`) and CMake targets for all of
     them. A 2-line `main` calling `clang::clangd::clangdMain` (mirroring
     `clangd/tool/ClangdToolMain.cpp:11-12`), linked with our module,
     `clangdMain`, `-force_load libclangDaemonTweaks.a`, `clangDaemon`,
     `clangTidy`, `clang-cpp` and `LLVM`, gives a 29 MB `verbs-clangd`.
   - The whole probe project builds in 10.5 s wall: a LibTooling tool, the
     tidy plugin and the custom clangd. No LLVM rebuild was needed.
   - Two burdens. First, clangd's default `FastCheckFilter` is `Strict`
     (`clangd/Config.h:113`), which drops checks missing from
     `TidyFastChecks.inc` (`TidyProvider.cpp:321-330`, `ParsedAST.cpp:
     577`). Our `verbs-*` checks ran only with `FastCheckFilter: Loose`
     (probe: Strict gave 0 diagnostics, Loose gave 2 `verbs-int-field`).
     Second, a clangd outside the LLVM bin layout logs "Failed to
     auto-detect resource directory". Pass `--resource-dir` or install it
     next to the LLVM layout.

   **Stance:** if tier 0 is wanted, build `verbs-clangd` against the pinned
   LLVM, and have repos that opt in add `FastCheckFilter: Loose` to their
   `.clangd`.

5. **Standalone LibTooling tools need the resource directory and C enabled in
   CMake.**
   - Without `-resource-dir=/opt/homebrew/opt/llvm/lib/clang/23`, a tool in
     our build directory fails on `'stdarg.h' file not found` (probe). Bake
     the path in at build time.
   - `find_package(Clang)` fails unless the project enables C:
     `FindLibEdit.cmake:28` uses `check_include_file`, and `AddLLVM.cmake:341,
     348` uses `check_linker_flag`, both of which need C. Use
     `project(... LANGUAGES C CXX)`.

6. **Visibility flags must match LLVM's.** Linking our objects against
   Homebrew's static clang-tidy libs produced dozens of `ld: warning: direct
   access ... weak symbol cannot be overridden at runtime`. Building with
   `-fvisibility-inlines-hidden`, as LLVM does (`HandleLLVMOptions.cmake:
   492-496`), removes all of them (probe: 0 warnings).
   **Stance:** add it to every target that links LLVM.

7. **Our tools must match LLVM's build settings.** Homebrew builds LLVM with
   RTTI ON and EH OFF (`LLVMConfig.cmake:286`; formula `-DLLVM_ENABLE_EH=OFF`),
   with dylib linking (`LLVM_LINK_LLVM_DYLIB ON`, `CLANG_LINK_CLANG_DYLIB ON`),
   with assertions OFF (`LLVMConfig.cmake:277`), and with two patches applied:
   a clang-cl triple fix and a macOS 27 SDK backport. The quarantined source
   is therefore close to, but not byte-identical with, what Homebrew built.
   Tools that link LLVM must not throw across LLVM frames, and nothing
   asserts if we misuse LLVM's APIs.

8. **libc++ headers and the dylib come from different releases.** Homebrew
   clang puts its own libc++ 23 headers first on the include path, but links
   `/usr/lib/libc++.1.dylib` by default (otool on probe binaries; Homebrew
   caveat: newer features need `-D_LIBCPP_DISABLE_AVAILABILITY`, or linking
   Homebrew libc++ with an rpath). With the system dylib, every C++23 probe
   compiled and ran. Linking `-L/opt/homebrew/opt/llvm/lib/c++
   -Wl,-rpath,...` also works.
   **Stance:** use the system dylib, and switch only when a needed library
   feature hits availability markup.

9. **compile-time FSM checks are bounded by constexpr step limits.**
   Defaults: 1,048,576 steps and depth 512 (`clang/include/clang/Basic/
   LangOptions.def:386-388`). A check_invariant-style BFS over a 3-event FSM
   gave these timings (probe):

   | States | Default limits | `-fconstexpr-steps=0` | new interpreter + steps=0 |
   |---|---|---|---|
   | 7.5k | ceiling (7468 passes, 7538 fails) | | |
   | 10k | | 2.4 s | 0.7 s (default steps) |
   | 100k | | 21.8 s | 5.4 s |
   | 1M | | 242 s | 50 s |

   The new interpreter is `-fexperimental-new-constant-interpreter`. The
   brief's 10⁴-10⁵ estimate holds only with raised limits, and costs seconds
   of compile time.
   **Stance:** put FSM checks in dedicated TUs with explicit step limits.
   Export to TLC above about 10⁵ states.

10. **No C++26 reflection in Clang 23, so `VERBS_ENUM` must spell out its
    values.** The status page lists P2996 as "No" (`clang/www/
    cxx_status.html:403-405`). `-freflection` is cc1-only
    (`clang/include/clang/Options/Options.td:4012-4016`), and `^^` accepts
    only builtin types (`clang/lib/Parse/ParseReflect.cpp:44-51`). The probe
    `^^Mode` gives "unknown or unimplemented reflectable entity", and libc++
    23 has no `<meta>`. magic_enum's reflection path needs
    `__cpp_impl_reflection` (`quarantine/magic_enum/include/magic_enum/
    magic_enum.hpp:54`), which Clang 23 does not define. For contrast,
    Homebrew GCC 16.2.0, which is installed, accepts
    `std::meta::enumerators_of(^^Mode)` with `[:e:]` splicing (probe).
    **Stance:** the `VERBS_ENUM` macro generates the value and name arrays
    itself. Reflection waits on a future Clang.

11. **The corpus repos use different toolchains.**
    - Blackbird matches the pin.
    - Oxcart is mostly Rust and Objective-C++, and builds with Apple clang.
    - BRepGPU is C++17, built on the Linux fleet with clang-18 and libstdc++,
      plus CUDA.

    Only Blackbird has a compilation database. The vlib types assume C++23,
    so they cannot go into BRepGPU or Oxcart's C++20 sources without raising
    those repos' standard. The lints can still run on them, because Clang 23
    parses C++17 and C++20 TUs.

12. **Disk space is low.** 70 GiB free of 1.8 TiB (97% used, `df`). The
    quarantined llvm-project is 2.5 GB plus a 179 MB archive. Each extra
    Homebrew LLVM costs about 1.6-1.9 GB.

13. **Not a burden: building LLVM from source.** Nothing probed required
    it: LibTooling, FlowSensitive, the tidy plugin, the custom clangd and
    FileCheck are all available from the bottle. It would only be needed for
    an LLVM with assertions enabled, or to test a Mull port outside the
    fleet. Build time was not measured, and disk (burden 12) is the binding
    constraint here.

## Evidence

### Pinning and packaging

- `brew info llvm`: 23.1.2 installed, stable 23.1.3, keg-only, alias
  `llvm@23`. `llvm@20` 20.1.8 is also installed. `brew list --pinned`
  printed nothing.
- `brew pin --help` exists ("preventing it from being upgraded when issuing
  the brew upgrade formula").
- The Homebrew formula, read with `brew cat llvm`, uses the same tarball
  URL and SHA-256 as our download. Its patches and CMake arguments are
  listed in burden 7.

### Development surface shipped by Homebrew

- CMake configs: `lib/cmake/{clang,llvm,mlir,polly}`.
- Headers: `include/clang/Analysis/FlowSensitive/*.h` (DataflowAnalysis.h,
  DataflowEnvironment.h, ...) and `include/clang-tidy/**` (452 headers).
- Libraries: `libclangAnalysisFlowSensitive.a`, `libclangAnalysis
  FlowSensitiveModels.a`, `libclang-cpp.23.1.dylib` (72 MB) and
  `libLLVM.23.1.dylib` (169 MB).
- `ClangTargets.cmake` exports clangTidy*, clangDaemon, clangdMain and
  clangDaemonTweaks.
- Installed test utilities: FileCheck, not, count, split-file. lit is not
  installed. clang-tidy's docs point out-of-tree check testing at llvm-lit
  and check_clang_tidy.py (`Contributing.rst:762-774`).

### Probe results

- **LibTooling** (`verbs-facts-probe`, AST matcher over integer fields):
  prints `field Door::mode : int` and `field Door::retries : unsigned int`.
  It links libclang-cpp.23.1, libLLVM.23.1 and the system libc++.
- **clang-tidy plugin:** `clang-tidy -load libVerbsTidy.so --checks=-*,verbs-*
  -list-checks` shows `verbs-int-field`. Run on the sample, it emits two
  `[verbs-int-field]` warnings. `clang-tidy --help` lists
  `--load=<pluginfilename>`. CMake reports LLVM_ENABLE_PLUGINS ON
  (`LLVMConfig.cmake:342`). The plugin was linked with
  `-undefined dynamic_lookup`.
- **Custom clangd over LSP:** didOpen with version 7 returned
  publishDiagnostics `version=7` with two `verbs-int-field` diagnostics.
  Stock clangd returned `version=7` with none. The client sent empty
  capabilities, so no `versionSupport` was advertised. clangd fills
  `version` from the document version it received
  (`ClangdLSPServer.cpp:1816`). It is serialized whenever present
  (`Protocol.cpp:796-797`), and nothing gates it on the client capability.
- **C++23 features:** `std::expected`, deducing `this`, `[[assume]]`, static
  `operator()`, `if consteval` and transient constexpr `std::vector` all
  compile and run with Apple clang 17 and with Homebrew clang 23 (once the
  sysroot is fixed). Apple clang 17 does not define
  `__cpp_explicit_this_parameter`, though it accepts the code. Homebrew clang
  23 defines it as 202110L.
- **Analyses** (Homebrew clang 23):
  - `-Wconsumed` flags "invalid invocation of method 'send' on object 'c'
    while it is in the 'consumed' state".
  - `-Wthread-safety` flags "calling function 'post_entry' requires holding
    authority 'ledger_write' exclusively" and "authority 'ledger_write' is
    still held at the end of function". This confirms `capability` works on
    a non-mutex type.
  - The same flag also flags "writing variable 'bal' requires holding mutex
    'a.mu'".
  - `-Wthread-safety-beta` adds local-variable alias resolution for
    capability expressions (`lib/Analysis/ThreadSafety.cpp:1700, 1789`;
    `docs/ThreadSafetyAnalysis.md:567-570`).
  - `-Werror=switch-enum` errors with "enumeration value 'Firing' not
    explicitly handled", even with a `default:`.
  - Apple clang 17 emits the same diagnostics.
  - Consumed tracks exactly three states: unknown, consumed, unconsumed
    (`clang/include/clang/Basic/Attr.td:4298-4300`).

### Corpus fit (read-only; nothing in these repos was built)

| Repo | Compiler | Standard | Build system | compile_commands.json |
|---|---|---|---|---|
| blackbird | Homebrew clang exactly 23.1.2 (macOS profile); 23.1.4 (`linux-llvm23` profile) | C++23 (`CMakeLists.txt:23`, set in 9e9dad5 today; `build/debug` db is c++23, older build dirs still c++20) | CMake 3.28+, presets, Ninja | Exported (`CMAKE_EXPORT_COMPILE_COMMANDS ON`); 25 build dirs, `build/debug` has 257 TUs |
| bow_shock (Oxcart) | Apple clang `/usr/bin/c++` (CMakeCache) | C++20 and ObjC++20 (`native/cef/CMakeLists.txt:3-6`) | CMake + Ninja via `scripts/build-native.py`; needs the CEF runtime acquired | Not exported, none present |
| BRepGPU | Unpinned; scripts use `/usr/bin/clang++-18` with libstdc++ and nvcc (Linux) | C++17 (`cxx_std_17`), CUDA 17 optional | CMake 3.28+ | None; no local build dir |

- Oxcart is mostly Rust: 203 `.rs` files on Rust 1.94.1, against 25 `.cc`
  and 37 `.mm` files.
- BRepGPU has 181 `.cpp`, 120 `.hpp` and 24 `.h` files.

### Edit-loop latency on Blackbird

This is input for the daemon decision. Nothing was written into Blackbird:
`git status` was unchanged. Stock clangd 23.1.2 ran with
`--background-index=false --compile-commands-dir=build/debug` and the repo's
`.clangd`, driven over stdio. The edit appends a function at the end of the
file. Cold clang-tidy used `-p build/debug`. There were 3 edits per file, one
run each, with a warm OS file cache.

| TU (size) | clangd cold open | clangd warm edit | warm edit, `--clang-tidy=false` | cold clang-tidy, trivial verbs check | cold clang-tidy, repo `.clang-tidy` |
|---|---|---|---|---|---|
| `src/coding.cpp` (273 KB) | 5.7 s | 2.4-2.7 s | 2.0-2.6 s | 3.8 s | 76.0 s |
| `src/terminal.cpp` (156 KB) | 4.4 s | 2.3-3.0 s | 1.2-1.6 s | 3.5 s | 40.8 s |
| `src/raw_provider.cpp` (16 KB) | 1.3 s | 0.54-0.58 s | 0.52-0.55 s | 1.4 s | 2.4 s |

The repo's `.clang-tidy` includes `clang-analyzer-*`. Reading the table:

- Warm clangd beats a cold per-TU clang-tidy by about 1.5× on large TUs,
  where reparsing the main file dominates, and about 2.5× on small ones.
- The repo's analyzer-heavy clang-tidy config is unusable in an edit loop
  for large TUs.
- Header edits, which force a preamble rebuild and fan out across TUs, were
  not measured.

To measure Oxcart and BRepGPU the same way, each needs a compilation
database. Oxcart: configure `native/cef` with
`-DCMAKE_EXPORT_COMPILE_COMMANDS=ON` after acquiring the CEF runtime.
BRepGPU: configure with export on and CUDA off, here or on the fleet. Either
step writes a build directory and runs that repo's configure, so I did not do
it.

## Acquisition

| Field | Value |
|---|---|
| Name | llvm-project 23.1.2 source release |
| URL | https://github.com/llvm/llvm-project/releases/download/llvmorg-23.1.2/llvm-project-23.1.2.src.tar.xz |
| License | Apache-2.0 WITH LLVM-exception |
| Archive | `quarantine/_archives/llvm-project-23.1.2.src.tar.xz`, 179,200,068 bytes |
| SHA-256 | `c98bbef08a2b4c2613cd50e9aa9ae7b69b1fe6c16b2c40373bc0ab6116fdf78a` (equals the Homebrew formula's) |
| Acquired | 2026-10-17 |
| Clean copy | `quarantine/llvm-project/`: 180,580 regular files, 2.5 GB. No nested `.git`. 19 symlinks omitted (clang driver test inputs and mlgo utils), per workspace practice; `.DS_Store` removed. |

Restore:

```sh
mkdir -p quarantine/_archives && cd quarantine/_archives
curl -fsSLO https://github.com/llvm/llvm-project/releases/download/llvmorg-23.1.2/llvm-project-23.1.2.src.tar.xz
echo "c98bbef08a2b4c2613cd50e9aa9ae7b69b1fe6c16b2c40373bc0ab6116fdf78a  llvm-project-23.1.2.src.tar.xz" | shasum -a 256 -c
cd .. && tar -xJf _archives/llvm-project-23.1.2.src.tar.xz && mv -f llvm-project-23.1.2.src llvm-project
find llvm-project -type l -delete; find llvm-project -name .DS_Store -delete
```
