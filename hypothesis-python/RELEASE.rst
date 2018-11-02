RELEASE_TYPE: minor

Our pytest plugin now warns you when strategy functions have been collected
as tests, which may happen when e.g. using the
:func:`@composite <hypothesis.strategies.composite>` decorator when you
should be using ``@given(st.data())`` for inline draws.
Such functions *always* pass when treated as tests, because the lazy creation
of strategies mean that the function body is never actually executed!
