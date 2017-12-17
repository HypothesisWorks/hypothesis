RELEASE_TYPE: patch

This release fixes :issue:`997`, in which under some circumstances the body of
tests run under Hypothesis would not show up when run under coverage even
though the tests were run and the code they called outside of the test file
would show up normally.
