RELEASE_TYPE: major

This is a major release of Hypothesis, which removes deprecated APIs but
has no other breaking changes.  There are no new features in this version.

If your code runs without *warnings* on the last minor version of Hypothesis 3,
it will run without warnings or errors on Hypothesis 4.0.x and you will find
upgrading very easy.


Strategies removed in Hypothesis 4
==================================

- ``streaming()`` and ``choices()`` were both deprecated in 3.15.0, and should
  both be replaced with the :func:`~hypothesis.strategies.data` strategy.
- The ``fake_factory`` extra was deprecated in 3.42.0, and should be replaced
  with a strategy for the given type (e.g. :func:`~hypothesis.strategies.text`,
  :func:`~hypothesis.strategies.integers`, or
  :func:`~hypothesis.strategies.from_regex`).
- The ``datetime`` extra was deprecated in 3.11.0, and should be replaced by
  the core :func:`~hypothesis.strategies.dates`,
  :func:`~hypothesis.strategies.times`, and
  :func:`~hypothesis.strategies.datetimes` strategies.


Other changes in Hypothesis 4
=============================

- :func:`~hypothesis.strategies.dates`, :func:`~hypothesis.strategies.times`,
  and :func:`~hypothesis.strategies.datetimes` now *only* accept ``min_value``
  and ``max_value`` as bounding arguments.
