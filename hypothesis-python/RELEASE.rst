RELEASE_TYPE: patch

This release modifies how Hypothesis selects operations to run during shrinking,
by causing it to deprioritise previously useless classes of shrink until others have reached a fixed point.

This avoids certain pathological cases where the shrinker gets very close to finishing and then takes a very long time to finish the last small changes because it tries many useless shrinks for each useful one towards the end.
It also should cause a more modest improvement (probably no more than about 30%) in shrinking performance for most tests.
