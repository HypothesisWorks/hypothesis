RELEASE_TYPE: minor

This release makes :func:`~hypothesis.extra.numpy.arrays` more pedantic about
``elements`` strategies that cannot be exactly represented as array elements.

In practice, you will see new warnings if you were using a ``float16`` or
``float32`` dtype without passing :func:`~hypothesis.strategies.floats` the
``width=16`` or ``width=32`` arguments respectively.

The previous behaviour could lead to silent truncation, and thus some elements
being equal to an explicitly excluded bound (:issue:`1899`).
