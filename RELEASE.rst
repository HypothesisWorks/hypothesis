RELEASE_TYPE: patch

This patch improves the quality of strategies inferred from Numpy dtypes:

* Signed integer dtypes generated examples with some upper bits set to zero
  due to an operator precedence bug.  The inferred strategies can now produce
  any representable value.
* Fixed-width unicode- and byte-string dtypes now cap the internal example
  length, which should improve example and shrink quality.
* Numpy arrays can only store fixed-size strings internally, and allow shorter
  strings by right-padding them with null bytes.  Inferred string strategies
  no longer generate such values, as they can never be retrieved from an array.

This has already been useful in Hypothesis - we found an overflow bug in our
Pandas support, and as a result :func:`~hypothesis.extra.pandas.indexes` and
:func:`~hypothesis.extra.pandas.range_indexes` now check that ``min_size``
and ``max_size`` are at least zero.
