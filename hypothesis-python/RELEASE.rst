RELEASE_TYPE: patch

This release makes ``--hypothesis-show-statistics`` much more useful for
tests using a :class:`~hypothesis.stateful.RuleBasedStateMachine`, by
simplifying the reprs so that events are aggregated correctly.
