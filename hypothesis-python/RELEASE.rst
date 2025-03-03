RELEASE_TYPE: patch

This patch deprecates the nesting of :func:`@given <hypothesis.given>` inside :func:`@given <hypothesis.given>`. We recommend using :func:`~hypothesis.strategies.data` to define the inner function instead. (:issue:`4167`)
