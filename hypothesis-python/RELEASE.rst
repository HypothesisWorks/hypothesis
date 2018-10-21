RELEASE_TYPE: patch

The abstract number classes :class:`~python:numbers.Number`,
:class:`~python:numbers.Complex`, :class:`~python:numbers.Real`,
:class:`~python:numbers.Rational`, and :class:`~python:numbers.Integral`
are now supported by the :func:`~hypothesis.strategies.from_type` 
strategy.  Previously, you would have to use 
:func:`~hypothesis.strategies.register_type_strategy` before they
could be resolved (:issue:`1636`)