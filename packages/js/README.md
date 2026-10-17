# Verbs

Named synchronous constraints for more verifiable agent-written code.

```js
import { check } from "jsverbs";
const retries = check("bounded retries", 3, n => n >= 1 && n <= 5);
```

`check(name, value, predicate)` evaluates the predicate exactly once and returns
the original value only if it returns `true`. Otherwise it throws `Violation`,
whose `constraint` property holds the name. Predicate exceptions propagate.
Use synchronous predicates: promises are rejected, as are other non-booleans.
An async predicate can still start work before rejection; do not pass one.

Values are omitted from errors. Checks apply at check time; later mutation can
invalidate a constraint. The 0.1.0 API is experimental. No runtime dependencies.

TypeScript on JSR uses `import { check } from "jsr:@antimemeai/verbs"` once
published. See https://github.com/antimemeai/verbs for registry status.
