RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.strategies._internal.types.is_a_new_type`.
It was failing on Python ``3.10.0b4``, where ``NewType`` is a function.
