RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.strategies.builds`, so that when passed
:obj:`~hypothesis.infer` for an argument with a non-:class:`~python:typing.Optional`
type annotation and a default value of ``None`` to build a class which defines
an explicit ``__signature__`` attribute, either ``None`` or that type may be
generated.

This is unlikely to happen unless you are using :pypi:`pydantic` (:issue:`2648`).
