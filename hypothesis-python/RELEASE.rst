RELEASE_TYPE: patch

This patch improves the development experience by simplifying the tracebacks
you will see when e.g. you have used the ``.map(...)`` method of a strategy
and the mapped function raises an exception.

No new exceptions can be raised, nor existing exceptions change anything but
their traceback.  We're simply using if-statements rather than exceptions for
control flow in a certain part of the internals!
