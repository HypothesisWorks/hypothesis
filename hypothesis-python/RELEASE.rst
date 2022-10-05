RELEASE_TYPE: patch

This patch improves the error message when Hypothesis detects "flush to zero"
mode for floating-point: we now report which package(s) enabled this, which
can make debugging much easier.  See :issue:`3458` for details.
