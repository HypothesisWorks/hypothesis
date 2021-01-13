RELEASE_TYPE: patch

This patch fixes an interaction where our :ref:`test statistics <statistics>`
handling made Pytest's ``--junit-xml`` output fail to validate against the
strict ``xunit2`` schema (:issue:`1975`).
