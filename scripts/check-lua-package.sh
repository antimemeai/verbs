#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

rockspec="$PWD/packages/lua/verbs-0.1.0-1.rockspec"
luarocks_bin="${LUAROCKS_BIN:-$PWD/context/toolchains/luarocks/bin/luarocks}"
tree="$PWD/context/lua-release"
"$luarocks_bin" lint "$rockspec"
"$luarocks_bin" build "$rockspec" --tree="$tree" --deps-mode=none
LUA_PATH="$tree/share/lua/5.4/?.lua;;" "${LUA_BIN:-lua5.4}" packages/lua/test/check.lua
