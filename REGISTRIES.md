# Registry status

Checked 2026-10-16. A missing package is not a reserved name. Publication and
source preparation are separate states. Do not publish placeholder-only packages.

| Ecosystem | Requested identity | Current state |
| --- | --- | --- |
| GitHub | `antimemeai/verbs` | Public personal repository created |
| Rust / crates.io | `verbs` | Package validates; publication rejected with HTTP 403 authentication failed; token refresh required |
| Python / PyPI | `pyverbs` | Taken by [rdma-core bindings](https://pypi.org/project/pyverbs/) |
| Python alternative | `verbs-agent` | API returned 404; source prepared, not packaged or claimed |
| npm | `jsverbs` | API returned 404; package prepared; npm login required |
| JSR | `@antimemeai/verbs` | Source prepared; scope/package creation and authentication required |
| ConanCenter | `verbs` | Recipe path absent; local package creation and consumer test pass, central submission/review required |
| vcpkg | `verbs` | Port path absent; port draft prepared, package validation and submission required |
| opam | `verbs` | Package path absent; release manifest with URL/checksum prepared, isolated install and submission required |

Rust: `cargo publish` from the repository root. The local rustup toolchain is
pinned in rust-toolchain.toml; prefer `~/.cargo/bin` on PATH. Standard Cargo
credentials stay outside this repository.

npm: `cd packages/js && npm login && npm publish --access public`. Dry run with
`npm pack --dry-run`. Package includes ESM JavaScript and TypeScript declarations.

JSR: create the personal scope and package through https://jsr.io/new, then
publish from packages/js with `deno publish`. All JSR names are scoped;
there is no globally claimed bare `verbs` package. The personal scope can hold
this package without creating a GitHub organization.
[Scopes](https://jsr.io/docs/scopes), [publishing](https://jsr.io/docs/publishing-packages).

ConanCenter contributions are recipes reviewed through pull requests to
conan-io/conan-center-index. vcpkg similarly accepts ports through its source
repository. A local recipe or overlay does not claim a central registry name.
[ConanCenter](https://docs.conan.io/2/tutorial/conan_repositories/conan_center.html),
[vcpkg ports](https://learn.microsoft.com/en-us/vcpkg/concepts/ports).

opam publication uses a released source archive and a reviewed repository
contribution. packaging/opam/verbs.opam contains the release URL and checksum;
packages/ocaml/verbs.opam supports local source development.
[opam packaging](https://opam.ocaml.org/doc/Packaging.html).

See packaging/README.md for submission drafts. The public source tag is v0.1.0.
JavaScript tests and npm packaging pass. Deno type checking, JSR public-type
checking, and JSR publication dry run pass. JSR publication still needs account
authorization. No package registry publication has succeeded yet.

## Other ecosystems to consider

Prioritize .NET/NuGet and JVM/Maven Central if those language surfaces are
planned. NuGet has package IDs and a separate prefix-reservation process;
Maven Central uses verified namespaces, such as `io.github.antimemeai`.
[NuGet prefixes](https://learn.microsoft.com/en-us/nuget/nuget-org/id-prefix-reservation),
[Central namespaces](https://central.sonatype.org/register/namespace/).

Go uses repository/module paths, so `github.com/antimemeai/verbs` is the
natural identity if a Go module is added. A source release tag publishes the
version; there is no flat central `verbs` claim.
[Go publishing](https://go.dev/doc/modules/publishing).

Also consider SwiftPM, RubyGems, Hex (Elixir/Erlang), Packagist (PHP), and
pub.dev (Dart). Direct API checks found existing unrelated `verbs` packages on
RubyGems and Hex, and an existing `verbs` on npm. NuGet's flat-container API
returned 404 for `verbs`, which does not guarantee the name is publishable.
No names in these additional ecosystems have been claimed.

For a future CLI, Homebrew, winget, Scoop, apt/rpm, and Nix are distribution
channels to consider once there is a useful executable. Domain names and
container-image namespaces are separate identities, not package releases.
