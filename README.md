# Verbs

Verbs makes constraints explicit so agents can write code whose behavior is
easier to check. The project aims to enrich code with constraints, improve
verifiability, and make doing the right thing easier.

The initial implementation is deliberately small: a named predicate check.

```rust
let retries = verbs::check("bounded retries", 3, |n| (1..=5).contains(n))?;
```

`check(name, value, predicate)` calls the predicate exactly once. On success it
returns the original value. On failure it reports the constraint name without
embedding the potentially sensitive value. Predicate errors propagate.
Rust and OCaml return a result; Python, JavaScript, and C++ throw an exception.

This checks a value at a moment in time. It does not establish a persistent
refinement type, prove a predicate correct, or verify an entire program. Mutable
values can cease to satisfy their constraints after a successful check.

Source surfaces: Rust at the repository root, JavaScript and TypeScript in
`packages/js`, Python in `packages/python`, C++17 in `packages/cpp`, and OCaml in
`packages/ocaml`. Registry names and publication status are in REGISTRIES.md.
The public API is experimental in 0.1.0.

Run `./scripts/check.sh` to check the language implementations with local tools.
There are no runtime dependencies.

Licensed under the MIT license.
