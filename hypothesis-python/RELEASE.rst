RELEASE_TYPE: patch

This patch documents :func:`~hypothesis.strategies.timezones`
`Windows-only requirement <https://docs.python.org/3/library/zoneinfo.html#data-sources>`__
for the :pypi:`tzdata` package, and ensures that
``pip install hypothesis[zoneinfo]`` will install the latest version.
