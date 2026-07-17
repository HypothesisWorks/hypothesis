RELEASE_TYPE: minor

:func:`~hypothesis.strategies.from_type` now supports the :pypi:`annotated-types`
``Timezone`` constraint on :class:`~python:datetime.datetime` and
:class:`~python:datetime.time`: ``Timezone(None)`` generates naive values,
``Timezone(...)`` generates aware values with any timezone, and a timezone
string or :class:`~python:datetime.tzinfo` instance generates values in that
specific timezone.  Previously this constraint was ignored with a warning.

In addition, the ``ResolutionFailed`` error for an ``Annotated`` type nested
in the metadata position now explains that generic aliases such as
``annotated_types.LowerCase`` should be subscripted with the type and used in
the type position - e.g. ``LowerCase[str]`` rather than
``Annotated[str, LowerCase]``.
