RELEASE_TYPE: minor

This release adds a new mechanism to infer strategies for classes
defined using :pypi:`attrs`, based on the the type, converter, or
validator of each attribute.  This inference is now built in to
:func:`~hypothesis.strategies.builds` and :func:`~hypothesis.strategies.from_type`.

On Python 2, :func:`~hypothesis.strategies.from_type` no longer generates
instances of ``int`` when passed ``long``, or vice-versa.
