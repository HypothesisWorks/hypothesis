RELEASE_TYPE: patch

This patch fixes a longstanding performance problem in stateful testing (:issue:`3618`),
where state machines which generated a substantial amount of input for each step would
hit the maximum amount of entropy and then fail with an ``Unsatisfiable`` error.

We now stop taking additional steps when we're approaching the entropy limit,
which neatly resolves the problem without touching unaffected tests.
