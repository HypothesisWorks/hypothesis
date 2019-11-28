RELEASE_TYPE: patch

This release adds some heuristics to test case generation that try to ensure that test cases generated early on will be relatively small.

This fixes a bug introduced in :ref:`Hypothesis 4.42.0 <v4.42.0>` which would cause occasional
:obj:`~hypothesis.HealthCheck.too_slow` failures on some tests.
