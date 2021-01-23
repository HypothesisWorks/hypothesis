RELEASE_TYPE: patch

This patch improves the type annotations for :func:`~hypothesis.strategies.one_of`,
by adding overloads to handle up to five distinct arguments as
:class:`~python:typing.Union` before falling back to :class:`~python:typing.Any`,
as well as annotating the ``|`` (``__or__``) operator for strategies (:issue:`2765`).
