RELEASE_TYPE: patch

This release fixes dependency information for coverage.  Previously Hypothesis
would allow installing :pypi:`coverage` with any version, but it only works
with coverage 4.0 or later.

We now specify the correct metadata in our ``setup.py``, so Hypothesis will
only allow installation with compatible versions of coverage.
