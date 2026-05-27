RELEASE_TYPE: patch

This patch fixes a bug where :ref:`fuzz_one_input <fuzz_one_input>` did not
track the ``interesting_origin`` of failures (:issue:`4420`).  As a result, it
only saved the single smallest failure to the database rather than the smallest
example of each distinct failure, and the ``interesting_origin`` was missing
from :ref:`observability <observability>` reports.
