# Initial release

The operator requested a personal public GitHub repository named verbs and
minimal packages for crates.io, PyPI, npm, JSR, ConanCenter, vcpkg, and opam.
The active GitHub account is antimemeai, verified as type User.

Plan: provide one small useful operation, `check(name, value, predicate)`.
Evaluate the predicate once. Return the original value when it passes;
otherwise report the constraint name. Propagate errors from the predicate.
This checks a value at one moment; it does not prove future invariants or
verify an entire program. No dependencies or broad framework are needed.

First validate Rust behavior and its packaged artifact, then publish with the
existing local Cargo credential if it is valid and the license is settled.
Prepare equivalent small language surfaces and registry instructions. Test
acceptance, rejection, single evaluation, original-value identity where relevant,
and propagation of predicate errors. Keep registry status explicit.

Initial registry API checks: verbs on crates.io and jsverbs on npm returned
404. pyverbs exists and belongs to an unrelated rdma-core binding project.
ConanCenter, vcpkg, and opam source paths for verbs returned 404; these
registries require reviewed contributions, not direct package-name claims.
JSR uses scopes. No npm, PyPI, or JSR credentials were found in the standard
environment/config locations checked. A Cargo token is configured.

License and alternative Python distribution name were asked of the operator
before publication. Availability can change and a 404 is not a reservation.
