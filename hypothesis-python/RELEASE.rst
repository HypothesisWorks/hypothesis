RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.strategies.from_type` on Python 2
for classes where ``cls.__init__ is object.__init__``.
Thanks to ccxcz for reporting :issue:`1656`.
