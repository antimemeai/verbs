# Additional package footprints

The operator provisionally approved PHP, Dart, Ruby, Erlang, and .NET, asked
whether verbs is taken, and requested a simple footprint. Maven/Java remains
out of scope. Haskell, Lisp, and Zig are being evaluated, not silently selected
as additional implementation commitments.

Plan: reuse the existing check-at-call-time contract in five owned, dependency-
free implementations, with native package metadata and executable contract
checks. Test bounded acceptance/rejection, exact error naming, one predicate
call, reference identity where meaningful, and predicate exception propagation.
No new test framework or runtime library is needed. Package preparation does
not publish or reserve a name. Keep alternatives provisional until publication.

Registry checks: Packagist's APIs return no antimemeai vendor packages and 404
for antimemeai/verbs and verbs/verbs. Packagist requires vendor/package names,
and a root composer.json. Place the PHP manifest at this repository's root so
the existing personal repository can be submitted without a second repository.
pub.dev verbs returns 404. NuGet's verbs flat-container endpoint returns 404,
and an exact-ID search returns zero hits. These indicate missing listings, not
a guarantee that first publication will be accepted.

RubyGems verbs 3.1.0 belongs to an English conjugation library; Hex verbs 0.6.1
is also a conjugation library. Prepare verbs-agent (Ruby) and verbs_agent
(Erlang), both of which return 404. Use distinct module/application names to
avoid shadowing the existing packages. Prepare Verbs as the NuGet package ID.

Hackage verbs returns 404 and is absent from preferred-versions. The current
Quicklisp 2026-01-01 systems index has no verbs or cl-verbs system; Quicklisp's
project source paths for those names also return 404. Quicklisp accepts project
requests; it is not an instant name reservation. Zig 0.15.2 is installed and its
built-in package manager uses source locations/hashes; there is no official flat
registry name to claim. Lisp dialects have separate ecosystems; do not infer
Scheme/Racket/Clojure availability from the Common Lisp result.

Local tools: Ruby and Mono are available. PHP, Dart, Erlang, and the dotnet SDK
are absent. Docker is installed but its daemon is not running. Validate the
available implementations locally and use a small GitHub workflow to run the
five native checks and package dry runs with the missing tools. Keep publishing
out of the workflow; no registry authorization was requested this turn.

Implemented the five footprints and pushed commit 8069446. Ruby's contract
checks and gem build pass locally. The installed Mono compiler wrapper points
to an executable that macOS rejects with Bad CPU type; did not change the
operator's toolchain. Its presence did not establish a working C# compiler.

GitHub Actions run 38990090145 completed successfully:
https://github.com/antimemeai/verbs/actions/runs/38990090145

All five implementations pass the contract checks. Composer strict validation
passes. RubyGem creation passes. Dart analysis finds no issues; the publication
dry run reports zero warnings. The .NET 10 SDK runs the .NET Standard 2.0
library's consumer checks and creates Verbs.0.1.0.nupkg. The workflow uses
official SDK setup actions pinned to inspected commit SHAs, and contains no
publication step or registry credentials. No runtime/test library was added.

Added scripts/check-footprints.sh for native checks/package dry runs and
scripts/check-registries.py for public endpoint rechecks. Updated issue #1 with
the new publication work, provisional alternatives, and Maven/Java exclusion.
Wrote the endpoint snapshot, registry rules, and Haskell/Common Lisp/Zig
assessment in papers/ecosystem-package-identities.md. Clojars' verbs endpoint
and Racket's verbs page also returned 404; these are separate Lisp ecosystems,
not an implication of the Quicklisp result. No package names were claimed.
