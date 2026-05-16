RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.strategies.decimals` with ``places=``
generating values outside the requested ``min_value`` / ``max_value``
bounds when those bounds contain many significant digits (:issue:`4651`).
The internal precision was derived from :func:`math.log10`, which
captures only the order of magnitude and therefore under-allocated
precision both for very small bounds (``log10`` becomes negative) and
for bounds with many digits. We now count coefficient digits directly
from :meth:`~decimal.Decimal.as_tuple`.
