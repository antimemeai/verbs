(** Named runtime constraints, evaluated once at the time of the call. *)

type violation = { constraint_name : string }

val check : string -> 'a -> ('a -> bool) -> ('a, violation) result
(** [check name value predicate] returns [Ok value] when the predicate passes,
    or [Error {constraint_name = name}]. Predicate exceptions propagate.
    Later mutation can invalidate a constraint. *)
