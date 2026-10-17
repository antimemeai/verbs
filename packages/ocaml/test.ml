let expect condition = if not condition then failwith "contract test failed"

let () =
  for n = -10 to 10 do
    match Verbs.check "bounded" n (fun n -> n >= 1 && n <= 5) with
    | Ok value -> expect (n >= 1 && n <= 5 && value = n)
    | Error error -> expect ((n < 1 || n > 5) && error.constraint_name = "bounded")
  done;
  let value = ref 7 in
  let calls = ref 0 in
  (match Verbs.check "same" value (fun _ -> incr calls; true) with
   | Ok result -> expect (result == value && !calls = 1)
   | Error _ -> failwith "accepted value rejected");
  let exception Predicate_error in
  let propagated =
    try
      ignore (Verbs.check "broken" 0 (fun _ -> raise Predicate_error));
      false
    with Predicate_error -> true
  in
  expect propagated
