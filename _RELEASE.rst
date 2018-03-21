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
- :func:`~hypothesis.strategies.sampled_from` raises an error instead of
  issuing a deprecation warning when passed a non-sequence input.
- :func:`~hypothesis.strategies.builds` no longer supports the ``target``
  keyword - pass the callable to build as the first positional argument.
- Misuse of the ``.example()`` method of a strategy - while defining a
  strategy, or inside a test - is now an error instead of a warning.
- Applying :func:`@given <hypothesis.given>` multiple times to a single test
  is now an error instead of a warning.  Apply it once, with all the arguments
  in a single call.
- The deprecated SQLite3 example database has been removed.
- The ``categories`` arguments to :func:`~hypothesis.strategies.characters`
  are now strictly validated, so passing a non-existent category is an error.
- The ``settings`` keyword to `~hypothesis.settings.register_profile` was
  deprecated in favor of ``parent``, and has been removed.
- The ``strict`` setting was deprecated (and thus enabling it was an error),
  and has been removed.
- Unused Hypothesis exception types - ``BadData``, ``BadTemplateDraw``,
  ``DefinitelyNoSuchExample``, and ``WrongFormat`` - have been removed.
