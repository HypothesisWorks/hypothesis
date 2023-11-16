RELEASE_TYPE: minor

This release teaches :func:`~hypothesis.strategies.from_type` to handle constraints
implied by the :pypi:`annotated-types` package - as used by e.g. :pypi:`Pydantic`.
This is usually efficient, but falls back to filtering in a few remaining cases.

Thanks to Viicos for :pull:`3780`!
