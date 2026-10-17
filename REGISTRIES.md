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
| PHP / Packagist | `antimemeai/verbs` | Package API returns 404, vendor listing empty; root Composer manifest and PHP source prepared |
| Dart / pub.dev | `verbs` | Package API returns 404; SDK-only package prepared |
| Ruby / RubyGems | `verbs-agent` (provisional) | `verbs` is taken; alternative API returns 404; gem builds locally |
| Erlang / Hex | `verbs_agent` (provisional) | `verbs` is taken; alternative API returns 404; OTP source and metadata prepared |
| .NET / NuGet | `Verbs` | Flat-container API returns 404, exact-ID search empty; .NET Standard 2.0 project prepared |
| Lua / LuaRocks | `verbs` | Absent from root manifest and manifest-5.1; development rockspec and pure Lua module prepared |

The five additional footprints passed [CI run 38990090145](https://github.com/antimemeai/verbs/actions/runs/38990090145):
PHP/Ruby/Erlang/Dart/.NET contract checks, strict Composer validation, Ruby gem
creation, Dart analysis and publication dry run (zero warnings), and NuGet
package creation. These are package-preparation results; no registry upload
was run. Haskell/Common Lisp/Zig remain research candidates.

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

## Additional provisional footprints

PHP, Dart, Ruby, Erlang, and .NET were provisionally approved by the operator.
Lua/LuaRocks was subsequently added.
Maven/Java is excluded. The implementations have no added runtime or test
libraries. Ruby's gem name and Erlang's application/module name avoid collisions
with the existing unrelated conjugation libraries.

Packagist requires a vendor prefix; bare `verbs` is not a valid identity.
The root composer.json allows submitting the existing personal repository as
`antimemeai/verbs`. The v0.1.0 tag predates this manifest; a future release tag
must include the PHP source before Packagist can index a stable PHP release.
[Packagist naming/submission](https://packagist.org/about).

Dart publication is run from packages/dart with `dart pub publish`; first use
`--dry-run`. Ruby publication would use the built gem under packages/ruby/dist.
Hex publication needs the rebar3 Hex plugin and authentication; plugin adoption
and registry publication have not been performed. NuGet publication would use
the nupkg generated by `dotnet pack`. No additional namespace is registered by
preparing a package. NuGet's separate prefix-reservation process is distinct
from an initial package upload.
[Dart publishing](https://dart.dev/tools/pub/publishing),
[Hex Erlang publishing](https://hex.pm/docs/rebar3-publish),
[NuGet prefixes](https://learn.microsoft.com/en-us/nuget/nuget-org/id-prefix-reservation).

Lua: packages/lua/verbs-scm-1.rockspec tracks main and installs the module using
LuaRocks' builtin backend. Lua 5.1 through 5.5 and LuaJIT are supported. The
existing v0.1.0 tag predates Lua; a numbered rockspec needs a new immutable
source release. Local checks pass on Lua 5.4, 5.5.1, and LuaJIT. Rockspec lint,
installation, and installed-module checks pass on Lua 5.1 and 5.4 in
[CI run 38995766475](https://github.com/antimemeai/verbs/actions/runs/38995766475).
LuaRocks also supports
personal namespaces such as antimemeai/verbs. No root name or namespace was
claimed. Publication requires registry authentication.
[LuaRocks namespaces](https://github.com/luarocks/luarocks/blob/main/docs/namespaces.md),
[rock creation](https://github.com/luarocks/luarocks/blob/main/docs/creating_a_rock.md).

Source preparation and CI validation do not claim registry names. Run
scripts/check-registries.py for fresh status. Research and exact endpoints are
in papers/ecosystem-package-identities.md.

## Candidates under consideration

Haskell's `verbs` returns 404 on Hackage. It is a flat package name, and an
account with upload permission is needed to publish. A source package must be
produced by Cabal; no Haskell implementation has been prepared yet.
[Hackage uploading](https://hackage.haskell.org/upload).

Common Lisp: no `verbs` or `cl-verbs` system appears in the current Quicklisp
2026-01-01 index. This establishes only absence from that index, not global
uniqueness among Lisp libraries. An ASDF system can be distributed from this
repository before requesting Quicklisp inclusion; inclusion is reviewed.
Scheme/Racket/Clojure have separate ecosystems and identities.
[Quicklisp project requests](https://www.quicklisp.org/beta/faq.html).

Zig: the built-in package machinery uses source URLs and package hashes, so
there is no official global bare `verbs` name to reserve. Repository/module
identity is the useful starting point. No Zig implementation is prepared.
[Zig build system](https://ziglang.org/learn/build-system/).

Go uses repository/module paths, so `github.com/antimemeai/verbs` is the
natural identity if a Go module is added. A source release tag publishes the
version; there is no flat central `verbs` claim.
[Go publishing](https://go.dev/doc/modules/publishing).

SwiftPM is also a candidate if Swift support is wanted. No implementations or
new registry identities have been prepared for Go or Swift.

For a future CLI, Homebrew, winget, Scoop, apt/rpm, and Nix are distribution
channels to consider once there is a useful executable. Domain names and
container-image namespaces are separate identities, not package releases.
