RELEASE_TYPE: patch

This patch ensures that we shorten tracebacks for tests which fail due
to inconsistent data generation between runs (i.e. raise ``Flaky``).
