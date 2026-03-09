RELEASE_TYPE: patch

This patch improves :class:`~hypothesis.errors.FlakyStrategyDefinition` error
messages to describe *what* changed between runs (e.g. different constraints,
different types, or a different number of draws), making it much easier to
diagnose flaky data generation. Duplicate errors are no longer raised when a
single mismatch triggers multiple checks, and when a real test failure is found
alongside a flaky strategy error, the real failure is now reported cleanly with
a warning about the flaky issue. Stateful tests also gain context about which
steps led to the error when observability is enabled.

Thanks to Ian Hunt-Isaak for this contribution!
