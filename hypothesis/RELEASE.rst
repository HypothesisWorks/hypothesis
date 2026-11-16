RELEASE_TYPE: patch

This patch fixes a performance regression on Python 3.12 and 3.13, where
the ``sys.monitoring`` line events used to explain a failing test were left
enabled afterwards, slowing down the rest of the process (:issue:`4964`).

Thanks to Anubhav Lal for this fix, and to ternasky for reporting it!
