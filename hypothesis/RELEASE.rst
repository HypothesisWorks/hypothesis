RELEASE_TYPE: patch

This patch fixes a performance regression on Python 3.12 and 3.13, where the ``sys.monitoring`` line events for |Phase.explain| were left enabled even after the test had completed (:issue:`4964`).

Thanks to Anubhav Lal for this fix!
