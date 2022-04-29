RELEASE_TYPE: patch

This patch fixes :issue:`3314`, where Hypothesis would raise an internal
error from :func:`~hypothesis.provisional.domains` or (only on Windows)
from :func:`~hypothesis.strategies.timezones` in some rare circumstances
where the installation was subtly broken.

Thanks to Munir Abdinur for this contribution.
