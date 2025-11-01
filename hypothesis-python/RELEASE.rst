RELEASE_TYPE: patch

:func:`~hypothesis.strategies.from_type` now correctly handles :pypi:`annotated-types`
annotations on :class:`typing.TypedDict` fields which are also marked as being
:obj:`~typing.ReadOnly`, :obj:`~typing.Required`, or :obj:`~typing.NotRequired`
(:issue:`4474`).
