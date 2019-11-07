RELEASE_TYPE: patch

This release ensures that the strategies passed to
:func:`@given <hypothesis.given>` are properly validated when applied to a test
method inside a test class.

This should result in clearer error messages when some of those strategies are
invalid.
