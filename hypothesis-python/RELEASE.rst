RELEASE_TYPE: patch

This patch turns off a check in :func:`~hypothesis.register_random` for possibly
unreferenced RNG instances on the free-threaded build of CPython 3.13 because
this check has a much higher false positive rate in the free-threaded build
(:issue:`3965`).
