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
Rust, OCaml, and Erlang return a result; the other implementations throw an
exception.

This checks a value at a moment in time. It does not establish a persistent
refinement type, prove a predicate correct, or verify an entire program. Mutable
values can cease to satisfy their constraints after a successful check.

Source surfaces: Rust at the repository root, JavaScript and TypeScript in
`packages/js`, Python in `packages/python`, C++17 in `packages/cpp`, and OCaml in
`packages/ocaml`. Registry names and publication status are in REGISTRIES.md.
The public API is experimental in 0.1.0.

Additional provisional footprints live in `packages/php`, `packages/dart`,
`packages/ruby`, `packages/erlang`, and `packages/dotnet`. The root composer.json
describes the PHP package for Packagist. Ruby uses the provisional gem name
`verbs-agent` and Erlang uses `verbs_agent` because `verbs` is taken in both
registries. No new registry names have been claimed.

Run `./scripts/check.sh` to check the language implementations with local tools.
There are no runtime dependencies.

Run `./scripts/check-footprints.sh` for the five additional language checks, or
pass individual names such as `ruby` or `dotnet` when only those tools are
installed. The Package footprints workflow runs their checks and available
package dry runs without publishing. `./scripts/check-registries.py` rechecks
their public registry endpoints.

Licensed under the MIT license.
