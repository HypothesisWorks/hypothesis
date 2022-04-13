RELEASE_TYPE: patch

This patch makes it an explicit error to call
:func:`~hypothesis.strategies.register_type_strategy` with a
`Pydantic GenericModel <https://pydantic-docs.helpmanual.io/usage/models/#generic-models>`__
and a callable, because ``GenericModel`` isn't actually a generic type at
runtime and so you have to register each of the "parametrized versions"
(actually subclasses!) manually.  See :issue:`2940` for more details.
