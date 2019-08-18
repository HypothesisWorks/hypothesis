RELEASE_TYPE: minor

The :func:`~hypothesis.strategies.from_type` strategy now knows to look up
the subclasses of abstract types, which cannot be instantiated directly.

This is very useful for :pypi:`hypothesmith` to support :pypi:`libCST`.
