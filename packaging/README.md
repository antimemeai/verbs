# Registry submission drafts

These files do not claim central registry names and have not been submitted.
The recipes point to the public v0.1.0 source archive. Archive hashes were
computed from the downloaded archive. C++ source/build/install checks pass.
Conan package creation and its consumer build/run pass on macOS arm64.
The vcpkg package-manager build has not been run locally.

- Conan: conan/conanfile.py and conandata.yml are the header-only recipe.
  A test_package checks a consumer through CMakeDeps. Adapt the directory/config
  layout to conan-center-index before opening a central submission.
- vcpkg: vcpkg/verbs is an overlay port draft. Validate with
  `vcpkg install verbs --overlay-ports=packaging/vcpkg`, then follow the central
  repository's contribution/versioning process.
- opam: opam/verbs.opam builds the source archive with the owned Makefile.
  `opam lint packaging/opam/verbs.opam` checks metadata; an isolated opam install
  remains necessary before submitting it to opam-repository.

The API has no runtime dependencies. Conan and vcpkg helpers are build tooling.
