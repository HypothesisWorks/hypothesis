RELEASE_TYPE: patch

Hypothesis collects coverage information during the ``shrink`` and ``explain`` :ref:`phases <phases>` in order to show a more informative error message. On 3.12+, this uses :mod:`sys.monitoring`. This patch improves the performance of coverage collection on 3.12+ by disabling events we don't need.
