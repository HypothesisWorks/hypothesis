RELEASE_TYPE: minor

Values recorded with :func:`~hypothesis.note` are now included in
:ref:`observability <observability>` reports, as an ordered list of strings
under the ``metadata.notes`` key of each test-case observation.  Previously,
notes were only shown in the terminal for the minimal failing example (or
for every example under |Verbosity.verbose|), and never appeared in
observations at all.

The :class:`~hypothesis.errors.Unsatisfiable` error message now explains
when Hypothesis has tried every possible input, so that the assumptions of
the test are impossible to satisfy and running more examples cannot help.
Also removes an outdated reference to test timeouts from the
:class:`~hypothesis.errors.Unsatisfiable` docstring; the timeout setting
was removed in :v:`4.0.0`.
