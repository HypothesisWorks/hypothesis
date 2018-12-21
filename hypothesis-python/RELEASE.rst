RELEASE_TYPE: major

Welcome to the next major version of Hypothesis!

There are no new features here, as we release those in minor versions.
Instead, 4.0 is a chance for us to remove deprecated features (many already
converted into no-ops), and turn a variety of warnings into errors.

If you were running on the last version of Hypothesis 3.x *without any
Hypothesis deprecation warnings* (or using private APIs), this will be
a very boring upgrade.  **In fact, nothing will change for you at all.**
Per :ref:`our deprecation policy <deprecation-policy>`, warnings added in
the last six months (after 2018-07-05) have not been converted to errors.


Removals
~~~~~~~~
- ``hypothesis.extra.datetime`` has been removed, replaced by the core
  date and time strategies.
- ``hypothesis.extra.fakefactory`` has been removed, replaced by general
  expansion of Hypothesis' strategies and the third-party ecosystem.
- The SQLite example database backend has been removed.

Settings
~~~~~~~~
- The :obj:`~hypothesis.settings.deadline` is now enforced by default, rather than just
  emitting a warning when the default (200 milliseconds per test case) deadline is exceeded.
- The ``database_file`` setting has been removed; use :obj:`~hypothesis.settings.database`.
- The ``perform_health_check`` setting has been removed; use
  :obj:`~hypothesis.settings.suppress_health_check`.
- The ``max_shrinks`` setting has been removed; use :obj:`~hypothesis.settings.phases`
  to disable shrinking.
- The ``min_satisfying_examples``, ``max_iterations``, ``strict``, ``timeout``, and
  ``use_coverage`` settings have been removed without user-configurable replacements.

Strategies
~~~~~~~~~~
- The ``elements`` argument is now required for collection strategies.
- The ``average_size`` argument was a no-op and has been removed.
- Date and time strategies now only accept ``min_value`` and ``max_value`` for bounds.
- :func:`~hypothesis.strategies.builds` now requires that the thing to build is
  passed as the first positional argument.
- Alphabet validation for :func:`~hypothesis.strategies.text` raises errors, not warnings,
  as does category validation for :func:`~hypothesis.strategies.characters`.
- The ``choices()`` strategy has been removed.  Instead, you can use
  :func:`~hypothesis.strategies.data` with :func:`~hypothesis.strategies.sampled_from`,
  so ``choice(elements)`` becomes ``data.draw(sampled_from(elements))``.
- The ``streaming()`` strategy has been removed.  Instead, you can use
  :func:`~hypothesis.strategies.data` and replace iterating over the stream with
  ``data.draw()`` calls.
- :func:`~hypothesis.strategies.sampled_from` and :func:`~hypothesis.strategies.permutations`
  raise errors instead of warnings if passed a collection that is not a sequence.

Miscellaneous
~~~~~~~~~~~~~
- Applying :func:`@given <hypothesis.given>` to a test function multiple times
  was really inefficient, and now it's also an error.
- Using the ``.example()`` method of a strategy (intended for interactive
  exploration) within another strategy or a test function always weakened
  data generation and broke shrinking, and now it's an error too.
- The ``HYPOTHESIS_DATABASE_FILE`` environment variable is no longer
  supported, as the ``database_file`` setting has been removed.
- The ``HYPOTHESIS_VERBOSITY_LEVEL`` environment variable is no longer
  supported.  You can use the ``--hypothesis-verbosity`` pytest argument instead,
  or write your own setup code using the settings profile system to replace it.
- Using :func:`@seed <hypothesis.seed>` or
  :obj:`derandomize=True <hypothesis.settings.derandomize>` now forces
  :obj:`database=None <hypothesis.settings.database>` to ensure results
  are in fact reproducible.  If :obj:`~hypothesis.settings.database` is
  *not* ``None``, doing so also emits a ``HypothesisWarning``.
- Unused exception types have been removed from ``hypothesis.errors``;
  namely ``AbnormalExit``, ``BadData``, ``BadTemplateDraw``,
  ``DefinitelyNoSuchExample``, ``Timeout``, and ``WrongFormat``.
