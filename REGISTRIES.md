# Registry status

Checked 2026-10-16. A missing package is not a reserved name. Publication and
source preparation are separate states. Do not publish placeholder-only packages.

| Ecosystem | Requested identity | Current state |
| --- | --- | --- |
| GitHub | `antimemeai/verbs` | Public personal repository created |
| Rust / crates.io | `verbs` | Published 0.1.0; public API confirms the version and repository |
| Python / PyPI | `pverbs` | Published 0.1.0; wheel/sdist hashes confirmed by public API; fresh pip installation passes |
| npm | `jsverbs` | Publication deferred by operator; saved credential requires additional 2FA |
| JSR | `@antimeme/verbs` | Published 0.1.0; public API and package metadata confirm the release |
| ConanCenter | `verbs` | Local package creation and consumer test pass; central submission deferred by operator |
| vcpkg | `verbs` | Port draft prepared; package validation pending, central submission deferred by operator |
| opam | `verbs` | Package path absent; release manifest with URL/checksum prepared, isolated install and submission required |
| PHP / Packagist | `antimemeai/verbs` | Package API returns 404, vendor listing empty; root Composer manifest and PHP source prepared |
| Dart / pub.dev | `verbs` | Package API returns 404; SDK-only package prepared |
| Ruby / RubyGems | `verbs-agent` (provisional) | `verbs` is taken; alternative API returns 404; gem builds locally |
| Erlang / Hex | `verbs_agent` (provisional) | `verbs` is taken; alternative API returns 404; OTP source and metadata prepared |
| .NET / NuGet | `Verbs` | Flat-container API returns 404, exact-ID search empty; .NET Standard 2.0 project prepared |
| Lua / LuaRocks | `verbs` | Published 0.1.0-1 in root manifest; fresh registry installation and installed-module checks pass |

The five additional footprints passed [CI run 38990090145](https://github.com/antimemeai/verbs/actions/runs/38990090145):
PHP/Ruby/Erlang/Dart/.NET contract checks, strict Composer validation, Ruby gem
creation, Dart analysis and publication dry run (zero warnings), and NuGet
package creation. These are package-preparation results; no registry upload
was run. Haskell/Common Lisp/Zig remain research candidates.

Rust: [verbs 0.1.0](https://crates.io/crates/verbs) is published. The local rustup
toolchain is pinned in rust-toolchain.toml; prefer ~/.cargo/bin on PATH. The
release utility `python scripts/publish.py crates` reads the crates key in
~/projects/.env and passes CARGO_REGISTRY_TOKEN to Cargo. No credential is
written into this repository or persistent Cargo configuration.

Python: pverbs is the operator-selected distribution and import name. pyverbs
remains an unrelated [rdma-core binding](https://pypi.org/project/pyverbs/).
[pverbs 0.1.0](https://pypi.org/project/pverbs/0.1.0/) is published with a wheel
and source distribution. `pip install pverbs` installs it; `from pverbs import
check` imports the API. Both published hashes match the tested local artifacts.
Run scripts/check-python-package.sh to build a wheel and sdist and test isolated
installations on Python 3.10. Setuptools is the discussed build-only backend;
the installed module has no runtime dependencies. `python scripts/publish.py
pypi` reads the pypi key in ~/projects/.env and uploads the prepared artifacts.

npm: `cd packages/js && npm login && npm publish --access public`. Dry run with
`npm pack --dry-run`. Package includes ESM JavaScript and TypeScript declarations.
The release utility also supports `python scripts/publish.py npm`, reading the
npm key from ~/projects/.env through a temporary npmrc that references a child
environment variable. It leaves no credential in the repository or user npmrc.
The current token requires a second factor. With a current code saved as
npm_otp in that file, use `python scripts/publish.py npm --otp-from-env`.
The code goes only into the child NPM_CONFIG_OTP environment and is redacted
from captured output. Alternatively supply a publishing token with 2FA bypass.
The operator deferred npm publication while sorting out its Chrome/passkey
authentication. Do not retry npm publication until the operator resumes it.

JSR: [@antimeme/verbs 0.1.0](https://jsr.io/@antimeme/verbs@0.1.0) is published.
For future versions, publish from packages/js with `deno publish` and complete
browser authorization. All JSR names are scoped;
there is no globally claimed bare `verbs` package. The personal scope can hold
this package without creating a GitHub organization.
[Scopes](https://jsr.io/docs/scopes), [publishing](https://jsr.io/docs/publishing-packages).

ConanCenter contributions are recipes reviewed through pull requests to
conan-io/conan-center-index. vcpkg similarly accepts ports through its source
repository. A local recipe or overlay does not claim a central registry name.
[ConanCenter](https://docs.conan.io/2/tutorial/conan_repositories/conan_center.html),
[vcpkg ports](https://learn.microsoft.com/en-us/vcpkg/concepts/ports).

JSR and LuaRocks publication are complete. npm and the other outstanding
registry publications can wait. ConanCenter and vcpkg remain intended targets,
but the operator wants further project development before central review.

opam publication uses a released source archive and a reviewed repository
contribution. packaging/opam/verbs.opam contains the release URL and checksum;
packages/ocaml/verbs.opam supports local source development.
[opam packaging](https://opam.ocaml.org/doc/Packaging.html).

See packaging/README.md for submission drafts. The public source tag is v0.1.0.
JavaScript tests and npm packaging pass. Deno type checking, JSR public-type
checking, and publication succeeded. Rust, Python, LuaRocks, and JSR publication
have succeeded; the remaining registry states
are listed individually above.

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

Lua: packages/lua/verbs-scm-1.rockspec tracks main. The numbered
verbs-0.1.0-1.rockspec installs from the new lua-v0.1.0 source tag; that source
archive's checksum is included. LuaRocks' builtin backend installs the module.
[verbs 0.1.0-1](https://luarocks.org/modules/antimemeai/verbs) is now published in
the root manifest. A fresh `luarocks install verbs 0.1.0-1` into an isolated
local tree succeeded, and the installed module passes its contract suite.
Lua 5.1 through 5.5 and LuaJIT are supported. The older v0.1.0 tag predates Lua.
scripts/check-lua-package.sh passes lint, archive download/install, and contract
checks against the installed release module on Lua 5.4. The release utility
supports `python scripts/publish.py luarocks`, using the official rockspec-only
upload API and the workspace luarocks credential without persistent config.
Local source checks pass on Lua 5.4, 5.5.1, and LuaJIT. Rockspec lint,
installation, and installed-module checks pass on Lua 5.1 and 5.4 in
[CI run 38995766475](https://github.com/antimemeai/verbs/actions/runs/38995766475).
LuaRocks also supports
personal namespaces such as antimemeai/verbs. The root verbs name is now
claimed by this publication under antimemeai. Future uploads require registry
authentication.
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
