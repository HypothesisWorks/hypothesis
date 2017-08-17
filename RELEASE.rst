RELEASE_TYPE: patch
Release to fix a bug where mocks can be used as test runners under certain
conditions. Specifically, if a mock is injected into a test via pytest
fixtures or patch decorators, and that mock is the first argument in the
list, hypothesis will think it represents self and turns the mock
into a test runner.  If this happens, the affected test always passes
because the mock is executed instead of the test body. Sometimes, it
will also fail health checks.

Related to a section of issue 198 and fixes issue 491
(a partial duplicate of 198).

Thanks to Ben Peterson for this bug fix.
