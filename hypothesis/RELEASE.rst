RELEASE_TYPE: minor

:func:`~hypothesis.strategies.from_type` now supports the :pypi:`annotated-types`
``Timezone`` constraint on :class:`~python:datetime.datetime` and
:class:`~python:datetime.time`, resolves the :pypi:`typing-extensions`
``TypeAliasType`` backport as well as the native form from Python 3.12+, and
suggests subscripting generic aliases like ``annotated_types.LowerCase`` if
they are mistakenly passed as ``Annotated`` metadata.
