RELEASE_TYPE: patch

This release fixes a problem introduced in `3.56.0 <v3.56.0>` where
setting :obj:`~hypothesis.settings.max_examples` to ``1`` test failing with
``Unsatisfiable``. This problem could also occur in other harder to trigger
circumstances (e.g. by setting it to a low value, having a hard to satisfy
assumption, and disabling health checks).
