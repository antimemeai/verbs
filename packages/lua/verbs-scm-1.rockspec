rockspec_format = "3.0"
package = "verbs"
version = "scm-1"
source = {
    url = "git+https://github.com/antimemeai/verbs.git",
    branch = "main",
}
description = {
    summary = "Explicit, named constraints for more verifiable agent-written code",
    detailed = [[Evaluate a synchronous predicate once, returning the original
        value or raising a named violation. Predicate errors propagate.]],
    homepage = "https://github.com/antimemeai/verbs",
    issues_url = "https://github.com/antimemeai/verbs/issues",
    license = "MIT",
}
dependencies = { "lua >= 5.1, < 5.6" }
build = {
    type = "builtin",
    modules = { verbs = "packages/lua/verbs.lua" },
}
