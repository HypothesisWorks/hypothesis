RELEASE_TYPE: minor

:func:`~hypothesis.strategies.datetimes` now accepts timezone-aware
``min_value`` and ``max_value`` bounds, which are treated as moments in time.
In this case ``timezones`` defaults to :func:`~hypothesis.strategies.timezones`,
and each generated datetime lies between the two moments.
Passing one aware and one naive bound is an error.

If :pypi:`annotated-types` has been imported, the overloaded type hints
for this strategy now distinguish naive from aware datetimes using
``Timezone`` metadata.
