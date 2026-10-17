# Verbs for Erlang

Provisional Hex identity and OTP application: `verbs_agent`; not published.
The existing `verbs` Hex package is an unrelated conjugation library.
No runtime dependencies beyond Erlang/OTP's kernel and stdlib.

```erlang
{ok, Retries} = verbs_agent:check(<<"bounded retries">>, 3,
    fun(N) -> N >= 1 andalso N =< 5 end).
```

The synchronous predicate runs once. Only true passes; rejection returns
`{error, {constraint_violated, Name}}`, with Name a binary. Predicate errors,
throws, and exits propagate. Values stay out of errors. Success checks the term
at call time; it cannot guarantee mutable state addressed by a term stays valid.
Elixir can call the Erlang module directly. The 0.1.0 API is experimental and
MIT licensed.

Run `../../scripts/check-footprints.sh erlang` here. `rebar3 compile` builds the
OTP application. Hex publication additionally needs the rebar3 Hex plugin and
authentication; no plugin or package has been adopted or published here.
