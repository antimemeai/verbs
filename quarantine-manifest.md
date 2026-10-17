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
