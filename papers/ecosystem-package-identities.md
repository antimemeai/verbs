# Package identities and publication routes

Checked 2026-10-16 America/New_York (2026-10-17 UTC). Findings are a snapshot.
A 404 can mean an unlisted, reserved, or otherwise unavailable name; only a
successful registry registration/publication establishes ownership.

| Ecosystem | Exact endpoint/check | Observation |
| --- | --- | --- |
| PHP | [antimemeai/verbs](https://repo.packagist.org/p2/antimemeai/verbs.json) | HTTP 404 |
| PHP vendor | [antimemeai packages](https://packagist.org/packages/list.json?vendor=antimemeai) | Empty packageNames array |
| PHP project vendor | [verbs/verbs](https://repo.packagist.org/p2/verbs/verbs.json) | HTTP 404; not the selected footprint |
| Dart | [verbs](https://pub.dev/api/packages/verbs) | HTTP 404 |
| Ruby | [verbs](https://rubygems.org/api/v1/gems/verbs.json) | Existing English-conjugation library, 3.1.0 |
| Ruby alternative | [verbs-agent](https://rubygems.org/api/v1/gems/verbs-agent.json) | HTTP 404 |
| Erlang/Elixir | [verbs](https://hex.pm/api/packages/verbs) | Existing English-conjugation library, latest listing 0.6.1 |
| Erlang alternative | [verbs_agent](https://hex.pm/api/packages/verbs_agent) | HTTP 404 |
| .NET | [Verbs flat container](https://api.nuget.org/v3-flatcontainer/verbs/index.json) | HTTP 404 |
| .NET exact-ID search | [Verbs search](https://azuresearch-usnc.nuget.org/query?q=packageid:Verbs&prerelease=true) | totalHits 0 |
| Haskell | [verbs package](https://hackage.haskell.org/package/verbs), [preferred versions](https://hackage.haskell.org/package/verbs/preferred.json) | Both HTTP 404; no exact verbs entry in preferred-versions |
| Common Lisp | [Quicklisp 2026-01-01 systems](https://beta.quicklisp.org/dist/quicklisp/2026-01-01/systems.txt) | No verbs or cl-verbs system |
| Common Lisp project list | quicklisp/quicklisp-projects projects/verbs/source.txt and projects/cl-verbs/source.txt | Both HTTP 404 on master |
| Clojure | [verbs artifact API](https://clojars.org/api/artifacts/verbs) | HTTP 404; no implementation selected |
| Racket | [verbs package](https://pkgs.racket-lang.org/package/verbs) | HTTP 404; JSON endpoint returned 403, so do not infer complete catalog coverage |

Packagist requires vendor/package names and reads composer.json from the
repository root. Publishing a package protects its vendor namespace; a missing
package under a vendor does not by itself grant rights to that vendor. The
empty antimemeai listing is the relevant extra check here.
[Packagist documentation](https://packagist.org/about).

Dart uses a global pub.dev name. The SDK can validate and list publication
contents with `dart pub publish --dry-run`. A dry run does not reserve anything.
[Dart publishing](https://dart.dev/tools/pub/publishing).

Hex serves Erlang, Elixir, and other BEAM languages. An Erlang implementation
can be used by Elixir without another package. The application metadata and
Rebar configuration form its package footprint. The rebar3 Hex plugin is a
separate publication tool, not a runtime dependency adopted by these sources.
[Hex publishing](https://hex.pm/docs/rebar3-publish).

Hackage accepts Cabal source distributions and requires upload privileges.
New package names are compared case-insensitively. Candidate uploads are
available for preview; permanent publication and namespace ownership should
not be claimed on the basis of an HTTP lookup.
[Hackage upload rules](https://hackage.haskell.org/upload),
[account request](https://hackage-content.haskell.org/users/register-request).

Common Lisp is the initial interpretation of "Lisp" for the Quicklisp check.
ASDF loads/builds systems; Quicklisp distributes them and accepts project
inclusion requests. Other Lisp dialects use separate registries. Clojure runs
on the JVM; keep its support undecided rather than conflating it with Java or
assuming the operator has approved it.
[Quicklisp FAQ](https://www.quicklisp.org/beta/faq.html).

Zig's installed 0.15.2 build system and standard library implement URL/hash
dependency fetching. There is no official central flat package name to claim;
community catalogs are discovery channels rather than a single authority over
all import names. Preserve the GitHub repository identity and add a Zig module
and build.zig/build.zig.zon if Zig support is selected.
[Official build-system guide](https://ziglang.org/learn/build-system/).

For the next language discussion, Haskell fits the project's typed constraint
and verifiability goals; Zig offers compile-time checks and explicit errors;
Common Lisp offers conditions and macros. These are design-fit judgments, not
claims that the current one-function footprint already provides those features.
