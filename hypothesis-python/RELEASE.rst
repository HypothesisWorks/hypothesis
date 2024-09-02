RELEASE_TYPE: patch

This patch adds support for variable-width bytes in our IR layer (:pull:`3962`), which should mean improved performance anywhere you use :func:`~hypothesis.strategies.binary`.
