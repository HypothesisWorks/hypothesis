RELEASE_TYPE: patch

This patch exposes :class:`~hypothesis.strategies.DataObject`, *solely*
to support more precise type hints.  Objects of this type are provided
by :func:`~hypothesis.strategies.data`, and can be used to draw examples
from strategies intermixed with your test code.
