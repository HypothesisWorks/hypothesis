RELEASE_TYPE: patch

This release changes the order in which Hypothesis tries most shrink operations.
This should have no effect on the final outcome but may affect performance - for small examples that are already fast, shrinking may get slightly slower,
but for large or pathological examples it will likely improve noticeably.
