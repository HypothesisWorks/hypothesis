RELEASE_TYPE: minor

:func:`~hypothesis.register_random` has used :mod:`weakref` since :ref:`v6.27.1`,
allowing the :class:`~random.Random`-compatible objects to be garbage-collected when
there are no other references remaining in order to avoid memory leaks.
We now raise an error or emit a warning when this seems likely to happen immediately.

The type annotation of :func:`~hypothesis.register_random` was also widened so that
structural subtypes of :class:`~random.Random` are accepted by static typecheckers.
