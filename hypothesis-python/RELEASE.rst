RELEASE_TYPE: minor

This release adds :func:`hypothesis.currently_in_test_context`, which can be used
to check whether the calling code is currently running inside an
:func:`@given <hypothesis.given>` or :doc:`stateful <stateful>` test.

This is most useful for third-party integrations and assertion helpers which may
wish to use :func:`~hypothesis.assume` or :func:`~hypothesis.target`, without also
requiring that the helper only be used from property-based tests (:issue:`2581`).
