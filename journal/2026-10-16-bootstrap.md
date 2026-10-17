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

After leaving the optional questions open while preparing the sources, stated
MIT and verbs-agent as the working defaults. No Python distribution was built
or published. Python build-backend selection remains open under the workspace
library policy; no packaging dependency was silently adopted.

Validation: Rust unit/doc tests, formatting, Clippy, and packaged-archive build
passed; JavaScript and Python contract tests passed; C++ compiled, contract test
passed, and CMake installation succeeded; OCaml contract test and opam lint
passed. npm pack dry run passed. Deno checked the TypeScript entrypoint and JSR
publication dry run passed, including the public-type check. Every language
checks a bounded numeric range, exact acceptance/rejection, one evaluation, and
predicate error propagation. Ownership/identity is checked where applicable.

The public personal repository and v0.1.0 source tag were pushed. crates.io
upload was attempted and rejected with HTTP 403 authentication failed. Asked
the operator to refresh Cargo credentials locally, without sending a token to
chat. npm login is pending browser authorization. Conan/vcpkg/opam submission
drafts refer to the tagged archive with downloaded-byte SHA256/SHA512 hashes;
they have not been submitted or tested through Conan/vcpkg.

Homebrew Rust is broken against its installed LLVM; selecting the installed
rustup 1.99.0 toolchain and putting ~/.cargo/bin first avoids it without changing
the machine's global configuration.

Remaining publication work is tracked in
https://github.com/antimemeai/verbs/issues/1. The npm and JSR CLIs are awaiting
the operator's browser authorization; no credentials were written into Git.
The OCaml Makefile's install target also succeeded into an ignored local prefix.

Conan package creation was then exercised with the Conan CLI in an isolated
CONAN_HOME under context/. The first attempt exposed URL-based archive-type
guessing: the codeload URL ends in v0.1.0, so the recipe must supply an explicit
.tar.gz filename. Fixed that and added a packaged consumer test. Package creation,
CMakeDeps consumer configuration/build, and consumer execution now pass on
macOS arm64 with AppleClang 17. No runtime dependency was added. vcpkg remains
unvalidated through its package manager. All registry claims remain pending.
