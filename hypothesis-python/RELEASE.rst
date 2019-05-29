RELEASE_TYPE: minor

This release deprecates ``GenericStateMachine``, in favor of
:class:`~hypothesis.stateful.RuleBasedStateMachine`.  Rule-based stateful
testing is significantly faster, especially during shrinking.

If your use-case truly does not fit rule-based stateful testing,
we recommend writing a custom test function which drives your specific
control-flow using :func:`~hypothesis.strategies.data`.
