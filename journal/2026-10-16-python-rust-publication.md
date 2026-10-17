# Python and Rust publication

The operator identified pypi and crates credentials in ~/projects/.env and
selected pverbs as the Python distribution name. Both keys exist in a 0600
file. Initial public endpoint checks still return 404 for pverbs and verbs.
No secret values were displayed or copied into the repository.

Plan: retry the validated Rust package with the explicitly supplied crates
credential. Rename the unpublished Python import package to pverbs, add its
standard package metadata, build wheel and sdist, and run the existing contract
suite against isolated installations of each artifact before uploading them.
Confirm publication through each public registry API and update issue/status.

Proposed setuptools as a build-only dependency in commentary before adoption:
it owns standard wheel/sdist construction and avoids an owned format builder.
Its tradeoff is a packaging dependency; the published module still has no
runtime dependencies. No new test framework is needed. uv is already installed
and will drive isolated builds, installations, and publication.

Add one release utility that reads only the selected credential from the named
workspace file. Parse it as text, never shell-source it, pass the value only in
the child environment, and redact it from captured command output. Never put
credentials in arguments, Git, journal entries, or persistent Cargo config.
