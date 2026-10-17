# Reference implementations — 2026-10-17

Twenty-one references were acquired for the verbs preliminaries. They are study
material; verbs ships none of them. Each one is an immutable-revision GitHub
source ZIP kept intact in `quarantine/_archives/refimpls-2026-10-17/`, with a
clean copy extracted to `quarantine/<name>/`. Nothing acquired was built or run.
Paths below are relative to `quarantine/`.

The llvm-project source (clang-tidy, clangd, Thread Safety Analysis, Consumed,
FlowSensitive, `-verify`) belongs to the toolchain lane and is not covered here.

Archived instructions inside references (for example `mp-units/AGENTS.md`,
`mp-units/CLAUDE.md`) are historical reference, not instructions to us.

## Findings that bear on the brief

1. **bounded::integer is close prior art for vlib `Bounded` (brief §4.1), and
   it diverges from the brief in four places that need decisions.**
   - It takes `auto` non-type template parameters (`template<auto minimum, auto
     maximum>`). Its bounds can be signed or unsigned values up to 128 bits.
   - It computes bounds in modular `max_unsigned_t`, with an explicit
     `static_assert(..., "Overflow in calculation of bounds.")`. It does not rely
     on undefined behaviour making constant evaluation ill-formed, which is what
     the brief's sketch relies on. See `bounded-integer/source/bounded/arithmetic/plus.cpp`.
   - Assigning from a type whose range only overlaps is undefined behaviour:
     `operator=` calls `assume_in_range`, which reaches `std::unreachable()`
     (`source/bounded/integer.cpp`). The brief forbids implicit narrowing; this
     library permits it at runtime, unchecked.
   - Its stored value, `m_value`, is public, because C++20 structural types
     require this for use as a non-type template parameter. That is exactly the
     leak path the brief's `verbs-invariant-leak` lint would flag. vlib has to
     choose between NTTP-usability and encapsulation.
   - `value()` carries `[[assume(minimum <= m_value and m_value <= maximum)]]`.
     This is the brief's representation-gated `[[assume]]` (§2) in shipping code.
   - It is written as C++ modules, the README says it builds with Clang 22+, and
     storage selection is in `source/bounded/underlying_type_t.cpp`.
   - Testing: 485 `static_assert`s inline in the module sources serve as
     compile-time specification oracles, plus a few runtime tests in
     `source/bounded/test/`.
2. **Compile-fail oracles vary sharply in strength. vlib should use the strongest.**
   - GSL wraps negative cases in `#ifdef CONFIRM_COMPILATION_ERRORS`
     (`GSL/tests/notnull_tests.cpp`). CI never runs them, so there is no oracle.
   - sml marks failing targets `WILL_FAIL TRUE` (`sml/test/ft/errors/CMakeLists.txt`).
     Any failure passes, including an unrelated typo.
   - magic_enum's `test/check_compile_fail.cmake` requires the build to fail
     **and** the expected diagnostic text to appear in the output.
   - mp-units writes in-language negative tests, such as
     `requires !requires { typename Q<isq::length[m], bool>; }`
     (`mp-units/test/static/quantity_test.cpp`). These need no build harness,
     but they only cover rejections expressed through concepts.
   - Recommendation: use concept-rejection tests for API-shape claims (no
     raw-int ingress, widening-only conversion). Use an expected-diagnostic
     harness for `static_assert` messages; Clang's own `-verify` belongs to the
     toolchain lane.
3. **Specification-oracle tables.** Boost.SafeNumerics keeps hand-written
   pass/fail matrices for every operand-type pair (for example
   `safe_numerics/test/test_add_native_results.hpp`). It runs the same table at
   runtime and under `constexpr` (`test_*_constexpr.cpp`). That is a tier-7
   oracle on two execution paths. Its `trap_exception` policy
   (`include/boost/safe_numerics/exception_policies.hpp`) turns any operation
   that *could* fail at runtime into a compile error, which is the same idea as
   the brief's mechanism ladder.
4. **The brief's argument for `VERBS_ENUM` over magic_enum still holds, but it
   is now a dated argument.**
   - magic_enum's default scan range is still [-128, 127]
     (`magic_enum/include/magic_enum/magic_enum.hpp:120-129`).
   - magic_enum now selects C++26 standard reflection automatically when
     `__cpp_impl_reflection >= 202506L` and expansion statements are available
     (line 54). It then uses `std::meta::enumerators_of(^^E)` (line 338), which
     gives an exact, complete domain with no range limit.
   - Its CI exercises that path only on GCC 16 with `-freflection`
     (`.github/workflows/ubuntu.yml:66`).
   - Whether Clang 23 implements P2996 is a toolchain-lane question. If it does,
     `VERBS_ENUM` can generate its value array from reflection instead of
     duplicating it through a macro.
5. **Mull does not support LLVM 23.** `mull/MODULE.bazel` lists macOS LLVM
   16–21 and Ubuntu 26.04 LLVM 17–22. That conflicts with pinning LLVM 23 for
   the kill-criterion experiment (brief §10). Mutants run on the fleet anyway,
   so the corpus and vlib must also compile with the fleet's Mull-supported
   Clang (at most 22), or Mull must be ported.
   - Mull injects all mutants behind runtime flags in one binary, through
     `-fpass-plugin=mull-ir-frontend-N` (`docs/HowMullWorks.rst`).
   - It filters invalid mutants with Clang AST "junk detection"
     (`lib/JunkDetection/CXX/`).
   - It has an AST-level clang plugin frontend (`tools/mull-cxx-frontend/`).
   - Its git-diff incremental mode (`docs/IncrementalMutationTesting.rst`) is
     edit-local mutation testing.
6. **Out-of-tree clang-tidy plugins are a small, specific build.**
   - In `clang-tidy-plugin-examples/src/example/CMakeLists.txt`, each check is a
     CMake `MODULE` library built with `-fno-rtti`, including `clang-tidy/ClangTidyCheck.h`
     and the clang/LLVM include directories. It links no clang libraries;
     symbols resolve from the host `clang-tidy` at `--load` time.
   - Observation only, for the toolchain lane: Homebrew LLVM ships
     `/opt/homebrew/opt/llvm/include/clang-tidy/`.
   - The examples test with stub headers, input files and "expected" output
     files diffed after fix-it application (`src/replace_cglpath_by_std/testReplacePath.sh`).
   - include-what-you-use is the long-lived out-of-tree LibTooling exemplar.
     `master` tracks Clang main, and `clang_<N>` branches exist up to
     `clang_23` (checked through the GitHub API). Builds choose between
     `clang-cpp` dylib and static `clang*` libraries (`CMakeLists.txt:185-217`).
   - IWYU's test oracle is expected diagnostics written as source comments
     (`// IWYU: ...`, parsed in `iwyu_test_util.py:29`). That is the right shape
     for verbs lint tests.
7. **Daikon and Kvasir are the dynamic half of the brief's lints.**
   - `daikon/java/daikon/inv/unary/OneOf.java.jpp` (`dkconfig_size = 3`) is the
     dynamic enum-candidate.
   - `Range.java.jpp`, `Bound.java.jpp`, `NonZero` and `Modulus` are the bounded
     and refined candidates.
   - Justification is statistical: `Invariant.dkconfig_confidence_limit = .99`
     (`java/daikon/inv/Invariant.java:95`). This is a precedent for the brief's
     observation-versus-hypothesis split.
   - DynComp (`java/daikon/dcomp/`) is dynamic Lackwit, inferring abstract types
     from value interactions.
   - The C/C++ version is in `fjalar/valgrind/fjalar/kvasir/dyncomp_*.c` with
     `union_find.c`. It is directly relevant to `verbs-kind-discovery`.
   - Kvasir is a Valgrind tool and needs DWARF on Linux x86/amd64, so it cannot
     run on this macOS arm64 host. It is for study only.
   - Testing: goal-file regression suites in `daikon/tests/` (`daikon-tests`,
     `dyncomp-tests`, `kvasir-tests`).
8. **Glean's ownership-based incrementality is verbs' edit-invalidation design,
   already in production.**
   - Facts carry owning "units"; derived facts carry owner expressions; changed
     units hide their facts (`Glean/glean/website/docs/implementation/incrementality.md`,
     `glean/db/Glean/Query/Incremental.hs`).
   - Compare the brief's `preservation_dep` table and conservative invalidation
     (§8).
   - Glean's C++ indexer is a LibTooling tool (`glean/lang/clang/ast.cpp`,
     `index.cpp`), and its schema is `glean/schema/source/cxx.angle`.
   - Regression tests diff indexer output against goldens
     (`glean/lang/clang/tests/regression*`).
9. **CodeQL shows a complete C++ fact model.**
   - The schema is `codeql/cpp/ql/lib/semmlecode.cpp.dbscheme` (2,602 lines).
     Libraries are in `cpp/ql/lib/semmle/code/cpp/{controlflow,rangeanalysis,dataflow}`.
     Shared range analysis and SSA are in `shared/`.
   - `cpp/ql/test/query-tests/AlertSuppression/` is a suppression-handling
     precedent for the brief's agent-suppression rule.
   - CodeQL migrates schemas with `upgrades/` and `downgrades/` scripts; the
     brief's rule is delete-and-rebuild.
   - The C++ extractor is not open source; only the QL libraries are (MIT).
   - Tests are `.qlref` query references plus source files plus `.expected`
     result goldens.
10. **Soufflé fits the brief's SQL-shaped gap and enum queries.**
    - Datalog with provenance (`souffle/tests/provenance/`) explains why a fact
      was derived, which bears on how lint findings show their evidence.
    - Tests run every program in interpreted, compiled and compiled-split modes
      against expected CSV and stdout (`cmake/SouffleTests.cmake`). That is a
      differential model oracle between two engines.
11. **Trace validation (brief §4.7) has a reproducible production example.**
    - `etcd-raft` emits transition events only under a build tag
      (`state_trace.go` / `state_trace_nop.go`); `tla/Traceetcdraft.tla` is the
      trace spec checked by TLC.
    - `trace_validation_tools` provides Java tracing primitives, trace-spec
      templates and merge/check scripts.
    - `CommunityModules/modules/` supplies `Json`, `VectorClocks` and
      `TLCExt`-family modules that trace specs import.
    - vlib FSM tables could emit traces through a compiled-out hook in the same
      way.
12. **Type and state-machine design precedents:**
    - strong_type `affine_point` and `difference`
      (`strong_type/include/strong_type/affine_point.hpp`) separate point kinds
      from delta kinds. `verbs-kind-discovery` should be able to propose that
      split (timestamp/duration, index/offset).
    - type_safe `constrained_type::modify()` returns an RAII modifier that
      re-verifies on destruction (`type_safe/include/type_safe/constrained_type.hpp:205`).
      It is a bounded mutation window; check its exception-safety implications
      against the brief's unwind rules.
    - mp-units attaches range policies (`check_in_range`, `clamp_to_range`,
      `wrap_to_range`) to quantity-point origins
      (`src/core/include/mp-units/overflow_policies.h`). The invariant is scoped
      by type. `utility/constrained.h` is a policy-carrying wrapper comparable to
      `Refined`.
    - GSL `strict_not_null` (`include/gsl/pointers`) is the minimal refined
      pointer.
    - Boost.SML transition tables are types that can be visited at compile time
      (`sml/example/plant_uml.cpp`). They can be executed under `constexpr`
      (`test/ft/constexpr.cpp`), and `sml::testing` lets a test set the current
      state.
    - Boost.MSM's `back/mpl_graph_fsm_check.hpp` checks unreachable states and
      region orthogonality at compile time through template-metaprogramming
      graph search (`include/boost/msm/mpl_graph/`). It is the prior art for
      the brief's `consteval` BFS, but it checks graph structure only, not
      invariants over state.
    - SML guards are opaque callables, so a reachability check over an SML table
      must either abstract the guards or enumerate their outcomes.

Searches for C++23 refinement or contract libraries and for standalone
`constexpr` FSM verifiers found nothing substantial. The only hit was the
zero-star experiment `rvarago/cpp_refined`. The P2900 contracts
implementations live in compilers (toolchain lane).

## Per reference

| Reference | Study for verbs | Testing strategy |
| --- | --- | --- |
| bounded-integer | Range propagation (`source/bounded/arithmetic/*.cpp`), storage choice (`underlying_type_t.cpp`), `check_in_range` / `assume_in_range` / `clamp` ingress, `[[assume]]` in `value()`, the UB-on-overlap assignment (to reject) | Inline `static_assert` spec oracles; small runtime tests |
| type_safe | `constrained_type` with verifier policies (assertion/throwing), `modify()` re-verification, `strong_typedef` mixins, `flag_set`, `tagged_union` | Catch-based runtime tests in `test/` |
| safe_numerics | Interval arithmetic (`interval.hpp`), `checked_result`, `safe_range`, compile-time `trap_exception` | Result matrices run at runtime and constexpr |
| NamedType | Skills/CRTP strong typedef (`include/NamedType/underlying_functionalities.hpp`); a baseline | Catch tests |
| strong_type | Modifier-list strong types; `affine_point`/`difference`; `ordered_with`/`equality_with` cross-type relations | Catch tests plus `static_assert` type checks |
| mp-units | Type-level quantity propagation; `constrained.h`; overflow and range policies tied to origins; `requires !requires` negative tests | Large `test/static/` compile-time suite plus `test/runtime/` |
| magic_enum | Range limits and `__PRETTY_FUNCTION__` scan (to avoid); C++26 reflection path (`enumerators_of`) | Catch tests plus compile-fail with expected diagnostic text |
| GSL | `not_null`/`strict_not_null`, `Expects`/`Ensures`, `narrow` | gtest; death tests; untested `CONFIRM_COMPILATION_ERRORS` (anti-pattern) |
| sml | Transition table as type, compile-time table visiting, constexpr SM, testing policy, logging policy (trace emission hook) | Functional tests per feature; `WILL_FAIL` compile-fail |
| msm | `mpl_graph_fsm_check.hpp` compile-time reachability; `backmp11` modern back end | Boost test suite in `test/` |
| daikon | Invariant templates (`java/daikon/inv/`), confidence/justification, `OneOf`, DynComp, `.decls`/`.dtrace` formats | Goal-file regression suites in `tests/` |
| fjalar (Kvasir) | C/C++ dynamic front end; DynComp for C (`valgrind/fjalar/kvasir/dyncomp_*.c`, `union_find.c`) | `test-kvasir.sh`; Valgrind `.exp` goldens |
| mull | IR plus AST mutation, junk detection, single-binary mutant activation, git-diff incremental mode, LLVM version matrix | Unit, integration and end2end tests with expected reports (`tests/end2end/*expected*`) |
| include-what-you-use | Out-of-tree LibTooling build (`find_package(LLVM/Clang)`, dylib or static), `clang_<N>` release branches | Expected diagnostics as source comments (`iwyu_test_util.py`) |
| clang-tidy-plugin-examples | Minimal `--load` plugin build; fix-it check workflow | Stub plus input plus expected-after-fix-it diff scripts |
| souffle | Datalog evaluation for fact queries; provenance | Expected outputs across interpreted and compiled modes |
| Glean | Unit ownership incrementality; LibTooling C++ indexer; Angle schemas | Golden regression output; incremental tests |
| codeql (cpp, shared) | C++ dbscheme; guards, range analysis, dataflow; suppression query | `.qlref` plus `.expected` goldens |
| etcd-raft | Build-tag trace emission; TLA+ trace spec | TLC over recorded NDJSON traces |
| trace_validation_tools | Trace logging primitives, trace-spec templates, trace merge | Example traces checked by TLC |
| CommunityModules | Modules used by trace specs (`Json`, `VectorClocks`, `IOUtils`) | TLC-run module tests |

## Deferred or not acquired

- **Rust, deferred until R1:** Stateright, Kani, Dylint, bolero, loom, shuttle,
  salsa/rust-analyzer.
- **Not acquired:**
  - `tlaplus/tlaplus` (TLC itself; large, and needed only if trace validation
    proceeds).
  - Doop (points-to analysis in Soufflé; a large example of Datalog program
    analysis).
  - Bloomberg's `clang-p2996` fork (toolchain lane decides whether reflection
    matters).
  - IWYU's `clang_23` branch, which is the variant that builds against the
    pinned LLVM; acquire it if we study IWYU's build in detail.
- **Shopping item:** Lackwit's original source (O'Callahan & Jackson 1997). No
  repository was found on GitHub; the literature lane should check the authors'
  pages.

## Manifest entries

### Reference implementations — 2026-10-17

Acquired 21 references for verbs preliminaries: C++ vocabulary types,
state-machine libraries, mutation and dynamic-invariant tooling, out-of-tree
Clang tooling exemplars, fact stores and TLA+ trace validation. Each is an
intact GitHub source ZIP at a full commit SHA, kept in
`quarantine/_archives/refimpls-2026-10-17/`, with a clean copy in
`quarantine/<name>/`.

Extraction strips the archive's top-level directory and omits nested Git
metadata, `.DS_Store`, `__MACOSX` and symlinks. The originals keep them.
Omitted symlinks:

- mp-units: two doc aliases to `CONTRIBUTING.md` and `CHANGELOG.md`.
- fjalar: 163 Valgrind test-fixture aliases.

`codeql` keeps only `cpp/`, `shared/`, `LICENSE` and `README.md`; 51,646 other
entries remain in the archive. No acquired build, test or program ran, and no
dependency was adopted. The survey is
`papers/2026-10-17-reference-implementations.md`.

| Name | Canonical URL | Revision | License | Archive SHA-256 | Archive bytes | Files |
| --- | --- | --- | --- | --- | --- | --- |
| bounded-integer | https://github.com/davidstone/bounded-integer | 32f8c2b67f21c9cc6f141d6e39a06636b8aaf80e | BSL-1.0 | 2cd73580a1ea8f0cf459a7fb595a8ad7a233e5fc73d7161db058f08dfac768a0 | 451247 | 427 |
| type_safe | https://github.com/foonathan/type_safe | 292e8c127037e33d92f8f52dab0f1184993942d0 | MIT | a79dff3541a4b414addef458bbf436e45f50f9902cea3f29b07fc6ae11f01ee7 | 149644 | 83 |
| safe_numerics | https://github.com/boostorg/safe_numerics | be8f6473d3bbb5c546b0a031a9e78f9ba91579c9 | BSL-1.0 | 86a20a7b5dfe26dfc00c048ae69cadd11e739af4af68edaf09e6e06febfba724 | 2699247 | 425 |
| NamedType | https://github.com/joboccara/NamedType | 76668abe09807f92a695ee5e868f9719e888e65f | MIT | e67d5d324503de8c00ef3c7b3be8a2ce45c84da8d83bb6ad521d709c1d763820 | 120933 | 16 |
| strong_type | https://github.com/rollbear/strong_type | aa02c520eff7eacae66e200d35ad71b6980c4b7f | BSL-1.0 | 17c59194314db646c42a44c70815377e83f3a883256c7dd843b1fcf197e30690 | 93778 | 81 |
| mp-units | https://github.com/mpusz/mp-units | 9ffaf3e1fa4b6185903f06646f8012e91993344e | MIT | 8f4d59f2b971b3931802ebe75f5658d47b5312bb0b4d575d213aebabd1bd9f41 | 4990478 | 765 |
| magic_enum | https://github.com/Neargye/magic_enum | 5de969c9005938a27a34d3af3ea5923d18679ad8 | MIT | 932ea69f7dad77fc0599812f34b3c6e1dbdac85f49608f239fd9da24cd656638 | 231969 | 85 |
| GSL | https://github.com/microsoft/GSL | 7cd11f6fb3c4026ad5205a602ea2ed0e95fba808 | MIT | a99bb6647ab25e47ba4d0c25b9aa0519a4360ca595861641fc24567b63b6dbba | 105975 | 54 |
| sml | https://github.com/boost-ext/sml | bc13fcbb8060dd53ce4fc22f7967898faa3a7e13 | BSL-1.0 | 83d4152c95d849b3aa6ecca730661afd67cc90c4c2b76388f880d820b8e6253a | 54339037 | 2193 |
| msm | https://github.com/boostorg/msm | f2d60cb2b76243528f91933b681d00fbdfd8c230 | BSL-1.0 (file headers; no LICENSE file) | 03b627db9607687c613df423646b1e48e49d7aafe3d9218f39d576dfbd1d21a3 | 1173402 | 316 |
| daikon | https://github.com/codespecs/daikon | 67fbddac4e8e281b55bc1efa1bdd2d60fda901e6 | MIT-style permissive (`LICENSE.txt`) | a81a7a36c47c53a9c8f151132e3c67c55ca3707ff54a910cfb68311b94148618 | 77864041 | 3908 |
| fjalar | https://github.com/codespecs/fjalar | 426321853215840f2f0b49c7f2adc4401bcd26bb | GPL (Valgrind-derived; `valgrind/COPYING`) | f1ff4b00de3447f6f02e7c49c8ed3ca0c8ec3ad988556a1af7ac3378e19e83b2 | 43767819 | 7064 |
| mull | https://github.com/mull-project/mull | e53b0f0d332d22b94b96c53cff3074a50f6f6915 | Apache-2.0 | 19f64f2bd80150695cf7e98a1db99ca4637f9722cd60d68eca9eba6512bc249a | 2576108 | 820 |
| include-what-you-use | https://github.com/include-what-you-use/include-what-you-use | 40473dcc0d5e51cd03c025abf6e5d07e9e653c5a | NCSA (LLVM Release License) | a878fc87dfeec13b60b4454d6a78acab12c0cba3f42d2b691b1e5a7044f43204 | 1771345 | 1040 |
| clang-tidy-plugin-examples | https://github.com/coveooss/clang-tidy-plugin-examples | eec71314adaddf5ee866a71c26e5bf432759b1d2 | Apache-2.0 | 97e074cae48894051e4ed8cd29d767c95095b0b62b82e84b15274715d5b1862e | 4146751 | 55 |
| souffle | https://github.com/souffle-lang/souffle | f53dab8bf4bbf2395a26d2771f6b75395825cc46 | UPL-1.0 | edb2fa73e02afe9658db2e60a70082d99f3a5a0744411b15add3f6df23831d81 | 11324467 | 4080 |
| Glean | https://github.com/facebookincubator/Glean | 5f11916fc9841a9ee44e4da305fa01ef910eb0e6 | BSD (`LICENSE`) | ef6f76f4cbed7615005f29f98b56159de5a7f2a88436838d2aae382ffcaacbc4 | 12512704 | 15314 |
| codeql | https://github.com/github/codeql | ff3231c5ac4779befd8c8690bb04f447fc6a8d13 | MIT (QL libraries) | 29ab1057cc58d6d605ef26394b78247006e6235d4304011f0afd2a7bdff348e4 | 83047607 | 8540 (cpp, shared) |
| etcd-raft | https://github.com/etcd-io/raft | 638f42739b77572b5708eb0d8a776a272ade71ed | Apache-2.0 | a190e79e2e4dd3f37c4035bb0cba67135db5bc9901f16e29ae57fa3009cc39da | 423724 | 170 |
| trace_validation_tools | https://github.com/lbinria/trace_validation_tools | 7b31b03bd0025edc0a85a7a8e82dc1390a311ae4 | MIT | d879c164f838dacb2dbfb88b1bb91139b869c499968da50cbb844f9445960e7d | 36485 | 34 |
| CommunityModules | https://github.com/tlaplus/CommunityModules | 4c6c79bf6f3124dfa3a4fd3cfa9a92fe34c20763 | MIT | d9bf6feaa50189f3a2cb5ad8f4acdebd4165eddd2ffcab29ff0bf9b582281646 | 5048604 | 153 |

Restore: save the extractor below as `extract-reference.py` outside
`quarantine/`. Then, from the repository root, for each row run the following,
with `N` the name, `R` the owner/repository from the URL, `SHA` the revision,
and an extra `cpp shared LICENSE README.md` argument for codeql only:

```sh
A=quarantine/_archives/refimpls-2026-10-17
mkdir -p "$A" "quarantine/$N"
curl -fL -o "$A/$N-$(printf %.12s "$SHA").zip" "https://github.com/$R/archive/$SHA.zip"
shasum -a 256 "$A/$N-$(printf %.12s "$SHA").zip"   # compare with the table
python3 -I extract-reference.py "$A/$N-$(printf %.12s "$SHA").zip" "quarantine/$N"
```

```python
"""Extract a GitHub source ZIP into a clean reference copy.

Usage: extract-reference.py ARCHIVE DEST [PREFIX ...]
Strips the single top-level directory. Omits symlinks, .git entries,
.DS_Store and __MACOSX. If PREFIXes are given, keeps only paths under them.
Prints: files, omitted symlinks, omitted detritus, omitted by prefix.
"""
import os, stat, sys, zipfile
archive, dest, prefixes = sys.argv[1], sys.argv[2], tuple(sys.argv[3:])
files = links = detritus = filtered = 0
with zipfile.ZipFile(archive) as z:
    for info in z.infolist():
        parts = info.filename.split("/", 1)
        if len(parts) < 2 or not parts[1]:
            continue
        rel = parts[1]
        if info.is_dir():
            continue
        comps = rel.split("/")
        if any(c in (".git", "__MACOSX", ".DS_Store") for c in comps):
            detritus += 1; continue
        mode = (info.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(mode):
            links += 1; continue
        if prefixes and not any(rel == p or rel.startswith(p.rstrip("/") + "/") for p in prefixes):
            filtered += 1; continue
        out = os.path.realpath(os.path.join(dest, rel))
        if not out.startswith(os.path.realpath(dest) + os.sep):
            raise SystemExit(f"unsafe path {rel}")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with z.open(info) as src, open(out, "wb") as dst:
            dst.write(src.read())
        os.chmod(out, 0o755 if mode & 0o111 else 0o644)
        files += 1
print(f"{files}\t{links}\t{detritus}\t{filtered}")
```
