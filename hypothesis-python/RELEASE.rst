RELEASE_TYPE: patch

This patch implements filter-rewriting for :func:`~hypothesis.strategies.text`
and :func:`~hypothesis.strategies.binary` with the :meth:`~re.Pattern.search`,
:meth:`~re.Pattern.match`, or :meth:`~re.Pattern.fullmatch` method of a
:func:`re.compile`\ d regex.
