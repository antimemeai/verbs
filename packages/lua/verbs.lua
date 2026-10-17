-- Named synchronous constraints; success applies at check time.
local Violation = {}
Violation.__index = Violation

function Violation:__tostring()
    return "constraint violated: " .. self.constraint
end

local verbs = { Violation = Violation }

-- Evaluate once. Only boolean true passes; predicate errors propagate unchanged.
function verbs.check(name, value, predicate)
    if predicate(value) ~= true then
        error(setmetatable({ constraint = name }, Violation), 0)
    end
    return value
end

return verbs
