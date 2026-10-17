-module(verbs_agent_check).
-export([run/0]).

run() ->
    lists:foreach(fun(N) ->
        Result = verbs_agent:check(<<"bounded">>, N, fun(V) -> V >= 1 andalso V =< 5 end),
        case N >= 1 andalso N =< 5 of
            true -> {ok, N} = Result;
            false -> {error, {constraint_violated, <<"bounded">>}} = Result
        end
    end, lists:seq(-10, 10)),
    Counter = make_ref(),
    put(Counter, 0),
    {ok, Counter} = verbs_agent:check(<<"same">>, Counter, fun(_) ->
        put(Counter, get(Counter) + 1), true
    end),
    1 = erase(Counter),
    Sentinel = make_ref(),
    Propagated = try
        verbs_agent:check(<<"broken">>, 0, fun(_) -> error(Sentinel) end),
        false
    catch error:Sentinel -> true end,
    true = Propagated,
    lists:foreach(fun(Invalid) ->
        {error, {constraint_violated, <<"boolean">>}} =
            verbs_agent:check(<<"boolean">>, 0, fun(_) -> Invalid end)
    end, [1, <<"true">>, [], #{}, undefined]),
    io:format("Erlang contract checks passed~n"),
    ok.
