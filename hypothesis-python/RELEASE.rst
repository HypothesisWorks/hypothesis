RELEASE_TYPE: patch

This release adds type hints to the :func:`~hypothesis.example` and
:func:`~hypothesis.seed` decorators, and fixes the type hint on
:func:`~hypothesis.strategies.register_type_strategy`. The second argument to
:func:`~hypothesis.strategies.register_type_strategy` must either be a
``SearchStrategy``, or a callable which takes a ``type`` and returns a
``SearchStrategy``.
