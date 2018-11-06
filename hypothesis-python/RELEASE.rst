RELEASE_TYPE: patch

This patch fixes :issue:`1667`, where passing bounds of Numpy
dtype ``int64`` to :func:`~hypothesis.strategies.integers` could
cause errors on Python 3 due to internal rounding.
