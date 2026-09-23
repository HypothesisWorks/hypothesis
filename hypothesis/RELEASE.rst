RELEASE_TYPE: patch

This patch fixes ``BytestringProvider.draw_integer`` so that it can generate
negative integers. Previously, only non-negative bit patterns were drawn and
checked against the bounds, so negative values were unreachable. When both
``min_value`` and ``max_value`` were negative, this caused an infinite loop.
