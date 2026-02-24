RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.strategies.decimals` generating values
outside the specified ``min_value``/``max_value`` range when bounds have many
significant digits and ``places`` is set. The precision context for internal
arithmetic now uses the actual digit count from the :class:`~decimal.Decimal`
representation rather than ``log10(magnitude)``, which lost precision for
values with more significant digits than their magnitude implied.
