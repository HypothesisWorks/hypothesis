RELEASE_TYPE: minor

This release deprecates use of :func:`@settings(...) <hypothesis.settings>`
as a decorator, on functions or methods that are not also decorated with
:func:`@given <hypothesis.given>`.  You can still apply these decorators
in any order, though you should only do so once each.

Applying :func:`@given <hypothesis.given>` twice was already deprecated, and
applying :func:`@settings(...) <hypothesis.settings>` twice is deprecated in
this release and will become an error in a future version. Neither could ever
be used twice to good effect.)

Using :func:`@settings(...) <hypothesis.settings>` as the sole decorator on
a test is completely pointless, so this common usage error will become an
error in a future version of Hypothesis.
