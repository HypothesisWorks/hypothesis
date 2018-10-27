RELEASE_TYPE: minor

:obj:`hypothesis.stateful.GenericStateMachine` and
:obj:`hypothesis.stateful.RuleBasedStateMachine` now raise an explicit error
when instances of :obj:`hypothesis.settings` are assigned to the classes'
settings attribute, which is a no-op (:issue:`1643`). Instead assign to
``SomeStateMachine.TestCase.settings``, or use ``@settings(...)`` as a class
decorator to handle this automatically.
