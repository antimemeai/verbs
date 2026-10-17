# Verbs for Python

```python
from verbs_agent import check
retries = check("bounded retries", 3, lambda n: 1 <= n <= 5)
```

`check` evaluates a synchronous predicate once and returns the original value
only for the boolean `True`; otherwise it raises `Violation` with a `constraint`
attribute. Predicate exceptions propagate. Later mutation can invalidate a check.
No runtime dependencies. Python 3.10 or newer.

Proposed distribution name: `verbs-agent`. `pyverbs` is already an unrelated
published package. This directory is source only: a build backend and PyPI
authentication must be configured before publication. Do not attempt to publish
under `pyverbs`. The initial API is experimental.
