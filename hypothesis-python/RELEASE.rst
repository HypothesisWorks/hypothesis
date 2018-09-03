RELEASE_TYPE: patch

This patch fixes an internal bug where a corrupted argument to
:func:`@reproduce_failure <hypothesis.reproduce_failure>` could raise
the wrong type of error.  Thanks again to Paweł T. Jochym, who maintains
Hypothesis on `conda-forge <https://conda-forge.org/>`_ and consistently
provides excellent bug reports including :issue:`1558`.
