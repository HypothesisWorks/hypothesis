RELEASE_TYPE: minor

This release changes the behaviour of :func:`~hypothesis.strategies.floats`
when excluding signed zeros - ``floats(max_value=0.0, exclude_max=True)``
can no longer generate ``-0.0`` nor the much rarer
``floats(min_value=-0.0, exclude_min=True)`` generate ``+0.0``.

The correct interaction between signed zeros and exclusive endpoints was unclear;
we now enforce the invariant that :func:`~hypothesis.strategies.floats` will
never generate a value equal to an excluded endpoint (:issue:`2201`).

If you prefer the old behaviour, you can pass ``floats(max_value=-0.0)`` or
``floats(min_value=0.0)`` which is exactly equivalent and has not changed.
If you had *two* endpoints equal to zero, we recommend clarifying your tests by using
:func:`~hypothesis.strategies.just` or :func:`~hypothesis.strategies.sampled_from`
instead of :func:`~hypothesis.strategies.floats`.
