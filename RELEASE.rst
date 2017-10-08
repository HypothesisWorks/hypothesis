RELEASE_TYPE: minor

This changes the default value of
:attr:`use_coverage=True <hypothesis.settings.use_coverage>` to True when
running on pypy (it was already True on CPython).

It was previously set to False because we expected it to be too slow, but
recent benchmarking shows that actually performance of the feature on pypy is
fairly acceptable - sometimes it's slower than on CPython, sometimes it's
faster, but it's generally within a factor of two either way.
