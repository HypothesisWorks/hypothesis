RELEASE_TYPE: patch

This patch fixes a bug where an exception raised by user code while the
conjecture data is frozen (for example after an explicit
``data.conjecture_data.freeze()``) was silently swallowed, so the test passed
instead of failing (:issue:`4132`). Such exceptions are now reported as test
failures. Internal control-flow markers (``Frozen``/``StopTest``) and errors
raised in a ``finally`` block while a ``StopTest`` was propagating are still
handled as before.

Thanks to feiiiiii5 for this fix!
