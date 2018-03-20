RELEASE_TYPE: minor

This release deprecates use of :func:`@settings(...) <hypothesis.settings>`
as a decorator, on functions or methods that are not also decorated with
:func:`@given <hypothesis.given>`.  You can still apply these decorators
in any order, though only once each.

Using :func:`@settings(...) <hypothesis.settings>` as the sole decorator on
a test is completely pointless, so this common usage error will become an
error in a future version of Hypothesis.
