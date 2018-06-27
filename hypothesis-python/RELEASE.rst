RELEASE_TYPE: patch

This patch fixes a conflict between the built-in Hypothesis plugin for Pytest,
and the new :ref:`test customisation interface <custom-function-execution>`
that caused errors if Hypothesis tests had other pytest markers applied
(:issue:`1362`).  Thanks to Matt Bullock for reporting this.
