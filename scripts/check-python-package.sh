#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

uv build packages/python --out-dir packages/python/dist --clear --no-build-logs
for kind in wheel sdist; do
    environment="$PWD/context/python-$kind"
    uv venv --python 3.10 --clear "$environment"
    case "$kind" in
        wheel) artifact="$PWD/packages/python/dist/pverbs-0.1.0-py3-none-any.whl" ;;
        sdist) artifact="$PWD/packages/python/dist/pverbs-0.1.0.tar.gz" ;;
    esac
    uv pip install --python "$environment/bin/python" --no-deps --no-cache "$artifact"
    "$environment/bin/python" -I - "$PWD/packages/python/test_verbs.py" <<'PY'
import importlib.metadata
import importlib.util
from pathlib import Path
import sys
import unittest
import pverbs

assert 'site-packages' in Path(pverbs.__file__).parts, pverbs.__file__
assert importlib.metadata.version('pverbs') == '0.1.0'
assert not importlib.metadata.requires('pverbs')
assert Path(pverbs.__file__).with_name('py.typed').is_file()
spec = importlib.util.spec_from_file_location('test_installed_pverbs', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suite = unittest.defaultTestLoader.loadTestsFromModule(module)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
PY
done
