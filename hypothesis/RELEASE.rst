RELEASE_TYPE: minor

:class:`~hypothesis.stateful.RuleBasedStateMachine` now chooses rules with
probability weighted by the amount of code under each rule, following Holmes et
al., "Using Relative Lines of Code to Guide Automated Test Generation for
Python" (ACM TOSEM 2020).  The first time a state machine runs in a process, a
short probe of 10 extra examples measures the lines of code each rule
calls into; the remaining examples then favour rules that exercise more code,
while every rule keeps at least a quarter of its uniform share.  Machines run
with fewer than 50 :obj:`~hypothesis.settings.max_examples`, or without the
:obj:`~hypothesis.Phase.generate` phase, are unaffected.

In our experiments on stateful tests from eight open-source projects at the
default budget, this covered significantly more branches on four of them and
was not significantly worse on any, at any budget we tried.
