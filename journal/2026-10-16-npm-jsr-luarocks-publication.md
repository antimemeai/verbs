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
