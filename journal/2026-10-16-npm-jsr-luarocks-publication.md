# npm, JSR, and LuaRocks publication

The operator supplied npm and luarocks credential key names in the workspace
.env and showed the newly created JSR package @antimeme/verbs. Other registries
can wait. Conan/vcpkg remain planned, but do not submit them for review yet.

Plan: update JSR configuration and usage docs from the previously proposed
@antimemeai scope to the actual @antimeme scope. Recheck the publication files,
publish npm with temporary credential configuration, and start JSR's browser
authorization. Publish LuaRocks with the supplied API key after validating a
numbered rockspec against an immutable source revision containing Lua. Keep
credentials out of arguments, logs, Git, and lasting package-manager config.
Confirm each registry's version/contents before marking it published.

The JSR API confirms @antimeme/verbs exists with no versions and no linked
GitHub repository yet. npm jsverbs returns 404. LuaRocks' root manifest still
has no verbs entry. Initial exact-key checks did not find npm/luarocks values;
check expected case/alias spellings before treating credentials as absent.

Updated and pushed the JSR scope. Its dry run and the existing JavaScript
contract suite pass. Started JSR publication, which is awaiting the operator's
browser authorization. The workspace .env still has no matching npm/luarocks
keys or usual uppercase aliases, and there is no repository-local .env; asked
the operator to save the entries without putting their values in chat.

Created lua-v0.1.0 at e184c8c and pushed it. That archive includes the Lua module
and has SHA256 3be41648263bdd2e2b1c1dee3d75dde5ee9d2429e2e8c34506893b122d95fd82
and MD5 7f9e3393d50ba86e39d94195a26e4c9b. The new numbered rockspec uses that
archive/root and MD5 as supported by LuaRocks' rockspec format. The existing
v0.1.0 tag remains unchanged for earlier Conan/opam recipe references.

Built LuaRocks 3.13.0 as local publication tooling under ignored context/,
without installing a project dependency or changing system tooling. Retained
https://luarocks.org/releases/luarocks-3.13.0.tar.gz with SHA256
245bf6ec560c042cb8948e3d661189292587c5949104677f1eecddc54dbe7e37.
Restore with configure --prefix=<local tool directory> --with-lua=<Lua prefix>,
then make and make install. Lint and install of the numbered rockspec succeeded
from the remote tag, and the installed-module contract checks passed on Lua 5.4.
npm pack dry run confirms exactly the expected five JavaScript package files.

Extended the release utility for npm and LuaRocks. npm uses an isolated
temporary npmrc referencing NODE_AUTH_TOKEN in the child environment. LuaRocks'
documented client puts the API key in its request URL and may delegate HTTP to
curl, so the owned transport follows its check_rockspec/upload protocol directly
in Python with TLS and redirects disabled. It performs a rockspec-only upload;
the immutable source archive remains on GitHub. No upload key is passed to a
subprocess or saved in lasting config, and errors redact the key. Source:
luarocks/luarocks v3.13.0 src/luarocks/cmd/upload.lua and upload/api.lua.

The operator saved the workspace file; both npm and luarocks keys are now
available. LuaRocks' authenticated preflight passed and the rockspec upload
succeeded. The root manifest lists verbs 0.1.0-1, and the public module page is
https://luarocks.org/modules/antimemeai/verbs. A fresh registry-based install
into an isolated local rock tree succeeded; the installed module passes the
contract suite. The root verbs identity is now claimed by this publication.

npm's dry run passed, but actual upload returned EOTP requiring an additional
authenticator code. No jsverbs version has been published. Asked for either a
publishing token that permits 2FA bypass or a current npm_otp entry in the
workspace file. Added --otp-from-env to read that code only when explicitly
requested, pass it through NPM_CONFIG_OTP, and redact it with the API token.

The earlier JSR request expired before authorization. Started a new request
for @antimeme/verbs 0.1.0 and provided its fresh browser link. JSR remains
created with zero published versions until approval and server verification.

The operator deferred npm publication while sorting out its Chrome/passkey
authentication. Do not retry npm until the operator resumes it. The existing
credential and optional-code support remain available; no further npm request
was made after the deferral.

JSR authorization completed successfully as Patrick Beam. Deno published
@antimeme/verbs 0.1.0. The public package API confirms versionCount 1 and
latestVersion 0.1.0; the registry meta.json independently lists that version.
Public requests need a suitable User-Agent; an initial default urllib request
returned 403, while the normal release-check request succeeded. Publication:
https://jsr.io/@antimeme/verbs@0.1.0
