RELEASE_TYPE: minor

Warns when constructing a `repr` that is overly long. This can
happen by accident if stringifying arbitrary strategies, and
is expensive in time and memory. The associated deferring of
these long strings in :func:`~hypothesis.strategies.sampled_from`
should also lead to improved performance.
