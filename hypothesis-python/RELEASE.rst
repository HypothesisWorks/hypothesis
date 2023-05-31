RELEASE_TYPE: patch

:func:`~hypothesis.strategies.from_type` now works in cases where we use
:func:`~hypothesis.strategies.builds` to create an instance and the constructor
has an argument which would lead to recursion.  Previously, this would raise
an error if the argument had a default value.

Thanks to Joachim B Haga for reporting and fixing this problem.
