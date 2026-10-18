# Reference material

Retain source archives intact and strip nested Git metadata only from extracted
copies. Record URLs, revisions, licenses, hashes, and restoration commands here
when adding references.

## polyglot_paddock

`quarantine/polyglot_paddock/` holds this repository's own non-C++/Rust
surfaces, moved out of the tracked tree on 2026-10-17. verbs is C++ first and
Rust later; these are retained as reference, not maintained. Paths inside the
paddock mirror their former repository paths.

- Source: this repository at commit 700f1e8 (MIT).
- Contents: `packages/{dart,dotnet,erlang,js,lua,ocaml,php,python,ruby}`,
  `packaging/opam`, `composer.json`, `.github/workflows/{footprints,lua}.yml`,
  `scripts/check-{footprints,lua-package,python-package}.sh`.
- Placeholder releases built from these sources: pverbs 0.1.0 (PyPI),
  @antimeme/verbs 0.1.0 (JSR), verbs 0.1.0-1 (LuaRocks, from tag `lua-v0.1.0`).
  Tag `v0.1.0` predates the pverbs packaging and the JSR scope; 700f1e8 holds
  the sources as they stood when paddocked.

Restore (tracked files only; local build outputs were not retained in Git):

```sh
mkdir -p quarantine/polyglot_paddock
git archive 700f1e8 packages/dart packages/dotnet packages/erlang packages/js \
  packages/lua packages/ocaml packages/php packages/python packages/ruby \
  packaging/opam composer.json .github/workflows scripts/check-footprints.sh \
  scripts/check-lua-package.sh scripts/check-python-package.sh \
  | tar -x -C quarantine/polyglot_paddock
```

## Reference implementations — 2026-10-17

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

Restore with `scripts/extract-reference.py`. From the repository root, for
each row run the following,
with `N` the name, `R` the owner/repository from the URL, `SHA` the revision,
and an extra `cpp shared LICENSE README.md` argument for codeql only:

```sh
A=quarantine/_archives/refimpls-2026-10-17
mkdir -p "$A" "quarantine/$N"
curl -fL -o "$A/$N-$(printf %.12s "$SHA").zip" "https://github.com/$R/archive/$SHA.zip"
shasum -a 256 "$A/$N-$(printf %.12s "$SHA").zip"   # compare with the table
python3 -I scripts/extract-reference.py "$A/$N-$(printf %.12s "$SHA").zip" "quarantine/$N"
```


## llvm-project 23.1.2 — 2026-10-17

Source release matching the pinned Homebrew LLVM, for reading Clang, clangd,
clang-tidy and analysis sources. Never built or run from quarantine.

- URL: https://github.com/llvm/llvm-project/releases/download/llvmorg-23.1.2/llvm-project-23.1.2.src.tar.xz
- License: Apache-2.0 WITH LLVM-exception
- Archive: `quarantine/_archives/llvm-project-23.1.2.src.tar.xz`, 179,200,068
  bytes, SHA-256
  `c98bbef08a2b4c2613cd50e9aa9ae7b69b1fe6c16b2c40373bc0ab6116fdf78a` (matches
  the Homebrew formula).
- Clean copy: `quarantine/llvm-project/`, 180,580 regular files, 2.5 GB. 19
  symlinks (clang driver test inputs, mlgo utils) and `.DS_Store` omitted.

Restore from the repository root:

```sh
mkdir -p quarantine/_archives && cd quarantine/_archives
curl -fsSLO https://github.com/llvm/llvm-project/releases/download/llvmorg-23.1.2/llvm-project-23.1.2.src.tar.xz
echo "c98bbef08a2b4c2613cd50e9aa9ae7b69b1fe6c16b2c40373bc0ab6116fdf78a  llvm-project-23.1.2.src.tar.xz" | shasum -a 256 -c
cd .. && tar -xJf _archives/llvm-project-23.1.2.src.tar.xz && mv -f llvm-project-23.1.2.src llvm-project
find llvm-project -type l -delete; find llvm-project -name .DS_Store -delete
```

## C++ corpus — 2026-10-18 (in progress)

Open-source C++ for the deterministic corpus runs (SPEC §1.1, bead verbs-2or).
- **Selection is mechanical, not hand-picked.** GitHub's 1,000 most-starred
  C++ repositories (`language:C++ archived:false fork:false`), minus those
  with no license, those over 2 GB, and those not pushed since 2025-10-01.
  That leaves 755. List: `context/corpus/selected.tsv`; candidates:
  `context/corpus/candidates.tsv`.
- **Archives:** `quarantine/_archives/corpus-2026-10-18/`, one GitHub source
  tarball per repository at a full commit SHA. Tarballs carry no `.git`.
  `context/corpus/fetched.tsv` records name, SHA, license, stars, bytes,
  SHA-256 and file name. Licenses vary (MIT, Apache-2.0, BSD, GPL and
  others). The corpus is local test input and is never redistributed.
- **Submodules** are fetched at their pinned commits by `probe.py` into the
  same archive directory, and unpacked in place.
- **Extracted trees:** `quarantine/corpus/src/<owner>__<repo>/`, stripped of
  `.git`, `.hg`, `.svn` and `.DS_Store`. They exist only while a project is
  probed. The tarballs are the source of truth, and extraction is
  deterministic, so a later run re-extracts.
- **Build outputs** never persist. Each configure runs in a per-project
  build directory under `sandbox-exec`, which allows writes only there and
  in temp directories. The directory is deleted when the probe ends,
  including on failure. Only `compile_commands.json` is kept, in
  `context/corpus/db/`.
- **Status:** fetched 318 of 755 (12 GB). Fetching stopped for disk space.
  `reconcile.py` recorded the tarballs already on disk in `fetched.tsv`. The
  other 437 are listed in `context/corpus/unfetched.tsv` (columns of
  `selected.tsv`). The probe runs over the 318.

Fetch the rest, then probe, from the repository root:

```sh
cd context/corpus
python3 -I fetch.py unfetched.tsv ../../quarantine/_archives/corpus-2026-10-18 fetched.tsv 40
python3 -I probe.py fetched.tsv ../../quarantine/_archives/corpus-2026-10-18 \
  ../../quarantine/corpus/src db ../../quarantine/corpus/build probe.tsv 8
```
