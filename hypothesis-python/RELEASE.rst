RELEASE_TYPE: patch

This patch teaches :func:`~hypothesis.strategies.builds` and
:func:`~hypothesis.strategies.from_type` to use the ``__signature__``
attribute of classes where it has been set, improving our support
for :pypi:`Pydantic` models (`in pydantic >= 1.5
<https://github.com/samuelcolvin/pydantic/pull/1034>`__).
