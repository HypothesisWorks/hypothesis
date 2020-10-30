RELEASE_TYPE: minor

Hypothesis now shrinks examples where the error is raised while drawing from
a strategy.  This makes complicated custom strategies *much* easier to debug,
at the cost of a slowdown for use-cases where you catch and ignore such errors.
