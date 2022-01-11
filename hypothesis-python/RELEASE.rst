RELEASE_TYPE: minor

This preserves the type annotations of functions passed to :func:`hypothesis.strategies.composite` and :func:`hypothesis.strategies.functions` by using :obj:`python:typing.ParamSpec`.

This improves the ability of static type-checkers to check test code that uses Hypothesis, and improves auto-completion in IDEs.