# Verbs for Lua

Prepared LuaRocks identity: `verbs`; not uploaded or reserved. Pure Lua,
compatible with Lua 5.1 through 5.5 and LuaJIT. No other rocks are required.

```lua
local verbs = require("verbs")
local retries = verbs.check("bounded retries", 3, function(n)
    return n >= 1 and n <= 5
end)
```

The synchronous predicate runs once. Only boolean true passes. Success returns
the original value, including nil or false. Rejection raises a Violation table
with a constraint field and a readable tostring representation; pcall catches
that table. Check its type with `getmetatable(err) == verbs.Violation`.
Predicate errors propagate unchanged. Checks apply at call time; later mutation
can invalidate them. Values stay out of errors. The API is experimental and
MIT licensed.

Run `./scripts/check-footprints.sh lua` from the repository root, or set LUA_BIN
to a particular interpreter. From the root, `luarocks lint
packages/lua/verbs-scm-1.rockspec` validates the rockspec, and `luarocks make
packages/lua/verbs-scm-1.rockspec --tree=context/lua-rocks` installs locally.

The development rockspec tracks main. The numbered verbs-0.1.0-1.rockspec uses
the immutable lua-v0.1.0 source tag and its archive checksum. The older v0.1.0
tag has no Lua module. Run scripts/check-lua-package.sh from the repository root
to lint and install the numbered rockspec and check its installed module.

`python scripts/publish.py luarocks` reads the luarocks credential in
~/projects/.env and uploads the numbered rockspec through LuaRocks' official
API. This publishes a rockspec whose source archive stays on GitHub; no binary
rock or source-rock file is needed. The authenticated HTTP request stays inside
the process, with no API key in command arguments or persistent CLI config.
Use --dry-run for the authenticated name/version check without an upload.

Publication requires LuaRocks authentication. Personal user namespaces are
supported, for example `antimemeai/verbs`; preparing these files claims neither
the root name nor a user namespace.
