# Verbs

Verbs aims to enrich code with explicit constraints so agents can make and
check stronger claims about their work. It targets C++ (Clang, C++23) first and
Rust later. Each language gets its strongest native realization; there is no
cross-language parity layer.

The project is in research and design. design/verbs-design-brief.md is the
founding orientation input, not a settled design. Decisions are recorded in
journal/; literature and lane reports are in papers/.

## Claim boundary

Early verbs nails the basics before complex cases. Every invariant claim it
makes holds only under these assumptions, and verbs states them with the
claim:

- **No exception unwinds mid-mutation.** Unwind preservation is not checked.
- **No moved-from object is used.** Moved-from states are not modelled.
- **One exclusive owner.** An invariant mentions only its owner's own value
  members, and only the owner's operations mutate them.
- **One thread at a time.** The owner is confined to one thread. Lock-scoped
  and lock-free cases are outside the claim; memory ordering is never claimed.
- **No call-outs while broken.** The owner does not call unowned code while
  its invariant is temporarily broken.
- **Single-state only.** No relation between before and after a mutation is
  claimed, except `const`.

Code outside these bounds is reported as outside the claim, not as passing.
The deferred cases are tracked as beads under `verbs-de3`.

## What exists today

A placeholder runtime check, `check(name, value, predicate)`, in Rust (repository
root) and C++17 (`packages/cpp`). It calls the predicate once, returns the
original value on success, reports only the constraint name on failure, and
propagates predicate errors. It checks one value at one moment; it establishes
no persistent invariant. The intended design replaces it.

```rust
let retries = verbs::check("bounded retries", 3, |n| (1..=5).contains(n))?;
```

`./scripts/check.sh` runs the Rust tests, rustfmt, clippy, and the C++ contract
test. There are no runtime dependencies.

## Releases

These 0.1.0 releases remain up as placeholders: Rust `verbs` (crates.io),
Python `pverbs` (PyPI), `@antimeme/verbs` (JSR), and `verbs` 0.1.0-1
(LuaRocks). Non-C++/Rust sources were moved out of the tracked tree; they
remain in history at commit 700f1e8 (see quarantine-manifest.md).
Registry notes and release tooling are parked in utils/.

Licensed under the MIT license.
