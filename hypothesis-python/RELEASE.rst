RELEASE_TYPE: patch

This makes ``model`` a positional-only argument to
:func:`~hypothesis.extra.django.from_model`, to support models
with a field literally named "model" (:issue:`2369`).
