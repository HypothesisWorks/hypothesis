---
name: porting
description: Port a Hypothesis module from Python to Rust faithfully, without changing behavior or structure, and differential-test the port against the original. Use when translating a module, function, or file from hypothesis/src/hypothesis/ into the native Rust extension as part of the Python-to-Rust engine migration, or when verifying that a just-finished port behaves identically to the Python it replaced.
---

This skill is for the Hypothesis Python-to-Rust engine migration (HypothesisWorks/hypothesis#4740). It is temporary — we delete it when the migration is done. It governs how to port a Python module to Rust.

A "port" is a straight-line, line-for-line translation of existing Python into Rust. It is **not** a rewrite, a refactor, a cleanup, or a redesign. The Python is the spec, down to its structure and comments.

The prime directive: **port exactly.** A reviewer holding the Python and the Rust side by side should be able to see, function by function and line by line, that they do the same thing the same way. Obvious equivalence is the whole deliverable — if a reader has to think hard to convince themselves the two are equivalent, the port has failed even if it is correct. Exactly one rule outranks this: ported code stays pure Rust and never handles Python objects (see "Keep ported code pure Rust"), and that rule may force a divergence from an exact port — but only with human approval.

## How the migration is wired

- Native code lives in `hypothesis/rust/` — PyO3 declarative modules (`#[pyo3::pymodule]`), built with maturin, exposed to Python as `hypothesis._native.*`. The submodule tree mirrors the Python package, so `hypothesis/internal/floats.py` ports into `hypothesis._native.internal.floats`.
- The original Python module (e.g. `hypothesis/src/hypothesis/internal/floats.py`) becomes a thin shim that re-exports the ported functions from the native module (`from hypothesis._native.internal.floats import next_up as next_up, ...`, with the explicit `as` so mypy's `no_implicit_reexport` treats them as re-exported). Everything that imports `from hypothesis.internal.floats import ...` keeps working unchanged.
- Pieces that genuinely cannot move (see below) stay defined in the shim alongside the re-exports.

# Keep ported code pure Rust

The migration's end state is native Rust, so every Python-object handle left in a port is future rework. **By default, ported Rust must not use `Bound`, `Py`, `PyAny`, or any dynamic Python-object handling.** No `.extract()`/`.downcast()` in the logic, no calling Python operators or methods on objects (`x.le(y)`, `x.eq(0.0)`, `x.repr()`), no `Bound<'_, PyAny>` parameters or returns. Ported functions work on Rust scalars (`f64`, `u64`, `bool`, …).

**This rule outranks "port exactly."** Where a literal translation would only be possible by handling Python objects, purity wins over line-for-line fidelity — but only through the human gate below. The default is still an exact port; the no-`Bound`/`Py` rule is the *one* thing allowed to force a divergence.

**Scope — what's banned vs. allowed.** The ban is on *dynamic Python-object handling*, not on PyO3 itself. The module scaffolding every ported function needs is fine and expected: `#[pyo3::pymodule]`, `#[pyfunction]`, `PyResult`, returning a `PyErr`/`PyOverflowError`, and PyO3's automatic scalar conversion at the boundary. Raising a `PyErr` is allowed; *needing a `Bound` to construct it* — e.g. reading `repr(x)` off the original object for a message — is not, and trips the gate.

**When a faithful port would require `Bound`/`Py`, stop and consult the human.** Don't reach for `Bound` on your own, and don't silently pick a path. Present both options with a recommendation:

- **Don't port it** — leave the function defined in the Python shim. Correct when the behavior genuinely depends on Python semantics: `int`/`float` polymorphism, arbitrary-precision `int`, exact large-int comparison. `clamp` and `sign_aware_lte` stay in Python for exactly this — they run on unbounded ints, which no `f64` signature can hold (and coercing a huge `int` at an `f64` boundary would itself raise `OverflowError`).
- **Adapt the Rust** — port it, but change the implementation to work on Rust scalars, accepting a documented behavior difference. Correct when the Python type is incidental, not contract. `is_negative` takes `f64` (`x.is_sign_negative()`); the only casualty is the custom `TypeError` message on non-float input, which nothing depends on.

Only use `Bound`/`Py` in ported code with explicit human approval, as a deliberate exception. An adapted port and an approved-`Bound` port are the two cases that carry a marker comment (see "Preserve comments").

# Port exactly

Translate the Python as literally as Rust allows. Do not add, do not remove, do not rearrange, do not "improve."

## Preserve comments — verbatim, and only the Python's

The only comments in the port are verbatim copies of the Python's own comments, carried to the corresponding spot (a `#` comment becomes a `//` comment; a docstring becomes a `///` doc comment). Copy them unchanged — don't reword them, don't drop ones that seem redundant.

Add **no** new comments of any kind. Not migration notes ("ported to Rust", "this is now a shim", "moved from X"), not cross-file pointers ("see rust/src/internal/floats.rs"), not restatements of what an import path or name already says. Deviation rationale goes to the human directing the port (see "Surface every deviation"), never into the source — with **one exception**: a function that deliberately departs from a literal translation (an adapted port, or a `Bound`/`Py` port the human approved — see "Keep ported code pure Rust") carries one short comment marking it as such: what diverges and that it was approved, so a reviewer comparing Python and Rust side by side reads the mismatch as sanctioned, not a bug. That marker is the *only* deviation rationale that belongs in source; all other reasoning lives in the report.

The Python module you leave behind is a shim that only *loses* code (function bodies become imports); it gains nothing, so it gets no new comments at all.

## Preserve structure, order, and names

- Keep functions, constants, and types in the **same order** as the Python module.
- Keep the **same control flow shape**: same branches, same early returns, same recursion, same loop structure. If the Python has three `if/elif/else` arms, the Rust has three `match`/`if` arms — not one clever expression that covers all three.
- **Names** may be adjusted to fit Rust idiom (e.g. `SCREAMING_CASE` Python constants becoming ordinary Rust items), but keep the correspondence obvious — a reader should immediately see which Python name each Rust name came from. The names PyO3 exposes to Python must match what the call sites import (`next_up`, `float_to_int`, …), since the shim re-exports them by name.
- Mirror the Python's **decomposition**: same helper functions, same inlining decisions. Don't introduce a new helper to deduplicate something the Python repeated, and don't inline a helper the Python factored out.

## Do not simplify, and do not substitute "equivalent" code

Do not replace the Python's formulation with a different one, even when you are certain they are semantically equivalent, and even when yours is shorter or cleaner. Review clarity and obvious equivalence matter more than elegance at this stage.

A clever reformulation forces the reviewer to *prove* equivalence instead of *seeing* it. That is exactly the work the port is supposed to save them.

## Do not drop assertions or validation

Value and invariant assertions — `assert x <= y`, `assert 0 <= e <= MAX_EXPONENT`, bounds and range checks — are behavior. Port them with `assert!`/`debug_assert!`, even when you believe they can't fail. (A failed Rust `assert!` surfaces as `PanicException` rather than `AssertionError`; that's an accepted consequence — report it as a deviation to the human, don't contort around it.)

The exception is a pure *type* assertion that Rust's type system already enforces and that has nothing to translate to — e.g. `assert isinstance(value, float)` has no expression in Rust when the parameter is already typed `f64`. Dropping that is fine: it's not a behavior change, just a redundancy the type system absorbs.

## Match behavior exactly, including the corners

Never justify a behavior difference with "that input never occurs in practice." The port's contract is the Python's contract, for every input the Python handles. If you genuinely cannot match a corner, that is a forced deviation — handle it as below, don't paper over it.

**For errors, match _whether_ it fails, not always _which_ exception.** Two different things hide under "match the error":

- *Raise vs. return* is always part of the contract. If the Python raises on an input, the Rust must also fail on that input — never return a value there. So don't use `wrapping_*` or saturating casts to turn an overflow into a wrong number; use `checked_*().unwrap()` / `try_into().unwrap()` so it actually fails (a panic is a real failure; a wrong value is not).
- *Which exception type and message* only matters when something observable depends on it — a caller does `except ThatType`, or a test asserts the message. Reproduce it then, and only then. Otherwise any failure will do; don't go out of your way to forge the Python exception.

Decide per case by asking "does any caller catch this, or any test assert it?" Don't reach for `PyKeyError`/`PyOverflowError`/`PyTypeError` unless that specific type is the thing being observed.

# Do not optimize

Performance is not a porting concern.

- **FFI/call overhead is irrelevant.** Do not decide *what* to port, or *whether* to port a function, based on the cost of crossing the Python/Rust boundary. If a trivial one-line function is in scope, port it; do not leave it in Python because "the FFI hop isn't worth it."
- **Do not change the algorithm.** Keep the Python's algorithm and its complexity. (Straight-line porting won't tempt you toward an asymptotically worse algorithm — but it also means you don't get to pick a *better* one. Same algorithm, same shape.)
- Micro-optimizations, caching, and restructuring "while you're in there" are all out of scope.

# When an exact port is genuinely impossible

Sometimes Rust cannot express the Python faithfully. The bar is **meaningfully impossible**, not "awkward" or "less pretty." The recurring cases in this migration:

- **A Python builtin raises implicitly where Rust doesn't.** `struct.pack("!e"/"!f", x)` raises `OverflowError` on a finite value too large for the format; Rust's `as f32` / `half::f16::from_f64` saturate to infinity. To match, add an explicit check and `return Err(PyOverflowError::new_err(...))`. Some Python code relies on this (e.g. the width-downcast `reject()` in `strategies/_internal/numbers.py`).
- **Arbitrary-precision `int` vs fixed-width.** A Python `int` has no bound; `u64`/`i64` do. If a function can return a value exceeding `u64`, no `u64` return is faithful — use a wider type or surface the narrowing. A function that operates on both `int` and `float` and depends on `int` being exact (e.g. `clamp`, `sign_aware_lte`, called on huge ints) has no faithful `f64` signature. Do **not** rescue it with `&Bound<'_, PyAny>` + Python operators (`x.le(y)`) — that is the banned path (see "Keep ported code pure Rust"). Stop and consult the human; the usual resolution is to leave such a function in the Python shim (`clamp` and `sign_aware_lte` both stayed there for this reason).
- **A Rust type isn't available.** `f16` is unstable, so width-16 work needs the `half` crate. Adding a dependency is a real change; flag it.
- **An exception type or message that is observed.** When a caller catches a specific type or a test asserts a message, reproduce it exactly (e.g. `float_of`'s `OverflowError`). When nothing observes it, don't — see "Match behavior exactly" above. If reproducing an observed *message* would require a `Bound` (e.g. reading `repr(x)` off the original object), that trips the no-`Bound` gate — consult the human (see "Keep ported code pure Rust").

When you hit one of these:

1. Deviate as little as possible — change only what's forced.
2. Do not annotate it in the code — no explanatory comment. The reasoning goes in the report to the human, never in the source.
3. **Surface it** (next section).

Deciding to leave something in Python is the human's call — surface it, don't silently keep it and rationalize. FFI/call cost is never a reason (see "Do not optimize"). Needing `Bound`/`Py` to port faithfully **is** a legitimate reason to leave a function in Python — but it's still the human's choice between that and an adapted port, so consult rather than defaulting either way (see "Keep ported code pure Rust"). Genuine hard technical blockers are rare: Rust can import and call Python at runtime, so even a cycle-breaking local import like `make_float_clamper` → `choice_permitted` isn't a hard blocker — keeping that in Python is a scope call for the human, not a necessity. Whatever stays, stays in the shim.

# Surface every deviation

The port's companion deliverable is an explicit, complete list — reported to the human directing the port — of **every place the Rust is not a literal translation of the Python**, with the reason for each. This report is the *only* place deviation rationale lives; it never goes into source comments. Nothing in this list should be a surprise to the reviewer. Include, at minimum:

- forced deviations (type changes, added overflow checks, the `half` dependency, error-type/message changes, `assert!` → `PanicException`)
- adapted ports (a function given a Rust-scalar signature at the cost of a behavior difference, e.g. a dropped error message) and any human-approved `Bound`/`Py` usage
- anything you kept in Python (in the shim) instead of porting, and why
- anything you believe should be deleted/changed but didn't touch
- any corner where you are not 100% certain the Rust matches the Python

If the list is empty, say so. A port with hidden deviations is worse than one with disclosed ones, because the reviewer trusts it.

# Verify by differential testing against the Python

The strongest evidence a port is faithful is running the old Python and the new Rust on the same inputs and diffing the results. A difftest exists to answer one question in the moment — *does the new implementation produce identical output to the old one?* — so it is **ephemeral scaffolding**: write it, run it, read the result, delete it. **Never commit or merge a difftest, and never `git add` it.** The day the port lands there is only one implementation, so the test is dead weight.

## Old vs. new: two installations, not two copies in the tree

Compare two *installations*. Do **not** keep an old and new copy of the module side-by-side in the working tree "so they can be compared" — we ship only the new one. The old one comes from a separate checkout.

- **New** is your working tree; build it so the extension is compiled and importable (`maturin develop`, or `./build.sh check-py314` — whatever gives you a built, importable `hypothesis`).
- **Old** is a throwaway git worktree at the last commit where the target module is still unported (usually `git merge-base HEAD master`, or the commit just before your port), with the package directory renamed so it imports under a different name:

```bash
base=$(git merge-base HEAD master)
git worktree add /tmp/hyp-base "$base"
mv /tmp/hyp-base/hypothesis/src/hypothesis /tmp/hyp-base/hypothesis/src/hypothesis_old
```

Renaming the directory (not its internal import strings) is deliberate. `import hypothesis_old` resolves to the old bodies, while the old code's absolute `from hypothesis... import ...` lines fall through to the **new** installed `hypothesis`. That fall-through is the feature: it isolates the difference to exactly the module you ported — every other dependency is identical old-vs-new by construction.

The one sharp edge: do **not** load a second copy of the compiled `_native` extension. It self-registers in `sys.modules` as `hypothesis._native`, so a second copy collides. You never need one — the old Python reaches `_native` via its absolute import, which resolves to the already-built new extension.

## Write it and run it

Put the script outside the package (e.g. `/tmp/difftest.py`) so there's no chance of committing it. Import both sides and assert **bit-exact** equality over a meaningful input set:

```python
import sys

sys.path.insert(0, "/tmp/hyp-base/hypothesis/src")

from hypothesis_old.internal.floats import next_up as old

from hypothesis.internal.floats import next_up as new
```

- Drive both with a large randomized input set **plus** hand-picked edge cases: NaN (both signs and non-canonical payloads), ±0.0, infinities, subnormals, overflow/narrowing boundaries, max/min finite, and invalid inputs that should raise (bad widths, wrong types).
- Compare for **exact** equality — mind `float` NaN and `-0.0`: compare via `math.isnan` / `float_to_int` / `struct.pack("!d", x)` where bit-identity matters.
- Compare **whether** each side raises; per "Match behavior exactly," only require the same exception type/message where something observes it — both-fail is a match.
- Lean on the existing suite too: because the shim keeps the same import path, the module's own tests (and every module that imports it) exercise the Rust for free. `maturin develop`, then run them.

Run a difftest when it will actually tell you something — at a checkpoint after porting a function or cohesive group, before opening or updating the PR, or when a regular test fails in a way that might be a behavioral divergence. It's a checkpoint tool, not a keystroke tool. And don't let one that "mostly passes" slide: a single mismatch is either a bug in the port or a forced deviation you need to surface — never "close enough."

# Hygiene

- Don't leave build artifacts or scratch state in the tree: the `maturin develop` virtualenv, `hypothesis/rust/target/`, compiled `_native.*.so`, throwaway differential-test scripts. Remove them (or confirm they're git-ignored) before finishing.
- A PR that changes `hypothesis/src/` needs a `RELEASE.rst`; a port that only moves code between languages is internal and not user-visible, so decide whether one is warranted and say which.
- Don't mutate branch/worktree state (resets, rebases, changing the PR base) beyond what the task requires without saying so.

# Rust style guide

* Prefer match statements over if statements where appropriate. For example:

    ```
    if width == 64 {
        Ok(x)
    } else if width == 32 {
        int_to_float(float_to_int(x, 32)?, 32)
    } else {
        int_to_float(float_to_int(x, 16)?, 16)
    }
    ```

    should be written as a match instead.
