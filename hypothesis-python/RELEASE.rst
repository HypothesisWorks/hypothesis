RELEASE_TYPE: minor

This release improves the :func:`~hypothesis.extra.lark.from_lark` strategy,
tightening argument validation and adding the ``explicit`` argument to allow use
with terminals that use ``@declare`` instead of a string or regular expression.

This feature is required to handle features such as indent and dedent tokens
in Python code, which can be generated with the :pypi:`hypothesmith` package.
