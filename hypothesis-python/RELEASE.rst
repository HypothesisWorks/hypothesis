RELEASE_TYPE: major

Welcome to the next major version of Hypothesis!

There are no new features here, as we release those in minor versions.
Instead, 5.0 is a chance for us to remove deprecated features (many already
converted into no-ops), and turn a variety of warnings into errors.

If you were running on the last version of Hypothesis 4.x *without any
Hypothesis deprecation warnings*, this will be a very boring upgrade.
**In fact, nothing will change for you at all.**

.. note::
    This release drops support for Python 2, which has passed
    `its end of life date <https://devguide.python.org/#status-of-python-branches>`__.
    The `Python 3 Statement <https://python3statement.org/>`__ outlines our
    reasons, and lists many other packages that have made the same decision.

    ``pip install hypothesis`` should continue to give you the latest compatible version.
    If you have somehow ended up with Hypothesis 5.0 on Python 2, you need to update your
    packaging stack to ``pip >= 9.0`` and ``setuptools >= 24.2`` - see `here for details
    <https://packaging.python.org/guides/distributing-packages-using-setuptools/#python-requires>`__.
    Then ``pip uninstall hypothesis && pip install hypothesis`` will get you back to
    a compatible version.


Strategies
~~~~~~~~~~
- :func:`~hypothesis.strategies.integers` bounds must be equal to an integer,
  though they can still be other types.
- If :func:`~hypothesis.strategies.fractions` is passed a ``max_denominator``,
  the bounds must have at most that denominator.
- :func:`~hypothesis.strategies.floats` bounds must be exactly representable as a
  floating-point number with the given ``width``.  If not, the error message
  includes the nearest such number.
- :func:`sampled_from([]) <hypothesis.strategies.sampled_from>` is now an error.
- The values from the ``elements`` and ``fill`` strategies for
  :func:`hypothesis.extra.numpy.arrays` must be losslessly representable in an
  array of the given dtype.
- The ``min_size`` and ``max_size`` arguments to all collection strategies must
  be of type :class:`python:int` (or ``max_size`` may be ``None``).

Miscellaneous
~~~~~~~~~~~~~
- The ``.example()`` method of strategies (intended for interactive
  exploration) no longer takes a ``random`` argument.
- You may pass either the ``target`` or ``targets`` argument to stateful rules, but not both.
- :obj:`~hypothesis.settings.deadline` must be ``None`` (to disable), a
  :class:`~python:datetime.timedelta`, or an integer or float number of milliseconds.
- Both of :obj:`~hypothesis.settings.derandomize` and
  :obj:`~hypothesis.settings.print_blob` must be either ``True`` or ``False``,
  where they previously accepted other values.
- :obj:`~hypothesis.settings.stateful_step_count` must be at least one.
- :obj:`~hypothesis.settings.max_examples` must be at least one.
  To disable example generation, use the :obj:`~hypothesis.settings.phases` setting.

Removals
~~~~~~~~
- ``hypothesis.stateful.GenericStateMachine`` in favor of :class:`hypothesis.stateful.RuleBasedStateMachine`
- ``hypothesis.extra.django.models.models`` in favor of :func:`hypothesis.extra.django.from_model`
  and ``hypothesis.extra.django.models.add_default_field_mapping`` in favor of
  :func:`hypothesis.extra.django.register_field_strategy`
- ``hypothesis.HealthCheck.hung_test``, without replacement
- ``hypothesis.settings.buffer``, without replacement
- ``hypothesis.PrintSettings``, because :obj:`hypothesis.settings.print_blob` takes ``True`` or ``False``
- ``hypothesis.settings.timeout``, in favor of :obj:`hypothesis.settings.deadline`
- ``hypothesis.unlimited`` without replacement (only only useful as argument to ``timeout``)
