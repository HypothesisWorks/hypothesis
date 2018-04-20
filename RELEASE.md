RELEASE_TYPE: patch

This improves Hypothesis for Ruby's shrinking to be much closer
to Hypothesis for Python's. It's still far from complete, and even
in cases where it has the same level of quality it will often be
significantly slower, but examples should now be much more consistent,
especially in cases where you are using e.g. `built_as`.
