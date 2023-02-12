RELEASE_TYPE: patch

This patch adds the ``_min_stateful_steps`` argument to the ``run_state_machine_as_test`` function, allowing users to
specify the minimum number of steps that the state machine should execute during testing.
Note that ``_min_stateful_steps`` is not a part of Hypothesis' public API and should not be used directly, as it may be
subject to change or removal in future versions of Hypothesis.
