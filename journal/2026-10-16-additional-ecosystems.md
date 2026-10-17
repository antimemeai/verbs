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
