local verbs = require("verbs")

for n = -10, 10 do
    local ok, result = pcall(verbs.check, "bounded", n, function(value)
        return value >= 1 and value <= 5
    end)
    if n >= 1 and n <= 5 then
        assert(ok and result == n)
    else
        assert(not ok and getmetatable(result) == verbs.Violation)
        assert(result.constraint == "bounded")
        assert(tostring(result) == "constraint violated: bounded")
    end
end

local value, calls = {}, 0
local checked = verbs.check("same", value, function(v)
    assert(rawequal(v, value))
    calls = calls + 1
    return true
end)
assert(rawequal(checked, value) and calls == 1)
assert(verbs.check("false value", false, function() return true end) == false)
assert(select("#", verbs.check("nil value", nil, function() return true end)) == 1)
assert(verbs.check("nil value", nil, function() return true end) == nil)

local sentinel = {}
local ok, err = pcall(verbs.check, "broken", 0, function() error(sentinel) end)
assert(not ok and rawequal(err, sentinel))

local function rejected(result)
    local passed, violation = pcall(verbs.check, "boolean", 0, function()
        return result
    end)
    assert(not passed and getmetatable(violation) == verbs.Violation)
    assert(violation.constraint == "boolean")
end
for _, invalid in ipairs({ false, 0, 1, "true", {}, function() end }) do
    rejected(invalid)
end
rejected(nil)
print("Lua contract checks passed: " .. _VERSION)
