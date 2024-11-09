RELEASE_TYPE: patch

This patch migrates the optimisation algorithm for :ref:`targeted property-based testing <targeted-search>` to our IR layer (:issue:`3921`). This should result in moderately different (and hopefully improved) exploration behavior in tests which use :func:`hypothesis.target`
