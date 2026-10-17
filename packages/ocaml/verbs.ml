type violation = { constraint_name : string }

let check name value predicate =
  if predicate value then Ok value else Error { constraint_name = name }
