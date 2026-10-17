# C++/Rust focus

The operator supplied verbs-design-brief.md, a design synthesized with web
Claude. It recasts verbs as structural typing, invariant discovery, and
edit-local verification feedback for C++ (Clang, C++23) first and Rust later.
The prior work in this repository is registry groundwork around a one-function
`check(name, value, predicate)` runtime check; none of the brief is built.

The operator directed every language except C++ and Rust into
quarantine/polyglot_paddock/. Moved the nine package surfaces, opam packaging,
composer.json, both GitHub workflows (each covered only paddocked languages),
and the three per-language check scripts. Paths mirror the repository layout;
quarantine-manifest.md records the source commit and a git archive restoration
command. Published releases remain reproducible from their tags.

scripts/check.sh no longer runs node, python, or OCaml checks. It passes:
Rust tests/fmt/clippy and the C++ contract test. scripts/publish.py and
scripts/check-registries.py stay in place for discussion: they are Python
release tooling that also drives the crates.io release.

Linked BLACKBIRD.md to ../BLACKBIRD.md as a tracked relative symlink, matching
blackbird, arconaut, perspicuity, and r1337.

Toolchain facts for the brief's VERIFY items: Homebrew LLVM 23.1.2 (also
llvm@20) provides clang++, clangd, clang-tidy, and run-clang-tidy. The system
default is Apple clang 17.0.0, which is not the target. The brief's Clang >= 18
(deducing this) and >= 19 ([[assume]]) floors are met by LLVM 23; pin it.
