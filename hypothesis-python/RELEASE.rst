RELEASE_TYPE: minor

:obj:`hypothesis.stateful.GenericStateMachine` and
:obj:`hypothesis.stateful.RuleBasedStateMachine` now raise an explicit error
when instances of :obj:`hypothesis.settings` are assigned to the classes'
settings attribute. Error directs users to use correct assignment methods.
