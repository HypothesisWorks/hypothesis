RELEASE_TYPE: patch

This patch fixes type annotations that had caused the signature of 
:func:`@given <hypothesis.given>` to be partially-unknown to type-checkers for Python 
versions before 3.10.
