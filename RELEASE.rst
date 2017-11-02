RELEASE_TYPE: minor

Hypothesis now emits deprecation warnings if you apply
:func:`@given <hypothesis.given>` more than once to a target.

Applying :func:`@given <hypothesis.given>` repeatedly wraps the target multiple
times. Each wrapper will search the space of of possible parameters separately.
This is equivalent but will be much more inefficient than doing it with a
single call to :func:`@given <hypothesis.given>`.

For example, instead of
``@given(booleans()) @given(integers())``, you could write
``@given(booleans(), integers())``
