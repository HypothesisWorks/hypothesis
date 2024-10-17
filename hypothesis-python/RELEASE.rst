RELEASE_TYPE: minor

This release changes :class:`hypothesis.stateful.Bundle` to use the internals of
:func:`~hypothesis.strategies.sampled_from`, improving the `filter` and `map` methods.
In addition to performance improvements, you can now ``consumes(some_bundle).filter(...)``!

Thanks to Reagan Lee for this feature (:issue:`3944`).