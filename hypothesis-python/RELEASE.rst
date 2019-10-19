RELEASE_TYPE: patch

This patch makes stateful step printing expand the result of a step into
multiple variables when a MultipleResult is returned (:issue:`2139`).
Thanks to Joseph Weston for reporting and fixing this bug!
