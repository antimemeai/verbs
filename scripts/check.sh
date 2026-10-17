#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

# Prefer rustup shims over an unrelated system Rust installation.
if [ -d "${HOME}/.cargo/bin" ]; then
    PATH="${HOME}/.cargo/bin:$PATH"
    export PATH
fi
cargo test
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cmake -S packages/cpp -B packages/cpp/build -DVERBS_BUILD_TESTS=ON
cmake --build packages/cpp/build
ctest --test-dir packages/cpp/build --output-on-failure
