# Design: a better heuristic for optimising `target()` metrics

Issue: https://github.com/HypothesisWorks/hypothesis/issues/3176

## Problem

The targeted-PBT optimiser (`hypothesis.internal.conjecture.optimiser.Optimiser`)
currently runs **exactly once**, at the halfway point of the `max_examples`
budget. In `ConjectureRunner.generate_new_examples`:

```python
optimise_at = max(self.settings.max_examples // 2, small_example_cap + 1, 10)
ran_optimisations = False
...
if self.valid_examples >= max(small_example_cap, optimise_at) and not ran_optimisations:
    ran_optimisations = True
    self.optimise_targets()
```

This is well tuned for the default budget of 100 examples, but degrades for
large budgets used in exploratory searches:

- With `max_examples=100_000`, we run 50k purely random examples before any
  hill-climbing starts, even though random generation has usually stopped
  producing new best scores long before that.
- `optimise_targets()` runs until it goes dry (no improvements and no new
  calls), then never runs again. Any better seed found by generation in the
  second half of the run is never hill-climbed from.
- Conversely, a single pass has no per-pass call ceiling, so on an easy
  unbounded score it can consume most of the remaining budget in one go.

## Goals and non-goals

Goals:

1. **No behaviour change for small budgets.** `max_examples < 1000` keeps the
   current single-pass-at-half-budget behaviour, which is well tested.
2. **Start optimising early for large budgets** (after ~200 valid examples),
   so exploratory searches get most of their budget applied to climbing.
3. **Interleave generation and optimisation**, still aiming to spend roughly
   half the total budget on optimisation, so late lucky seeds from generation
   can still be exploited.
4. **A principled criterion for repeated passes** that avoids the wasteful
   re-run behaviour we've seen from the Pareto optimiser.

Non-goals:

- Changing the hill-climbing algorithm itself (`Optimiser.hill_climb`).
- Changing the Pareto front machinery, beyond when `pareto_optimise` is invoked.
- Any public API or settings change. This is all `internals` + `performance`.

## Proposed design

### Scheduling state

Add a small amount of scheduling state to `ConjectureRunner` (or a tiny
`TargetingSchedule` helper object, if it reads better):

- `self._target_valid_budget: int` — valid examples we're willing to spend on
  optimisation in total: `max_examples // 2`.
- `self._target_valid_spent: int` — valid examples consumed inside
  `optimise_targets` passes so far (measure by diffing `self.valid_examples`
  around each pass).
- `self._next_optimise_at: int` — the `valid_examples` threshold for the next
  pass.
- `self._last_pass_yield: float` — `improvements / calls` of the previous pass.
- `self._best_scores_at_last_pass: dict[str, float]` — snapshot of
  `self.best_observed_targets` when the last pass finished.

### Schedule

In `generate_new_examples`, replace the `ran_optimisations` one-shot with:

- **Small budgets** (`max_examples < 1000`): unchanged — one pass at
  `max(max_examples // 2, small_example_cap + 1, 10)`, no per-pass ceiling.
  (Implemented as: first pass at the current threshold, and the repeat
  criterion below never fires because the remaining budget is 0.)
- **Large budgets** (`max_examples >= 1000`): first pass at
  `max(200, small_example_cap + 1)` valid examples. Subsequent passes are
  scheduled by the repeat criterion below, and each pass gets a per-pass
  ceiling so it cannot eat the whole run:
  `pass_budget = max(200, remaining_target_budget // 4)` valid examples,
  enforced by passing a call/valid-example ceiling down into
  `optimise_targets` (a new `max_valid` parameter checked between
  `Optimiser` runs and inside the `while True` loop).

Overall cap: stop scheduling passes once
`self._target_valid_spent >= self._target_valid_budget`, so the ~50/50 split
between generation and optimisation is preserved in aggregate.

### Repeat criterion

After a pass finishes, schedule the next one when **either**:

1. **Fresh material**: generation (or mutation) produces a new best score for
   any target — i.e. `self.best_observed_targets` has improved over
   `self._best_scores_at_last_pass`. A better seed is exactly the situation
   where re-climbing is likely to pay off. To avoid thrashing, require at
   least `pass_budget // 2` valid examples of generation since the last pass
   before acting on this signal; **or**
2. **Fair-share fallback**: the run has spent as many valid examples on
   generation since the last pass as that pass consumed, **and** the last
   pass's yield (`improvements / calls`) was above a small threshold
   (e.g. 1%). This keeps the interleaving going while scores are still
   improving, and stops re-running a dry optimiser — the failure mode the
   issue calls out for the Pareto optimiser.

If neither fires, generation simply continues and uses the rest of the budget,
which is the correct behaviour once the optimiser has plateaued.

`pareto_optimise()` stays where it is — only invoked from within
`optimise_targets` once hill-climbing goes dry within a pass — but now also
benefits from the per-pass ceiling.

### Interaction with existing exit logic

- `should_generate_more()` is checked inside `Optimiser` via
  `engine.cached_test_function` → `test_function` raising `RunIsComplete`,
  so passes already terminate cleanly at budget exhaustion; the per-pass
  ceiling is purely about *sharing* budget, not about correctness.
- The `Phase.target`-without-`Phase.generate` path in `_run` keeps calling
  `optimise_targets()` once, unbudgeted, as today.
- `max_improvements` keeps its exponential ramp (10, 20, 40, …) but the
  ramp state persists across passes, so later passes may climb further per
  target rather than re-verifying easy wins.

### Rough implementation order

1. Extract the pass-trigger decision into a
   `ConjectureRunner._should_optimise_now()` method; add the scheduling state.
2. Add the `max_valid` ceiling to `optimise_targets`.
3. Wire the repeat criterion into the generate loop.
4. Benchmarks + tests (below), tune the two constants (start-at 200, yield
   threshold) against the benchmark suite.

## Measuring success

There are currently **no targeting benchmarks** in `tests/quality/`; the
existing coverage is functional only (`tests/nocover/test_targeting.py`,
`tests/cover/test_targeting.py`). Step one is to build the measurement
harness, before changing the heuristic.

### Benchmark suite (`tests/quality/test_targeting_quality.py`)

Standard tasks, each run over ~10 seeds with `database=None`:

- **Threshold-bug discovery** (primary metric): a test that fails once a
  target-correlated score crosses a threshold, e.g. `sum(ls) >= N` or the
  existing "x > 100" shape from `test_reports_target_results`. Metric: number
  of test-function calls until the bug is found (`runner.call_count` at exit),
  or budget exhausted. This measures what users of exploratory targeting
  actually care about: time-to-bug.
- **Score maximisation**: bounded score tasks (so unbounded blow-up doesn't
  distort results), e.g. `min(sum(ls), cap)` and the square-loss task from
  issue #2395 (`-(d - 42.5) ** 2`). Metric: best observed score at budget
  exhaustion (`runner.statistics["targets"]`), plus calls-to-reach a fixed
  score threshold.
- **No-target control**: a task without `target()` calls, to confirm the
  scheduler adds no overhead when there is nothing to optimise.

Each task runs at `max_examples ∈ {100, 1_000, 10_000}`. The engine's
per-phase statistics (`statistics["target-phase"]["test-cases"]`) let us also
assert the budget split directly.

### Success criteria

1. **No regression at the default budget**: at `max_examples=100`, both
   metrics within noise of current master (paired comparison over seeds).
2. **Large-budget improvement**: at `max_examples=10_000`, median
   calls-to-bug / calls-to-threshold-score improves materially (target:
   ≥2x on at least the threshold-discovery tasks — going from "climbing
   starts at call ~5000" to "~200" should dominate here).
3. **Budget split holds**: target-phase valid examples between ~20% and ~55%
   of the total on tasks where scores keep improving, and near the current
   behaviour when the optimiser plateaus immediately.
4. **No pathological re-runs**: on a task whose score plateaus early (e.g. a
   constant score), the number of optimisation passes after the plateau is 0
   — checked via a unit test on the yield criterion, guarding against the
   Pareto-style waste mentioned in the issue.
5. **Existing suite green**, notably `test_issue_2395_regression`,
   `test_targeting_can_be_disabled` (relies on targeting being strictly
   better than not), and the statistics/phases tests.

Wall-clock overhead of the scheduler itself is negligible by construction
(a few integer comparisons per generated example), so we measure in
test-function calls, which is the resource that matters.

### Keeping it honest over time

The seed-averaged quality tests from the benchmark suite get committed as
`tests/quality/` tests with generous margins (like
`test_can_find_high_scores` style assertions), so future engine changes can't
silently regress targeting at large budgets — that gap is how the current
behaviour went unnoticed.
