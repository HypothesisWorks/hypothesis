RELEASE_TYPE: minor

:func:`~hypothesis.strategies.functions` can now infer the appropriate ``returns``
strategy if you pass a ``like`` function with a return-type annotation.  Before,
omitting the ``returns`` argument would generate functions that always returned None.