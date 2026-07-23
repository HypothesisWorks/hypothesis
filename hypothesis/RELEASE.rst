RELEASE_TYPE: minor

:func:`~hypothesis.strategies.functions` now generates functions of the same
kind as the ``like=`` argument, so that async functions, generator functions,
and async generator functions can be imitated as well as plain functions
(:issue:`4149`).  ``pure=True`` is only supported for plain functions.

Generated generator functions yield a list of values drawn from ``returns``,
inferring e.g. ``returns=integers()`` from an ``Iterator[int]`` or
``AsyncIterator[int]`` return-type annotation, and generated async functions
follow Trio-style checkpoint semantics.
