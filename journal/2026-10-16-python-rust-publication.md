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

The first retry stopped before upload: Cargo's unanchored LICENSE* include
matched ignored copies of LICENSE in local package-install trees. The same
issue applied to the unanchored README pattern. Corrected the include list to
root-anchored source, manifest, README, and LICENSE paths; inspect the resulting
archive list before retrying. No --allow-dirty workaround is appropriate.

The next attempt still used the saved Cargo credential because the release
utility initially set the alternate-registry token variable. crates.io reads
CARGO_REGISTRY_TOKEN. Corrected the environment variable after checking Cargo's
configuration reference. That failed attempt did not establish that the new
workspace token was invalid.

With CARGO_REGISTRY_TOKEN set from the workspace crates key, Cargo successfully
published verbs 0.1.0. The public crates.io API confirms max_version 0.1.0 and
repository https://github.com/antimemeai/verbs. The archive has seven expected
files, with no context/ or other language package contents.

Renamed the unpublished Python module from verbs_agent to pverbs and updated
its contract suite. Added standard pyproject.toml metadata with the setuptools
build-only backend proposed above. uv built pverbs 0.1.0 as wheel and sdist.
Separate clean Python 3.10.20 environments installed each artifact with no
runtime dependencies. The existing contract checks pass against both installed
copies, with source-directory imports excluded. Metadata version, py.typed
presence, and absence of runtime requirements were also checked. Publication
is next; do not claim the PyPI name until its API confirms it.
