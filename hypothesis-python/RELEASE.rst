RELEASE_TYPE: patch

This patch corrects the exception type and error message you get if you attempt
to use :func:`~hypothesis.strategies.data` to draw from something which is not
a strategy.  This never worked, but the error is more helpful now.
