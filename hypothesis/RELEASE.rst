RELEASE_TYPE: minor

This release is the start of our migration of Hypothesis internals from Python to Rust (:issue:`4740`).

As a start, this release migrates a simple internal helper to Rust. As of this release, Hypothesis now requires a rust toolchain to build from source (if not installing from a native wheel).

Hypothesis now ships native wheels for:

* Linux x86_64 (manylinux): 3.10, 3.11, 3.12, 3.13, 3.14, 3.14t, PyPy 3.11
* Linux x86_64 (musllinux): 3.10, 3.11, 3.12, 3.13, 3.14, 3.14t
* Linux aarch64 (manylinux): 3.10, 3.11, 3.12, 3.13, 3.14, 3.14t, PyPy 3.11
* Linux aarch64 (musllinux): 3.10, 3.11, 3.12, 3.13, 3.14, 3.14t
* macOS x86_64: 3.10, 3.11, 3.12, 3.13, 3.14, 3.14t, PyPy 3.11
* macOS arm64: 3.10, 3.11, 3.12, 3.13, 3.14, 3.14t, PyPy 3.11
* Windows x64: 3.10, 3.11, 3.12, 3.13, 3.14, 3.14t, PyPy 3.11
* Pyodide (wasm32-unknown-emscripten): 3.13

If you'd like Hypothesis to ship native wheels for a platform not mentioned here, please open an issue.
