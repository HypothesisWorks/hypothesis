RELEASE_TYPE: patch

This patch clarifies some error messages when the test function signature
is incompatible with the arguments to :func:`@given <hypothesis.given>`,
especially when the :obj:`@settings() <hypothesis.settings>` decorator
is also used (:issue:`1978`).
