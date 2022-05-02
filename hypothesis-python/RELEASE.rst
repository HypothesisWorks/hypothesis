RELEASE_TYPE: patch

This patch refactors the strategy classes hypothesis uses internally to implement the
`floats() <https://hypothesis.readthedocs.io/en/latest/data.html#hypothesis.strategies.floats>`__
strategy.
It should not produce in any behavioral changes.
This refactoring supports
`a larger refactoring <https://github.com/HypothesisWorks/hypothesis/issues/3086>`__
to facilitate integrations with symbolic execution tools and fuzzers.
