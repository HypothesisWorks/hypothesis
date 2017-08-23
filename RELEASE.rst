RELEASE_TYPE: minor

This release deprecates Hypothesis's strict mode, which turned Hypothesis's
deprecation warnings into errors. Similar functionality can be achieved
by using :func:`simplefilter('error', HypothesisDeprecationWarning) <python:warnings.simplefilter>`.
