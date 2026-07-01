RELEASE_TYPE: minor

This release is the start of our migration of Hypothesis internals from Python to Rust (:issue:`4740`).

As a start, this release migrates a simple internal helper to Rust. As of this release, Hypothesis now requires a rust toolchain to build from source (if not installing from a native wheel).

Hypothesis now publishes a wide variety of native wheels on PyPI.

Python versions: 3.10, 3.11, 3.12, 3.13, 3.14, 3.14t, and (except on musllinux) PyPy 3.11
Platforms: Linux x86_64/aarch64 manylinux/musllinux, macOS x86_64/arm64, Windows x64.

We additionally publish wheels for Pyodide (wasm32-unknown-emscripten) for Python 3.13 (`details <https://blog.pyodide.org/posts/314-release/>`__).

If you'd like Hypothesis to ship native wheels for a platform not mentioned here, please open an issue.
