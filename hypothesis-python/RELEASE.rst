RELEASE_TYPE: minor

This release teaches :class:`~hypothesis.stateful.RuleBasedStateMachine` to avoid
checking :func:`~hypothesis.stateful.invariant`\ s until all
:func:`~hypothesis.stateful.initialize` rules have been run.  You can enable checking
of specific invariants for incompletely initialized machines by using
``@invariant(check_during_init=True)`` (:issue:`2868`).

In previous versions, it was possible if awkward to implement this behaviour
using :func:`~hypothesis.stateful.precondition` and an auxiliary variable.
