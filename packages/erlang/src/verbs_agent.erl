%% Named synchronous constraints. A success applies at check time.
-module(verbs_agent).
-export([check/3]).

-spec check(binary(), T, fun((T) -> boolean())) ->
    {ok, T} | {error, {constraint_violated, binary()}}.
check(Name, Value, Predicate) when is_binary(Name), is_function(Predicate, 1) ->
    case Predicate(Value) of
        true -> {ok, Value};
        _ -> {error, {constraint_violated, Name}}
    end.
