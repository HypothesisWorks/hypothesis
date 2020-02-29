RELEASE_TYPE: minor

This release adds an explicit warning for tests that are both decorated with
:func:`@given(...) <hypothesis.given>` and request a
:doc:`function-scoped pytest fixture <pytest:fixture>`, because such fixtures
are only executed once for *all* Hypothesis test cases and that often causes
trouble (:issue:`377`).

It's *very* difficult to fix this on the :pypi:`pytest` side, so since 2015
our advice has been "just don't use function-scoped fixtures with Hypothesis".
Now we detect and warn about the issue at runtime!
