RELEASE_TYPE: minor

This release changes the stateful testing backend from
:func:`~hypothesis.find` to use :func:`@given <hypothesis.given>`
(:issue:`1300`).  This doesn't change how you create stateful tests,
but does make them run more like other Hypothesis tests.

:func:`@reproduce_failure <hypothesis.reproduce_failure>` and
:func:`@seed <hypothesis.seed>` now work for stateful tests.

Stateful tests now respect the :attr:`~hypothesis.settings.deadline`
and :attr:`~hypothesis.settings.suppress_health_check` settings,
though they are disabled by default.  You can enable them by using
:func:`@settings(...) <hypothesis.settings>` as a class decorator
with whatever arguments you prefer.
