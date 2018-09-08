RELEASE_TYPE: patch

This patch changes the behaviour of :func:`~hypothesis.reproduce_failure`
so that blobs are only printed in quiet mode when the
:obj:`~hypothesis.settings.print_blob` setting is set to ``ALWAYS``.

Thanks to Cameron McGill for writing this patch at the PyCon Australia sprints!
