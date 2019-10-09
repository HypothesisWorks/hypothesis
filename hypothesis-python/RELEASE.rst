RELEASE_TYPE: patch

This patch improves our type hints on the :func:`~hypothesis.strategies.emails`,
:func:`~hypothesis.strategies.functions`, :func:`~hypothesis.strategies.integers`,
:func:`~hypothesis.strategies.iterables`, and :func:`~hypothesis.strategies.slices`
strategies, as well as the ``.filter()`` method.

There is no runtime change, but if you use :pypi:`mypy` or a similar
type-checker on your tests the results will be a bit more precise.
