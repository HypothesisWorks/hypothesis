RELEASE_TYPE: patch

This release improves test case reduction for recursive data structures.
Hypothesis now guarantees that whenever a strategy calls itself recursively
(usually this will happen because you are using :func:`~hypothesis.strategies.deferred`),
any recursive call may replace the top level value. e.g. given a tree structure,
Hypothesis will always try replacing it with a subtree.

Additionally this introduces a new heuristic that may in some circumstances
significantly speed up test case reduction - Hypothesis should be better at
immediately replacing elements drawn inside another strategy with their minimal
possible value.
