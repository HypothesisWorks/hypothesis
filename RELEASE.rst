RELEASE_TYPE: patch

This patch improves the quality of strategies inferred from Numpy dtypes:

* Signed integer dtypes generated examples with some upper bits set to zero
  due to an operator precedence bug.  The inferred strategies can now produce
  any representable value.
