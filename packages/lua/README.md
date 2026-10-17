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

The development rockspec tracks main. Before a numbered release, create an
immutable source release containing Lua and give its rockspec the matching
version and source reference. The existing v0.1.0 tag has no Lua module.
Publication requires LuaRocks authentication. Personal user namespaces are
supported, for example `antimemeai/verbs`; preparing these files claims neither
the root name nor a user namespace.
