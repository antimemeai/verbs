import assert from "node:assert/strict";
import { test } from "node:test";
import { check, Violation } from "./index.js";

test("accepts exactly the allowed range and names violations", () => {
  for (let n = -10; n <= 10; n++) {
    if (n >= 1 && n <= 5) {
      assert.equal(check("bounded", n, n => n >= 1 && n <= 5), n);
    } else {
      assert.throws(() => check("bounded", n, n => n >= 1 && n <= 5),
        error => error instanceof Violation && error.constraint === "bounded"
          && error.message === "constraint violated: bounded");
    }
  }
});

test("preserves identity and calls once", () => {
  const value = {};
  let calls = 0;
  assert.equal(check("same", value, () => { calls++; return true; }), value);
  assert.equal(calls, 1);
});

test("propagates predicate exceptions and rejects non-boolean success", () => {
  const error = new Error("broken predicate");
  assert.throws(() => check("broken", 0, () => { throw error; }), e => e === error);
  for (const invalid of [1, "true", {}, Promise.resolve(false), null, undefined]) {
    assert.throws(() => check("boolean", 0, () => invalid), Violation);
  }
});
