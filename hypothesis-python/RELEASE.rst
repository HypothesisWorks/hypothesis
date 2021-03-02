RELEASE_TYPE: minor

This patch fixes
:func:`~hypothesis.strategies._internal.types.type_sorting_key`
to avoid an exception due to type unions of the
:pypi:`typing_extensions` ``Literal`` backport on Python 3.6.
