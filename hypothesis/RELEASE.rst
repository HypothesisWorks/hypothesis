RELEASE_TYPE: minor

Swarm testing of :class:`~hypothesis.stateful.RuleBasedStateMachine` rules now
respects bundle dependencies.  Previously, when swarm testing disabled the only
rule that adds values to a :class:`~hypothesis.stateful.Bundle`, every rule that
takes arguments from that bundle was silently disabled too, for the whole test
case.  Now a rule that produces into a bundle is enabled whenever an enabled
rule consumes from it (transitively), as in TSTL's swarm testing.  Machines
without bundles generate exactly the same test cases as before.
