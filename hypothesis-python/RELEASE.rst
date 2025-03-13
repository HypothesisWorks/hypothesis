RELEASE_TYPE: patch

:func:`~hypothesis.strategies.randoms` no longer produces ``1.0``, matching
the exclusive upper bound of :obj:`random.Random.random` (:issue:`4297`).
