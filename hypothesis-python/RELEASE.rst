RELEASE_TYPE: patch

This patch ensures that :doc:`stateful tests <stateful>` which raise an
error from a :pypi:`pytest` helper still print the sequence of steps
taken to reach that point (:issue:`1372`).  This reporting was previously
broken because the helpers inherit directly from ``BaseException``, and
therefore require special handling to catch without breaking e.g. the use
of ctrl-C to quit the test.
