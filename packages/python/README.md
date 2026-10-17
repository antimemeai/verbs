# Verbs for Python

```python
from pverbs import check
retries = check("bounded retries", 3, lambda n: 1 <= n <= 5)
```

`check` evaluates a synchronous predicate once and returns the original value
only for the boolean `True`; otherwise it raises `Violation` with a `constraint`
attribute. Predicate exceptions propagate. Later mutation can invalidate a check.
No runtime dependencies. Python 3.10 or newer.

Distribution and import name: `pverbs`, selected by the operator. `pyverbs` is
an unrelated published package. The initial API is experimental and MIT licensed.

Install with `pip install pverbs` after publication. From this directory,
`python -m unittest -v test_verbs` checks the source. From the repository root,
`uv build packages/python --out-dir packages/python/dist` builds the source
distribution and wheel, using setuptools as a build-only dependency.
There are no runtime or test dependencies beyond the Python standard library.

`python scripts/publish.py pypi` publishes the prepared files using the pypi
credential from ~/projects/.env. The utility passes the credential through the
child environment and does not persist it in this repository. Use --dry-run
to check the upload preparation without publishing.
