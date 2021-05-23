RELEASE_TYPE: patch

Some of Hypothesis's numpy/pandas strategies use a ``fill`` argument to speed
up generating large arrays, by generating a single fill value and sharing that
value among many array slots instead of filling every single slot individually.

When no ``fill`` argument is provided, Hypothesis tries to detect whether it is
OK to automatically use the ``elements`` argument as a fill strategy, so that
it can still use the faster approach.

This patch fixes a bug that would cause that optimization to trigger in some
cases where it isn't 100% guaranteed to be OK.

If this makes some of your numpy/pandas tests run more slowly, try adding an
explicit ``fill`` argument to the relevant strategies to ensure that Hypothesis
always uses the faster approach.
