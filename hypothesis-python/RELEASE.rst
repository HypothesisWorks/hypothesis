RELEASE_TYPE: minor

This release improves Hypothesis' ability to resolve forward references in 
type annotations. It fixes a bug that prevented 
:func:`~hypothesis.strategies.builds` from being used with `pydantic models that
possess updated forward references <https://pydantic-docs.helpmanual.io/usage/postponed_annotations/>`__. See :issue:`3519`.